"""Logging configuration using Loguru."""

import sys
from contextvars import ContextVar
from pathlib import Path

from loguru import logger
from rich.traceback import install as install_rich_traceback

# Context variable for request_id
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def setup_logging(log_level: str = "INFO", log_file: str | None = None) -> None:
    """
    Configure loguru logging with optional file output.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    """
    # Remove default handler
    logger.remove()

    # Add console handler with request_id context
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[request_id]}</cyan> | <level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[request_id]} | {message}",
            level=log_level,
            rotation="100 MB",
            retention="30 days",
            compression="zip",
        )

    # Patch logger to always include request_id from context
    logger.configure(patcher=lambda record: record["extra"].update(request_id=request_id_var.get() or "N/A"))

    # Install rich tracebacks for better error display
    install_rich_traceback(show_locals=True, max_frames=10, width=120)


def set_request_id(request_id: str | int) -> None:
    """Set the request_id in context for all subsequent log messages."""
    request_id_var.set(str(request_id))


def clear_request_id() -> None:
    """Clear the request_id from context."""
    request_id_var.set(None)


# Default setup
setup_logging()

