"""Tests for configuration loading and validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import conftest  # noqa: F401

from silentguard.config import load_config
from silentguard.config.loader import Config, ConfigError


class TestConfigLoading(unittest.TestCase):
    def test_bundled_config_loads(self) -> None:
        config = load_config()
        self.assertIsInstance(config.section("decision"), dict)

    def test_dotted_lookup(self) -> None:
        self.assertGreater(load_config().get("decision.confirmation_seconds"), 0)

    def test_missing_key_returns_default(self) -> None:
        self.assertEqual(load_config().get("nope.not.here", "fallback"), "fallback")

    def test_require_raises_for_missing_key(self) -> None:
        with self.assertRaises(ConfigError):
            load_config().require("nope.not.here")

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(ConfigError):
            load_config("/nonexistent/config.yaml")

    def test_weights_must_sum_to_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.yaml"
            path.write_text(
                "perception: {}\n"
                "fall_detection:\n"
                "  weights: {a: 0.5, b: 0.9}\n"
                "decision: {}\nactions: {}\nappliances: {}\nvoice: {}\n",
                encoding="utf-8",
            )
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_overrides_do_not_mutate_the_original(self) -> None:
        config = load_config()
        original = config.get("actions.ir_backend")
        modified = config.with_overrides(**{"actions.ir_backend": "device"})
        self.assertEqual(modified.get("actions.ir_backend"), "device")
        self.assertEqual(config.get("actions.ir_backend"), original)

    def test_rejects_non_mapping_root(self) -> None:
        with self.assertRaises(ConfigError):
            Config(["not", "a", "mapping"])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
