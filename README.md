# trysac-browser-task-recorder

Turn recorded browser steps, including Chrome DevTools Recorder JSON exports, into reproducible Playwright Python scripts with safe literals and secrets moved to environment variables.

## The Problem

Browser tasks for agents and tests are often recorded once by hand, but recordings leak typed passwords into scripts, contain redundant keystrokes and use selector syntaxes Playwright does not understand. Converting a recording into a clean, reproducible script should be deterministic and safe. This library normalises recorded steps and generates a Playwright script with every value emitted as a safe literal.

## Installation

```bash
pip install trysac-browser-task-recorder
```

## Usage Example

```python
from browser_task_recorder import Recording, Step, to_playwright_python

rec = Recording(
    title="Login",
    steps=(
        Step(kind="goto", url="https://example.com/login"),
        Step(kind="fill", selector="#password", value="hunter2"),
    ),
)
# Generates a script with os.environ['RECORDER_SECRET_1']
script = to_playwright_python(rec)
print(script)
```

## API Summary

### Core Classes
- `Recording`: A container for `title`, `steps` (tuple of `Step`), `viewport`, and `warnings`.
- `Step`: Defines `kind` (goto, click, fill, press, select, check, wait_for), `selector`, `value`, `url`, `key`, `secret`, and `double_click`.
- `RecorderError`: Raised on failures with codes `unsafe_url`, `too_large`, `invalid_recording`.

### Functions
- `load_recording(text: str, *, max_bytes=5_000_000, max_steps=10_000) -> Recording`: Parses input text; detects DevTools or native formats.
- `from_devtools(data: Mapping) -> Recording`: Parses Chrome DevTools JSON exports.
- `normalize(steps: Sequence[Step]) -> list[Step]`: Collapses redundant fills and navigations.
- `to_playwright_python(recording: Recording, *, headless=True, secret_env_prefix='RECORDER_SECRET_') -> str`: Generates the Python script.

## Why not playwright codegen?

Playwright codegen requires a live browser session and does not support safe secret management. This library works offline on existing recordings and never writes typed secrets to disk.

## Security

See [docs/SECURITY.md](docs/SECURITY.md).