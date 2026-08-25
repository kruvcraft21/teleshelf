import os

from dotenv import load_dotenv

from config.models import (
    ApiSettings,
    Config,
    LogSettings,
    PGDatabseSettings,
    RedisSettings,
    TgApiServer,
    TgBot,
)

load_dotenv()


def load_config(path: str | None = None) -> Config:
    return Config(
        bot=TgBot(token=os.getenv("BOT_TOKEN", "")),
        log=LogSettings(
            level=os.getenv("LOG_LEVEL", ""), format=os.getenv("LOG_FORMAT", "")
        ),
        database=PGDatabseSettings(
            host=os.getenv("POSTGRES_HOST", ""),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", ""),
            username=os.getenv("POSTGRES_USER", ""),
            password=os.getenv("POSTGRES_PASSWORD", ""),
        ),
        tg_api=TgApiServer(
            api_id=int(os.getenv("TELEGRAM_API_ID", "0")),
            api_hash=os.getenv("TELEGRAM_API_HASH", ""),
        ),
        redis=RedisSettings(
            host=os.getenv("REDIS_HOST", ""),
            port=int(os.getenv("REDIS_PORT", "6379")),
        ),
        api=ApiSettings(
            api_domain=os.getenv("API_DOMAIN", ""),
        ),
    )
