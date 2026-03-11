"""
context-compactor/handler.py — Automatic context compaction.

During long firesides, monitor token count.
When context exceeds 75% of window:
  - Summarize earlier messages into a compressed block
  - Replace message history with: [Compressed: 47 messages] + last 10 messages

User sees full history in UI, but brain gets compressed version.
Enables 2+ hour conversations without hitting limits.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.context-compactor")


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return max(1, len(text) // 4)


def estimate_messages_tokens(messages: list[dict]) -> int:
    """Estimate total tokens across all messages."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        total += estimate_tokens(content) + 4  # role overhead
    return total


# ---------------------------------------------------------------------------
# Compaction logic
# ---------------------------------------------------------------------------

DEFAULT_CONTEXT_WINDOW = 8192
COMPACT_THRESHOLD = 0.75  # Trigger compaction at 75%
KEEP_RECENT = 10  # Keep last N messages uncompressed


def summarize_messages(messages: list[dict]) -> str:
    """Create a compressed summary of message history.

    Uses extractive summarization (key points from each message).
    For full abstractive summary, would use the brain itself.
    """
    if not messages:
        return ""

    # Group by topic/turn
    key_points = []
    for msg in messages:
        content = msg.get("content", "").strip()
        role = msg.get("role", "unknown")
        if not content:
            continue

        # Extract first meaningful sentence as summary
        sentences = re.split(r'[.!?\n]', content)
        summary = next((s.strip() for s in sentences if len(s.strip()) > 10), content[:100])

        if role == "user":
            key_points.append(f"User asked: {summary}")
        elif role == "assistant":
            # For assistant, grab key action/answer
            if len(content) > 200:
                key_points.append(f"AI: {summary}...")
            else:
                key_points.append(f"AI: {summary}")

    return "\n".join(key_points)


def compact(
    messages: list[dict],
    context_window: int = DEFAULT_CONTEXT_WINDOW,
    keep_recent: int = KEEP_RECENT,
) -> dict:
    """Compact message history if needed.

    Returns:
        - compacted: bool — whether compaction was performed
        - messages: list — the (possibly compacted) messages
        - stats: dict — token counts before/after
    """
    system_msgs = [m for m in messages if m.get("role") == "system"]
    chat_msgs = [m for m in messages if m.get("role") != "system"]

    total_tokens = estimate_messages_tokens(messages)
    threshold_tokens = int(context_window * COMPACT_THRESHOLD)

    if total_tokens < threshold_tokens or len(chat_msgs) <= keep_recent:
        return {
            "compacted": False,
            "messages": messages,
            "stats": {
                "total_tokens": total_tokens,
                "threshold_tokens": threshold_tokens,
                "message_count": len(messages),
            },
        }

    # Split: old messages to compress + recent to keep
    old_msgs = chat_msgs[:-keep_recent]
    recent_msgs = chat_msgs[-keep_recent:]

    # Create compressed summary
    summary = summarize_messages(old_msgs)
    compressed_count = len(old_msgs)

    compressed_block = {
        "role": "system",
        "content": (
            f"[Compressed: {compressed_count} earlier messages]\n"
            f"Key topics discussed:\n{summary}"
        ),
    }

    # Rebuild: system + compressed + recent
    compacted_messages = system_msgs + [compressed_block] + recent_msgs

    after_tokens = estimate_messages_tokens(compacted_messages)

    _publish("context.compacted", {
        "compressed_count": compressed_count,
        "tokens_before": total_tokens,
        "tokens_after": after_tokens,
        "savings_pct": round((1 - after_tokens / max(total_tokens, 1)) * 100),
    })

    log.info("[context-compactor] Compressed %d messages. %d → %d tokens (%.0f%% savings)",
             compressed_count, total_tokens, after_tokens,
             (1 - after_tokens / max(total_tokens, 1)) * 100)

    return {
        "compacted": True,
        "messages": compacted_messages,
        "stats": {
            "total_tokens_before": total_tokens,
            "total_tokens_after": after_tokens,
            "messages_compressed": compressed_count,
            "messages_kept": len(recent_msgs),
            "savings_pct": round((1 - after_tokens / max(total_tokens, 1)) * 100),
        },
    }


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CompactRequest(BaseModel):
    messages: list[dict]
    context_window: int = DEFAULT_CONTEXT_WINDOW
    keep_recent: int = KEEP_RECENT


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    router = APIRouter(tags=["context-compactor"])

    @router.post("/api/v1/context/compact")
    async def api_compact(req: CompactRequest):
        """Compact conversation context if needed."""
        result = compact(req.messages, req.context_window, req.keep_recent)
        return result

    app.include_router(router)
    log.info("[context-compactor] Plugin loaded. Window: %d, threshold: %.0f%%",
             DEFAULT_CONTEXT_WINDOW, COMPACT_THRESHOLD * 100)
