"""
Parsers for different package manager outputs.
"""

from .base import BaseParser
from .uv_parser import UVParser
from .pip_parser import PipParser

__all__ = ["BaseParser", "UVParser", "PipParser"]
