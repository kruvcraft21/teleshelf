from logging.config import dictConfig

import yaml

from config.models import LogSettings


def config_logger(log_settings: LogSettings, config_path: str = "logging.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        config_text = f.read()

    config_text = config_text.replace("${LOG_LEVEL}", log_settings.level)
    config_text = config_text.replace("${LOG_FORMAT}", log_settings.format)
    dictConfig(yaml.safe_load(config_text))