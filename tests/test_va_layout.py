"""Synthetic terminal layout contracts, separate from byte-preserving export tests."""

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest
import test_va_reading
from rich.cells import cell_len
from rich.console import Console

from vulnarc.display import pretty_enabled, render_report
from vulnarc.reading import ReportKind, load_case, select_report

intake = test_va_reading.intake
case = test_va_reading.case
invoke = test_va_reading.invoke
mutate = test_va_reading.mutate
set_body = test_va_reading.set_body
snapshot = test_va_reading.snapshot


def render(case, text, *, terminal_width=120, width=None, report=ReportKind.PRIMARY):
    _, record = load_case(case[0], case[1])
    ref = select_report(record, report, None)
    stdout = io.StringIO()
    stderr = io.StringIO()
    out_console = Console(file=stdout, width=terminal_width, color_system=None)
    err_console = Console(file=stderr, width=terminal_width, color_system=None)
    render_report(
        record, ref, report, text, width=width, console=out_console, metadata_console=err_console
    )
    return stdout.getvalue(), stderr.getvalue()


@pytest.mark.parametrize(
    "tty,pretty,raw,expected",
    [
        (False, False, False, False),
        (True, False, False, True),
        (False, True, False, True),
        (True, False, True, False),
        (False, False, True, False),
        (True, True, True, False),
    ],
)
def test_mode_detection(monkeypatch, tty, pretty, raw, expected):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: tty)
    assert pretty_enabled(pretty=pretty, raw=raw) is expected


def test_pretty_markdown_blocks_and_metadata_stream(case):
    result = invoke(case, "read", "--pretty")
    assert result.exit_code == 0, result.output
    assert "正文 · Markdown" in result.stdout and "╭" in result.stdout and "╰" in result.stdout
    assert "# 主报告" not in result.stdout and "```sh" not in result.stdout
    assert "中文" in result.stdout and "栏" in result.stdout and "echo inert" in result.stdout
    assert "example.invalid" in result.stdout
    assert case[1] in result.stderr and "SHA-256 已核对" in result.stderr
    assert "--report translation" in result.stderr and "● 主报告" in result.stderr
    assert str(case[3]) not in result.stdout
    assert "\x1b]8;" not in result.output  # No terminal hyperlinks are emitted.


def test_terminal_default_and_raw_override(case, monkeypatch):
    monkeypatch.setattr("vulnarc.display.sys.stdout.isatty", lambda: True)
    # CliRunner replaces stdout: patch the mode at its boundary for this integration check.
    monkeypatch.setattr("vulnarc.va.pretty_enabled", lambda **kw: not kw["raw"])
    formatted = invoke(case, "read")
    assert formatted.exit_code == 0 and "正文 · Markdown" in formatted.stdout
    plain = invoke(case, "read", "--raw")
    assert plain.exit_code == 0 and plain.stdout == test_va_reading.BODY


def test_pipe_default_remains_exact_text(case):
    result = invoke(case, "read")
    assert result.exit_code == 0 and result.stdout == test_va_reading.BODY
    assert "正文 · Markdown" not in result.stdout and "╭" not in result.stdout


def test_translation_selection_remains_explicit(case):
    result = invoke(case, "read", "--pretty", "--report", "translation")
    assert result.exit_code == 0
    assert "Translation" in result.stdout and "Complete translated text" in result.stdout
    assert "● 已登记翻译" in result.stderr and "--report primary" in result.stderr
    assert "SHA-256 已核对" in result.stderr


def test_no_unregistered_translation_tab(case):
    mutate(case, lambda data: data["materials"].pop(1))
    result = invoke(case, "read", "--pretty")
    assert result.exit_code == 0 and "尚未登记翻译" in result.stderr
    assert "--report translation" not in result.stderr


