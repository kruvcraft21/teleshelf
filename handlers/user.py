from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from database.db import Database
from keyboards.pagination_maker import pagination_maker, calculate_pagination, build_navigation_buttons, MAX_BUTTONS
from callbacks.pagination import TopicsPagination, FilesPagination
from callbacks.collection_worker import Topic, File

user_router = Router()

@user_router.message(CommandStart(), F.from_user)
async def start(message: Message, db: Database):
    user_id = message.from_user.id
    chats = await db.get_chats(user_id)
    if len(chats) == 0:
        await message.answer("Увы нет чатов")
        return
    buttons_topics = [(chat, Topic(topic_id=chats[chat]).pack()) for chat in chats.keys()]
    navigation = build_navigation_buttons(1, TopicsPagination)
    keyboard = pagination_maker(result_search=buttons_topics[:MAX_BUTTONS], navigation=navigation)
    await message.answer("Вот ваша коллекция чатов", reply_markup=keyboard)

@user_router.callback_query(TopicsPagination.filter())
async def topics_pagination(callback_query: CallbackQuery, db: Database, callback_data: TopicsPagination):
    user_id = callback_query.from_user.id
    chats = await db.get_chats(user_id)
    buttons_topics = [(chat, Topic(topic_id=chats[chat]).pack()) for chat in chats.keys()]
    paginated = calculate_pagination(buttons_topics, callback_data.current_page, callback_data.next_step)
    if not paginated:
        await callback_query.answer("Дальше уже некуда")
        return

    current_items, new_page = paginated
    navigation = build_navigation_buttons(new_page, TopicsPagination)
    keyboard = pagination_maker(result_search=current_items, navigation=navigation)
    await callback_query.message.edit_text("Вот ваша коллекция чатов", reply_markup=keyboard)


async def show_topic_files(topic_id: int, db: Database):
    files = await db.get_files(topic_id)
    topic_name = await db.get_topic_title(topic_id)
    buttons_files = [(file, File(topic_id=topic_id, file_id=files[file]).pack()) for file in files.keys()]
    return buttons_files, topic_name

@user_router.callback_query(Topic.filter())
async def open_topic(callback_query: CallbackQuery, db: Database, callback_data: Topic):
    topic_id = callback_data.topic_id
    buttons_files, topic_name  = await show_topic_files(topic_id, db)

    navigation = build_navigation_buttons(1, FilesPagination, topic_id=topic_id)
    keyboard = pagination_maker(result_search=buttons_files[:MAX_BUTTONS], navigation=navigation)

    await callback_query.message.edit_text(f"В колекции {topic_name} есть следующие файлы", reply_markup=keyboard)

@user_router.callback_query(FilesPagination.filter())
async def files_pagination(callback_query: CallbackQuery, db: Database, callback_data: FilesPagination):
    topic_id = callback_data.topic_id
    buttons_files, topic_name  = await show_topic_files(topic_id, db)

    paginated = calculate_pagination(buttons_files, callback_data.current_page, callback_data.next_step)
    if not paginated:
        await callback_query.answer("Дальше уже некуда")
        return

    current_items, new_page = paginated
    navigation = build_navigation_buttons(new_page, FilesPagination, topic_id=topic_id)
    keyboard = pagination_maker(result_search=current_items, navigation=navigation)
    await callback_query.message.edit_text(f"В колекции {topic_name} есть следующие файлы", reply_markup=keyboard)

