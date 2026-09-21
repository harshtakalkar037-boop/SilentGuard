"""End-to-end tests: the same path the demos drive."""

from __future__ import annotations

import unittest

import conftest  # noqa: F401

from silentguard.actions import ActionManager, LocalAlert, MockIRController
from silentguard.audio import MockAudioDistressDetector
from silentguard.audio.detector_interface import AudioSignal
from silentguard.decision import SystemState
from silentguard.perception import build_pose_detector
from silentguard.runtime import GuardianRuntime


def make_runtime(scenario: str, **kwargs) -> GuardianRuntime:
    """Build a quiet runtime over a scripted scenario."""
    return GuardianRuntime(
        pose_source=build_pose_detector("synthetic", scenario=scenario),
        action_manager=ActionManager(
            ir_controller=MockIRController(verbose=False),
            local_alert=LocalAlert(verbose=False),
            verbose=False,
        ),
        verbose=False,
        **kwargs,
    )


def drain(runtime: GuardianRuntime) -> dict:
    for _ in runtime.run():
        pass
    return runtime.summary()


class TestAutonomousPipeline(unittest.TestCase):
    def test_fall_reaches_emergency_and_acts(self) -> None:
        runtime = make_runtime("fall")
        summary = drain(runtime)
        self.assertEqual(summary["final_state"], "EMERGENCY")
        self.assertEqual(summary["actions"], ["LIGHTS_ON", "TV_SOS", "LOCAL_ALERT"])

    def test_normal_activity_never_acts(self) -> None:
        summary = drain(make_runtime("normal"))
        self.assertEqual(summary["final_state"], "NORMAL")
        self.assertEqual(summary["actions"], [])

    def test_sitting_down_never_acts(self) -> None:
        summary = drain(make_runtime("sit_down"))
        self.assertEqual(summary["actions"], [])

    def test_cancellation_prevents_action(self) -> None:
        runtime = make_runtime("fall", cancel_hook=lambda now: now >= 6.0)
        summary = drain(runtime)
        self.assertEqual(summary["actions"], [])
        self.assertEqual(summary["final_state"], "NORMAL")

    def test_actions_fire_exactly_once(self) -> None:
        runtime = make_runtime("fall")
        drain(runtime)
        dispatched = [action for tick in runtime.ticks for action in tick.actions]
        self.assertEqual(len(dispatched), 3)

    def test_all_actions_report_as_simulated(self) -> None:
        summary = drain(make_runtime("fall"))
        self.assertTrue(summary["all_actions_simulated"])

    def test_reset_allows_a_second_run(self) -> None:
        runtime = make_runtime("fall")
        drain(runtime)
        runtime.reset()
        self.assertIs(runtime.state, SystemState.NORMAL)
        self.assertEqual(runtime.ticks, [])

    def test_audio_detector_is_consulted_when_supplied(self) -> None:
        runtime = make_runtime("fall", audio_detector=MockAudioDistressDetector())
        summary = drain(runtime)
        self.assertEqual(summary["final_state"], "EMERGENCY")


class TestMockAudioDetector(unittest.TestCase):
    def test_follows_its_schedule(self) -> None:
        detector = MockAudioDistressDetector(schedule={0.0: 0.0, 2.0: 0.9})
        self.assertEqual(detector.observe(1.0).distress_score, 0.0)
        self.assertEqual(detector.observe(2.5).distress_score, 0.9)

    def test_always_marks_itself_simulated(self) -> None:
        detector = MockAudioDistressDetector()
        self.assertTrue(detector.observe(5.0).is_simulated)
        self.assertFalse(detector.is_trained_model)

    def test_rejects_out_of_range_schedule(self) -> None:
        with self.assertRaises(ValueError):
            MockAudioDistressDetector(schedule={0.0: 2.0})

    def test_signal_validates_its_score(self) -> None:
        with self.assertRaises(ValueError):
            AudioSignal(timestamp=0.0, distress_score=-0.1)


if __name__ == "__main__":
    unittest.main()
