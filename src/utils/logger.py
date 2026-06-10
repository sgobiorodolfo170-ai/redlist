import logging
import os
import sys
from typing import Optional

_loggers: dict = {}


def get_logger(name: str = "RedList", level: Optional[int] = None) -> logging.Logger:
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)

    if level is None:
        level = logging.DEBUG if os.environ.get('REDLIST_DEBUG') else logging.INFO

    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _loggers[name] = logger
    return logger


def log_exception(logger: Optional[logging.Logger] = None, message: str = "Exception occurred"):
    if logger is None:
        logger = get_logger()

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"{message}: {e}")
                raise
        return wrapper
    return decorator
