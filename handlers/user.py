from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, WebAppInfo, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from yarl import URL

from database.db import Database
from keyboards.pagination_maker import is_navigation, render_keyboard
from callbacks.pagination import PaginationButton

from callbacks.reader_state import ReaderState
from aiogram.fsm.context import FSMContext

import logging
import os

user_router = Router()

logger = logging.getLogger(__name__)

@user_router.message(CommandStart(), F.from_user)
async def start(message: Message, db: Database, state: FSMContext):
    user_id = message.from_user.id
    chats = await db.get_chats(user_id)
    if len(chats) == 0:
        await message.answer("Увы нет чатов")
        return
    await state.set_state(ReaderState.choose_topic)
    await render_keyboard(buttons=list(chats.keys()),
                          event=message,
                          message="Вот ваша коллекция чатов",
                          next_page=1)

@user_router.callback_query(StateFilter(ReaderState.choose_topic), PaginationButton.filter())
async def choose_topic(callback_query: CallbackQuery, state: FSMContext, db: Database, callback_data: PaginationButton):
    user_id = callback_query.from_user.id
    chats = await db.get_chats(user_id)
    chats_list = list(chats.keys())
    if is_navigation(callback_data) or callback_data.index > len(chats_list):
        await render_keyboard(buttons=chats_list,
                              event=callback_query,
                              message="Вот ваша коллекция чатов",
                              next_page=callback_data.current_page + callback_data.next_step)
    else:
        topic_name = chats_list[callback_data.index]
        topic_id = chats[topic_name]
        files = await db.get_files(chats[topic_name], user_id)
        await state.set_state(ReaderState.choose_file)
        await state.update_data(topic_name=topic_name, topic_id=topic_id)
        await render_keyboard(buttons=list(files.keys()),
                              event=callback_query,
                              message=f"В колекции {topic_name} есть следующие файлы",
                              next_page=1)

@user_router.callback_query(StateFilter(ReaderState.choose_file), PaginationButton.filter())
async def choose_file(callback_query: CallbackQuery, state: FSMContext, db: Database, callback_data: PaginationButton):
    data = await state.get_data()
    topic_id : int = data['topic_id']
    topic_name : str = data['topic_name']
    files = await db.get_files(topic_id, callback_query.from_user.id)
    files_id = list(files.values())
    if is_navigation(callback_data) or callback_data.index > len(files_id):
        await render_keyboard(buttons=list(files.keys()),
                              event=callback_query,
                              message=f"В колекции {topic_name} есть следующие файлы",
                              next_page=callback_data.current_page + callback_data.next_step)
    else:
        file_id = files_id[callback_data.index]
        session = await db.create_session(file_id, callback_query.from_user.id)
        url = URL(os.getenv('API_DOMAIN', ""))
        final_url = str(url.update_query(session_id=session))
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="Ссылка на документ",
                                 web_app=WebAppInfo(url=final_url)),
            InlineKeyboardButton(text="Назад",
                                 callback_data=PaginationButton(current_page=callback_data.current_page, next_step=callback_data.next_step, index=-1).pack()),
            width=1
        )
        await state.set_state(ReaderState.choose_file)
        await callback_query.message.edit_text("Вот ваш документ", reply_markup=builder.as_markup())


@user_router.message(Command("clear"))
async def clear_keyboard(message: Message):
    await message.answer("Clear keyboard", reply_markup=ReplyKeyboardRemove())