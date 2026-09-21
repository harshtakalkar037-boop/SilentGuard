"""Pose extraction.

Two sources implement the same :class:`PoseDetector` contract:

* :class:`MediaPipePoseDetector` — real landmarks from a camera or video file.
  Requires the optional ``mediapipe`` dependency.
* :class:`SyntheticPoseSource` — scripted keypoints used for offline demos and
  tests. It is a **simulation**, not a recording of a real person, and every
  entry point that uses it says so in its output.

Coordinates are normalised to the frame (0.0-1.0), with y increasing downward,
matching MediaPipe's convention.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Protocol, Tuple

# The nine landmarks the fall detector reasons about, mapped to MediaPipe Pose
# landmark indices (https://developers.google.com/mediapipe).
KEYPOINT_NAMES: Dict[str, int] = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}


@dataclass(frozen=True)
class PoseFrame:
    """One frame of pose data.

    Attributes:
        timestamp: Seconds since the start of the stream (monotonic).
        keypoints: Mapping of landmark name to ``(x, y)`` in normalised units.
        present: False when no person was detected in the frame.
    """

    timestamp: float
    keypoints: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    present: bool = True

    def point(self, name: str) -> Optional[Tuple[float, float]]:
        """Return a landmark, or None when it was not detected."""
        return self.keypoints.get(name)

    def midpoint(self, left: str, right: str) -> Optional[Tuple[float, float]]:
        """Return the midpoint of a symmetric landmark pair, if both exist."""
        a, b = self.point(left), self.point(right)
        if a is None or b is None:
            return None
        return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)

    @property
    def shoulder_center(self) -> Optional[Tuple[float, float]]:
        return self.midpoint("left_shoulder", "right_shoulder")

    @property
    def hip_center(self) -> Optional[Tuple[float, float]]:
        return self.midpoint("left_hip", "right_hip")

    def bounding_box(self) -> Optional[Tuple[float, float, float, float]]:
        """Return ``(min_x, min_y, max_x, max_y)`` over all detected landmarks."""
        if not self.keypoints:
            return None
        xs = [p[0] for p in self.keypoints.values()]
        ys = [p[1] for p in self.keypoints.values()]
        return (min(xs), min(ys), max(xs), max(ys))

    def torso_angle_from_vertical(self) -> Optional[float]:
        """Angle in degrees between the torso axis and the vertical axis.

        0 degrees is fully upright; 90 degrees is fully horizontal.
        """
        shoulders, hips = self.shoulder_center, self.hip_center
        if shoulders is None or hips is None:
            return None
        dx = hips[0] - shoulders[0]
        dy = hips[1] - shoulders[1]
        if math.isclose(dx, 0.0) and math.isclose(dy, 0.0):
            return None
        angle = math.degrees(math.atan2(abs(dx), abs(dy)))
        return min(angle, 90.0)


class PoseDetector(Protocol):
    """Anything that can yield :class:`PoseFrame` objects in time order."""

    def frames(self) -> Iterator[PoseFrame]:
        """Yield pose frames until the source is exhausted."""
        ...

    def close(self) -> None:
        """Release any underlying resources."""
        ...


class SyntheticPoseSource:
    """Scripted pose frames for offline demos and deterministic tests.

    This generates geometry, not predictions. It exists so the decision engine
    and action layer can be exercised without a camera. Scenarios:

    * ``"fall"``      — stands, drops rapidly, lands horizontal, stays still.
    * ``"fall_cancel"`` — same descent, then the subject gets back up.
    * ``"normal"``    — stands and shifts weight, never leaves upright posture.
    * ``"sit_down"``  — a slow, controlled descent that must NOT read as a fall.
    """

    SCENARIOS = ("fall", "fall_cancel", "normal", "sit_down")

    def __init__(
        self,
        scenario: str = "fall",
        fps: float = 15.0,
        duration: float = 22.0,
    ) -> None:
        if scenario not in self.SCENARIOS:
            raise ValueError(
                f"Unknown scenario {scenario!r}; expected one of {self.SCENARIOS}"
            )
        if fps <= 0:
            raise ValueError("fps must be positive")
        if duration <= 0:
            raise ValueError("duration must be positive")
        self.scenario = scenario
        self.fps = float(fps)
        self.duration = float(duration)
        self.is_simulated = True

    def frames(self) -> Iterator[PoseFrame]:
        """Yield the scripted frame sequence for the configured scenario."""
        step = 1.0 / self.fps
        count = int(self.duration * self.fps)
        for index in range(count):
            timestamp = index * step
            yield self._frame_at(timestamp)

    def close(self) -> None:
        """No resources to release for the synthetic source."""
        return None

    # -- scenario geometry -------------------------------------------------

    def _frame_at(self, t: float) -> PoseFrame:
        if self.scenario == "normal":
            return self._upright(t, sway=0.012)
        if self.scenario == "sit_down":
            return self._slow_descent(t)
        return self._fall_sequence(t, recover=self.scenario == "fall_cancel")

    def _upright(self, t: float, sway: float = 0.0) -> PoseFrame:
        drift = sway * math.sin(t * 1.7)
        return self._build(
            t,
            hip_y=0.55,
            shoulder_y=0.35,
            center_x=0.50 + drift,
            horizontal=False,
        )

    def _slow_descent(self, t: float) -> PoseFrame:
        # Controlled sit: 0.55 -> 0.68 over four seconds, stays upright.
        progress = min(max((t - 2.0) / 4.0, 0.0), 1.0)
        hip_y = 0.55 + 0.13 * progress
        return self._build(
            t,
            hip_y=hip_y,
            shoulder_y=hip_y - 0.20,
            center_x=0.50,
            horizontal=False,
        )

    def _fall_sequence(self, t: float, recover: bool) -> PoseFrame:
        stand_until = 3.0
        fall_duration = 0.6
        landed_at = stand_until + fall_duration

        if t < stand_until:
            return self._upright(t, sway=0.008)

        if t < landed_at:
            progress = (t - stand_until) / fall_duration
            hip_y = 0.55 + (0.33 * progress)
            shoulder_y = 0.35 + (0.45 * progress)
            return self._build(
                t,
                hip_y=hip_y,
                shoulder_y=shoulder_y,
                center_x=0.50,
                horizontal=progress > 0.6,
            )

        if recover and t > landed_at + 4.0:
            # Subject gets back up; posture returns to upright.
            progress = min((t - landed_at - 4.0) / 1.5, 1.0)
            hip_y = 0.88 - 0.33 * progress
            shoulder_y = 0.80 - 0.45 * progress
            return self._build(
                t,
                hip_y=hip_y,
                shoulder_y=shoulder_y,
                center_x=0.50,
                horizontal=progress < 0.4,
            )

        # Landed and motionless.
        return self._build(t, hip_y=0.88, shoulder_y=0.80, center_x=0.50, horizontal=True)

    def _build(
        self,
        t: float,
        hip_y: float,
        shoulder_y: float,
        center_x: float,
        horizontal: bool,
    ) -> PoseFrame:
        """Assemble a full landmark set from a few body parameters."""
        if horizontal:
            # Body laid out along the x axis: shoulders and hips separate
            # horizontally and the limbs extend sideways.
            points = {
                "nose": (center_x - 0.22, shoulder_y - 0.01),
                "left_shoulder": (center_x - 0.16, shoulder_y - 0.03),
                "right_shoulder": (center_x - 0.16, shoulder_y + 0.03),
                "left_hip": (center_x + 0.02, hip_y - 0.03),
                "right_hip": (center_x + 0.02, hip_y + 0.03),
                "left_knee": (center_x + 0.14, hip_y - 0.03),
                "right_knee": (center_x + 0.14, hip_y + 0.03),
                "left_ankle": (center_x + 0.26, hip_y - 0.03),
                "right_ankle": (center_x + 0.26, hip_y + 0.03),
            }
        else:
            knee_y = min(hip_y + 0.18, 0.97)
            ankle_y = min(hip_y + 0.34, 0.99)
            points = {
                "nose": (center_x, shoulder_y - 0.09),
                "left_shoulder": (center_x - 0.07, shoulder_y),
                "right_shoulder": (center_x + 0.07, shoulder_y),
                "left_hip": (center_x - 0.05, hip_y),
                "right_hip": (center_x + 0.05, hip_y),
                "left_knee": (center_x - 0.05, knee_y),
                "right_knee": (center_x + 0.05, knee_y),
                "left_ankle": (center_x - 0.05, ankle_y),
                "right_ankle": (center_x + 0.05, ankle_y),
            }
        clamped = {
            name: (min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0))
            for name, (x, y) in points.items()
        }
        return PoseFrame(timestamp=t, keypoints=clamped, present=True)


class MediaPipePoseDetector:
    """Real pose landmarks from a camera index or a video file path.

    Raises:
        RuntimeError: if ``mediapipe``/``opencv-python`` are not installed, or
            the capture source cannot be opened.
    """

    def __init__(
        self,
        source: int | str = 0,
        min_visibility: float = 0.5,
        model_complexity: int = 0,
    ) -> None:
        try:
            import cv2  # noqa: F401
            import mediapipe as mp
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "MediaPipePoseDetector needs 'mediapipe' and 'opencv-python'. "
                "Install them with: pip install -r requirements.txt"
            ) from exc

        self._cv2 = cv2
        self._mp = mp
        self.source = source
        self.min_visibility = float(min_visibility)
        self.is_simulated = False
        self._capture = cv2.VideoCapture(source)
        if not self._capture.isOpened():
            raise RuntimeError(f"Could not open video source: {source!r}")
        self._pose = mp.solutions.pose.Pose(
            model_complexity=model_complexity,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def frames(self) -> Iterator[PoseFrame]:
        """Yield a :class:`PoseFrame` per decoded video frame."""
        cv2 = self._cv2
        fps = self._capture.get(cv2.CAP_PROP_FPS) or 0.0
        step = 1.0 / fps if fps > 1e-3 else 1.0 / 30.0
        index = 0
        while True:
            ok, frame = self._capture.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self._pose.process(rgb)
            timestamp = index * step
            index += 1
            landmarks = getattr(result, "pose_landmarks", None)
            if landmarks is None:
                yield PoseFrame(timestamp=timestamp, keypoints={}, present=False)
                continue
            points: Dict[str, Tuple[float, float]] = {}
            for name, idx in KEYPOINT_NAMES.items():
                landmark = landmarks.landmark[idx]
                if getattr(landmark, "visibility", 1.0) < self.min_visibility:
                    continue
                points[name] = (float(landmark.x), float(landmark.y))
            yield PoseFrame(
                timestamp=timestamp, keypoints=points, present=bool(points)
            )

    def close(self) -> None:
        """Release the capture handle and the MediaPipe graph."""
        try:
            self._capture.release()
        finally:
            self._pose.close()


def build_pose_detector(
    source: str = "synthetic",
    *,
    scenario: str = "fall",
    video: Optional[str] = None,
    camera: int = 0,
    min_visibility: float = 0.5,
) -> PoseDetector:
    """Construct the configured pose source.

    Args:
        source: ``"synthetic"`` or ``"mediapipe"``.
        scenario: Scenario name when ``source`` is ``"synthetic"``.
        video: Optional video path when ``source`` is ``"mediapipe"``.
        camera: Camera index used when ``video`` is None.
        min_visibility: Landmark visibility floor for MediaPipe.
    """
    if source == "synthetic":
        return SyntheticPoseSource(scenario=scenario)
    if source == "mediapipe":
        return MediaPipePoseDetector(
            source=video if video is not None else camera,
            min_visibility=min_visibility,
        )
    raise ValueError(f"Unknown pose source {source!r}; expected 'synthetic' or 'mediapipe'")
