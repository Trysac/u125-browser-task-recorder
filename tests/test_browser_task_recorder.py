"""Tests for browser_task_recorder."""

import ast
import json
from pathlib import Path

import pytest

from browser_task_recorder import (
    RecorderError,
    Recording,
    Step,
    from_devtools,
    load_recording,
    normalize,
    to_playwright_python,
)
from browser_task_recorder.__main__ import main


def test_acceptance_golden_script() -> None:
    # Acceptance item 1:
    # to_playwright_python for steps goto 'https://example.com/login', fill '#user' 'ana', fill '#password' 'hunter2'
    # and click 'button[type=submit]' returns exactly the documented golden script, in which the password line is
    # "        page.locator('#password').fill(os.environ['RECORDER_SECRET_1'])" and 'hunter2' does not appear
    steps = (
        Step(kind="goto", url="https://example.com/login"),
        Step(kind="fill", selector="#user", value="ana"),
        Step(kind="fill", selector="#password", value="hunter2"),
        Step(kind="click", selector="button[type=submit]"),
    )
    rec = Recording(title="login", steps=steps)
    script = to_playwright_python(rec)

    expected = (
        "import os\n"
        "from playwright.sync_api import sync_playwright\n\n\n"
        "def run() -> None:\n"
        "    with sync_playwright() as p:\n"
        "        browser = p.chromium.launch(headless=True)\n"
        "        page = browser.new_page()\n"
        "        page.goto('https://example.com/login')\n"
        "        page.locator('#user').fill('ana')\n"
        "        page.locator('#password').fill(os.environ['RECORDER_SECRET_1'])\n"
        "        page.locator('button[type=submit]').click()\n"
        "        browser.close()\n\n\n"
        "if __name__ == '__main__':\n"
        "    run()\n"
    )
    assert script == expected
    assert "hunter2" not in script
    assert "page.locator('#password').fill(os.environ['RECORDER_SECRET_1'])" in script
    ast.parse(script)


def test_acceptance_ast_parse_quotes_and_newlines() -> None:
    # Acceptance item 2:
    # The generated script passes ast.parse for a selector 'a[title="it\'s"]' and a fill value 'a\nb' + chr(39) * 3,
    # because every value is emitted with repr()
    val = "a\nb" + chr(39) * 3
    sel = 'a[title="it\'s"]'
    rec = Recording(title="quotes", steps=(Step(kind="fill", selector=sel, value=val),))
    script = to_playwright_python(rec)
    parsed = ast.parse(script)
    assert isinstance(parsed, ast.Module)


def test_acceptance_normalize_merges_and_drops() -> None:
    # Acceptance item 3:
    # normalize merges consecutive fills of '#q' with 'a', 'ab' and 'abc' into one fill 'abc',
    # drops a goto identical to the previous goto, and keeps two consecutive identical clicks
    steps = [
        Step(kind="goto", url="https://example.com"),
        Step(kind="goto", url="https://example.com"),
        Step(kind="fill", selector="#q", value="a"),
        Step(kind="fill", selector="#q", value="ab"),
        Step(kind="fill", selector="#q", value="abc"),
        Step(kind="click", selector="#btn"),
        Step(kind="click", selector="#btn"),
    ]
    norm = normalize(steps)
    assert len(norm) == 4
    assert norm[0] == Step(kind="goto", url="https://example.com")
    assert norm[1] == Step(kind="fill", selector="#q", value="abc")
    assert norm[2] == Step(kind="click", selector="#btn")
    assert norm[3] == Step(kind="click", selector="#btn")


def test_acceptance_from_devtools() -> None:
    # Acceptance item 4:
    # from_devtools({"title": "t", "steps": [{"type": "setViewport", "width": 800, "height": 600}, {"type": "navigate", "url": "https://example.com"}, {"type": "click", "selectors": [["aria/Submit"], ["#go"]]}, {"type": "change", "value": "x", "selectors": [["xpath///input"]]}]})
    # returns steps [goto 'https://example.com', click '#go', fill 'xpath=//input' 'x'] and viewport (800, 600)
    data = {
        "title": "t",
        "steps": [
            {"type": "setViewport", "width": 800, "height": 600},
            {"type": "navigate", "url": "https://example.com"},
            {
                "type": "click",
                "selectors": [["aria/Submit"], ["#go"]],
            },  # aria ignored, fallback to CSS #go
            {
                "type": "change",
                "value": "x",
                "selectors": [["xpath///input"]],
            },  # xpath///input -> xpath=//input
        ],
    }
    rec = from_devtools(data)
    assert rec.viewport == (800, 600)
    assert len(rec.steps) == 3
    assert rec.steps[0] == Step(kind="goto", url="https://example.com")
    assert rec.steps[1] == Step(kind="click", selector="#go", double_click=False)
    assert rec.steps[2] == Step(kind="fill", selector="xpath=//input", value="x", secret=False)


