"""Configuración centralizada de logging para la aplicación y los scripts."""
import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import get_config

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    config = get_config()
    os.makedirs(os.path.dirname(config.log_file) or ".", exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        config.log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(config.log_level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(config.log_level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _configured = True
