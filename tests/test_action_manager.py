"""Tests for the action layer: IR resolution, dispatch, and honest failure."""

from __future__ import annotations

import unittest

import conftest  # noqa: F401

from silentguard.actions import (
    ActionManager,
    IRTransmissionError,
    LocalAlert,
    MockIRController,
    UnavailableIRController,
)
from silentguard.appliances import CommandRegistry
from silentguard.appliances.command_registry import ApplianceError
from silentguard.config import load_config


class TestCommandRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CommandRegistry()

    def test_loads_bundled_profiles(self) -> None:
        for device in ("lights", "tv", "fan"):
            self.assertIn(device, self.registry.devices)

    def test_resolves_a_command(self) -> None:
        command = self.registry.resolve("lights", "ON")
        self.assertEqual(command.device, "lights")
        self.assertEqual(command.command, "ON")
        self.assertTrue(command.code_id)

    def test_resolution_is_case_insensitive(self) -> None:
        self.assertEqual(self.registry.resolve("TV", "sos").command, "SOS")

    def test_repeat_is_read_from_the_profile(self) -> None:
        self.assertGreater(self.registry.resolve("tv", "SOS").repeat, 1)

    def test_unknown_device_raises(self) -> None:
        with self.assertRaises(ApplianceError):
            self.registry.resolve("kettle", "ON")

    def test_unsupported_command_raises(self) -> None:
        with self.assertRaises(ApplianceError):
            self.registry.resolve("fan", "VOLUME_UP")

    def test_supports_reports_without_raising(self) -> None:
        self.assertTrue(self.registry.supports("tv", "VOLUME_UP"))
        self.assertFalse(self.registry.supports("fan", "VOLUME_UP"))
        self.assertFalse(self.registry.supports("kettle", "ON"))


class TestMockIRController(unittest.TestCase):
    def test_records_sent_commands(self) -> None:
        controller = MockIRController(verbose=False)
        registry = CommandRegistry()
        controller.send(registry.resolve("lights", "ON"))
        controller.send(registry.resolve("tv", "SOS"))
        self.assertEqual([c.command for c in controller.sent], ["ON", "SOS"])

    def test_declares_itself_not_real_hardware(self) -> None:
        controller = MockIRController(verbose=False)
        self.assertFalse(controller.is_real_hardware)
        self.assertTrue(controller.available())

    def test_rejects_wrong_type(self) -> None:
        with self.assertRaises(TypeError):
            MockIRController(verbose=False).send("lights on")  # type: ignore[arg-type]


class TestUnavailableIRController(unittest.TestCase):
    def test_refuses_rather_than_pretending(self) -> None:
        """An emergency system must not report a fake success."""
        controller = UnavailableIRController()
        self.assertFalse(controller.available())
        with self.assertRaises(IRTransmissionError):
            controller.send(CommandRegistry().resolve("lights", "ON"))


class TestLocalAlert(unittest.TestCase):
    def test_records_history(self) -> None:
        alert = LocalAlert(verbose=False)
        alert.raise_alert("test message")
        self.assertEqual(len(alert.history), 1)
        self.assertEqual(alert.history[0].level, "emergency")

    def test_rejects_bad_level(self) -> None:
        with self.assertRaises(ValueError):
            LocalAlert(verbose=False).raise_alert("x", level="catastrophe")

    def test_rejects_empty_message(self) -> None:
        with self.assertRaises(ValueError):
            LocalAlert(verbose=False).raise_alert("   ")


class TestActionManager(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = MockIRController(verbose=False)
        self.manager = ActionManager(
            ir_controller=self.controller,
            local_alert=LocalAlert(verbose=False),
            verbose=False,
        )

    def test_dispatches_named_action_to_ir(self) -> None:
        result = self.manager.dispatch("LIGHTS_ON")
        self.assertTrue(result.succeeded)
        self.assertEqual(self.controller.sent[-1].device, "lights")

    def test_local_alert_does_not_use_ir(self) -> None:
        result = self.manager.dispatch("LOCAL_ALERT")
        self.assertTrue(result.succeeded)
        self.assertEqual(result.via, "local_alert")
        self.assertEqual(self.controller.sent, [])

    def test_emergency_response_dispatches_configured_set(self) -> None:
        expected = list(load_config().get("actions.on_emergency"))
        results = self.manager.trigger_emergency_response()
        self.assertEqual([r.action for r in results], expected)
        self.assertTrue(all(r.succeeded for r in results))

    def test_every_result_is_flagged_simulated(self) -> None:
        for result in self.manager.trigger_emergency_response():
            self.assertTrue(result.simulated)

    def test_unknown_action_fails_without_raising(self) -> None:
        result = self.manager.dispatch("LAUNCH_ROCKET")
        self.assertFalse(result.succeeded)
        self.assertIn("No mapping", result.detail)

    def test_empty_action_name_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.dispatch("   ")

    def test_direct_device_command(self) -> None:
        result = self.manager.dispatch_device_command("tv", "VOLUME_UP")
        self.assertTrue(result.succeeded)
        self.assertEqual(self.controller.sent[-1].command, "VOLUME_UP")

    def test_direct_command_failure_is_reported(self) -> None:
        result = self.manager.dispatch_device_command("fan", "VOLUME_UP")
        self.assertFalse(result.succeeded)

    def test_history_records_every_dispatch(self) -> None:
        self.manager.dispatch("LIGHTS_ON")
        self.manager.dispatch("LOCAL_ALERT")
        self.assertEqual(len(self.manager.history), 2)

    def test_clear_resets_history(self) -> None:
        self.manager.trigger_emergency_response()
        self.manager.clear()
        self.assertEqual(self.manager.history, [])

    def test_device_backend_without_binding_fails_loudly(self) -> None:
        config = load_config().with_overrides(**{"actions.ir_backend": "device"})
        manager = ActionManager(config, local_alert=LocalAlert(verbose=False), verbose=False)
        result = manager.dispatch("LIGHTS_ON")
        self.assertFalse(result.succeeded)
        self.assertIn("docs/ir_integration.md", result.detail)

    def test_unknown_backend_rejected(self) -> None:
        config = load_config().with_overrides(**{"actions.ir_backend": "telepathy"})
        with self.assertRaises(ValueError):
            ActionManager(config, verbose=False)


if __name__ == "__main__":
    unittest.main()
