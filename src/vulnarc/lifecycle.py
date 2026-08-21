"""Explicit finding lifecycle rules."""

from .models import Status

TRANSITIONS: dict[Status, set[Status]] = {
    Status.HYPOTHESIS: {Status.CANDIDATE},
    Status.CANDIDATE: {Status.VALIDATED, Status.REJECTED},
    Status.VALIDATED: {Status.REPORTED},
    Status.REPORTED: {Status.EMBARGOED, Status.DISCLOSED},
    Status.EMBARGOED: {Status.DISCLOSED},
    Status.DISCLOSED: {Status.PUBLIC},
    Status.PUBLIC: set(),
    Status.REJECTED: set(),
}


def require_transition(current: Status, target: Status) -> None:
    if target not in TRANSITIONS[current]:
        raise ValueError(f"invalid lifecycle transition: {current.value} -> {target.value}")