@pytest.mark.parametrize(
    "options",
    [
        ["--pretty", "--raw"],
        ["--width", "39"],
        ["--width", "201"],
        ["--width", "invalid"],
    ],
)
def test_layout_parameter_errors(case, options):
    before = snapshot(case[0].parent)
    result = invoke(case, "read", *options)
    assert result.exit_code == 2
    assert "SHA-256 已核对" not in result.output
    assert before == snapshot(case[0].parent)


@pytest.mark.parametrize(
    "terminal_width,width,expected",
    [(240, None, 100), (80, None, 80), (120, 60, 60), (50, 100, 50), (40, None, 40)],
)
def test_reading_width_is_bounded_and_folds_long_code(case, terminal_width, width, expected):
    text = "# 标题\n\n```text\n" + "x" * 220 + "CODE-END\n```\n\nBODY-END"
    out, err = render(case, text, terminal_width=terminal_width, width=width)
    assert all(cell_len(line) <= expected for line in (out + err).splitlines())
    flattened = out.replace("│", "").replace(" ", "").replace("\n", "")
    assert "CODE-END" in flattened and "BODY-END" in flattened
    assert "x" * 220 in flattened  # No long code content was cropped.


def test_table_cells_wrap_instead_of_disappearing(case):
    text = "| 列 | 内容 |\n|---|---|\n| 中文 | " + "z" * 120 + "CELL-END |\n"
    out, _ = render(case, text, terminal_width=60)
    flattened = out.replace("│", "").replace("┃", "").replace(" ", "").replace("\n", "")
    assert "中文" in out and "CELL-END" in flattened and "z" * 120 in flattened


def test_metadata_is_literal_and_control_escaped(case):
    mutate(case, lambda data: data.update(title="[red]literal title[/red]\x1b[31m\u202e"))
    result = invoke(case, "read", "--pretty")
    assert result.exit_code == 0
    assert "[red]literal title[/red]" in result.stderr
    assert r"\x1b[31m" in result.stderr and r"\u202e" in result.stderr
    assert "\x1b" not in result.output and "\u202e" not in result.output


def test_pretty_failure_has_no_panel_or_verified_badge(case):
    case[3].write_text("changed since registration")
    result = invoke(case, "read", "--pretty")
    assert result.exit_code == 1 and result.stdout == ""
    assert "SHA-256 已核对" not in result.output and "正文 · Markdown" not in result.output


def test_pretty_is_readonly_and_inert(case, monkeypatch):
    before = snapshot(case[0].parent)

    def forbidden(*args, **kwargs):
        raise AssertionError("renderer started a subprocess or network operation")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    result = invoke(case, "read", "--pretty")
    assert result.exit_code == 0
    assert before == snapshot(case[0].parent)


def test_controls_remain_visible_in_pretty_body(case):
    set_body(case, b"# text\n\x1b]52;c;inert\x07\nEND")
    result = invoke(case, "read", "--pretty")
    assert result.exit_code == 0
    assert "\x1b" not in result.output and r"\x1b]52;c;inert\x07" in result.stdout


@pytest.mark.parametrize("code", [0x061C, 0x200F, 0x202E, 0x2066])
def test_markdown_decoded_bidi_entities_remain_visible(case, code):
    set_body(case, f"# text\n&#x{code:x};\nEND".encode())
    result = invoke(case, "read", "--pretty")
    assert result.exit_code == 0
    assert chr(code) not in result.output
    assert f"\\u{code:04x}" in result.stdout


def test_pretty_uses_one_checked_read(case, monkeypatch):
    original = Path.read_bytes
    reads = []

    def changed_after_read(path):
        content = original(path)
        if path == case[3]:
            reads.append(path)
            path.write_text("changed immediately afterward")
        return content

    monkeypatch.setattr(Path, "read_bytes", changed_after_read)
    result = invoke(case, "read", "--pretty")
    assert result.exit_code == 0 and "主报告" in result.stdout and "echo inert" in result.stdout
    assert reads == [case[3]]
