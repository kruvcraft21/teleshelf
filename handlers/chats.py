from dataclasses import dataclass

from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from hydrogram.types import Message as hy_Message
import logging
from mimetypes import guess_type

from database.db import Database
from clients.hydroclient import HydroClient

logger = logging.getLogger(__name__)

chats_router = Router()

@dataclass
class DocumentInfo:
    user_id : int
    chat_id : int
    topic_title : str
    thread_id : int
    file_id : str
    file_name : str
    file_type: str

async def try_add_document(document: DocumentInfo, db : Database):
    logger.info("По возможности добавляем пользователя в базу данных")
    await db.try_add_user(user_id=document.user_id, chat_id=document.chat_id)
    logger.info("По возможности добавляем чат в базу данных")
    chat_id = await db.try_add_chat(chat_id=document.chat_id, topic_id=document.thread_id,
                                    topic_title=document.topic_title)
    logger.info("Получаем название файла и по возможности добавляем его в базу данных")
    await db.try_add_file(document.file_id, topic_id=chat_id,
                          caption=document.file_name, file_type=document.file_type)

@chats_router.message(Command(commands=['info']), F.from_user, F.chat.is_forum)
async def info(message: Message):
    await message.answer("Есть пробитие")

@chats_router.message(F.from_user, F.message_thread_id, F.document)
async def put_documents(message: Message, db: Database):
    document = DocumentInfo(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        topic_title=message.reply_to_message.forum_topic_created.name,
        thread_id=message.message_thread_id,
        file_id=message.document.file_id,
        file_name=message.caption if message.caption else message.document.file_name,
        file_type=guess_type(message.document.file_name)[0],
    )
    await try_add_document(document=document, db=db)

async def is_document(message_reaction: MessageReactionUpdated, hy_client: HydroClient) -> bool | dict[str, hy_Message]:
    chat_id = message_reaction.chat.id
    message_id = message_reaction.message_id
    message = await hy_client.get_messages(chat_id=chat_id, message_ids=message_id)
    message = message[0] if isinstance(message, list) else message
    return {'message': message} if message.document is not None else False

@chats_router.message_reaction(is_document)
async def react_message(message_reaction: MessageReactionUpdated, message: hy_Message, db: Database):
    if len(message_reaction.new_reaction) == 0:
        return
    document = DocumentInfo(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        topic_title=message.topics.title,
        thread_id=message.message_thread_id,
        file_id=message.document.file_id,
        file_name=message.caption if message.caption else message.document.file_name,
        file_type=message.document.mime_type,
    )
    await try_add_document(document=document, db=db)

