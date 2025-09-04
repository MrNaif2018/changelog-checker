"""
Parsers for different package manager outputs.
"""

from .base import BaseParser
from .pip_parser import PipParser
from .uv_parser import UVParser

__all__ = ["BaseParser", "UVParser", "PipParser"]
