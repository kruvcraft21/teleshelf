import logging
from dataclasses import dataclass
from typing import Any

from config import PGDatabseSettings

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy import URL, select, delete
from sqlalchemy.dialects.postgresql import insert

from database.models import Base, UserChats, Topic, File, Position

@dataclass
class FileInfo:
    file_id: int
    caption: str
    page: int


class PostgresStorage:
    def __init__(self, engin: AsyncEngine, session_maker: async_sessionmaker[AsyncSession | Any],
                 logger: logging.Logger):
        self._engine = engin
        self._session = session_maker
        self.logger = logger

    @classmethod
    async def create(cls, db_settings: PGDatabseSettings):
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

    async def try_add_user(self, user_id: int, chat_id: int) -> None:
        async with self._session.begin() as session:
            users = await session.get(UserChats, (user_id, chat_id))
            if users is None:
                new_user = UserChats(user_id=user_id, chat_id=chat_id)
                session.add(new_user)

    async def try_add_chat(self, chat_id: int, topic_id: int, topic_title: str) -> int:
        async with self._session.begin() as session:
            chat: Any = await session.scalar(select(Topic).where(Topic.chat_id == chat_id)
                                             .where(Topic.topic_id == topic_id))
            if chat is None:
                chat = Topic(chat_id=chat_id, topic_id=topic_id, files=[], title=topic_title)
                session.add(chat)

            if chat.title != topic_title:
                chat.title = topic_title

        return chat.id

    async def try_add_file(self, file_id: str, topic_id: int, caption: str | None, file_type: str) -> None:
        async with self._session.begin() as session:
            stmt = select(File.id).where(File.topic_id == topic_id,
                                         File.tg_file_id == file_id)
            file = await session.scalar(stmt)
            if file is None:
                new_file = File(topic_id=topic_id, caption=caption, tg_file_id=file_id, positions=[],
                                file_type=file_type)
                session.add(new_file)

    @staticmethod
    async def _upsert_files(files: list[dict], session: AsyncSession) -> None:
        if not files:
            return
        stmt = insert(File).values(files)
        stmt = stmt.on_conflict_do_update(
            index_elements=[File.topic_id, File.tg_file_id],
            set_={
                "caption": stmt.excluded.caption,
                "file_type": stmt.excluded.file_type,
            }
        )
        await session.execute(stmt)

    @staticmethod
    async def _delete_missing_files(expected_files, session: AsyncSession) -> None:
        for topic_id, file_ids in expected_files.items():
            await session.execute(
                delete(File).where(File.topic_id == topic_id, File.tg_file_id.notin_(file_ids))
            )

    @staticmethod
    async def _delete_topics(chat_id: int, topic_ids: list[int], session: AsyncSession) -> None:
        await session.execute(
            delete(Topic).where(Topic.id.notin_(topic_ids), Topic.chat_id == chat_id)
        )

    async def update_chat_status(self,
                                 chat_id: int,
                                 topic_ids: list[int],
                                 files: list[dict],
                                 expected_files: dict[int, list[str]]
                                 ) -> None:
        async with self._session.begin() as session:
            await self._upsert_files(files, session)
            await self._delete_topics(chat_id, topic_ids, session)
            await self._delete_missing_files(expected_files, session)

    async def get_chats(self, user_id: int) -> dict[str, int]:
        result = {}
        async with self._session() as session:
            user_chats = await session.scalars(select(UserChats.chat_id).where(UserChats.user_id == user_id))
            iter_topic = await session.execute(select(Topic.id, Topic.title).where(Topic.chat_id.in_(user_chats)))
            for topic in iter_topic.all():
                result[topic.title] = topic.id
        return result

    async def get_files(self, topic_id: int, user_id: int) -> list[FileInfo]:
        async with self._session() as session:
            stmt = (
                select(File.id, File.caption, Position.page)
                .outerjoin(
                    Position, (Position.file_id == File.id) & (Position.user_id == user_id)
                )
                .where(File.topic_id == topic_id)
                .order_by(File.id)
            )
            rows = await session.execute(stmt)
            return [
                FileInfo(
                    file_id=file_id,
                    caption=file_caption or "None",
                    page=page or 0
                )
                for file_id, file_caption, page in rows
            ]

    async def get_topic_title(self, topic_id: int) -> str:
        result = ""
        async with self._session() as session:
            topic = await session.get(Topic, topic_id)
            if topic is not None:
                result = str(topic.title)
        return result

    async def get_or_create_position(self, file_id: int, user_id: int) -> tuple[Position | None, str]:
        async with self._session.begin() as session:
            position = await session.scalar(select(Position).where(Position.user_id == user_id,
                                                                   Position.file_id == file_id))
            tg_file_id = await session.scalar(select(File.tg_file_id).where(File.id == file_id))
            if tg_file_id is None:
                return None, ""

            if position is None:
                position = Position(user_id=user_id, file_id=file_id, page=0)
                session.add(position)

            return position, tg_file_id

    async def try_add_positions(self, positions: list[dict]):
        stmt = insert(Position).values(positions)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Position.user_id, Position.file_id],
            set_={
                "page": stmt.excluded.page,
            }
        )
        async with self._session.begin() as session:
            result = await session.execute(stmt)

    async def close(self):
        await self._engine.dispose()


if __name__ == "__main__":
    from config import load_config
    import asyncio

    config = load_config()
    logging.basicConfig(
        level=logging.getLevelName(level=config.log.level),
        format=config.log.format,
    )


    async def clear_db():
        db = await PostgresStorage.create(config.database)
        async with db._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


    async def main():
        db = await PostgresStorage.create(config.database)


    asyncio.run(main())
