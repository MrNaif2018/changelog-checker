"""
Core application logic for the changelog checker.
"""

import logging

from .models import ChangeType, DependencyChange, PackageReport
from .output import RichFormatter
from .parsers import UVParser
from .research import ChangelogFinder, PackageFinder
from .utils import ChangelogCheckerError, NetworkError, ParserError


class ChangelogChecker:
    """Main application class that orchestrates all components."""

    def __init__(self, github_token: str | None = None):
        """
        Initialize the changelog checker.

        Args:
            github_token: Optional GitHub API token.
        """
        self.logger = logging.getLogger("changelog_checker")
        self.formatter = RichFormatter()
        self.package_finder = PackageFinder()
        if github_token:
            self.logger.debug("Using GitHub API token for authentication")
        else:
            self.logger.debug("No GitHub API token provided - using unauthenticated requests")
        self.changelog_finder = ChangelogFinder(github_token=github_token)

    def check_dependencies(self, input_text: str, parser_type: str = "uv") -> list[PackageReport]:
        """
        Check dependencies and generate reports.

        Args:
            input_text: Raw output from package manager
            parser_type: Type of parser to use ("uv", etc.)

        Returns:
            List of PackageReport objects
        """
        try:
            if parser_type == "uv":
                parser = UVParser()
            else:
                raise ParserError(f"Unsupported parser type: {parser_type}")
            if not parser.validate_output(input_text):
                raise ParserError(f"Input doesn't appear to be from {parser.get_package_manager_name()}")
            self.logger.info(f"Using {parser.get_package_manager_name()} parser")
            dependency_changes = parser.parse(input_text)
            if not dependency_changes:
                self.logger.info("No dependency changes found")
                return []
            self.logger.info(f"Found {len(dependency_changes)} dependency changes")
            self.formatter.display_progress(f"Found {len(dependency_changes)} dependency changes")
            reports = []
            for i, change in enumerate(dependency_changes, 1):
                self.formatter.display_progress(f"Processing {change.name} ({i}/{len(dependency_changes)})...")
                try:
                    report = self._generate_package_report(change)
                    reports.append(report)
                except Exception as e:
                    self.logger.error(f"Failed to process {change.name}: {e}")
                    error_report = PackageReport(
                        dependency_change=change,
                        package_info=None,
                        changelog_entries=[],
                        error_message=str(e),
                    )
                    reports.append(error_report)
            return reports
        except ParserError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in check_dependencies: {e}")
            raise ChangelogCheckerError(f"Failed to check dependencies: {e}") from e

    def _generate_package_report(self, change: DependencyChange) -> PackageReport:
        """Generate a complete report for a single package."""
        report = PackageReport(
            dependency_change=change,
            package_info=None,
            changelog_entries=[],
            error_message=None,
        )
        try:
            self.logger.debug(f"Finding package info for {change.name}")
            package_info = self.package_finder.find_package_info(change.name)
            report.package_info = package_info
            if not package_info:
                self.logger.warning(f"No package info found for {change.name}")
                return report
            if (
                package_info.github_url
                and change.change_type == ChangeType.UPDATED
                and change.old_version
                and change.new_version
            ):
                self.logger.debug(f"Looking for changelog for {change.name} at {package_info.github_url}")
                try:
                    entries, changelog_url = self.changelog_finder.find_changelog_entries(
                        package_info.github_url, change.old_version, change.new_version
                    )
                    if entries:
                        package_info.changelog_found = True
                        report.changelog_entries = entries
                        if changelog_url:
                            package_info.changelog_url = changelog_url
                        self.logger.debug(f"Found {len(entries)} changelog entries for {change.name}")
                    else:
                        self.logger.debug(f"No changelog content found for {change.name}")
                except NetworkError as e:
                    self.logger.warning(f"Network error while fetching changelog for {change.name}: {e}")
                    report.error_message = f"Network error: {e}"
                except Exception as e:
                    self.logger.error(f"Error processing changelog for {change.name}: {e}")
                    report.error_message = f"Changelog error: {e}"
        except NetworkError as e:
            self.logger.warning(f"Network error while processing {change.name}: {e}")
            report.error_message = f"Network error: {e}"
        except Exception as e:
            self.logger.error(f"Unexpected error processing {change.name}: {e}")
            report.error_message = f"Processing error: {e}"
        return report
