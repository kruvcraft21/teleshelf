from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
import logging
from mimetypes import guess_type

from database.db import Database

logging.getLogger(__name__)

chats_router = Router()

@chats_router.message(Command(commands=['info']), F.from_user, F.chat.is_forum)
async def info(message: Message):
    await message.answer("Есть пробитие")

@chats_router.message(F.from_user, F.message_thread_id, F.document)
async def put_documents(message: Message, db: Database):
    logging.info("По возможности добавляем пользователя в базу данных")
    await db.try_add_user(user_id=message.from_user.id, chat_id=message.chat.id)
    logging.info("По возможности добавляем чат в базу данных")
    topic_title = message.reply_to_message.forum_topic_created.name
    chat_id = await db.try_add_chat(chat_id=message.chat.id, topic_id=message.message_thread_id, topic_title=topic_title)
    logging.info("Получаем название файла и по возможности добавляем его в базу данных")
    caption_file = message.caption if message.caption else message.document.file_name
    file_type = guess_type(message.document.file_name)[0]
    await db.try_add_file(message.document.file_id, topic_id=chat_id, caption=caption_file, file_type=file_type)


