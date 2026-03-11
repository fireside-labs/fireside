"""
socratic plugin — Structured multi-perspective debate engine.

NEW in V2 (no V1 source). The Socratic Review system.

NOT binary PASS/FAIL — structured multi-round deliberation.
Reviewers are *personas*, not nodes. Same agent can wear different hats.

Debate protocol:
  Round 1: Each reviewer critiques independently (parallel)
  Round 2: Original agent responds — defends or accepts
  Round 3: Reviewers respond to defenses — still object or concede
  After N rounds: score consensus. Threshold met → advance. Not → revise/escalate.

Works at every scale:
  Solo (1 machine): Same model, 3 personas = 3 system-prompt passes
  Power user (2-3 machines): Different local models, different hats
  Enterprise: Different cloud models per reviewer
"""
from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger("valhalla.socratic")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_BASE_DIR = Path(".")
_MODEL_PROVIDERS: dict = {}
_ROUTING: dict = {}

# Active debates: {debate_id: debate_state}
_debates: dict[str, dict] = {}


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


def _call_model(prompt: str, system: str = "",
                model_ref: str = "local/default", timeout: int = 60) -> Optional[str]:
    """Call a model with a specific system prompt (for persona)."""
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
            "max_tokens": 1000,
            "temperature": 0.7,
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
        log.debug("[socratic] Model call failed: %s", e)
        return None


def _debate_dir() -> Path:
    d = _BASE_DIR / "war_room_data" / "debates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_debate(debate_id: str, state: dict) -> None:
    path = _debate_dir() / f"{debate_id}.json"
    path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def _load_debate(debate_id: str) -> Optional[dict]:
    path = _debate_dir() / f"{debate_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return _debates.get(debate_id)


# ---------------------------------------------------------------------------
# Debate engine
# ---------------------------------------------------------------------------

def start_debate(content: str, content_type: str, reviewers: list,
                 rounds: int = 3, consensus_threshold: float = 0.7) -> dict:
    """Start a structured debate.

    Args:
        content: The content to debate (code, spec, strategy, etc.)
        content_type: Label for the content type
        reviewers: List of reviewer configs:
            [{"persona": "architect", "model": "cloud/glm-5",
              "prompt": "Review as a senior architect..."}]
        rounds: Number of debate rounds (default 3)
        consensus_threshold: % agreement to pass (0-1)
    """
    debate_id = f"debate_{uuid.uuid4().hex[:8]}"

    state = {
        "id": debate_id,
        "content": content,
        "content_type": content_type,
        "reviewers": reviewers,
        "rounds": rounds,
        "consensus_threshold": consensus_threshold,
        "current_round": 0,
        "status": "active",
        "transcript": [],
        "scores": {},  # {persona: score}
        "created_at": int(time.time()),
    }

    _debates[debate_id] = state

    _publish("debate.started", {
        "debate_id": debate_id,
        "content_type": content_type,
        "reviewers": len(reviewers),
        "rounds": rounds,
    })

    # Run Round 1: Independent critiques
    _run_round(debate_id, state, 1)

    return state


def _run_round(debate_id: str, state: dict, round_num: int) -> None:
    """Execute a debate round."""
    state["current_round"] = round_num
    content = state["content"]

    if round_num == 1:
        # Round 1: Each reviewer critiques independently
        for reviewer in state["reviewers"]:
            persona = reviewer.get("persona", "reviewer")
            model = reviewer.get("model", "local/default")
            system = reviewer.get("prompt", f"You are a {persona}. Review critically.")

            prompt = (
                f"Review the following {state['content_type']}:\n\n"
                f"{content[:3000]}\n\n"
                f"Provide your critique. Be specific. End with:\n"
                f"SCORE: <0-10> (10 = excellent, 0 = terrible)\n"
                f"VERDICT: APPROVE or OBJECT\n"
                f"If OBJECT, explain what must change."
            )

            response = _call_model(prompt, system=system, model_ref=model)

            entry = {
                "round": round_num,
                "persona": persona,
                "model": model,
                "type": "critique",
                "content": response or "(no response — model unavailable)",
                "ts": int(time.time()),
            }
            state["transcript"].append(entry)

            # Parse score
            if response:
                score_match = re.search(r"SCORE:\s*(\d+)", response)
                if score_match:
                    state["scores"][persona] = int(score_match.group(1))

    elif round_num == 2:
        # Round 2: Author responds to critiques
        critiques = [t for t in state["transcript"] if t["round"] == 1]
        critique_text = "\n\n".join(
            f"**{c['persona']}**: {c['content'][:500]}" for c in critiques
        )

        prompt = (
            f"You created this {state['content_type']}:\n\n"
            f"{content[:2000]}\n\n"
            f"The reviewers had these critiques:\n\n{critique_text}\n\n"
            f"Respond to each critique. For each: defend your choice OR accept and propose a fix.\n"
            f"End with REVISED: yes/no"
        )

        response = _call_model(prompt, model_ref=state["reviewers"][0].get("model", "local/default"))
        state["transcript"].append({
            "round": round_num,
            "persona": "author",
            "type": "defense",
            "content": response or "(no response)",
            "ts": int(time.time()),
        })

    elif round_num >= 3:
        # Round 3+: Reviewers respond to defense
        defense = next(
            (t for t in reversed(state["transcript"]) if t["type"] == "defense"), None
        )
        defense_text = defense["content"][:1000] if defense else ""

        for reviewer in state["reviewers"]:
            persona = reviewer.get("persona", "reviewer")
            model = reviewer.get("model", "local/default")
            system = reviewer.get("prompt", f"You are a {persona}.")

            prompt = (
                f"The author responded to your critique:\n\n{defense_text}\n\n"
                f"Do you concede or still object?\n"
                f"VERDICT: CONCEDE or STILL_OBJECT\n"
                f"SCORE: <0-10>"
            )

            response = _call_model(prompt, system=system, model_ref=model)
            state["transcript"].append({
                "round": round_num,
                "persona": persona,
                "type": "response",
                "content": response or "(no response)",
                "ts": int(time.time()),
            })

            if response:
                score_match = re.search(r"SCORE:\s*(\d+)", response)
                if score_match:
                    state["scores"][persona] = int(score_match.group(1))

    # Check consensus
    _evaluate_consensus(debate_id, state)

    _publish("debate.round_complete", {
        "debate_id": debate_id,
        "round": round_num,
        "scores": state["scores"],
    })

    _save_debate(debate_id, state)


