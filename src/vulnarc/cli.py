"""Small, terminal-friendly VulnArc CLI."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from .lifecycle import require_transition
from .models import Experiment, Origin, Status
from .statistics import calculate, experiment_table
from .storage import (
    dump_yaml,
    find_record,
    load_yaml,
    metadata_files,
    parse_record,
    validate_workspace,
)

app = typer.Typer(help="Structured Human–AI vulnerability research records.", no_args_is_help=True)
new_app = typer.Typer(help="Create a research record.")
app.add_typer(new_app, name="new")
Workspace = Annotated[
    Path, typer.Option("--workspace", "-w", help="External/public workspace path")
]


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def next_id(workspace: Path, prefix: str, target: str) -> str:
    stem = f"{prefix}-{target.upper().replace('_', '-')}-"
    used = []
    for path in metadata_files(workspace):
        value = load_yaml(path).get("id", "")
        if value.startswith(stem) and value[len(stem) :].isdigit():
            used.append(int(value[len(stem) :]))
    return f"{stem}{max(used, default=0) + 1:03d}"


@new_app.command("hypothesis")
def new_hypothesis(
    target: Annotated[str | None, typer.Option()] = None,
    title: Annotated[str | None, typer.Option()] = None,
    origin: Annotated[Origin | None, typer.Option(case_sensitive=False)] = None,
    security_boundary: Annotated[str | None, typer.Option("--security-boundary")] = None,
    workspace: Workspace = Path("."),
    record_id: Annotated[str | None, typer.Option("--id")] = None,
) -> None:
    target = target or typer.prompt("Target")
    title = title or typer.prompt("Title")
    origin = origin or Origin(typer.prompt("Origin", default="human").lower())
    security_boundary = security_boundary or typer.prompt("Security boundary")
    record_id = record_id or next_id(workspace, "HYP", target)
    directory = workspace / "hypotheses" / record_id
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
    dump_yaml(directory / "metadata.yaml", data)
    body = Path(__file__).parents[2] / "templates" / "hypothesis.md"
    text = (
        body.read_text(encoding="utf-8")
        if body.exists()
        else "# Hypothesis\n\n## Why This Might Be Wrong\n"
    )
    (directory / "hypothesis.md").write_text(text, encoding="utf-8")
    typer.echo(f"Created {record_id} at {directory}")


@new_app.command("experiment")
def new_experiment(
    title: Annotated[str | None, typer.Option()] = None,
    target: Annotated[str | None, typer.Option()] = None,
    scope: Annotated[str | None, typer.Option()] = None,
    time_budget: Annotated[float, typer.Option()] = 1.0,
    workspace: Workspace = Path("."),
    record_id: Annotated[str | None, typer.Option("--id")] = None,
) -> None:
    title = title or typer.prompt("Research question")
    target = target or typer.prompt("Target")
    scope = scope or typer.prompt("Audit scope")
    record_id = record_id or next_id(workspace, "EXP", target)
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
    directory = workspace / "experiments" / "human-vs-ai" / record_id
    dump_yaml(directory / "metadata.yaml", data)
    template = Path(__file__).parents[2] / "templates" / "experiment.md"
    (directory / "experiment.md").write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    typer.echo(f"Created {record_id} at {directory}")


@new_app.command("case")
def new_case(
    title: Annotated[str, typer.Option(prompt=True)],
    target: Annotated[str, typer.Option(prompt=True)],
    disclosure_date: Annotated[str, typer.Option(prompt=True)],
    workspace: Workspace = Path("."),
    record_id: Annotated[str | None, typer.Option("--id")] = None,
) -> None:
    record_id = record_id or next_id(workspace, "CASE", target)
    directory = workspace / "cases" / "public" / record_id
    data = {
        "kind": "public_case",
        "id": record_id,
        "title": title,
        "target": target,
        "status": "public",
        "created_at": now(),
        "disclosure_date": disclosure_date,
    }
    dump_yaml(directory / "metadata.yaml", data)
    template = Path(__file__).parents[2] / "templates" / "public-case" / "README.md"
    (directory / "README.md").write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    typer.echo(f"Created {record_id} at {directory}")


@app.command("validate")
def validate(workspace: Workspace = Path(".")) -> None:
    errors = validate_workspace(workspace)
    if errors:
        for error in errors:
            typer.echo(f"ERROR {error}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Valid: {len(metadata_files(workspace))} record(s)")


@app.command("list")
def list_records(workspace: Workspace = Path(".")) -> None:
    for path in metadata_files(workspace):
        record = parse_record(path)
        typer.echo(f"{record.id:<24} {record.kind:<12} {getattr(record, 'status', '—')}")


@app.command("status")
def status(record_id: str, new_status: Status, workspace: Workspace = Path(".")) -> None:
    path, data = find_record(workspace, record_id)
    current = Status(data["status"])
    require_transition(current, new_status)
    if data.get("kind") == "hypothesis":
        data["kind"] = "finding"
        data["hypothesis"] = data["id"]
        data.pop("confidence", None)
    data["status"] = new_status.value
    dump_yaml(path, data)
    typer.echo(f"{record_id}: {current.value} -> {new_status.value}")


@app.command("stats")
def stats(workspace: Workspace = Path(".")) -> None:
    data = calculate(workspace)
    labels = {
        "targets": "Targets",
        "hypotheses": "Hypotheses",
        "candidates": "Candidates",
        "validated": "Validated vulnerabilities",
        "rejected": "Rejected hypotheses",
        "public_cases": "Public cases",
        "cve_ghsa": "CVE / GHSA count",
    }
    for key, label in labels.items():
        typer.echo(f"{label}: {data[key]}")
    typer.echo(
        "Origins: " + (", ".join(f"{k}={v}" for k, v in data["origins"].items()) or "no data")
    )
    for origin, rates in data.get("rates", {}).items():
        validation = rates["validation_rate"]
        rejection = rates["rejection_rate"]
        typer.echo(f"{origin} validation rate: {validation:.1%}; rejection rate: {rejection:.1%}")


@app.command("compare")
def compare(record_id: str, workspace: Workspace = Path(".")) -> None:
    path, _ = find_record(workspace, record_id)
    record = parse_record(path)
    if not isinstance(record, Experiment):
        raise typer.BadParameter(f"{record_id} is not an experiment")
    typer.echo(experiment_table(record))


if __name__ == "__main__":
    app()
