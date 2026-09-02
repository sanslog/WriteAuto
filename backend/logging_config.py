"""Logging configuration for WriteAuto.

Sets up file-based logging to DATA_DIR/logs/ for all backend modules.
Called once at application startup.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from backend.config import LOG_DIR, DATA_DIR

# Keep references so they are not garbage-collected
_file_handlers: list[logging.Handler] = []


def setup_file_logging(logger_names: list[str] | None = None, level: int = logging.DEBUG) -> None:
    """Add a rotating file handler to each named logger.

    If logger_names is None, applies to the root logger.
    Logs are written to DATA_DIR/logs/writeauto.log with daily rotation.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "writeauto.log"

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.handlers.TimedRotatingFileHandler(
        log_path,
        when="midnight",
        interval=1,
        backupCount=30,  # keep 30 days
        encoding="utf-8",
        delay=True,
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)

    targets = logger_names or [None]  # None means root
    for name in targets:
        log = logging.getLogger(name)
        log.addHandler(handler)
        # Ensure it propagates to root so console output is preserved
        log.setLevel(level)

    _file_handlers.append(handler)

    logging.getLogger(__name__).info(
        "File logging initialised: %s (backupCount=%d, level=%s)",
        log_path, 30, logging.getLevelName(level),
    )
