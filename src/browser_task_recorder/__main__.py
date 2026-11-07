"""CLI entry point for browser_task_recorder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from browser_task_recorder import RecorderError, load_recording, to_playwright_python


def main(argv: list[str] | None = None) -> int:
    """CLI main execution function."""
    parser = argparse.ArgumentParser(
        prog="browser_task_recorder",
        description="Turn recorded browser steps into reproducible Playwright Python scripts.",
    )
    parser.add_argument("file", help="Path to the JSON recording file")
    parser.add_argument("-o", "--output", dest="output", help="Path to output script file")
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        default=True,
        help="Generate script with headless=False",
    )
    parser.add_argument(
        "--secret-prefix",
        dest="secret_prefix",
        default="RECORDER_SECRET_",
        help="Environment variable prefix for secrets",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
        return 2 if code != 0 else 0

    path = Path(args.file)
    if not path.is_file():
        sys.stderr.write(f"Error: file '{args.file}' does not exist\n")
        return 2

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        sys.stderr.write(f"IO error: {exc}\n")
        return 2

    try:
        recording = load_recording(content)
    except RecorderError as exc:
        if exc.code in ("too_large", "invalid_recording"):
            sys.stderr.write(f"Recorder error ({exc.code}): {exc}\n")
            return 2
        sys.stderr.write(f"Recorder error ({exc.code}): {exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"Parse error: {exc}\n")
        return 2

    for warning in recording.warnings:
        sys.stderr.write(f"{warning}\n")

    try:
        script = to_playwright_python(
            recording,
            headless=args.headless,
            secret_env_prefix=args.secret_prefix,
        )
    except RecorderError as exc:
        sys.stderr.write(f"Error generating script ({exc.code}): {exc}\n")
        return 1

    if args.output:
        try:
            Path(args.output).write_text(script, encoding="utf-8")
        except Exception as exc:
            sys.stderr.write(f"Output IO error: {exc}\n")
            return 2
    else:
        sys.stdout.write(script)

    return 0


if __name__ == "__main__":
    sys.exit(main())
