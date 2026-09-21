"""Temporal motion analysis over a sliding window of pose frames.

The fall detector never looks at a single frame. This module turns a stream of
:class:`~silentguard.perception.pose_detector.PoseFrame` objects into the
time-derived features the detector reasons about.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional, Tuple

from .pose_detector import PoseFrame


@dataclass(frozen=True)
class MotionFeatures:
    """Features derived from the recent pose history.

    Attributes:
        timestamp: Timestamp of the frame these features describe.
        descent_velocity: Downward hip velocity in normalised units/second.
            Positive means moving down the image.
        torso_angle: Torso angle from vertical in degrees (0 upright, 90 flat).
        aspect_ratio: Bounding-box width divided by height.
        stillness: Mean landmark displacement per second (lower is stiller).
        tracked: False when there was not enough history or no person present.
    """

    timestamp: float
    descent_velocity: float = 0.0
    torso_angle: Optional[float] = None
    aspect_ratio: Optional[float] = None
    stillness: Optional[float] = None
    tracked: bool = False


class MotionAnalyzer:
    """Maintains a time-bounded history of pose frames and derives features."""

    def __init__(self, history_seconds: float = 4.0) -> None:
        if history_seconds <= 0:
            raise ValueError("history_seconds must be positive")
        self.history_seconds = float(history_seconds)
        self._frames: Deque[PoseFrame] = deque()

    def reset(self) -> None:
        """Drop all accumulated history."""
        self._frames.clear()

    def update(self, frame: PoseFrame) -> MotionFeatures:
        """Add ``frame`` to the history and return the features it produces."""
        if not isinstance(frame, PoseFrame):
            raise TypeError("frame must be a PoseFrame")

        if not frame.present or not frame.keypoints:
            # Keep the history but report an untracked frame.
            return MotionFeatures(timestamp=frame.timestamp, tracked=False)

        self._frames.append(frame)
        self._evict(frame.timestamp)

        return MotionFeatures(
            timestamp=frame.timestamp,
            descent_velocity=self._descent_velocity(),
            torso_angle=frame.torso_angle_from_vertical(),
            aspect_ratio=self._aspect_ratio(frame),
            stillness=self._stillness(),
            tracked=len(self._frames) >= 2,
        )

    # -- internals ---------------------------------------------------------

    def _evict(self, now: float) -> None:
        cutoff = now - self.history_seconds
        while self._frames and self._frames[0].timestamp < cutoff:
            self._frames.popleft()

    def _descent_velocity(self, window: float = 0.7) -> float:
        """Peak downward hip velocity over the last ``window`` seconds."""
        if len(self._frames) < 2:
            return 0.0
        recent = [f for f in self._frames if f.timestamp >= self._frames[-1].timestamp - window]
        peak = 0.0
        for earlier, later in zip(recent, recent[1:]):
            a, b = earlier.hip_center, later.hip_center
            dt = later.timestamp - earlier.timestamp
            if a is None or b is None or dt <= 1e-6:
                continue
            velocity = (b[1] - a[1]) / dt  # y grows downward
            peak = max(peak, velocity)
        return peak

    @staticmethod
    def _aspect_ratio(frame: PoseFrame) -> Optional[float]:
        box = frame.bounding_box()
        if box is None:
            return None
        min_x, min_y, max_x, max_y = box
        height = max_y - min_y
        if height <= 1e-6:
            return None
        return (max_x - min_x) / height

    def _stillness(self, window: float = 1.5) -> Optional[float]:
        """Mean per-second landmark displacement over the recent window."""
        if len(self._frames) < 2:
            return None
        cutoff = self._frames[-1].timestamp - window
        recent = [f for f in self._frames if f.timestamp >= cutoff]
        if len(recent) < 2:
            return None

        totals: list[float] = []
        for earlier, later in zip(recent, recent[1:]):
            dt = later.timestamp - earlier.timestamp
            if dt <= 1e-6:
                continue
            shared = set(earlier.keypoints) & set(later.keypoints)
            if not shared:
                continue
            displacement = 0.0
            for name in shared:
                ax, ay = earlier.keypoints[name]
                bx, by = later.keypoints[name]
                displacement += ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
            totals.append((displacement / len(shared)) / dt)
        if not totals:
            return None
        return sum(totals) / len(totals)

    @property
    def history_size(self) -> int:
        """Number of frames currently retained."""
        return len(self._frames)

    @property
    def span(self) -> Tuple[float, float]:
        """``(first, last)`` timestamp in the retained history."""
        if not self._frames:
            return (0.0, 0.0)
        return (self._frames[0].timestamp, self._frames[-1].timestamp)
