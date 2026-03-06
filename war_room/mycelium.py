"""
mycelium.py — Self-healing network layer.

Like mycelium in a forest, this background process senses when nodes are
struggling and silently ships relevant solutions from the shared memory
to the stressed agent — without any human intervention.

Cycle (every POLL_INTERVAL seconds):
  1. Query Heimdall GET /audit?severity=high&since=<now-5min>
  2. Count high-severity events per node
  3. Any node with >= STRESS_THRESHOLD events = "stressed"
  4. For each stressed node, extract error topics
  5. [IMMUNE] Check vaccine store — known patterns get instant cure injection
  6. Otherwise: query /memory-query for relevant successful memories
  7. Re-inject top memories tagged for the stressed node
  8. [IMMUNE] Record what worked → strengthen the vaccine

Immune Memory (vaccination):
  - Every successful healing event is recorded as a "vaccine"
  - A vaccine maps a symptom fingerprint → list of cure memory_ids
  - On recurrence, skip steps 1-6 and directly inject the known cure
  - Repeated successes increase vaccine efficacy (0.0→1.0)
  - Stored in BIFROST_VACCINE_FILE (default: vaccines.json)

Started as a daemon thread by bifrost_local.py register_routes().
"""

import hashlib
import json
import logging
import os
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

log = logging.getLogger("war-room.mycelium")

POLL_INTERVAL    = 300      # 5 minutes
STRESS_WINDOW    = 300      # look-back window (seconds) for stress detection
STRESS_THRESHOLD = 3        # events in window = stressed
HEALING_LIMIT    = 3        # max memories to inject per stressed node per cycle
HEALING_IMPORTANCE = 0.9   # importance score for injected memories

# Vaccine store path
_DEFAULT_VACCINE_FILE = str(Path(__file__).parent.parent / "vaccines.json")
VACCINE_FILE = os.environ.get("BIFROST_VACCINE_FILE", _DEFAULT_VACCINE_FILE)

# Heimdall's audit endpoint
_HEIMDALL_AUDIT_URL: Optional[str] = None
# Local bifrost address
_LOCAL_URL = "http://localhost:8765"

# Track which nodes got healing this cycle (avoid spam)
_healed_this_cycle: set = set()

_thread: Optional[threading.Thread] = None
_running = False

# In-memory vaccine cache (loaded from disk at start)
_vaccines: dict = {}   # {symptom_fingerprint: {cure_ids, efficacy, hit_count, last_used}}
_vaccine_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Vaccine store — persistent immune memory
# ---------------------------------------------------------------------------

def _load_vaccines() -> None:
    """Load vaccine store from disk."""
    global _vaccines
    try:
        if Path(VACCINE_FILE).exists():
            with open(VACCINE_FILE, "r", encoding="utf-8") as f:
                _vaccines = json.load(f)
            log.info("[mycelium] Loaded %d vaccines from %s", len(_vaccines), VACCINE_FILE)
        else:
            _vaccines = {}
            log.info("[mycelium] Vaccine store empty (new install)")
    except Exception as e:
        log.warning("[mycelium] Failed to load vaccines: %s", e)
        _vaccines = {}


def _save_vaccines() -> None:
    """Persist vaccine store to disk."""
    try:
        with _vaccine_lock:
            with open(VACCINE_FILE, "w", encoding="utf-8") as f:
                json.dump(_vaccines, f, indent=2)
    except Exception as e:
        log.warning("[mycelium] Failed to save vaccines: %s", e)


def _symptom_fingerprint(topics: list) -> str:
    """Create a stable fingerprint for a set of error topics."""
    key = "|".join(sorted(set(t[:80].lower() for t in topics)))
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def _record_vaccine(fingerprint: str, topics: list, cure_memory_ids: list) -> None:
    """Record a successful cure as a vaccine."""
    with _vaccine_lock:
        existing = _vaccines.get(fingerprint, {
            "fingerprint": fingerprint,
            "symptoms":    topics[:3],
            "cure_ids":    [],
            "efficacy":    0.0,
            "hit_count":   0,
            "use_count":   0,
            "last_healed": 0,
        })
        # Merge cure ids (deduplicate)
        merged = list(set(existing["cure_ids"] + cure_memory_ids))
        existing["cure_ids"]    = merged[:10]   # keep top 10 cure memories
        existing["hit_count"]  += 1
        existing["last_healed"] = time.time()
        # Efficacy increases with each confirmed success, capped at 1.0
        existing["efficacy"] = min(1.0, existing["efficacy"] + 0.2)
        _vaccines[fingerprint] = existing
    _save_vaccines()
    log.info("[immune] Recorded vaccine for fingerprint %s (efficacy: %.1f, cures: %d)",
             fingerprint, existing["efficacy"], len(existing["cure_ids"]))


def _lookup_vaccine(fingerprint: str) -> Optional[dict]:
    """Check if we have a known vaccine for this symptom pattern."""
    with _vaccine_lock:
        v = _vaccines.get(fingerprint)
        if v and v.get("cure_ids") and v.get("efficacy", 0) > 0:
            return dict(v)
    return None


def _apply_vaccine(node: str, vaccine: dict) -> int:
    """
    Directly inject known cure memories for a stressed node.
    Returns number of memories injected.
    """
    cure_ids = vaccine.get("cure_ids", [])
    if not cure_ids:
        return 0

    injected = 0
    for mid in cure_ids[:HEALING_LIMIT]:
        # Fetch the actual memory content by querying with the memory_id
        memories = _query_memory_by_id(mid)
        if not memories:
            continue
        content = memories[0].get("content", "").strip()
        if not content or "[MYCELIUM]" in content:
            continue

        healing = {
            "memories": [{
                "content":    f"[MYCELIUM][IMMUNE] For {node}: {content}",
                "node":       node,
                "importance": HEALING_IMPORTANCE,
                "tags":       ["mycelium", "healing", "immune", node],
                "shared":     True,
                "valence":    1.0,         # immune injections are always positive
            }]
        }
        ok = _post_memory(healing)
        if ok:
            injected += 1

    # Update vaccine use count
    with _vaccine_lock:
        if vaccine["fingerprint"] in _vaccines:
            _vaccines[vaccine["fingerprint"]]["use_count"] = \
                _vaccines[vaccine["fingerprint"]].get("use_count", 0) + 1
    _save_vaccines()

    if injected:
        log.info("[immune] Applied vaccine to %s: %d memories injected (efficacy: %.1f)",
                 node, injected, vaccine.get("efficacy", 0))
    return injected


def _query_memory_by_id(memory_id: str) -> list:
    """Retrieve a specific memory by its ID."""
    try:
        params = urllib.parse.urlencode({"q": memory_id, "limit": 1})
        url = f"{_LOCAL_URL}/memory-query?{params}"
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
            return data.get("results", [])
    except Exception as e:
        log.debug("[immune] Memory lookup failed for %s: %s", memory_id[:12], e)
        return []


# ---------------------------------------------------------------------------
# Main mycelium engine
# ---------------------------------------------------------------------------

def start(nodes: dict) -> None:
    """Start the mycelium background thread. Called from register_routes()."""
    global _HEIMDALL_AUDIT_URL, _thread, _running

    heimdall = nodes.get("heimdall", {})
    ip   = heimdall.get("ip", "100.108.153.23")
    port = heimdall.get("port", 8765)
    _HEIMDALL_AUDIT_URL = f"http://{ip}:{port}/audit"

    _load_vaccines()

    if _thread and _thread.is_alive():
        log.info("[mycelium] Already running")
        return

    _running = True
    _thread = threading.Thread(target=_loop, daemon=True, name="mycelium")
    _thread.start()
    log.info("[mycelium] Started — polling Heimdall every %ds / %d vaccines loaded",
             POLL_INTERVAL, len(_vaccines))


