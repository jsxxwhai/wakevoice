"""Centralized logging with optional rich formatting."""
from __future__ import annotations

import logging
import sys

try:
    from rich.logging import RichHandler
    _RICH = True
except ImportError:  # pragma: no cover
    _RICH = False


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the root logger for the assistant."""
    logger = logging.getLogger("assistant")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    if logger.handlers:  # already configured
        return logger
    if _RICH:
        handler = RichHandler(rich_tracebacks=True, markup=True)
        handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger
