import json
from pathlib import Path

from typer.testing import CliRunner

from vulnarc.cli import app
from vulnarc.inventory_import import apply_preview, preview_inventory
from vulnarc.storage import metadata_files, validate_workspace


def inventory(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    data = []
    for i, (status, channel, number) in enumerate(
        [
            ("closed_duplicate", "HackerOne", "123"),
            ("pending_program_review", "HackerOne", "124"),
            ("submitted_pending_platform_review", "补天", None),
        ]
    ):
        doc = root / f"{i}.txt"
        doc.write_text("local ledger\n")
        data.append(
            {
                "id": f"demo:{i}",
                "project": "demo",
                "title": f"report {i}",
                "filing_group": "local_submission_record",
                "proposed_status": status,
                "external_report": {"platform": channel, "id": number} if number else None,
                "channel_recorded_or_proposed": channel,
                "submitted_at_raw": "约 09-28/29",
                "canonical_document": doc.name,
                "related_documents": [],
                "status_evidence": [{"path": doc.name, "note": "ledger", "line": 1}],
                "missing_information": ["回执"],
                "notes": [],
                "events_from_local_documents": [
                    {"date_raw": "2026-09-01", "event": status, "note": "本地反馈"}
                ],
            }
        )
    path = tmp_path / "inventory.json"
    path.write_text(
        json.dumps(
            {
                "schema": "local-vulnarc-planning-v1 (NOT an official VulnArc import schema)",
                "source_root": str(root),
                "records": data,
            }
        )
    )
    return path


def test_dry_run_zero_writes_then_apply_idempotent(tmp_path):
    inv = inventory(tmp_path)
    workspace = tmp_path / "workspace"
    previews = preview_inventory(inv, workspace)
    assert not workspace.exists()
    assert [p["record"]["processing_status"] for p in previews] == [
        "duplicate",
        "pending_review",
        "pending_review",
    ]
    assert all(p["record"]["submitted_at"] is None for p in previews)
    assert previews[2]["record"]["external_id"] is None
    apply_preview(workspace, previews)
    assert len(metadata_files(workspace)) == 3
    assert validate_workspace(workspace) == []
    before = {p: p.read_bytes() for p in workspace.rglob("*") if p.is_file()}
    repeated = preview_inventory(inv, workspace)
    assert all(p["action"] == "skip" for p in repeated)
    apply_preview(workspace, repeated)
    assert before == {p: p.read_bytes() for p in workspace.rglob("*") if p.is_file()}


def test_cli_default_preview_does_not_create_workspace(tmp_path):
    inv = inventory(tmp_path)
    workspace = tmp_path / "workspace"
    result = CliRunner().invoke(app, ["report", "import-inventory", str(inv), "-w", str(workspace)])
    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output
    assert not workspace.exists()


def test_changed_source_key_reports_conflict(tmp_path):
    inv = inventory(tmp_path)
    workspace = tmp_path / "workspace"
    apply_preview(workspace, preview_inventory(inv, workspace))
    source = json.loads(inv.read_text())
    source["records"][0]["title"] = "changed title"
    inv.write_text(json.dumps(source))
    previews = preview_inventory(inv, workspace)
    assert previews[0]["action"] == "conflict"


def test_apply_preflight_no_partial_on_conflict(tmp_path):
    import pytest

    inv = inventory(tmp_path)
    workspace = tmp_path / "workspace"
    previews = preview_inventory(inv, workspace)
    previews[2]["action"] = "conflict"
    with pytest.raises(ValueError, match="conflict"):
        apply_preview(workspace, previews)
    assert not workspace.exists()


def test_source_escape_is_rejected(tmp_path):
    import pytest

    inv = inventory(tmp_path)
    source = json.loads(inv.read_text())
    source["records"][0]["canonical_document"] = "../inventory.json"
    inv.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="source path"):
        preview_inventory(inv, tmp_path / "workspace")


def test_source_changes_after_preview_block_apply(tmp_path):
    import pytest

    inv = inventory(tmp_path)
    workspace = tmp_path / "workspace"
    previews = preview_inventory(inv, workspace)
    source = json.loads(inv.read_text())
    (Path(source["source_root"]) / "2.txt").write_text("changed")
    with pytest.raises(ValueError, match="source changed"):
        apply_preview(workspace, previews)
    assert not workspace.exists()
