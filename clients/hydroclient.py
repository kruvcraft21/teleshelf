from dataclasses import dataclass, field
from functools import wraps

from hydrogram import Client
from hydrogram.types import Message

BATCH_SIZE = 100

@dataclass
class File:
    message_id: int
    file_caption: str
    file_type : str

@dataclass
class Topic:
    topic_id: int
    topic_title: str
    files: list[File] = field(default_factory=list)

class HydroClient(Client):
    @classmethod
    @wraps(Client.__init__)
    async def create(cls, **kwargs) -> "HydroClient":
        client = cls(**kwargs)
        await client.start()
        return client

    async def fetch_chat_content(self, chat_id, message_id : int) -> list[Topic]:
        all_ids = list(range(1, message_id + 1))
        batches = [all_ids[i:i + BATCH_SIZE] for i in range(0, len(all_ids), BATCH_SIZE)]
        all_messages : list [Message] = []
        for batch in batches:
            messages = await self.get_messages(chat_id, batch)
            if isinstance(messages, list):
                all_messages.extend(messages)
        return self._group_messages_by_topic(all_messages)

    async def fetch_chat_members(self, chat_id : int) -> list[dict[str, int]]:
        members = []
        # pyrefly: ignore [not-iterable]
        async for member in self.get_chat_members(chat_id):
            if member.user and not member.user.is_bot:
                members.append({"user_id": member.user.id, "chat_id": chat_id})
        return members

    @staticmethod
    def _group_messages_by_topic(messages: list[Message]) -> list[Topic]:
        topics: dict[int, Topic] = {}

        for message in messages:
            if not message.document or not message.topics:
                continue

            topic_id = message.topics.id
            topic = topics.setdefault(
                topic_id,
                Topic(topic_id=topic_id,
                      topic_title=message.topics.title)
            )

            topic.files.append(File(
                message_id=message.id,
                file_caption=message.caption or message.document.file_name or 'No caption',
                file_type=message.document.mime_type or 'unknown',
            ))

        return list(topics.values())
