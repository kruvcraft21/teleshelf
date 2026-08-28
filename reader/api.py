import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import APIRouter, Body, FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from clients.hydroclient import HydroClient
from config import load_config
from config.logging import config_logger
from reader.dependencies import Hydro, Redis

# Конфигурация
config = load_config()
logger = logging.getLogger(__name__)


# FastAPI приложение
reader = APIRouter()
templates = Jinja2Templates(directory="templates")
reader.mount("/css", StaticFiles(directory="static/css"), name="css")
reader.mount("/js", StaticFiles(directory="static/js"), name="js")
reader.mount("/pdfjs", StaticFiles(directory="static/pdfjs"), name="pdfjs")


@reader.get("/", response_class=HTMLResponse)
async def reader_page(
    request: Request,
    redis_session: Redis,
    session_id: str = "",
    mode: Literal["fullscreen", "normal"] = "normal",
):
    """Страница читалки"""
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    page = 0
    if len(session_id) > 0:
        page = await redis_session.get_page(session_id)

    return templates.TemplateResponse(
        request=request,
        name="reader.html",
        context={
            "session_id": session_id,
            "ver": str(uuid.uuid4()),
            "level_debug": config.log.level,
            "page": page,
            "reader_mode": mode,
        },
        headers=headers,
    )


@reader.get("/api/pdf/{session_id}", response_class=StreamingResponse)
async def get_pdf(
    request: Request, bot: Hydro, redis_session: Redis, session_id: str
) -> AsyncIterator[bytes]:
    """Стриминг PDF из Telegram"""

    chat_id = await redis_session.get_chat_id(session_id)
    message_id = await redis_session.get_message_id(session_id)
    message = await bot.get_messages(chat_id, message_id)
    if not isinstance(message, list):
        # pyrefly: ignore [not-iterable]
        async for chunk in bot.stream_media(message):
            yield chunk


@reader.post("/api/pdf/update_position/{session_id}")
async def update_pdf_position(
    request: Request,
    redis_session: Redis,
    session_id: str,
    page: int = Body(0, embed=True),
):
    """Обновление позиции PDF"""

    logger.info(f"session_id: {session_id}, page: {page}")
    await redis_session.update_page(session_id, page)


@asynccontextmanager
async def lifespan(fast_app: FastAPI):
    config_logger(config.log)
    bot = await HydroClient.create(
        name="tg_reader",
        api_id=config.tg_api.api_id,
        api_hash=config.tg_api.api_hash,
        bot_token=config.bot.token,
    )
    fast_app.state.bot = bot
    yield
    await fast_app.state.bot.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(reader)
