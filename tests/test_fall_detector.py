"""Tests for the perception layer: motion features and fall scoring."""

from __future__ import annotations

import unittest

import conftest  # noqa: F401  (import for its side effect: sys.path)

from silentguard.config import load_config
from silentguard.perception import FallDetector, MotionAnalyzer, build_pose_detector
from silentguard.perception.pose_detector import PoseFrame, SyntheticPoseSource


def run_scenario(scenario: str) -> tuple[float, float]:
    """Return ``(peak_confidence, peak_inactivity)`` for a scripted scenario."""
    detector = FallDetector()
    source = build_pose_detector("synthetic", scenario=scenario)
    peak_conf = 0.0
    peak_inactivity = 0.0
    for frame in source.frames():
        signals = detector.update(frame)
        peak_conf = max(peak_conf, signals.confidence)
        peak_inactivity = max(peak_inactivity, signals.inactivity_duration)
    return peak_conf, peak_inactivity


class TestSyntheticPoseSource(unittest.TestCase):
    def test_rejects_unknown_scenario(self) -> None:
        with self.assertRaises(ValueError):
            SyntheticPoseSource(scenario="teleport")

    def test_rejects_invalid_timing(self) -> None:
        with self.assertRaises(ValueError):
            SyntheticPoseSource(fps=0)
        with self.assertRaises(ValueError):
            SyntheticPoseSource(duration=-1)

    def test_frames_are_time_ordered_and_normalised(self) -> None:
        frames = list(SyntheticPoseSource("fall", fps=10, duration=2).frames())
        self.assertEqual(len(frames), 20)
        timestamps = [f.timestamp for f in frames]
        self.assertEqual(timestamps, sorted(timestamps))
        for frame in frames:
            for x, y in frame.keypoints.values():
                self.assertGreaterEqual(x, 0.0)
                self.assertLessEqual(x, 1.0)
                self.assertGreaterEqual(y, 0.0)
                self.assertLessEqual(y, 1.0)

    def test_marks_itself_as_simulated(self) -> None:
        self.assertTrue(SyntheticPoseSource("fall").is_simulated)


class TestPoseFrameGeometry(unittest.TestCase):
    def test_upright_torso_angle_is_small(self) -> None:
        frame = PoseFrame(
            timestamp=0.0,
            keypoints={
                "left_shoulder": (0.45, 0.35),
                "right_shoulder": (0.55, 0.35),
                "left_hip": (0.45, 0.55),
                "right_hip": (0.55, 0.55),
            },
        )
        self.assertLess(frame.torso_angle_from_vertical(), 10.0)

    def test_horizontal_torso_angle_is_large(self) -> None:
        frame = PoseFrame(
            timestamp=0.0,
            keypoints={
                "left_shoulder": (0.30, 0.80),
                "right_shoulder": (0.30, 0.86),
                "left_hip": (0.60, 0.80),
                "right_hip": (0.60, 0.86),
            },
        )
        self.assertGreater(frame.torso_angle_from_vertical(), 70.0)

    def test_angle_is_none_without_both_landmark_pairs(self) -> None:
        frame = PoseFrame(timestamp=0.0, keypoints={"nose": (0.5, 0.2)})
        self.assertIsNone(frame.torso_angle_from_vertical())


class TestMotionAnalyzer(unittest.TestCase):
    def test_rejects_non_positive_history(self) -> None:
        with self.assertRaises(ValueError):
            MotionAnalyzer(history_seconds=0)

    def test_first_frame_is_untracked(self) -> None:
        analyzer = MotionAnalyzer()
        frame = next(iter(SyntheticPoseSource("normal", fps=10, duration=1).frames()))
        self.assertFalse(analyzer.update(frame).tracked)

    def test_absent_person_yields_untracked_features(self) -> None:
        analyzer = MotionAnalyzer()
        features = analyzer.update(PoseFrame(timestamp=1.0, keypoints={}, present=False))
        self.assertFalse(features.tracked)

    def test_detects_downward_velocity(self) -> None:
        analyzer = MotionAnalyzer()
        peak = 0.0
        for frame in SyntheticPoseSource("fall", fps=20, duration=5).frames():
            peak = max(peak, analyzer.update(frame).descent_velocity)
        self.assertGreater(peak, 0.3)

    def test_history_is_time_bounded(self) -> None:
        analyzer = MotionAnalyzer(history_seconds=1.0)
        for frame in SyntheticPoseSource("normal", fps=20, duration=5).frames():
            analyzer.update(frame)
        first, last = analyzer.span
        self.assertLessEqual(last - first, 1.0 + 1e-6)


class TestFallDetector(unittest.TestCase):
    def test_fall_scenario_crosses_confirm_threshold(self) -> None:
        threshold = load_config().get("decision.confirm_threshold")
        peak, _ = run_scenario("fall")
        self.assertGreaterEqual(peak, threshold)

    def test_normal_activity_never_suspected(self) -> None:
        suspect = load_config().get("decision.suspect_threshold")
        peak, _ = run_scenario("normal")
        self.assertLess(peak, suspect)

    def test_sitting_down_is_not_a_fall(self) -> None:
        """The controlled-descent case that naive height checks get wrong."""
        suspect = load_config().get("decision.suspect_threshold")
        peak, _ = run_scenario("sit_down")
        self.assertLess(peak, suspect)

    def test_inactivity_accumulates_after_landing(self) -> None:
        _, inactivity = run_scenario("fall")
        self.assertGreater(inactivity, 3.0)

    def test_untracked_frame_yields_zero_confidence(self) -> None:
        detector = FallDetector()
        signals = detector.update(PoseFrame(timestamp=0.5, keypoints={}, present=False))
        self.assertFalse(signals.tracked)
        self.assertEqual(signals.confidence, 0.0)

    def test_reset_clears_temporal_state(self) -> None:
        detector = FallDetector()
        for frame in SyntheticPoseSource("fall", fps=15, duration=8).frames():
            detector.update(frame)
        detector.reset()
        first = detector.update(
            next(iter(SyntheticPoseSource("fall", fps=15, duration=1).frames()))
        )
        self.assertEqual(first.confidence, 0.0)

    def test_signals_explain_themselves(self) -> None:
        detector = FallDetector()
        explained = False
        for frame in SyntheticPoseSource("fall", fps=15, duration=8).frames():
            signals = detector.update(frame)
            if signals.confidence > 0.5:
                self.assertTrue(signals.reasons)
                self.assertEqual(
                    set(signals.contributions),
                    {
                        "rapid_descent",
                        "posture_change",
                        "horizontal_state",
                        "sustained_inactivity",
                    },
                )
                explained = True
                break
        self.assertTrue(explained, "fall scenario never produced a scored frame")


if __name__ == "__main__":
    unittest.main()
