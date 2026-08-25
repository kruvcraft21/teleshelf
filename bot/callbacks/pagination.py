from aiogram.filters.callback_data import CallbackData

class PaginationButton(CallbackData, prefix='pg'):
    current_page: int = 0
    next_step: int = 0
    index: int = -1


if __name__ == "__main__":
    test = PaginationButton()
    print(test.pack())