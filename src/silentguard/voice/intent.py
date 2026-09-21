"""Intent representation for on-demand control."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IntentType(str, Enum):
    """What the user asked for."""

    APPLIANCE_CONTROL = "APPLIANCE_CONTROL"
    CANCEL_EMERGENCY = "CANCEL_EMERGENCY"
    RAISE_EMERGENCY = "RAISE_EMERGENCY"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:  # pragma: no cover - display only
        return self.value


@dataclass(frozen=True)
class Intent:
    """A parsed user command.

    Attributes:
        type: The intent category.
        device: Target device key, for appliance control.
        command: Command key, for appliance control.
        confidence: Parser confidence in [0, 1].
        utterance: The original text.
        explanation: Why the parser reached this result.
    """

    type: IntentType
    device: Optional[str] = None
    command: Optional[str] = None
    confidence: float = 0.0
    utterance: str = ""
    explanation: str = ""

    @property
    def is_actionable(self) -> bool:
        """True when this intent can be routed to the action layer."""
        return (
            self.type is IntentType.APPLIANCE_CONTROL
            and self.device is not None
            and self.command is not None
        )
