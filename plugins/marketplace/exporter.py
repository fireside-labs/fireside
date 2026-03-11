"""
marketplace/exporter.py — Package an agent as a .valhalla zip.

Exports:
  manifest.yaml      — name, description, version, model requirements, price
  SOUL.md             — evolved soul file
  IDENTITY.md         — agent identity
  procedures.json     — crucible-tested, high-confidence procedures only
  philosopher_prompt.md — distilled wisdom prompt
  personality.json    — evolved personality traits
  config_fragment.yaml — plugin requirements + model preferences

Strips private data: API keys, IPs, user info.
"""
from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from pathlib import Path
from typing import Optional

log = logging.getLogger("valhalla.marketplace.exporter")

# Patterns to strip from exported files
_PRIVATE_PATTERNS = [
    (re.compile(r'(api[_-]?key|token|secret|password)\s*[:=]\s*\S+', re.IGNORECASE), r'\1: ***REDACTED***'),
    (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '0.0.0.0'),
    (re.compile(r'(NVIDIA_API_KEY|OLLAMA_EMBED_BASE)\s*[:=]\s*\S+', re.IGNORECASE), r'\1: ***REDACTED***'),
    (re.compile(r'\$\{[A-Z_]+\}'), '${REDACTED}'),
]


def _strip_private(text: str) -> str:
    """Remove API keys, IPs, and environment variable references."""
    for pattern, replacement in _PRIVATE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _simple_yaml_dump(data: dict, indent: int = 0) -> str:
    """Minimal YAML serializer (no PyYAML dependency)."""
    lines = []
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_simple_yaml_dump(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    first = True
                    for k, v in item.items():
                        if first:
                            lines.append(f"{prefix}  - {k}: {v}")
                            first = False
                        else:
                            lines.append(f"{prefix}    {k}: {v}")
                else:
                    lines.append(f"{prefix}  - {item}")
        elif value is None:
            lines.append(f"{prefix}{key}:")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines)


def _read_file_safe(path: Path) -> Optional[str]:
    """Read a file, returning None if it doesn't exist."""
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        pass
    return None


def _fetch_procedures(base_dir: Path, min_confidence: float = 0.7) -> list:
    """Load procedures and filter by confidence."""
    proc_file = base_dir / "war_room_data" / "procedures.json"
    if not proc_file.exists():
        return []

    try:
        procedures = json.loads(proc_file.read_text(encoding="utf-8"))
        if isinstance(procedures, list):
            return [
                p for p in procedures
                if p.get("confidence", 0) >= min_confidence
            ]
        elif isinstance(procedures, dict):
            filtered = {}
            for key, proc in procedures.items():
                if isinstance(proc, dict) and proc.get("confidence", 0) >= min_confidence:
                    filtered[key] = proc
            return filtered if filtered else []
    except Exception:
        return []


def export_agent(
    agent_name: str,
    base_dir: Path,
    soul_config: dict,
    version: str = "1.0.0",
    description: str = "",
    model_requirements: Optional[dict] = None,
    price: float = 0.0,
    min_confidence: float = 0.7,
) -> Optional[bytes]:
    """Export an agent as a .valhalla zip package.

    Returns the zip file as bytes, or None on failure.
    """
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. manifest.yaml
        manifest = {
            "name": agent_name,
            "version": version,
            "description": description or f"Exported agent: {agent_name}",
            "model_requirements": model_requirements or {
                "min_ram_gb": 8,
                "gpu_recommended": True,
                "min_context": 4096,
            },
            "price": price,
            "format_version": "1.0",
            "exported_by": "valhalla-mesh-v2",
        }
        zf.writestr("manifest.yaml", _simple_yaml_dump(manifest))

        # 2. SOUL.md
        soul_path = soul_config.get("personality", "")
        if soul_path:
            content = _read_file_safe(base_dir / soul_path)
            if content:
                zf.writestr("SOUL.md", _strip_private(content))

        # 3. IDENTITY.md
        identity_path = soul_config.get("identity", "")
        if identity_path:
            content = _read_file_safe(base_dir / identity_path)
            if content:
                zf.writestr("IDENTITY.md", _strip_private(content))

        # 4. procedures.json — only high-confidence, crucible-tested
        procedures = _fetch_procedures(base_dir, min_confidence)
        if procedures:
            proc_json = json.dumps(procedures, indent=2, default=str)
            zf.writestr("procedures.json", _strip_private(proc_json))

        # 5. philosopher_prompt.md
        phil_path = base_dir / "war_room_data" / "philosopher_prompt.md"
        content = _read_file_safe(phil_path)
        if content:
            zf.writestr("philosopher_prompt.md", _strip_private(content))

        # 6. personality.json
        personality_path = base_dir / "war_room_data" / "personality_traits.json"
        content = _read_file_safe(personality_path)
        if content:
            zf.writestr("personality.json", _strip_private(content))

        # 7. config_fragment.yaml — plugin requirements + model preferences
        config_fragment = {
            "required_plugins": [
                "pipeline", "crucible", "personality",
                "philosopher-stone", "belief-shadows",
            ],
            "recommended_model": "local/default",
        }
        zf.writestr("config_fragment.yaml", _simple_yaml_dump(config_fragment))

    result = buf.getvalue()
    log.info("[exporter] Exported %s: %d bytes", agent_name, len(result))
    return result
