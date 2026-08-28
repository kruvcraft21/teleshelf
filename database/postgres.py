import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import URL, delete, select, values
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.models import PGDatabseSettings
from database.models import Base, File, Position, Topic, UserChats


@dataclass
class FileInfo:
    file_id: int
    caption: str
    page: int


class PostgresStorage:
    def __init__(
        self,
        engin: AsyncEngine,
        session_maker: async_sessionmaker[AsyncSession | Any],
        logger: logging.Logger,
    ):
        self._engine = engin
        self._session = session_maker
        self.logger = logger

    @classmethod
    async def create(cls, db_settings: PGDatabseSettings):
        # self = cls()
        logger = logging.getLogger(__name__)
        logger.info("Пытаемся подключится")
        database_url = URL.create(
            drivername="postgresql+asyncpg",
            username=db_settings.username,
            password=db_settings.password,
            host=db_settings.host,
            port=db_settings.port,
            database=db_settings.database,
        )
        logger.info("Вроде бы получили ссылку")
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
            chat: Any = await session.scalar(
                select(Topic)
                .where(Topic.chat_id == chat_id)
                .where(Topic.topic_id == topic_id)
            )
            if chat is None:
                chat = Topic(
                    chat_id=chat_id, topic_id=topic_id, files=[], title=topic_title
                )
                session.add(chat)

            if chat.title != topic_title:
                chat.title = topic_title

        return chat.id

    @staticmethod
    async def _upsert_files(files: list[dict], session: AsyncSession) -> None:
        if not files:
            return
        stmt = insert(File).values(files)
        stmt = stmt.on_conflict_do_update(
            index_elements=[File.topic_id, File.tg_message_id],
            set_={
                "caption": stmt.excluded.caption,
                "file_type": stmt.excluded.file_type,
            },
        )
        await session.execute(stmt)

    @staticmethod
    async def _delete_missing_files(expected_files, session: AsyncSession) -> None:
        for topic_id, file_ids in expected_files.items():
            await session.execute(
                delete(File).where(
                    File.topic_id == topic_id, File.tg_message_id.notin_(file_ids)
                )
            )

    @staticmethod
    async def _delete_topics(
        chat_id: int, topic_ids: list[int], session: AsyncSession
    ) -> None:
        await session.execute(
            delete(Topic).where(Topic.id.notin_(topic_ids), Topic.chat_id == chat_id)
        )

    async def update_chat_files(
        self,
        chat_id: int,
        topic_ids: list[int],
        files: list[dict],
        expected_files: dict[int, list[int]],
    ) -> None:
        async with self._session.begin() as session:
            await self._upsert_files(files, session)
            await self._delete_topics(chat_id, topic_ids, session)
            await self._delete_missing_files(expected_files, session)

    @staticmethod
    async def _upsert_chat_members(
        members: list[dict[str, int]], session: AsyncSession
    ) -> None:
        if not members:
            return
        stmt = insert(UserChats).values(members)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=[UserChats.user_id, UserChats.chat_id]
        )
        await session.execute(stmt)

    @staticmethod
    async def _delete_chat_members(
        members: list[dict[str, int]], chat_id: int, session: AsyncSession
    ) -> None:
        user_ids = [member["user_id"] for member in members]
        if user_ids:
            stmt = (
                delete(UserChats)
                .where(UserChats.chat_id == chat_id)
                .where(UserChats.user_id.notin_(user_ids))
            )
            await session.execute(stmt)

    async def update_chat_members(
        self, chat_id: int, members: list[dict[str, int]]
    ) -> None:
        async with self._session.begin() as session:
            await self._upsert_chat_members(members, session)
            await self._delete_chat_members(members, chat_id, session)

    async def get_chats(self, user_id: int) -> dict[str, int]:
        result = {}
        async with self._session() as session:
            user_chats = await session.scalars(
                select(UserChats.chat_id).where(UserChats.user_id == user_id)
            )
            iter_topic = await session.execute(
                select(Topic.id, Topic.title).where(Topic.chat_id.in_(user_chats))
            )
            for topic in iter_topic.all():
                result[topic.title] = topic.id
        return result

    async def get_files(self, topic_id: int, user_id: int) -> list[FileInfo]:
        async with self._session() as session:
            stmt = (
                select(File.id, File.caption, Position.page)
                .outerjoin(
                    Position,
                    (Position.file_id == File.id) & (Position.user_id == user_id),
                )
                .where(File.topic_id == topic_id)
                .order_by(File.id)
            )
            rows = await session.execute(stmt)
            return [
                FileInfo(
                    file_id=file_id, caption=file_caption or "None", page=page or 0
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

    async def get_or_create_position(
        self, file_id: int, user_id: int
    ) -> tuple[Position | None, int, int]:
        async with self._session.begin() as session:
            position = await session.scalar(
                select(Position).where(
                    Position.user_id == user_id, Position.file_id == file_id
                )
            )
            stmt = (
                select(Topic.chat_id, File.tg_message_id)
                .join(File, File.topic_id == Topic.id)
                .where(File.id == file_id)
            )
            chat_id, message_id = (await session.execute(stmt)).one()

            if position is None:
                position = Position(user_id=user_id, file_id=file_id, page=0)
                session.add(position)

            return position, chat_id, message_id

    async def try_add_positions(self, positions: list[dict]):
        positions_columns = tuple(Position.__table__.columns)
        redis_positions = (
            values(
                *positions_columns
            )
            .data(
                [
                    (position["user_id"], position["file_id"], position["page"])
                    for position in positions
                ]
            )
            .alias("redis_positions")
        )
        exist_file_positions = (
            select(redis_positions).join(File, File.id == redis_positions.c.file_id)
        )
        stmt = insert(Position).from_select(positions_columns, exist_file_positions)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Position.user_id, Position.file_id],
            set_={
                "page": stmt.excluded.page,
            },
        )
        async with self._session.begin() as session:
            await session.execute(stmt)

    async def close(self):
        await self._engine.dispose()


if __name__ == "__main__":
    import asyncio

    from config import load_config

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
        await PostgresStorage.create(config.database)

    asyncio.run(main())
