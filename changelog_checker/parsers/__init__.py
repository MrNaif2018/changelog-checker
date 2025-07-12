"""
Parsers for different package manager outputs.
"""

from .base import BaseParser
from .uv_parser import UVParser

__all__ = ["BaseParser", "UVParser"]
