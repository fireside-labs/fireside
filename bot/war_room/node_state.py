"""
node_state.py — Persistent node status helper for the Valhalla War Room.

Moved here from bifrost.py to break the circular import between
bifrost.py (parent) and war_room/routes.py (child).

Both bifrost.py and war_room/routes.py import from here.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("war-room.node-state")

# Resolve path relative to this file — works on any node regardless of cwd
_STATUS_FILE = Path(__file__).parent.parent / "status.json"


def write_node_status(status: str, last_task: "str | None" = None, detail: "str | None" = None) -> None:
    """Write current node status to status.json."""
    try:
        existing = {}
        if _STATUS_FILE.exists():
            try:
                existing = json.loads(_STATUS_FILE.read_text())
            except Exception:
                pass

        existing.update({
            "status": status,
            "last_task": last_task or existing.get("last_task"),
            "detail": detail,
            "updated": datetime.now(timezone.utc).isoformat(),
        })
        _STATUS_FILE.write_text(json.dumps(existing, indent=2))
    except Exception as e:
        log.debug("write_node_status failed: %s", e)


def read_node_status() -> dict:
    """Read current node status from status.json."""
    try:
        if _STATUS_FILE.exists():
            return json.loads(_STATUS_FILE.read_text())
    except Exception as e:
        log.debug("read_node_status failed: %s", e)
    return {"status": "idle", "last_task": None, "updated": None}


# Legacy aliases for backward compatibility with any code using the old names
_write_node_status = write_node_status
_read_node_status = read_node_status
