"""
Rich formatter for displaying changelog checker results.
"""

import re

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from changelog_checker.models import ChangeType, PackageReport

try:
    from rich_rst import RestructuredText

    HAS_RST_SUPPORT = True
except ImportError:
    RestructuredText = None
    HAS_RST_SUPPORT = False


class RichFormatter:
    """Formats output using the Rich library for colorful console display."""

    def __init__(self) -> None:
        self.console = Console()

    def display_results(self, reports: list[PackageReport]) -> None:
        """Display the complete results of changelog checking."""
        self.console.print("\n")
        self.console.print(Panel.fit("[bold blue]📦 Dependency Update Report[/bold blue]", border_style="blue"))
        if not reports:
            self.console.print("[yellow]No dependency changes found.[/yellow]")
            return
        updated = [r for r in reports if r.dependency_change.change_type == ChangeType.UPDATED]
        added = [r for r in reports if r.dependency_change.change_type == ChangeType.ADDED]
        removed = [r for r in reports if r.dependency_change.change_type == ChangeType.REMOVED]
        missing_changelogs = self._get_packages_with_missing_changelogs(reports)
        self._display_summary(len(updated), len(added), len(removed), len(missing_changelogs))
        if updated:
            self._display_updated_packages(updated)
        if added:
            self._display_added_packages(added)
        if removed:
            self._display_removed_packages(removed)
        if missing_changelogs:
            self._display_missing_changelogs(missing_changelogs)

    def _display_summary(self, updated_count: int, added_count: int, removed_count: int, missing_changelog_count: int) -> None:
        """Display summary statistics."""
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Type", style="bold")
        table.add_column("Count", justify="right")
        if updated_count > 0:
            table.add_row("📈 Updated", f"[green]{updated_count}[/green]")
        if added_count > 0:
            table.add_row("➕ Added", f"[blue]{added_count}[/blue]")
        if removed_count > 0:
            table.add_row("➖ Removed", f"[red]{removed_count}[/red]")
        if missing_changelog_count > 0:
            table.add_row("📝 Missing Changelogs", f"[yellow]{missing_changelog_count}[/yellow]")
        self.console.print(Panel(table, title="Summary", border_style="dim"))
        self.console.print()

    def _display_updated_packages(self, reports: list[PackageReport]) -> None:
        """Display updated packages with their changelogs."""
        self.console.print(Panel.fit("[bold green]📈 Updated Packages[/bold green]", border_style="green"))
        for report in reports:
            self._display_package_report(report)

    def _display_added_packages(self, reports: list[PackageReport]) -> None:
        """Display newly added packages."""
        self.console.print(Panel.fit("[bold blue]➕ Added Packages[/bold blue]", border_style="blue"))
        for report in reports:
            self._display_package_report(report)

    def _display_removed_packages(self, reports: list[PackageReport]) -> None:
        """Display removed packages."""
        self.console.print(Panel.fit("[bold red]➖ Removed Packages[/bold red]", border_style="red"))
        for report in reports:
            self._display_package_report(report)

    def _get_packages_with_missing_changelogs(self, reports: list[PackageReport]) -> list[PackageReport]:
        """Get packages that have missing changelogs."""
        missing_changelogs = []
        for report in reports:
            if (
                report.dependency_change.change_type == ChangeType.UPDATED
                and report.package_info
                and not report.changelog_entries
                and not report.error_message
            ):
                missing_changelogs.append(report)
        return missing_changelogs

    def _display_missing_changelogs(self, reports: list[PackageReport]) -> None:
        """Display packages with missing changelogs."""
        self.console.print(Panel.fit("[bold yellow]📝 Packages with Missing Changelogs[/bold yellow]", border_style="yellow"))
        table = Table(show_header=True, box=box.SIMPLE)
        table.add_column("Package", style="bold")
        table.add_column("Version Change", style="dim")
        table.add_column("GitHub Repository", style="blue")
        for report in reports:
            change = report.dependency_change
            info = report.package_info
            version_change = f"{change.old_version} → {change.new_version}"
            github_link = f"[link={info.github_url}]{info.github_url}[/link]" if info and info.github_url else "N/A"
            table.add_row(change.name, version_change, github_link)
        self.console.print(table)
        self.console.print()

    def _display_package_report(self, report: PackageReport) -> None:
        """Display a single package report."""
        change = report.dependency_change
        info = report.package_info
        if change.change_type == ChangeType.UPDATED:
            header = f"[bold]{change.name}[/bold]: {change.old_version} → [green]{change.new_version}[/green]"
        elif change.change_type == ChangeType.ADDED:
            header = f"[bold]{change.name}[/bold]: [blue]added {change.new_version}[/blue]"
        else:
            header = f"[bold]{change.name}[/bold]: [red]removed {change.old_version}[/red]"
        if info and info.github_url:
            header += f" ([link={info.github_url}]GitHub[/link]"
            if info.changelog_url:
                header += f" | [link={info.changelog_url}]Changelog[/link]"
            header += ")"
        else:
            header += " [red](GitHub not found)[/red]"
        content_parts = []
        if report.error_message:
            content_parts.append(f"[red]Error: {report.error_message}[/red]")
        if report.changelog_entries:
            content_parts.append("[bold]Changelog:[/bold]")
            for entry in report.changelog_entries:
                content_parts.append(f"\n[bold cyan]Version {entry.version}:[/bold cyan]")
                formatted_content = self._format_changelog_content(entry.content)
                content_parts.append(formatted_content)
        else:
            if change.change_type == ChangeType.UPDATED:
                if info and info.github_url:
                    content_parts.append("[red]Changelog not found in repository[/red]")
                else:
                    content_parts.append("[red]No GitHub repository found - cannot check changelog[/red]")
            elif change.change_type == ChangeType.REMOVED:
                content_parts.append("[dim]Package removed from dependencies[/dim]")
            elif change.change_type == ChangeType.ADDED:
                content_parts.append("[dim]Package added to dependencies[/dim]")
        content = "\n".join(content_parts) if content_parts else "[dim]No additional information available[/dim]"
        self.console.print(Panel(content, title=header, border_style="dim", expand=False))
        self.console.print()

    def _format_changelog_content(self, content: str) -> str:
        """Format changelog content for display with proper markdown/RST rendering."""
        if not content.strip():
            return "[dim]No changelog content found[/dim]"
        content_format = self._detect_content_format(content)
        if content_format == "markdown":
            return self._format_as_markdown(content)
        if content_format == "rst" and HAS_RST_SUPPORT:
            return self._format_as_rst(content)
        return self._format_as_plain_text(content)

    def _detect_content_format(self, content: str) -> str:
        """Detect if content is markdown, RST, or plain text."""
        lines = content.split("\n")
        markdown_indicators = 0
        rst_indicators = 0
        for line in lines:
            stripped = line.strip()
            if re.match(r"^#+\s", stripped):  # Headers: # ## ###
                markdown_indicators += 2
            elif re.match(r"^\*\*.*\*\*", stripped) or re.match(r"^[-*+]\s", stripped):  # Bold: **text**
                markdown_indicators += 1
            elif re.match(r"^```", stripped) or re.match(r"^\[.*\]\(.*\)", stripped):  # Code blocks: ```
                markdown_indicators += 2
            elif re.match(r"^[=\-~`#^\"']{3,}$", stripped) or re.match(r"^\.\. ", stripped):  # RST underlines
                rst_indicators += 2
            elif "~~~~" in stripped or "^^^^" in stripped:  # RST section markers
                rst_indicators += 1
            elif re.match(r"^[\w\-_]+\s+v\d+\.\d+\.\d+.*\([^)]+\)$", stripped):  # RST-style version headers
                rst_indicators += 2
        if rst_indicators > markdown_indicators and rst_indicators > 0:
            return "rst"
        if markdown_indicators > 0:
            return "markdown"
        return "plain"

    def _format_as_markdown(self, content: str) -> str:
        """Format content as markdown using Rich's Markdown renderer."""
        try:
            md = Markdown(content)
            temp_console = Console(file=None, width=80)
            with temp_console.capture() as capture:
                temp_console.print(md)
            return capture.get().strip()
        except Exception:
            return self._format_as_plain_text(content)

    def _format_as_rst(self, content: str) -> str:
        """Format content as RST using rich-rst if available."""
        try:
            rst = RestructuredText(content, show_errors=False)
            temp_console = Console(file=None, width=80)
            with temp_console.capture() as capture:
                temp_console.print(rst)
            return capture.get().strip()
        except Exception:
            return self._format_as_plain_text(content)

    def _format_as_plain_text(self, content: str) -> str:
        """Format content as plain text."""
        lines = content.split("\n")
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("*") or line.startswith("-") or line.startswith("+"):
                formatted_lines.append(f"  {line}")
            elif line.startswith("#"):
                formatted_lines.append(f"[bold]{line}[/bold]")
            else:
                formatted_lines.append(f"  {line}")
        return "\n".join(formatted_lines) if formatted_lines else "[dim]No readable content[/dim]"

    def display_error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(Panel(f"[red]Error: {message}[/red]", title="Error", border_style="red"))

    def display_progress(self, message: str) -> None:
        """Display a progress message."""
        self.console.print(f"[dim]{message}[/dim]")
