from redis.asyncio import Redis

from config import RedisSettings
from database.models import Position
import uuid
import logging

logger = logging.getLogger(__name__)

class RedisWrapper:
    def __init__(self, poll: Redis) -> None:
        self._poll = poll

    @classmethod
    async def get_redis_client(cls, redis_config: RedisSettings, db : int = 0):
        r = Redis(host=redis_config.host, port=redis_config.port, decode_responses=True, max_connections=10, db=db)
        self = cls(r)
        return self

    def get_poll(self) -> Redis:
        return self._poll

    async def try_create_session(self, position: Position, tg_file_id: str) -> str:
        session_id = await self._poll.get(f"index:{position.user_id}:{position.file_id}")
        logger.info(f"Получил объект типа {type(session_id)} {session_id}")
        if (session_id is None) or (not isinstance(session_id, str)):
            session_id = f"session:{uuid.uuid4()}"
            async with self._poll.pipeline(transaction=True) as pipe:
                pipe.set(f"index:{position.user_id}:{position.file_id}", session_id)
                pipe.hset(session_id, mapping={"user_id": position.user_id,
                                                      "file_id": position.file_id,
                                                      "page": position.page,
                                                      "tg_file_id": tg_file_id
                                                      })
                results = await pipe.execute()
        await self._poll.expire(session_id, 3600)
        await self._poll.expire(f"index:{position.user_id}:{position.file_id}", 3600)
        return session_id

    async def get_page(self, session_id: str) -> int:
        page = await self._poll.hget(session_id, "page")
        if page is None:
            logger.warning(f"Не удалось получить position_id для session_id: {session_id}")
            return 0
        return int(page)

    async def get_tg_file_id(self, session_id: str) -> str:
        tg_file_id = await self._poll.hget(session_id, "tg_file_id")
        return str(tg_file_id) if tg_file_id is not None else ""

    async def update_page(self, session_id: str, page: int) -> None:
        code = await self._poll.hset(session_id, "page", page)
        logger.info(f"Обновление записи {code}")
        await self._poll.expire(session_id, 3600)

    async def get_sessions(self, template: str):
        keys = await self._poll.keys(template)
        async with self._poll.pipeline(transaction=False) as pipe:
            for key in keys:
                pipe.hgetall(key)
            results = await pipe.execute()
        return results

    async def close(self):
        await self._poll.aclose()