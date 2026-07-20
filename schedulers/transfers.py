from sqlalchemy.sql.elements import KeyedColumnElement

from database.db import Database, RedisWrapper
from database.models import Position
from apscheduler.events import JobExecutionEvent
import logging
from rich import inspect


logger = logging.getLogger(__name__)

class DataTransferJob:
    def __init__(self, db: Database, redis_wrapper: RedisWrapper) -> None:
        self._db = db
        self._redis_wrapper = redis_wrapper
        self._position_meta = DataTransferJob._get_position_meta()
        logger.info("Джоба создана")

    @staticmethod
    def _get_position_meta() -> dict[str, type]:
        return {
            column.key: column.type.python_type
            for column in Position.__table__.columns
        }

    def _convert_value(self, column_name:str, value: str):
        return self._position_meta[column_name](value)

    def prepare_items(self, raw_position: list[dict]) -> list[dict]:
        result = []
        for position in raw_position:
            _position = {}
            for col in self._position_meta.keys():
                _position[col] = self._convert_value(col, position[col])
            result.append(_position)
        return result


    async def __call__(self):
        sessions = await self._redis_wrapper.get_sessions("session:*")
        inspect(sessions)
        if len(sessions) > 0:
            _session = self.prepare_items(sessions)
            inspect(_session)
            await self._db.try_add_positions(_session)
            logger.info("Трансфер сделан")

    @staticmethod
    def handle_event(event : JobExecutionEvent):
        if event.exception:
            logger.error(f"Задача {event.job_id} упала с ошибкой {event.exception}, трейсбек: {event.traceback}")
        else:
            logger.info(f"Все ок задача {event.job_id} выполнилась!")


