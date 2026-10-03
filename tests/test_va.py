import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vulnarc.cli import app
from vulnarc.models import CaseDetails
from vulnarc.storage import digest, load_yaml, validate_workspace
from vulnarc.va import register_case

runner = CliRunner()


@pytest.fixture
def intake(tmp_path, monkeypatch):
    monkeypatch.setattr("vulnarc.va.local_year", lambda: "2026")
    report = tmp_path / "existing-report.md"
    report.write_text("# Existing report\nCWE-78\nCVSS 3.1 reporter score\n")
    proof = {
        "type": "existing_report",
        "path": str(report),
        "sha256": digest(report.read_bytes()),
        "line": 2,
    }
    data = {
        "project": "example",
        "title": "Existing report archive",
        "purpose": "own_research",
        "source_key": "VA:example:CAND-01",
        "legacy_ids": ["CAND-01"],
        "category": "report archive",
        "cwe": ["CWE-78"],
        "ratings": [
            {
                "version": "3.1",
                "score": 9.7,
                "vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:H/A:H",
                "attribution": "reporter",
                "source": proof,
            }
        ],
        "reference_cases": [{"identifier": "CVE-2020-26222", "source": proof}],
        "materials": [
            {
                "role": "primary_report",
                "label": "report",
                "path": str(report),
                "sha256": proof["sha256"],
            }
        ],
        "evidence": [proof],
        "summary": "Archive supplied documentation, no revalidation.",
        "learning_notes": ["Preserve the distinction between a source claim and a new test."],
    }
    path = tmp_path / "intake.json"
    path.write_text(json.dumps({"schema": "vulnarc-case-intake-v1", "case": data}))
    return path


def run(intake, ws, *extra):
    return runner.invoke(app, ["va", "register", str(intake), "-w", str(ws), *extra])


def test_preview_does_not_allocate_or_write(intake, tmp_path):
    ws = tmp_path / "private"
    result = run(intake, ws)
    assert result.exit_code == 0, result.output
    assert "尚未分配编号" in result.output
    assert not ws.exists()


def test_registration_receipt_and_five_part_case(intake, tmp_path):
    ws = tmp_path / "private"
    result = run(intake, ws, "--apply")
    assert result.exit_code == 0, result.output
    assert "已为您分配好 VA 编号" in result.output
    assert "VA-2026-0001" in result.output and "报告自评" in result.output
    assert "本次未向外部平台发送" in result.output
    folder = ws / "cases/private/VA-2026-0001"
    assert {p.name for p in folder.iterdir()} == {
        "metadata.yaml",
        "case.md",
        "materials.md",
        "timeline.md",
        "learning.md",
    }
    record = load_yaml(folder / "metadata.yaml")
    assert record["assigned_identifiers"] == []
    assert record["submission_status"] == "unknown"
    assert record["reference_cases"][0]["identifier"] == "CVE-2020-26222"
    assert validate_workspace(ws) == []
    listed = runner.invoke(app, ["va", "list", "-w", str(ws)])
    assert "VA-2026-0001" in listed.output


def test_repeat_intake_reuses_id_and_manual_notes(intake, tmp_path):
    ws = tmp_path / "private"
    _, folder, _ = register_case(ws, intake)
    (folder / "learning.md").write_text("user notes stay")
    before = {str(p): p.read_bytes() for p in ws.rglob("*") if p.is_file()}
    result = run(intake, ws, "--apply")
    assert result.exit_code == 0, result.output
    assert "未重复分配" in result.output
    assert "已为您分配好" not in result.output
    assert before == {str(p): p.read_bytes() for p in ws.rglob("*") if p.is_file()}


def test_modified_manifest_is_not_an_overwrite(intake, tmp_path):
    ws = tmp_path / "private"
    register_case(ws, intake)
    changed = json.loads(intake.read_text())
    changed["case"]["title"] = "different"
    intake.write_text(json.dumps(changed))
    result = run(intake, ws, "--apply")
    assert result.exit_code == 1
    assert "no overwrite" in result.output


