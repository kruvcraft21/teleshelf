from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from clients import HydroClient
from database import PostgresStorage, RedisSessionStore
from reader.session import ReaderSession

@dataclass(slots=True)
class AppContext:
    bot: Bot
    db: PostgresStorage
    dp: Dispatcher
    hydro: HydroClient
    scheduler: AsyncIOScheduler
    reader_session: ReaderSession
    redis: RedisSessionStore