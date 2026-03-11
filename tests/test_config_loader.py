"""
Tests for config_loader.py
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

# Ensure the project root is importable
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_loader import (
    ConfigError,
    _resolve_env,
    _validate,
    load_config,
    get_config,
    reload_config,
    get_config_raw_yaml,
    save_config_yaml,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_CONFIG = {
    "node": {"name": "test-node", "role": "test", "port": 8765},
    "mesh": {
        "nodes": {
            "peer1": {"ip": "10.0.0.1", "port": 8765, "role": "worker"},
        }
    },
    "models": {
        "default": "llama/test-model",
        "providers": {},
        "aliases": {"fast": "llama/test-model"},
    },
    "plugins": {"enabled": ["model-switch"]},
}


@pytest.fixture
def config_file(tmp_path):
    """Write a valid config to a temp file and return the path."""
    path = tmp_path / "valhalla.yaml"
    path.write_text(yaml.dump(VALID_CONFIG), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the config singleton between tests."""
    import config_loader
    config_loader._config = None
    yield
    config_loader._config = None


# ---------------------------------------------------------------------------
# ENV resolution
# ---------------------------------------------------------------------------

class TestResolveEnv:
    def test_string_resolution(self):
        os.environ["TEST_VAL_123"] = "hello"
        assert _resolve_env("${TEST_VAL_123}") == "hello"
        del os.environ["TEST_VAL_123"]

    def test_nested_dict(self):
        os.environ["DB_HOST"] = "localhost"
        result = _resolve_env({"db": {"host": "${DB_HOST}"}})
        assert result["db"]["host"] == "localhost"
        del os.environ["DB_HOST"]

    def test_list_resolution(self):
        os.environ["ITEM_A"] = "alpha"
        result = _resolve_env(["${ITEM_A}", "static"])
        assert result == ["alpha", "static"]
        del os.environ["ITEM_A"]

    def test_missing_env_var_resolves_empty(self):
        result = _resolve_env("${DEFINITELY_NOT_SET_XYZ}")
        assert result == ""

    def test_non_string_passthrough(self):
        assert _resolve_env(42) == 42
        assert _resolve_env(True) is True
        assert _resolve_env(None) is None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_valid_config_passes(self):
        _validate(VALID_CONFIG)  # should not raise

    def test_missing_node_fails(self):
        cfg = {k: v for k, v in VALID_CONFIG.items() if k != "node"}
        with pytest.raises(ConfigError, match="Missing required"):
            _validate(cfg)

    def test_missing_node_name_fails(self):
        cfg = {**VALID_CONFIG, "node": {"port": 8765}}
        with pytest.raises(ConfigError, match="node.name"):
            _validate(cfg)

    def test_missing_models_default_fails(self):
        cfg = {**VALID_CONFIG, "models": {"providers": {}}}
        with pytest.raises(ConfigError, match="models.default"):
            _validate(cfg)

    def test_missing_plugins_enabled_fails(self):
        cfg = {**VALID_CONFIG, "plugins": {}}
        with pytest.raises(ConfigError, match="plugins.enabled"):
            _validate(cfg)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_load_valid(self, config_file):
        config = load_config(config_file)
        assert config["node"]["name"] == "test-node"
        assert "_meta" in config

    def test_load_missing_file(self, tmp_path):
        with pytest.raises(ConfigError, match="not found"):
            load_config(tmp_path / "nonexistent.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("just a string", encoding="utf-8")
        with pytest.raises(ConfigError, match="YAML mapping"):
            load_config(bad)

    def test_env_resolution_in_load(self, tmp_path):
        os.environ["MY_TEST_KEY"] = "secret123"
        cfg = {**VALID_CONFIG}
        cfg["models"] = {**cfg["models"], "providers": {
            "nvidia": {"key": "${MY_TEST_KEY}"}
        }}
        path = tmp_path / "valhalla.yaml"
        path.write_text(yaml.dump(cfg), encoding="utf-8")
        result = load_config(path)
        assert result["models"]["providers"]["nvidia"]["key"] == "secret123"
        del os.environ["MY_TEST_KEY"]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_config_returns_same_object(self, config_file):
        a = get_config(config_file)
        b = get_config(config_file)
        assert a is b

    def test_reload_updates_singleton(self, tmp_path):
        path = tmp_path / "valhalla.yaml"
        path.write_text(yaml.dump(VALID_CONFIG), encoding="utf-8")
        original = get_config(path)
        assert original["node"]["name"] == "test-node"

        # Modify and reload
        updated = {**VALID_CONFIG, "node": {**VALID_CONFIG["node"], "name": "reloaded"}}
        path.write_text(yaml.dump(updated), encoding="utf-8")
        reloaded = reload_config(path)
        assert reloaded["node"]["name"] == "reloaded"


# ---------------------------------------------------------------------------
# Raw YAML / Save
# ---------------------------------------------------------------------------

class TestRawYaml:
    def test_get_raw_yaml(self, config_file):
        raw = get_config_raw_yaml(config_file)
        assert "test-node" in raw

    def test_save_config_yaml(self, config_file):
        new_yaml = yaml.dump({**VALID_CONFIG, "node": {**VALID_CONFIG["node"], "name": "saved"}})
        result = save_config_yaml(new_yaml, config_file)
        assert result["node"]["name"] == "saved"
        # Verify on disk
        on_disk = yaml.safe_load(config_file.read_text())
        assert on_disk["node"]["name"] == "saved"

    def test_save_invalid_yaml_rejected(self, config_file):
        with pytest.raises(ConfigError):
            save_config_yaml("not: {a: valid: config}", config_file)
