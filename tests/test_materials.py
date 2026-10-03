from copy import deepcopy

import pytest
from typer.testing import CliRunner

from vulnarc.cli import app
from vulnarc.models import CaseDetails
from vulnarc.storage import digest, dump_yaml, validate_workspace
from vulnarc.va import register_case, verify_materials


@pytest.fixture
def sources(tmp_path):
    source = tmp_path / "original.md"
    source.write_text("first\nsecond\n", encoding="utf-8")
    proof = {"type": "existing_report", "path": str(source),
             "sha256": digest(source.read_bytes()), "line": 2}
    details = {"project": "synthetic", "title": "archive", "purpose": "study",
               "source_key": "VA:synthetic:1", "category": "archive", "summary": "notes",
               "materials": [{"role": "primary_report", "label": "original",
                              "path": str(source), "sha256": proof["sha256"]}],
               "evidence": [proof]}
    return source, details


@pytest.mark.parametrize("problem,expected", [
    ("missing", "missing absolute source path"),
    ("relative", "missing absolute source path"),
    ("hash", "source hash changed"),
    ("no_hash", "case material/evidence needs a path and SHA-256"),
    ("line", "source line out of range"),
])
def test_va_original_rules(sources, problem, expected):
    source, data = sources
    if problem == "missing":
        source.unlink()
    elif problem == "relative":
        data["materials"][0]["path"] = source.name
    elif problem == "hash":
        source.write_text("changed")
    elif problem == "no_hash":
        data["evidence"][0].pop("sha256")
    elif problem == "line":
        data["evidence"][0]["line"] = 3
    with pytest.raises(ValueError, match=expected):
        verify_materials(CaseDetails.model_validate(data))


def test_va_valid_boundary_and_note_only_proof(sources):
    _, data = sources
    verify_materials(CaseDetails.model_validate(data))
    data["evidence"] = [{"type": "local_ledger", "note": "note only"}]
    with pytest.raises(ValueError, match="needs a path and SHA-256"):
        verify_materials(CaseDetails.model_validate(data))


@pytest.mark.parametrize("kind", ["original", "related", "submission", "status", "history"])
@pytest.mark.parametrize("problem", ["valid", "missing", "hash", "line", "no_hash"])
def test_report_material_and_evidence_rules(tmp_path, kind, problem):
    source = tmp_path / "source.md"
    source.write_text("one\ntwo\n")
    ref = {"path": source.name, "sha256": digest(source.read_bytes())}
    proof = {"type": "local_ledger", **ref, "line": 2}
    if problem == "missing":
        source.unlink()
    elif problem == "hash":
        source.write_text("changed")
    elif problem == "line":
        proof["line"] = 3
    elif problem == "no_hash":
        ref.pop("sha256")
        proof.pop("sha256")
    data = {"kind": "report", "id": "RPT-SYNTH-001", "project": "synthetic",
            "title": "legacy", "created_at": "2026-01-01T00:00:00Z"}
    if kind == "original":
        data["original_report"] = ref
    elif kind == "related":
        data["related_documents"] = [ref]
    elif kind in {"submission", "status"}:
        data[kind + "_evidence"] = [proof]
    else:
        from vulnarc.history import event
        data["history"] = [event("feedback", {}, evidence=[proof])]
    dump_yaml(tmp_path / "reports/RPT-SYNTH-001/metadata.yaml", data)
    errors = validate_workspace(tmp_path)
    if problem == "missing":
        assert len(errors) == 1 and "missing material source.md" in errors[0]
    elif problem == "hash":
        assert len(errors) == 1 and "hash mismatch for source.md" in errors[0]
    elif problem == "line" and kind not in {"original", "related"}:
        assert len(errors) == 1 and "evidence line out of range source.md" in errors[0]
    else:
        assert errors == []  # Relative paths and old RPTs without a hash remain valid.


def test_report_hash_error_precedes_line_error(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("one\n")
    data = {"kind": "report", "id": "RPT-SYNTH-001", "project": "synthetic",
            "title": "legacy", "created_at": "2026-01-01T00:00:00Z",
            "status_evidence": [{"type": "receipt", "path": source.name,
                                 "sha256": "0" * 64, "line": 10}]}
    dump_yaml(tmp_path / "reports/RPT-SYNTH-001/metadata.yaml", data)
    errors = validate_workspace(tmp_path)
    assert len(errors) == 1 and "hash mismatch" in errors[0]


def test_report_note_only_evidence_is_valid(tmp_path):
    data = {"kind": "report", "id": "RPT-SYNTH-001", "project": "synthetic",
            "title": "legacy", "created_at": "2026-01-01T00:00:00Z",
            "status_evidence": [{"type": "receipt", "note": "note only"}]}
    dump_yaml(tmp_path / "reports/RPT-SYNTH-001/metadata.yaml", data)
    assert validate_workspace(tmp_path) == []


def test_va_cli_exit_code_and_material_preservation(sources, tmp_path):
    import json

    source, data = sources
    intake = tmp_path / "intake.json"
    intake.write_text(json.dumps({"schema": "vulnarc-case-intake-v1", "case": data}))
    workspace = tmp_path / "workspace"
    _, folder, _ = register_case(workspace, intake)
    notes = folder / "learning.md"
    notes.write_text("manual notes\n")
    before = {str(p): p.read_bytes() for p in workspace.rglob("*") if p.is_file()}
    source.write_text("changed later")
    result = CliRunner().invoke(app, ["va", "check", "-w", str(workspace)])
    assert result.exit_code == 1 and "source hash changed" in result.output
    assert before == {str(p): p.read_bytes() for p in workspace.rglob("*") if p.is_file()}


def test_va_rating_and_reference_sources_are_checked(sources, tmp_path):
    _, data = sources
    other = tmp_path / "other.md"
    other.write_text("proof\n")
    proof = {"type": "existing_report", "path": str(other),
             "sha256": digest(other.read_bytes()), "line": 1}
    data["reference_cases"] = [{"identifier": "CVE-2020-0001", "source": deepcopy(proof)}]
    data["ratings"] = [{"version": "3.1", "score": 5.0, "vector": "CVSS:3.1/AV:N",
                        "attribution": "reporter", "source": deepcopy(proof)}]
    verify_materials(CaseDetails.model_validate(data))
    other.unlink()
    with pytest.raises(ValueError, match="missing absolute source path"):
        verify_materials(CaseDetails.model_validate(data))


def test_storage_validation_does_not_import_cli(sources, tmp_path):
    import json
    import subprocess
    import sys

    _, data = sources
    intake = tmp_path / "intake.json"
    intake.write_text(json.dumps({"schema": "vulnarc-case-intake-v1", "case": data}))
    workspace = tmp_path / "workspace"
    register_case(workspace, intake)
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; from pathlib import Path; "
         "from vulnarc.storage import validate_workspace; "
         "assert validate_workspace(Path(sys.argv[1])) == []; "
         "assert 'vulnarc.va' not in sys.modules; "
         "assert 'vulnarc.cli' not in sys.modules; "
         "assert 'typer' not in sys.modules", str(workspace)],
        text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
