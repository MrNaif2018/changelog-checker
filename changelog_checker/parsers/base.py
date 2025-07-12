"""
Base parser class for different package managers.
"""

from abc import ABC, abstractmethod

from changelog_checker.models import DependencyChange


class BaseParser(ABC):
    """Abstract base class for package manager output parsers."""

    @abstractmethod
    def parse(self, output: str) -> list[DependencyChange]:
        """
        Parse package manager output and return list of dependency changes.

        Args:
            output: Raw output from package manager command

        Returns:
            List of DependencyChange objects
        """
        pass

    @abstractmethod
    def get_package_manager_name(self) -> str:
        """Return the name of the package manager this parser handles."""
        pass

    def validate_output(self, output: str) -> bool:
        """
        Validate that the output is from the expected package manager.

        Args:
            output: Raw output to validate

        Returns:
            True if output appears to be from this package manager
        """
        return True
