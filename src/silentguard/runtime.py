"""The guardian runtime: one object that wires the whole pipeline together.

PERCEIVE -> UNDERSTAND -> DECIDE -> ACT

``GuardianRuntime`` owns a pose source, the fall detector, the decision engine
and the action manager, and steps them in lockstep. Demos and tests both drive
it, so what a judge runs is the same code path the tests cover.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterator, List, Optional

from .actions.action_manager import ActionManager, ActionResult
from .audio.detector_interface import AudioDistressDetector
from .config import Config, load_config
from .decision.decision_engine import DecisionEngine
from .decision.states import DecisionResult, SystemState
from .perception.fall_detector import FallDetector, FallSignals
from .perception.pose_detector import PoseDetector, PoseFrame, build_pose_detector

#: Signature of a cancel hook: given the current timestamp, return True to cancel.
CancelHook = Callable[[float], bool]


@dataclass
class TickResult:
    """The full outcome of one pipeline step.

    Attributes:
        frame: The pose frame that was processed.
        signals: Perception output.
        decision: Decision-engine output.
        actions: Actions dispatched on this tick (empty unless an emergency
            was newly confirmed).
    """

    frame: PoseFrame
    signals: FallSignals
    decision: DecisionResult
    actions: List[ActionResult] = field(default_factory=list)


class GuardianRuntime:
    """Runs autonomous guardian mode end to end."""

    def __init__(
        self,
        config: Optional[Config] = None,
        pose_source: Optional[PoseDetector] = None,
        action_manager: Optional[ActionManager] = None,
        audio_detector: Optional[AudioDistressDetector] = None,
        cancel_hook: Optional[CancelHook] = None,
        verbose: bool = True,
    ) -> None:
        self.config = config or load_config()
        self.verbose = verbose
        self.pose_source = pose_source or build_pose_detector(
            source=str(self.config.get("perception.source", "synthetic"))
        )
        self.detector = FallDetector(self.config)
        self.engine = DecisionEngine(config=self.config)
        self.actions = action_manager or ActionManager(self.config, verbose=verbose)
        self.audio_detector = audio_detector
        self.cancel_hook = cancel_hook
        self._ticks: List[TickResult] = []

    @property
    def state(self) -> SystemState:
        """Current decision state."""
        return self.engine.state

    @property
    def ticks(self) -> List[TickResult]:
        """Every tick processed this run."""
        return list(self._ticks)

    def reset(self) -> None:
        """Clear detector, engine and action history for a fresh run."""
        self.detector.reset()
        self.engine.reset()
        self.actions.clear()
        self._ticks.clear()

    def step(self, frame: PoseFrame) -> TickResult:
        """Process a single pose frame through the whole pipeline."""
        signals = self.detector.update(frame)

        audio_score = 0.0
        if self.audio_detector is not None:
            audio_score = self.audio_detector.observe(frame.timestamp).distress_score

        cancel = False
        if self.cancel_hook is not None and self.engine.state in (
            SystemState.FALL_SUSPECTED,
            SystemState.CONFIRMING,
        ):
            cancel = bool(self.cancel_hook(frame.timestamp))

        decision = self.engine.update(
            signals, cancel_requested=cancel, audio_distress=audio_score
        )

        dispatched: List[ActionResult] = []
        if decision.triggers_action:
            dispatched = self.actions.trigger_emergency_response()

        tick = TickResult(
            frame=frame, signals=signals, decision=decision, actions=dispatched
        )
        self._ticks.append(tick)
        return tick

    def run(self, max_frames: Optional[int] = None) -> Iterator[TickResult]:
        """Drive the pose source to exhaustion, yielding each tick."""
        try:
            for index, frame in enumerate(self.pose_source.frames()):
                if max_frames is not None and index >= max_frames:
                    break
                yield self.step(frame)
        finally:
            self.pose_source.close()

    def summary(self) -> dict:
        """A compact, printable summary of the run."""
        peak = max((t.signals.confidence for t in self._ticks), default=0.0)
        transitions = [
            f"{t.decision.previous_state} -> {t.decision.state}"
            for t in self._ticks
            if t.decision.changed
        ]
        dispatched = [a for t in self._ticks for a in t.actions]
        return {
            "frames": len(self._ticks),
            "final_state": str(self.engine.state),
            "peak_confidence": round(peak, 4),
            "transitions": transitions,
            "actions": [a.action for a in dispatched],
            "all_actions_simulated": all(a.simulated for a in dispatched) if dispatched else True,
        }
