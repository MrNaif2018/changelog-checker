from unittest.mock import patch

from changelog_checker.research.changelog_finder import ChangelogFinder


class TestChangelogFinder:
    def setup_method(self):
        self.finder = ChangelogFinder()

    def test_init(self):
        finder = ChangelogFinder()
        assert finder.session is not None

    @patch("changelog_checker.research.changelog_finder.ChangelogFinder._fetch_from_repository_archive")
    def test_find_changelog_success(self, mock_fetch):
        mock_content = """
        # Changelog

        ## [1.2.0] - 2023-12-01
        - Added new feature
        - Fixed bug

        ## [1.1.0] - 2023-11-01
        - Initial release
        """
        mock_fetch.return_value = ("https://github.com/user/repo/blob/HEAD/CHANGELOG.md", mock_content)
        changelog_url, content = self.finder.find_changelog("user", "repo")
        assert changelog_url is not None
        assert content is not None
        assert "1.2.0" in content
        assert "Added new feature" in content

    def test_find_changelog_no_github_url(self):
        changelog_url, content = self.finder.find_changelog("", "")
        assert changelog_url is None
        assert content is None

    @patch("changelog_checker.research.changelog_finder.ChangelogFinder._fetch_from_repository_archive")
    def test_find_changelog_not_found(self, mock_fetch):
        mock_fetch.return_value = (None, None)
        changelog_url, content = self.finder.find_changelog("user", "repo")
        assert changelog_url is None
        assert content is None

    def test_invalid_github_url(self):
        changelog_url, content = self.finder.find_changelog("", "repo")
        assert changelog_url is None
        assert content is None

    def test_malformed_github_url(self):
        changelog_url, content = self.finder.find_changelog("user", "")
        assert changelog_url is None
        assert content is None

    def test_version_in_range(self):
        assert self.finder._version_in_range("1.4.0", "1.3.2", "1.4.0") is True
        assert self.finder._version_in_range("1.3.5", "1.3.2", "1.4.0") is True
        assert self.finder._version_in_range("1.3.0", "1.3.2", "1.4.0") is False
        assert self.finder._version_in_range("1.5.0", "1.3.2", "1.4.0") is False
        assert self.finder._version_in_range("1.4.0a0", "1.3.2", "1.5.0") is True
        assert self.finder._version_in_range("1.3.5a0", "1.3.2", "1.4.0") is True
        assert self.finder._version_in_range("1.0.0a0", "1.3.2", "1.4.0") is False
        assert self.finder._version_in_range("2.0.0b1", "1.3.2", "1.4.0") is False
        assert self.finder._version_in_range("invalid-version", "1.3.2", "1.4.0") is False
