"""Tests for the decision engine: state transitions and the cancel window."""

from __future__ import annotations

import unittest

import conftest  # noqa: F401

from silentguard.decision import DecisionEngine, DecisionThresholds, SystemState
from silentguard.perception.fall_detector import FallSignals


def signals(timestamp: float, confidence: float) -> FallSignals:
    """Build a minimal FallSignals for driving the engine directly."""
    return FallSignals(timestamp=timestamp, confidence=confidence, tracked=True)


class TestThresholds(unittest.TestCase):
    def test_confirm_must_not_be_below_suspect(self) -> None:
        with self.assertRaises(ValueError):
            DecisionThresholds(suspect_threshold=0.8, confirm_threshold=0.5)

    def test_window_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            DecisionThresholds(confirmation_seconds=0)

    def test_rejects_out_of_range_confidence(self) -> None:
        with self.assertRaises(ValueError):
            DecisionThresholds(suspect_threshold=1.5)

    def test_loads_from_config(self) -> None:
        thresholds = DecisionThresholds.from_config()
        self.assertGreater(thresholds.confirmation_seconds, 0)
        self.assertGreaterEqual(thresholds.confirm_threshold, thresholds.suspect_threshold)


class TestStateTransitions(unittest.TestCase):
    def setUp(self) -> None:
        self.thresholds = DecisionThresholds(
            suspect_threshold=0.55, confirm_threshold=0.70, confirmation_seconds=10.0
        )
        self.engine = DecisionEngine(self.thresholds)

    def test_starts_normal(self) -> None:
        self.assertIs(self.engine.state, SystemState.NORMAL)

    def test_low_confidence_stays_normal(self) -> None:
        result = self.engine.update(signals(0.0, 0.10))
        self.assertIs(result.state, SystemState.NORMAL)
        self.assertFalse(result.changed)

    def test_mid_confidence_suspects(self) -> None:
        result = self.engine.update(signals(0.0, 0.60))
        self.assertIs(result.state, SystemState.FALL_SUSPECTED)
        self.assertTrue(result.changed)

    def test_high_confidence_opens_confirmation_window(self) -> None:
        result = self.engine.update(signals(1.0, 0.80))
        self.assertIs(result.state, SystemState.CONFIRMING)
        self.assertEqual(result.seconds_remaining, 10.0)
        self.assertEqual(self.engine.confirm_started_at, 1.0)

    def test_window_elapsing_confirms_emergency(self) -> None:
        self.engine.update(signals(0.0, 0.80))
        mid = self.engine.update(signals(5.0, 0.80))
        self.assertIs(mid.state, SystemState.CONFIRMING)
        self.assertAlmostEqual(mid.seconds_remaining, 5.0)
        final = self.engine.update(signals(10.5, 0.80))
        self.assertIs(final.state, SystemState.EMERGENCY)
        self.assertTrue(final.triggers_action)

    def test_action_fires_exactly_once(self) -> None:
        self.engine.update(signals(0.0, 0.80))
        self.engine.update(signals(11.0, 0.80))
        later = [self.engine.update(signals(t, 0.80)) for t in (12.0, 13.0, 14.0)]
        self.assertTrue(all(not r.triggers_action for r in later))

    def test_emergency_is_latched(self) -> None:
        """A quiet frame after confirmation must not undo the emergency."""
        self.engine.update(signals(0.0, 0.80))
        self.engine.update(signals(11.0, 0.80))
        result = self.engine.update(signals(12.0, 0.00))
        self.assertIs(result.state, SystemState.EMERGENCY)

    def test_confidence_dropping_before_window_returns_to_normal(self) -> None:
        self.engine.update(signals(0.0, 0.60))
        result = self.engine.update(signals(1.0, 0.05))
        self.assertIs(result.state, SystemState.NORMAL)

    def test_every_result_carries_a_reason(self) -> None:
        for timestamp, confidence in ((0.0, 0.1), (1.0, 0.6), (2.0, 0.8), (20.0, 0.8)):
            result = self.engine.update(signals(timestamp, confidence))
            self.assertTrue(result.reason.strip())

    def test_rejects_wrong_signal_type(self) -> None:
        with self.assertRaises(TypeError):
            self.engine.update({"confidence": 0.9})  # type: ignore[arg-type]


class TestCancellation(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = DecisionEngine(
            DecisionThresholds(confirm_threshold=0.70, confirmation_seconds=10.0)
        )

    def test_cancel_during_window_returns_to_normal(self) -> None:
        self.engine.update(signals(0.0, 0.85))
        result = self.engine.update(signals(3.0, 0.85), cancel_requested=True)
        self.assertIs(result.state, SystemState.NORMAL)
        self.assertIn("cancel", result.reason.lower())

    def test_cancel_prevents_emergency(self) -> None:
        self.engine.update(signals(0.0, 0.85))
        self.engine.update(signals(3.0, 0.85), cancel_requested=True)
        result = self.engine.update(signals(20.0, 0.10))
        self.assertIs(result.state, SystemState.NORMAL)
        self.assertFalse(result.triggers_action)

    def test_cancel_in_normal_state_is_a_no_op(self) -> None:
        result = self.engine.update(signals(0.0, 0.10), cancel_requested=True)
        self.assertIs(result.state, SystemState.NORMAL)

    def test_cancel_after_emergency_does_not_unlatch(self) -> None:
        self.engine.update(signals(0.0, 0.85))
        self.engine.update(signals(11.0, 0.85))
        result = self.engine.update(signals(12.0, 0.85), cancel_requested=True)
        self.assertIs(result.state, SystemState.EMERGENCY)

    def test_reset_clears_everything(self) -> None:
        self.engine.update(signals(0.0, 0.85))
        self.engine.update(signals(11.0, 0.85))
        self.engine.reset()
        self.assertIs(self.engine.state, SystemState.NORMAL)
        self.assertIsNone(self.engine.confirm_started_at)


class TestAudioCorroboration(unittest.TestCase):
    def test_audio_ignored_when_disabled(self) -> None:
        engine = DecisionEngine(DecisionThresholds(use_audio_signal=False))
        result = engine.update(signals(0.0, 0.10), audio_distress=1.0)
        self.assertIs(result.state, SystemState.NORMAL)

    def test_audio_alone_cannot_raise_an_emergency(self) -> None:
        """Loud noise with no visual evidence must not confirm a fall."""
        engine = DecisionEngine(
            DecisionThresholds(use_audio_signal=True, audio_distress_threshold=0.8)
        )
        for timestamp in range(0, 40):
            result = engine.update(signals(float(timestamp), 0.05), audio_distress=1.0)
        self.assertIs(result.state, SystemState.NORMAL)

    def test_audio_corroborates_existing_visual_evidence(self) -> None:
        engine = DecisionEngine(
            DecisionThresholds(
                suspect_threshold=0.55,
                confirm_threshold=0.70,
                use_audio_signal=True,
                audio_distress_threshold=0.8,
            )
        )
        result = engine.update(signals(0.0, 0.65), audio_distress=0.9)
        self.assertIs(result.state, SystemState.CONFIRMING)

    def test_rejects_out_of_range_audio_score(self) -> None:
        engine = DecisionEngine()
        with self.assertRaises(ValueError):
            engine.update(signals(0.0, 0.1), audio_distress=1.4)


if __name__ == "__main__":
    unittest.main()
