"""
Package finder for discovering GitHub repositories from PyPI packages.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from googlesearch import search as google_search

from changelog_checker.models import PackageInfo
from changelog_checker.utils import NetworkError, handle_network_errors
from changelog_checker.version import VERSION


class PackageFinder:
    """Finds GitHub repositories for PyPI packages."""

    def __init__(self) -> None:
        """
        Initialize the package finder.

        """
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": f"changelog-checker/{VERSION} (https://github.com/user/changelog-checker)"})
        self.logger = logging.getLogger("changelog_checker.package_finder")
        self._reserved_names = self._load_reserved_names()

    def _load_reserved_names(self) -> set[str]:
        """Load GitHub reserved names from data file."""
        try:
            data_file = Path(__file__).parent.parent / "data" / "reserved-names.json"
            with data_file.open() as f:
                return set(json.load(f))
        except Exception as e:
            self.logger.warning(f"Failed to load reserved names: {e}")
            return set()

    def find_package_info(self, package_name: str) -> PackageInfo:
        """
        Find GitHub repository and other info for a PyPI package.

        Args:
            package_name: Name of the PyPI package

        Returns:
            PackageInfo object with discovered information
        """
        self.logger.debug(f"Finding package info for {package_name}")
        package_info = PackageInfo(name=package_name, pypi_url=f"https://pypi.org/project/{package_name}/")
        try:
            github_url = self._find_github_from_pypi(package_name)
            if github_url:
                self.logger.debug(f"Found GitHub URL from PyPI for {package_name}: {github_url}")
                package_info.github_url = github_url
            else:
                self.logger.debug(f"No GitHub URL found on PyPI for {package_name}, trying fallback")
                github_url = self._find_github_from_google(package_name)
                if github_url:
                    self.logger.debug(f"Found GitHub URL from Google for {package_name}: {github_url}")
                    package_info.github_url = github_url
                else:
                    self.logger.debug(f"No GitHub URL found for {package_name}")
        except Exception as e:
            self.logger.warning(f"Error finding package info for {package_name}: {e}")
        return package_info

    @handle_network_errors
    def _find_github_from_pypi(self, package_name: str) -> str | None:
        """Find GitHub URL from PyPI JSON API."""
        try:
            self.logger.debug(f"Fetching PyPI JSON API data for {package_name}")
            pypi_json_url = f"https://pypi.org/pypi/{package_name}/json"
            response = self.session.get(pypi_json_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.logger.debug(f"Successfully fetched PyPI JSON data for {package_name}")
            info = data.get("info", {})
            github_url = (
                self._find_github_in_project_urls(info, package_name)
                or self._find_github_in_info_fields(info, package_name)
                or self._find_github_in_description(info, package_name)
            )
            if not github_url:
                self.logger.debug(f"No GitHub URL found in PyPI JSON data for {package_name}")
            return github_url
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Network error fetching PyPI JSON API for {package_name}: {e}")
            raise NetworkError(f"Failed to fetch PyPI JSON API for {package_name}") from e
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error parsing PyPI JSON data for {package_name}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error processing PyPI JSON data for {package_name}: {e}")
        return None

    def _find_github_in_project_urls(self, info: dict[str, Any], package_name: str) -> str | None:
        """Find GitHub URL in project_urls section."""
        project_urls = info.get("project_urls", {})
        if not project_urls:
            return None
        self.logger.debug(f"Found project_urls for {package_name}: {list(project_urls.keys())}")
        for key, url in project_urls.items():
            if url and "github.com" in url.lower():
                self.logger.debug(f"Found GitHub URL in project_urls[{key}] for {package_name}: {url}")
                github_url = self._clean_github_url(url)
                if github_url:
                    return github_url
        return None

    def _find_github_in_info_fields(self, info: dict[str, Any], package_name: str) -> str | None:
        """Find GitHub URL in standard info fields."""
        fields_to_check = ["home_page", "download_url"]
        for field in fields_to_check:
            value = info.get(field)
            if value and "github.com" in value.lower():
                self.logger.debug(f"Found GitHub URL in {field} for {package_name}: {value}")
                github_url = self._clean_github_url(value)
                if github_url:
                    return github_url
        return None

    def _find_github_in_description(self, info: dict[str, Any], package_name: str) -> str | None:
        """Find GitHub URL in package description using regex patterns."""
        description = info.get("description", "")
        if not description or "github.com" not in description.lower():
            return None
        github_patterns = [
            r"https://github\.com/[^/\s]+/[^/\s]+",
            r"https://www\.github\.com/[^/\s]+/[^/\s]+",
        ]
        for pattern in github_patterns:
            matches = re.findall(pattern, description)
            if matches:
                self.logger.debug(f"Found GitHub URL in description for {package_name}: {matches[0]}")
                github_url = self._clean_github_url(matches[0])
                if github_url:
                    return github_url
        return None

    @handle_network_errors
    def _find_github_from_google(self, package_name: str) -> str | None:
        """Find GitHub URL using Google search as fallback method."""
        try:
            self.logger.debug(f"Searching Google for GitHub repository for {package_name}")
            search_query = f"{package_name} site:github.com"
            results = list(google_search(search_query, num_results=3))
            self.logger.debug(f"Google search returned {len(results)} results for {package_name}")
            if results:
                for i, result in enumerate(results):
                    self.logger.debug(f"Checking Google result {i + 1} for {package_name}: {result}")
                    github_url = self._clean_github_url(result)
                    if github_url:
                        self.logger.debug(f"Found valid GitHub URL from Google for {package_name}: {github_url}")
                        return github_url
                self.logger.debug(f"No valid GitHub URLs found in Google results for {package_name}")
            else:
                self.logger.debug(f"No Google search results found for {package_name}")
            return None
        except ImportError as e:
            self.logger.warning(f"Google search not available (googlesearch package issue): {e}")
            return None
        except Exception as e:
            self.logger.warning(f"Error during Google search for {package_name}: {e}")
            return None

    def _clean_github_url(self, url: str) -> str | None:
        """Clean and validate GitHub URL."""
        try:
            parsed = urlparse(url)
            if "github.com" not in parsed.netloc:
                return None
            path_parts = [p for p in parsed.path.split("/") if p]
            if len(path_parts) >= 2:
                owner, repo = path_parts[0], path_parts[1]
                if owner.lower() in self._reserved_names:
                    self.logger.debug(f"Skipping GitHub URL with reserved owner '{owner}': {url}")
                    return None
                if repo.endswith(".git"):
                    repo = repo[:-4]
                return f"https://github.com/{owner}/{repo}"
        except Exception:
            self.logger.warning(f"Error parsing GitHub URL: {url}")
        return None
