from typer.testing import CliRunner

from vulnarc.cli import app
from vulnarc.statistics import calculate
from vulnarc.storage import dump_yaml, find_record

runner = CliRunner()


def add(root, *extra):
    result = runner.invoke(
        app,
        [
            "report",
            "add",
            "-w",
            str(root),
            "--project",
            "demo",
            "--title",
            "report",
            "--id",
            "RPT-DEMO-001",
            *extra,
        ],
    )
    assert result.exit_code == 0, (result.output, result.exception)
    return find_record(root, "RPT-DEMO-001")


def test_report_flow_dates_mapping_list_show_and_stats(tmp_path):
    _, data = add(
        tmp_path,
        "--channel",
        "邮件",
        "--submission",
        "submitted",
        "--evidence-type",
        "local_ledger",
        "--evidence",
        "登记簿已发出",
        "--submitted-at-raw",
        "约 09-28/29",
        "--raw-status",
        "Pending program review",
    )
    assert data["processing_status"] == "pending_review"
    assert data["submitted_at"] is None
    assert len(data["history"]) == 1
    result = runner.invoke(
        app, ["report", "list", "-w", str(tmp_path), "--status", "pending_review"]
    )
    assert result.exit_code == 0
    assert all(t in result.output for t in ["demo", "submitted", "pending_review", "缺项"])
    result = runner.invoke(app, ["report", "show", "RPT-DEMO-001", "-w", str(tmp_path)])
    assert result.exit_code == 0
    assert "Pending program review" in result.output and "约 09-28/29" in result.output
    stats = calculate(tmp_path)
    assert stats["reports"] == 1 and stats["hypotheses"] == 0
    assert stats["report_statuses"] == {"pending_review": 1}
    assert runner.invoke(app, ["validate", "-w", str(tmp_path)]).exit_code == 0