def _evaluate_consensus(debate_id: str, state: dict) -> None:
    """Check if consensus has been reached."""
    scores = state["scores"]
    if not scores:
        return

    # Consensus = average score >= threshold * 10
    avg = sum(scores.values()) / len(scores)
    threshold = state["consensus_threshold"] * 10

    if avg >= threshold:
        state["status"] = "consensus"
        state["consensus_score"] = round(avg, 1)
        _publish("debate.consensus", {
            "debate_id": debate_id, "score": round(avg, 1),
        })
    elif state["current_round"] >= state["rounds"]:
        state["status"] = "deadlock"
        state["consensus_score"] = round(avg, 1)
        _publish("debate.deadlock", {
            "debate_id": debate_id, "score": round(avg, 1),
        })


def intervene(debate_id: str, objection: str) -> dict:
    """Human intervenes in a debate with their own objection."""
    state = _load_debate(debate_id)
    if not state:
        return {"ok": False, "reason": "Debate not found"}

    state["transcript"].append({
        "round": state["current_round"],
        "persona": "human",
        "type": "intervention",
        "content": objection,
        "ts": int(time.time()),
    })

    state["status"] = "active"  # Resume after intervention
    _debates[debate_id] = state
    _save_debate(debate_id, state)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class DebateRequest(BaseModel):
    content: str
    content_type: str = "code"
    reviewers: list = []
    rounds: int = 3
    consensus_threshold: float = 0.7


class InterveneRequest(BaseModel):
    objection: str


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _BASE_DIR, _MODEL_PROVIDERS, _ROUTING

    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _MODEL_PROVIDERS = config.get("models", {}).get("providers", {})
    _ROUTING = config.get("model_router", {}).get("routing", {})

    router = APIRouter(tags=["socratic"])

    @router.post("/api/v1/socratic/debate")
    async def api_start_debate(req: DebateRequest):
        # Default reviewers if none provided
        reviewers = req.reviewers or [
            {"persona": "architect", "model": "local/default",
             "prompt": "Review as a senior architect. Focus on scalability."},
            {"persona": "devil_advocate", "model": "local/default",
             "prompt": "Attack every assumption. What breaks in 6 months?"},
            {"persona": "end_user", "model": "local/default",
             "prompt": "You are a non-technical user. What's confusing?"},
        ]
        state = start_debate(
            content=req.content,
            content_type=req.content_type,
            reviewers=reviewers,
            rounds=req.rounds,
            consensus_threshold=req.consensus_threshold,
        )
        return {"debate_id": state["id"], "status": state["status"]}

    @router.get("/api/v1/socratic/debate/{debate_id}")
    async def api_get_debate(debate_id: str):
        state = _load_debate(debate_id)
        if not state:
            raise HTTPException(status_code=404, detail="Debate not found")
        return {
            "id": state["id"],
            "status": state["status"],
            "content_type": state.get("content_type"),
            "current_round": state.get("current_round", 0),
            "total_rounds": state.get("rounds", 3),
            "scores": state.get("scores", {}),
            "consensus_score": state.get("consensus_score"),
            "transcript_entries": len(state.get("transcript", [])),
        }

    @router.get("/api/v1/socratic/debate/{debate_id}/transcript")
    async def api_get_transcript(debate_id: str):
        state = _load_debate(debate_id)
        if not state:
            raise HTTPException(status_code=404, detail="Debate not found")
        return {"transcript": state.get("transcript", [])}

    @router.post("/api/v1/socratic/debate/{debate_id}/intervene")
    async def api_intervene(debate_id: str, req: InterveneRequest):
        return intervene(debate_id, req.objection)

    app.include_router(router)
    log.info("[socratic] Plugin loaded. Debate engine ready.")
