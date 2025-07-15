"""
Utility functions and error handling for the changelog checker.
"""

import logging
import re
import sys
import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

import requests

from changelog_checker.models import ChangeType, PackageReport

P = ParamSpec("P")
T = TypeVar("T")


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


def handle_network_errors(func: Callable[P, T]) -> Callable[P, T | None]:
    """Decorator to handle common network errors gracefully."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger("changelog_checker")
            logger.warning(f"Network error in {func.__name__}: {e}")
            return None

    return wrapper


def safe_request(func: Callable[P, T]) -> Callable[P, T | None]:
    """Decorator to make HTTP requests safer with retries and timeouts."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
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

    return wrapper


class ChangelogCheckerError(Exception):
    """Base exception for changelog checker errors."""


class ParserError(ChangelogCheckerError):
    """Error in parsing package manager output."""


class NetworkError(ChangelogCheckerError):
    """Error in network operations."""


class ChangelogNotFoundError(ChangelogCheckerError):
    """Error when changelog cannot be found."""


def detect_content_format(content: str) -> str:
    """
    Detect if content is markdown, RST, or plain text.

    Args:
        content: The content to analyze

    Returns:
        One of: "markdown", "rst", "plain"
    """
    lines = content.split("\n")
    markdown_indicators = 0
    rst_indicators = 0
    for line in lines:
        stripped = line.strip()
        if re.match(r"^#+\s", stripped):  # Headers: # ## ###
            markdown_indicators += 2
        elif re.match(r"^\*\*.*\*\*", stripped) or re.match(r"^[-*+]\s", stripped):  # Bold: **text**
            markdown_indicators += 1
        elif re.match(r"^```", stripped) or re.match(r"^\[.*\]\(.*\)", stripped):  # Code blocks: ```
            markdown_indicators += 2
        elif re.match(r"^[=\-~`#^\"']{3,}$", stripped) or re.match(r"^\.\. ", stripped):  # RST underlines
            rst_indicators += 2
        elif "~~~~" in stripped or "^^^^" in stripped:  # RST section markers
            rst_indicators += 1
        elif re.match(r"^[\w\-_]+\s+v\d+\.\d+\.\d+.*\([^)]+\)$", stripped):  # RST-style version headers
            rst_indicators += 2
    if rst_indicators > markdown_indicators and rst_indicators > 0:
        return "rst"
    if markdown_indicators > 0:
        return "markdown"
    return "plain"


def get_packages_with_missing_changelogs(reports: list[PackageReport]) -> list[PackageReport]:
    """Get packages that have missing changelogs."""
    missing_changelogs = []
    for report in reports:
        if (
            report.dependency_change.change_type == ChangeType.UPDATED
            and report.package_info
            and not report.changelog_entries
            and not report.error_message
        ):
            missing_changelogs.append(report)
    return missing_changelogs
