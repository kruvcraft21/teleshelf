from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from config import load_config, Config
from handlers.chats import chats_router
from handlers.other import other_router
from handlers.user import user_router
from database.db import Database

from clients.hydroclient import HydroClient

from reader import reader

import logging
import asyncio

from contextlib import asynccontextmanager
from fastapi import FastAPI

from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from schedulers.transfers import DataTransferJob

logger = logging.getLogger(__name__)
config: Config = load_config()
logging.basicConfig(
    level=logging.getLevelName(level=config.log.level),
    format=config.log.format,
)

@dataclass(slots=True)
class AppContext:
    bot: Bot
    db: Database
    dp: Dispatcher
    hydro: HydroClient
    scheduler: AsyncIOScheduler

async def start_app() -> AppContext:
    # Выводим в консоль информацию о начале запуска бота
    logger.info("Starting bot")

    # Инициализируем бот и диспетчер
    bot = Bot(
        token=config.bot.token,
    )
    db = await Database.create(config.database, config.redis)
    dp = Dispatcher(storage=RedisStorage(db.get_redis_poll(), data_ttl=1800, state_ttl=1800))
    dp.include_router(chats_router)
    dp.include_router(user_router)
    if config.log.level in ["DEBUG", "INFO"]:
        dp.include_router(other_router)

    await bot.delete_webhook(drop_pending_updates=True)

    hy_client = await HydroClient.start(name="tg_reader",api_id=config.tg_api.api_id, api_hash=config.tg_api.api_hash, bot_token=config.bot.token)

    transfer_job = DataTransferJob(db, db.get_redis_wrap())
    scheduler = AsyncIOScheduler()
    scheduler.add_job(transfer_job.__call__, trigger="interval", minutes=1, max_instances=1)
    scheduler.add_listener(transfer_job.handle_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    return AppContext(bot=bot, db=db, dp=dp, hydro=hy_client, scheduler=scheduler)

async def stop_app(client: HydroClient, db: Database):
    await client.stop()
    await db.close()


@asynccontextmanager
async def lifespan(fast_app: FastAPI):
    app_context = await start_app()
    hy_client = app_context.hydro
    dp = app_context.dp
    db = app_context.db
    bot = app_context.bot
    fast_app.state.bot = hy_client
    fast_app.state.db = db
    fast_app.state.polling_task = asyncio.create_task(dp.start_polling(bot, db=db, hy_client=hy_client, handle_signals=False))
    app_context.scheduler.start()
    yield
    logger.info("Shutting down bot")
    await hy_client.stop()
    await db.close()
    app_context.scheduler.shutdown()

async def main():
    app_con: AppContext = await start_app()
    hy_client: HydroClient = app_con.hydro
    dp = app_con.dp
    bot = app_con.bot
    db = app_con.db
    try:
        await dp.start_polling(bot, db=db, hy_client=hy_client)
    finally:
        await db.close()
        await hy_client.stop()

app = FastAPI(lifespan=lifespan)
app.include_router(reader)

if __name__ == "__main__":
    asyncio.run(main())

