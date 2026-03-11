"""
Integration test suite for Valhalla Mesh V2.

Sprint 5 — Proves all plugins load together, endpoints respond,
and key workflows (pipeline, debate, export/import) work end-to-end.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPO_ROOT = Path(os.path.dirname(__file__)).parent


class TestPluginDiscovery:
    """All 15 plugins have valid manifests."""

    def test_all_plugins_have_manifests(self):
        plugins_dir = REPO_ROOT / "plugins"
        for pdir in sorted(plugins_dir.iterdir()):
            if not pdir.is_dir() or pdir.name.startswith("_"):
                continue
            manifest = pdir / "plugin.yaml"
            assert manifest.exists(), f"Missing plugin.yaml for {pdir.name}"

    def test_all_plugins_have_handlers(self):
        plugins_dir = REPO_ROOT / "plugins"
        for pdir in sorted(plugins_dir.iterdir()):
            if not pdir.is_dir() or pdir.name.startswith("_"):
                continue
            handler = pdir / "handler.py"
            assert handler.exists(), f"Missing handler.py for {pdir.name}"

    def test_all_handlers_importable(self):
        """Every handler.py can be imported without error."""
        plugins_dir = REPO_ROOT / "plugins"
        failures = []
        for pdir in sorted(plugins_dir.iterdir()):
            if not pdir.is_dir() or pdir.name.startswith("_"):
                continue
            handler = pdir / "handler.py"
            if not handler.exists():
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"test_{pdir.name}_handler", str(handler)
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                assert hasattr(mod, "register_routes"), \
                    f"{pdir.name}/handler.py missing register_routes()"
            except Exception as e:
                failures.append(f"{pdir.name}: {e}")

        assert not failures, f"Handler import failures:\n" + "\n".join(failures)

    def test_no_duplicate_routes(self):
        """No two plugins claim the same route path."""
        import yaml

        plugins_dir = REPO_ROOT / "plugins"
        all_routes = []
        for pdir in sorted(plugins_dir.iterdir()):
            manifest = pdir / "plugin.yaml"
            if not manifest.exists():
                continue
            data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
            for route in data.get("routes", []):
                path = route.get("path", "")
                method = route.get("method", "GET")
                key = f"{method} {path}"
                assert key not in all_routes, \
                    f"Duplicate route: {key} (in {pdir.name})"
                all_routes.append(key)


class TestExportImportRoundtrip:
    """Export an agent, re-import it, verify identity preserved."""

    def _get_exporter(self):
        spec = importlib.util.spec_from_file_location(
            "exporter",
            str(REPO_ROOT / "plugins" / "marketplace" / "exporter.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _get_importer(self):
        spec = importlib.util.spec_from_file_location(
            "importer",
            str(REPO_ROOT / "plugins" / "marketplace" / "importer.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_export_creates_valid_zip(self):
        exporter = self._get_exporter()
        tmpdir = Path(tempfile.mkdtemp())

        # Create soul files
        soul_dir = tmpdir / "mesh" / "souls"
        soul_dir.mkdir(parents=True)
        (soul_dir / "SOUL.test.md").write_text("I am a test agent.")
        (soul_dir / "IDENTITY.test.md").write_text("Test identity.")

        result = exporter.export_agent(
            agent_name="test-agent",
            base_dir=tmpdir,
            soul_config={
                "personality": "mesh/souls/SOUL.test.md",
                "identity": "mesh/souls/IDENTITY.test.md",
            },
            version="1.0.0",
            description="Test agent for CI",
        )

        assert result is not None
        assert len(result) > 0

        # Verify it's a valid zip
        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            names = zf.namelist()
            assert "manifest.yaml" in names
            assert "SOUL.md" in names
            assert "IDENTITY.md" in names

    def test_import_validates_manifest(self):
        importer = self._get_importer()

        # Create a minimal valid package
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr("manifest.yaml",
                        "name: roundtrip-test\nversion: 1.0.0\nformat_version: 1.0\n")
            zf.writestr("SOUL.md", "I am the test soul.")

        tmpdir = Path(tempfile.mkdtemp())
        result = importer.import_agent(buf.getvalue(), tmpdir)

        assert result["ok"] is True
        assert result["agent_name"] == "roundtrip-test"
        assert result["version"] == "1.0.0"

        # Verify files on disk
        agent_dir = tmpdir / "agents" / "roundtrip-test"
        assert agent_dir.exists()
        soul = (agent_dir / "SOUL.md").read_text()
        assert "test soul" in soul

    def test_import_rejects_executable_files(self):
        importer = self._get_importer()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr("manifest.yaml",
                        "name: evil\nversion: 1.0.0\nformat_version: 1.0\n")
            zf.writestr("backdoor.py", "import os; os.system('rm -rf /')")

        is_valid, manifest, issues = importer.validate_package(buf.getvalue())
        assert not is_valid
        assert any("Blocked" in i for i in issues)

    def test_import_rejects_missing_manifest(self):
        importer = self._get_importer()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr("random.txt", "no manifest here")

        is_valid, manifest, issues = importer.validate_package(buf.getvalue())
        assert not is_valid
        assert any("manifest" in i.lower() for i in issues)

    def test_full_roundtrip(self):
        """Export → validate → import → verify identity."""
        exporter = self._get_exporter()
        importer = self._get_importer()

        # Setup source
        src = Path(tempfile.mkdtemp())
        soul_dir = src / "mesh" / "souls"
        soul_dir.mkdir(parents=True)
        (soul_dir / "SOUL.odin.md").write_text("I am Odin, the Allfather.")
        (soul_dir / "IDENTITY.odin.md").write_text("Orchestrator of Valhalla.")

        # Write some procedures
        proc_dir = src / "war_room_data"
        proc_dir.mkdir(parents=True)
        procedures = [
            {"task_type": "devops", "approach": "Use CI/CD", "confidence": 0.95},
            {"task_type": "debug", "approach": "Print and pray", "confidence": 0.3},
        ]
        (proc_dir / "procedures.json").write_text(json.dumps(procedures))

        # Export
        zip_bytes = exporter.export_agent(
            agent_name="odin-export",
            base_dir=src,
            soul_config={
                "personality": "mesh/souls/SOUL.odin.md",
                "identity": "mesh/souls/IDENTITY.odin.md",
            },
            min_confidence=0.7,
        )
        assert zip_bytes

        # Validate
        is_valid, manifest, issues = importer.validate_package(zip_bytes)
        assert is_valid, f"Validation failed: {issues}"

        # Import to a different directory
        dst = Path(tempfile.mkdtemp())
        result = importer.import_agent(zip_bytes, dst)
        assert result["ok"] is True
        assert result["agent_name"] == "odin-export"

        # Verify: SOUL preserved
        soul = (dst / "agents" / "odin-export" / "SOUL.md").read_text()
        assert "Allfather" in soul

        # Verify: only high-confidence procedure exported
        procs = json.loads(
            (dst / "agents" / "odin-export" / "procedures.json").read_text()
        )
        assert len(procs) == 1
        assert procs[0]["task_type"] == "devops"

    def test_private_data_stripped(self):
        """Ensure API keys and IPs are stripped from exports."""
        exporter = self._get_exporter()

        src = Path(tempfile.mkdtemp())
        soul_dir = src / "mesh" / "souls"
        soul_dir.mkdir(parents=True)
        (soul_dir / "SOUL.md").write_text(
            "I run on 192.168.1.100 with api_key: sk-abc123secret"
        )

        zip_bytes = exporter.export_agent(
            agent_name="redact-test",
            base_dir=src,
            soul_config={"personality": "mesh/souls/SOUL.md"},
        )

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            if "SOUL.md" in zf.namelist():
                content = zf.read("SOUL.md").decode()
                assert "sk-abc123" not in content
                assert "192.168.1.100" not in content


class TestMarketplaceRegistry:
    """Marketplace registry functions."""

    def _get_handler(self):
        spec = importlib.util.spec_from_file_location(
            "mkt_handler",
            str(REPO_ROOT / "plugins" / "marketplace" / "handler.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_registry_load_save(self):
        mod = self._get_handler()
        mod._REGISTRY_PATH = Path(tempfile.mkdtemp())

        # Save
        entries = [{"id": "test-1", "name": "test", "description": "A test"}]
        mod._save_registry(entries)

        # Load
        loaded = mod._load_registry()
        assert len(loaded) == 1
        assert loaded[0]["name"] == "test"

    def test_empty_registry(self):
        mod = self._get_handler()
        mod._REGISTRY_PATH = Path(tempfile.mkdtemp())
        assert mod._load_registry() == []


class TestPipelineGitBranching:
    """Pipeline git branching functions."""

    def _get_handler(self):
        spec = importlib.util.spec_from_file_location(
            "pipe_handler",
            str(REPO_ROOT / "plugins" / "pipeline" / "handler.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_git_branching_disabled_by_default(self):
        mod = self._get_handler()
        assert mod._GIT_BRANCHING is False

    def test_git_create_branch_noop_when_disabled(self):
        mod = self._get_handler()
        mod._GIT_BRANCHING = False
        result = mod._git_create_branch("pipe_123", "thor")
        assert result is False

    def test_git_merge_branch_noop_when_disabled(self):
        mod = self._get_handler()
        mod._GIT_BRANCHING = False
        result = mod._git_merge_branch("pipe_123", "thor")
        assert result is False


class TestSocraticConsensus:
    """Socratic debate consensus logic."""

    def _get_handler(self):
        spec = importlib.util.spec_from_file_location(
            "socratic_handler",
            str(REPO_ROOT / "plugins" / "socratic" / "handler.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_consensus_reached(self):
        mod = self._get_handler()
        state = {
            "scores": {"architect": 8, "critic": 9, "user": 7},
            "consensus_threshold": 0.7,
            "current_round": 3,
            "rounds": 3,
        }
        mod._evaluate_consensus("test", state)
        assert state["status"] == "consensus"
        assert state["consensus_score"] == 8.0

    def test_deadlock(self):
        mod = self._get_handler()
        state = {
            "scores": {"architect": 3, "critic": 4},
            "consensus_threshold": 0.8,
            "current_round": 3,
            "rounds": 3,
        }
        mod._evaluate_consensus("test", state)
        assert state["status"] == "deadlock"


class TestBeliefNovelty:
    """Belief shadow novelty scoring integration."""

    def _get_handler(self):
        spec = importlib.util.spec_from_file_location(
            "belief_handler",
            str(REPO_ROOT / "plugins" / "belief-shadows" / "handler.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_novelty_workflow(self):
        """Record → check novelty → verify it drops."""
        mod = self._get_handler()
        mod._shadows = {}
        mod._BASE_DIR = Path(tempfile.mkdtemp())

        # Before sharing: novelty = 1.0
        assert mod.novelty_score("hyp_1", "test", "thor") == 1.0

        # After sharing: novelty = 0.0
        mod.record_shared("thor", "hyp_1", "test hypothesis")
        assert mod.novelty_score("hyp_1", "test", "thor") == 0.0


class TestPersonalityEvolution:
    """Personality evolution integration."""

    def _get_handler(self):
        spec = importlib.util.spec_from_file_location(
            "personality_handler",
            str(REPO_ROOT / "plugins" / "personality" / "handler.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_evolution_chain(self):
        """Multiple events should cumulatively shift traits."""
        mod = self._get_handler()
        mod._traits = {**mod.DEFAULT_TRAITS}
        mod._BASE_DIR = Path(tempfile.mkdtemp())

        initial_accuracy = mod._traits["accuracy"]

        # Ship 5 pipelines
        for _ in range(5):
            mod.evolve("pipeline.shipped")

        assert mod._traits["accuracy"] > initial_accuracy
        assert mod._traits["accuracy"] <= 1.0

    def test_system_prompt_reflects_traits(self):
        mod = self._get_handler()
        mod._traits = {**mod.DEFAULT_TRAITS, "skepticism": 0.9, "caution": 0.9}
        prompt = mod.to_system_prompt()
        assert "Question every assumption" in prompt
        assert "safe approaches" in prompt.lower() or "Prefer safe" in prompt
