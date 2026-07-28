"""
Centralized logger for the Islamic AI Chatbot project.

Usage in any module:
    from custom_logger import setup_logger
    logger = setup_logger(__name__)
    logger.info("Connected to Qdrant")
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent / "logs" / "chatbot.log"


def setup_logger(name: str = None) -> logging.Logger:
    if name is None:
        name = __name__

    logger = logging.getLogger(name)

    # Prevent duplicate handlers if module is imported multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler — prints to terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler — rotates at 5MB, keeps 3 backups
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

