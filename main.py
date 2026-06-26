from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    KeyboardButton,
    KeyboardButtonRequestChat,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from config import load_config, Config
from handlers import chats

import logging
import asyncio

logger = logging.getLogger(__name__)
config: Config = load_config()
logging.basicConfig(
    level=logging.getLevelName(level=config.log.level),
    format=config.log.format,
)

logger.info("Starting bot")
bot = Bot(token=config.bot.token)
dp = Dispatcher()
# bot.delete_webhook(drop_pending_updates=True)

button = KeyboardButton(
    text="Выбрать чат",
    request_chat=KeyboardButtonRequestChat(
        request_id=111,
        chat_is_channel=False,
    )
)

keyboard = ReplyKeyboardMarkup(keyboard=[[button]])
dp.include_router(chats.chats_router)


@dp.message(CommandStart())
async def start_command(message: Message):
    await message.answer("Выберете чат", reply_markup=keyboard)

@dp.message(Command(commands=['clear']))
async def clear_command(message: Message):
    await message.answer("Клавиатура убрана", reply_markup=ReplyKeyboardRemove())

@dp.message(F.chat_shared)
async def chat_check(message: Message):
    logger.info(message.model_dump_json(indent=4, exclude_none=True))

# @dp.message()
# async def text_check(message: Message):
#     logger.info(message.model_dump_json(indent=4, exclude_none=True))



if __name__ == "__main__":
    dp.run_polling(bot)


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

