from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from config import load_config, Config

from handlers.chats import chats_router
from handlers.other import other_router
from handlers.user import user_router
from database import PostgresStorage, RedisSessionStore

from clients import HydroClient

from reader import ReaderSession
from reader.api import reader
from core import AppContext

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


async def start_app() -> AppContext:
    # Выводим в консоль информацию о начале запуска бота
    logger.info("Starting bot")

    # Инициализируем бот и диспетчер
    bot = Bot(
        token=config.bot.token,
    )
    redis = RedisSessionStore.from_settings(config.redis)
    db = await PostgresStorage.create(config.database)
    reader_session = ReaderSession(db, redis)

    dp = Dispatcher(storage=RedisStorage(redis.client, data_ttl=1800, state_ttl=1800))
    dp.include_router(chats_router)
    dp.include_router(user_router)
    if config.log.level in ["DEBUG", "INFO"]:
        dp.include_router(other_router)

    await bot.delete_webhook(drop_pending_updates=True)

    hy_client = await HydroClient.create(name="tg_reader", api_id=config.tg_api.api_id, api_hash=config.tg_api.api_hash,
                                         bot_token=config.bot.token)

    transfer_job = DataTransferJob(db, redis)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(transfer_job.__call__, trigger="interval", minutes=30, max_instances=1)
    scheduler.add_listener(transfer_job.handle_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    return AppContext(
        bot=bot,
        db=db,
        dp=dp,
        hydro=hy_client,
        scheduler=scheduler,
        reader_session=reader_session,
        redis=redis,
    )


async def stop_app(client: HydroClient, db: PostgresStorage):
    await client.stop()
    await db.close()


@asynccontextmanager
async def lifespan(fast_app: FastAPI):
    context = await start_app()
    fast_app.state.context = context
    fast_app.state.polling_task = asyncio.create_task(context.dp.start_polling(
        context.bot,
        db=context.db,
        hy_client=context.hydro,
        session_manager=context.reader_session,
        handle_signals=False
    ))
    context.scheduler.start()
    try:
        yield
    finally:
        logger.info("Shutting down bot")
        await asyncio.gather(
            context.dp.stop_polling(),
            context.hydro.stop(),
            context.db.close()
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
        await db.close()
        await hy_client.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(reader)

if __name__ == "__main__":
    asyncio.run(main())
