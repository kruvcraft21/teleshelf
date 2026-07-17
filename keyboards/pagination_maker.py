from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callbacks.pagination import PaginationButton

MAX_BUTTONS = 5

def calculate_pagination(buttons: list, current_page: int, next_step: int) -> tuple[list, int] | None:
    total_pages = len(buttons) // MAX_BUTTONS + (1 if len(buttons) % MAX_BUTTONS > 0 else 0)
    next_page = current_page + next_step

    if next_page <= 0 or next_page > total_pages:
        return None

    start_index = (current_page - 1) * MAX_BUTTONS
    end_index = min(start_index + MAX_BUTTONS, len(buttons))
    return buttons[start_index:end_index], next_page

def build_navigation_buttons(page: int, callback_class: type[PaginationButton], **extra_params) -> list[str]:
    return [
        callback_class(current_page=page, next_step=-1, **extra_params).pack(),
        callback_class(current_page=page, next_step=1, **extra_params).pack(),
    ]

def pagination_maker(result_search: list[tuple[str, str]], navigation: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    result_keyboard = [InlineKeyboardButton(text=result, callback_data=callback) for result, callback in result_search]
    builder.row(*result_keyboard, width=1)
    navigation_keyboard = [
        InlineKeyboardButton(text='<<', callback_data=navigation[0]),
        InlineKeyboardButton(text='>>', callback_data=navigation[1]),
    ]
    builder.row(*navigation_keyboard)
    return builder.as_markup()

def is_navigation(callback_data: PaginationButton) -> bool:
    return callback_data.index == -1

async def render_keyboard(buttons:list[str], event : CallbackQuery | Message, message:str, current_page: int, next_step: int):
    buttons_topics = [(chat, PaginationButton(next_step=next_step, current_page=current_page, index=idx).pack()) for idx, chat in
                      enumerate(buttons)]
    paginated = calculate_pagination(buttons_topics, current_page, next_step)

    if not paginated:
        await event.answer("Дальше уже некуда")
        return

    current_items, new_page = paginated
    navigation = build_navigation_buttons(new_page, PaginationButton, index=-1)
    keyboard = pagination_maker(result_search=current_items, navigation=navigation)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(message, reply_markup=keyboard)
    else:
        await event.answer(message, reply_markup=keyboard)