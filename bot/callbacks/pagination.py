from typing import Literal

from aiogram.filters.callback_data import CallbackData


class PaginationButton(CallbackData, prefix="pg"):
    action: Literal["topic", "file", "page", "back_to_topics", "back_to_files"]
    index: int = -1
    page: int = 1


if __name__ == "__main__":
    test = PaginationButton(action="topic")
    print(test.pack())
