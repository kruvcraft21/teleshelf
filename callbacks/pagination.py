from aiogram.filters.callback_data import CallbackData

class PaginationButton(CallbackData, prefix='pg'):
    current_page: int
    next_step: int
    index: int