from unittest.mock import Mock, patch

from click.testing import CliRunner

from changelog_checker.cli import main
from changelog_checker.models import (
    ChangelogEntry,
    ChangeType,
    DependencyChange,
    PackageInfo,
)


class TestCLI:
    def setup_method(self):
        self.runner = CliRunner()

    def test_main_help(self):
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Changelog Checker" in result.output
        assert "--input-file" in result.output
        assert "--parser" in result.output

    @patch("changelog_checker.core.UVParser")
    @patch("changelog_checker.core.PackageFinder")
    @patch("changelog_checker.core.ChangelogFinder")
    @patch("changelog_checker.core.RichFormatter")
    def test_main_with_input_file(self, mock_formatter, mock_changelog_finder, mock_package_finder, mock_parser):
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        mock_parser_instance.validate_output.return_value = True
        mock_parser_instance.parse.return_value = [
            DependencyChange(
                name="requests",
                change_type=ChangeType.UPDATED,
                old_version="2.28.0",
                new_version="2.29.0",
            )
        ]
        mock_package_finder_instance = Mock()
        mock_package_finder.return_value = mock_package_finder_instance
        mock_package_finder_instance.find_package_info.return_value = PackageInfo(
            name="requests", github_url="https://github.com/user/requests"
        )
        mock_changelog_finder_instance = Mock()
        mock_changelog_finder.return_value = mock_changelog_finder_instance
        mock_changelog_finder_instance.find_changelog_entries.return_value = (
            [ChangelogEntry(version="2.29.0", content="Bug fixes")],
            "https://github.com/user/requests/blob/HEAD/CHANGELOG.md",
        )
        mock_formatter_instance = Mock()
        mock_formatter.return_value = mock_formatter_instance
        with self.runner.isolated_filesystem():
            with open("input.txt", "w") as f:
                f.write("- requests==2.28.0\n+ requests==2.29.0\n")
            result = self.runner.invoke(main, ["--input-file", "input.txt"])
            assert result.exit_code == 0
            mock_parser_instance.parse.assert_called_once()
            mock_package_finder_instance.find_package_info.assert_called_once_with("requests")
            mock_formatter_instance.display_results.assert_called_once()

    @patch("changelog_checker.core.UVParser")
    def test_main_with_stdin(self, mock_parser):
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        mock_parser_instance.validate_output.return_value = True
        mock_parser_instance.parse.return_value = []
        input_data = "- requests==2.28.0\n+ requests==2.29.0\n"
        result = self.runner.invoke(main, input=input_data)
        assert result.exit_code == 0
        mock_parser_instance.parse.assert_called_once_with(input_data)

    def test_main_no_input(self):
        result = self.runner.invoke(main)
        assert result.exit_code != 0
        assert "Empty input provided" in result.output

    @patch("changelog_checker.core.UVParser")
    def test_main_invalid_parser_output(self, mock_parser):
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        mock_parser_instance.validate_output.return_value = False
        input_data = "invalid output"
        result = self.runner.invoke(main, input=input_data)
        assert result.exit_code != 0
        assert "doesn't appear to be from" in result.output

    @patch("changelog_checker.core.UVParser")
    @patch("changelog_checker.core.PackageFinder")
    @patch("changelog_checker.core.ChangelogFinder")
    @patch("changelog_checker.core.RichFormatter")
    def test_main_error_handling(self, mock_formatter, mock_changelog_finder, mock_package_finder, mock_parser):
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        mock_parser_instance.validate_output.return_value = True
        mock_parser_instance.parse.side_effect = Exception("Test error")
        input_data = "- requests==2.28.0\n+ requests==2.29.0\n"
        result = self.runner.invoke(main, input=input_data)
        assert result.exit_code != 0
        assert "Failed to check dependencies" in result.output

    def test_main_file_not_found(self):
        result = self.runner.invoke(main, ["--input-file", "nonexistent.txt"])
        assert result.exit_code != 0
        assert "No such file" in result.output