def stop() -> None:
    global _running
    _running = False


def _loop() -> None:
    """Main mycelium cycle — runs forever in background."""
    # Stagger first run by 30s to let Bifrost fully initialise
    time.sleep(30)
    while _running:
        try:
            _cycle()
        except Exception as e:
            log.error("[mycelium] Cycle error: %s", e)
        for _ in range(POLL_INTERVAL):
            if not _running:
                break
            time.sleep(1)


def _cycle() -> None:
    """One mycelium scan cycle."""
    global _healed_this_cycle
    _healed_this_cycle = set()

    # 1. Poll Heimdall for recent high-severity audit events
    events = _fetch_audit_events()
    if events is None:
        log.debug("[mycelium] Heimdall unreachable — skipping cycle")
        return

    if not events:
        log.debug("[mycelium] No high-severity events — mesh healthy")
        return

    # 2. Count events per node in the stress window
    now    = time.time()
    cutoff = now - STRESS_WINDOW
    node_events: dict = {}
    for ev in events:
        ts = ev.get("ts") or ev.get("timestamp", 0)
        if isinstance(ts, str):
            try:
                import datetime
                ts = datetime.datetime.fromisoformat(ts).timestamp()
            except Exception:
                ts = 0
        if ts < cutoff:
            continue
        node = ev.get("node", "unknown")
        node_events.setdefault(node, []).append(ev)

    # 3. Identify stressed nodes
    stressed = {n: evs for n, evs in node_events.items()
                if len(evs) >= STRESS_THRESHOLD}

    if not stressed:
        log.debug("[mycelium] No stressed nodes (max events: %d)",
                  max((len(v) for v in node_events.values()), default=0))
        return

    log.info("[mycelium] Stressed nodes: %s", list(stressed.keys()))

    # 4-8. Heal each stressed node
    for node, evs in stressed.items():
        if node in _healed_this_cycle:
            continue
        # Journal the stress episode
        try:
            from war_room import dream_journal as _dj
            _dj.record_stress(node, len(evs))
        except Exception:
            pass
        _heal(node, evs)
        _healed_this_cycle.add(node)


def _fetch_audit_events() -> Optional[list]:
    """GET Heimdall's /audit endpoint. Returns list of events or None on failure."""
    if not _HEIMDALL_AUDIT_URL:
        return None
    try:
        params = urllib.parse.urlencode({"severity": "high", "limit": 50})
        url    = f"{_HEIMDALL_AUDIT_URL}?{params}"
        req    = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            if isinstance(data, list):
                return data
            return data.get("events") or data.get("logs") or []
    except Exception as e:
        log.debug("[mycelium] Heimdall audit fetch failed: %s", e)
        return None


def _extract_topics(events: list) -> list:
    """Extract error keywords from audit events to use as query topics."""
    topics = []
    for ev in events:
        text = " ".join(filter(None, [
            ev.get("detail", ""),
            ev.get("message", ""),
            ev.get("error", ""),
            ev.get("event", ""),
        ]))
        if text.strip():
            topics.append(text[:200])
    return topics[:5]


