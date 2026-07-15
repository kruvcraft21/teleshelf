from contextlib import asynccontextmanager
from typing import AsyncIterator
import logging
from hydrogram import Client
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from config import load_config, Config
from rich import inspect


from dotenv import load_dotenv
import os
import uuid

load_dotenv()

# Конфигурация
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

config: Config = load_config()
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
reader.mount("/static", StaticFiles(directory="static"), name="static")
@reader.get("/", response_class=HTMLResponse)
async def reader_page(request: Request, file_id: str):
    """Страница читалки"""
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    return templates.TemplateResponse(
        request=request,
        name="reader.html",
        context={
            "pdf_url": f"/api/pdf/{file_id}",
            "ver": str(uuid.uuid4()),
        },
        headers=headers,
    )

@reader.get("/api/pdf/{file_id}", response_class=StreamingResponse)
async def get_pdf(request: Request, file_id: str) -> AsyncIterator[bytes]:
    """Стриминг PDF из Telegram"""
    
    bot = request.app.state.bot

    async for chunk in bot.stream_media(file_id):
        yield chunk

@asynccontextmanager
async def lifespan(fast_app: FastAPI):
    bot = await HydroClient.start(name='tg_reader', api_id=config.tg_api.api_id, api_hash=config.tg_api.api_hash,
                       bot_token=config.bot.token)
    fast_app.state.bot = bot
    yield
    await fast_app.state.bot.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(reader)