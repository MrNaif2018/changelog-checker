"""
Data models for the changelog checker.
"""

from dataclasses import dataclass
from enum import Enum


class ChangeType(Enum):
    """Type of dependency change."""

    UPDATED = "updated"
    ADDED = "added"
    REMOVED = "removed"


@dataclass
class DependencyChange:
    """Represents a change in a dependency."""

    name: str
    change_type: ChangeType
    old_version: str | None = None
    new_version: str | None = None

    def __str__(self) -> str:
        if self.change_type == ChangeType.UPDATED:
            return f"{self.name}: {self.old_version} -> {self.new_version}"
        if self.change_type == ChangeType.ADDED:
            return f"{self.name}: added {self.new_version}"
        if self.change_type == ChangeType.REMOVED:
            return f"{self.name}: removed {self.old_version}"


@dataclass
class PackageInfo:
    """Information about a package."""

    name: str
    github_url: str | None = None
    pypi_url: str | None = None
    changelog_url: str | None = None
    changelog_found: bool = False


@dataclass
class ChangelogEntry:
    """A single changelog entry."""

    version: str
    content: str
    date: str | None = None


@dataclass
class PackageReport:
    """Complete report for a single package."""

    dependency_change: DependencyChange
    package_info: PackageInfo | None
    changelog_entries: list[ChangelogEntry]
    error_message: str | None = None
