"""States and results for the SilentGuard decision engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


class SystemState(str, Enum):
    """The states the guardian can occupy.

    ``NORMAL`` -> ``FALL_SUSPECTED`` -> ``CONFIRMING`` -> ``EMERGENCY``
    with ``CANCELLED`` as the user-initiated exit from ``CONFIRMING``.
    """

    NORMAL = "NORMAL"
    FALL_SUSPECTED = "FALL_SUSPECTED"
    CONFIRMING = "CONFIRMING"
    EMERGENCY = "EMERGENCY"
    CANCELLED = "CANCELLED"

    def __str__(self) -> str:  # pragma: no cover - display only
        return self.value


@dataclass(frozen=True)
class DecisionResult:
    """One decision-engine output.

    Attributes:
        state: The state the system is in after this update.
        previous_state: The state it was in before this update.
        changed: True when this update caused a transition.
        reason: Human-readable explanation of the decision.
        confidence: The fall confidence that drove the decision.
        seconds_remaining: Time left in the confirmation window, if open.
        triggers_action: True exactly once, on entry to ``EMERGENCY``.
        evidence: The signal reasons carried up from perception.
    """

    state: SystemState
    previous_state: SystemState
    changed: bool
    reason: str
    confidence: float = 0.0
    seconds_remaining: Optional[float] = None
    triggers_action: bool = False
    evidence: Tuple[str, ...] = field(default_factory=tuple)
