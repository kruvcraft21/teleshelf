import logging
from typing import Any

from config import DatabaseSettings

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncAttrs, AsyncEngine
from sqlalchemy import engine, Column, Integer, BigInteger, Text, ForeignKey, URL, select, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(AsyncAttrs, DeclarativeBase):
    pass

class UserChats(Base):
    __tablename__ = 'user_chats'

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id : Mapped[int] = mapped_column(BigInteger, primary_key=True)

class Topic(Base):
    __tablename__ = 'topics'

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    topic_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(Text)

    files: Mapped[list["File"]] = relationship(back_populates="topic", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uniqe_chat_topic_id", "chat_id", "topic_id", unique=True),
    )

class File(Base):
    __tablename__ = 'files'

    id : Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    topic_id: Mapped[int] = mapped_column(Integer, ForeignKey('topics.id', ondelete='CASCADE'))
    tg_file_id: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)

    topic: Mapped["Topic"] = relationship(back_populates="files")
    positions: Mapped[list["Position"]] = relationship(back_populates="file", cascade="all, delete-orphan")

class Position(Base):
    __tablename__ = 'positions'

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey('files.id', ondelete='CASCADE'), primary_key=True)
    page: Mapped[int] = mapped_column(Integer)

    file: Mapped["File"] = relationship(back_populates="positions")


class Database:
    def __init__(self, engin : AsyncEngine, session_maker : async_sessionmaker[AsyncSession | Any], logger: logging.Logger):
        self._engine = engin
        self._session = session_maker
        self.logger = logger

    @classmethod
    async def create(cls, db_settings: DatabaseSettings):
        # self = cls()
        logger = logging.getLogger(__name__)
        logger.info(f"Пытаемся подключится")
        database_url = URL.create(
            drivername="postgresql+asyncpg",
            username=db_settings.username,
            password=db_settings.password,
            host=db_settings.host,
            port=db_settings.port,
            database=db_settings.database,
        )
        logger.info(f"Вроде бы получили ссылку")
        _engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
        )
        _session = async_sessionmaker(
            bind=_engine,
            expire_on_commit=False,
            autoflush=False,
        )
        self = cls(_engine, session_maker=_session, logger=logger)
        self.logger.info("Автоматическое создание таблиц при инициализации базы...")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.logger.info("База данных полностью готова к работе.")
        return self

    async def try_add_user(self, user_id : int, chat_id : int) -> None:
        async with self._session.begin() as session:
            users = await session.get(UserChats, (user_id, chat_id))
            if users is None:
                new_user = UserChats(user_id=user_id, chat_id=chat_id)
                session.add(new_user)

    async def try_add_chat(self, chat_id: int, topic_id: int, topic_title: str) -> int:
        async with self._session.begin() as session:
            chat : Any = await session.scalar(select(Topic).where(Topic.chat_id == chat_id)
                                  .where(Topic.topic_id == topic_id))
            if chat is None:
                chat = Topic(chat_id=chat_id, topic_id=topic_id, files=[], title=topic_title)
                session.add(chat)

            if chat.title != topic_title:
                chat.title = topic_title

        return chat.id

    async def try_add_file(self, file_id: str, topic_id: int, caption: str | None) -> None:
        async with self._session.begin() as session:
            chat = await session.get(Topic, topic_id)
            if chat is not None:
                files: list[File] = await chat.awaitable_attrs.files
                if not any(file.tg_file_id == file_id for file in files):
                    new_file_in_topic = File(topic_id=topic_id, caption=caption, tg_file_id=file_id, positions=[])
                    files.append(new_file_in_topic)

    async def get_chats(self, user_id: int) -> dict[str, int]:
        result = {}
        async with self._session() as session:
            user_chats = await session.scalars(select(UserChats.chat_id).where(UserChats.user_id == user_id))
            iter_topic = await session.execute(select(Topic.id, Topic.title).where(Topic.chat_id.in_(user_chats)))
            for topic in iter_topic.all():
                result[topic.title] = topic.id
        return result

    async def get_files(self, topic_id: int) -> dict[str, int]:
        result = {}
        async with self._session() as session:
            topic = await session.get(Topic, topic_id)
            if topic is not None:
                files = await topic.awaitable_attrs.files
                for file in files:
                    result[file.caption] = file.id
        return result

    async def get_topic_title(self, topic_id: int) -> str:
        result = ""
        async with self._session() as session:
            topic = await session.get(Topic, topic_id)
            if topic is not None:
                result = str(topic.title)
        return result

if __name__ == "__main__":
    from config import load_config
    import asyncio

    config = load_config()
    logging.basicConfig(
        level=logging.getLevelName(level=config.log.level),
        format=config.log.format,
    )

    async def clear_db():
        db = await Database.create(config.database)
        async with db._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def main():
        db = await Database.create(config.database)

    asyncio.run(main())