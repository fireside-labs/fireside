"""
Tests for plugin_loader.py
"""

import sys
import textwrap
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from plugin_loader import (
    _load_plugin_manifest,
    discover_plugins,
    load_plugins,
    get_plugins,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def plugins_dir(tmp_path):
    """Create a temporary plugins directory with a test plugin."""
    pdir = tmp_path / "plugins"
    pdir.mkdir()

    # Plugin A — valid
    a_dir = pdir / "test-plugin-a"
    a_dir.mkdir()
    (a_dir / "plugin.yaml").write_text(yaml.dump({
        "name": "test-plugin-a",
        "version": "1.0.0",
        "description": "Test plugin A",
        "author": "tests",
        "routes": [{"method": "GET", "path": "/test-a"}],
        "events": ["test.event"],
        "config_keys": ["test.key"],
    }), encoding="utf-8")
    (a_dir / "handler.py").write_text(textwrap.dedent("""
        _registered = False

        def register_routes(app, config):
            global _registered
            _registered = True
    """), encoding="utf-8")

    # Plugin B — valid
    b_dir = pdir / "test-plugin-b"
    b_dir.mkdir()
    (b_dir / "plugin.yaml").write_text(yaml.dump({
        "name": "test-plugin-b",
        "version": "0.1.0",
        "description": "Test plugin B",
    }), encoding="utf-8")
    (b_dir / "handler.py").write_text(textwrap.dedent("""
        def register_routes(app, config):
            pass
    """), encoding="utf-8")

    # Plugin C — no handler.py (should be skipped)
    c_dir = pdir / "test-plugin-c"
    c_dir.mkdir()
    (c_dir / "plugin.yaml").write_text(yaml.dump({
        "name": "test-plugin-c",
    }), encoding="utf-8")

    return pdir


@pytest.fixture
def config():
    return {
        "node": {"name": "test", "port": 8765},
        "mesh": {"nodes": {}},
        "models": {"default": "test", "aliases": {}},
        "plugins": {"enabled": ["test-plugin-a", "test-plugin-b"]},
    }


@pytest.fixture(autouse=True)
def reset_loaded():
    """Reset loaded plugins between tests."""
    import plugin_loader
    plugin_loader._loaded_plugins = []
    yield
    plugin_loader._loaded_plugins = []


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

class TestManifest:
    def test_load_valid_manifest(self, plugins_dir):
        manifest = _load_plugin_manifest(plugins_dir / "test-plugin-a")
        assert manifest is not None
        assert manifest["name"] == "test-plugin-a"
        assert manifest["version"] == "1.0.0"

    def test_load_missing_manifest(self, tmp_path):
        empty = tmp_path / "empty-plugin"
        empty.mkdir()
        assert _load_plugin_manifest(empty) is None

    def test_load_invalid_manifest(self, tmp_path):
        bad = tmp_path / "bad-plugin"
        bad.mkdir()
        (bad / "plugin.yaml").write_text("just a string", encoding="utf-8")
        assert _load_plugin_manifest(bad) is None


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

class TestDiscovery:
    def test_discover_all_plugins(self, plugins_dir):
        manifests = discover_plugins(plugins_dir)
        names = [m["name"] for m in manifests]
        assert "test-plugin-a" in names
        assert "test-plugin-b" in names
        assert "test-plugin-c" in names  # has manifest, just no handler

    def test_discover_empty_dir(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        assert discover_plugins(empty) == []

    def test_discover_nonexistent_dir(self, tmp_path):
        assert discover_plugins(tmp_path / "nope") == []


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

class TestLoading:
    def test_load_enabled_plugins(self, plugins_dir, config):
        app = type("FakeApp", (), {"include_router": lambda self, r: None})()
        loaded = load_plugins(app, config, plugins_dir)
        names = [p["name"] for p in loaded]
        assert "test-plugin-a" in names
        assert "test-plugin-b" in names
        assert len(loaded) == 2

    def test_skip_missing_plugin(self, plugins_dir, config):
        config["plugins"]["enabled"] = ["nonexistent"]
        app = type("FakeApp", (), {"include_router": lambda self, r: None})()
        loaded = load_plugins(app, config, plugins_dir)
        assert len(loaded) == 0

    def test_skip_plugin_without_handler(self, plugins_dir, config):
        config["plugins"]["enabled"] = ["test-plugin-c"]
        app = type("FakeApp", (), {"include_router": lambda self, r: None})()
        loaded = load_plugins(app, config, plugins_dir)
        assert len(loaded) == 0


# ---------------------------------------------------------------------------
# get_plugins
# ---------------------------------------------------------------------------

class TestGetPlugins:
    def test_get_plugins_metadata(self, plugins_dir, config):
        app = type("FakeApp", (), {"include_router": lambda self, r: None})()
        load_plugins(app, config, plugins_dir)
        plugins = get_plugins()
        assert len(plugins) == 2
        a = next(p for p in plugins if p["name"] == "test-plugin-a")
        assert a["version"] == "1.0.0"
        assert a["status"] == "loaded"
        assert a["description"] == "Test plugin A"

    def test_get_plugins_empty_before_load(self):
        assert get_plugins() == []
