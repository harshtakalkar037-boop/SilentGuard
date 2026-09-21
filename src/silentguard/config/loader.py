"""Loads and validates the central SilentGuard configuration.

All thresholds live in ``config.yaml``. Modules receive a :class:`Config`
instance rather than reading globals, which keeps them unit-testable.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

_REQUIRED_SECTIONS = (
    "perception",
    "fall_detection",
    "decision",
    "actions",
    "appliances",
    "voice",
)


class ConfigError(ValueError):
    """Raised when the configuration file is missing or structurally invalid."""


class Config:
    """Dictionary-backed configuration with dotted-path lookup.

    Example:
        >>> cfg = load_config()
        >>> cfg.get("decision.confirmation_seconds")
        12.0
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ConfigError("Configuration root must be a mapping.")
        self._data: Dict[str, Any] = copy.deepcopy(data)

    @property
    def data(self) -> Dict[str, Any]:
        """A deep copy of the raw configuration mapping."""
        return copy.deepcopy(self._data)

    def get(self, path: str, default: Any = None) -> Any:
        """Return the value at a dotted ``path``, or ``default`` if absent."""
        node: Any = self._data
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def require(self, path: str) -> Any:
        """Return the value at ``path``, raising :class:`ConfigError` if absent."""
        sentinel = object()
        value = self.get(path, sentinel)
        if value is sentinel:
            raise ConfigError(f"Missing required configuration key: {path!r}")
        return value

    def section(self, name: str) -> Dict[str, Any]:
        """Return a copy of a top-level section."""
        value = self.require(name)
        if not isinstance(value, dict):
            raise ConfigError(f"Configuration section {name!r} must be a mapping.")
        return copy.deepcopy(value)

    def with_overrides(self, **overrides: Any) -> "Config":
        """Return a new Config with dotted-path ``overrides`` applied.

        Used mainly by tests to vary a single threshold without editing the file.
        """
        data = self.data
        for dotted, value in overrides.items():
            parts = dotted.split(".")
            node = data
            for part in parts[:-1]:
                node = node.setdefault(part, {})
                if not isinstance(node, dict):
                    raise ConfigError(f"Cannot override through non-mapping: {dotted!r}")
            node[parts[-1]] = value
        return Config(data)


def load_config(path: Optional[Path | str] = None) -> Config:
    """Load configuration from ``path`` (defaults to the bundled config.yaml)."""
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
    except yaml.YAMLError as exc:  # pragma: no cover - depends on file contents
        raise ConfigError(f"Could not parse {config_path}: {exc}") from exc

    if raw is None:
        raise ConfigError(f"Configuration file is empty: {config_path}")

    config = Config(raw)
    for section in _REQUIRED_SECTIONS:
        config.section(section)

    weights = config.section("fall_detection")["weights"]
    total = sum(float(v) for v in weights.values())
    if abs(total - 1.0) > 1e-6:
        raise ConfigError(
            f"fall_detection.weights must sum to 1.0, got {total:.4f}"
        )
    return config
