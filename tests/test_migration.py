"""
Tests for scripts/migrate_v1.py — V1→V2 config migration.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from migrate_v1 import parse_v1_configs, to_yaml, _yaml_value


class TestMigrationParser:
    """Test V1 config parsing."""

    def _make_v1_dir(self, files: dict) -> Path:
        """Create a temp directory with V1 config files."""
        tmpdir = Path(tempfile.mkdtemp())
        for name, content in files.items():
            path = tmpdir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, dict):
                path.write_text(json.dumps(content), encoding="utf-8")
            else:
                path.write_text(content, encoding="utf-8")
        return tmpdir

    def test_empty_dir(self):
        """Migration with an empty directory."""
        tmpdir = Path(tempfile.mkdtemp())
        result = parse_v1_configs(tmpdir, "odin")
        assert result["node"]["name"] == "odin"
        assert isinstance(result["plugins"]["enabled"], list)

    def test_basic_config(self):
        """Parse a basic config.json."""
        v1_dir = self._make_v1_dir({
            "config.json": {
                "port": 9000,
                "role": "orchestrator",
                "model": "llama/test-model",
            }
        })
        result = parse_v1_configs(v1_dir, "odin")
        assert result["node"]["port"] == 9000
        assert result["node"]["role"] == "orchestrator"
        assert result["models"]["default"] == "llama/test-model"

    def test_node_specific_config(self):
        """Prefer config.<node>.json over config.json."""
        v1_dir = self._make_v1_dir({
            "config.json": {"port": 8000},
            "config.thor.json": {"port": 9999, "role": "backend"},
        })
        result = parse_v1_configs(v1_dir, "thor")
        assert result["node"]["port"] == 9999
        assert result["node"]["role"] == "backend"

    def test_mesh_nodes_from_config(self):
        """Extract mesh nodes from config."""
        v1_dir = self._make_v1_dir({
            "config.json": {
                "port": 8765,
                "nodes": {
                    "thor": {"ip": "100.1.2.3", "port": 8765, "role": "backend"},
                    "freya": {"ip": "100.4.5.6", "port": 8765, "role": "memory"},
                },
            }
        })
        result = parse_v1_configs(v1_dir, "odin")
        assert "thor" in result["mesh"]["nodes"]
        assert result["mesh"]["nodes"]["thor"]["ip"] == "100.1.2.3"
        assert "freya" in result["mesh"]["nodes"]

    def test_war_room_enables_plugins(self):
        """war_room/ directory presence enables cognitive plugins."""
        v1_dir = self._make_v1_dir({
            "config.json": {"port": 8765},
        })
        # Create war_room subdirectory
        (v1_dir / "war_room").mkdir()

        result = parse_v1_configs(v1_dir, "odin")
        assert "event-bus" in result["plugins"]["enabled"]
        assert "hypotheses" in result["plugins"]["enabled"]

    def test_hydra_detection(self):
        """hydra.py presence enables hydra plugin."""
        v1_dir = self._make_v1_dir({
            "config.json": {"port": 8765},
            "hydra.py": "# hydra stub",
        })
        result = parse_v1_configs(v1_dir, "odin")
        assert "hydra" in result["plugins"]["enabled"]

    def test_aliases_extraction(self):
        """Extract model aliases from config."""
        v1_dir = self._make_v1_dir({
            "config.json": {
                "aliases": {
                    "odin": "llama/big-model",
                    "hugs": "nvidia/other-model",
                },
            }
        })
        result = parse_v1_configs(v1_dir, "odin")
        assert result["models"]["aliases"]["odin"] == "llama/big-model"

    def test_scan_other_configs_for_mesh(self):
        """Discover mesh topology from config.*.json files."""
        v1_dir = self._make_v1_dir({
            "config.odin.json": {"port": 8765, "ip": "100.0.0.1"},
            "config.thor.json": {"port": 8765, "ip": "100.0.0.2", "role": "backend"},
            "config.freya.json": {"port": 8765, "ip": "100.0.0.3", "role": "memory"},
        })
        result = parse_v1_configs(v1_dir, "odin")
        assert "thor" in result["mesh"]["nodes"]
        assert "freya" in result["mesh"]["nodes"]
        assert result["mesh"]["nodes"]["thor"]["ip"] == "100.0.0.2"


class TestYamlOutput:
    """Test YAML serialization."""

    def test_simple_dict(self):
        """Simple key-value output."""
        result = to_yaml({"name": "odin", "port": 8765})
        assert "name: odin" in result
        assert "port: 8765" in result

    def test_nested_dict(self):
        """Nested dict indentation."""
        result = to_yaml({"node": {"name": "odin", "role": "orchestrator"}})
        assert "node:" in result
        assert "  name: odin" in result

    def test_list_values(self):
        """List values are formatted correctly."""
        result = to_yaml({"plugins": ["model-switch", "watchdog"]})
        assert "  - model-switch" in result
        assert "  - watchdog" in result

    def test_yaml_value_quoting(self):
        """Values with special chars are quoted."""
        assert _yaml_value("hello") == "hello"
        assert _yaml_value("true") == '"true"'
        assert _yaml_value("http://localhost:8080") == '"http://localhost:8080"'
        assert _yaml_value(42) == "42"
        assert _yaml_value(True) == "true"
        assert _yaml_value(None) == "null"

    def test_bool_values(self):
        """Boolean values serialize correctly."""
        result = to_yaml({"enabled": True, "debug": False})
        assert "enabled: true" in result
        assert "debug: false" in result
