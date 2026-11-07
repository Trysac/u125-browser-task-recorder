# Testing

## Running

```sh
uv run pytest --cov=browser_task_recorder
uv run python scripts/check.py
```

## Coverage

- Branch coverage must remain at or above 80%.

## Test Suite Structure

- `tests/test_browser_task_recorder.py`: Covers the acceptance criteria:
  - Acceptance of DevTools Recorder JSON input format.
  - Normalization of steps (merging fills, dropping duplicate gotos).
  - Proper redaction of secrets into `os.environ` references.
  - Generation of byte-exact golden script outputs.
  - Proper `RecorderError` raising for invalid inputs, large files, and unsafe URLs.
  - AST parsing validation for generated literals.