from redis.asyncio import Redis

from config.models import RedisSettings
from .models import Position
import uuid
import logging

logger = logging.getLogger(__name__)


class RedisSessionStore:
    SESSION_TTL = 60 * 60

    def __init__(self, redis_client: Redis):
        self._redis = redis_client

    @classmethod
    def from_settings(cls, settings: RedisSettings, db: int = 0) -> "RedisSessionStore":
        redis_client = Redis(
            host=settings.host,
            port=settings.port,
            decode_responses=True,
            max_connections=10,
            db=db
        )
        return cls(redis_client)

    @property
    def client(self) -> Redis:
        return self._redis

    async def close(self):
        await self._redis.aclose()

    async def get_or_create(self, position: Position, tg_file_id: str) -> str:
        new_session_id = f"session:{uuid.uuid4()}"
        point_session = f"index:{position.user_id}:{position.file_id}"

        old_session_id = await self._redis.set(
            name=point_session,
            value=new_session_id,
            nx=True,
            ex=self.SESSION_TTL,
            get=True
        )

        if isinstance(old_session_id, str):
            logger.info(f"Сессия уже существует: {old_session_id}")
            await self._redis.expire(old_session_id, self.SESSION_TTL)
            await self._redis.expire(point_session, self.SESSION_TTL)
            return old_session_id

        logger.info(f"Создана новая сессия: {new_session_id}")

        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.hset(new_session_id,
                      mapping={"user_id": position.user_id,
                               "file_id": position.file_id,
                               "page": position.page,
                               "tg_file_id": tg_file_id
                               }
                      )
            pipe.expire(new_session_id, self.SESSION_TTL)
            await pipe.execute()
        return new_session_id

    async def get_page(self, session_id: str) -> int:
        page = await self._redis.hget(session_id, "page")
        if page is None:
            logger.warning(f"Не удалось получить position_id для session_id: {session_id}")
            return 0
        return int(page)

    async def get_page_by_file(self, user_id: int, file_id: int) -> int:
        session_id = await self._redis.get(f"index:{user_id}:{file_id}")
        if not isinstance(session_id, str):
            logger.warning(f"Не удалось получить session для {user_id}:{file_id}")
            return 0
        return await self.get_page(session_id)

    async def get_tg_file_id(self, session_id: str) -> str:
        tg_file_id = await self._redis.hget(session_id, "tg_file_id")
        return str(tg_file_id) if tg_file_id is not None else ""

    async def update_page(self, session_id: str, page: int) -> None:
        session = await self._redis.hmget(session_id, "user_id", "file_id")
        user_id, file_id = session
        if user_id is None or file_id is None:
            logger.warning(f"Не удалось обновить указатель для session_id: {session_id}")
            return

        point_session = f"index:{user_id}:{file_id}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.hset(session_id, "page", page)
            pipe.expire(session_id, self.SESSION_TTL)
            pipe.expire(point_session, self.SESSION_TTL)
            result = await pipe.execute()
        logger.info(f"Обновление записи {result[0]}")

    async def list_sessions(self) -> list[dict]:
        results = []
        async with self._redis.pipeline(transaction=False) as pipe:
            async for key in self._redis.scan_iter(match="session:*"):
                pipe.hgetall(key)
            results = await pipe.execute()
        return results
