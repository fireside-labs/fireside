"""
explain.py — Freya's /explain endpoint.

Accepts a workspace file path, reads it, and returns a structured
code explanation using the local model.

Supports:
  POST /explain  { "path": "bot/bifrost.py", "focus": "security" }
  GET  /explain/info

Response:
  {
    "file": "bot/bifrost.py",
    "purpose": "...",
    "key_components": [...],
    "dependencies": [...],
    "risks": [...],
    "model_used": "qwen3.5:35b",
    "duration_ms": 4200
  }
"""

import json
import logging
import os
import time
import urllib.request
from pathlib import Path
from typing import Optional

log = logging.getLogger("war-room.explain")

OLLAMA_BASE = "http://127.0.0.1:11434"
EXPLAIN_TIMEOUT = 180   # large files may take a while
MAX_FILE_BYTES = 256 * 1024   # 256 KB — truncate if larger

_SYSTEM_PROMPT = """You are a senior software engineer doing a code review.
When given a file, you MUST respond with ONLY valid JSON in this exact structure:
{
  "purpose": "One sentence describing what this file does.",
  "key_components": ["List", "of", "main", "classes", "or", "functions"],
  "dependencies": ["External", "modules", "or", "services", "this", "relies", "on"],
  "risks": ["Potential", "issues", "or", "things", "to", "watch", "out", "for"],
  "summary": "2-3 sentence technical summary."
}
Do not include any text before or after the JSON."""

_FOCUS_PROMPTS = {
    "security": "Focus especially on security risks, injection points, authentication issues, and exposed secrets.",
    "performance": "Focus especially on bottlenecks, blocking calls, memory usage, and scalability concerns.",
    "architecture": "Focus especially on design patterns, coupling, separation of concerns, and extensibility.",
    "dependencies": "Focus especially on external dependencies, version pinning, and potential conflicts.",
}


class ExplainHandler:
    def __init__(self, agent_config: dict, workspace_root: Path):
        self.local_model = agent_config.get("local_model", "qwen3.5:35b")
        self.workspace_root = workspace_root

    def handle(self, body: dict) -> tuple:
        """
        POST /explain
        body: { "path": "bot/bifrost.py", "focus": "security" }  # focus optional
        Returns (status_code, response_dict)
        """
        rel_path = body.get("path", "").strip()
        if not rel_path:
            return 400, {"error": "path is required"}

        focus = body.get("focus", "").lower()

        # Resolve safely within workspace
        target = (self.workspace_root / rel_path.replace("/", os.sep)).resolve()
        try:
            target.relative_to(self.workspace_root.resolve())
        except ValueError:
            return 403, {"error": "path must be within workspace"}

        if not target.exists():
            return 404, {"error": f"file not found: {rel_path}"}
        if not target.is_file():
            return 400, {"error": "path must point to a file, not a directory"}

        raw = target.read_bytes()
        if len(raw) > MAX_FILE_BYTES:
            log.warning("File %s truncated from %d to %d bytes for explain", rel_path, len(raw), MAX_FILE_BYTES)
            raw = raw[:MAX_FILE_BYTES]

        try:
            content = raw.decode("utf-8", errors="replace")
        except Exception as e:
            return 400, {"error": f"could not decode file: {e}"}

        system = _SYSTEM_PROMPT
        if focus and focus in _FOCUS_PROMPTS:
            system += "\n\n" + _FOCUS_PROMPTS[focus]

        prompt = f"File: {rel_path}\n\n```\n{content}\n```"

        start = time.time()
        result = self._ask_local(prompt, system)
        elapsed_ms = int((time.time() - start) * 1000)

        if "error" in result:
            return 500, result

        # Parse the JSON response — strip <think>...</think> blocks first
        raw_text = result["response"]
        parsed = self._extract_json(raw_text)

        if parsed is None:
            return 200, {
                "file": rel_path,
                "raw_response": raw_text[:2000],
                "model_used": self.local_model,
                "duration_ms": elapsed_ms,
                "note": "model returned non-JSON response",
            }

        return 200, {
            "file": rel_path,
            "focus": focus or "general",
            **parsed,
            "model_used": self.local_model,
            "duration_ms": elapsed_ms,
        }

    def _extract_json(self, text: str):
        """Strip <think> blocks and extract the JSON object from model output."""
        import re
        # Remove <think>...</think> blocks (qwen3.5 reasoning)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Find first {...} block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None


    def _ask_local(self, prompt: str, system: str) -> dict:
        url = f"{OLLAMA_BASE}/api/chat"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        payload = {
            "model": self.local_model,
            "messages": messages,
            "stream": False,
            "think": False,   # disable qwen3.5 reasoning mode — we need clean JSON output
            "options": {"num_predict": 1024, "temperature": 0.1},
        }
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=EXPLAIN_TIMEOUT) as resp:
                result = json.loads(resp.read())
                return {
                    "response": result.get("message", {}).get("content", ""),
                    "model": self.local_model,
                }
        except Exception as e:
            log.error("Explain local inference failed: %s", e)
            return {"error": f"inference failed: {e}"}

    def info(self) -> dict:
        return {
            "model": self.local_model,
            "max_file_bytes": MAX_FILE_BYTES,
            "focus_modes": list(_FOCUS_PROMPTS.keys()),
            "workspace": str(self.workspace_root),
        }
