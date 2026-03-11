"""
Tests for Sprint 7 — Brain Installer + Telegram Bot.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPO_ROOT = Path(os.path.dirname(__file__)).parent


def _load_module(plugin_name: str, filename: str = "handler.py"):
    plugin_dir = REPO_ROOT / "plugins" / plugin_name
    # For nested paths like installers/cloud.py
    filepath = plugin_dir / filename
    safe_name = f"test_{plugin_name}_{filename}".replace("/", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(safe_name, str(filepath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Model Registry
# ---------------------------------------------------------------------------

class TestModelRegistry:
    def test_models_list_expanded(self):
        mod = _load_module("brain-installer", "registry.py")
        assert len(mod.MODELS) >= 26, f"Expected 26+ models, found {len(mod.MODELS)}"

    def test_get_available_high_vram(self):
        mod = _load_module("brain-installer", "registry.py")
        models = mod.get_available(48.0)
        assert len(models) >= 20
        # All local models should be compatible
        local = [m for m in models if m.get("provider") is None]
        assert all(m["compatible"] for m in local)

    def test_get_available_8gb(self):
        mod = _load_module("brain-installer", "registry.py")
        models = mod.get_available(8.0)
        compatible = [m for m in models if m["compatible"]]
        # Should include small models + cloud
        assert len(compatible) >= 10

    def test_get_available_no_vram(self):
        mod = _load_module("brain-installer", "registry.py")
        models = mod.get_available(0.0)
        # Only cloud models should be compatible
        compatible = [m for m in models if m["compatible"]]
        assert all(m.get("provider") is not None for m in compatible)

    def test_get_model_exists(self):
        mod = _load_module("brain-installer", "registry.py")
        m = mod.get_model("llama-3.1-8b")
        assert m is not None
        assert m["name"] == "Smart & Fast"

    def test_get_model_not_found(self):
        mod = _load_module("brain-installer", "registry.py")
        assert mod.get_model("nonexistent-model") is None

    def test_models_have_required_fields(self):
        mod = _load_module("brain-installer", "registry.py")
        required = {"id", "name", "params", "min_vram", "tier", "description", "category"}
        for m in mod.MODELS:
            missing = required - set(m.keys())
            assert not missing, f"Model {m.get('id')} missing: {missing}"

    def test_categories(self):
        mod = _load_module("brain-installer", "registry.py")
        coding = mod.get_by_category("coding")
        assert len(coding) >= 3
        assert all(m["category"] == "coding" for m in coding)

    def test_reasoning_models(self):
        mod = _load_module("brain-installer", "registry.py")
        reasoning = mod.get_by_category("reasoning")
        assert len(reasoning) >= 4
        assert all("DeepSeek" in m["family"] or "Phi" in m["family"] for m in reasoning)

    def test_families(self):
        mod = _load_module("brain-installer", "registry.py")
        qwen = mod.get_by_family("Qwen")
        assert len(qwen) >= 5
        deepseek = mod.get_by_family("DeepSeek")
        assert len(deepseek) >= 4

    def test_cloud_models(self):
        mod = _load_module("brain-installer", "registry.py")
        cloud = [m for m in mod.MODELS if m.get("provider") is not None]
        assert len(cloud) >= 5

    def test_custom_model_add_remove(self):
        mod = _load_module("brain-installer", "registry.py")
        # Create a temp GGUF file
        tmpdir = Path(tempfile.mkdtemp())
        fake_gguf = tmpdir / "test-model.gguf"
        fake_gguf.write_bytes(b"fake gguf data " * 100)

        result = mod.add_custom_model("Test Model", str(fake_gguf), context=8192)
        assert result["ok"]
        assert result["model"]["family"] == "Custom"
        assert result["model"]["category"] == "custom"

        # Should appear in get_all_models
        all_m = mod.get_all_models()
        custom_ids = [m["id"] for m in all_m if m.get("custom")]
        assert "custom-test-model" in custom_ids

        # Remove
        rm = mod.remove_custom_model("custom-test-model")
        assert rm["ok"]

    def test_custom_model_bad_extension(self):
        mod = _load_module("brain-installer", "registry.py")
        tmpdir = Path(tempfile.mkdtemp())
        bad = tmpdir / "model.bin"
        bad.write_bytes(b"not a gguf")
        result = mod.add_custom_model("Bad Model", str(bad))
        assert not result["ok"]
        assert "gguf" in result["error"].lower()


# ---------------------------------------------------------------------------
# Cloud Installer
# ---------------------------------------------------------------------------

class TestCloudInstaller:
    def test_cloud_always_available(self):
        mod = _load_module("brain-installer", "installers/cloud.py")
        assert mod.is_available() is True

    def test_mask_key(self):
        mod = _load_module("brain-installer", "installers/cloud.py")
        assert mod._mask_key(None) == "Not configured"
        assert mod._mask_key("sk-abc123def456") == "sk-a...f456"
        assert mod._mask_key("short") == "***"

    def test_install_info(self):
        mod = _load_module("brain-installer", "installers/cloud.py")
        info = mod.get_install_info()
        assert info["runtime"] == "cloud"
        assert info["available"] is True


# ---------------------------------------------------------------------------
# oMLX Installer
# ---------------------------------------------------------------------------

class TestOmlxInstaller:
    def test_install_info(self):
        mod = _load_module("brain-installer", "installers/omlx.py")
        info = mod.get_install_info()
        assert info["runtime"] == "omlx"
        assert isinstance(info["available"], bool)

    def test_is_available_returns_bool(self):
        mod = _load_module("brain-installer", "installers/omlx.py")
        assert isinstance(mod.is_available(), bool)


# ---------------------------------------------------------------------------
# llama-server Installer
# ---------------------------------------------------------------------------

class TestLlamacppInstaller:
    def test_install_info(self):
        mod = _load_module("brain-installer", "installers/llamacpp.py")
        info = mod.get_install_info()
        assert info["runtime"] == "llamacpp"
        assert isinstance(info["available"], bool)

    def test_binary_url_generation(self):
        mod = _load_module("brain-installer", "installers/llamacpp.py")
        url = mod._get_binary_url()
        assert "github.com" in url
        assert "llama" in url


# ---------------------------------------------------------------------------
# Process Manager
# ---------------------------------------------------------------------------

class TestProcessManager:
    def test_plist_content(self):
        mod = _load_module("brain-installer", "process_manager.py")
        plist = mod._plist_content(["python3", "-m", "server", "--port", "8080"])
        assert "<?xml" in plist
        assert "python3" in plist
        assert "KeepAlive" in plist

    def test_systemd_content(self):
        mod = _load_module("brain-installer", "process_manager.py")
        unit = mod._systemd_content(["llama-server", "-m", "model.gguf"])
        assert "[Unit]" in unit
        assert "[Service]" in unit
        assert "llama-server" in unit
        assert "Restart=always" in unit

    def test_is_running_returns_bool(self):
        mod = _load_module("brain-installer", "process_manager.py")
        assert isinstance(mod.is_running(), bool)


# ---------------------------------------------------------------------------
# Telegram Bot
# ---------------------------------------------------------------------------

class TestTelegramBot:
    def test_format_notification_pipeline_shipped(self):
        mod = _load_module("telegram")
        text = mod.format_notification("pipeline.shipped", {
            "title": "Fix login", "iterations": 3,
        })
        assert "Task completed" in text
        assert "Fix login" in text

    def test_format_notification_unknown_event(self):
        mod = _load_module("telegram")
        text = mod.format_notification("some.unknown", {"data": 42})
        assert "some.unknown" in text

    def test_command_start(self):
        mod = _load_module("telegram")
        reply = mod.handle_command("/start", 123)
        assert "Welcome" in reply
        assert "/status" in reply

    def test_command_status(self):
        mod = _load_module("telegram")
        reply = mod.handle_command("/status", 123)
        assert "online" in reply.lower()

    def test_command_task_empty(self):
        mod = _load_module("telegram")
        reply = mod.handle_command("/task", 123)
        assert "Usage" in reply

    def test_command_task_with_args(self):
        mod = _load_module("telegram")
        reply = mod.handle_command("/task Fix the CSS", 123)
        assert "queued" in reply.lower()
        assert "Fix the CSS" in reply

    def test_command_brains_no_state(self):
        mod = _load_module("telegram")
        reply = mod.handle_command("/brains", 123)
        assert isinstance(reply, str)

    def test_command_unknown(self):
        mod = _load_module("telegram")
        reply = mod.handle_command("/xyz", 123)
        assert "Unknown" in reply

    def test_validate_token_bad(self):
        mod = _load_module("telegram")
        result = mod._validate_token("bad-token")
        assert not result.get("ok")


# ---------------------------------------------------------------------------
# Plugin Structure
# ---------------------------------------------------------------------------

class TestPluginStructure:
    def test_brain_installer_manifest(self):
        assert (REPO_ROOT / "plugins" / "brain-installer" / "plugin.yaml").exists()

    def test_telegram_manifest(self):
        assert (REPO_ROOT / "plugins" / "telegram" / "plugin.yaml").exists()

    def test_brain_installer_handler(self):
        mod = _load_module("brain-installer")
        assert hasattr(mod, "register_routes")

    def test_telegram_handler(self):
        mod = _load_module("telegram")
        assert hasattr(mod, "register_routes")
        assert hasattr(mod, "on_event")

    def test_install_script_exists(self):
        script = REPO_ROOT / "install.sh"
        assert script.exists()
        assert os.access(str(script), os.X_OK)

    def test_total_plugins_now_18(self):
        plugins_dir = REPO_ROOT / "plugins"
        dirs = [d for d in plugins_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")]
        assert len(dirs) >= 18, f"Expected 18, found {len(dirs)}: {[d.name for d in dirs]}"
