# Security Model

`trysac-browser-task-recorder` is designed to prevent credential leaks and code injection.

## Defended Threats

- **Insecure URL Schemes**: Navigation actions strictly reject non-HTTP(S) schemes (e.g., `javascript:`, `file:`, `data:`). These raise `RecorderError('unsafe_url').
- **Secret Exposure**: Any `fill` step with a selector matching `(?i)password|passwd|pin|otp|token|secret` or explicitly marked `secret=True` is automatically redacted. The value is replaced by `os.environ[<secret_env_prefix>+n]`.
- **Injection Attacks**: All inputs (selectors, URLs, values) are emitted in the generated script using Python's `repr()`. This ensures input cannot escape its literal bounds.

## Not Defended / Limits

- **Resource Exhaustion**: The library enforces limits to prevent memory exhaustion:
  - `max_bytes`: 5,000,000 bytes.
  - `max_steps`: 10,000 steps.
  - Exceeding these raises `RecorderError('too_large').
- **Execution Environment**: This library does not validate the security of the resulting script when executed; it is the user's responsibility to handle the generated Python file safely.