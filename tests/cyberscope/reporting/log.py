"""Console and per-run file logging without secret-bearing context."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logger(log_path: Path | None = None, debug: bool = False) -> logging.Logger:
    logger = logging.getLogger("cyberscope")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger
