"""
tests/test_sandbox.py — Unit tests for plugin sandbox.

Run: cd /Users/odin/Documents/ProjectOpenClaw/valhalla-mesh-v2 && python3 -m pytest tests/test_sandbox.py -v
"""
from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.sandbox import (
    safe_register_routes,
    validate_plugin_path,
    get_plugin_data_dir,
    get_circuit_state,
    reset_circuit,
    _circuit_state,
)


class TestSafeRegisterRoutes(unittest.TestCase):
    """Tests for safe plugin registration."""

    def setUp(self):
        _circuit_state.clear()

    def test_successful_registration(self):
        """Plugin with valid register_routes() should succeed."""
        module = MagicMock()
        module.register_routes = MagicMock()
        app = MagicMock()
        config = {}

        result = safe_register_routes(module, app, config, "test-plugin")
        self.assertTrue(result)
        module.register_routes.assert_called_once_with(app, config)

    def test_missing_register_routes(self):
        """Plugin without register_routes() should fail gracefully."""
        module = MagicMock(spec=[])  # no register_routes
        del module.register_routes
        app = MagicMock()

        result = safe_register_routes(module, app, {}, "bad-plugin")
        self.assertFalse(result)

    def test_exception_isolation(self):
        """Plugin that raises should not crash bifrost."""
        module = MagicMock()
        module.register_routes = MagicMock(side_effect=RuntimeError("boom"))
        app = MagicMock()

        result = safe_register_routes(module, app, {}, "crashy-plugin")
        self.assertFalse(result)
        state = get_circuit_state()
        self.assertEqual(state["crashy-plugin"]["failures"], 1)

    def test_circuit_breaker_trips(self):
        """After 3 failures, plugin should be disabled."""
        module = MagicMock()
        module.register_routes = MagicMock(side_effect=RuntimeError("boom"))
        app = MagicMock()

        for i in range(3):
            safe_register_routes(module, app, {}, "fragile-plugin")

        state = get_circuit_state()
        self.assertTrue(state["fragile-plugin"]["disabled"])

        # Fourth call should be blocked immediately
        result = safe_register_routes(module, app, {}, "fragile-plugin")
        self.assertFalse(result)

    def test_circuit_breaker_reset(self):
        """Reset should re-enable a disabled plugin."""
        _circuit_state["broken"] = {"failures": 3, "disabled": True, "last_error": "test"}
        reset_circuit("broken")
        state = get_circuit_state()
        self.assertFalse(state["broken"]["disabled"])
        self.assertEqual(state["broken"]["failures"], 0)

    def test_success_resets_failure_count(self):
        """Successful registration should reset failure count."""
        _circuit_state["flaky"] = {"failures": 2, "disabled": False, "last_error": "prev"}
        module = MagicMock()
        module.register_routes = MagicMock()
        app = MagicMock()

        result = safe_register_routes(module, app, {}, "flaky")
        self.assertTrue(result)
        self.assertEqual(get_circuit_state()["flaky"]["failures"], 0)


class TestValidatePluginPath(unittest.TestCase):
    """Tests for plugin filesystem access validation."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        (self.base / "my-plugin").mkdir()
        (self.base / "my-plugin" / "data.json").write_text("{}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.base, ignore_errors=True)

    def test_valid_path(self):
        result = validate_plugin_path("data.json", "my-plugin", self.base)
        self.assertIsNotNone(result)

    def test_traversal_blocked(self):
        result = validate_plugin_path("../other-plugin/data.json", "my-plugin", self.base)
        self.assertIsNone(result)

    def test_absolute_path_blocked(self):
        result = validate_plugin_path("/etc/passwd", "my-plugin", self.base)
        self.assertIsNone(result)

    def test_empty_path_blocked(self):
        result = validate_plugin_path("", "my-plugin", self.base)
        self.assertIsNone(result)


class TestGetPluginDataDir(unittest.TestCase):
    """Tests for plugin data directory creation."""

    def test_creates_data_dir(self):
        base = Path(tempfile.mkdtemp())
        data_dir = get_plugin_data_dir("test-plugin", base)
        self.assertTrue(data_dir.is_dir())
        self.assertEqual(data_dir.name, "data")
        import shutil
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
