import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from bot.handlers.chats import chats_router
from bot.handlers.other import other_router
from bot.handlers.user import user_router
from bot.keyboards.menu_commands import set_menu_commands
from clients import HydroClient
from config import load_config
from config.logging import config_logger
from core import AppContext
from database import PostgresStorage, RedisSessionStore
from reader import ReaderSession, reader
from schedulers.transfers import DataTransferJob

config = load_config()
config_logger(config.log)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logger.info(f"BASE_DIR: {BASE_DIR}")


async def start_app() -> AppContext:
    # Выводим в консоль информацию о начале запуска бота
    logger.info("Starting bot")

    # Инициализируем бот и диспетчер
    bot = Bot(
        token=config.bot.token,
    )
    redis = RedisSessionStore.from_settings(config.redis, db=config.redis.db)
    db = await PostgresStorage.create(config.database)
    reader_session = ReaderSession(db, redis)

    dp = Dispatcher(
        storage=RedisStorage(
            redis.client, data_ttl=config.fsm.data_ttl, state_ttl=config.fsm.state_ttl
        )
    )
    dp.include_router(chats_router)
    dp.include_router(user_router)
    await set_menu_commands(bot)
    if config.log.level in ["DEBUG", "INFO"]:
        dp.include_router(other_router)

    await bot.delete_webhook(drop_pending_updates=True)

    hy_client = await HydroClient.create(
        name="tg_reader",
        api_id=config.tg_api.api_id,
        api_hash=config.tg_api.api_hash,
        bot_token=config.bot.token,
        workdir=BASE_DIR,
    )

    transfer_job = DataTransferJob(db, redis)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        transfer_job.__call__,
        trigger="interval",
        minutes=config.transfer_job.interval_minutes,
        max_instances=config.transfer_job.scheduler_max_instances,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.add_listener(
        transfer_job.handle_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
    )

    return AppContext(
        bot=bot,
        db=db,
        dp=dp,
        hydro=hy_client,
        scheduler=scheduler,
        reader_session=reader_session,
        redis=redis,
    )


@asynccontextmanager
async def lifespan(fast_app: FastAPI):
    context = await start_app()
    fast_app.state.context = context
    fast_app.state.polling_task = asyncio.create_task(
        context.dp.start_polling(
            context.bot,
            db=context.db,
            hy_client=context.hydro,
            session_manager=context.reader_session,
            config=config,
            handle_signals=False,
        )
    )
    context.scheduler.start()
    try:
        yield
    finally:
        logger.info("Shutting down bot")
        await asyncio.gather(
            context.dp.stop_polling(),
            context.hydro.stop(),
            context.db.close(),
            context.redis.close(),
        )
        context.scheduler.shutdown()


async def main():
    app_con: AppContext = await start_app()
    hy_client: HydroClient = app_con.hydro
    dp = app_con.dp
    bot = app_con.bot
    db = app_con.db
    try:
        await dp.start_polling(bot, db=db, hy_client=hy_client)
    finally:
        await asyncio.gather(db.close(), hy_client.stop(), app_con.redis.close())


app = FastAPI(lifespan=lifespan)
app.include_router(reader)

if __name__ == "__main__":
    asyncio.run(main())
