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
class PGDatabseSettings:
    host: str
    port: int
    database: str
    username: str
    password: str

@dataclass
class TgApiServer:
    api_id: int
    api_hash: str


@dataclass
class RedisSettings:
    host: str
    port: int

@dataclass
class Config:
    bot: TgBot
    log: LogSettings
    database: PGDatabseSettings
    tg_api: TgApiServer
    redis: RedisSettings

def load_config(path: str | None = None) -> Config:
    return Config(
        bot=TgBot(token=os.getenv("BOT_TOKEN", "")),
        log=LogSettings(level=os.getenv("LOG_LEVEL", ""),
                        format=os.getenv("LOG_FORMAT", "")),
        database=PGDatabseSettings(host=os.getenv("POSTGRES_HOST", ""),
                                   port=int(os.getenv("POSTGRES_PORT", "5432")),
                                   database=os.getenv("POSTGRES_DB", ""),
                                   username=os.getenv("POSTGRES_USER", ""),
                                   password=os.getenv("POSTGRES_PASSWORD", ""), ),
        tg_api=TgApiServer(api_id=int(os.getenv("TELEGRAM_API_ID", "0")),
                           api_hash=os.getenv("TELEGRAM_API_HASH", ""),),
        redis = RedisSettings(host=os.getenv("REDIS_HOST", ""), port=int(os.getenv("REDIS_PORT", "6379")),),
    )