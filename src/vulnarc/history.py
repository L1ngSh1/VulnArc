"""Append-only local audit events; recorded time never substitutes for event time."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def now() -> str:
    return datetime.now(UTC).isoformat()


def event(
    event_type: str,
    changes: dict[str, Any],
    *,
    actual_at=None,
    date_raw=None,
    note=None,
    evidence=None,
    corrects=None,
) -> dict[str, Any]:
    return {
        "id": uuid4().hex,
        "recorded_at": now(),
        "event_type": event_type,
        "actual_at": actual_at,
        "date_raw": date_raw,
        "changes": deepcopy(changes),
        "note": note,
        "evidence": deepcopy(evidence or []),
        "corrects_event_id": corrects,
    }


def append_change(
    data: dict[str, Any], changes: dict[str, Any], event_type="update", snapshot=None, **kwargs
):
    history = data.setdefault("history", [])
    if not history:
        snapshot = {
            k: {"before": None, "after": deepcopy(v)}
            for k, v in (snapshot if snapshot is not None else data).items()
            if k != "history"
        }
        history.append(event("legacy_snapshot", snapshot, note="旧记录当前快照；不推断过去时间"))
    history.append(event(event_type, changes, **kwargs))
    data["updated_at"] = now()
