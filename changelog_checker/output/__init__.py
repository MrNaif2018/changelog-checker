"""
Output formatters for displaying results.
"""

from .html_formatter import HTMLFormatter
from .rich_formatter import RichFormatter

__all__ = ["RichFormatter", "HTMLFormatter"]
