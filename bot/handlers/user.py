import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InaccessibleMessage,
    Message,
    ReplyKeyboardRemove,
    User,
)
from yarl import URL

from bot.callbacks import PaginationButton, ReaderState
from bot.keyboards.pagination_maker import (
    document_keyboard,
    file_keyboard,
    topic_keyboard,
)
from config.models import Config
from database.postgres import PostgresStorage
from reader import ReaderSession

user_router = Router()

logger = logging.getLogger(__name__)


@user_router.message(CommandStart(), F.from_user)
async def start(message: Message, db: PostgresStorage, state: FSMContext):
    # pyrefly: ignore [bad-assignment]
    user : User = message.from_user
    chats = await db.get_chats(user.id)
    if len(chats) == 0:
        await message.answer("Увы нет чатов")
        return
    await state.set_state(ReaderState.choose_topic)
    await message.answer(
        "Вот ваша коллекция чатов", reply_markup=topic_keyboard(chats, 1)
    )


@user_router.callback_query(
    StateFilter(ReaderState.choose_topic), PaginationButton.filter()
)
async def choose_topic(
    callback_query: CallbackQuery,
    state: FSMContext,
    db: PostgresStorage,
    session_manager: ReaderSession,
    callback_data: PaginationButton,
):
    if (
        isinstance(callback_query.message, InaccessibleMessage)
        or callback_query.message is None
    ):
        callback_query.answer("Обновите список чатов", show_alert=True)
        return

    user_id = callback_query.from_user.id
    chats = await db.get_chats(user_id)

    if callback_data.action == "page":
        await callback_query.message.edit_text(
            "Вот ваша коллекция чатов",
            reply_markup=topic_keyboard(chats, callback_data.page),
        )
    elif callback_data.action == "topic":
        chats_list = list(chats.items())
        topic_name, topic_id = chats_list[callback_data.index]
        files = await session_manager.get_files(topic_id, user_id)
        await state.set_state(ReaderState.choose_file)
        await state.update_data(topic_name=topic_name, topic_id=topic_id)
        await callback_query.message.edit_text(
            f"В колекции {topic_name} есть следующие файлы",
            reply_markup=file_keyboard(files, 1),
        )
    else:
        await callback_query.answer("Недоступное действие", show_alert=True)
        return

    await callback_query.answer()


@user_router.callback_query(
    StateFilter(ReaderState.choose_file), PaginationButton.filter()
)
async def choose_file(
    callback_query: CallbackQuery,
    state: FSMContext,
    session_manager: ReaderSession,
    callback_data: PaginationButton,
    db: PostgresStorage,
    config: Config,
):
    if (
        isinstance(callback_query.message, InaccessibleMessage)
        or callback_query.message is None
    ):
        callback_query.answer("Обновите список чатов", show_alert=True)
        return

    data = await state.get_data()

    if callback_data.action == "back_to_topics":
        await state.set_state(ReaderState.choose_topic)
        chats = await db.get_chats(callback_query.from_user.id)
        await callback_query.message.edit_text(
            "Вот ваша коллекция чатов", reply_markup=topic_keyboard(chats, 1)
        )
        return

    topic_id: int = data["topic_id"]
    topic_name: str = data["topic_name"]
    files = await session_manager.get_files(topic_id, callback_query.from_user.id)

    if callback_data.action in ["page", "back_to_files"]:
        await callback_query.message.edit_text(
            f"В колекции {topic_name} есть следующие файлы",
            reply_markup=file_keyboard(files, callback_data.page),
        )
    elif callback_data.action == "file":
        files_list = list(files.items())
        file_name, file_id = files_list[callback_data.index]
        session = await session_manager.create(file_id, callback_query.from_user.id)
        document_url = str(URL(config.api.api_domain).update_query(session_id=session))
        await callback_query.message.edit_text(
            f"Вот ваш документ: {file_name}",
            reply_markup=document_keyboard(document_url, 1),
        )
    else:
        await callback_query.answer("Недоступное действие", show_alert=True)
        return

    await callback_query.answer()


@user_router.message(Command("clear"))
async def clear_keyboard(message: Message):
    await message.answer("Clear keyboard", reply_markup=ReplyKeyboardRemove())
