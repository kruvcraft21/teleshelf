from contextlib import asynccontextmanager
from typing import AsyncIterator
import logging

from clients.hydroclient import HydroClient
from fastapi import FastAPI, Request, APIRouter, Body
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from config import load_config
from reader.dependencies import Db, Hydro, Redis

import os
import uuid

# Конфигурация
config = load_config()
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.getLevelName(level=config.log.level),
    format=config.log.format,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logger.info(f"BASE_DIR: {BASE_DIR}")

# FastAPI приложение
reader = APIRouter()
templates = Jinja2Templates(directory="templates")
reader.mount("/css", StaticFiles(directory="static/css"), name="css")
reader.mount("/js", StaticFiles(directory="static/js"), name="js")
reader.mount("/pdfjs", StaticFiles(directory="static/pdfjs"), name="pdfjs")

@reader.get("/", response_class=HTMLResponse)
async def reader_page(request: Request, redis_session: Redis, session_id: str  = ""):
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
            "level_debug": str(config.log.level),
            "page": page,
        },
        headers=headers,
    )

@reader.get("/api/pdf/{session_id}", response_class=StreamingResponse)
async def get_pdf(request: Request, bot: Hydro, redis_session: Redis, session_id: str) -> AsyncIterator[bytes]:
    """Стриминг PDF из Telegram"""

    file_id = await redis_session.get_tg_file_id(session_id)
    async for chunk in bot.stream_media(file_id):
        yield chunk

@reader.post("/api/pdf/update_position/{session_id}")
async def update_pdf_position(request: Request, redis_session: Redis, session_id: str, page: int = Body(0, embed=True)):
    """Обновление позиции PDF"""

    logger.info(f"session_id: {session_id}, page: {page}")
    await redis_session.update_page(session_id, page)

@asynccontextmanager
async def lifespan(fast_app: FastAPI):
    bot = await HydroClient.create(name='tg_reader', api_id=config.tg_api.api_id, api_hash=config.tg_api.api_hash,
                                   bot_token=config.bot.token)
    fast_app.state.bot = bot
    yield
    await fast_app.state.bot.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(reader)