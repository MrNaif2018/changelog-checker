"""
Changelog Checker - A tool for analyzing dependency updates and their changelogs.
"""

from .core import ChangelogChecker
from .output import RichFormatter
from .research import ChangelogFinder, PackageFinder
from .version import VERSION

__version__ = VERSION

__all__ = ["ChangelogChecker", "ChangelogFinder", "PackageFinder", "RichFormatter"]
