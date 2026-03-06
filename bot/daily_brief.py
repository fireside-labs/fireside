"""
daily_brief.py — Morning summary of war room activity across all nodes.
Run via cron at 7am on Odin:
    0 7 * * * /usr/bin/python3 /Users/odin/.openclaw/workspace/bot/bot/daily_brief.py
Windows Task Scheduler on other nodes:
    python C:\\Users\\Jorda\\.openclaw\\workspace\\bot\\bot\\daily_brief.py
"""

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE = Path(__file__).parent
CONFIG = json.loads((BASE / "config.json").read_text())

BOT_TOKEN = CONFIG["telegram_bot_token"]
CHAT_ID   = CONFIG["telegram_chat_id"]
NODES     = CONFIG.get("nodes", {})
THIS_NODE = CONFIG.get("this_node", "odin")

TIMEOUT = 6  # seconds per node


def fetch_summary(name: str, info: dict) -> Optional[dict]:
    url = f"http://{info['ip']}:{info.get('port', 8765)}/war-room/summary"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }).encode()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def main():
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%A, %b %-d")

    lines = [f"☀️ *Morning Brief — {date_str}*\n"]

    total_msgs = 0
    total_active = 0
    total_blocked = 0

    for name, info in NODES.items():
        summary = fetch_summary(name, info)
        if summary is None:
            lines.append(f"🔴 *{name.capitalize()}* — offline")
            continue

        msgs     = summary.get("total_messages", 0)
        active   = summary.get("active_tasks", 0)
        blocked  = summary.get("blocked_tasks", 0)
        done     = summary.get("done_tasks", 0)
        agents   = summary.get("active_agents", {})

        total_msgs    += msgs
        total_active  += active
        total_blocked += blocked

        status_icon = "🟡" if blocked > 0 else "🟢"
        agent_str = ", ".join(f"{a}({c})" for a, c in agents.items()) or "quiet"

        lines.append(
            f"{status_icon} *{name.capitalize()}*\n"
            f"  Messages: {msgs}  ·  Active: {active}  ·  Blocked: {blocked}  ·  Done: {done}\n"
            f"  Active agents: {agent_str}"
        )

    # Summary footer
    lines.append(
        f"\n📊 *Mesh totals* — {total_msgs} msgs  ·  "
        f"{total_active} active tasks  ·  "
        f"{total_blocked} blocked"
    )

    if total_blocked > 0:
        lines.append(f"\n⚠️ *{total_blocked} task(s) are blocked — check the board.*")

    message = "\n".join(lines)
    send_telegram(message)
    print(f"Brief sent at {now.isoformat()}")


if __name__ == "__main__":
    main()
