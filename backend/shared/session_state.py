import enum
from typing import Dict, Set


class SessionStatus(str, enum.Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


_VALID_TRANSITIONS: Dict[SessionStatus, Set[SessionStatus]] = {
    SessionStatus.CREATED: {SessionStatus.ACTIVE},
    SessionStatus.ACTIVE: {SessionStatus.PAUSED, SessionStatus.COMPLETED},
    SessionStatus.PAUSED: {SessionStatus.ACTIVE, SessionStatus.COMPLETED},
    SessionStatus.COMPLETED: set(),
}


def can_transition(from_status: SessionStatus, to_status: SessionStatus) -> bool:
    return to_status in _VALID_TRANSITIONS.get(from_status, set())


def transition(from_status: SessionStatus, to_status: SessionStatus) -> SessionStatus:
    if not can_transition(from_status, to_status):
        raise ValueError(
            f"Invalid transition from {from_status.value} to {to_status.value}"
        )
    return to_status
