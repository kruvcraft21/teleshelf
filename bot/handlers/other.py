from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
import logging

logging.getLogger(__name__)

other_router = Router()

@other_router.message()
async def print_info(message: Message):
    logging.info("Попали в other")
    logging.info(message.model_dump_json(indent=4, exclude_none=True))

