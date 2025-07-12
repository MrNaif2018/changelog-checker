"""
Parser for UV package manager output.
"""

import re

from changelog_checker.models import ChangeType, DependencyChange

from .base import BaseParser


class UVParser(BaseParser):
    """Parser for UV sync -U output."""

    def get_package_manager_name(self) -> str:
        return "uv"

    def validate_output(self, output: str) -> bool:
        """Check if output looks like UV sync output."""
        uv_indicators = ["Resolved", "packages in", "Prepared", "Installed", "Uninstalled"]
        return any(indicator in output for indicator in uv_indicators)

    def parse(self, output: str) -> list[DependencyChange]:
        """
        Parse UV sync -U output to extract dependency changes.

        Expected format:
        - package==old_version
        + package==new_version

        Or for new packages:
        + package==version

        Or for removed packages:
        - package==version
        """
        changes = []
        lines = output.strip().split("\n")
        removed_packages = {}
        added_packages = {}
        package_order = []
        for line in lines:
            line = line.strip()
            if line.startswith("- "):
                match = re.match(r"- ([^=]+)==(.+)", line)
                if match:
                    package_name, version = match.groups()
                    removed_packages[package_name] = version
                    if package_name not in package_order:
                        package_order.append(package_name)
            elif line.startswith("+ "):
                match = re.match(r"\+ ([^=]+)==(.+)", line)
                if match:
                    package_name, version = match.groups()
                    added_packages[package_name] = version
                    if package_name not in package_order:
                        package_order.append(package_name)
        for package_name in package_order:
            old_version = removed_packages.get(package_name)
            new_version = added_packages.get(package_name)
            if old_version and new_version:
                changes.append(
                    DependencyChange(
                        name=package_name, change_type=ChangeType.UPDATED, old_version=old_version, new_version=new_version
                    )
                )
            elif new_version and not old_version:
                changes.append(DependencyChange(name=package_name, change_type=ChangeType.ADDED, new_version=new_version))
            elif old_version and not new_version:
                changes.append(DependencyChange(name=package_name, change_type=ChangeType.REMOVED, old_version=old_version))
        return changes
