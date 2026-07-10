from aiogram import Bot, Dispatcher

from config import load_config, Config
from handlers.chats import chats_router
from handlers.other import other_router
from handlers.user import user_router
from database.db import Database

from hydrogram import Client

from reader import reader
import uvicorn

import logging
import asyncio

logger = logging.getLogger(__name__)

async def main():
    # Загружаем конфиг в переменную config
    config: Config = load_config()

    # Задаём базовую конфигурацию логирования
    logging.basicConfig(
        level=logging.getLevelName(level=config.log.level),
        format=config.log.format,
    )
    # Выводим в консоль информацию о начале запуска бота
    logger.info("Starting bot")

    # Инициализируем бот и диспетчер
    bot = Bot(
        token=config.bot.token,
    )
    dp = Dispatcher()
    hy_client = Client("tg_reader",api_id=config.tg_api.api_id, api_hash=config.tg_api.api_hash, bot_token=config.bot.token)
    reader.state.bot = hy_client

    # Инициализируем "базу данных"
    db = await Database.create(config.database)
    # Регистрируем роутеры в диспетчере
    dp.include_router(chats_router)
    dp.include_router(user_router)

    if config.log.level in ["DEBUG", "INFO"]:
        dp.include_router(other_router)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)

    uvicorn_config = uvicorn.Config(host="127.0.0.1", port=8000, log_level="info", workers=4, app=reader)
    uvicorn_server = uvicorn.Server(uvicorn_config)

    try:
        await hy_client.start()
        await asyncio.gather(uvicorn_server.serve(),
                             dp.start_polling(bot, db=db, hy_client=hy_client))

    finally:
        await hy_client.stop()

if __name__ == "__main__":
    asyncio.run(main())

