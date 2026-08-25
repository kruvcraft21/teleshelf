import logging

from aiogram import Router
from aiogram.types import Message

logger = logging.getLogger(__name__)

other_router = Router()


@other_router.message()
async def print_info(message: Message):
    logger.info("Попали в other")
    logger.info(message.model_dump_json(indent=4, exclude_none=True))
