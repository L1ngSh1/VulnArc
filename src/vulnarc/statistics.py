"""Research metrics computed only from recorded observations."""

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .models import Experiment, Finding, Hypothesis, PublicCase, Status
from .storage import metadata_files, parse_record


def calculate(workspace: Path) -> dict[str, Any]:
    records = [parse_record(path) for path in metadata_files(workspace)]
    counts = Counter(type(r).__name__ for r in records)
    statuses = Counter(r.status.value for r in records if isinstance(r, (Hypothesis, Finding)))
    origins = Counter(r.origin.value for r in records if isinstance(r, (Hypothesis, Finding)))
    decisions: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        if isinstance(record, Finding):
            decisions[record.origin.value][record.status.value] += 1
    identifiers = sum(
        int(bool(r.cve)) + int(bool(r.ghsa)) for r in records if isinstance(r, PublicCase)
    )
    result: dict[str, Any] = {
        "targets": counts["Target"],
        "hypotheses": counts["Hypothesis"] + counts["Finding"],
        "candidates": statuses[Status.CANDIDATE.value],
        "validated": statuses[Status.VALIDATED.value],
        "rejected": statuses[Status.REJECTED.value],
        "public_cases": counts["PublicCase"],
        "cve_ghsa": identifiers,
        "origins": dict(origins),
    }
    rates = {}
    for origin, values in decisions.items():
        decided = values["validated"] + values["rejected"]
        if decided:
            rates[origin] = {
                "validation_rate": values["validated"] / decided,
                "rejection_rate": values["rejected"] / decided,
            }
    if rates:
        result["rates"] = rates
    return result


def experiment_table(experiment: Experiment) -> str:
    headers = [arm.name for arm in experiment.arms]
    width = max(16, *(len(h) + 2 for h in headers))
    lines = [experiment.title, "─" * max(32, width * (len(headers) + 1)), ""]
    lines.append(f"{'Metric':<16}" + "".join(f"{h:>{width}}" for h in headers))
    for label, field in (
        ("Hypotheses", "hypotheses"),
        ("Validated", "validated"),
        ("Rejected", "rejected"),
        ("Unique", "unique"),
    ):
        lines.append(
            f"{label:<16}" + "".join(f"{getattr(a, field):>{width}}" for a in experiment.arms)
        )
    lines.append(f"{'Overlap':<16}{experiment.overlap:>{width}}")
    lines.append(
        f"{'Time':<16}"
        + "".join(
            f"{('—' if a.time_hours is None else f'{a.time_hours:g}h'):>{width}}"
            for a in experiment.arms
        )
    )
    lines.append(
        f"{'API cost':<16}"
        + "".join(
            f"{('—' if a.api_cost is None else f'${a.api_cost:.2f}'):>{width}}"
            for a in experiment.arms
        )
    )
    return "\n".join(lines)
