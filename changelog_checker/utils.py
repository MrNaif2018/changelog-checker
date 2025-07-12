"""
Utility functions and error handling for the changelog checker.
"""

import logging
import sys
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

import requests

F = TypeVar("F", bound=Callable[..., Any])


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("changelog_checker")
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper()))
    return logger


def handle_network_errors(func: F) -> F:
    """Decorator to handle common network errors gracefully."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger("changelog_checker")
            logger.warning(f"Network error in {func.__name__}: {e}")
            return None

    return cast(F, wrapper)


def safe_request(func: F) -> F:
    """Decorator to make HTTP requests safer with retries and timeouts."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        max_retries = 3
        base_delay = 1.0
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                logger = logging.getLogger("changelog_checker")
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                logger = logging.getLogger("changelog_checker")
                logger.error(f"Unexpected error in {func.__name__}: {e}")
                raise
        return None

    return cast(F, wrapper)


class ChangelogCheckerError(Exception):
    """Base exception for changelog checker errors."""


class ParserError(ChangelogCheckerError):
    """Error in parsing package manager output."""


class NetworkError(ChangelogCheckerError):
    """Error in network operations."""


class ChangelogNotFoundError(ChangelogCheckerError):
    """Error when changelog cannot be found."""