def test_update_historical_feedback_and_correction(tmp_path):
    path, _ = add(tmp_path, "--status", "pending_review")
    note = path.with_name("report.md")
    note.write_text("manual body")
    args = ["report", "update", "RPT-DEMO-001", "-w", str(tmp_path)]
    result = runner.invoke(
        app,
        args
        + [
            "--raw-status",
            "Duplicate",
            "--date-raw",
            "2026-09-01",
            "--historical",
            "--note",
            "旧反馈",
        ],
    )
    assert result.exit_code == 0, result.output
    _, data = find_record(tmp_path, "RPT-DEMO-001")
    assert data["processing_status"] == "pending_review"
    assert data["history"][-1]["changes"]["processing_status"]["after"] == "duplicate"
    event = data["history"][-1]["id"]
    previous = data["history"].copy()
    result = runner.invoke(
        app,
        args
        + [
            "--status",
            "informative",
            "--corrects",
            event,
            "--reason",
            "台账文字更正",
            "--apply-current",
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.output
    _, data = find_record(tmp_path, "RPT-DEMO-001")
    assert data["processing_status"] == "informative"
    assert data["history"][:-1] == previous
    assert data["history"][-1]["corrects_event_id"] == event
    assert note.read_text() == "manual body"
    assert runner.invoke(app, args + ["--status", "accepted", "--corrects", event]).exit_code != 0


def test_legacy_snapshot_no_past_events_fabricated(tmp_path):
    path, data = add(tmp_path)
    data.pop("history")
    dump_yaml(path, data)
    result = runner.invoke(
        app,
        [
            "report",
            "update",
            "RPT-DEMO-001",
            "-w",
            str(tmp_path),
            "--status",
            "duplicate",
            "--note",
            "反馈",
        ],
    )
    assert result.exit_code == 0, result.output
    _, data = find_record(tmp_path, "RPT-DEMO-001")
    assert [e["event_type"] for e in data["history"]] == ["legacy_snapshot", "feedback"]
    assert data["history"][0]["actual_at"] is None


def test_current_state_and_event_fail_together(tmp_path, monkeypatch):
    import vulnarc.storage as storage

    path, _ = add(tmp_path)
    before = path.read_bytes()

    def fail(*_):
        raise OSError("injected replace failure")

    monkeypatch.setattr(storage.os, "replace", fail)
    result = runner.invoke(
        app, ["report", "update", "RPT-DEMO-001", "-w", str(tmp_path), "--status", "duplicate"]
    )
    assert result.exit_code != 0
    assert path.read_bytes() == before


def test_workspace_required_and_chinese_prompts(tmp_path):
    assert runner.invoke(app, ["report", "add", "--project", "demo", "--title", "x"]).exit_code != 0
    result = runner.invoke(app, ["report", "add", "-w", str(tmp_path)], input="示例\n标题\n")
    assert result.exit_code == 0, result.output
    assert "项目" in result.output and "标题" in result.output


def test_research_reported_still_counts_as_verified(tmp_path):
    from test_write_protection import args

    assert runner.invoke(app, args(tmp_path)).exit_code == 0
    for state in ["candidate", "validated", "reported"]:
        assert (
            runner.invoke(app, ["status", "SYNTH-HYP-001", state, "-w", str(tmp_path)]).exit_code
            == 0
        )
    data = calculate(tmp_path)
    assert data["validated"] == 0 and data["validated_and_later"] == 1
    assert data["rates"]["human"]["validation_rate"] == 1
    _, record = find_record(tmp_path, "SYNTH-HYP-001")
    assert len(record["history"]) == 4  # legacy snapshot + three real updates


def test_old_date_defaults_to_history_and_snapshot_is_old(tmp_path):
    _, initial = add(tmp_path, "--status", "pending_review", "--status-at-raw", "2026-09-30")
    result = runner.invoke(
        app,
        [
            "report",
            "update",
            "RPT-DEMO-001",
            "-w",
            str(tmp_path),
            "--status",
            "duplicate",
            "--date-raw",
            "2026-09-01",
        ],
    )
    assert result.exit_code == 0, result.output
    _, data = find_record(tmp_path, "RPT-DEMO-001")
    assert data["processing_status"] == "pending_review"
    assert data["history"][:-1] == initial["history"]
    path, _ = find_record(tmp_path, "RPT-DEMO-001")
    data.pop("history")
    dump_yaml(path, data)
    result = runner.invoke(
        app, ["report", "update", "RPT-DEMO-001", "-w", str(tmp_path), "--status", "accepted"]
    )
    assert result.exit_code == 0
    _, data = find_record(tmp_path, "RPT-DEMO-001")
    assert data["history"][0]["changes"]["processing_status"]["after"] == "pending_review"
    assert data["history"][-1]["changes"]["processing_status"]["before"] == "pending_review"
    assert data["processing_status"] == "accepted"


def test_append_only_and_research_status_rejects_reports(tmp_path):
    import pytest

    from vulnarc.storage import read_for_update, update_record

    add(tmp_path)
    path, data, fingerprint = read_for_update(tmp_path, "RPT-DEMO-001")
    data["history"] = []
    with pytest.raises(ValueError, match="append-only"):
        update_record(tmp_path, path, data, fingerprint)
    result = runner.invoke(app, ["status", "RPT-DEMO-001", "candidate", "-w", str(tmp_path)])
    assert result.exit_code != 0
    assert "report update" in result.output


def test_invalid_historical_fields_never_written(tmp_path):
    import pytest

    from vulnarc.reports import update_report

    path, _ = add(tmp_path)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        update_report(tmp_path, "RPT-DEMO-001", {"submitted_at": "nonsense"}, historical=True)
    assert path.read_bytes() == before


def test_similar_title_does_not_merge(tmp_path):
    add(tmp_path)
    result = runner.invoke(
        app,
        [
            "report",
            "add",
            "-w",
            str(tmp_path),
            "--project",
            "demo",
            "--title",
            "report",
            "--id",
            "RPT-DEMO-002",
        ],
    )
    assert result.exit_code == 0
    assert "不会自动合并" in result.output
    assert calculate(tmp_path)["reports"] == 2
