"""Synthetic reading contracts; no real report content is used in tests."""

import json
import os
import shlex
import subprocess
from pathlib import Path

import pytest
import test_va
from rich.text import Text
from typer.testing import CliRunner

from vulnarc.cli import app
from vulnarc.materials import material_problem, read_material
from vulnarc.reading import visible_text
from vulnarc.storage import digest, dump_yaml, load_yaml
from vulnarc.va import register_case

intake = test_va.intake  # Reuse only the existing synthetic fixture.
runner = CliRunner()
BODY = "# 主报告\n\n| 栏 | 值 |\n|---|---|\n| 中文 | 保留 |\n\n```sh\necho inert\n```\n[链接](https://example.invalid)\n"


@pytest.fixture
def case(intake, tmp_path):
    data = json.loads(intake.read_text())
    report = Path(data["case"]["materials"][0]["path"])
    report.write_text(BODY, encoding="utf-8")
    fingerprint = digest(report.read_bytes())
    data["case"]["materials"][0]["sha256"] = fingerprint
    for proof in [
        *data["case"]["evidence"],
        data["case"]["ratings"][0]["source"],
        data["case"]["reference_cases"][0]["source"],
    ]:
        proof["sha256"] = fingerprint
    translation = tmp_path / "translation.md"
    translation.write_text("# Translation\nComplete translated text\n", encoding="utf-8")
    attachment = tmp_path / "attachment.txt"
    attachment.write_text("synthetic attachment\n", encoding="utf-8")
    for role, path in [("translation", translation), ("attachment", attachment)]:
        data["case"]["materials"].append(
            {"role": role, "label": role, "path": str(path), "sha256": digest(path.read_bytes())}
        )
    intake.write_text(json.dumps(data))
    workspace = tmp_path / "nondefault workspace 'quoted' 中文"
    record, folder, _ = register_case(workspace, intake)
    return workspace, record.id, folder, report, translation, attachment


def invoke(case, command, *options):
    return runner.invoke(app, ["va", command, case[1], "--workspace", str(case[0]), *options])


def mutate(case, change):
    path = case[2] / "metadata.yaml"
    data = load_yaml(path)
    change(data)
    dump_yaml(path, data)


def set_body(case, content):
    case[3].write_bytes(content)
    mutate(case, lambda data: data["materials"][0].update(sha256=digest(content)))


def snapshot(root):
    return {
        str(p.relative_to(root)): (
            p.stat().st_mtime_ns,
            digest(p.read_bytes()) if p.is_file() else None,
        )
        for p in root.rglob("*")
    }


@pytest.mark.parametrize(
    "options,index",
    [
        ([], 3),
        (["--report", "primary"], 3),
        (["--report", "translation"], 4),
        (["--material", "1"], 3),
        (["--report", "translation", "--material", "2"], 4),
    ],
)
def test_complete_report_and_separate_streams(case, options, index):
    expected = case[index].read_text()
    result = invoke(case, "read", *options)
    assert result.exit_code == 0, result.output
    assert result.stdout == expected
    assert case[1] in result.stderr and str(case[index]) in result.stderr
    assert "SHA-256 已核对" in result.stderr
    assert "摘要" not in result.stdout


@pytest.mark.parametrize(
    "content",
    [
        b"",
        BODY.encode(),
        b"\xef\xbb\xbf" + BODY.encode(),
        ("# 长文\n" + "正文\n" * 2500 + "FINAL-NO-NEWLINE").encode(),
        b"# CRLF\r\n\tcode\r\nend",
        "# 中文没有末尾换行".encode(),
    ],
)
def test_full_text_encoding_and_whitespace(case, content):
    set_body(case, content)
    result = invoke(case, "read")
    assert result.exit_code == 0, result.output
    assert result.stdout_bytes.decode("utf-8") == content.decode("utf-8-sig")


@pytest.mark.parametrize(
    "options",
    [
        ["--report", "invalid"],
        ["--material", "0"],
        ["--material", "-1"],
        ["--material", "4"],
        ["--material", "2"],
        ["--report", "translation", "--material", "1"],
        ["--material", "not-int"],
        ["--unknown"],
        ["--ignore-hash"],
    ],
)
def test_parameter_errors(case, options):
    result = invoke(case, "read", *options)
    assert result.exit_code == 2
    assert "SHA-256 已核对" not in result.output


@pytest.mark.parametrize("report,original_index", [("primary", 0), ("translation", 1)])
def test_ambiguity_uses_full_material_list_numbers(case, report, original_index):
    def duplicate(data):
        data["materials"].append({**data["materials"][original_index], "label": "second candidate"})

    mutate(case, duplicate)
    result = invoke(case, "read", "--report", report)
    assert result.exit_code == 2 and result.stdout == ""
    assert f"{original_index + 1}." in result.stderr and "4. second candidate" in result.stderr
    assert "--material N" in result.stderr
    chosen = invoke(case, "read", "--report", report, "--material", "4")
    assert chosen.exit_code == 0
    assert chosen.stdout == case[original_index + 3].read_text()


