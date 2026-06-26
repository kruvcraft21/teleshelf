from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class TgBot:
    token: str  # Токен для доступа к телеграм-боту

@dataclass
class LogSettings:
    level: str
    format: str

@dataclass
class Config:
    bot: TgBot
    log: LogSettings

def load_config(path: str | None = None) -> Config:
    return Config(
        bot=TgBot(token=os.getenv("BOT_TOKEN", "")),
        log=LogSettings(level=os.getenv("LOG_LEVEL", ""), format=os.getenv("LOG_FORMAT", "")),
    )