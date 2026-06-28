from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
import logging

logging.getLogger(__name__)

chats_router = Router()

@chats_router.message(Command(commands=['info']), F.from_user, F.chat.is_forum)
async def info(message: Message):
    await message.answer("Есть пробитие")
