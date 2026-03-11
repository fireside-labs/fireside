"""
Tests for the Hydra plugin — fracture resilience.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestHydraCore:
    """Core Hydra functions (no network)."""

    def _get_handler(self):
        """Import Hydra handler."""
        import importlib.util
        handler_path = os.path.join(
            os.path.dirname(__file__), "..", "plugins", "hydra", "handler.py"
        )
        spec = importlib.util.spec_from_file_location("hydra_handler", handler_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_initial_status_empty(self):
        """Status should show no absorbed roles initially."""
        mod = self._get_handler()
        # Reset state
        mod._absorbed.clear()
        status = mod.get_status()
        assert status["hydra_active"] is False
        assert status["absorbed_roles"] == []

    def test_build_absorption_prompt_no_soul(self):
        """Build prompt with empty soul data."""
        mod = self._get_handler()
        prompt = mod._build_absorption_prompt("thor", {}, {"role": "backend"})
        assert "HYDRA MODE" in prompt
        assert "thor" in prompt
        assert "backend" in prompt

    def test_build_absorption_prompt_with_soul(self):
        """Build prompt with soul content."""
        mod = self._get_handler()
        soul = {
            "IDENTITY": "# Thor\n- Role: Backend\n- Vibe: Technical",
            "SOUL": "## Core Traits\nBuild things that work. Think deep.\n## Boundaries\nDefers to Odin.",
        }
        prompt = mod._build_absorption_prompt("thor", soul, {"role": "backend"})
        assert "Build things that work" in prompt
        assert "thor" in prompt.lower()

    def test_absorb_cold_no_snapshot(self):
        """Absorb with no stored snapshot gives cold status."""
        mod = self._get_handler()
        mod._absorbed.clear()
        mod._NODE_ID = "odin"
        mod._MESH_NODES = {}

        # Use a temp dir so no snapshots exist
        mod._BASE_DIR = Path(tempfile.mkdtemp())

        ctx = mod.absorb_node("thor")
        assert ctx["status"] == "cold"
        assert ctx["dead_node"] == "thor"
        assert "thor" in mod._absorbed

    def test_release_role(self):
        """Release a previously absorbed role."""
        mod = self._get_handler()
        mod._absorbed["freya"] = {
            "dead_node": "freya",
            "absorbed_at": time.time() - 60,
            "status": "active",
        }

        result = mod.release_role("freya")
        assert result["ok"] is True
        assert "freya" not in mod._absorbed

    def test_release_nonexistent(self):
        """Releasing a non-absorbed role returns error."""
        mod = self._get_handler()
        mod._absorbed.clear()

        result = mod.release_role("nonexistent")
        assert result["ok"] is False

    def test_get_system_prompt_injection_empty(self):
        """No injection when nothing is absorbed."""
        mod = self._get_handler()
        mod._absorbed.clear()
        assert mod.get_system_prompt_injection() == ""

    def test_get_system_prompt_injection_with_absorbed(self):
        """Injection returned when roles are absorbed."""
        mod = self._get_handler()
        mod._absorbed = {
            "thor": {
                "system_prompt_injection": "[HYDRA MODE — proxying thor]\nYou are Thor.",
            },
        }
        injection = mod.get_system_prompt_injection()
        assert "HYDRA MODE" in injection
        assert "thor" in injection.lower()

    def test_status_with_absorbed_roles(self):
        """Status shows absorbed role details."""
        mod = self._get_handler()
        mod._NODE_ID = "odin"
        mod._absorbed = {
            "thor": {
                "status": "active",
                "absorbed_at": time.time() - 120,
            },
        }

        status = mod.get_status()
        assert status["hydra_active"] is True
        assert "thor" in status["absorbed_roles"]
        assert "thor" in status["absorbed_details"]
        assert status["absorbed_details"]["thor"]["status"] == "active"

    def test_snapshot_writes_json(self):
        """Snapshot generates a JSON file locally."""
        mod = self._get_handler()
        mod._NODE_ID = "test_node"
        mod._BASE_DIR = Path(tempfile.mkdtemp())
        mod._MESH_NODES = {}
        mod._AUTH_TOKEN = ""

        snapshot = mod.generate_snapshot()

        assert snapshot["node"] == "test_node"
        assert "snapshot_id" in snapshot

        # Check file was written
        snap_file = mod._BASE_DIR / "war_room_data" / "snapshots" / "test_node_latest.json"
        assert snap_file.exists()
        data = json.loads(snap_file.read_text())
        assert data["node"] == "test_node"
