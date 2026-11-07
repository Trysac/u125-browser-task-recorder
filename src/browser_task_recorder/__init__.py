"""Turn recorded browser steps into reproducible Playwright Python scripts."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlparse

__all__ = [
    "RecorderError",
    "Recording",
    "Step",
    "__version__",
    "from_devtools",
    "load_recording",
    "normalize",
    "to_playwright_python",
]

__version__ = "0.1.0"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

StepKind = Literal["goto", "click", "fill", "press", "select", "check", "wait_for"]
ErrorCode = Literal["unsafe_url", "too_large", "invalid_recording"]

VALID_KINDS: set[str] = {"goto", "click", "fill", "press", "select", "check", "wait_for"}
SECRET_PATTERN = re.compile(r"(?i)(?:password|passwd|pin|otp|token|secret)")


class RecorderError(Exception):
    """Base error raised by browser_task_recorder operations."""

    def __init__(self, code: ErrorCode, message: str = "") -> None:
        super().__init__(message or code)
        self.code: ErrorCode = code


@dataclass(frozen=True)
class Step:
    """Represents a single browser interaction step."""

    kind: StepKind
    selector: str | None = None
    value: str | None = None
    url: str | None = None
    key: str | None = None
    secret: bool = False
    double_click: bool = False


@dataclass(frozen=True)
class Recording:
    """Structured representation of a recorded browser session."""

    title: str
    steps: tuple[Step, ...]
    viewport: tuple[int, int] | None = None
    warnings: tuple[str, ...] = ()


def _validate_url(url: str | None) -> None:
    if url is None:
        return
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise RecorderError("unsafe_url", f"Unsafe or unsupported URL scheme: {parsed.scheme}")


def _is_secret_selector(selector: str | None) -> bool:
    if not selector:
        return False
    return bool(SECRET_PATTERN.search(selector))


def _parse_devtools_selector(selectors_list: Any) -> str | None:
    """Select the first selector list of length 1 that matches CSS, xpath, or text."""
    if not isinstance(selectors_list, list):
        return None

    for candidate in selectors_list:
        if not isinstance(candidate, list) or len(candidate) != 1:
            continue
        sel = candidate[0]
        if not isinstance(sel, str):
            continue
        if sel.startswith("aria/") or sel.startswith("pierce/"):
            continue
        if sel.startswith("xpath/"):
            return "xpath=" + sel[len("xpath/") :]
        if sel.startswith("text/"):
            return "text=" + sel[len("text/") :]
        # plain CSS selector (no prefix)
        return sel
    return None


def from_devtools(data: Mapping[str, Any]) -> Recording:
    """Parse a Chrome DevTools Recorder JSON mapping into a Recording."""
    title = str(data.get("title", "DevTools Recording"))
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list):
        raise RecorderError("invalid_recording", "Field 'steps' must be a list")

    steps: list[Step] = []
    warnings: list[str] = []
    viewport: tuple[int, int] | None = None

    ignored_types = {"keyup", "hover", "close"}

    for idx, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, Mapping):
            raise RecorderError("invalid_recording", f"Step {idx} is not an object")

        step_type = raw_step.get("type")
        if not isinstance(step_type, str):
            raise RecorderError("invalid_recording", f"Step {idx} missing string 'type'")

        type_lower = step_type.lower()

        if type_lower in ignored_types:
            continue

        if step_type == "setViewport":
            w = raw_step.get("width")
            h = raw_step.get("height")
            if isinstance(w, (int, float)) and isinstance(h, (int, float)):
                viewport = (int(w), int(h))
            continue

        if step_type == "navigate":
            url = raw_step.get("url")
            if not isinstance(url, str):
                raise RecorderError("invalid_recording", f"Step {idx} navigate missing string url")
            _validate_url(url)
            steps.append(Step(kind="goto", url=url))
            continue

        if step_type in ("click", "doubleClick"):
            sel = _parse_devtools_selector(raw_step.get("selectors"))
            if sel is None:
                warnings.append(f"no_selector:{idx}")
                continue
            is_dbl = step_type == "doubleClick"
            steps.append(Step(kind="click", selector=sel, double_click=is_dbl))
            continue

        if step_type == "change":
            sel = _parse_devtools_selector(raw_step.get("selectors"))
            if sel is None:
                warnings.append(f"no_selector:{idx}")
                continue
            val = raw_step.get("value", "")
            val_str = str(val) if val is not None else ""
            secret = _is_secret_selector(sel)
            steps.append(Step(kind="fill", selector=sel, value=val_str, secret=secret))
            continue

        if step_type == "keyDown":
            key = raw_step.get("key")
            key_str = str(key) if key is not None else ""
            steps.append(Step(kind="press", key=key_str))
            continue

        if step_type == "waitForElement":
            sel = _parse_devtools_selector(raw_step.get("selectors"))
            if sel is None:
                warnings.append(f"no_selector:{idx}")
                continue
            steps.append(Step(kind="wait_for", selector=sel))
            continue

        warnings.append(f"unsupported_step:{step_type}")

    return Recording(title=title, steps=tuple(steps), viewport=viewport, warnings=tuple(warnings))


def _from_native(data: Mapping[str, Any]) -> Recording:
    """Parse the native recording format."""
    title = str(data.get("title", "Recorded Task"))
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list):
        raise RecorderError("invalid_recording", "Field 'steps' must be a list")

    viewport = None
    raw_vp = data.get("viewport")
    if isinstance(raw_vp, (list, tuple)) and len(raw_vp) == 2:
        viewport = (int(raw_vp[0]), int(raw_vp[1]))

    steps: list[Step] = []
    for idx, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, Mapping):
            raise RecorderError("invalid_recording", f"Step {idx} is not an object")
        kind = raw_step.get("kind")
        if kind not in VALID_KINDS:
            raise RecorderError("invalid_recording", f"Unknown step kind at index {idx}: {kind}")

        url = raw_step.get("url")
        if kind == "goto":
            if not isinstance(url, str):
                raise RecorderError("invalid_recording", f"Step {idx} goto missing string url")
            _validate_url(url)

        selector = raw_step.get("selector")
        value = raw_step.get("value")
        key = raw_step.get("key")
        secret = bool(raw_step.get("secret", False)) or _is_secret_selector(selector)
        double_click = bool(raw_step.get("double_click", False))

        steps.append(
            Step(
                kind=kind,
                selector=selector,
                value=value,
                url=url,
                key=key,
                secret=secret,
                double_click=double_click,
            )
        )

    warnings_raw = data.get("warnings", ())
    warnings = (
        tuple(str(w) for w in warnings_raw) if isinstance(warnings_raw, (list, tuple)) else ()
    )
    return Recording(title=title, steps=tuple(steps), viewport=viewport, warnings=warnings)


def load_recording(text: str, *, max_bytes: int = 5_000_000, max_steps: int = 10_000) -> Recording:
    """Load and parse a recording from JSON text."""
    if len(text.encode("utf-8")) > max_bytes:
        raise RecorderError("too_large", f"Input exceeds maximum allowed bytes ({max_bytes})")

    try:
        data = json.loads(text)
    except Exception as exc:
        raise RecorderError("invalid_recording", f"Failed to parse JSON: {exc}") from exc

    if not isinstance(data, Mapping):
        raise RecorderError("invalid_recording", "Root JSON value must be an object")

    steps = data.get("steps")
    if not isinstance(steps, list):
        raise RecorderError("invalid_recording", "Recording must contain a 'steps' list")

    if len(steps) > max_steps:
        raise RecorderError("too_large", f"Step count {len(steps)} exceeds max_steps ({max_steps})")

    # Auto-detect DevTools format: steps list of objects with 'type'
    is_devtools = any(isinstance(s, Mapping) and "type" in s for s in steps)
    if is_devtools:
        return from_devtools(data)
    return _from_native(data)


def normalize(steps: Sequence[Step]) -> list[Step]:
    """Normalize steps: merge consecutive fills on same selector, drop redundant gotos."""
    normalized: list[Step] = []

    for step in steps:
        if step.kind == "goto":
            if normalized and normalized[-1].kind == "goto" and normalized[-1].url == step.url:
                continue
            normalized.append(step)
            continue

        if step.kind == "fill":
            if (
                normalized
                and normalized[-1].kind == "fill"
                and normalized[-1].selector == step.selector
            ):
                # Replace previous fill with latest one, preserving secret flag if either was secret
                is_secret = normalized[-1].secret or step.secret
                normalized[-1] = Step(
                    kind="fill",
                    selector=step.selector,
                    value=step.value,
                    secret=is_secret,
                )
                continue
            normalized.append(step)
            continue

        normalized.append(step)

    return normalized


def to_playwright_python(
    recording: Recording,
    *,
    headless: bool = True,
    secret_env_prefix: str = "RECORDER_SECRET_",  # noqa: S107
) -> str:
    """Generate a byte-exact Playwright Python script from a Recording."""
    # First normalize steps
    norm_steps = normalize(recording.steps)

    # Map distinct secret selectors to environment variables
    secret_map: dict[str, str] = {}
    secret_count = 0
    for step in norm_steps:
        if step.kind == "fill" and (step.secret or _is_secret_selector(step.selector)):
            sel = step.selector or ""
            if sel not in secret_map:
                secret_count += 1
                secret_map[sel] = f"{secret_env_prefix}{secret_count}"

    lines: list[str] = [
        "import os",
        "from playwright.sync_api import sync_playwright",
        "",
        "",
        "def run() -> None:",
        "    with sync_playwright() as p:",
        f"        browser = p.chromium.launch(headless={headless!r})",
    ]

    if recording.viewport is not None:
        w, h = recording.viewport
        lines.append(f"        page = browser.new_page(viewport={{'width': {w}, 'height': {h}}})")
    else:
        lines.append("        page = browser.new_page()")

    for step in norm_steps:
        if step.kind == "goto":
            _validate_url(step.url)
            lines.append(f"        page.goto({step.url or ''!r})")
        elif step.kind == "click":
            sel_repr = repr(step.selector or "")
            if step.double_click:
                lines.append(f"        page.locator({sel_repr}).dblclick()")
            else:
                lines.append(f"        page.locator({sel_repr}).click()")
        elif step.kind == "fill":
            sel = step.selector or ""
            sel_repr = repr(sel)
            if sel in secret_map:
                env_var = secret_map[sel]
                lines.append(f"        page.locator({sel_repr}).fill(os.environ[{env_var!r}])")
            else:
                val_repr = repr(step.value or "")
                lines.append(f"        page.locator({sel_repr}).fill({val_repr})")
        elif step.kind == "select":
            sel_repr = repr(step.selector or "")
            val_repr = repr(step.value or "")
            lines.append(f"        page.locator({sel_repr}).select_option({val_repr})")
        elif step.kind == "check":
            sel_repr = repr(step.selector or "")
            lines.append(f"        page.locator({sel_repr}).check()")
        elif step.kind == "wait_for":
            sel_repr = repr(step.selector or "")
            lines.append(f"        page.locator({sel_repr}).wait_for()")
        elif step.kind == "press":
            key_repr = repr(step.key or "")
            lines.append(f"        page.keyboard.press({key_repr})")

    lines.append("        browser.close()")
    lines.append("")
    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    run()")
    lines.append("")

    return "\n".join(lines)
