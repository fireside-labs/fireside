"""
lesson-distiller plugin — Extracts reusable lessons from completed pipelines.

After a pipeline completes, this plugin:
  1. Takes the full pipeline transcript (all stage outputs, iterations, feedback)
  2. Calls a local model to extract 2-5 concise, reusable lessons
  3. Stores each lesson in working memory with high importance
  4. Emits 'lesson.distilled' for the dashboard

Two modes:
  - Quick extract: runs immediately after pipeline (~30s, 3-5 key points)
  - Deep overnight: batch all pipelines from today, distill at 2 AM

NEW in V2. Closes the learning loop: next pipeline starts smarter.
"""
from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.lesson_distiller")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_BASE_DIR = Path(".")
_MODEL_PROVIDERS: dict = {}
_MAX_LESSONS = 5
_MIN_IMPORTANCE = 0.6

# In-memory lesson store (also persisted to working memory)
_recent_lessons: list[dict] = []
_MAX_RECENT = 50


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


def _call_model(prompt: str, system: str = "",
                model_ref: str = "local/default", timeout: int = 90) -> Optional[str]:
    """Call a model for lesson extraction."""
    if "/" in model_ref:
        provider_key, model_name = model_ref.split("/", 1)
    else:
        provider_key = "llama"
        model_name = model_ref

    provider = _MODEL_PROVIDERS.get(provider_key, {})
    url = provider.get("url", "http://127.0.0.1:8080/v1")

    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "model": model_name,
            "messages": messages,
            "max_tokens": 800,
            "temperature": 0.3,  # low temp for structured extraction
        }).encode()

        req = urllib.request.Request(
            f"{url.rstrip('/')}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        key = provider.get("key", "")
        if key and key != "local" and not key.startswith("$"):
            req.add_header("Authorization", f"Bearer {key}")

        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.debug("[lesson-distiller] Model call failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Core distillation logic
# ---------------------------------------------------------------------------

DISTILLER_SYSTEM = """You are a lesson distiller. Given a pipeline transcript
(stages, outputs, failures, fixes), extract 2-5 reusable lessons.

Output EXACTLY this JSON format, nothing else:
{
  "lessons": [
    {
      "lesson": "One concise sentence describing what was learned",
      "domain": "coding|research|writing|analysis|general",
      "importance": 0.7,
      "tags": ["relevant", "keywords"]
    }
  ]
}

Focus on:
- What went wrong and how it was fixed
- Patterns that worked well
- Edge cases discovered
- Approaches that should be avoided next time

Keep lessons actionable and specific. Not "test your code" but
"JWT refresh endpoints need mutex locks to prevent race conditions."
"""


def distill_lessons(pipeline_id: str, transcript: list[dict],
                    template_name: str = "unknown",
                    task_summary: str = "") -> list[dict]:
    """Extract lessons from a pipeline transcript.

    Args:
        pipeline_id: The pipeline that completed
        transcript: List of iteration dicts from track_iteration()
        template_name: Which template was used
        task_summary: Brief description of the task

    Returns: List of extracted lessons
    """
    if not transcript:
        return []

    # Build condensed transcript for the model
    condensed = []
    for it in transcript:
        stage = it.get("stage", "?")
        verdict = it.get("verdict", "")
        output = it.get("output", "")[:500]
        rnd = it.get("round", 0)
        condensed.append(
            f"[Round {rnd} | Stage: {stage} | Verdict: {verdict}]\n{output}"
        )

    transcript_text = "\n\n---\n\n".join(condensed)

    prompt = (
        f"Pipeline: {task_summary[:200]}\n"
        f"Template: {template_name}\n"
        f"Total iterations: {len(transcript)}\n\n"
        f"--- TRANSCRIPT ---\n\n{transcript_text[:4000]}"
    )

    response = _call_model(prompt, system=DISTILLER_SYSTEM)
    if not response:
        log.warning("[lesson-distiller] No response from model")
        return []

    # Parse JSON from response
    lessons = _parse_lessons(response)

    # Store each lesson in working memory
    for lesson in lessons:
        _store_lesson(pipeline_id, lesson, template_name)

    _publish("lesson.distilled", {
        "pipeline_id": pipeline_id,
        "lessons_count": len(lessons),
        "template": template_name,
    })

    log.info("[lesson-distiller] Extracted %d lessons from pipeline %s",
             len(lessons), pipeline_id)

    return lessons


def _parse_lessons(response: str) -> list[dict]:
    """Parse structured lessons from model response."""
    # Try to extract JSON from response
    try:
        # Handle markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            # Try parsing entire response as JSON
            data = json.loads(response)

        raw_lessons = data.get("lessons", [])
        lessons = []
        for raw in raw_lessons[:_MAX_LESSONS]:
            lesson = {
                "lesson": str(raw.get("lesson", ""))[:200],
                "domain": str(raw.get("domain", "general")),
                "importance": min(1.0, max(0.0, float(raw.get("importance", 0.7)))),
                "tags": raw.get("tags", [])[:5],
                "ts": time.time(),
            }
            if lesson["importance"] >= _MIN_IMPORTANCE:
                lessons.append(lesson)
        return lessons
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        log.debug("[lesson-distiller] Parse failed: %s", e)
        return []


def _store_lesson(pipeline_id: str, lesson: dict, template: str) -> None:
    """Store lesson in working memory and local cache."""
    # Store in working memory via API
    try:
        content = (
            f"[LESSON from {template} pipeline {pipeline_id}] "
            f"{lesson['lesson']} "
            f"(domain: {lesson['domain']}, tags: {', '.join(lesson.get('tags', []))})"
        )

        payload = json.dumps({
            "content": content,
            "importance": lesson["importance"],
            "source": "lesson-distiller",
        }).encode()

        req = urllib.request.Request(
            "http://127.0.0.1:8765/api/v1/working-memory/observe",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        log.debug("[lesson-distiller] Failed to store in working memory: %s", e)

    # Local cache
    entry = {**lesson, "pipeline_id": pipeline_id, "template": template}
    _recent_lessons.append(entry)
    if len(_recent_lessons) > _MAX_RECENT:
        _recent_lessons.pop(0)

    _publish("lesson.stored", {
        "lesson": lesson["lesson"],
        "domain": lesson["domain"],
        "importance": lesson["importance"],
        "pipeline_id": pipeline_id,
    })


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class DistillRequest(BaseModel):
    pipeline_id: str
    transcript: list = []
    template_name: str = "unknown"
    task_summary: str = ""


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _BASE_DIR, _MODEL_PROVIDERS, _MAX_LESSONS, _MIN_IMPORTANCE

    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _MODEL_PROVIDERS = config.get("models", {}).get("providers", {})

    distiller_cfg = config.get("lesson_distiller", {})
    _MAX_LESSONS = distiller_cfg.get("max_lessons", 5)
    _MIN_IMPORTANCE = distiller_cfg.get("min_importance", 0.6)

    router = APIRouter(tags=["lesson-distiller"])

    @router.post("/api/v1/lessons/distill")
    async def api_distill(req: DistillRequest):
        """Trigger lesson extraction from a pipeline transcript."""
        lessons = distill_lessons(
            pipeline_id=req.pipeline_id,
            transcript=req.transcript,
            template_name=req.template_name,
            task_summary=req.task_summary,
        )
        return {
            "ok": True,
            "pipeline_id": req.pipeline_id,
            "lessons": lessons,
            "count": len(lessons),
        }

    @router.get("/api/v1/lessons/recent")
    async def api_recent(limit: int = 10):
        """Get recently extracted lessons."""
        return {
            "lessons": _recent_lessons[-limit:],
            "total": len(_recent_lessons),
        }

    app.include_router(router)
    log.info("[lesson-distiller] Plugin loaded. Ready to extract wisdom.")
""",
<parameter name="Complexity">7
