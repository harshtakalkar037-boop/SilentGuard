"""The contract any audio distress detector must satisfy."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AudioSignal:
    """One audio observation.

    Attributes:
        timestamp: Seconds since the start of the stream.
        distress_score: Confidence in [0, 1] that distress was heard.
        label: Coarse class name, e.g. ``"speech"``, ``"impact"``, ``"none"``.
        is_simulated: True when the score did not come from a trained model.
    """

    timestamp: float
    distress_score: float = 0.0
    label: str = "none"
    is_simulated: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.distress_score <= 1.0:
            raise ValueError("distress_score must be within [0, 1]")


class AudioDistressDetector(ABC):
    """Produces an :class:`AudioSignal` for a given moment in time."""

    #: False for any implementation not backed by a trained model.
    is_trained_model: bool = False

    @abstractmethod
    def observe(self, timestamp: float) -> AudioSignal:
        """Return the audio signal for ``timestamp``."""

    def close(self) -> None:
        """Release any audio resources. Default is a no-op."""
        return None
