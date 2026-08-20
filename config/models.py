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

@dataclass
class TgApiServer:
    api_id: int
    api_hash: str


@dataclass
class RedisSettings:
    host: str
    port: int

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