"""The SilentGuard decision engine.

Rule-based, transparent, and fully testable. It consumes
:class:`~silentguard.perception.fall_detector.FallSignals` (plus an optional
audio distress score) and produces a :class:`DecisionResult` describing the
state and *why* the system is in it.

The engine holds no I/O and no timers of its own: the caller supplies the
timestamp. That keeps it deterministic under test and independent of frame
rate.
"""

from __future__ import annotations

from typing import Optional

from ..config import Config
from ..perception.fall_detector import FallSignals
from .states import DecisionResult, SystemState
from .thresholds import DecisionThresholds


class DecisionEngine:
    """An explainable state machine guarding against false emergencies."""

    def __init__(
        self,
        thresholds: Optional[DecisionThresholds] = None,
        config: Optional[Config] = None,
    ) -> None:
        self.thresholds = thresholds or DecisionThresholds.from_config(config)
        self._state = SystemState.NORMAL
        self._confirm_started_at: Optional[float] = None
        self._emergency_fired = False

    @property
    def state(self) -> SystemState:
        """The current state."""
        return self._state

    @property
    def confirm_started_at(self) -> Optional[float]:
        """Timestamp the confirmation window opened, if it is open."""
        return self._confirm_started_at

    def reset(self) -> None:
        """Return the engine to ``NORMAL`` and clear the confirmation window."""
        self._state = SystemState.NORMAL
        self._confirm_started_at = None
        self._emergency_fired = False

    def update(
        self,
        signals: FallSignals,
        *,
        cancel_requested: bool = False,
        audio_distress: float = 0.0,
    ) -> DecisionResult:
        """Advance the state machine by one observation.

        Args:
            signals: Perception output for this frame.
            cancel_requested: True when the user cancelled during the window.
            audio_distress: Optional corroborating audio score in [0, 1].
                Only consulted when ``decision.use_audio_signal`` is enabled.

        Returns:
            A :class:`DecisionResult` for this update.
        """
        if not isinstance(signals, FallSignals):
            raise TypeError("signals must be a FallSignals instance")
        if not 0.0 <= audio_distress <= 1.0:
            raise ValueError("audio_distress must be within [0, 1]")

        previous = self._state
        now = signals.timestamp
        confidence = self._apply_audio(signals.confidence, audio_distress)

        # A cancel is honoured whenever a window is open, and only then.
        if cancel_requested and self._state in (
            SystemState.FALL_SUSPECTED,
            SystemState.CONFIRMING,
        ):
            self._state = SystemState.NORMAL
            self._confirm_started_at = None
            return self._result(
                previous,
                "user cancelled during the confirmation window",
                confidence,
                signals,
            )

        if self._state is SystemState.EMERGENCY:
            # Latched. Only an explicit reset() leaves this state, so a
            # confirmed emergency cannot be silently undone by a noisy frame.
            return self._result(
                previous, "emergency already confirmed (latched)", confidence, signals
            )

        if self._state is SystemState.CONFIRMING:
            # Explicit None check: a window that opened at t=0.0 is still an
            # open window, and `or now` would silently restart it.
            started = self._confirm_started_at
            elapsed = now - (started if started is not None else now)
            remaining = self.thresholds.confirmation_seconds - elapsed
            if remaining <= 0:
                self._state = SystemState.EMERGENCY
                fired = not self._emergency_fired
                self._emergency_fired = True
                return self._result(
                    previous,
                    "confirmation window elapsed with no cancellation",
                    confidence,
                    signals,
                    triggers_action=fired,
                )
            return self._result(
                previous,
                f"waiting for cancellation ({remaining:.1f}s remaining)",
                confidence,
                signals,
                seconds_remaining=round(remaining, 2),
            )

        # NORMAL / FALL_SUSPECTED.
        if confidence >= self.thresholds.confirm_threshold:
            self._state = SystemState.CONFIRMING
            self._confirm_started_at = now
            return self._result(
                previous,
                f"fall confidence {confidence:.2f} >= "
                f"{self.thresholds.confirm_threshold:.2f}; opening cancel window",
                confidence,
                signals,
                seconds_remaining=self.thresholds.confirmation_seconds,
            )

        if confidence >= self.thresholds.suspect_threshold:
            self._state = SystemState.FALL_SUSPECTED
            return self._result(
                previous,
                f"fall confidence {confidence:.2f} above suspect threshold; monitoring",
                confidence,
                signals,
            )

        self._state = SystemState.NORMAL
        return self._result(previous, "no distress indicators", confidence, signals)

    # -- internals ---------------------------------------------------------

    def _apply_audio(self, confidence: float, audio_distress: float) -> float:
        """Let a strong audio cue corroborate, never originate, a fall."""
        if not self.thresholds.use_audio_signal:
            return confidence
        if audio_distress < self.thresholds.audio_distress_threshold:
            return confidence
        if confidence < self.thresholds.suspect_threshold * 0.5:
            # Audio alone is not evidence of a fall - see docs/decision_engine.md.
            return confidence
        return min(confidence + 0.10, 1.0)

    def _result(
        self,
        previous: SystemState,
        reason: str,
        confidence: float,
        signals: FallSignals,
        *,
        seconds_remaining: Optional[float] = None,
        triggers_action: bool = False,
    ) -> DecisionResult:
        return DecisionResult(
            state=self._state,
            previous_state=previous,
            changed=self._state is not previous,
            reason=reason,
            confidence=round(confidence, 4),
            seconds_remaining=seconds_remaining,
            triggers_action=triggers_action,
            evidence=signals.reasons,
        )
