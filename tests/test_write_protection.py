import multiprocessing

import pytest
from typer.testing import CliRunner

from vulnarc import storage
from vulnarc.cli import app


def args(root, record_id="SYNTH-HYP-001"):
    return [
        "new",
        "hypothesis",
        "-w",
        str(root),
        "--target",
        "synthetic",
        "--title",
        "first",
        "--origin",
        "human",
        "--security-boundary",
        "a -> b",
        "--id",
        record_id,
    ]


def create_worker(root, queue):
    queue.put(CliRunner().invoke(app, args(root)).exit_code)


def test_duplicate_preserves_metadata_and_manual_body(tmp_path):
    runner = CliRunner()
    assert runner.invoke(app, args(tmp_path)).exit_code == 0
    note = tmp_path / "hypotheses/SYNTH-HYP-001/hypothesis.md"
    note.write_text("manual note\n")
    assert (
        runner.invoke(app, ["status", "SYNTH-HYP-001", "candidate", "-w", str(tmp_path)]).exit_code
        == 0
    )
    meta = note.with_name("metadata.yaml")
    before = meta.read_bytes(), note.read_bytes()
    result = runner.invoke(app, args(tmp_path))
    assert result.exit_code != 0
    assert "duplicate id" in result.output
    assert (meta.read_bytes(), note.read_bytes()) == before


def test_invalid_input_leaves_no_record(tmp_path):
    result = CliRunner().invoke(app, args(tmp_path, "../../bad"))
    assert result.exit_code != 0
    assert storage.metadata_files(tmp_path) == []


def test_cross_kind_id_is_rejected(tmp_path):
    runner = CliRunner()
    assert runner.invoke(app, args(tmp_path)).exit_code == 0
    result = runner.invoke(
        app,
        [
            "new",
            "experiment",
            "-w",
            str(tmp_path),
            "--title",
            "x",
            "--target",
            "x",
            "--scope",
            "x",
            "--id",
            "SYNTH-HYP-001",
        ],
    )
    assert result.exit_code != 0
    assert not (tmp_path / "experiments/human-vs-ai/SYNTH-HYP-001").exists()


def test_two_processes_one_success(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    workers = [ctx.Process(target=create_worker, args=(tmp_path, queue)) for _ in range(2)]
    for w in workers:
        w.start()
    for w in workers:
        w.join(20)
        assert w.exitcode == 0
    assert sorted(queue.get(timeout=5) for _ in workers) == [0, 1]
    assert len(storage.metadata_files(tmp_path)) == 1


def test_atomic_failure_keeps_original_and_cleans_temp(tmp_path, monkeypatch):
    runner = CliRunner()
    assert runner.invoke(app, args(tmp_path)).exit_code == 0
    path, data, fingerprint = storage.read_for_update(tmp_path, "SYNTH-HYP-001")
    before = path.read_bytes()
    data["title"] = "changed"

    def fail(*_):
        raise OSError("injected before replace")

    monkeypatch.setattr(storage.os, "replace", fail)
    with pytest.raises(OSError, match="injected"):
        storage.update_record(tmp_path, path, data, fingerprint)
    assert path.read_bytes() == before
    assert storage.validate_workspace(tmp_path) == []
    assert not list(path.parent.glob(".metadata-*"))
    assert len(storage.metadata_files(tmp_path)) == 1


def test_external_edit_conflict_and_restore(tmp_path):
    runner = CliRunner()
    assert runner.invoke(app, args(tmp_path)).exit_code == 0
    path, data, fingerprint = storage.read_for_update(tmp_path, "SYNTH-HYP-001")
    original = path.read_bytes()
    path.write_bytes(original + b"\n# manual edit\n")
    with pytest.raises(ValueError, match="external edit"):
        storage.update_record(tmp_path, path, data, fingerprint)
    path.write_bytes(original)
    data["title"] = "changed"
    backup = storage.update_record(tmp_path, path, data, fingerprint)
    changed = path.read_bytes()
    storage.restore_backup(tmp_path, backup.name)
    assert path.read_bytes() == original
    with pytest.raises(ValueError, match="current version"):
        storage.restore_backup(tmp_path, backup.name)
    assert changed != original
    assert len(storage.metadata_files(tmp_path)) == 1


def test_staging_failure_never_publishes_record(tmp_path, monkeypatch):
    def fail(*_):
        raise OSError("injected directory commit failure")

    monkeypatch.setattr(storage.os, "rename", fail)
    result = CliRunner().invoke(app, args(tmp_path))
    assert result.exit_code != 0
    assert storage.metadata_files(tmp_path) == []
    assert not list((tmp_path / ".vulnarc/staging").iterdir())


def test_restore_detects_later_edits_and_tampered_backup(tmp_path):
    runner = CliRunner()
    assert runner.invoke(app, args(tmp_path)).exit_code == 0
    path, data, fingerprint = storage.read_for_update(tmp_path, "SYNTH-HYP-001")
    data["title"] = "changed"
    backup = storage.update_record(tmp_path, path, data, fingerprint)
    changed = path.read_bytes()
    path.write_bytes(changed + b"\n# later edit\n")
    with pytest.raises(ValueError, match="current version"):
        storage.restore_backup(tmp_path, backup.name)
    path.write_bytes(changed)
    (backup / "before.bin").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="backup hash"):
        storage.restore_backup(tmp_path, backup.name)
    assert path.read_bytes() == changed


def test_symlink_record_path_is_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "hypotheses").symlink_to(outside, target_is_directory=True)
    result = CliRunner().invoke(app, args(workspace))
    assert result.exit_code != 0
    assert "symlink" in result.output
    assert list(outside.iterdir()) == []


def test_research_legacy_snapshot_and_kind_delta(tmp_path):
    runner = CliRunner()
    assert runner.invoke(app, args(tmp_path)).exit_code == 0
    result = runner.invoke(app, ["status", "SYNTH-HYP-001", "candidate", "-w", str(tmp_path)])
    assert result.exit_code == 0
    _, data = storage.find_record(tmp_path, "SYNTH-HYP-001")
    assert data["history"][0]["changes"]["status"]["after"] == "hypothesis"
    assert data["history"][0]["changes"]["kind"]["after"] == "hypothesis"
    assert data["history"][1]["changes"]["kind"] == {"before": "hypothesis", "after": "finding"}


def test_workspace_alias_root_updates_correctly(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    runner = CliRunner()
    assert runner.invoke(app, args(alias)).exit_code == 0
    result = runner.invoke(app, ["status", "SYNTH-HYP-001", "candidate", "-w", str(alias)])
    assert result.exit_code == 0, result.output
    assert storage.validate_workspace(alias) == []
