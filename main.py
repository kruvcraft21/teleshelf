from aiogram import Bot, Dispatcher

from config import load_config, Config
from handlers.chats import chats_router
from database.db import Database

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

    # Инициализируем "базу данных"
    db = await Database.create(config.database)

    # Сохраняем готовую книгу и "базу данных" в \`workflow_data\`
    dp.workflow_data.update(db=db)

    # Регистрируем роутеры в диспетчере
    dp.include_router(chats_router)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


# async def main():
#     # Загружаем конфиг в переменную config
#     config: Config = load_config()
#
#     # Задаём базовую конфигурацию логирования
#     logging.basicConfig(
#         level=logging.getLevelName(level=config.log.level),
#         format=config.log.format,
#     )
#     # Выводим в консоль информацию о начале запуска бота
#     logger.info("Starting bot")
#
#     # Инициализируем бот и диспетчер
#     bot = Bot(
#         token=config.bot.token,
#     )
#     dp = Dispatcher()
#
#     # Пропускаем накопившиеся апдейты и запускаем polling
#     await bot.delete_webhook(drop_pending_updates=True)
#     await dp.start_polling(bot)
#
# if __name__ == "__main__":
#     asyncio.run(main())

