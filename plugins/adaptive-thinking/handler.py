"""
adaptive-thinking/handler.py — System 1/2 question classification.

Simple questions → fast, low-token response (max_tokens=256, temp=0.3)
Complex questions → full reasoning chain (max_tokens=2048, temp=0.7)

Classification heuristics:
  - Word count (short → simple)
  - Question type detection (yes/no, factual → simple)
  - Keyword complexity (analysis, compare, explain → complex)
  - Code/technical patterns (→ complex)
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.adaptive-thinking")

# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------

# Words that signal simple questions
SIMPLE_PATTERNS = [
    r"^(yes|no|ok|sure|thanks|thank you|hi|hello|hey)\b",
    r"^what (is|are|was|were)\b",
    r"^who (is|are|was|were)\b",
    r"^when (is|are|was|were|did)\b",
    r"^where (is|are|was|were)\b",
    r"^(is|are|was|were|do|does|did|can|will|would|should)\b",
    r"^how (much|many|old|long|far)\b",
    r"^(define|meaning of|what does .+ mean)\b",
]

# Words that signal complex questions
COMPLEX_KEYWORDS = [
    "compare", "contrast", "analyze", "explain why", "in detail",
    "step by step", "write a", "create a", "implement", "debug",
    "refactor", "design", "architecture", "trade-off", "pros and cons",
    "how would you", "what are the implications", "evaluate",
    "comprehensive", "thorough", "elaborate", "deep dive",
]

# Code-related patterns → always complex
CODE_PATTERNS = [
    r"```",
    r"function\s+\w+",
    r"def\s+\w+",
    r"class\s+\w+",
    r"import\s+\w+",
    r"\bsql\b.*\bquery\b",
    r"\bapi\b.*\bendpoint\b",
]

SIMPLE_COMPILED = [re.compile(p, re.IGNORECASE) for p in SIMPLE_PATTERNS]
COMPLEX_COMPILED = [re.compile(p, re.IGNORECASE) for p in CODE_PATTERNS]


def classify_question(text: str) -> dict:
    """Classify a question as System 1 (fast) or System 2 (deep)."""
    text_lower = text.lower().strip()
    word_count = len(text.split())
    score = 0.0  # 0 = simple, 1 = complex

    # Word count heuristic
    if word_count <= 5:
        score -= 0.3
    elif word_count <= 15:
        score -= 0.1
    elif word_count >= 50:
        score += 0.3
    elif word_count >= 25:
        score += 0.15

    # Simple pattern matching
    for pat in SIMPLE_COMPILED:
        if pat.search(text_lower):
            score -= 0.25
            break

    # Complex keyword matching
    for kw in COMPLEX_KEYWORDS:
        if kw in text_lower:
            score += 0.3
            break

    # Code patterns
    for pat in COMPLEX_COMPILED:
        if pat.search(text):
            score += 0.4
            break

    # Question mark density (multiple questions = complex)
    q_count = text.count("?")
    if q_count >= 3:
        score += 0.2
    elif q_count == 0 and word_count > 20:
        score += 0.1  # Long statement, probably a task

    # Clamp
    score = max(0.0, min(1.0, score + 0.5))

    system = 1 if score < 0.55 else 2

    if system == 1:
        config = {
            "max_tokens": 256,
            "temperature": 0.3,
            "label": "fast",
        }
    else:
        config = {
            "max_tokens": 2048,
            "temperature": 0.7,
            "label": "deep",
        }

    return {
        "system": system,
        "score": round(score, 3),
        "config": config,
        "word_count": word_count,
    }


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ClassifyRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    router = APIRouter(tags=["adaptive-thinking"])

    @router.post("/api/v1/thinking/classify")
    async def api_classify(req: ClassifyRequest):
        """Classify question complexity → inference parameters."""
        result = classify_question(req.message)
        return result

    app.include_router(router)
    log.info("[adaptive-thinking] Plugin loaded.")