def test_acceptance_devtools_warnings_and_keys() -> None:
    # Acceptance item 5:
    # A DevTools step whose only selectors are ["aria/Name"] and ["pierce/#x"] is skipped with warning 'no_selector:2',
    # a step of type 'scroll' is skipped with warning 'unsupported_step:scroll',
    # keyDown 'Enter' becomes "page.keyboard.press('Enter')" and keyUp is ignored without a warning
    data = {
        "title": "keys and warnings",
        "steps": [
            {"type": "scroll"},
            {"type": "keyUp", "key": "Shift"},
            {"type": "click", "selectors": [["aria/Name"], ["pierce/#x"]]},
            {"type": "keyDown", "key": "Enter"},
        ],
    }
    rec = from_devtools(data)
    assert "unsupported_step:scroll" in rec.warnings
    assert "no_selector:2" in rec.warnings
    assert len(rec.steps) == 1
    assert rec.steps[0] == Step(kind="press", key="Enter")
    script = to_playwright_python(rec)
    assert "page.keyboard.press('Enter')" in script
    assert not any("keyUp" in w for w in rec.warnings)


def test_acceptance_unsafe_url() -> None:
    # Acceptance item 6:
    # goto with 'javascript:alert(1)' or 'file:///etc/passwd' raises RecorderError with code 'unsafe_url'
    for bad_url in ["javascript:alert(1)", "file:///etc/passwd", "data:text/html,bad"]:
        with pytest.raises(RecorderError) as exc_info:
            to_playwright_python(Recording(title="bad", steps=(Step(kind="goto", url=bad_url),)))
        assert exc_info.value.code == "unsafe_url"

        dev_data = {"title": "bad", "steps": [{"type": "navigate", "url": bad_url}]}
        with pytest.raises(RecorderError) as exc_info2:
            from_devtools(dev_data)
        assert exc_info2.value.code == "unsafe_url"


def test_acceptance_limits_and_json_errors() -> None:
    # Acceptance item 7:
    # A recording over 5_000_000 bytes or with 10_001 steps raises code 'too_large', and invalid JSON raises code 'invalid_recording'
    big_text = "x" * 5_000_001
    with pytest.raises(RecorderError) as exc:
        load_recording(big_text)
    assert exc.value.code == "too_large"

    many_steps_json = json.dumps(
        {"title": "t", "steps": [{"kind": "click", "selector": "#b"}] * 10_001}
    )
    with pytest.raises(RecorderError) as exc:
        load_recording(many_steps_json)
    assert exc.value.code == "too_large"

    with pytest.raises(RecorderError) as exc:
        load_recording("{bad json")
    assert exc.value.code == "invalid_recording"

    with pytest.raises(RecorderError) as exc:
        load_recording("[]")
    assert exc.value.code == "invalid_recording"

    with pytest.raises(RecorderError) as exc:
        load_recording('{"title": "no steps"}')
    assert exc.value.code == "invalid_recording"


