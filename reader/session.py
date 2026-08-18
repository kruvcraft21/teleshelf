from database import RedisSessionStore, PostgresStorage

class ReaderSession:
    def __init__(self, postgres: PostgresStorage, redis: RedisSessionStore):
        self._postgres = postgres
        self._redis = redis

    async def create(self, file_id: int, user_id: int) -> str:
        position, tg_file_id = await self._postgres.get_or_create_position(file_id, user_id)

        if position is None:
            return ""

        return await self._redis.get_or_create(position, tg_file_id)

    async def get_files(self, topic_id: int, user_id: int) -> dict[str, int]:
        files = await self._postgres.get_files(topic_id, user_id)
        result = {}
        for file in files:
            redis_page = await self._redis.get_page_by_file(user_id, file.file_id)
            caption = file.caption
            if redis_page > file.page:
                caption = f"{redis_page} - {caption}"
            elif redis_page < file.page:
                caption = f"{file.page} - {caption}"
            result[caption] = file.file_id
        return result