def _heal(node: str, events: list) -> None:
    """
    Attempt to heal a stressed node.
    Tries immune memory (vaccine) first for instant response,
    falls back to fresh memory search if no vaccine exists.
    """
    topics = _extract_topics(events)
    if not topics:
        topics = [f"{node} error recovery"]

    fingerprint = _symptom_fingerprint(topics)

    # === IMMUNE MEMORY: check vaccine store first ===
    vaccine = _lookup_vaccine(fingerprint)
    if vaccine:
        log.info("[immune] Known pattern detected for %s (efficacy: %.1f) — applying vaccine",
                 node, vaccine.get("efficacy", 0))
        injected = _apply_vaccine(node, vaccine)
        if injected > 0:
            log.info("[immune] Vaccination complete: %s healed instantly (%d memories)",
                     node, injected)
            try:
                from war_room import dream_journal as _dj
                _dj.record_healing(node, injected, via_vaccine=True)
            except Exception:
                pass
            return
        log.info("[immune] Vaccine had no viable memories — falling back to fresh search")

    # === STANDARD MYCELIUM: search shared memory ===
    injected    = 0
    seen_ids: set = set()
    cured_ids: list = []

    for topic in topics:
        if injected >= HEALING_LIMIT:
            break

        memories = _query_memory(topic)
        if not memories:
            continue

        for mem in memories:
            if injected >= HEALING_LIMIT:
                break
            mid = mem.get("memory_id", "")
            if mid in seen_ids:
                continue
            content = mem.get("content", "").strip()
            if not content or "[MYCELIUM]" in content:
                continue
            seen_ids.add(mid)

            healing = {
                "memories": [{
                    "content":    f"[MYCELIUM] For {node}: {content}",
                    "node":       node,
                    "importance": HEALING_IMPORTANCE,
                    "tags":       ["mycelium", "healing", node],
                    "shared":     True,
                    "valence":    1.0,
                }]
            }
            ok = _post_memory(healing)
            if ok:
                injected += 1
                cured_ids.append(mid)
                log.info("[mycelium] Injected healing memory for %s: %s...",
                         node, content[:60])

    if injected == 0:
        log.info("[mycelium] No relevant memories found for %s (topics: %s)",
                 node, topics)
    else:
        log.info("[mycelium] Healed %s with %d memories — recording vaccine", node, injected)
        # === RECORD VACCINE: learn this cure for future instant response ===
        _record_vaccine(fingerprint, topics, cured_ids)
        try:
            from war_room import dream_journal as _dj
            _dj.record_healing(node, injected, via_vaccine=False)
        except Exception:
            pass


def _query_memory(topic: str) -> list:
    """Query local /memory-query for successful memories related to topic."""
    try:
        params = urllib.parse.urlencode({"q": topic, "node": "all", "limit": 5,
                                         "min_importance": "0.6"})
        url = f"{_LOCAL_URL}/memory-query?{params}"
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
            return data.get("results", [])
    except Exception as e:
        log.debug("[mycelium] Memory query failed for '%s': %s", topic[:40], e)
        return []


def _post_memory(payload: dict) -> bool:
    """POST a healing memory to local /memory-sync."""
    try:
        body = json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"{_LOCAL_URL}/memory-sync", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = json.loads(r.read())
            return resp.get("upserted", 0) > 0
    except Exception as e:
        log.debug("[mycelium] Memory inject failed: %s", e)
        return False


def status() -> dict:
    """Return current mycelium health including vaccine store stats."""
    with _vaccine_lock:
        vaccines_snapshot = dict(_vaccines)

    total_vaccines    = len(vaccines_snapshot)
    avg_efficacy      = (sum(v.get("efficacy", 0) for v in vaccines_snapshot.values())
                         / total_vaccines) if total_vaccines else 0.0
    total_vaccinations = sum(v.get("use_count", 0) for v in vaccines_snapshot.values())

    return {
        "running":           _running and bool(_thread and _thread.is_alive()),
        "poll_interval_s":   POLL_INTERVAL,
        "stress_threshold":  STRESS_THRESHOLD,
        "stress_window_s":   STRESS_WINDOW,
        "healing_limit":     HEALING_LIMIT,
        "heimdall_url":      _HEIMDALL_AUDIT_URL,
        "healed_this_cycle": list(_healed_this_cycle),
        "immune_memory": {
            "vaccines":          total_vaccines,
            "avg_efficacy":      round(avg_efficacy, 3),
            "total_vaccinations": total_vaccinations,
            "vaccine_file":      VACCINE_FILE,
        },
    }


