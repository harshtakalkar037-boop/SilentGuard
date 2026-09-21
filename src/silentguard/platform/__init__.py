"""Platform integration layer.

Nothing here executes on a handset from this repository. These modules define
the contracts a device-side implementation must satisfy, so the boundary
between "runs today" and "runs on the phone" is explicit rather than implied.
"""

from .contracts import (
    CameraSource,
    DeviceCapabilities,
    DeviceIRTransmitter,
    NotificationChannel,
)

__all__ = [
    "CameraSource",
    "DeviceCapabilities",
    "DeviceIRTransmitter",
    "NotificationChannel",
]
