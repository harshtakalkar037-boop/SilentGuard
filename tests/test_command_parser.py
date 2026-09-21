"""Tests for on-demand voice/text command parsing."""

from __future__ import annotations

import unittest

import conftest  # noqa: F401

from silentguard.voice import CommandParser, ParseError
from silentguard.voice.intent import Intent, IntentType


class TestApplianceCommands(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = CommandParser()

    def test_turn_on_the_lights(self) -> None:
        intent = self.parser.parse("turn on the lights")
        self.assertIs(intent.type, IntentType.APPLIANCE_CONTROL)
        self.assertEqual(intent.device, "lights")
        self.assertEqual(intent.command, "ON")
        self.assertTrue(intent.is_actionable)

    def test_fan_off(self) -> None:
        intent = self.parser.parse("fan off")
        self.assertEqual((intent.device, intent.command), ("fan", "OFF"))

    def test_volume_command(self) -> None:
        intent = self.parser.parse("tv volume up")
        self.assertEqual((intent.device, intent.command), ("tv", "VOLUME_UP"))

    def test_synonyms_resolve_to_canonical_device(self) -> None:
        for phrase in ("switch on the lamp", "turn on the bulb"):
            self.assertEqual(self.parser.parse(phrase).device, "lights")
        for phrase in ("turn off the television", "telly off"):
            self.assertEqual(self.parser.parse(phrase).device, "tv")

    def test_case_and_punctuation_are_ignored(self) -> None:
        intent = self.parser.parse("  TURN ON, the LIGHTS!! ")
        self.assertIs(intent.type, IntentType.APPLIANCE_CONTROL)
        self.assertEqual(intent.device, "lights")

    def test_longest_synonym_wins(self) -> None:
        """'turn it down' must not be read as the 'down' fragment alone."""
        intent = self.parser.parse("tv turn it down")
        self.assertEqual(intent.command, "VOLUME_DOWN")

    def test_unsupported_pairing_is_rejected(self) -> None:
        """A fan has no volume, and the registry is what decides that."""
        intent = self.parser.parse("fan volume up")
        self.assertIs(intent.type, IntentType.UNKNOWN)
        self.assertFalse(intent.is_actionable)

    def test_unrelated_speech_is_unknown(self) -> None:
        intent = self.parser.parse("what is the weather tomorrow")
        self.assertIs(intent.type, IntentType.UNKNOWN)
        self.assertEqual(intent.confidence, 0.0)


class TestSafetyPhrases(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = CommandParser()

    def test_cancellation_phrases(self) -> None:
        for phrase in ("I am fine", "i'm fine", "cancel", "false alarm", "all good"):
            self.assertIs(
                self.parser.parse(phrase).type,
                IntentType.CANCEL_EMERGENCY,
                msg=phrase,
            )

    def test_emergency_phrases(self) -> None:
        for phrase in ("help me", "emergency", "call for help"):
            self.assertIs(
                self.parser.parse(phrase).type,
                IntentType.RAISE_EMERGENCY,
                msg=phrase,
            )

    def test_cancellation_outranks_appliance_control(self) -> None:
        """During a cancel window, safety wording must win."""
        intent = self.parser.parse("cancel, turn off the fan")
        self.assertIs(intent.type, IntentType.CANCEL_EMERGENCY)


class TestInputValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = CommandParser()

    def test_empty_string_rejected(self) -> None:
        with self.assertRaises(ParseError):
            self.parser.parse("   ")

    def test_non_string_rejected(self) -> None:
        with self.assertRaises(ParseError):
            self.parser.parse(None)  # type: ignore[arg-type]

    def test_symbols_only_rejected(self) -> None:
        with self.assertRaises(ParseError):
            self.parser.parse("!!!???")


class TestActionMapping(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = CommandParser()

    def test_named_action_is_resolved(self) -> None:
        intent = self.parser.parse("turn on the lights")
        self.assertEqual(self.parser.action_name(intent), "LIGHTS_ON")

    def test_unmapped_command_has_no_named_action(self) -> None:
        intent = self.parser.parse("tv volume up")
        self.assertIsNone(self.parser.action_name(intent))

    def test_non_actionable_intent_has_no_named_action(self) -> None:
        self.assertIsNone(self.parser.action_name(Intent(type=IntentType.UNKNOWN)))


if __name__ == "__main__":
    unittest.main()
