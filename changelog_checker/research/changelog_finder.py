"""
Changelog finder for discovering and parsing changelog files from GitHub repositories.
"""

import contextlib
import io
import logging
import os
import re
import zipfile
from typing import Any

import requests
from distlib.version import NormalizedVersion, UnsupportedVersionError

from changelog_checker.models import ChangelogEntry
from changelog_checker.utils import NetworkError, handle_network_errors
from changelog_checker.version import VERSION

COMMON_FILES = [
    "CHANGELOG",
    "CHANGE_LOG",
    "HISTORY",
    "RELEASES",
    "NEWS",
    "CHANGES",
    "RELEASE-NOTES",
    "RELEASE_NOTES",
]


class ChangelogFinder:
    """Finds and parses changelog files from GitHub repositories."""

    def __init__(self, github_token: str | None = None):
        """
        Initialize the changelog finder.

        Args:
            github_token: Optional GitHub API token for authentication
        """
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": f"changelog-checker/{VERSION} (https://github.com/MrNaif2018/changelog-checker)"}
        )
        if github_token:
            self.session.headers.update({"Authorization": f"token {github_token}"})
        self.logger = logging.getLogger("changelog_checker.changelog_finder")
        self.changelog_paths = []
        for file in COMMON_FILES:
            l_file = file.lower()
            u_file = file.upper()
            self.changelog_paths.extend([f"{l_file}.md", f"{l_file}.rst", f"{l_file}.txt", l_file])
            self.changelog_paths.extend([f"{u_file}.md", f"{u_file}.rst", f"{u_file}.txt", u_file])

    def find_changelog(self, owner: str, repo: str) -> tuple[str | None, str | None]:
        """
        Find changelog file in GitHub repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Tuple of (changelog_url, changelog_content) or (None, None) if not found
        """
        self.logger.debug(f"Trying repository archive download for {owner}/{repo}")
        changelog_url, content = self._fetch_from_repository_archive(owner, repo)
        if content:
            return changelog_url, content
        return None, None

    def find_changelog_entries(
        self, github_url: str, old_version: str, new_version: str
    ) -> tuple[list[ChangelogEntry], str | None]:
        """
        Find and parse changelog entries for version range using the most efficient method.

        Args:
            github_url: GitHub repository URL
            old_version: Starting version (exclusive)
            new_version: Ending version (inclusive)

        Returns:
            Tuple of (List of ChangelogEntry objects, changelog_url) for versions between old and new
        """
        if not github_url or "github.com" not in github_url:
            self.logger.debug(f"Invalid GitHub URL: {github_url}")
            return [], None
        parts = github_url.rstrip("/").split("/")
        if len(parts) < 2:
            self.logger.warning(f"Could not parse GitHub URL: {github_url}")
            return [], None
        owner, repo = parts[-2], parts[-1]
        self.logger.debug(f"Looking for changelog entries in {owner}/{repo} for versions {old_version} to {new_version}")
        self.logger.debug(f"Trying GitHub releases API for {owner}/{repo}")
        entries, releases_url = self._fetch_from_github_releases(owner, repo, old_version, new_version)
        if entries:
            self.logger.debug(f"Found {len(entries)} entries from GitHub releases")
            return entries, releases_url
        self.logger.debug(f"Falling back to changelog file parsing for {owner}/{repo}")
        changelog_url, content = self.find_changelog(owner, repo)
        if content:
            entries = self.parse_changelog(content, old_version, new_version)
            self.logger.debug(f"Found {len(entries)} entries from changelog file")
            return entries, changelog_url
        return [], None

    def _normalize_tag_to_version(self, tag_name: str) -> str:
        """
        Convert a git tag name to a normalized version string.

        Args:
            tag_name: Git tag name (e.g., "v1.2.3", "rel_1_2_3")

        Returns:
            Normalized version string (e.g., "1.2.3")
        """
        version = tag_name.lstrip("v")
        if version.startswith("rel_"):
            version = version[4:].replace("_", ".")
        return version

    def _fetch_all_releases(self, owner: str, repo: str, old_version: str) -> list[dict[str, Any]] | None:
        """
        Fetch releases from GitHub API with pagination support, stopping when old_version is found.

        Args:
            owner: Repository owner
            repo: Repository name
            old_version: Stop fetching when this version is encountered

        Returns:
            List of release dictionaries or None if error occurred
        """
        all_releases = []
        page = 1
        per_page = 40  # for faster responses
        while True:
            api_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
            params = {"page": page, "per_page": per_page}
            self.logger.debug(f"Fetching releases from GitHub API: {api_url} (page {page})")
            response = self.session.get(api_url, params=params, timeout=15)
            if response.status_code == 200:
                pass
            elif response.status_code == 404:
                self.logger.debug(f"Repository not found (404) for {owner}/{repo}")
                return None
            elif response.status_code == 403:
                self.logger.warning(f"GitHub API rate limit or access forbidden (403) for {owner}/{repo}")
                return None
            else:
                self.logger.debug(f"GitHub releases API returned {response.status_code} for {owner}/{repo}")
                return None
            releases = response.json()
            if not releases:
                break
            all_releases.extend(releases)
            will_break = False
            for release in releases:
                tag_name = release.get("tag_name", "")
                version = self._normalize_tag_to_version(tag_name)
                with contextlib.suppress(UnsupportedVersionError):
                    if not will_break and NormalizedVersion(version) <= NormalizedVersion(old_version):
                        self.logger.debug(f"Found old_version {old_version}, stopping pagination")
                        will_break = True
            self.logger.debug(f"Fetched {len(releases)} releases on page {page}, total: {len(all_releases)}")
            if len(releases) < per_page:
                break
            if will_break:
                break
            page += 1
        self.logger.debug(f"Total releases fetched: {len(all_releases)}")
        return all_releases

    @handle_network_errors
    def _fetch_from_github_releases(
        self, owner: str, repo: str, old_version: str, new_version: str
    ) -> tuple[list[ChangelogEntry], str | None]:
        """
        Fetch changelog entries from GitHub releases API and return appropriate URL.

        Args:
            owner: Repository owner
            repo: Repository name
            old_version: Starting version (exclusive)
            new_version: Ending version (inclusive)

        Returns:
            Tuple of (List of ChangelogEntry objects, releases_url)
        """
        try:
            all_releases = self._fetch_all_releases(owner, repo, old_version)
            if all_releases is None:
                return [], None
            entries = []
            for release in all_releases:
                tag_name = release.get("tag_name", "")
                release_body = release.get("body", "") or ""
                version = self._normalize_tag_to_version(tag_name)
                if self._version_in_range(version, old_version, new_version) and release_body.strip():
                    self.logger.debug(f"Found release {version} with changelog content")
                    entries.append(
                        ChangelogEntry(version=version, content=release_body.strip(), date=release.get("published_at"))
                    )
            if entries:
                with contextlib.suppress(Exception):
                    entries.sort(key=lambda entry: NormalizedVersion(entry.version), reverse=True)
                releases_url = f"https://github.com/{owner}/{repo}/releases"
                return entries, releases_url
            return [], None
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"Network error fetching GitHub releases for {owner}/{repo}: {e}")
            raise NetworkError(f"Failed to fetch GitHub releases for {owner}/{repo}") from e
        except Exception as e:
            self.logger.warning(f"Error fetching GitHub releases for {owner}/{repo}: {e}")
            return [], None

    @handle_network_errors
    def _fetch_from_repository_archive(self, owner: str, repo: str) -> tuple[str | None, str | None]:
        """
        Download repository archive and search for changelog files locally.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Tuple of (changelog_url, changelog_content) or (None, None) if not found
        """
        try:
            archive_url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
            self.logger.debug(f"Downloading repository archive from {archive_url}")
            response = self.session.get(archive_url, timeout=30)
            if response.status_code == 200:
                pass
            elif response.status_code == 404:
                self.logger.debug(f"Branch not found (404) for {owner}/{repo}")
                return None, None
            elif response.status_code == 403:
                self.logger.warning(f"GitHub API rate limit or access forbidden (403) for {owner}/{repo}")
                return None, None
            else:
                self.logger.debug(f"Archive download failed with status {response.status_code}")
                return None, None
            changelog_url, content = self._search_archive_for_changelog(response.content, owner, repo)
            if content:
                return changelog_url, content
            return None, None
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"Network error downloading repository archive for {owner}/{repo}: {e}")
            raise NetworkError(f"Failed to download repository archive for {owner}/{repo}") from e
        except Exception as e:
            self.logger.warning(f"Error downloading repository archive for {owner}/{repo}: {e}")
            return None, None

    def _search_archive_for_changelog(self, archive_data: bytes, owner: str, repo: str) -> tuple[str | None, str | None]:
        """
        Search extracted archive for changelog files by examining all files in the archive.

        Args:
            archive_data: Raw zip archive data
            owner: Repository owner
            repo: Repository name

        Returns:
            Tuple of (changelog_url, changelog_content) or (None, None) if not found
        """
        try:
            with zipfile.ZipFile(io.BytesIO(archive_data)) as zip_file:
                file_list = zip_file.namelist()
                potential_files = []
                for file_path in file_list:
                    if file_path.endswith("/"):
                        continue
                    filename = os.path.basename(file_path).lower()
                    for changelog_path in self.changelog_paths:
                        if filename == changelog_path.lower():
                            potential_files.append(file_path)
                            break

                def file_priority(file_path: str) -> int:
                    filename = os.path.basename(file_path).lower()
                    depth = len([p for p in file_path.split("/") if p]) - 1
                    priority = depth * 100
                    for i, changelog_path in enumerate(self.changelog_paths):
                        if filename == changelog_path.lower():
                            priority += i
                            break
                    return priority

                potential_files.sort(key=file_priority)
                for file_path in potential_files:
                    relative_path = "/".join(file_path.split("/")[1:]) if "/" in file_path else file_path
                    self.logger.debug(f"Found changelog file in archive: {file_path}")
                    try:
                        with zip_file.open(file_path) as changelog_file:
                            content = changelog_file.read().decode("utf-8", errors="ignore")
                        changelog_url = f"https://github.com/{owner}/{repo}/blob/HEAD/{relative_path}"
                        return changelog_url, content
                    except Exception as e:
                        self.logger.warning(f"Error reading file {file_path} from archive: {e}")
                        continue
                return None, None
        except zipfile.BadZipFile:
            self.logger.warning(f"Invalid zip archive received for {owner}/{repo}")
            return None, None
        except Exception as e:
            self.logger.warning(f"Error searching archive for {owner}/{repo}: {e}")
            return None, None

    def parse_changelog(self, content: str, old_version: str, new_version: str) -> list[ChangelogEntry]:
        """
        Parse changelog content to extract entries between versions.

        Args:
            content: Raw changelog content
            old_version: Starting version (exclusive)
            new_version: Ending version (inclusive)

        Returns:
            List of ChangelogEntry objects for versions between old and new
        """
        self.logger.debug(f"Parsing changelog for versions {old_version} to {new_version}")
        entries = []
        lines = content.split("\n")
        current_content: list[str] = []
        versions_in_current_section: list[str] = []
        for line in lines:
            version_found = self._extract_version_from_line(line.strip())
            if version_found:
                if versions_in_current_section and current_content:
                    content_str = "\n".join(current_content).strip()
                    for version in versions_in_current_section:
                        entries.append(ChangelogEntry(version=version, content=content_str))
                    versions_in_current_section = []
                    current_content = []
                if self._version_in_range(version_found, old_version, new_version):
                    versions_in_current_section.append(version_found)
                if version_found == old_version:
                    break
            elif versions_in_current_section:
                stripped_line = line.strip()
                if not (stripped_line and len(set(stripped_line)) == 1 and stripped_line[0] in "-~=^#"):
                    current_content.append(line)
        if versions_in_current_section:
            content_str = "\n".join(current_content).strip()
            for version in versions_in_current_section:
                entries.append(ChangelogEntry(version=version, content=content_str))
        with contextlib.suppress(Exception):
            entries.sort(key=lambda entry: NormalizedVersion(entry.version), reverse=True)
        return entries

    def _extract_version_from_line(self, line: str) -> str | None:
        """
        Extract version string from a changelog line

        Args:
            line: A single line from the changelog

        Returns:
            Normalized version string if found and valid, None otherwise
        """
        if not line:
            return None
        version_patterns = [
            # Markdown headers: ## Version 1.2.3 or ## v1.2.3
            r"^#+\s*(?:Version\s+)?v?(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)",
            # Bold versions: **1.2.3**
            r"^\*\*v?(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)\*\*",
            # Bracketed versions: [1.2.3] or [v1.2.3]
            r"^\[v?(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)\]",
            # Package name with version and optional date: "ecdsa 0.19.1", "ecdsa v0.19.1", "H11 0.16.0 (2025-04-23)"
            r"^[\w\-_]+\s+v?(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)(?:\s*\([^)]+\))?",
            # Simple version with optional date: "v1.2.3 (2025-04-14)"
            # or "1.2.3 (2025-04-14)" or "1.2.3" or "8.2 (01 May 2025)"
            r"^v?(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)(?:\s*\([^)]+\)|\s*[-:]|$)",
            # Sphinx release format: - :release:`3.4.1 <2024-08-11>`
            r"^-\s*:release:`v?(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)",
            # * Release 0.19.1 (13 Mar 2025)
            r"^\*?\s*Release\s+v?(\d+\.\d+(?:\.\d+)?(?:\.\d+)?(?:[ab]\d+|\.dev\d*|\.post\d+)?)",
        ]
        for pattern in version_patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                try:
                    NormalizedVersion(match)
                    return match
                except Exception:
                    self.logger.debug(f"Trying version pattern {pattern} on line {line}, but failed to parse version {match}")
                    continue
        return None

    def _version_in_range(self, version: str, old_version: str, new_version: str) -> bool:
        """Check if version is between old_version (exclusive) and new_version (inclusive)."""
        try:
            v1 = NormalizedVersion(old_version)
            v2 = NormalizedVersion(new_version)
            v3 = NormalizedVersion(version)
            return v1 < v3 and v3 <= v2
        except Exception:
            return False
