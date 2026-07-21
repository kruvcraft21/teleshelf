from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callbacks.pagination import PaginationButton

MAX_BUTTONS = 5

def _calculate_pagination(buttons: list[tuple[str, str]], next_page: int) -> list[tuple[str, str]] | None:
    total_pages = len(buttons) // MAX_BUTTONS + (1 if len(buttons) % MAX_BUTTONS > 0 else 0)
    if next_page <= 0 or next_page > total_pages:
        return None

    start_index = (next_page - 1) * MAX_BUTTONS
    end_index = min(start_index + MAX_BUTTONS, len(buttons))
    return buttons[start_index:end_index]

def _pagination_maker(result_search: list[tuple[str, str]], navigation: list[str]) -> InlineKeyboardMarkup:
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

async def render_keyboard(buttons:list[str], event : CallbackQuery | Message, message:str, next_page):
    buttons_topics = [
        (chat, PaginationButton(index=idx).pack())
        for idx, chat in enumerate(buttons)
    ]
    paginated = _calculate_pagination(buttons_topics, next_page)

    if not paginated:
        await event.answer("Дальше уже некуда")
        return

    current_items = paginated
    navigation = [
        PaginationButton(current_page=next_page, next_step=-1).pack(),
        PaginationButton(current_page=next_page, next_step=1).pack(),
    ]
    keyboard = _pagination_maker(result_search=current_items, navigation=navigation)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(message, reply_markup=keyboard)
    else:
        await event.answer(message, reply_markup=keyboard)