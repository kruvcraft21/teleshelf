import logging

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

from bot.keyboards.model_commands import BotCommand as bc

logger = logging.getLogger(__name__)


async def set_menu_commands(bot: Bot):
    is_success = await bot.delete_my_commands()
    logger.info(f"Deleted menu commands, success: {is_success}")
    bot_commands = [
        BotCommand(command=bc.START, description="Начать работу с ботом"),
        BotCommand(
            command=bc.UPDATE,
            description="Обновить документы (Работает только в форумах)",
        ),
    ]
    is_success = await bot.set_my_commands(bot_commands, scope=BotCommandScopeDefault())
    logger.info(f"Set menu commands: {bot_commands}, success: {is_success}")
