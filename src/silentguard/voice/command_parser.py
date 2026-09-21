"""A small, deterministic command parser for on-demand control.

Deliberately rule-based. A full speech-to-text stack (Whisper and friends)
would add weight and a model download without changing what this layer proves:
that an utterance becomes a validated appliance command routed through the
same action path the autonomous mode uses.

Speech-to-text is an adapter concern. Any recogniser that returns a string can
feed this parser - see ``docs/technical_architecture.md``.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, Optional, Tuple

from ..appliances.command_registry import CommandRegistry
from ..config import Config, load_config
from .intent import Intent, IntentType


class ParseError(ValueError):
    """Raised when the input is not usable text."""


#: Device synonyms -> canonical device key.
DEVICE_SYNONYMS: Dict[str, str] = {
    "light": "lights",
    "lights": "lights",
    "lamp": "lights",
    "lamps": "lights",
    "bulb": "lights",
    "tv": "tv",
    "television": "tv",
    "telly": "tv",
    "screen": "tv",
    "fan": "fan",
    "ceiling fan": "fan",
}

#: Command synonyms -> canonical command key.
COMMAND_SYNONYMS: Dict[str, str] = {
    "on": "ON",
    "turn on": "ON",
    "switch on": "ON",
    "start": "ON",
    "off": "OFF",
    "turn off": "OFF",
    "switch off": "OFF",
    "stop": "OFF",
    "shut": "OFF",
    "volume up": "VOLUME_UP",
    "louder": "VOLUME_UP",
    "turn it up": "VOLUME_UP",
    "volume down": "VOLUME_DOWN",
    "quieter": "VOLUME_DOWN",
    "turn it down": "VOLUME_DOWN",
    "sos": "SOS",
}

CANCEL_PHRASES: Tuple[str, ...] = (
    "i am fine",
    "i'm fine",
    "im fine",
    "cancel",
    "stop alert",
    "false alarm",
    "no emergency",
    "all good",
)

EMERGENCY_PHRASES: Tuple[str, ...] = (
    "help me",
    "help",
    "emergency",
    "call for help",
    "sos now",
)


class CommandParser:
    """Turns an utterance into an :class:`Intent`, validated against the registry."""

    def __init__(
        self,
        registry: Optional[CommandRegistry] = None,
        config: Optional[Config] = None,
    ) -> None:
        self.config = config or load_config()
        self.registry = registry or CommandRegistry()
        self.min_confidence = float(self.config.get("voice.min_intent_confidence", 0.6))

    def parse(self, utterance: str) -> Intent:
        """Parse ``utterance`` into an intent.

        Raises:
            ParseError: if ``utterance`` is not a non-empty string.
        """
        if not isinstance(utterance, str):
            raise ParseError("utterance must be a string")
        text = self._normalise(utterance)
        if not text:
            raise ParseError("utterance must not be empty")

        # Safety phrases take priority over appliance control: during a
        # confirmation window, "cancel" must never be read as "fan off".
        cancel = self._match_phrase(text, CANCEL_PHRASES)
        if cancel:
            return Intent(
                type=IntentType.CANCEL_EMERGENCY,
                confidence=0.95,
                utterance=utterance,
                explanation=f"matched cancellation phrase {cancel!r}",
            )

        emergency = self._match_phrase(text, EMERGENCY_PHRASES)
        if emergency:
            return Intent(
                type=IntentType.RAISE_EMERGENCY,
                confidence=0.9,
                utterance=utterance,
                explanation=f"matched emergency phrase {emergency!r}",
            )

        device = self._find(text, DEVICE_SYNONYMS)
        command = self._find(text, COMMAND_SYNONYMS)

        if device is None or command is None:
            missing = "device" if device is None else "command"
            return Intent(
                type=IntentType.UNKNOWN,
                device=device,
                command=command,
                confidence=0.0,
                utterance=utterance,
                explanation=f"could not identify a {missing} in the utterance",
            )

        if not self.registry.supports(device, command):
            return Intent(
                type=IntentType.UNKNOWN,
                device=device,
                command=command,
                confidence=0.3,
                utterance=utterance,
                explanation=(
                    f"device {device!r} does not support command {command!r}"
                ),
            )

        confidence = self._score(text, device, command)
        if confidence < self.min_confidence:
            return Intent(
                type=IntentType.UNKNOWN,
                device=device,
                command=command,
                confidence=confidence,
                utterance=utterance,
                explanation=(
                    f"confidence {confidence:.2f} below "
                    f"minimum {self.min_confidence:.2f}"
                ),
            )

        return Intent(
            type=IntentType.APPLIANCE_CONTROL,
            device=device,
            command=command,
            confidence=confidence,
            utterance=utterance,
            explanation=f"resolved to {device}.{command}",
        )

    def action_name(self, intent: Intent) -> Optional[str]:
        """Map an actionable intent to a configured action name, if one exists.

        Returns the action key from ``appliances.action_map`` whose device and
        command match, so on-demand mode reuses the same dispatch path as the
        autonomous mode.
        """
        if not intent.is_actionable:
            return None
        action_map = self.config.get("appliances.action_map", {}) or {}
        for name, mapping in action_map.items():
            if (
                str(mapping.get("device", "")).lower() == intent.device
                and str(mapping.get("command", "")).upper() == intent.command
            ):
                return str(name).upper()
        return None

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _normalise(text: str) -> str:
        lowered = text.lower().strip()
        lowered = re.sub(r"[^a-z0-9' ]+", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    @staticmethod
    def _match_phrase(text: str, phrases: Iterable[str]) -> Optional[str]:
        for phrase in phrases:
            if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text):
                return phrase
        return None

    @staticmethod
    def _find(text: str, synonyms: Dict[str, str]) -> Optional[str]:
        """Return the canonical value for the longest matching synonym."""
        best: Optional[str] = None
        best_len = 0
        for phrase, canonical in synonyms.items():
            if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) and len(phrase) > best_len:
                best, best_len = canonical, len(phrase)
        return best

    @staticmethod
    def _score(text: str, device: str, command: str) -> float:
        """Confidence heuristic: explicit verbs and short commands score higher."""
        score = 0.7
        if re.search(r"(?<!\w)(turn|switch|please)(?!\w)", text):
            score += 0.15
        if len(text.split()) <= 5:
            score += 0.1
        if command in ("VOLUME_UP", "VOLUME_DOWN"):
            score += 0.05
        return round(min(score, 1.0), 2)
