"""
Command-line interface for the changelog checker.
"""

import sys
from typing import TextIO

import click

from .core import ChangelogChecker
from .utils import ChangelogCheckerError, NetworkError, ParserError, setup_logging


@click.command()
@click.option(
    "--input-file",
    "-f",
    type=click.File("r"),
    help="Read input from file instead of stdin",
)
@click.option(
    "--parser",
    "-p",
    default="uv",
    type=click.Choice(["uv"]),
    help="Parser type to use (default: uv)",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Logging level (default: INFO)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output (equivalent to --log-level DEBUG)",
)
@click.option(
    "--github-token",
    "-t",
    envvar="GITHUB_TOKEN",
    help="GitHub API token for authentication (can also use GITHUB_TOKEN env var)",
)
def main(input_file: TextIO | None, parser: str, log_level: str, verbose: bool, github_token: str | None) -> None:
    """
    Changelog Checker - Analyze dependency updates and their changelogs.

    Reads package manager output from stdin or a file and generates a report
    showing what changed in each updated dependency.

    Example usage:

        uv sync -U | changelog-checker

        changelog-checker -f uv_output.txt
    """
    if verbose:
        log_level = "DEBUG"
    logger = setup_logging(log_level)
    logger.info(f"Starting changelog checker with log level: {log_level}")
    try:
        if input_file:
            logger.debug(f"Reading input from file: {input_file.name}")
            input_text = input_file.read()
        else:
            if sys.stdin.isatty():
                click.echo("Error: No input provided. Use --input-file or pipe input to stdin.")
                click.echo("Example: uv sync -U | changelog-checker")
                sys.exit(1)
            logger.debug("Reading input from stdin")
            input_text = sys.stdin.read()
        if not input_text.strip():
            logger.error("Empty input provided")
            click.echo("Error: Empty input provided.")
            sys.exit(1)
        logger.debug(f"Input length: {len(input_text)} characters")
        checker = ChangelogChecker(github_token=github_token)
        reports = checker.check_dependencies(input_text, parser)
        logger.info(f"Generated {len(reports)} package reports")
        checker.formatter.display_results(reports)
        successful_reports = [r for r in reports if not r.error_message]
        error_reports = [r for r in reports if r.error_message]
        changelog_reports = [r for r in reports if r.changelog_entries]
        logger.info(
            f"Summary: {len(successful_reports)} successful, {len(error_reports)} errors, "
            f"{len(changelog_reports)} with changelogs"
        )
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        click.echo("\nOperation cancelled by user.")
        sys.exit(1)
    except ParserError as e:
        logger.error(f"Parser error: {e}")
        click.echo(f"Parser Error: {e}")
        sys.exit(1)
    except NetworkError as e:
        logger.error(f"Network error: {e}")
        click.echo(f"Network Error: {e}")
        click.echo("Check your internet connection and try again.")
        sys.exit(1)
    except ChangelogCheckerError as e:
        logger.error(f"Changelog checker error: {e}")
        click.echo(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        click.echo(f"Unexpected Error: {e}")
        click.echo("Please report this issue with the full error details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
