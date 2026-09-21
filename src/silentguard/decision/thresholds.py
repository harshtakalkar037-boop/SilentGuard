"""Decision thresholds, loaded from the central configuration."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Config, load_config


@dataclass(frozen=True)
class DecisionThresholds:
    """Tunables governing state transitions.

    Attributes:
        suspect_threshold: Confidence at which a fall becomes suspected.
        confirm_threshold: Confidence at which the cancel window opens.
        confirmation_seconds: Length of the cancel window.
        use_audio_signal: Whether audio distress may raise confidence.
        audio_distress_threshold: Audio score treated as corroborating.
    """

    suspect_threshold: float = 0.55
    confirm_threshold: float = 0.70
    confirmation_seconds: float = 12.0
    use_audio_signal: bool = False
    audio_distress_threshold: float = 0.80

    def __post_init__(self) -> None:
        if not 0.0 <= self.suspect_threshold <= 1.0:
            raise ValueError("suspect_threshold must be within [0, 1]")
        if not 0.0 <= self.confirm_threshold <= 1.0:
            raise ValueError("confirm_threshold must be within [0, 1]")
        if self.confirm_threshold < self.suspect_threshold:
            raise ValueError("confirm_threshold must be >= suspect_threshold")
        if self.confirmation_seconds <= 0:
            raise ValueError("confirmation_seconds must be positive")

    @classmethod
    def from_config(cls, config: Config | None = None) -> "DecisionThresholds":
        """Build thresholds from ``config.yaml``."""
        cfg = config or load_config()
        section = cfg.section("decision")
        return cls(
            suspect_threshold=float(section["suspect_threshold"]),
            confirm_threshold=float(section["confirm_threshold"]),
            confirmation_seconds=float(section["confirmation_seconds"]),
            use_audio_signal=bool(section.get("use_audio_signal", False)),
            audio_distress_threshold=float(section.get("audio_distress_threshold", 0.8)),
        )
