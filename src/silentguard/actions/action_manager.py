"""Dispatches named actions to the IR and alert layers.

The decision engine never talks to hardware. It emits a state; the action
manager translates the configured action names (``LIGHTS_ON``, ``TV_SOS``,
``LOCAL_ALERT``) into concrete calls, and reports exactly what happened.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from ..appliances.command_registry import ApplianceError, CommandRegistry
from ..config import Config, load_config
from .ir_controller import IRController, IRTransmissionError, UnavailableIRController
from .local_alert import LocalAlert
from .mock_ir import MockIRController

logger = logging.getLogger(__name__)

#: Action names handled directly by the manager rather than via an appliance.
LOCAL_ACTIONS = ("LOCAL_ALERT",)


@dataclass(frozen=True)
class ActionResult:
    """Outcome of dispatching one action.

    Attributes:
        action: The requested action name.
        succeeded: Whether it completed.
        detail: Human-readable description of what happened.
        via: Which backend handled it (``"mock"``, ``"local_alert"``, ...).
        simulated: True when no real hardware was involved.
    """

    action: str
    succeeded: bool
    detail: str
    via: str
    simulated: bool = True


class ActionManager:
    """Routes action names to IR commands and local alerts."""

    def __init__(
        self,
        config: Optional[Config] = None,
        ir_controller: Optional[IRController] = None,
        registry: Optional[CommandRegistry] = None,
        local_alert: Optional[LocalAlert] = None,
        verbose: bool = True,
    ) -> None:
        self.config = config or load_config()
        self.verbose = verbose
        self.registry = registry or CommandRegistry()
        self.local_alert = local_alert or LocalAlert(verbose=verbose)
        self.ir = ir_controller or self._build_ir_controller()
        self._action_map: Dict[str, Dict[str, str]] = {
            str(k).upper(): dict(v)
            for k, v in (self.config.get("appliances.action_map", {}) or {}).items()
        }
        self._history: List[ActionResult] = []

    def _build_ir_controller(self) -> IRController:
        backend = str(self.config.get("actions.ir_backend", "mock")).lower()
        if backend == "mock":
            return MockIRController(verbose=self.verbose)
        if backend == "device":
            # Resolved at runtime by the platform layer. Absent a binding, this
            # refuses to transmit rather than faking success.
            return UnavailableIRController(
                reason="actions.ir_backend is 'device' but no platform IR "
                "implementation is bound in this environment"
            )
        raise ValueError(
            f"Unknown actions.ir_backend {backend!r}; expected 'mock' or 'device'"
        )

    @property
    def emergency_actions(self) -> Sequence[str]:
        """The action names configured for a confirmed emergency."""
        return tuple(self.config.get("actions.on_emergency", []) or [])

    @property
    def history(self) -> List[ActionResult]:
        """Every action dispatched this session, in order."""
        return list(self._history)

    def dispatch(self, action: str) -> ActionResult:
        """Dispatch a single named action."""
        name = str(action).strip().upper()
        if not name:
            raise ValueError("action name must not be empty")

        if name in LOCAL_ACTIONS:
            record = self.local_alert.raise_alert(
                "Possible fall detected. Emergency response triggered.",
                level="emergency",
            )
            result = ActionResult(
                action=name,
                succeeded=True,
                detail=record.message,
                via="local_alert",
                simulated=True,
            )
            self._history.append(result)
            return result

        mapping = self._action_map.get(name)
        if mapping is None:
            result = ActionResult(
                action=name,
                succeeded=False,
                detail=(
                    f"No mapping for action {name!r} in appliances.action_map. "
                    "Add it to config.yaml."
                ),
                via="none",
            )
            self._history.append(result)
            logger.error(result.detail)
            return result

        try:
            command = self.registry.resolve(mapping["device"], mapping["command"])
        except (ApplianceError, KeyError) as exc:
            result = ActionResult(
                action=name, succeeded=False, detail=str(exc), via=self.ir.name
            )
            self._history.append(result)
            logger.error("Action %s failed: %s", name, exc)
            return result

        try:
            ok = self.ir.send(command)
            detail = (
                f"{command.device}.{command.command} "
                f"(code_id={command.code_id}, x{command.repeat})"
            )
        except IRTransmissionError as exc:
            ok, detail = False, str(exc)
            logger.error("Action %s failed: %s", name, exc)

        result = ActionResult(
            action=name,
            succeeded=ok,
            detail=detail,
            via=self.ir.name,
            simulated=not self.ir.is_real_hardware,
        )
        self._history.append(result)
        return result

    def dispatch_device_command(self, device: str, command: str) -> ActionResult:
        """Dispatch a device/command pair that has no named action mapping.

        On-demand control can address any command an appliance profile
        declares (``tv.VOLUME_UP``, for instance), not only the named actions
        used by the autonomous mode. Both paths end at the same IR backend.
        """
        try:
            ir_command = self.registry.resolve(device, command)
        except ApplianceError as exc:
            result = ActionResult(
                action=f"{device}.{command}".upper(),
                succeeded=False,
                detail=str(exc),
                via=self.ir.name,
            )
            self._history.append(result)
            logger.error("Command %s.%s failed: %s", device, command, exc)
            return result

        try:
            ok = self.ir.send(ir_command)
            detail = (
                f"{ir_command.device}.{ir_command.command} "
                f"(code_id={ir_command.code_id}, x{ir_command.repeat})"
            )
        except IRTransmissionError as exc:
            ok, detail = False, str(exc)
            logger.error("Command %s.%s failed: %s", device, command, exc)

        result = ActionResult(
            action=f"{ir_command.device}.{ir_command.command}".upper(),
            succeeded=ok,
            detail=detail,
            via=self.ir.name,
            simulated=not self.ir.is_real_hardware,
        )
        self._history.append(result)
        return result

    def dispatch_many(self, actions: Sequence[str]) -> List[ActionResult]:
        """Dispatch several actions in order, continuing past failures."""
        return [self.dispatch(action) for action in actions]

    def trigger_emergency_response(self) -> List[ActionResult]:
        """Dispatch the configured emergency action set."""
        actions = self.emergency_actions
        if not actions:
            logger.warning("actions.on_emergency is empty; nothing to dispatch")
            return []
        return self.dispatch_many(actions)

    def clear(self) -> None:
        """Reset the dispatch history and any backend records."""
        self._history.clear()
        self.local_alert.clear()
        if isinstance(self.ir, MockIRController):
            self.ir.clear()
