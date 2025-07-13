import tempfile
from pathlib import Path
from unittest.mock import patch

from changelog_checker.models import (
    ChangelogEntry,
    ChangeType,
    DependencyChange,
    PackageInfo,
    PackageReport,
)
from changelog_checker.output.html_formatter import HTMLFormatter
from changelog_checker.utils import get_packages_with_missing_changelogs


class TestHTMLFormatter:
    def setup_method(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as temp_file:
            self.temp_file = temp_file
        self.formatter = HTMLFormatter(output_file=self.temp_file.name)

    def teardown_method(self):
        Path(self.temp_file.name).unlink(missing_ok=True)

    def test_init_with_default_output_file(self):
        formatter = HTMLFormatter()
        assert formatter.output_file == Path("changelog_report.html")

    def test_init_with_custom_output_file(self):
        formatter = HTMLFormatter(output_file="custom_report.html")
        assert formatter.output_file == Path("custom_report.html")

    def test_display_results_empty(self):
        self.formatter.display_results([])
        assert Path(self.temp_file.name).exists()
        content = Path(self.temp_file.name).read_text()
        assert "<!DOCTYPE html>" in content
        assert "Dependency Update Report" in content
        assert "Generated on" in content

    def test_display_results_with_updated_packages(self):
        change = DependencyChange(name="requests", change_type=ChangeType.UPDATED, old_version="2.28.0", new_version="2.29.0")
        info = PackageInfo(name="requests", github_url="https://github.com/user/requests")
        entries = [ChangelogEntry(version="2.29.0", content="- Fixed bug\n- Added feature")]
        report = PackageReport(dependency_change=change, package_info=info, changelog_entries=entries)
        self.formatter.display_results([report])
        content = Path(self.temp_file.name).read_text()
        assert "requests" in content
        assert "2.28.0 → 2.29.0" in content
        assert "https://github.com/user/requests" in content
        assert "Fixed bug" in content
        assert "Added feature" in content

    def test_display_results_with_added_packages(self):
        change = DependencyChange(name="new-package", change_type=ChangeType.ADDED, new_version="1.0.0")
        info = PackageInfo(name="new-package", github_url="https://github.com/user/new-package")
        report = PackageReport(dependency_change=change, package_info=info, changelog_entries=[])
        self.formatter.display_results([report])
        content = Path(self.temp_file.name).read_text()
        assert "Added Packages" in content
        assert "new-package" in content
        assert "1.0.0" in content

    def test_display_results_with_removed_packages(self):
        change = DependencyChange(name="old-package", change_type=ChangeType.REMOVED, old_version="1.5.0")
        info = PackageInfo(name="old-package", github_url="https://github.com/user/old-package")
        report = PackageReport(dependency_change=change, package_info=info, changelog_entries=[])
        self.formatter.display_results([report])
        content = Path(self.temp_file.name).read_text()
        assert "Removed Packages" in content
        assert "old-package" in content
        assert "1.5.0" in content

    def test_display_results_with_missing_changelogs(self):
        change = DependencyChange(
            name="no-changelog", change_type=ChangeType.UPDATED, old_version="1.0.0", new_version="1.1.0"
        )
        info = PackageInfo(name="no-changelog", github_url="https://github.com/user/no-changelog")
        report = PackageReport(
            dependency_change=change,
            package_info=info,
            changelog_entries=[],
        )
        self.formatter.display_results([report])
        content = Path(self.temp_file.name).read_text()
        assert "Missing Changelogs" in content
        assert "no-changelog" in content

    def test_format_changelog_content_html_plain_text(self):
        content = "Header\nList item 1\nList item 2\nRegular text"
        result = self.formatter._format_changelog_content_html(content)
        assert "Header" in result
        assert "List item 1" in result
        assert "List item 2" in result
        assert "Regular text" in result

    def test_format_changelog_content_html_empty(self):
        result = self.formatter._format_changelog_content_html("")
        assert "No changelog content found" in result
        result = self.formatter._format_changelog_content_html("   \n  \n  ")
        assert "No changelog content found" in result

    @patch("changelog_checker.output.html_formatter.HAS_MARKDOWN_SUPPORT", True)
    def test_format_changelog_content_html_markdown(self):
        markdown_content = "# Header\n- List item"
        with patch("changelog_checker.output.html_formatter.markdown") as mock_md:
            mock_md.markdown.return_value = "<h1>Header</h1><ul><li>List item</li></ul>"
            result = self.formatter._format_changelog_content_html(markdown_content)
            assert result == "<h1>Header</h1><ul><li>List item</li></ul>"

    @patch("changelog_checker.output.html_formatter.HAS_RST_SUPPORT", True)
    def test_format_changelog_content_html_rst(self):
        rst_content = """
Header
======

- List item
"""
        with patch("changelog_checker.output.html_formatter.publish_parts") as mock_publish:
            mock_publish.return_value = {"body": "<h1>Header</h1><ul><li>List item</li></ul>"}
            result = self.formatter._format_changelog_content_html(rst_content)
            assert result == "<h1>Header</h1><ul><li>List item</li></ul>"

    def test_format_changelog_content_html_fallback_on_error(self):
        markdown_content = "# Header\n- List item"
        with (
            patch("changelog_checker.output.html_formatter.HAS_MARKDOWN_SUPPORT", True),
            patch("changelog_checker.output.html_formatter.markdown") as mock_md,
        ):
            mock_md.markdown.side_effect = Exception("Rendering error")
            result = self.formatter._format_changelog_content_html(markdown_content)
            assert "<h1>Header</h1>" in result
            assert "<li>List item</li>" in result

    def test_get_packages_with_missing_changelogs(self):
        change1 = DependencyChange(
            name="with-changelog", change_type=ChangeType.UPDATED, old_version="1.0.0", new_version="1.1.0"
        )
        info1 = PackageInfo(name="with-changelog", github_url="https://github.com/user/with-changelog")
        report1 = PackageReport(
            dependency_change=change1,
            package_info=info1,
            changelog_entries=[ChangelogEntry(version="1.1.0", content="- Fixed bug")],
        )
        change2 = DependencyChange(
            name="without-changelog", change_type=ChangeType.UPDATED, old_version="1.0.0", new_version="1.1.0"
        )
        info2 = PackageInfo(name="without-changelog", github_url="https://github.com/user/without-changelog")
        report2 = PackageReport(dependency_change=change2, package_info=info2, changelog_entries=[])
        change3 = DependencyChange(name="added-package", change_type=ChangeType.ADDED, new_version="1.0.0")
        info3 = PackageInfo(name="added-package", github_url="https://github.com/user/added-package")
        report3 = PackageReport(dependency_change=change3, package_info=info3, changelog_entries=[])
        missing = get_packages_with_missing_changelogs([report1, report2, report3])
        assert len(missing) == 1
        assert missing[0].dependency_change.name == "without-changelog"

    def test_html_escaping(self):
        change = DependencyChange(
            name="<script>alert('xss')</script>", change_type=ChangeType.UPDATED, old_version="1.0.0", new_version="2.0.0"
        )
        info = PackageInfo(name="<script>alert('xss')</script>")
        report = PackageReport(dependency_change=change, package_info=info, changelog_entries=[])
        self.formatter.display_results([report])
        content = Path(self.temp_file.name).read_text()
        assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in content
        assert "<script>alert('xss')</script>" not in content

    def test_display_error(self, capsys):
        self.formatter.display_error("Test error message")
        captured = capsys.readouterr()
        assert "Error: Test error message" in captured.out

    def test_display_progress(self, capsys):
        self.formatter.display_progress("Processing...")
        captured = capsys.readouterr()
        assert "Processing..." in captured.out

    def test_add_target_blank_to_links(self):
        """Test that target='_blank' is added to external links."""
        html_without_target = '<a href="https://example.com">Link</a>'
        result = self.formatter._add_target_blank_to_links(html_without_target)
        assert 'target="_blank"' in result
        assert result == '<a href="https://example.com" target="_blank">Link</a>'
        html_with_target = '<a href="https://example.com" target="_self">Link</a>'
        result = self.formatter._add_target_blank_to_links(html_with_target)
        assert 'target="_self"' in result
        assert result.count("target=") == 1
        html_multiple = '<a href="https://example.com">Link1</a> and <a href="https://test.com">Link2</a>'
        result = self.formatter._add_target_blank_to_links(html_multiple)
        assert result.count('target="_blank"') == 2

    @patch("changelog_checker.output.html_formatter.HAS_MARKDOWN_SUPPORT", True)
    def test_markdown_links_get_target_blank(self):
        """Test that markdown links get target='_blank' added."""
        markdown_content = "# Header\nCheck out [this link](https://example.com) for more info."
        with patch("changelog_checker.output.html_formatter.markdown") as mock_md:
            mock_md.markdown.return_value = (
                '<h1>Header</h1><p>Check out <a href="https://example.com">this link</a> for more info.</p>'
            )
            result = self.formatter._format_changelog_content_html(markdown_content)
            assert 'target="_blank"' in result

    @patch("changelog_checker.output.html_formatter.HAS_RST_SUPPORT", True)
    def test_rst_links_get_target_blank(self):
        """Test that RST links get target='_blank' added."""
        rst_content = """
Header
======

Check out `this link <https://example.com>`__ for more info.
"""
        with patch("changelog_checker.output.html_formatter.publish_parts") as mock_publish:
            mock_publish.return_value = {
                "body": (
                    '<p>Check out <a class="reference external" href="https://example.com">this link</a> for more info.</p>'
                )
            }
            result = self.formatter._format_changelog_content_html(rst_content)
            assert 'target="_blank"' in result
