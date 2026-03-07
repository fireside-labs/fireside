"""
personality_cron.py — Weekly leaderboard-driven personality adjustment.

Reads /leaderboard from Odin, maps score patterns to personality parameter nudges,
applies P&L performance rank incentives (top/bottom performer autonomy adjustment),
and pushes updated personality.json to each node via POST /receive-files.

Run weekly via Windows Task Scheduler on Heimdall:
  python C:\\Users\\Jorda\\.openclaw\\workspace\\bot\\bot\\personality_cron.py
"""

import base64
import json
import logging
import sys
import time
import urllib.request
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("personality_cron")

BASE      = Path(__file__).parent
CFG       = json.loads((BASE / "config.json").read_text())
NODES     = CFG.get("nodes", {})
ODIN_IP   = NODES.get("odin", {}).get("ip", "100.105.27.121")
ODIN_PORT = NODES.get("odin", {}).get("port", 8765)

PERSONALITY_FILE = BASE / "personality.json"

# ---------------------------------------------------------------------------
# Leaderboard → personality mapping rules
# ---------------------------------------------------------------------------

_RULES = [
    # High whistleblower activity → more skeptical
    {
        "event":     "tattle",
        "condition": lambda count: count >= 3,
        "adjustments": {"skepticism": +0.05, "caution": +0.03},
        "label": "consistent_whistleblower",
    },
    # High task:complete rate → faster, more autonomous
    {
        "event":     "task:complete",
        "condition": lambda count: count >= 5,
        "adjustments": {"speed": +0.05, "autonomy": +0.03},
        "label": "high_task_complete",
    },
    # Many ideas/sparks → more creative
    {
        "event":     "idea:spark",
        "condition": lambda count: count >= 3,
        "adjustments": {"creativity": +0.05},
        "label": "high_idea_rate",
    },
    # Many errors → less autonomous, more cautious
    {
        "event":     "node:error",
        "condition": lambda count: count >= 3,
        "adjustments": {"autonomy": -0.05, "caution": +0.05},
        "label": "high_error_rate",
    },
    # Memory syncs → reward with speed
    {
        "event":     "memory:synced",
        "condition": lambda count: count >= 5,
        "adjustments": {"speed": +0.03, "accuracy": +0.02},
        "label": "high_memory_sync",
    },
]

_NUDGE_LIMIT = 0.15
_PARAM_MIN   = 0.1
_PARAM_MAX   = 0.95
_RANK_AUTONOMY_BONUS  = 0.05   # top performer gains
_RANK_AUTONOMY_PENALTY = 0.05  # bottom performer loses


def _clamp(v: float) -> float:
    return max(_PARAM_MIN, min(_PARAM_MAX, round(v, 3)))


# ---------------------------------------------------------------------------
# Leaderboard fetch
# ---------------------------------------------------------------------------

def fetch_leaderboard() -> list[dict]:
    url = f"http://{ODIN_IP}:{ODIN_PORT}/leaderboard"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("leaderboard", [])
    except Exception as e:
        log.error("Could not fetch leaderboard from Odin: %s", e)
        return []


# ---------------------------------------------------------------------------
# Performance Rank (P&L incentives) — Task 2
# ---------------------------------------------------------------------------

