from aiogram.fsm.state import State, StatesGroup

class ReaderState(StatesGroup):
    choose_topic = State()
    choose_file = State()