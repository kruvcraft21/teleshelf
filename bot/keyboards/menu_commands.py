import asyncio
import logging

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)

from bot.keyboards.model_commands import BotCommand as bc

logger = logging.getLogger(__name__)


async def set_menu_commands(bot: Bot):
    is_success = await asyncio.gather(
        bot.delete_my_commands(),
        bot.delete_my_commands(BotCommandScopeAllPrivateChats()),
        bot.delete_my_commands(BotCommandScopeAllGroupChats()),
    )
    logger.info(f"Deleted menu commands, from default scope, success: {is_success[0]}")
    logger.info(
        f"Deleted menu commands, from all private chats scope, success: {is_success[1]}"
    )
    logger.info(
        f"Deleted menu commands, from all group chats scope, success: {is_success[2]}"
    )
    user_commands = [
        BotCommand(command=bc.START, description="Начать работу с ботом"),
    ]
    group_commands = [
        BotCommand(
            command=bc.UPDATE,
            description="Обновить документы (Работает только в форумах)",
        ),
    ]
    user_is_success = await bot.set_my_commands(user_commands, scope=BotCommandScopeAllPrivateChats())
    logger.info(f"Set menu commands for users: {user_commands}, success: {user_is_success}")
    group_us_success = await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
    logger.info(f"Set menu commands for groups: {group_commands}, success: {group_us_success}")
