# browser-task-recorder

[![PyPI version](https://img.shields.io/pypi/v/trysac-browser-task-recorder)](https://pypi.org/project/trysac-browser-task-recorder/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-browser-task-recorder)](LICENSE)
[![CI](https://github.com/Trysac/u125-browser-task-recorder/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u125-browser-task-recorder/actions/workflows/ci.yml)

Turn recorded browser steps, including Chrome DevTools Recorder JSON exports, into reproducible Playwright Python scripts with safe literals and secrets moved to environment variables

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-browser-task-recorder
# or
uv add trysac-browser-task-recorder
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import browser_task_recorder

# normalize() trims surrounding whitespace and lower-cases the text.
print(browser_task_recorder.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    browser_task_recorder.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
