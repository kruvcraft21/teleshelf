from typing import Annotated

from fastapi import Depends, Request

from database import PostgresStorage, RedisSessionStore
from clients import HydroClient
from reader.session import ReaderSession
from core.context import AppContext


def get_context(request: Request) -> AppContext:
    return request.app.state.context


def get_db(context: AppContext = Depends(get_context)) -> PostgresStorage:
    return context.db


def get_hydro(context: AppContext = Depends(get_context)) -> HydroClient:
    return context.hydro


def get_reader_session(context: AppContext = Depends(get_context)) -> ReaderSession:
    return context.reader_session

def get_redis(context: AppContext = Depends(get_context)) -> RedisSessionStore:
    return context.redis


Db = Annotated[PostgresStorage, Depends(get_db)]
Hydro = Annotated[HydroClient, Depends(get_hydro)]
ReaderSessionDependency = Annotated[
    ReaderSession,
    Depends(get_reader_session),
]
Redis = Annotated[RedisSessionStore, Depends(get_redis)]
