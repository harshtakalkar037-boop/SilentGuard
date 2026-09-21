"""The IR control contract.

Every IR backend implements :class:`IRController`. The prototype ships one
working backend (:class:`~silentguard.actions.mock_ir.MockIRController`) and
one honest placeholder (:class:`UnavailableIRController`).

Why a placeholder rather than an implementation: transmitting IR requires a
device-side API on a handset with IR hardware. This repository does not invent
an API name for that. The device-specific implementation belongs in
``platform/iqoo/`` and is described in ``docs/ir_integration.md``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..appliances.command_registry import IRCommand


class IRTransmissionError(RuntimeError):
    """Raised when an IR command cannot be transmitted."""


class IRController(ABC):
    """Abstract IR transmitter."""

    #: Set False by backends that do not reach real hardware.
    is_real_hardware: bool = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Short backend name, used in logs and demo output."""

    @abstractmethod
    def available(self) -> bool:
        """True when this backend can currently transmit."""

    @abstractmethod
    def send(self, command: IRCommand) -> bool:
        """Transmit ``command``.

        Returns:
            True when the command was transmitted (or simulated) successfully.

        Raises:
            IRTransmissionError: when transmission fails.
        """

    def send_many(self, commands: List[IRCommand]) -> List[bool]:
        """Transmit several commands in order, stopping at the first failure."""
        results: List[bool] = []
        for command in commands:
            results.append(self.send(command))
        return results


class UnavailableIRController(IRController):
    """Stands in for real IR hardware that is not reachable from this process.

    Selecting ``actions.ir_backend: device`` without a platform implementation
    yields this controller. It fails loudly rather than pretending to transmit,
    which keeps demo output honest.
    """

    is_real_hardware = False

    def __init__(self, reason: str = "no platform IR implementation is bound") -> None:
        self.reason = reason

    @property
    def name(self) -> str:
        return "unavailable"

    def available(self) -> bool:
        return False

    def send(self, command: IRCommand) -> bool:
        raise IRTransmissionError(
            f"Cannot transmit {command.device}.{command.command}: {self.reason}. "
            "Use ir_backend 'mock' for development, or bind a device "
            "implementation - see docs/ir_integration.md."
        )
