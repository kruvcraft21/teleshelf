from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import passport_data

from config import load_config, Config
from handlers.chats import chats_router
from handlers.other import other_router
from handlers.user import user_router
from database.db import Database

from clients.hydroclient import HydroClient

from reader import reader
import uvicorn

import logging
import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)
config: Config = load_config()
logging.basicConfig(
    level=logging.getLevelName(level=config.log.level),
    format=config.log.format,
)

async def start_app():
    # Выводим в консоль информацию о начале запуска бота
    logger.info("Starting bot")

    # Инициализируем бот и диспетчер
    bot = Bot(
        token=config.bot.token,
    )
    db = await Database.create(config.database, config.redis)
    dp = Dispatcher(storage=RedisStorage(db.get_redis_poll(), data_ttl=300, state_ttl=300))
    dp.include_router(chats_router)
    dp.include_router(user_router)
    if config.log.level in ["DEBUG", "INFO"]:
        dp.include_router(other_router)

    await bot.delete_webhook(drop_pending_updates=True)

    hy_client = await HydroClient.start(name="tg_reader",api_id=config.tg_api.api_id, api_hash=config.tg_api.api_hash, bot_token=config.bot.token)

    return hy_client, db, bot, dp

async def stop_app(client: HydroClient, db: Database):
    await client.stop()
    await db.close()


@asynccontextmanager
async def lifespan(fast_app: FastAPI):
    hy_client, db, bot, dp = await start_app()
    fast_app.state.bot = hy_client
    fast_app.state.db = db
    fast_app.state.polling_task = asyncio.create_task(dp.start_polling(bot, db=db, hy_client=hy_client, handle_signals=False))
    yield
    logger.info("Shutting down bot")
    await hy_client.stop()
    await db.close()

async def main():
    hy_client, db, bot, dp = await start_app()
    try:
        await dp.start_polling(bot, db=db, hy_client=hy_client)
    finally:
        await db.close()
        await hy_client.stop()

app = FastAPI(lifespan=lifespan)
app.include_router(reader)

if __name__ == "__main__":
    asyncio.run(main())

