"""Action layer: turns confirmed decisions into physical-world effects."""

from .ir_controller import IRController, IRTransmissionError, UnavailableIRController
from .mock_ir import MockIRController
from .local_alert import AlertRecord, LocalAlert
from .action_manager import ActionManager, ActionResult

__all__ = [
    "ActionManager",
    "ActionResult",
    "AlertRecord",
    "IRController",
    "IRTransmissionError",
    "LocalAlert",
    "MockIRController",
    "UnavailableIRController",
]
