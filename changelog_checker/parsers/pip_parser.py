"""
Parser for pip package manager output.
"""

from changelog_checker.models import ChangeType, DependencyChange

from .base import BaseParser


class PipParser(BaseParser):
    """Parser for (uv) pip list --outdated output."""

    def get_package_manager_name(self) -> str:
        return "pip"

    def validate_output(self, output: str) -> bool:
        """Check if output looks like pip list --outdated output."""
        if output == "":  # empty output indicates no updates found
            return True
        pip_header = ["Package", "Version", "Latest", "Type"]
        lines = output.split("\n")
        words = lines[0].split()
        return words == pip_header

    def parse(self, output: str) -> list[DependencyChange]:
        """
        Parse (uv) pip list --outdated output to extract dependency changes.

        Expected format:
        package     old_version     new_version     type
        """
        changes = []
        lines = output.strip().split("\n")
        for line in lines[2:]:
            words = line.split()
            package_name = words[0]
            old_version = words[1]
            new_version = words[2]
            changes.append(
                DependencyChange(
                    name=package_name, change_type=ChangeType.UPDATED, old_version=old_version, new_version=new_version
                )
            )
        return changes
