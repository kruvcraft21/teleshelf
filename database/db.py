import logging
from typing import Any

from config import PGDatabseSettings, RedisSettings

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy import URL, select
from sqlalchemy.dialects.postgresql import insert

from database.models import Base, UserChats, Topic, File, Position

from database.redis_wrapper import RedisWrapper, Redis


class Database:
    def __init__(self, engin : AsyncEngine, session_maker : async_sessionmaker[AsyncSession | Any], logger: logging.Logger, redis : RedisWrapper):
        self._engine = engin
        self._session = session_maker
        self.logger = logger
        self._redis_wrap = redis

    @classmethod
    async def create(cls, db_settings: PGDatabseSettings, redis_settings: RedisSettings):
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
        redis = await RedisWrapper.get_redis_client(redis_settings)
        self = cls(_engine, session_maker=_session, logger=logger, redis=redis)
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

    async def try_add_file(self, file_id: str, topic_id: int, caption: str | None, file_type: str) -> None:
        async with self._session.begin() as session:
            stmt = select(File.id).where(File.topic_id == topic_id,
                                         File.tg_file_id == file_id)
            file = await session.scalar(stmt)
            if file is None:
                new_file = File(topic_id=topic_id, caption=caption, tg_file_id=file_id, positions=[], file_type=file_type)
                session.add(new_file)

    async def get_chats(self, user_id: int) -> dict[str, int]:
        result = {}
        async with self._session() as session:
            user_chats = await session.scalars(select(UserChats.chat_id).where(UserChats.user_id == user_id))
            iter_topic = await session.execute(select(Topic.id, Topic.title).where(Topic.chat_id.in_(user_chats)))
            for topic in iter_topic.all():
                result[topic.title] = topic.id
        return result

    async def get_files(self, topic_id: int, user_id : int) -> dict[str, int]:
        result = {}
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
            for file_id, file_caption, page in rows:
                caption = file_caption or "None"
                redis_page = await self._redis_wrap.get_page_by_file(user_id, file_id)
                now_page = redis_page or page
                if now_page is not None:
                    caption = f"{now_page} - {caption}"
                result[caption] = file_id
        return result

    async def get_topic_title(self, topic_id: int) -> str:
        result = ""
        async with self._session() as session:
            topic = await session.get(Topic, topic_id)
            if topic is not None:
                result = str(topic.title)
        return result

    async def get_file_tg_id(self, session_id: str) -> str:
        return await self._redis_wrap.get_tg_file_id(session_id)

    async def create_session(self, file_id: int, user_id: int) -> str :
        result = ""
        async with self._session.begin() as session:
            position = await session.scalar(select(Position).where(Position.user_id == user_id,
                                                                   Position.file_id == file_id))
            tg_file_id = await session.scalar(select(File.tg_file_id).where(File.id == file_id))
            if tg_file_id is not None:
                if position is None:
                    position = Position(user_id=user_id, file_id=file_id, page=0)
                    session.add(position)
                result = await self._redis_wrap.try_create_session(position, tg_file_id=tg_file_id)
        return result

    async def get_page(self, session_id: str) -> int:
        if len(session_id) > 0:
            return await self._redis_wrap.get_page_from_session(session_id)
        return 0

    async def update_page(self, session_id: str, page: int) -> None:
        if len(session_id) > 0:
            await self._redis_wrap.update_page(session_id, page)

    def get_redis_poll(self) -> Redis:
        return self._redis_wrap.get_poll()

    def get_redis_wrap(self) -> RedisWrapper:
        return self._redis_wrap

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
        await self._redis_wrap.close()

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