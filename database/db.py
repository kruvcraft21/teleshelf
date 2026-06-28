import logging
from compileall import compile_file
from typing import Any

from config import DatabaseSettings

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import engine, Column, Integer, BigInteger, String, ForeignKey, URL
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserChats(Base):
    __tablename__ = 'user_chats'

    user_id = Column(BigInteger, primary_key=True)
    chat_id = Column(BigInteger, primary_key=True)

class Topics(Base):
    __tablename__ = 'topics'

    id = Column(Integer, autoincrement=True, primary_key=True)
    topic_id = Column(BigInteger, nullable=False)
    title = Column(String)

class Files(Base):
    __tablename__ = 'files'

    id = Column(Integer, autoincrement=True, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id', ondelete='CASCADE'))
    tg_file_id = Column(BigInteger, nullable=False)
    caption = Column(String)

class Progress(Base):
    __tablename__ = 'progress'

    user_id = Column(BigInteger, primary_key=True)
    file_id = Column(Integer, ForeignKey('files.id', ondelete='CASCADE'), primary_key=True)
    page = Column(Integer)


class Database:
    def __init__(self):
        self._engine = None
        self._session : async_sessionmaker[AsyncSession | Any] | None = None
        self.logger = logging.getLogger(__name__)

    @classmethod
    async def create(cls, db_settings: DatabaseSettings):
        self = cls()
        self.logger.info(f"Получаем вот такие параметры подключения {db_settings}")
        database_url = URL.create(
            drivername="postgresql+asyncpg",
            username=db_settings.username,
            password=db_settings.password,
            host=db_settings.host,
            port=db_settings.port,
            database=db_settings.database,
        )
        self.logger.info(f"Вот по этой ссылке мы подключаемся {database_url}")
        self._engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
        )
        self._session = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
        )
        self.logger.info("Автоматическое создание таблиц при инициализации базы...")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.logger.info("База данных полностью готова к работе.")
        return self

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