from dataclasses import dataclass
import asyncio

from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated, MessageReactionUpdated
from hydrogram.types import Message as hy_Message
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER, CommandStart
import logging
from mimetypes import guess_type

from database.postgres import PostgresStorage
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

async def try_add_document(document: DocumentInfo, db : PostgresStorage):
    logger.info("По возможности добавляем пользователя в базу данных")
    await db.try_add_user(user_id=document.user_id, chat_id=document.chat_id)
    logger.info("По возможности добавляем чат в базу данных")
    chat_id = await db.try_add_chat(chat_id=document.chat_id, topic_id=document.thread_id,
                                    topic_title=document.topic_title)
    logger.info("Получаем название файла и по возможности добавляем его в базу данных")
    await db.try_add_file(document.file_id, topic_id=chat_id,
                          caption=document.file_name, file_type=document.file_type)

@chats_router.message(Command('info'), F.from_user, F.chat.is_forum)
async def info(message: Message):
    await message.answer("Есть пробитие")
    logger.info(message.model_dump_json(indent=4, exclude_none=True))

@chats_router.message(F.from_user, F.message_thread_id, F.document)
async def put_documents(message: Message, db: PostgresStorage):
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

@chats_router.message_reaction(is_document, F.chat.is_forum)
async def react_message(message_reaction: MessageReactionUpdated, message: hy_Message, db: PostgresStorage):
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

@chats_router.message(Command("update"), F.from_user, F.chat.is_forum)
async def update_documents(message: Message, db: PostgresStorage, hy_client: HydroClient):
    topics = await hy_client.fetch_chat_content(chat_id=message.chat.id, message_id=message.message_id)
    topic_cors = [db.try_add_chat(message.chat.id, topic.topic_id, topic.topic_title) for topic in topics]
    topic_ids = await asyncio.gather(*topic_cors)
    values = []
    expected_files: dict[int, list[str]] = {}

    for topic_id, topic in zip(topic_ids, topics):
        expected_files[topic_id] = []
        for file in topic.files:
            values.append({
                "topic_id": topic_id,
                "tg_file_id": file.file_id,
                "caption": file.file_caption,
                "file_type": file.file_type,
            })

            expected_files[topic_id].append(file.file_id)

    await db.update_chat_status(message.chat.id, topic_ids, values, expected_files)
    await message.answer("Вроде бы обновил коллекцию")

@chats_router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_leave(event: ChatMemberUpdated):
    pass

@chats_router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated):
    pass