def test_source_changed_cannot_confirm_registration(intake, tmp_path):
    data = json.loads(intake.read_text())
    Path(data["case"]["materials"][0]["path"]).write_text("changed")
    ws = tmp_path / "private"
    result = run(intake, ws, "--apply")
    assert result.exit_code == 1
    assert "已为您分配好" not in result.output
    assert not ws.exists()


def test_reference_is_not_assigned_cve(intake):
    data = json.loads(intake.read_text())["case"]
    data["assigned_identifiers"] = ["CVE-2020-26222"]
    with pytest.raises(ValueError, match="reference identifier"):
        CaseDetails.model_validate(data)


def test_invalid_input_has_no_success_or_workspace(intake, tmp_path):
    data = json.loads(intake.read_text())
    data["case"]["ratings"][0]["version"] = "4.0"
    intake.write_text(json.dumps(data))
    ws = tmp_path / "private"
    result = run(intake, ws, "--apply")
    assert result.exit_code == 1
    assert not ws.exists()


def test_failed_document_write_does_not_announce_allocation(intake, tmp_path, monkeypatch):
    ws = tmp_path / "private"
    monkeypatch.setattr(
        "vulnarc.va.render_documents",
        lambda _: (_ for _ in ()).throw(OSError("simulated storage failure")),
    )
    result = run(intake, ws, "--apply")
    assert result.exit_code == 1
    assert "已为您分配好" not in result.output
    assert not (ws / "cases/private/VA-2026-0001").exists()


def test_id_is_not_reused_after_deletion(intake, tmp_path):
    ws = tmp_path / "private"
    _, folder, _ = register_case(ws, intake)
    shutil.rmtree(folder)
    record, _, _ = register_case(ws, intake)
    assert record.id == "VA-2026-0002"


def test_two_writers_get_different_ids(intake, tmp_path):
    ws = tmp_path / "private"
    second = deepcopy(json.loads(intake.read_text()))
    second["case"]["source_key"] = "VA:example:CAND-02"
    other = tmp_path / "other.json"
    other.write_text(json.dumps(second))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda p: register_case(ws, p)[0].id, [intake, other]))
    assert set(results) == {"VA-2026-0001", "VA-2026-0002"}
    assert validate_workspace(ws) == []


def test_show_is_readonly_and_validator_detects_changed_source(intake, tmp_path):
    ws = tmp_path / "private"
    record, _, _ = register_case(ws, intake)
    before = {str(p): p.read_bytes() for p in ws.rglob("*") if p.is_file()}
    result = runner.invoke(app, ["va", "show", record.id, "-w", str(ws)])
    assert result.exit_code == 0
    assert before == {str(p): p.read_bytes() for p in ws.rglob("*") if p.is_file()}
    data = json.loads(intake.read_text())
    Path(data["case"]["materials"][0]["path"]).write_text("changed later")
    assert any("source hash changed" in e for e in validate_workspace(ws))


def test_submitted_requires_provenance(intake, tmp_path):
    data = json.loads(intake.read_text())
    data["case"]["submission_status"] = "submitted"
    intake.write_text(json.dumps(data))
    assert run(intake, tmp_path / "private", "--apply").exit_code == 1
    data["case"]["submission_basis"] = "user_instruction"
    data["case"]["submission_note"] = "Administrative state requested by user; receipt pending."
    data["case"]["evidence"][0]["type"] = "user_instruction"
    intake.write_text(json.dumps(data))
    result = run(intake, tmp_path / "private", "--apply")
    assert result.exit_code == 0, result.output
    assert "按用户口径" in result.output


def test_check_detects_incomplete_documents(intake, tmp_path):
    ws = tmp_path / "private"
    _, folder, _ = register_case(ws, intake)
    (folder / "timeline.md").unlink()
    assert any("missing case document timeline.md" in e for e in validate_workspace(ws))
