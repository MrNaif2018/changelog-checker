# Changelog Checker

A powerful tool for analyzing dependency updates and their changelogs. Automatically fetches and displays changelog information for updated packages, helping you understand what changed in your dependencies.

[![Python versions](https://img.shields.io/pypi/pyversions/changelog-checker?style=flat-square)](https://pypi.python.org/pypi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/changelog-checker.svg?style=flat-square)](https://pypi.python.org/pypi/changelog-checker)

## Features

- 🔍 **Automatic Changelog Detection**: Finds changelogs from GitHub releases, repository files, and PyPI
- 📊 **Rich Output**: Beautiful, formatted output with syntax highlighting
- 🔧 **Multiple Package Managers**: Currently supports `uv` with more coming soon
- 🚀 **Fast & Reliable**: Efficient parsing and caching for quick results
- 🔐 **GitHub Integration**: Optional GitHub token support for higher API rate limits
- 📝 **Multiple Formats**: Supports various changelog formats (Markdown, RST, Sphinx)

## Installation

### From PyPI

```bash
pip install changelog-checker
```

## Quick Start

The most common usage is to pipe package manager output directly to changelog-checker:

```bash
# Update dependencies and check changelogs
uv sync -U | changelog-checker

# Or save output to file first
uv sync -U > updates.txt
changelog-checker -f updates.txt
```

## Usage

### Basic Usage

```bash
# Pipe uv output directly
uv sync -U | changelog-checker

# Read from file
changelog-checker --input-file updates.txt

# Enable verbose output
changelog-checker -v --input-file updates.txt

# Use GitHub token for higher rate limits
export GITHUB_TOKEN=your_token_here
uv sync -U | changelog-checker
```

### Command Line Options

```bash
Options:
  -f, --input-file FILENAME       Read input from file instead of stdin
  -p, --parser [uv]               Parser type to use (default: uv)
  --log-level [DEBUG|INFO|WARNING|ERROR]
                                  Logging level (default: INFO)
  -v, --verbose                   Enable verbose output (equivalent to --log-
                                  level DEBUG)
  -t, --github-token TEXT         GitHub API token for authentication (can
                                  also use GITHUB_TOKEN env var)
  --help                          Show this message and exit.               Show this message and exit
```

### Environment Variables

- `GITHUB_TOKEN`: GitHub API token for authentication (optional but recommended)

## Example Output

When you run changelog-checker, you'll see a beautifully formatted report like this:

```bash


╭─────────────────────────────╮
│ 📦 Dependency Update Report │
╰─────────────────────────────╯
╭──────────────────────────────────────────────────────────────────────────────────────────── Summary ────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                                                                                                 │
│   📈 Updated              74                                                                                                                                                                    │
│   ➕ Added                 1                                                                                                                                                                    │
│   ➖ Removed               1                                                                                                                                                                    │
│   📝 Missing Changelogs    4                                                                                                                                                                    │
│                                                                                                                                                                                                 │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭─────────────────────╮
│ 📈 Updated Packages │
╰─────────────────────╯
╭───────────────────────────────────────────────────────────────────── aiohappyeyeballs: 2.4.4 → 2.6.1 (GitHub | Changelog) ──────────────────────────────────────────────────────────────────────╮
│ Changelog:                                                                                                                                                                                      │
│                                                                                                                                                                                                 │
│ Version 2.6.1:                                                                                                                                                                                  │
│ v2.6.1 (2025-03-12)                                                                                                                                                                     │
│                                                                                                                                                                                                 │
│                                    Bug Fixes                                                                                                                                              │
│                                                                                                                                                                                                 │
│  • Resolve TypeError on import for Python < 3.9.2 (#151,                                              │
│ 2042c82)                                                            │
│                                                                                                                                                                                                 │
│ ────────────────────────────────────────────────────────────────────────────────                                                                                                         │
│ Detailed Changes: v2.6.0...v2.6.1                                                         │
│                                                                                                                                                                                                 │
│ Version 2.6.0:                                                                                                                                                                                  │
│ v2.6.0 (2025-03-11)                                                                                                                                                                     │
│                                                                                                                                                                                                 │
│                                     Features                                                                                                                                              │
│                                                                                                                                                                                                 │
│  • docs: Publish documentation (#149,                                                            │
│ 4235273)                                                            │
│                                                                                                                                                                                                 │
│ Creates an api_reference.rst file to expose the existing documentation for the                                                                                                                  │
│ few functions that have docstrings, as well as add documentation for                                                                                                                            │
│ AddrInfoType and SocketFactoryType. Now, these can be properly pointed to by                                                                                                                    │
│ other projects' documentation.                                                                                                                                                                  │
│                                                                                                                                                                                                 │
│ ────────────────────────────────────────────────────────────────────────────────                                                                                                         │
│ Detailed Changes: v2.5.0...v2.6.0                                                         │
│                                                                                                                                                                                                 │
│ Version 2.5.0:                                                                                                                                                                                  │
│ v2.5.0 (2025-03-06)                                                                                                                                                                     │
│                                                                                                                                                                                                 │
│                                     Features                                                                                                                                              │
│                                                                                                                                                                                                 │
│  • Add callback for users to customize socket creation (#147,                                         │
│ 8e1bc6a)                                   
```

## Supported Package Managers

Currently supported:

- **uv**: Python package manager

## How It Works

1. **Parse Input**: Analyzes package manager output to identify updated packages
2. **Find Packages**: Searches for package information on PyPI and GitHub
3. **Fetch Changelogs**: Retrieves changelog information from multiple sources:
   - GitHub releases API
   - Repository changelog files (CHANGELOG.md, HISTORY.md, etc.)
   - PyPI project descriptions
4. **Parse & Format**: Processes changelog content and presents it in a readable format

## Configuration

### GitHub Token

For better rate limits and access to private repositories, set up a GitHub token:

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with `public_repo` scope
3. Set the environment variable:

   ```bash
   export GITHUB_TOKEN=your_token_here
   ```

## Development

### Setup

```bash
git clone https://github.com/MrNaif2018/changelog-checker.git
cd changelog-checker
uv sync
```

### Running Tests

```bash
uv run task test
```

### Code Quality

```bash
# Run linting
uv run task lint
# Type checking
uv run task lint_types

# Run all checks
uv run task ci
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Copyright and License

Copyright (C) 2025 MrNaif2018

Licensed under the [MIT license](LICENSE)

## Acknowledgments

- [github-reserved-names](https://github.com/Mottie/github-reserved-names) for a list of names to avoid treating as a github user during parsing
