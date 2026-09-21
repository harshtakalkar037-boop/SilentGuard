"""Loads appliance profiles and resolves device/command pairs to IR codes.

Profiles are plain JSON so a household can be configured without touching
code. A profile carries a protocol name and one entry per supported command.

The stored ``code_id`` values are **identifiers, not captured waveforms**. A
real deployment captures the household's own codes during setup; see
``docs/ir_integration.md``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

DEFAULT_PROFILE_DIR = Path(__file__).resolve().parent / "profiles"


class ApplianceError(LookupError):
    """Raised when a device or command is not present in the registry."""


@dataclass(frozen=True)
class IRCommand:
    """A resolved IR command.

    Attributes:
        device: Device key, e.g. ``"lights"``.
        command: Command key, e.g. ``"ON"``.
        code_id: Identifier the platform IR layer maps to a real code.
        protocol: IR protocol declared by the profile.
        description: Human-readable description.
        repeat: How many times the code should be transmitted.
    """

    device: str
    command: str
    code_id: str
    protocol: str
    description: str = ""
    repeat: int = 1


@dataclass(frozen=True)
class ApplianceProfile:
    """One appliance and the commands it accepts."""

    device: str
    display_name: str
    protocol: str
    commands: Dict[str, Dict[str, object]]

    @classmethod
    def from_file(cls, path: Path) -> "ApplianceProfile":
        """Load and validate a profile from a JSON file."""
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ApplianceError(f"Invalid JSON in appliance profile {path}: {exc}") from exc

        for key in ("device", "commands"):
            if key not in raw:
                raise ApplianceError(f"Profile {path.name} is missing required key {key!r}")
        if not isinstance(raw["commands"], dict) or not raw["commands"]:
            raise ApplianceError(f"Profile {path.name} declares no commands")

        return cls(
            device=str(raw["device"]),
            display_name=str(raw.get("display_name", raw["device"])),
            protocol=str(raw.get("protocol", "UNKNOWN")),
            commands=dict(raw["commands"]),
        )


class CommandRegistry:
    """In-memory index of appliance profiles."""

    def __init__(self, profile_dir: Optional[Path | str] = None) -> None:
        self.profile_dir = Path(profile_dir) if profile_dir else DEFAULT_PROFILE_DIR
        self._profiles: Dict[str, ApplianceProfile] = {}
        self.reload()

    def reload(self) -> None:
        """Re-read every ``*.json`` profile from the profile directory."""
        if not self.profile_dir.is_dir():
            raise ApplianceError(f"Appliance profile directory not found: {self.profile_dir}")
        profiles: Dict[str, ApplianceProfile] = {}
        for path in sorted(self.profile_dir.glob("*.json")):
            profile = ApplianceProfile.from_file(path)
            profiles[profile.device] = profile
        if not profiles:
            raise ApplianceError(f"No appliance profiles found in {self.profile_dir}")
        self._profiles = profiles

    @property
    def devices(self) -> Iterable[str]:
        """Device keys known to the registry."""
        return tuple(self._profiles)

    def profile(self, device: str) -> ApplianceProfile:
        """Return the profile for ``device``."""
        key = device.strip().lower()
        if key not in self._profiles:
            raise ApplianceError(
                f"Unknown device {device!r}. Known devices: {', '.join(self.devices)}"
            )
        return self._profiles[key]

    def supports(self, device: str, command: str) -> bool:
        """True when ``device`` accepts ``command``."""
        try:
            return command.strip().upper() in self.profile(device).commands
        except ApplianceError:
            return False

    def resolve(self, device: str, command: str) -> IRCommand:
        """Resolve a device/command pair into an :class:`IRCommand`."""
        profile = self.profile(device)
        key = command.strip().upper()
        if key not in profile.commands:
            raise ApplianceError(
                f"Device {profile.device!r} does not support command {command!r}. "
                f"Supported: {', '.join(sorted(profile.commands))}"
            )
        entry = profile.commands[key]
        if not isinstance(entry, dict) or "code_id" not in entry:
            raise ApplianceError(
                f"Command {key!r} on {profile.device!r} has no 'code_id'"
            )
        return IRCommand(
            device=profile.device,
            command=key,
            code_id=str(entry["code_id"]),
            protocol=profile.protocol,
            description=str(entry.get("description", "")),
            repeat=int(entry.get("repeat", 1)),
        )