def test_missing_translation(case):
    mutate(case, lambda data: data["materials"].pop(1))
    result = invoke(case, "read", "--report", "translation")
    assert result.exit_code == 1 and result.stdout == ""
    assert "未登记 translation" in result.stderr


@pytest.mark.parametrize("command", ["show", "read", "materials"])
@pytest.mark.parametrize(
    "problem",
    [
        "not_found",
        "wrong_kind",
        "broken_yaml",
        "nonmapping",
        "missing_primary",
        "bad_hash_format",
        "bad_utf8_metadata",
    ],
)
def test_case_input_errors(case, command, problem):
    if problem == "not_found":
        case = (case[0], "VA-2026-9999", *case[2:])
    elif problem == "wrong_kind":
        mutate(case, lambda data: data.update(kind="report"))
    elif problem == "broken_yaml":
        (case[2] / "metadata.yaml").write_text("materials: [broken\n")
    elif problem == "nonmapping":
        (case[2] / "metadata.yaml").write_text("[]\n")
    elif problem == "missing_primary":
        mutate(case, lambda data: data["materials"][0].update(role="attachment"))
    elif problem == "bad_hash_format":
        mutate(case, lambda data: data["materials"][0].update(sha256="invalid"))
    else:
        (case[2] / "metadata.yaml").write_bytes(b"\xff\xfe")
    result = invoke(case, command)
    assert result.exit_code == 1, result.output
    assert result.stdout == ""
    assert "SHA-256 已核对" not in result.output


@pytest.mark.parametrize("command", ["show", "read", "materials"])
@pytest.mark.parametrize("force_color", [False, True])
def test_formal_entry_requires_explicit_workspace(command, tmp_path, monkeypatch, force_color):
    monkeypatch.setenv("TERM", "xterm-256color" if force_color else "dumb")
    if force_color:
        monkeypatch.setenv("FORCE_COLOR", "1")
    else:
        monkeypatch.delenv("FORCE_COLOR", raising=False)
    before = snapshot(tmp_path)
    result = runner.invoke(app, ["va", command, "VA-2026-0001"])
    assert result.exit_code == 2 and "--workspace" in Text.from_ansi(result.output).plain
    if force_color:
        assert "\x1b[" in result.output  # Exercise Rich's styled option fragments.
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "problem,expected",
    [
        ("missing", "原件路径缺失"),
        ("directory", "不是文件"),
        ("changed", "SHA-256 变化"),
        ("no_hash", "缺少原件路径或"),
        ("relative", "不是绝对路径"),
        ("permission", "原件读取失败"),
        ("utf8", "有效 UTF-8"),
        ("nul", "材料类型"),
        ("pdf", "材料类型"),
        ("pdf_suffix", "材料类型"),
    ],
)
def test_selected_material_failure_outputs_no_body(case, monkeypatch, problem, expected):
    if problem == "missing":
        case[3].unlink()
    elif problem == "directory":
        case[3].unlink()
        case[3].mkdir()
    elif problem == "changed":
        case[3].write_text("changed after registration")
    elif problem == "no_hash":
        mutate(case, lambda data: data["materials"][0].update(sha256=None))
    elif problem == "relative":
        mutate(case, lambda data: data["materials"][0].update(path=case[3].name))
    elif problem == "permission":
        original = Path.read_bytes

        def denied(path):
            if path == case[3]:
                raise PermissionError("synthetic denied")
            return original(path)

        monkeypatch.setattr(Path, "read_bytes", denied)
    elif problem == "utf8":
        set_body(case, b"\xff")
    elif problem == "nul":
        set_body(case, b"valid UTF-8\x00binary")
    elif problem == "pdf":
        set_body(case, b"%PDF-1.7\nsynthetic text")
    else:
        pdf = case[3].with_suffix(".pdf")
        pdf.write_text("looks textual")
        mutate(
            case,
            lambda data: data["materials"][0].update(
                path=str(pdf), sha256=digest(pdf.read_bytes())
            ),
        )
    result = invoke(case, "read")
    assert result.exit_code == 1 and result.stdout == ""
    assert expected in result.stderr and "原件" in result.stderr
    assert "SHA-256 已核对" not in result.stderr


@pytest.mark.parametrize("problem", ["missing", "hash", "no_hash", "permission", "relative"])
def test_list_contains_every_item_and_report_ignores_unrelated_failure(case, monkeypatch, problem):
    if problem == "missing":
        case[5].unlink()
    elif problem == "hash":
        case[5].write_text("changed")
    elif problem == "no_hash":
        mutate(case, lambda data: data["materials"][2].update(sha256=None))
    elif problem == "relative":
        mutate(case, lambda data: data["materials"][2].update(path=case[5].name))
    else:
        original = Path.read_bytes

        def denied(path):
            if path == case[5]:
                raise PermissionError("synthetic denied")
            return original(path)

        monkeypatch.setattr(Path, "read_bytes", denied)
    read = invoke(case, "read")
    assert read.exit_code == 0 and read.stdout == BODY
    translated = invoke(case, "read", "--report", "translation")
    assert translated.exit_code == 0
    shown = invoke(case, "show")
    assert shown.exit_code == 0 and "未校验" in shown.output
    assert "SHA-256 已核对" not in shown.output
    listed = invoke(case, "materials")
    assert listed.exit_code == 1
    assert all(f"{i}. " in listed.stdout for i in [1, 2, 3])
    assert listed.stdout.count("SHA-256 已核对") == 2
    assert str(case[4]) in listed.stdout


