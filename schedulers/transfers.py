import logging

from apscheduler.events import JobExecutionEvent

from database import PostgresStorage, RedisSessionStore
from database.models import Position

logger = logging.getLogger(__name__)


class DataTransferJob:
    def __init__(self, db: PostgresStorage, redis_wrapper: RedisSessionStore) -> None:
        self._db = db
        self._redis_wrapper = redis_wrapper
        self._position_meta = DataTransferJob._get_position_meta()
        logger.info("Джоба создана")

    @staticmethod
    def _get_position_meta() -> dict[str, type]:
        return {
            column.key: column.type.python_type for column in Position.__table__.columns
        }

    def _convert_value(self, column_name: str, value: str):
        return self._position_meta[column_name](value)

    def prepare_items(self, raw_position: list[dict]) -> list[dict]:
        result = []
        for position in raw_position:
            _position = {}
            for col in self._position_meta:
                _position[col] = self._convert_value(col, position[col])
            result.append(_position)
        return result

    async def __call__(self):
        sessions = await self._redis_wrapper.list_sessions()
        if len(sessions) > 0:
            _session = self.prepare_items(sessions)
            logger.debug(_session)
            await self._db.try_add_positions(_session)
            logger.debug("Трансфер сделан")

    @staticmethod
    def handle_event(event: JobExecutionEvent):
        if event.exception:
            logger.error(
                f"Задача {event.job_id} упала с ошибкой {event.exception}, трейсбек: {event.traceback}"
            )
        else:
            logger.info(f"Все ок задача {event.job_id} выполнилась!")
