"""A scripted audio detector for wiring and tests.

This is **not** a classifier. It replays a fixed schedule of scores so the
fusion path through the decision engine can be exercised deterministically.
Every signal it emits carries ``is_simulated=True``.
"""

from __future__ import annotations

from typing import Dict, Optional

from .detector_interface import AudioDistressDetector, AudioSignal


class MockAudioDistressDetector(AudioDistressDetector):
    """Returns pre-scripted distress scores keyed by time window."""

    is_trained_model = False

    def __init__(
        self,
        schedule: Optional[Dict[float, float]] = None,
        label: str = "simulated_distress",
    ) -> None:
        """
        Args:
            schedule: Mapping of "from this timestamp onward" to distress score.
                Defaults to a quiet room that becomes distressed at t=3.5s.
            label: Label attached to non-zero scores.
        """
        self._schedule = dict(schedule) if schedule else {0.0: 0.0, 3.5: 0.85}
        for score in self._schedule.values():
            if not 0.0 <= float(score) <= 1.0:
                raise ValueError("scheduled scores must be within [0, 1]")
        self.label = label

    def observe(self, timestamp: float) -> AudioSignal:
        """Return the scripted signal in force at ``timestamp``."""
        applicable = [t for t in self._schedule if t <= timestamp]
        score = self._schedule[max(applicable)] if applicable else 0.0
        return AudioSignal(
            timestamp=timestamp,
            distress_score=float(score),
            label=self.label if score > 0 else "none",
            is_simulated=True,
        )
