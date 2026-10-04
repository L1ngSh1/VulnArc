from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from vulnarc.models import Report
from vulnarc.storage import create_record, dump_yaml, validate_workspace

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def sample(**extra):
    return {
        "id": "RPT-DEMO-001",
        "project": "demo",
        "title": "old report",
        "created_at": NOW.isoformat(),
        "kind": "report",
        **extra,
    }


def test_minimal_report_and_unknowns():
    record = Report.model_validate(sample(submitted_at_raw="约 09-28/29"))
    assert record.submission_status == "unknown"
    assert record.processing_status == "unknown"
    assert record.submitted_at is None
    assert record.submitted_at_raw == "约 09-28/29"
    assert record.history == []
    assert not hasattr(record, "hypothesis")


def test_submitted_needs_typed_evidence_not_number():
    with pytest.raises(ValidationError, match="submission evidence"):
        Report.model_validate(
            sample(submission_status="submitted", channel="HackerOne", external_id="123")
        )
    record = Report.model_validate(
        sample(
            submission_status="submitted",
            channel="补天",
            submission_evidence=[{"type": "local_ledger", "note": "登记簿"}],
        )
    )
    assert record.external_id is None


@pytest.mark.parametrize(
    "field,value",
    [("project", ""), ("title", " "), ("processing_status", "fixed"), ("schema_version", 2)],
)
def test_invalid_report(field, value):
    with pytest.raises(ValidationError):
        Report.model_validate(sample(**{field: value}))


def test_external_id_duplicate_and_tool_dir_exclusion(tmp_path):
    create_record(
        tmp_path, "reports", sample(channel="HackerOne", external_id="123"), {"report.md": "a"}
    )
    with pytest.raises(ValueError, match="external identifier"):
        create_record(
            tmp_path,
            "reports",
            sample(id="RPT-DEMO-002", channel=" hackerone ", external_id="123"),
            {"report.md": "b"},
        )
    dump_yaml(
        tmp_path / ".vulnarc/backup/metadata.yaml", sample(channel="HackerOne", external_id="123")
    )
    assert validate_workspace(tmp_path) == []


def test_reference_paths_hashes_and_external_duplicates(tmp_path):
    path = tmp_path / "original.txt"
    path.write_text("original")
    record = sample(
        original_report={"path": str(path), "sha256": "0" * 64}, research_refs=["HYP-MISSING-001"]
    )
    dump_yaml(tmp_path / "reports/one/metadata.yaml", record)
    errors = validate_workspace(tmp_path)
    assert any("hash mismatch" in e for e in errors)
    assert any("unresolved reference" in e for e in errors)
    path.unlink()
    assert any("missing material" in e for e in validate_workspace(tmp_path))


def test_schema_export_matches_model():
    import json
    from pathlib import Path

    exported = json.loads((Path(__file__).parents[1] / "schemas/report.schema.json").read_text())
    assert exported == Report.model_json_schema()


def test_workspace_validator_detects_external_collision(tmp_path):
    dump_yaml(tmp_path / "reports/a/metadata.yaml", sample(channel="HackerOne", external_id="123"))
    dump_yaml(
        tmp_path / "reports/b/metadata.yaml",
        sample(id="RPT-DEMO-002", channel="hackerone", external_id="123"),
    )
    assert any("duplicate external identifier" in e for e in validate_workspace(tmp_path))


def test_all_exported_schemas_match():
    import json
    from pathlib import Path

    from vulnarc.storage import MODELS

    for model in MODELS.values():
        path = Path(__file__).parents[1] / "schemas" / (model.__name__.lower() + ".schema.json")
        assert json.loads(path.read_text()) == model.model_json_schema()
