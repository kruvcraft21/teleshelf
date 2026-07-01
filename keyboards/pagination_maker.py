from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks.pagination import Pagination

MAX_BUTTONS = 5

def calculate_pagination(buttons: list, current_page: int, next_step: int) -> tuple[list, int] | None:
    total_pages = len(buttons) // MAX_BUTTONS + (1 if len(buttons) % MAX_BUTTONS > 0 else 0)
    next_page = current_page + next_step

    if next_page <= 0 or next_page > total_pages:
        return None

    start_index = (current_page - 1) * MAX_BUTTONS
    end_index = min(start_index + MAX_BUTTONS, len(buttons))
    return buttons[start_index:end_index], next_page

def build_navigation_buttons(page: int, callback_class: type[Pagination], **extra_params) -> list[str]:
    return [
        callback_class(current_page=page, next_step=-1, **extra_params).pack(),
        callback_class(current_page=page, next_step=1, **extra_params).pack(),
    ]

def pagination_maker(result_search: list[tuple[str, str]], navigation: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    result_keyboard = [InlineKeyboardButton(text=result, callback_data=callback) for result, callback in result_search]
    builder.row(*result_keyboard)
    navigation_keyboard = [
        InlineKeyboardButton(text='<<', callback_data=navigation[0]),
        InlineKeyboardButton(text='>>', callback_data=navigation[1]),
    ]
    builder.row(*navigation_keyboard)
    return builder.as_markup()