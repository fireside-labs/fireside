"""
marketplace/importer.py — Install a .valhalla agent package.

Validates manifest, checks model requirements, creates agent directory,
registers procedures, and queues philosopher prompt for next session.
"""
from __future__ import annotations

import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Optional

log = logging.getLogger("valhalla.marketplace.importer")

REQUIRED_MANIFEST_KEYS = {"name", "version", "format_version"}
ALLOWED_EXTENSIONS = {".yaml", ".md", ".json", ".txt"}
BLOCKED_EXTENSIONS = {".py", ".js", ".sh", ".bat", ".exe", ".so", ".dylib"}


def _parse_yaml_simple(text: str) -> dict:
    """Minimal YAML parser for manifest files."""
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                # Try to parse numbers and bools
                if value.lower() in ("true", "yes"):
                    result[key] = True
                elif value.lower() in ("false", "no"):
                    result[key] = False
                else:
                    try:
                        result[key] = float(value) if "." in value else int(value)
                    except ValueError:
                        result[key] = value
    return result


def validate_package(zip_bytes: bytes) -> tuple:
    """Validate a .valhalla package.

    Returns (is_valid: bool, manifest: dict | None, issues: list[str]).
    """
    issues = []

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            names = zf.namelist()

            # Check for blocked file types (security)
            for name in names:
                ext = Path(name).suffix.lower()
                if ext in BLOCKED_EXTENSIONS:
                    issues.append(f"Blocked file type: {name} ({ext})")

            # Must have manifest
            if "manifest.yaml" not in names:
                issues.append("Missing manifest.yaml")
                return False, None, issues

            # Parse manifest
            manifest_text = zf.read("manifest.yaml").decode("utf-8")
            manifest = _parse_yaml_simple(manifest_text)

            # Check required keys
            missing = REQUIRED_MANIFEST_KEYS - set(manifest.keys())
            if missing:
                issues.append(f"Missing manifest keys: {missing}")

            # Check format version
            fmt = str(manifest.get("format_version", ""))
            if fmt and fmt != "1.0":
                issues.append(f"Unsupported format version: {fmt}")

            # Size check (max 50MB)
            total_size = sum(info.file_size for info in zf.infolist())
            if total_size > 50 * 1024 * 1024:
                issues.append(f"Package too large: {total_size / 1024 / 1024:.1f}MB > 50MB")

    except zipfile.BadZipFile:
        issues.append("Invalid zip file")
        return False, None, issues
    except Exception as e:
        issues.append(f"Validation error: {e}")
        return False, None, issues

    return len(issues) == 0, manifest, issues


def check_model_requirements(manifest: dict, local_config: dict) -> tuple:
    """Check if local hardware meets model requirements.

    Returns (compatible: bool, warnings: list[str]).
    """
    warnings = []
    reqs = manifest.get("model_requirements", {})
    if isinstance(reqs, str):
        return True, []

    # We can't actually check GPU/RAM from Python easily,
    # so we just flag the requirements for the user
    if isinstance(reqs, dict):
        min_ram = reqs.get("min_ram_gb", 0)
        if isinstance(min_ram, (int, float)) and min_ram > 32:
            warnings.append(f"Requires {min_ram}GB RAM — verify your system has enough")

        gpu = reqs.get("gpu_recommended", False)
        if gpu:
            warnings.append("GPU recommended for best performance")

    return True, warnings


def import_agent(
    zip_bytes: bytes,
    base_dir: Path,
    agents_dir: Optional[Path] = None,
) -> dict:
    """Import a .valhalla agent package.

    Returns result dict with status, agent_name, and any warnings.
    """
    # Validate first
    is_valid, manifest, issues = validate_package(zip_bytes)
    if not is_valid:
        return {"ok": False, "errors": issues}

    agent_name = manifest.get("name", "unknown-agent")
    version = manifest.get("version", "1.0.0")

    # Create agent directory
    if agents_dir is None:
        agents_dir = base_dir / "agents"
    agent_dir = agents_dir / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)

    warnings = []
    installed_files = []

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            for name in zf.namelist():
                ext = Path(name).suffix.lower()

                # Security: skip blocked extensions
                if ext in BLOCKED_EXTENSIONS:
                    warnings.append(f"Skipped blocked file: {name}")
                    continue

                # Security: skip path traversal attempts
                if ".." in name or name.startswith("/"):
                    warnings.append(f"Skipped suspicious path: {name}")
                    continue

                content = zf.read(name)
                target = agent_dir / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                installed_files.append(name)

        # Register procedures if present
        proc_file = agent_dir / "procedures.json"
        procedure_count = 0
        if proc_file.exists():
            try:
                procs = json.loads(proc_file.read_text(encoding="utf-8"))
                if isinstance(procs, list):
                    procedure_count = len(procs)
                elif isinstance(procs, dict):
                    procedure_count = len(procs)

                # Merge into local procedures store
                local_procs = base_dir / "war_room_data" / "procedures.json"
                if local_procs.exists():
                    existing = json.loads(local_procs.read_text(encoding="utf-8"))
                else:
                    existing = []
                    local_procs.parent.mkdir(parents=True, exist_ok=True)

                if isinstance(procs, list) and isinstance(existing, list):
                    existing.extend(procs)
                    local_procs.write_text(json.dumps(existing, indent=2), encoding="utf-8")
                    log.info("[importer] Merged %d procedures", procedure_count)
            except Exception as e:
                warnings.append(f"Couldn't register procedures: {e}")

        # Queue philosopher prompt for next session
        phil_file = agent_dir / "philosopher_prompt.md"
        if phil_file.exists():
            inject_path = base_dir / "war_room_data" / f"injected_{agent_name}_prompt.md"
            inject_path.write_bytes(phil_file.read_bytes())
            log.info("[importer] Queued philosopher prompt for injection")

        # Write agent metadata
        meta = {
            "name": agent_name,
            "version": version,
            "description": manifest.get("description", ""),
            "installed_files": installed_files,
            "procedure_count": procedure_count,
            "source": "marketplace",
        }
        (agent_dir / "agent_meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

    except Exception as e:
        return {"ok": False, "errors": [str(e)]}

    log.info("[importer] Installed agent '%s' v%s (%d files, %d procedures)",
             agent_name, version, len(installed_files), procedure_count)

    return {
        "ok": True,
        "agent_name": agent_name,
        "version": version,
        "files_installed": len(installed_files),
        "procedures_registered": procedure_count,
        "warnings": warnings,
        "path": str(agent_dir),
    }


def list_agents(base_dir: Path) -> list:
    """List all installed agents."""
    agents_dir = base_dir / "agents"
    if not agents_dir.exists():
        return []

    agents = []
    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        meta_file = agent_dir / "agent_meta.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                agents.append(meta)
            except Exception:
                agents.append({"name": agent_dir.name, "version": "unknown"})
        else:
            agents.append({"name": agent_dir.name, "version": "unknown"})

    return agents
