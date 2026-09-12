import os

from dotenv import load_dotenv

from config.models import (
    ApiSettings,
    Config,
    FSMSettings,
    LogSettings,
    PGDatabseSettings,
    RedisSettings,
    TgApiServer,
    TgBot,
    TransferJobSettings,
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
            pool_size=int(os.getenv("POSTGRES_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("POSTGRES_MAX_OVERFLOW", "20")),
        ),
        tg_api=TgApiServer(
            api_id=int(os.getenv("TELEGRAM_API_ID", "0")),
            api_hash=os.getenv("TELEGRAM_API_HASH", ""),
        ),
        redis=RedisSettings(
            host=os.getenv("REDIS_HOST", ""),
            port=int(os.getenv("REDIS_PORT", "6379")),
            session_ttl=int(os.getenv("REDIS_SESSION_TTL", "3600")),
            db=int(os.getenv("REDIS_DB", "0")),
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "10")),
        ),
        api=ApiSettings(
            api_domain=os.getenv("API_DOMAIN", ""),
        ),
        fsm=FSMSettings(
            data_ttl=int(os.getenv("FSM_DATA_TTL_SECONDS", "1800")),
            state_ttl=int(os.getenv("FSM_STATE_TTL_SECONDS", "1800")),
        ),
        transfer_job=TransferJobSettings(
            interval_minutes=int(os.getenv("TRANSFER_JOB_INTERVAL_MINUTES", "2")),
            scheduler_max_instances=int(
                os.getenv("TRANSFER_JOB_SCHEDULER_MAX_INSTANCES", "1")
            ),
        ),
    )
