"""On-device alerting: the part of the response that needs no appliance.

A local alert is an audible/visual alarm raised by the phone itself. In the
prototype it prints and records; on a handset it maps to a full-volume alarm
tone and a high-priority notification (see ``platform/android/README.md``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlertRecord:
    """One raised alert.

    Attributes:
        level: ``"info"``, ``"warning"`` or ``"emergency"``.
        message: Text shown to whoever is nearby.
        raised_at: UTC ISO-8601 timestamp.
    """

    level: str
    message: str
    raised_at: str


class LocalAlert:
    """Raises on-device alerts and keeps a session history."""

    LEVELS = ("info", "warning", "emergency")

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self._history: List[AlertRecord] = []

    def raise_alert(
        self, message: str, level: str = "emergency", at: Optional[str] = None
    ) -> AlertRecord:
        """Raise an alert and return its record."""
        if level not in self.LEVELS:
            raise ValueError(f"level must be one of {self.LEVELS}, got {level!r}")
        if not message or not message.strip():
            raise ValueError("alert message must not be empty")

        record = AlertRecord(
            level=level,
            message=message.strip(),
            raised_at=at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self._history.append(record)
        line = f"[LOCAL ALERT | {record.level.upper()}] {record.message}"
        logger.warning(line)
        if self.verbose:
            print(line)
        return record

    @property
    def history(self) -> List[AlertRecord]:
        """All alerts raised this session."""
        return list(self._history)

    def clear(self) -> None:
        """Forget the alert history."""
        self._history.clear()