def _compute_performance_ranks(leaderboard: list[dict]) -> dict[str, int]:
    """Rank agents by total leaderboard score. Returns {agent: rank} (1=best)."""
    scored = []
    for entry in leaderboard:
        agent = entry.get("agent", "")
        score = entry.get("score", entry.get("total", 0))
        if agent:
            scored.append((agent, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return {agent: (i + 1) for i, (agent, _) in enumerate(scored)}


def apply_performance_incentives(
    personality: dict,
    leaderboard: list[dict],
    adjustments: dict,
) -> dict:
    """Apply P&L rank-based autonomy incentives. Top performer +0.05, bottom -0.05."""
    if len(leaderboard) < 2:
        return adjustments   # need at least 2 agents to rank

    ranks = _compute_performance_ranks(leaderboard)
    agents_cfg = personality.get("agents", {})
    top_agent    = min(ranks, key=ranks.get)
    bottom_agent = max(ranks, key=ranks.get)
    n = len(ranks)

    log.info("[rank] Top: %s (#1/%d) | Bottom: %s (#%d/%d)",
             top_agent, n, bottom_agent, n, n)

    for agent, rank in ranks.items():
        if agent not in agents_cfg:
            continue
        current = adjustments.get(agent, dict(agents_cfg[agent]))
        incentive_note = None

        if agent == top_agent:
            current["autonomy"] = _clamp(current.get("autonomy", 0.5) + _RANK_AUTONOMY_BONUS)
            current["performance_rank"] = rank
            incentive_note = f"Top performer (rank 1/{n}) — autonomy increased"
            log.info("[rank] %s TOP → autonomy +%.2f", agent, _RANK_AUTONOMY_BONUS)

        elif agent == bottom_agent and n >= 3:  # only penalize if 3+ agents
            current["autonomy"] = _clamp(current.get("autonomy", 0.5) - _RANK_AUTONOMY_PENALTY)
            current["performance_rank"] = rank
            incentive_note = f"Bottom performer (rank {n}/{n}) — autonomy decreased, more oversight"
            log.info("[rank] %s BOTTOM → autonomy -%.2f", agent, _RANK_AUTONOMY_PENALTY)
        else:
            current["performance_rank"] = rank

        # Inject P&L stakeholder directive into personality
        current["stakeholder_directive"] = (
            "Your physical resources are tied to mesh performance. "
            "Top performers earn more autonomy. Poor performers get constrained."
        )
        if incentive_note:
            current["rank_note"] = incentive_note
        adjustments[agent] = current

    return adjustments



# ---------------------------------------------------------------------------
# Personality computation
# ---------------------------------------------------------------------------

def compute_adjustments(leaderboard: list[dict]) -> dict[str, dict]:
    """Returns ({agent: updated_params}, personality_dict) for agents with changes."""
    personality = json.loads(PERSONALITY_FILE.read_text())
    agents_cfg  = personality.get("agents", {})
    adjustments = {}

    for entry in leaderboard:
        agent     = entry.get("agent", "")
        breakdown = entry.get("breakdown", {})
        if not agent or agent not in agents_cfg:
            continue

        current = deepcopy(agents_cfg[agent])
        deltas: dict[str, float] = {}

        for rule in _RULES:
            event_count = breakdown.get(rule["event"], 0)
            if rule["condition"](event_count):
                log.info("[%s] Rule '%s' triggered (count=%d)", agent, rule["label"], event_count)
                for param, delta in rule["adjustments"].items():
                    deltas[param] = deltas.get(param, 0.0) + delta

        if not deltas:
            continue

        # Apply nudges with clamping
        updated = dict(current)
        for param, delta in deltas.items():
            if param in updated and isinstance(updated[param], (int, float)):
                clamped_delta = max(-_NUDGE_LIMIT, min(_NUDGE_LIMIT, delta))
                updated[param] = _clamp(updated[param] + clamped_delta)
                log.info("[%s] %s: %.3f → %.3f (delta %.3f)",
                         agent, param, current[param], updated[param], clamped_delta)

        adjustments[agent] = updated

    return adjustments, personality


# ---------------------------------------------------------------------------
# Push to nodes
# ---------------------------------------------------------------------------

def push_to_node(node_name: str, info: dict, personality_bytes: bytes) -> bool:
    ip   = info.get("ip")
    port = info.get("port", 8765)
    if not ip:
        return False

    dst_path = (
        r"C:\Users\Jorda\.openclaw\workspace\bot\bot"
        if sys.platform == "win32"
        else "/Users/Jorda/.openclaw/workspace/bot/bot"
    )

    payload = json.dumps({
        "dst_path":  dst_path,
        "filename":  "personality.json",
        "data_b64":  base64.b64encode(personality_bytes).decode(),
        "from":      "heimdall",
    }).encode()

    url = f"http://{ip}:{port}/receive-files"
    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            log.info("Pushed personality.json to %s: %s", node_name, result)
            return True
    except Exception as e:
        log.warning("Could not push to %s: %s", node_name, e)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=== Personality Cron starting ===")
    leaderboard = fetch_leaderboard()
    if not leaderboard:
        log.warning("No leaderboard data — skipping adjustments (Thor event-log may be unreachable)")
        return

    adjustments, personality = compute_adjustments(leaderboard)

    # Apply P&L performance rank incentives (Task 2)
    adjustments = apply_performance_incentives(personality, leaderboard, adjustments)

    if not adjustments:
        log.info("No personality changes warranted this week.")
    else:
        for agent, params in adjustments.items():
            personality["agents"][agent] = params
        personality["_meta"]["updated"]    = datetime.now(timezone.utc).date().isoformat()
        personality["_meta"]["updated_by"] = "heimdall"
        personality["_meta"]["version"]   += 1
        log.info("Updated %d agent(s): %s", len(adjustments), list(adjustments.keys()))

    out_bytes = json.dumps(personality, indent=2).encode()
    PERSONALITY_FILE.write_bytes(out_bytes)
    log.info("Wrote %d bytes to %s", len(out_bytes), PERSONALITY_FILE)

    pushed, failed = 0, 0
    for name, info in NODES.items():
        if push_to_node(name, info, out_bytes):
            pushed += 1
        else:
            failed += 1

    log.info("Push complete: %d ok, %d failed", pushed, failed)
    log.info("=== Personality Cron done ===")


if __name__ == "__main__":
    main()
