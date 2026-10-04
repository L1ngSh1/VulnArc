"""Small, terminal-friendly VulnArc CLI."""

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from . import inventory_import  # noqa: F401 - registers the one-off import command
from .history import append_change
from .lifecycle import require_transition
from .models import Experiment, Origin, Status
from .reports import report_app
from .statistics import calculate, experiment_table
from .storage import (
    create_record,
    find_record,
    metadata_files,
    parse_record,
    read_for_update,
    restore_backup,
    update_record,
    validate_workspace,
)
from .template_loader import template_text
from .va import va_app

app = typer.Typer(help="Structured Human–AI vulnerability research records.", no_args_is_help=True)
new_app = typer.Typer(help="Create a research record.")
app.add_typer(new_app, name="new")
app.add_typer(report_app, name="report")
app.add_typer(va_app, name="va")
Workspace = Annotated[
    Path, typer.Option("--workspace", "-w", help="External/public workspace path")
]


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def write_create(workspace, folder, data, bodies, prefix, target):
    try:
        return create_record(workspace, folder, data, bodies, prefix=prefix, target=target)
    except (ValueError, OSError) as exc:
        typer.echo(f"ERROR {exc}", err=True)
        raise typer.Exit(1) from exc


@app.command("restore")
def restore(backup_id: str, workspace: Workspace) -> None:
    """Restore one metadata write, only if its current hash still matches."""
    try:
        path = restore_backup(workspace, backup_id)
    except (ValueError, OSError) as exc:
        typer.echo(f"ERROR {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Restored: {path}")


@new_app.command("hypothesis")
def new_hypothesis(
    target: Annotated[str | None, typer.Option()] = None,
    title: Annotated[str | None, typer.Option()] = None,
    origin: Annotated[Origin | None, typer.Option(case_sensitive=False)] = None,
    security_boundary: Annotated[str | None, typer.Option("--security-boundary")] = None,
    workspace: Workspace = ...,
    record_id: Annotated[str | None, typer.Option("--id")] = None,
) -> None:
    target = target or typer.prompt("Target")
    title = title or typer.prompt("Title")
    origin = origin or Origin(typer.prompt("Origin", default="human").lower())
    security_boundary = security_boundary or typer.prompt("Security boundary")
    data = {
        "kind": "hypothesis",
        "id": record_id,
        "target": target,
        "title": title,
        "origin": origin.value,
        "status": "hypothesis",
        "created_at": now(),
        "security_boundary": security_boundary,
        "confidence": None,
    }
    text = template_text("hypothesis.md")
    directory = write_create(workspace, "hypotheses", data, {"hypothesis.md": text}, "HYP", target)
    record_id = directory.name
    typer.echo(f"Created {record_id} at {directory}")


@new_app.command("experiment")
def new_experiment(
    title: Annotated[str | None, typer.Option()] = None,
    target: Annotated[str | None, typer.Option()] = None,
    scope: Annotated[str | None, typer.Option()] = None,
    time_budget: Annotated[float, typer.Option()] = 1.0,
    workspace: Workspace = ...,
    record_id: Annotated[str | None, typer.Option("--id")] = None,
) -> None:
    title = title or typer.prompt("Research question")
    target = target or typer.prompt("Target")
    scope = scope or typer.prompt("Audit scope")
    data = {
        "kind": "experiment",
        "id": record_id,
        "title": title,
        "target": target,
        "audit_scope": scope,
        "time_budget_hours": time_budget,
        "created_at": now(),
        "arms": [{"name": "Human", "origin": "human"}, {"name": "AI", "origin": "ai"}],
        "overlap": 0,
        "limitations": [],
    }
    directory = write_create(
        workspace,
        "experiments/human-vs-ai",
        data,
        {"experiment.md": template_text("experiment.md")},
        "EXP",
        target,
    )
    record_id = directory.name
    typer.echo(f"Created {record_id} at {directory}")


@new_app.command("case")
def new_case(
    title: Annotated[str, typer.Option(prompt=True)],
    target: Annotated[str, typer.Option(prompt=True)],
    disclosure_date: Annotated[str, typer.Option(prompt=True)],
    workspace: Workspace = ...,
    record_id: Annotated[str | None, typer.Option("--id")] = None,
) -> None:
    data = {
        "kind": "public_case",
        "id": record_id,
        "title": title,
        "target": target,
        "status": "public",
        "created_at": now(),
        "disclosure_date": disclosure_date,
    }
    directory = write_create(
        workspace,
        "cases/public",
        data,
        {"README.md": template_text("public-case/README.md")},
        "CASE",
        target,
    )
    record_id = directory.name
    typer.echo(f"Created {record_id} at {directory}")


@app.command("validate")
def validate(workspace: Workspace) -> None:
    errors = validate_workspace(workspace)
    if errors:
        for error in errors:
            typer.echo(f"ERROR {error}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Valid: {len(metadata_files(workspace))} record(s)")


@app.command("list")
def list_records(workspace: Workspace) -> None:
    for path in metadata_files(workspace):
        record = parse_record(path)
        typer.echo(f"{record.id:<24} {record.kind:<12} {getattr(record, 'status', '—')}")


@app.command("status")
def status(record_id: str, new_status: Status, workspace: Workspace) -> None:
    try:
        path, data, fingerprint = read_for_update(workspace, record_id)
        snapshot = deepcopy(data)
        if data.get("kind") not in {"hypothesis", "finding"}:
            raise ValueError("status accepts research records only; use report update for reports")
        current = Status(data["status"])
        require_transition(current, new_status)
        if data.get("kind") == "hypothesis":
            data["kind"] = "finding"
            data["hypothesis"] = data["id"]
            data.pop("confidence", None)
        data["status"] = new_status.value
        changes = {
            k: {"before": snapshot.get(k), "after": data.get(k)}
            for k in sorted(snapshot.keys() | data.keys())
            if snapshot.get(k) != data.get(k) and k != "history"
        }
        append_change(data, changes, "status_change", snapshot=snapshot)
        backup = update_record(workspace, path, data, fingerprint)
    except (ValueError, OSError) as exc:
        typer.echo(f"ERROR {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Backup: {backup.name}")
    typer.echo(f"{record_id}: {current.value} -> {new_status.value}")


@app.command("stats")
def stats(workspace: Workspace) -> None:
    data = calculate(workspace)
    labels = {
        "targets": "Targets",
        "hypotheses": "Hypotheses",
        "candidates": "Candidates",
        "validated": "Validated (current)",
        "validated_and_later": "Validated and later stages",
        "reports": "Reports (separate from research)",
        "rejected": "Rejected hypotheses",
        "public_cases": "Public cases",
        "cve_ghsa": "CVE / GHSA count",
    }
    for key, label in labels.items():
        typer.echo(f"{label}: {data[key]}")
    typer.echo(
        "Origins: " + (", ".join(f"{k}={v}" for k, v in data["origins"].items()) or "no data")
    )
    typer.echo("Report outcomes: " + str(data["report_statuses"]))
    for origin, rates in data.get("rates", {}).items():
        validation = rates["validation_rate"]
        rejection = rates["rejection_rate"]
        typer.echo(f"{origin} validation rate: {validation:.1%}; rejection rate: {rejection:.1%}")


@app.command("compare")
def compare(record_id: str, workspace: Workspace) -> None:
    path, _ = find_record(workspace, record_id)
    record = parse_record(path)
    if not isinstance(record, Experiment):
        raise typer.BadParameter(f"{record_id} is not an experiment")
    typer.echo(experiment_table(record))


if __name__ == "__main__":
    app()
