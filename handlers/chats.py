from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
import logging

from database.db import Database

logging.getLogger(__name__)

chats_router = Router()

@chats_router.message(Command(commands=['info']), F.from_user, F.chat.is_forum)
async def info(message: Message):
    await message.answer("Есть пробитие")

@chats_router.message(F.from_user, F.message_thread_id, F.document)
async def put_documents(message: Message, db: Database):
    await db.try_add_user(user_id=message.from_user.id, chat_id=message.chat.id)
    chat_id = await db.try_add_chat(chat_id=message.chat.id, topic_id=message.message_thread_id, topic_title=message.chat.title)
    caption_file = message.caption if message.caption else message.document.file_name
    await db.try_add_file(message.document.file_id, topic_id=chat_id, caption=caption_file)

