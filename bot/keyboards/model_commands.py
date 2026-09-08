from enum import Enum


class BotCommand(str, Enum):
    START = "start"
    UPDATE = "update"
