"""
HTML formatter for displaying changelog checker results.
"""

import html
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from changelog_checker.models import ChangeType, DependencyChange, PackageInfo, PackageReport
from changelog_checker.utils import detect_content_format, get_packages_with_missing_changelogs

try:
    import markdown

    HAS_MARKDOWN_SUPPORT = True
except ImportError:
    HAS_MARKDOWN_SUPPORT = False

try:
    import docutils
    from docutils.core import publish_parts

    HAS_RST_SUPPORT = True
except ImportError:
    HAS_RST_SUPPORT = False

BODY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📦 Dependency Update Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .timestamp {{
            margin-top: 10px;
            opacity: 0.9;
            font-size: 0.9em;
        }}
        .section {{
            background: white;
            margin: 20px 0;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .section h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #007bff;
        }}
        .summary-card.updated {{ border-left-color: #28a745; }}
        .summary-card.added {{ border-left-color: #007bff; }}
        .summary-card.removed {{ border-left-color: #dc3545; }}
        .summary-card.missing {{ border-left-color: #ffc107; }}
        .summary-number {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .summary-label {{
            color: #666;
            margin-top: 5px;
        }}
        .package-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            table-layout: fixed;
        }}
        .package-table th,
        .package-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        .package-table th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #333;
        }}
        .package-table tr:hover {{
            background-color: #f8f9fa;
        }}
        .version-change {{
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            background: #f1f3f4;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        .changelog-content {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 15px;
            margin: 10px 0;
            max-height: 800px;
            overflow-y: auto;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        .changelog-content h1,
        .changelog-content h2,
        .changelog-content h3 {{
            color: #333;
            margin-top: 20px;
            margin-bottom: 10px;
            border-bottom: 1px solid #e9ecef;
            padding-bottom: 5px;
        }}
        .changelog-content h1 {{
            font-size: 1.4em;
            color: #2c3e50;
        }}
        .changelog-content h2 {{
            font-size: 1.2em;
            color: #34495e;
        }}
        .changelog-content h3 {{
            font-size: 1.1em;
            color: #5d6d7e;
        }}
        .changelog-content .section {{
            background: transparent;
            margin: 15px 0;
            padding: 0;
            border-radius: 0;
            box-shadow: none;
            margin-bottom: 20px;
        }}
        .changelog-content .section:first-child h1 {{
            margin-top: 0;
        }}
        .changelog-content ul,
        .changelog-content ol {{
            padding-left: 20px;
        }}
        .changelog-content code {{
            background: #e9ecef;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        .changelog-content pre {{
            background: #e9ecef;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        .changelog-content p,
        .changelog-content li {{
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        .github-link {{
            color: #0366d6;
            text-decoration: none;
        }}
        .github-link:hover {{
            text-decoration: underline;
        }}
        .no-content {{
            color: #666;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📦 Dependency Update Report</h1>
        <div class="timestamp">Generated on {timestamp}</div>
    </div>
    {content}
</body>
</html>"""

SUMMARY_HTML = """
    <div class="section">
        <h2>📊 Summary</h2>
        <div class="summary-grid">
            <div class="summary-card updated">
                <div class="summary-number">{updated}</div>
                <div class="summary-label">Updated</div>
            </div>
            <div class="summary-card added">
                <div class="summary-number">{added}</div>
                <div class="summary-label">Added</div>
            </div>
            <div class="summary-card removed">
                <div class="summary-number">{removed}</div>
                <div class="summary-label">Removed</div>
            </div>
            <div class="summary-card missing">
                <div class="summary-number">{missing}</div>
                <div class="summary-label">Missing Changelogs</div>
            </div>
        </div>
    </div>"""

UPDATED_PACKAGES_HTML = """
    <div class="section">
        <h2>🔄 Updated Packages</h2>
        <table class="package-table">
            <thead>
                <tr>
                    <th>Package</th>
                    <th>Version Change</th>
                    <th>GitHub Repository</th>
                </tr>
            </thead>
            <tbody>
                {content}
            </tbody>
        </table>
    </div>"""

ADDED_PACKAGES_HTML = """
    <div class="section">
        <h2>➕ Added Packages</h2>
        <table class="package-table">
            <thead>
                <tr>
                    <th>Package</th>
                    <th>Version</th>
                    <th>GitHub Repository</th>
                </tr>
            </thead>
            <tbody>
                {content}
            </tbody>
        </table>
    </div>"""

REMOVED_PACKAGES_HTML = """
    <div class="section">
        <h2>➖ Removed Packages</h2>
        <table class="package-table">
            <thead>
                <tr>
                    <th>Package</th>
                    <th>Previous Version</th>
                    <th>GitHub Repository</th>
                </tr>
            </thead>
            <tbody>
                {content}
            </tbody>
        </table>
    </div>"""

MISSING_CHANGELOGS_HTML = """
    <div class="section">
        <h2>📝 Packages with Missing Changelogs</h2>
        <table class="package-table">
            <thead>
                <tr>
                    <th>Package</th>
                    <th>Version Change</th>
                    <th>GitHub Repository</th>
                </tr>
            </thead>
            <tbody>
                {content}
            </tbody>
        </table>
    </div>"""


class HTMLFormatter:
    """Formats output as an HTML file with proper markdown and RST rendering."""

    def __init__(self, output_file: str = "changelog_report.html") -> None:
        """
        Initialize the HTML formatter.

        Args:
            output_file: Path to the output HTML file
        """
        self.output_file = Path(output_file)

    def display_results(self, reports: list[PackageReport]) -> None:
        """Generate and save the complete HTML report."""
        html_content = self._generate_html_report(reports)
        self.output_file.write_text(html_content, encoding="utf-8")
        print(f"HTML report generated: {self.output_file.absolute()}")

    def _generate_html_report(self, reports: list[PackageReport]) -> str:
        updated = [r for r in reports if r.dependency_change.change_type == ChangeType.UPDATED]
        added = [r for r in reports if r.dependency_change.change_type == ChangeType.ADDED]
        removed = [r for r in reports if r.dependency_change.change_type == ChangeType.REMOVED]
        missing_changelogs = get_packages_with_missing_changelogs(reports)
        summary_html = self._generate_summary_html(len(updated), len(added), len(removed), len(missing_changelogs))
        updated_html = self._generate_updated_packages_html(updated) if updated else ""
        added_html = self._generate_added_packages_html(added) if added else ""
        removed_html = self._generate_removed_packages_html(removed) if removed else ""
        missing_html = self._generate_missing_changelogs_html(missing_changelogs) if missing_changelogs else ""
        return self._generate_html_template(summary_html + updated_html + added_html + removed_html + missing_html)

    def _generate_html_template(self, content: str) -> str:
        """Generate the complete HTML document template."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return BODY_HTML.format(timestamp=timestamp, content=content)

    def _generate_summary_html(self, updated: int, added: int, removed: int, missing: int) -> str:
        """Generate the summary section HTML."""
        return SUMMARY_HTML.format(updated=updated, added=added, removed=removed, missing=missing)

    def _generate_github_link(self, package_info: PackageInfo | None) -> str:
        """Generate GitHub link HTML for a package."""
        if package_info and package_info.github_url:
            return f'<a href="{package_info.github_url}" class="github-link" target="_blank">{package_info.github_url}</a>'
        return "N/A"

    def _generate_changelog_html(self, report: PackageReport) -> str:
        """Generate changelog HTML content for a package report."""
        if not report.changelog_entries:
            return '<div class="no-content">No changelog content found</div>'
        changelog_html = ""
        for entry in report.changelog_entries:
            changelog_html += f"<h4>Version {entry.version}</h4>"
            changelog_html += self._format_changelog_content_html(entry.content)
        return changelog_html

    def _generate_package_table_html(
        self,
        reports: list[PackageReport],
        template: str,
        version_formatter: Callable[[DependencyChange], str],
        include_changelog: bool = False,
    ) -> str:
        """
        Generate HTML table for packages with customizable version formatting.

        Args:
            reports: List of package reports
            template: HTML template string with {content} placeholder
            version_formatter: Function that takes a DependencyChange and returns version string
            include_changelog: Whether to include changelog content in the table
        """
        if not reports:
            return ""
        rows = []
        for report in reports:
            change = report.dependency_change
            version_text = version_formatter(change)
            github_link = self._generate_github_link(report.package_info)
            rows.append(f"""
            <tr>
                <td><strong>{html.escape(change.name)}</strong></td>
                <td><span class="version-change">{html.escape(version_text)}</span></td>
                <td>{github_link}</td>
            </tr>""")
            if include_changelog:
                changelog_html = self._generate_changelog_html(report)
                rows.append(f"""
            <tr>
                <td colspan="3">
                    <div class="changelog-content">
                        {changelog_html}
                    </div>
                </td>
            </tr>""")
        return template.format(content="".join(rows))

    def _generate_updated_packages_html(self, reports: list[PackageReport]) -> str:
        """Generate HTML for updated packages with changelogs."""

        def version_formatter(change: DependencyChange) -> str:
            return f"{change.old_version} → {change.new_version}"

        return self._generate_package_table_html(reports, UPDATED_PACKAGES_HTML, version_formatter, include_changelog=True)

    def _generate_added_packages_html(self, reports: list[PackageReport]) -> str:
        """Generate HTML for added packages."""

        def version_formatter(change: DependencyChange) -> str:
            return change.new_version or "N/A"

        return self._generate_package_table_html(reports, ADDED_PACKAGES_HTML, version_formatter, include_changelog=False)

    def _generate_removed_packages_html(self, reports: list[PackageReport]) -> str:
        """Generate HTML for removed packages."""

        def version_formatter(change: DependencyChange) -> str:
            return change.old_version or "N/A"

        return self._generate_package_table_html(reports, REMOVED_PACKAGES_HTML, version_formatter, include_changelog=False)

    def _generate_missing_changelogs_html(self, reports: list[PackageReport]) -> str:
        """Generate HTML for packages with missing changelogs."""

        def version_formatter(change: DependencyChange) -> str:
            return f"{change.old_version} → {change.new_version}"

        return self._generate_package_table_html(reports, MISSING_CHANGELOGS_HTML, version_formatter, include_changelog=False)

    def _format_changelog_content_html(self, content: str) -> str:
        """Format changelog content for HTML display with proper markdown/RST rendering."""
        if not content.strip():
            return '<div class="no-content">No changelog content found</div>'
        content_format = detect_content_format(content)
        if content_format == "markdown" and HAS_MARKDOWN_SUPPORT:
            return self._format_as_markdown_html(content)
        if content_format == "rst" and HAS_RST_SUPPORT:
            return self._format_as_rst_html(content)
        return self._format_as_plain_text_html(content)

    def _format_as_markdown_html(self, content: str) -> str:
        """Format content as HTML using markdown."""
        try:
            html_result = markdown.markdown(content, extensions=["fenced_code", "tables"])
            return self._add_target_blank_to_links(html_result)
        except Exception:
            return self._format_as_plain_text_html(content)

    def _format_as_rst_html(self, content: str) -> str:
        """Format content as HTML using RST."""
        try:
            silent_level = docutils.utils.Reporter.SEVERE_LEVEL + 1
            settings_overrides = {"report_level": silent_level}
            parts = publish_parts(content, writer_name="html", settings_overrides=settings_overrides)
            html_body = parts["body"]
            return self._add_target_blank_to_links(html_body)
        except Exception:
            return self._format_as_plain_text_html(content)

    def _add_target_blank_to_links(self, html_content: str) -> str:
        """
        Add target="_blank" to all external links in HTML content and convert plain text URLs to links.

        This ensures that all links in changelog content open in new tabs.
        """
        html_content = self._convert_plain_urls_to_links(html_content)

        def add_target(match: re.Match[str]) -> str:
            full_tag = match.group(0)
            if "target=" in full_tag:
                return full_tag
            return full_tag[:-1] + ' target="_blank">'

        pattern = r"<a\s+[^>]*href=[^>]*>"
        return re.sub(pattern, add_target, html_content)

    def _convert_plain_urls_to_links(self, html_content: str) -> str:
        """
        Convert plain text URLs to clickable links.

        This handles URLs that are not already wrapped in <a> tags.
        """
        url_pattern = r'(?<!href=["\'])(?<!src=["\'])(https?://[^\s<>"\']+)'

        def url_to_link(match: re.Match[str]) -> str:
            url = match.group(1)
            url = re.sub(r"[.,;:!?]+$", "", url)
            return f'<a href="{html.escape(url)}" target="_blank">{html.escape(url)}</a>'

        return re.sub(url_pattern, url_to_link, html_content)

    def _format_as_plain_text_html(self, content: str) -> str:
        """Format content as plain text HTML."""
        lines = content.split("\n")
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            escaped_line = html.escape(line)
            if line.startswith("*") or line.startswith("-") or line.startswith("+"):
                formatted_lines.append(f"<li>{escaped_line[1:].strip()}</li>")
            elif line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                header_text = line.lstrip("# ").strip()
                formatted_lines.append(f"<h{min(level, 6)}>{html.escape(header_text)}</h{min(level, 6)}>")
            else:
                formatted_lines.append(f"<p>{escaped_line}</p>")
        result = []
        in_list = False
        for line in formatted_lines:
            if line.startswith("<li>"):
                if not in_list:
                    result.append("<ul>")
                    in_list = True
                result.append(line)
            else:
                if in_list:
                    result.append("</ul>")
                    in_list = False
                result.append(line)
        if in_list:
            result.append("</ul>")
        html_result = "\n".join(result) if result else '<div class="no-content">No readable content</div>'
        return self._add_target_blank_to_links(html_result)

    def display_error(self, message: str) -> None:
        """Display an error message."""
        print(f"Error: {message}")

    def display_progress(self, message: str) -> None:
        """Display a progress message."""
        print(message)
