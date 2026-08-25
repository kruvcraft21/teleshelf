import asyncio

from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
import logging

from database.postgres import PostgresStorage
from clients.hydroclient import HydroClient

logger = logging.getLogger(__name__)

chats_router = Router()

@chats_router.message(Command('info'), F.from_user, F.chat.is_forum)
async def info(message: Message):
    await message.answer("Есть пробитие")
    logger.info(message.model_dump_json(indent=4, exclude_none=True))

@chats_router.message(Command("update"), F.from_user, F.chat.is_forum)
async def update_documents(message: Message, db: PostgresStorage, hy_client: HydroClient):
    topics = await hy_client.fetch_chat_content(chat_id=message.chat.id, message_id=message.message_id)
    topic_cors = [db.try_add_chat(message.chat.id, topic.topic_id, topic.topic_title) for topic in topics]
    topic_ids = await asyncio.gather(*topic_cors)
    values = []
    expected_files: dict[int, list[int]] = {}

    for topic_id, topic in zip(topic_ids, topics):
        expected_files[topic_id] = []
        for file in topic.files:
            values.append({
                "topic_id": topic_id,
                "tg_message_id": file.message_id,
                "caption": file.file_caption,
                "file_type": file.file_type,
            })

            expected_files[topic_id].append(file.message_id)

    await db.update_chat_files(message.chat.id, topic_ids, values, expected_files)

    members = await hy_client.fetch_chat_members(chat_id=message.chat.id)
    await db.update_chat_members(message.chat.id, members)

    await message.answer("Вроде бы обновил коллекцию")

@chats_router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_leave(event: ChatMemberUpdated):
    pass

@chats_router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated):
    pass
