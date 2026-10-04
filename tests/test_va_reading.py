"""VA ID -> verified full report and live material index, with zero archive writes."""

import json
from pathlib import Path

import pytest
from test_va import intake as case_intake
from typer.testing import CliRunner

from vulnarc.cli import app
from vulnarc.storage import digest, dump_yaml, load_yaml
from vulnarc.va import register_case

runner = CliRunner()
intake = case_intake
PRIMARY = "# 主报告\n\n第一段：原始报告。\n```sh\necho not-executed\n```\n\n最后一段。"
TRANSLATION = "# 中文翻译\n\n完整翻译正文。\n\n翻译结束。\n"


@pytest.fixture
def archive(intake, tmp_path):
    data = json.loads(intake.read_text())
    primary = Path(data["case"]["materials"][0]["path"])
    primary.write_text(PRIMARY, encoding="utf-8")
    sha = digest(primary.read_bytes())
    data["case"]["materials"][0]["sha256"] = sha
    data["case"]["evidence"][0]["sha256"] = sha
    data["case"]["ratings"][0]["source"]["sha256"] = sha
    data["case"]["reference_cases"][0]["source"]["sha256"] = sha
    translation = tmp_path / "中文 翻译.md"
    translation.write_text(TRANSLATION, encoding="utf-8")
    attachment = tmp_path / "attachment.tar.gz"
    attachment.write_bytes(b"\x1f\x8b\x00binary-attachment")
    for role, path in [("translation", translation), ("attachment", attachment)]:
        data["case"]["materials"].append(
            {
                "role": role,
                "label": role,
                "path": str(path),
                "sha256": digest(path.read_bytes()),
            }
        )
    intake.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    ws = tmp_path / "private workspace"
    record, folder, _ = register_case(ws, intake)
    return ws, record.id, folder, primary, translation, attachment


def invoke(archive, command, *args):
    ws, record_id, *_ = archive
    return runner.invoke(app, ["va", command, record_id, "-w", str(ws), *args])


