from typing import Literal

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.callbacks import PaginationButton

MAX_BUTTONS = 5

ItemAction = Literal["topic", "file"]
BackAction = Literal["back_to_topics"]


def _get_page(items: list[str], page: int) -> tuple[list[str], int, int, int]:
    total_pages = len(items) // MAX_BUTTONS + (1 if len(items) % MAX_BUTTONS > 0 else 0)
    current_page = min(max(page, 1), total_pages)

    start_index = (current_page - 1) * MAX_BUTTONS
    end_index = min(start_index + MAX_BUTTONS, len(items))
    return items[start_index:end_index], current_page, start_index, total_pages


def _add_navigation_buttons(
    builder: InlineKeyboardBuilder, page: int, total_pages: int
) -> None:
    buttons: list[InlineKeyboardButton] = []
    if page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="<<",
                callback_data=PaginationButton(action="page", page=page - 1).pack(),
            )
        )
    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text=">>",
                callback_data=PaginationButton(action="page", page=page + 1).pack(),
            )
        )
    builder.row(*buttons)


def _catalog_maker(
    items: list[str],
    page: int,
    item_action: ItemAction,
    back_action: BackAction | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    items, current_page, start_index, total_pages = _get_page(items, page)

    for idx, item in enumerate(items, start=start_index):
        builder.row(
            InlineKeyboardButton(
                text=item,
                callback_data=PaginationButton(action=item_action, index=idx).pack(),
            )
        )

    _add_navigation_buttons(builder, current_page, total_pages)

    if back_action:
        builder.row(
            InlineKeyboardButton(
                text="Назад",
                callback_data=PaginationButton(action=back_action).pack(),
            )
        )
    return builder.as_markup()

def topic_keyboard(chats: dict[str, int], page: int) -> InlineKeyboardMarkup:
    return _catalog_maker(
        items=list(chats.keys()),
        page=page,
        item_action="topic",
    )

def file_keyboard(files: dict[str, int], page: int) -> InlineKeyboardMarkup:
    return _catalog_maker(
        items=list(files.keys()),
        page=page,
        item_action="file",
        back_action="back_to_topics",
    )

def document_keyboard(url: str, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Ссылка на документ", web_app=WebAppInfo(url=url)
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=PaginationButton(action="back_to_files", page=page).pack(),
        )
    )
    return builder.as_markup()
