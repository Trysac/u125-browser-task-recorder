# Architecture

`trysac-browser-task-recorder` converts browser interaction sessions into reproducible, secure Playwright Python automation scripts.

## Component Overview

1. **Data Model (`Step`, `Recording`)**: Immutable dataclasses describing browser actions such as `goto`, `click`, `fill`, `press`, `select`, `check`, and `wait_for`.
2. **Parsers (`load_recording`, `from_devtools`)**: Ingest either Chrome DevTools Recorder JSON exports or a native JSON recording structure. Safely validates input size, schemes, and data shapes.
3. **Normalizer (`normalize`)**: Pure transformation function merging consecutive keystrokes on the same selector and removing duplicate consecutive navigation calls.
4. **Code Generator (`to_playwright_python`)**: Deterministic script emitter using Python's `repr()` for all string literals. Automatically intercepts sensitive input fields (e.g. selectors matching `(?i)password|passwd|pin|otp|token|secret`) and substitutes them with environment variable lookups.
5. **Command Line Interface (`__main__.py`)**: Thin entry point that processes recording files, prints warnings to `stderr`, and streams or writes the generated Playwright code.
