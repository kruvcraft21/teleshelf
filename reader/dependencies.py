from typing import Annotated

from fastapi import Depends, Request

from clients import HydroClient
from core.context import AppContext
from database import PostgresStorage, RedisSessionStore
from reader.session import ReaderSession


def _get_context(request: Request) -> AppContext:
    return request.app.state.context


AppCont = Annotated[AppContext, Depends(_get_context)]


def _get_db(context: AppCont) -> PostgresStorage:
    return context.db


def _get_hydro(context: AppCont) -> HydroClient:
    return context.hydro


def _get_reader_session(context: AppCont) -> ReaderSession:
    return context.reader_session


def _get_redis(context: AppCont) -> RedisSessionStore:
    return context.redis


Db = Annotated[PostgresStorage, Depends(_get_db)]
Hydro = Annotated[HydroClient, Depends(_get_hydro)]
ReaderSessionDependency = Annotated[
    ReaderSession,
    Depends(_get_reader_session),
]
Redis = Annotated[RedisSessionStore, Depends(_get_redis)]
