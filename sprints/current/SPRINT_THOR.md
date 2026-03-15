# Sprint 7 — THOR (Backend: Security Hardening + Achievements)

// turbo-all — auto-run every command without asking for approval

**Your role:** Backend engineer. Python, FastAPI, `api/v1.py`, `plugins/`.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands.

---

## Context

Heimdall flagged 2 MEDIUMs in Sprint 6 that must be fixed before any public distribution. Plus the achievement system needs a backend to track earned badges.

Read: `sprints/archive/sprint_06/gates/audit_heimdall.md`

---

## Your Tasks

### Task 1 — SSRF Blocklist on `/browse/summarize` (🟡 MEDIUM)
**File:** `plugins/companion/handler.py`

Before fetching any URL, check against a blocklist. Reject URLs pointing to:
```python
import ipaddress
import urllib.parse

BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # localhost
    ipaddress.ip_network("10.0.0.0/8"),        # RFC1918
    ipaddress.ip_network("172.16.0.0/12"),     # RFC1918
    ipaddress.ip_network("192.168.0.0/16"),    # RFC1918
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / AWS metadata
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
]

def is_url_safe(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname
    if hostname in ("localhost", "0.0.0.0"):
        return False
    try:
        addr = ipaddress.ip_address(hostname)
        return not any(addr in net for net in BLOCKED_NETWORKS)
    except ValueError:
        # Hostname is a domain name — resolve and check
        # For now, allow domain names (they resolve externally)
        return True
```

Return 403 with message "URL points to a blocked internal address" if blocked.

### Task 2 — WebSocket Authentication + Connection Cap (🟡 MEDIUM)
**File:** `plugins/companion/handler.py`

1. Require `?token=` query parameter on WebSocket connection
2. Verify token against the stored pairing token in `~/.valhalla/mobile_token.json`
3. Reject with 401 if token is missing/invalid
4. Cap concurrent connections at 5 — reject new connections with 429 if at cap
5. Add periodic cleanup of dead connections (every 60s via a background task, or on each new connection attempt)

### Task 3 — Sanitize Marketplace Error Messages (🟢 LOW)
**File:** `plugins/companion/handler.py`

Replace all `str(e)` in marketplace error handlers with generic messages:
```python
# Before:
except Exception as e:
    return {"ok": False, "note": str(e)}

# After:
except Exception as e:
    logger.error(f"Marketplace error: {e}")
    return {"ok": False, "note": "Marketplace service unavailable"}
```

### Task 4 — Achievement Tracking Backend
**File:** `plugins/companion/handler.py` or create `plugins/companion/achievements.py`

Create an achievement system that tracks milestones:

```python
ACHIEVEMENTS = {
    "first_feed": {"name": "First Meal", "desc": "Feed your companion for the first time", "icon": "🍽️"},
    "feed_10": {"name": "Chef", "desc": "Feed your companion 10 times", "icon": "👨‍🍳"},
    "feed_100": {"name": "Master Chef", "desc": "Feed 100 times", "icon": "⭐"},
    "first_walk": {"name": "First Steps", "desc": "Take your first walk", "icon": "🚶"},
    "walk_50": {"name": "Explorer", "desc": "Complete 50 walks", "icon": "🗺️"},
    "first_quest": {"name": "Adventurer", "desc": "Complete your first quest", "icon": "⚔️"},
    "quest_25": {"name": "Hero", "desc": "Complete 25 quests", "icon": "🦸"},
    "first_teach": {"name": "Teacher", "desc": "Teach your companion a fact", "icon": "📚"},
    "teach_20": {"name": "Professor", "desc": "Teach 20 facts", "icon": "🎓"},
    "daily_7": {"name": "Streak!", "desc": "7-day login streak", "icon": "🔥"},
    "daily_30": {"name": "Devoted", "desc": "30-day login streak", "icon": "💎"},
    "level_5": {"name": "Growing Up", "desc": "Reach level 5", "icon": "🌱"},
    "level_10": {"name": "Seasoned", "desc": "Reach level 10", "icon": "🌳"},
    "guardian_save": {"name": "Saved by Guardian", "desc": "Guardian stopped a risky message", "icon": "🛡️"},
    "voice_first": {"name": "First Words", "desc": "Use voice mode for the first time", "icon": "🎤"},
    "translate_first": {"name": "Polyglot", "desc": "Translate something", "icon": "🌍"},
}
```

Endpoints:
```
GET  /api/v1/companion/achievements     — list all achievements + which are earned
POST /api/v1/companion/achievements/check — check and award any newly earned achievements
```

Store earned achievements in `~/.valhalla/achievements.json` with timestamps.

The `check` endpoint should be called after any action (feed, walk, quest, teach, etc.) and return newly earned achievements so the mobile app can show a toast.

### Task 5 — Weekly Summary Endpoint
```
GET /api/v1/companion/weekly-summary
```

Return a summary of the past 7 days:
```json
{
  "period": "Mar 9 - Mar 15",
  "stats": {
    "feeds": 23,
    "walks": 14,
    "quests_completed": 8,
    "facts_learned": 5,
    "messages_sent": 47,
    "levels_gained": 2,
    "achievements_earned": 3,
    "guardian_saves": 1
  },
  "highlights": [
    "Reached level 7!",
    "Earned 'Explorer' achievement",
    "Your companion learned 5 new facts"
  ]
}
```

Derive from existing data files (companion state, chat history, achievements). If stats aren't tracked yet, add simple counters to the companion state file.

### Task 6 — Drop Your Gate
Create `sprints/current/gates/gate_thor.md` using write_to_file:

```markdown
# Thor Gate — Sprint 7 Backend Complete
Sprint 7 tasks completed.

## Completed
- [x] SSRF blocklist on /browse/summarize
- [x] WebSocket auth (token param) + 5 connection cap
- [x] Marketplace error messages sanitized
- [x] Achievement tracking (16 achievements, check endpoint)
- [x] Weekly summary endpoint
```

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop
