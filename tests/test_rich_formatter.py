from unittest.mock import Mock, patch

from changelog_checker.models import (
    ChangelogEntry,
    ChangeType,
    DependencyChange,
    PackageInfo,
    PackageReport,
)
from changelog_checker.output.rich_formatter import RichFormatter


class TestRichFormatter:
    def setup_method(self):
        self.formatter = RichFormatter()

    def test_detect_content_format_markdown(self):
        markdown_content = """
# Version 1.2.3

## Features
- Added new feature
- **Bold text** support

## Bug Fixes
- Fixed issue with [links](http://example.com)

```python
def example():
    pass
```
"""
        format_type = self.formatter._detect_content_format(markdown_content)
        assert format_type == "markdown"

    def test_detect_content_format_rst(self):
        rst_content = """
Release Notes
=============

package-name v1.2.3 (2024-01-15)
---------------------------------

Features
~~~~~~~~

- Added new feature
- Another feature

Bug Fixes
~~~~~~~~~

- Fixed issue
"""
        format_type = self.formatter._detect_content_format(rst_content)
        assert format_type == "rst"

    def test_detect_content_format_plain(self):
        plain_content = """
Version 1.2.3
Added new feature
Fixed bug
Updated documentation
"""
        format_type = self.formatter._detect_content_format(plain_content)
        assert format_type == "plain"

    def test_format_as_plain_text(self):
        content = """
# Header
- List item 1
- List item 2
* Another list item
+ Plus list item
Regular text
"""
        result = self.formatter._format_as_plain_text(content)
        lines = result.split("\n")
        assert lines == [
            "[bold]# Header[/bold]",
            "  - List item 1",
            "  - List item 2",
            "  * Another list item",
            "  + Plus list item",
            "  Regular text",
        ]

    @patch("changelog_checker.output.rich_formatter.HAS_RST_SUPPORT", True)
    def test_format_changelog_content_rst_with_support(self):
        rst_content = """
package v1.2.3 (2024-01-15)
---------------------------

Features
~~~~~~~~

- New feature
"""
        with patch("changelog_checker.output.rich_formatter.RestructuredText") as mock_rst:
            mock_rst.return_value = Mock()
            with patch("changelog_checker.output.rich_formatter.Console") as mock_console:
                mock_capture = Mock()
                mock_capture.get.return_value = "Formatted RST content"
                mock_console.return_value.capture.return_value.__enter__.return_value = mock_capture
                result = self.formatter._format_changelog_content(rst_content)
                assert result == "Formatted RST content"

    @patch("changelog_checker.output.rich_formatter.HAS_RST_SUPPORT", False)
    def test_format_changelog_content_rst_without_support(self):
        rst_content = """
package v1.2.3 (2024-01-15)
---------------------------

Features
~~~~~~~~

- New feature
"""
        result = self.formatter._format_changelog_content(rst_content)
        assert "- New feature" in result

    def test_format_changelog_content_markdown(self):
        markdown_content = """
# Version 1.2.3

## Features
- New feature
- **Bold feature**
"""
        with patch("changelog_checker.output.rich_formatter.Markdown") as mock_md:
            mock_md.return_value = Mock()
            with patch("changelog_checker.output.rich_formatter.Console") as mock_console:
                mock_capture = Mock()
                mock_capture.get.return_value = "Formatted markdown content"
                mock_console.return_value.capture.return_value.__enter__.return_value = mock_capture
                result = self.formatter._format_changelog_content(markdown_content)
                assert result == "Formatted markdown content"

    def test_format_changelog_content_empty(self):
        result = self.formatter._format_changelog_content("")
        assert result == "[dim]No changelog content found[/dim]"
        result = self.formatter._format_changelog_content("   \n  \n  ")
        assert result == "[dim]No changelog content found[/dim]"

    def test_format_changelog_content_fallback_on_error(self):
        markdown_content = "# Header\n- List item"
        with patch("changelog_checker.output.rich_formatter.Markdown") as mock_md:
            mock_md.side_effect = Exception("Rendering error")
            result = self.formatter._format_changelog_content(markdown_content)
            assert "[bold]# Header[/bold]" in result
            assert "  - List item" in result

    def test_display_results_empty(self):
        with patch.object(self.formatter.console, "print") as mock_print:
            self.formatter.display_results([])
            calls = [str(call) for call in mock_print.call_args_list]
            assert any("No dependency changes found" in call for call in calls)

    def test_display_package_report_with_changelog(self):
        change = DependencyChange(name="requests", change_type=ChangeType.UPDATED, old_version="2.28.0", new_version="2.29.0")
        info = PackageInfo(name="requests", github_url="https://github.com/user/requests")
        entries = [ChangelogEntry(version="2.29.0", content="- Fixed bug\n- Added feature")]
        report = PackageReport(dependency_change=change, package_info=info, changelog_entries=entries)
        with patch.object(self.formatter.console, "print") as mock_print:
            self.formatter._display_package_report(report)
            mock_print.assert_called()
            panel_call = mock_print.call_args_list[0]
            panel = panel_call[0][0]
            assert "Version 2.29.0" in str(panel.renderable)

    def test_display_package_report_with_changelog_url(self):
        change = DependencyChange(name="requests", change_type=ChangeType.UPDATED, old_version="2.28.0", new_version="2.29.0")
        info = PackageInfo(
            name="requests",
            github_url="https://github.com/user/requests",
            changelog_url="https://github.com/user/requests/blob/main/CHANGELOG.md",
        )
        entries = [ChangelogEntry(version="2.29.0", content="- Fixed bug\n- Added feature")]
        report = PackageReport(dependency_change=change, package_info=info, changelog_entries=entries)
        with patch.object(self.formatter.console, "print") as mock_print:
            self.formatter._display_package_report(report)
            mock_print.assert_called()
            panel_call = mock_print.call_args_list[0]
            panel = panel_call[0][0]
            title = str(panel.title)
            assert "GitHub" in title
            assert "Changelog" in title
            assert "https://github.com/user/requests" in title
            assert "https://github.com/user/requests/blob/main/CHANGELOG.md" in title

    def test_display_package_report_github_only(self):
        change = DependencyChange(name="requests", change_type=ChangeType.UPDATED, old_version="2.28.0", new_version="2.29.0")
        info = PackageInfo(
            name="requests",
            github_url="https://github.com/user/requests",
            changelog_url=None,
        )
        entries = []
        report = PackageReport(dependency_change=change, package_info=info, changelog_entries=entries)
        with patch.object(self.formatter.console, "print") as mock_print:
            self.formatter._display_package_report(report)
            mock_print.assert_called()
            panel_call = mock_print.call_args_list[0]
            panel = panel_call[0][0]
            title = str(panel.title)
            assert "GitHub" in title
            assert "Changelog" not in title
            assert "https://github.com/user/requests" in title

    def test_display_package_report_removed_package(self):
        change = DependencyChange(name="requests", change_type=ChangeType.REMOVED, old_version="1.5.0")
        info = PackageInfo(name="requests", github_url="https://github.com/user/user")
        report = PackageReport(dependency_change=change, package_info=info, changelog_entries=[])
        with patch.object(self.formatter.console, "print") as mock_print:
            self.formatter._display_package_report(report)
            mock_print.assert_called()
            panel_call = mock_print.call_args_list[0]
            panel = panel_call[0][0]
            content = str(panel.renderable)
            assert "Package removed from dependencies" in content
            assert "Changelog not found" not in content

    def test_display_package_report_added_package(self):
        change = DependencyChange(name="new-package", change_type=ChangeType.ADDED, new_version="1.0.0")
        info = PackageInfo(name="new-package", github_url="https://github.com/user/new-package")
        report = PackageReport(dependency_change=change, package_info=info, changelog_entries=[])
        with patch.object(self.formatter.console, "print") as mock_print:
            self.formatter._display_package_report(report)
            mock_print.assert_called()
            panel_call = mock_print.call_args_list[0]
            panel = panel_call[0][0]
            content = str(panel.renderable)
            assert "Package added to dependencies" in content
            assert "Changelog not found" not in content

    def test_display_package_report_updated_no_changelog(self):
        change = DependencyChange(name="requests", change_type=ChangeType.UPDATED, old_version="2.28.0", new_version="2.29.0")
        info = PackageInfo(name="requests", github_url="https://github.com/user/requests")
        report = PackageReport(dependency_change=change, package_info=info, changelog_entries=[])
        with patch.object(self.formatter.console, "print") as mock_print:
            self.formatter._display_package_report(report)
            mock_print.assert_called()
            panel_call = mock_print.call_args_list[0]
            panel = panel_call[0][0]
            content = str(panel.renderable)
            assert "Changelog not found in repository" in content
