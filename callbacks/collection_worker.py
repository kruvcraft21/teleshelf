from aiogram.filters.callback_data import CallbackData

class Topic(CallbackData, prefix='tc'):
    topic_id: int

class File(CallbackData, prefix='fc'):
    file_id: int
    topic_id: int