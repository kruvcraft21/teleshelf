from database import PostgresStorage, RedisSessionStore


class ReaderSession:
    def __init__(self, postgres: PostgresStorage, redis: RedisSessionStore):
        self._postgres = postgres
        self._redis = redis

    async def create(self, file_id: int, user_id: int) -> str:
        position, chat_id, message_id = await self._postgres.get_or_create_position(
            file_id, user_id
        )

        if position is None:
            return ""

        return await self._redis.get_or_create(position, chat_id, message_id)

    async def get_files(self, topic_id: int, user_id: int) -> dict[str, int]:
        files = await self._postgres.get_files(topic_id, user_id)
        result = {}
        for file in files:
            redis_page = await self._redis.get_page_by_file(user_id, file.file_id)
            caption = f"стр. {file.page} - {file.caption}"
            if redis_page > file.page:
                caption = f"стр. {redis_page} - {file.caption}"
            result[caption] = file.file_id
        return result
