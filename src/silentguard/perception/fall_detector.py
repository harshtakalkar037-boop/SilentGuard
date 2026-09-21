"""Explainable, multi-signal fall detection.

A fall is never declared from one frame or one cue. Four independent signals
are scored, weighted, and combined into a single confidence value, and every
contribution is reported so the decision can be explained to a human:

1. **Rapid descent** — the hips moved down quickly, recently.
2. **Posture change** — the torso is no longer near-vertical.
3. **Horizontal state** — the body's bounding box is wider than it is tall.
4. **Sustained inactivity** — the subject has stayed still since landing.

Thresholds and weights come from ``config.yaml``; nothing here is hardcoded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from ..config import Config, load_config
from .motion_analyzer import MotionAnalyzer, MotionFeatures
from .pose_detector import PoseFrame


@dataclass(frozen=True)
class FallSignals:
    """The output of one detector update.

    Attributes:
        timestamp: Frame timestamp in seconds.
        confidence: Weighted fall confidence in [0.0, 1.0].
        contributions: Per-signal score in [0.0, 1.0] before weighting.
        inactivity_duration: Seconds the subject has been continuously still.
        posture_state: One of ``"upright"``, ``"leaning"``, ``"horizontal"``,
            or ``"unknown"``.
        tracked: False when no usable pose was available for this frame.
        reasons: Human-readable strings describing which cues fired.
    """

    timestamp: float
    confidence: float = 0.0
    contributions: Dict[str, float] = field(default_factory=dict)
    inactivity_duration: float = 0.0
    posture_state: str = "unknown"
    tracked: bool = False
    reasons: tuple[str, ...] = ()


class FallDetector:
    """Combines motion features into an explainable fall confidence score."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or load_config()
        params = self.config.section("fall_detection")
        self._downward_velocity = float(params["downward_velocity"])
        self._posture_degrees = float(params["posture_change_degrees"])
        self._horizontal_ratio = float(params["horizontal_ratio"])
        self._stillness_threshold = float(params["stillness_threshold"])
        self._inactivity_seconds = float(params["inactivity_seconds"])
        self._descent_memory = float(params["descent_memory_seconds"])
        self._weights = {k: float(v) for k, v in params["weights"].items()}

        self._analyzer = MotionAnalyzer(
            history_seconds=float(self.config.get("perception.history_seconds", 4.0))
        )
        self._last_descent_at: Optional[float] = None
        self._still_since: Optional[float] = None

    def reset(self) -> None:
        """Clear all temporal state. Used between demo runs and in tests."""
        self._analyzer.reset()
        self._last_descent_at = None
        self._still_since = None

    def update(self, frame: PoseFrame) -> FallSignals:
        """Process one pose frame and return the resulting signals."""
        features = self._analyzer.update(frame)
        if not features.tracked:
            return FallSignals(timestamp=frame.timestamp, tracked=False)
        return self.evaluate(features)

    def evaluate(self, features: MotionFeatures) -> FallSignals:
        """Score pre-computed ``features``. Separated out so it is unit-testable."""
        now = features.timestamp
        reasons: list[str] = []

        # 1. Rapid descent, with a memory window so the cue survives the landing.
        if features.descent_velocity >= self._downward_velocity:
            self._last_descent_at = now
            reasons.append(
                f"rapid downward motion ({features.descent_velocity:.2f} u/s)"
            )
        descent_score = 0.0
        if self._last_descent_at is not None:
            age = now - self._last_descent_at
            if age <= self._descent_memory:
                descent_score = 1.0 - (age / self._descent_memory) * 0.35

        # 2. Posture change.
        posture_score = 0.0
        posture_state = "unknown"
        if features.torso_angle is not None:
            angle = features.torso_angle
            if angle >= self._posture_degrees:
                posture_score = min(angle / 90.0, 1.0)
                posture_state = "horizontal" if angle >= 70.0 else "leaning"
                reasons.append(f"torso {angle:.0f} deg from vertical")
            else:
                posture_state = "upright"

        # 3. Horizontal body state.
        horizontal_score = 0.0
        if features.aspect_ratio is not None and features.aspect_ratio >= self._horizontal_ratio:
            horizontal_score = min(features.aspect_ratio / (self._horizontal_ratio * 2.0), 1.0)
            reasons.append(f"body wider than tall (ratio {features.aspect_ratio:.2f})")
            if posture_state in ("unknown", "leaning"):
                posture_state = "horizontal"

        # 4. Sustained inactivity.
        inactivity = self._update_inactivity(now, features.stillness)
        inactivity_score = 0.0
        if inactivity >= self._inactivity_seconds:
            inactivity_score = min(inactivity / (self._inactivity_seconds * 2.0), 1.0)
            reasons.append(f"still for {inactivity:.1f}s")

        contributions = {
            "rapid_descent": round(descent_score, 4),
            "posture_change": round(posture_score, 4),
            "horizontal_state": round(horizontal_score, 4),
            "sustained_inactivity": round(inactivity_score, 4),
        }
        confidence = sum(
            contributions[name] * self._weights.get(name, 0.0) for name in contributions
        )
        # A fall requires descent evidence. Without it, a person lying on a sofa
        # or a mis-framed camera cannot climb past the suspect threshold.
        if descent_score <= 0.0:
            confidence *= 0.35
            reasons.append("no recent descent evidence (confidence damped)")

        return FallSignals(
            timestamp=now,
            confidence=round(min(max(confidence, 0.0), 1.0), 4),
            contributions=contributions,
            inactivity_duration=round(inactivity, 2),
            posture_state=posture_state,
            tracked=True,
            reasons=tuple(reasons),
        )

    # -- internals ---------------------------------------------------------

    def _update_inactivity(self, now: float, stillness: Optional[float]) -> float:
        if stillness is None:
            return 0.0
        if stillness <= self._stillness_threshold:
            if self._still_since is None:
                self._still_since = now
            return max(now - self._still_since, 0.0)
        self._still_since = None
        return 0.0
