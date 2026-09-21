"""Integration contracts for a device-side implementation.

These are Protocols, not implementations. A platform binding (Android/Kotlin
with a thin Python or IPC bridge, or a native port of this pipeline) satisfies
them. Deliberately absent: any invented vendor API name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol, Tuple


@dataclass(frozen=True)
class DeviceCapabilities:
    """What a given handset can actually do.

    A runtime should query this before enabling a mode, so an unsupported
    device degrades honestly instead of failing at the moment of emergency.
    """

    has_ir_blaster: bool = False
    has_npu_delegate: bool = False
    has_camera: bool = False
    has_microphone: bool = False
    model_name: str = "unknown"

    def supports_autonomous_mode(self) -> bool:
        """Autonomous guardian mode needs a camera at minimum."""
        return self.has_camera

    def supports_physical_action(self) -> bool:
        """Physical appliance action needs IR hardware."""
        return self.has_ir_blaster


class CameraSource(Protocol):
    """Frame source provided by the platform."""

    def frames(self) -> Iterator[Tuple[float, object]]:
        """Yield ``(timestamp_seconds, frame)`` pairs."""
        ...

    def close(self) -> None:
        """Release the camera."""
        ...


class DeviceIRTransmitter(Protocol):
    """Device-side IR transmission.

    The platform binding maps a ``code_id`` to a real carrier frequency and
    pattern, captured during household setup.
    """

    def transmit(self, code_id: str, protocol: str, repeat: int = 1) -> bool:
        """Transmit the code identified by ``code_id``."""
        ...

    def is_available(self) -> bool:
        """True when IR hardware is present and permitted."""
        ...


class NotificationChannel(Protocol):
    """High-priority on-device alerting."""

    def alert(self, title: str, body: str, full_screen: bool = True) -> bool:
        """Raise an alert that is visible without unlocking the device."""
        ...
