from dataclasses import dataclass


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
    pool_size: int
    max_overflow: int


@dataclass
class TgApiServer:
    api_id: int
    api_hash: str


@dataclass
class FSMSettings:
    data_ttl: int
    state_ttl: int


@dataclass
class RedisSettings:
    host: str
    port: int
    session_ttl: int
    db: int
    max_connections: int


@dataclass
class TransferJobSettings:
    interval_minutes: int
    scheduler_max_instances: int


@dataclass
class ApiSettings:
    api_domain: str


@dataclass
class Config:
    bot: TgBot
    log: LogSettings
    database: PGDatabseSettings
    tg_api: TgApiServer
    redis: RedisSettings
    api: ApiSettings
    fsm: FSMSettings
    transfer_job: TransferJobSettings