def test_acceptance_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Acceptance item 8:
    # main(['rec.json']) prints the script to stdout, warnings to stderr one per line, and returns 0; invalid input returns 2
    rec_file = tmp_path / "rec.json"
    data = {
        "title": "cli test",
        "steps": [
            {"type": "scroll"},
            {"type": "navigate", "url": "https://example.com"},
        ],
    }
    rec_file.write_text(json.dumps(data), encoding="utf-8")

    # Run main
    ret = main([str(rec_file)])
    assert ret == 0
    captured = capsys.readouterr()
    assert "unsupported_step:scroll" in captured.err
    assert "page.goto('https://example.com')" in captured.out

    # Invalid input
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{not valid json", encoding="utf-8")
    ret_err = main([str(invalid_file)])
    assert ret_err == 2

    # Non-existent file
    ret_missing = main([str(tmp_path / "missing.json")])
    assert ret_missing == 2

    # Output to file
    out_script = tmp_path / "out.py"
    ret_out = main([str(rec_file), "-o", str(out_script)])
    assert ret_out == 0
    assert out_script.exists()
    assert "page.goto('https://example.com')" in out_script.read_text(encoding="utf-8")


def test_empty_steps_script() -> None:
    rec = Recording(title="empty", steps=())
    script = to_playwright_python(rec)
    expected = (
        "import os\n"
        "from playwright.sync_api import sync_playwright\n\n\n"
        "def run() -> None:\n"
        "    with sync_playwright() as p:\n"
        "        browser = p.chromium.launch(headless=True)\n"
        "        page = browser.new_page()\n"
        "        browser.close()\n\n\n"
        "if __name__ == '__main__':\n"
        "    run()\n"
    )
    assert script == expected


def test_two_secret_fields() -> None:
    steps = (
        Step(kind="fill", selector="input[name=password]", value="p1"),
        Step(kind="fill", selector="#token_code", value="secret123"),
        Step(kind="fill", selector="input[name=password]", value="p2"),  # repeat selector
    )
    rec = Recording(title="secrets", steps=steps)
    script = to_playwright_python(rec)
    assert "RECORDER_SECRET_1" in script
    assert "RECORDER_SECRET_2" in script
    assert "RECORDER_SECRET_3" not in script
    assert "p1" not in script and "p2" not in script and "secret123" not in script


def test_unicode_and_backslashes() -> None:
    val = 'こんにちは "world" \\ 🚀'
    sel = r"""button[data-id="quote\'"]"""
    rec = Recording(title="unicode", steps=(Step(kind="fill", selector=sel, value=val),))
    script = to_playwright_python(rec)
    ast.parse(script)
    assert "こんにちは" in script


def test_native_recording_with_unknown_kind() -> None:
    data = {"title": "bad_kind", "steps": [{"kind": "unknown_magic"}]}
    with pytest.raises(RecorderError) as exc:
        load_recording(json.dumps(data))
    assert exc.value.code == "invalid_recording"


def test_native_recording_parsing() -> None:
    data = {
        "title": "native test",
        "viewport": [1280, 720],
        "steps": [
            {"kind": "goto", "url": "https://example.org"},
            {"kind": "fill", "selector": "#secret_key", "value": "xyz"},
            {"kind": "check", "selector": "#agree"},
            {"kind": "select", "selector": "#country", "value": "FR"},
            {"kind": "wait_for", "selector": "#done"},
            {"kind": "click", "selector": "#submit", "double_click": True},
        ],
    }
    rec = load_recording(json.dumps(data))
    assert rec.viewport == (1280, 720)
    script = to_playwright_python(rec, headless=False)
    assert "headless=False" in script
    assert "viewport={'width': 1280, 'height': 720}" in script
    assert ".select_option('FR')" in script
    assert ".check()" in script
    assert ".wait_for()" in script
    assert ".dblclick()" in script
    assert "RECORDER_SECRET_1" in script
    ast.parse(script)


def test_devtools_text_selector_and_various_steps() -> None:
    data = {
        "title": "devtools extra",
        "steps": [
            {"type": "hover"},  # ignored silently
            {"type": "close"},  # ignored silently
            {"type": "waitForElement", "selectors": [["text/Click me"]]},
            {"type": "doubleClick", "selectors": [["#my-button"]]},  # doubleClick
            {"type": "change", "value": "normal", "selectors": [["#standard"]]},
            {"type": "navigate", "url": "https://example.com/sub"},
            {"type": "otherThing"},
        ],
    }
    rec = from_devtools(data)
    assert rec.steps[0] == Step(kind="wait_for", selector="text=Click me")
    assert rec.steps[1] == Step(kind="click", selector="#my-button", double_click=True)
    assert rec.steps[2] == Step(kind="fill", selector="#standard", value="normal", secret=False)
    assert rec.steps[3] == Step(kind="goto", url="https://example.com/sub")
    assert "unsupported_step:otherThing" in rec.warnings


def test_devtools_error_conditions() -> None:
    with pytest.raises(RecorderError):
        from_devtools({"title": "t", "steps": "not a list"})  # type: ignore
    with pytest.raises(RecorderError):
        from_devtools({"title": "t", "steps": ["not a dict"]})  # type: ignore
    with pytest.raises(RecorderError):
        from_devtools({"title": "t", "steps": [{}]})  # type: ignore
    with pytest.raises(RecorderError):
        from_devtools({"title": "t", "steps": [{"type": "navigate"}]})


def test_native_error_conditions() -> None:
    data = {"title": "t", "steps": ["not an object"]}
    with pytest.raises(RecorderError) as exc:
        load_recording(json.dumps(data))
    assert exc.value.code == "invalid_recording"

    data_no_url = {"title": "t", "steps": [{"kind": "goto"}]}
    with pytest.raises(RecorderError) as exc:
        load_recording(json.dumps(data_no_url))
    assert exc.value.code == "invalid_recording"


def test_cli_help_and_errors(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    # parser error returns 2
    ret = main(["--unknown-flag"])
    assert ret == 2

    # write error in output file
    rec_file = tmp_path / "good.json"
    rec_file.write_text(json.dumps({"title": "t", "steps": []}))
    ret = main([str(rec_file), "-o", str(tmp_path)])  # passing directory as file
    assert ret == 2

    # domain failure in cli (unsafe url)
    bad_rec = tmp_path / "bad_url.json"
    bad_rec.write_text(
        json.dumps({"title": "t", "steps": [{"kind": "goto", "url": "http://example.com"}]})
    )
    # modify file to unsafe url
    bad_rec.write_text(
        json.dumps({"title": "t", "steps": [{"kind": "goto", "url": "javascript:alert(1)"}]})
    )
    ret = main([str(bad_rec)])
    assert ret == 1