def test_missing_selected_primary_does_not_block_translation(case):
    case[3].unlink()
    assert invoke(case, "read").exit_code == 1
    assert invoke(case, "read", "--report", "translation").exit_code == 0
    assert invoke(case, "show").exit_code == 0
    assert invoke(case, "materials").exit_code == 1
    assert runner.invoke(app, ["va", "check", "-w", str(case[0])]).exit_code == 1


def test_materials_success_and_raw_hash_of_bom(case):
    set_body(case, b"\xef\xbb\xbf" + BODY.encode())
    result = invoke(case, "materials")
    assert result.exit_code == 0
    assert result.stdout.count("SHA-256 已核对") == 3
    assert all(str(p) in result.stdout for p in case[3:])


def test_checked_bytes_are_the_only_report_read(case, monkeypatch):
    original = Path.read_bytes
    reads = []

    def changing(path):
        data = original(path)
        if path == case[3]:
            reads.append(path)
            path.write_text("changed immediately after read")
        return data

    monkeypatch.setattr(Path, "read_bytes", changing)
    result = invoke(case, "read")
    assert result.exit_code == 0 and result.stdout == BODY
    assert reads == [case[3]]
    assert invoke(case, "read").exit_code == 1


def test_no_source_reads_in_overview(case, monkeypatch):
    original = Path.read_bytes

    def metadata_only(path):
        assert path not in case[3:], "show must not inspect original materials"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", metadata_only)
    result = invoke(case, "show")
    assert result.exit_code == 0
    assert case[1] in result.output and "Existing report archive" in result.output
    assert "VA:example:CAND-01" in result.output and "reporter" in result.output
    assert "未校验" in result.output and "全库完整性校验" in result.output
    assert "SHA-256 已核对" not in result.output


def test_overview_commands_reuse_actual_quoted_workspace(case):
    result = invoke(case, "show")
    commands = [
        line.split("：", 1)[1] for line in result.stdout.splitlines() if "：vulnarc va " in line
    ]
    assert len(commands) == 4
    for command in commands:
        args = shlex.split(command)
        assert args[args.index("--workspace") + 1] == str(case[0].resolve())
        copied = runner.invoke(app, args[1:])
        assert copied.exit_code == 0, copied.output


@pytest.mark.parametrize(
    "command,options",
    [("show", []), ("materials", []), ("read", []), ("read", ["--report", "translation"])],
)
def test_zero_writes_hash_files_and_mtime(case, command, options):
    root = case[0].parent
    before = snapshot(root)
    assert invoke(case, command, *options).exit_code == 0
    assert snapshot(root) == before


def test_controls_are_visible_without_markdown_execution(case, monkeypatch):
    content = BODY + "\x1b]52;c;inert\x07\x9b31m\u202e\rEND"
    set_body(case, content.encode())

    def forbidden(*args, **kwargs):
        raise AssertionError("report caused external execution")

    monkeypatch.setattr(os, "system", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    result = invoke(case, "read")
    assert result.exit_code == 0
    assert result.stdout == BODY + r"\x1b]52;c;inert\x07\x9b31m\u202e\x0dEND"
    assert "\x1b" not in result.stdout and "\x9b" not in result.stdout


def test_metadata_and_candidate_control_characters_are_visible(case):
    def controls(data):
        data["title"] += "\x1b[31m\u202e"
        data["materials"][0]["label"] = "label\x1b\x9b\u202e\n"
        data["materials"].append({**data["materials"][0], "path": "/inert\x1b\u202e"})

    mutate(case, controls)
    for command in ["show", "materials", "read"]:
        result = invoke(case, command)
        assert "\x1b" not in result.output and "\x9b" not in result.output
        assert "\u202e" not in result.output
        assert r"\x1b" in result.output and r"\u202e" in result.output


@pytest.mark.parametrize(
    "content,expected",
    [
        ("\x00\x01\x1b\x7f\x80\x9f", r"\x00\x01\x1b\x7f\x80\x9f"),
        ("\u061c\u200e\u2066\u2069", r"\u061c\u200e\u2066\u2069"),
    ],
)
def test_visible_control_ranges(content, expected):
    assert visible_text(content, multiline=True) == expected


def test_read_material_shared_hash_and_legacy_existence_semantics(tmp_path, monkeypatch):
    source = tmp_path / "synthetic.md"
    source.write_text("one\r\ntwo\n")
    content = source.read_bytes()
    calls = []
    original = Path.read_bytes

    def counted(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", counted)
    assert material_problem(str(source), None) is None
    assert calls == []  # Original RPT existence-only behavior is unchanged.
    assert read_material(str(source), digest(content), 2) == (None, content)
    assert calls == [source]  # Hash and evidence-line checks use the same bytes.
