from hydrogram import Client
from hydrogram.types import Message
from dataclasses import dataclass, field

BATCH_SIZE = 100

@dataclass
class File:
    file_id: str
    file_caption: str
    file_type : str

@dataclass
class Topics:
    topic_id: int
    topic_title: str
    files: list[File] = field(default_factory=list)

class HydroClient(Client):
    @classmethod
    async def start(cls, **kwargs):
        self = HydroClient(**kwargs)
        await super(HydroClient, self).start()
        return self

    async def fetch_chat_content(self, chat_id, message_id) -> list[Topics]:
        result = {}
        all_ids = list(range(1, message_id + 1))
        batches = [all_ids[i:i + BATCH_SIZE] for i in range(0, len(all_ids), BATCH_SIZE)]
        for batch in batches:
            messages : list[Message]= await self.get_messages(chat_id, batch)
            for message in messages:
                if message.document and message.topics:
                    topic_id = message.topics.id
                    if topic_id not in result:
                        result[topic_id] = Topics(topic_id=topic_id, topic_title=message.topics.title)
                    file_caption = message.caption if message.caption else message.document.file_name
                    result[topic_id].files.append(File(file_id=message.document.file_id, file_caption=file_caption,
                                                       file_type=message.document.mime_type))
        return list(result.values())