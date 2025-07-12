from unittest.mock import Mock, patch

import requests

from changelog_checker.research.package_finder import PackageFinder


class TestPackageFinder:
    def setup_method(self):
        self.finder = PackageFinder()

    def test_init(self):
        finder = PackageFinder()
        assert finder.session is not None
        assert "changelog-checker" in finder.session.headers["User-Agent"]

    @patch("requests.Session.get")
    def test_find_package_info_success(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "info": {
                "project_urls": {
                    "Homepage": "https://github.com/user/requests",
                    "Repository": "https://github.com/user/requests",
                }
            }
        }
        mock_get.return_value = mock_response
        package_info = self.finder.find_package_info("requests")
        assert package_info.name == "requests"
        assert package_info.pypi_url == "https://pypi.org/project/requests/"
        assert package_info.github_url == "https://github.com/user/requests"
        mock_get.assert_called_once_with("https://pypi.org/pypi/requests/json", timeout=10)

    @patch("changelog_checker.research.package_finder.google_search")
    @patch("requests.Session.get")
    def test_find_package_info_no_github_link(self, mock_get, mock_google_search):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"info": {"project_urls": {"Homepage": "https://example.com"}}}
        mock_get.return_value = mock_response
        mock_google_search.return_value = []
        package_info = self.finder.find_package_info("some-package")
        assert package_info.name == "some-package"
        assert package_info.pypi_url == "https://pypi.org/project/some-package/"
        assert package_info.github_url is None

    @patch("changelog_checker.research.package_finder.google_search")
    @patch("requests.Session.get")
    def test_find_package_info_network_error(self, mock_get, mock_google_search):
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")
        mock_google_search.return_value = []
        package_info = self.finder.find_package_info("test-package")
        assert package_info.name == "test-package"
        assert package_info.pypi_url == "https://pypi.org/project/test-package/"
        assert package_info.github_url is None

    @patch("requests.Session.get")
    def test_find_github_from_pypi_various_project_urls(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"info": {"project_urls": {"Repository": "https://github.com/example/repo"}}}
        mock_get.return_value = mock_response
        package_info = self.finder.find_package_info("example-package")
        assert package_info.github_url == "https://github.com/example/repo"

    @patch("requests.Session.get")
    def test_find_github_from_pypi_fallback_fields(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "info": {"project_urls": {}, "home_page": "https://github.com/example/fallback-repo"}
        }
        mock_get.return_value = mock_response
        package_info = self.finder.find_package_info("fallback-package")
        assert package_info.github_url == "https://github.com/example/fallback-repo"

    def test_clean_github_url_reserved_names(self):
        result = self.finder._clean_github_url("https://github.com/api/some-repo")
        assert result is None
        result = self.finder._clean_github_url("https://github.com/admin/another-repo")
        assert result is None
        result = self.finder._clean_github_url("https://github.com/validuser/repo")
        assert result == "https://github.com/validuser/repo"

    def test_clean_github_url_case_insensitive_reserved_names(self):
        result = self.finder._clean_github_url("https://github.com/API/some-repo")
        assert result is None
        result = self.finder._clean_github_url("https://github.com/Admin/another-repo")
        assert result is None