def snapshot(root):
    return {
        str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("choice, expected", [("primary", PRIMARY), ("translation", TRANSLATION)])
def test_read_full_body_not_summary_or_snapshot(archive, choice, expected):
    before = snapshot(archive[0].parent)
    result = invoke(archive, "read", "--report", choice)
    assert result.exit_code == 0, result.output
    assert result.stdout == expected
    assert snapshot(archive[0].parent) == before


def test_read_defaults_to_primary(archive):
    result = invoke(archive, "read")
    assert result.exit_code == 0
    assert result.stdout == PRIMARY


def test_show_commands_and_materials_are_current_and_readonly(archive):
    ws, record_id, folder, *sources = archive
    (folder / "materials.md").write_text("stale snapshot")
    before = snapshot(ws.parent)
    for command in ["show", "materials"]:
        result = invoke(archive, command)
        assert result.exit_code == 0, result.output
        for source in sources:
            assert str(source) in result.output
        assert "primary_report" in result.output and "translation" in result.output
        assert "attachment" in result.output
        assert result.output.count("通过（SHA-256 一致）") == 3
        assert "stale snapshot" not in result.output
        if command == "show":
            for choice in ["primary", "translation"]:
                assert f"vulnarc va read {record_id} --report {choice}" in result.output
            assert f"vulnarc va materials {record_id}" in result.output
            assert f"--workspace '{ws}'" in result.output
        assert snapshot(ws.parent) == before


@pytest.mark.parametrize("command", ["read", "materials", "show"])
@pytest.mark.parametrize("problem", ["missing", "hash"])
def test_missing_or_changed_primary_is_explicit_without_writes(archive, command, problem):
    primary = archive[3]
    if problem == "missing":
        primary.unlink()
    else:
        primary.write_text("tampered body")
    before = snapshot(archive[0].parent)
    result = invoke(archive, command)
    assert result.exit_code == 1
    assert str(primary) in result.output
    assert ("缺失" if problem == "missing" else "哈希变化") in result.output
    assert PRIMARY not in result.output and "tampered body" not in result.output
    if command != "read":
        assert str(archive[4]) in result.output and str(archive[5]) in result.output
        assert result.output.count("通过（SHA-256 一致）") == 2
    assert snapshot(archive[0].parent) == before


def test_bad_attachment_does_not_block_good_report_or_hide_entrance(archive):
    archive[5].unlink()
    assert invoke(archive, "read").stdout == PRIMARY
    assert invoke(archive, "read", "--report", "translation").stdout == TRANSLATION
    result = invoke(archive, "show")
    assert result.exit_code == 1
    assert "vulnarc va read" in result.output and "vulnarc va materials" in result.output
    assert "SHA-256 已核对" not in result.output
    assert "缺失" in result.output


def modify_metadata(archive, change):
    path = archive[2] / "metadata.yaml"
    data = load_yaml(path)
    change(data)
    dump_yaml(path, data)


def test_no_translation_is_explicit(archive):
    modify_metadata(
        archive,
        lambda d: d.update(materials=[m for m in d["materials"] if m["role"] != "translation"]),
    )
    result = invoke(archive, "read", "--report", "translation")
    assert result.exit_code == 1 and "未登记 translation" in result.output
    result = invoke(archive, "show")
    assert result.exit_code == 0 and "正文 translation：未登记" in result.output


@pytest.mark.parametrize("choice, index", [("primary", 0), ("translation", 1)])
def test_ambiguous_report_is_not_arbitrarily_selected(archive, choice, index):
    modify_metadata(archive, lambda d: d["materials"].append(d["materials"][index].copy()))
    result = invoke(archive, "read", "--report", choice)
    assert result.exit_code == 1 and "报告不唯一（2 份）" in result.output
    assert PRIMARY not in result.output and TRANSLATION not in result.output


@pytest.mark.parametrize("command", ["read", "materials", "show"])
def test_unknown_id_does_not_create_workspace(tmp_path, command):
    ws = tmp_path / "absent"
    result = runner.invoke(app, ["va", command, "VA-2026-9999", "-w", str(ws)])
    assert result.exit_code == 1 and "record not found" in result.output
    assert not ws.exists()


def test_invalid_report_choice(archive):
    assert invoke(archive, "read", "--report", "attachment").exit_code == 2


@pytest.mark.parametrize(
    "content, suffix, message",
    [
        (b"%PDF-fake", ".pdf", "支持 UTF-8 Markdown/文本"),
        (b"\xff\xfe", ".md", "不是 UTF-8 文本"),
        (b"hello\x1b[2J", ".txt", "终端控制字符"),
        (b"hello\x00world", ".md", "终端控制字符"),
    ],
)
def test_non_text_is_not_emitted_or_opened(archive, content, suffix, message):
    replacement = archive[3].with_suffix(suffix)
    replacement.write_bytes(content)

    def change(data):
        data["materials"][0].update(path=str(replacement), sha256=digest(content))

    modify_metadata(archive, change)
    before = snapshot(archive[0].parent)
    result = invoke(archive, "read")
    assert result.exit_code == 1 and message in result.output
    assert snapshot(archive[0].parent) == before


def test_missing_hash_is_not_a_success(archive):
    modify_metadata(archive, lambda d: d["materials"][0].update(sha256=None))
    result = invoke(archive, "read")
    assert result.exit_code == 1 and "缺少 SHA-256" in result.output
    result = invoke(archive, "materials")
    assert result.exit_code == 1 and "缺少路径或 SHA-256" in result.output


def test_permission_failure_is_reported_per_material(archive, monkeypatch):
    original = Path.read_bytes

    def denied(path):
        if path == archive[3]:
            raise PermissionError("synthetic denied")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", denied)
    result = invoke(archive, "materials")
    assert result.exit_code == 1 and "读取失败" in result.output
    assert result.output.count("通过（SHA-256 一致）") == 2
    result = invoke(archive, "read")
    assert result.exit_code == 1 and "synthetic denied" in result.output


def test_report_reads_one_verified_snapshot(archive, monkeypatch):
    original = Path.read_bytes
    calls = []

    def observed(path):
        content = original(path)
        if path == archive[3]:
            calls.append(path)
            path.write_text("changed after read")
        return content

    monkeypatch.setattr(Path, "read_bytes", observed)
    result = invoke(archive, "read")
    assert result.exit_code == 0 and result.stdout == PRIMARY
    assert calls == [archive[3]]


def test_duplicate_id_fails_instead_of_selecting_first(archive, tmp_path):
    copy = archive[0] / "other/metadata.yaml"
    copy.parent.mkdir()
    copy.write_bytes((archive[2] / "metadata.yaml").read_bytes())
    result = invoke(archive, "read")
    assert result.exit_code == 1 and "duplicate id" in result.output


def test_non_va_record_is_not_read_as_va(archive):
    modify_metadata(archive, lambda d: d.update(kind="report"))
    result = invoke(archive, "read")
    assert result.exit_code == 1 and PRIMARY not in result.output
