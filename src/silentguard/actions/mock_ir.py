"""A development IR backend that records commands instead of transmitting them.

Everything it emits is labelled ``[MOCK IR]`` so nobody reading a demo
transcript can mistake it for hardware evidence.
"""

from __future__ import annotations

import logging
from typing import List

from ..appliances.command_registry import IRCommand
from .ir_controller import IRController

logger = logging.getLogger(__name__)


class MockIRController(IRController):
    """Records IR commands in memory and logs them."""

    is_real_hardware = False

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self._sent: List[IRCommand] = []

    @property
    def name(self) -> str:
        return "mock"

    def available(self) -> bool:
        """Always available; it has no hardware dependency."""
        return True

    def send(self, command: IRCommand) -> bool:
        """Record ``command`` and log a clearly-marked mock transmission."""
        if not isinstance(command, IRCommand):
            raise TypeError("command must be an IRCommand")
        self._sent.append(command)
        message = (
            f"[MOCK IR] {command.device}.{command.command} "
            f"-> code_id={command.code_id} protocol={command.protocol} "
            f"repeat={command.repeat} (simulated, no hardware)"
        )
        logger.info(message)
        if self.verbose:
            print(message)
        return True

    @property
    def sent(self) -> List[IRCommand]:
        """Commands recorded so far, in order."""
        return list(self._sent)

    def clear(self) -> None:
        """Forget all recorded commands."""
        self._sent.clear()
