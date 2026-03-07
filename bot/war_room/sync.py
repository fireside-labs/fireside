"""
sync.py ΓÇö Gossip sync protocol for the Valhalla War Room.

Every N seconds, pulls new messages and tasks from all peer nodes.
Merges into local store with deduplication. Eventually consistent.
"""

import json
import logging
import threading
import time
import urllib.request
from pathlib import Path
from typing import Optional

from .store import WarRoomStore

log = logging.getLogger("war-room.sync")

HEALTH_TIMEOUT = 5  # seconds


class GossipSync:
    """Background daemon that syncs war room data across the mesh."""

    def __init__(
        self,
        store: WarRoomStore,
        this_node: str,
        nodes: dict,
        interval: int = 30,
    ):
        self.store = store
        self.this_node = this_node
        self.nodes = nodes  # {name: {ip, port, ...}}
        self.interval = interval

        self._state_file = store.data_dir / "sync_state.json"
        self._sync_state = self._load_state()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> dict:
        try:
            if self._state_file.exists():
                return json.loads(self._state_file.read_text())
        except Exception:
            pass
        return {}

    def _save_state(self):
        try:
            self._state_file.write_text(json.dumps(self._sync_state, indent=2))
        except Exception as e:
            log.warning("Failed to save sync state: %s", e)

    # ------------------------------------------------------------------
    # Network helpers
    # ------------------------------------------------------------------

    def _health_check(self, node_name: str) -> bool:
        info = self.nodes.get(node_name)
        if not info:
            return False
        url = f"http://{info['ip']}:{info.get('port', 8765)}/health"
        try:
            with urllib.request.urlopen(url, timeout=HEALTH_TIMEOUT) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _get(self, node_name: str, endpoint: str) -> Optional[dict]:
        info = self.nodes.get(node_name)
        if not info:
            return None
        url = f"http://{info['ip']}:{info.get('port', 8765)}{endpoint}"
        try:
            with urllib.request.urlopen(url, timeout=HEALTH_TIMEOUT + 5) as resp:
                return json.loads(resp.read())
        except Exception as e:
            log.debug("GET %s from %s failed: %s", endpoint, node_name, e)
            return None

    # ------------------------------------------------------------------
    # Sync cycle
    # ------------------------------------------------------------------

    def _sync_one(self, node_name: str):
        """Pull new data from a single peer node."""
        if not self._health_check(node_name):
            return

        # Pull messages since last sync
        last_sync = self._sync_state.get(node_name, {}).get("last_msg_sync", "")
        endpoint = f"/war-room/read?since={last_sync}" if last_sync else "/war-room/read"
        data = self._get(node_name, endpoint)
        if data and isinstance(data, list):
            new_count = self.store.merge_messages(data)
            if new_count > 0:
                log.info("Synced %d new messages from %s", new_count, node_name)

        # Pull tasks (use ?raw=true to get dict keyed by id, which merge_tasks expects)
        # Pass ?since= so we only fetch tasks updated since last sync, not the full board
        task_endpoint = "/war-room/tasks?raw=true"
        if last_sync:
            task_endpoint += f"&since={last_sync}"
        task_data = self._get(node_name, task_endpoint)
        if task_data and isinstance(task_data, dict):
            updated = self.store.merge_tasks(task_data)
            if updated > 0:
                log.info("Synced %d task updates from %s", updated, node_name)

        # Pull tombstones (deleted IDs) ΓÇö apply locally to replicate deletes
        tombstone_endpoint = "/war-room/tombstones"
        if last_sync:
            tombstone_endpoint += f"?since={last_sync}"
        tombstone_data = self._get(node_name, tombstone_endpoint)
        if tombstone_data and isinstance(tombstone_data, dict) and tombstone_data:
            self.store.apply_tombstones(tombstone_data)
            log.info("Applied %d tombstones from %s", len(tombstone_data), node_name)

        # Update sync timestamp
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        self._sync_state.setdefault(node_name, {})["last_msg_sync"] = now
        self._save_state()

    def _sync_cycle(self):
        """Run one full sync cycle across all peers."""
        for node_name in self.nodes:
            if node_name == self.this_node:
                continue
            try:
                self._sync_one(node_name)
            except Exception as e:
                log.warning("Sync failed for %s: %s", node_name, e)

    # ------------------------------------------------------------------
    # Daemon loop
    # ------------------------------------------------------------------

    def _loop(self):
        log.info(
            "Gossip sync started (interval=%ds, peers=%s)",
            self.interval,
            [n for n in self.nodes if n != self.this_node],
        )
        while self._running:
            try:
                self._sync_cycle()
            except Exception as e:
                log.error("Sync cycle error: %s", e)
            time.sleep(self.interval)

    def start(self):
        """Start the gossip sync daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="war-room-gossip")
        self._thread.start()
        log.info("Gossip sync daemon started")

    def stop(self):
        """Stop the gossip sync daemon."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        log.info("Gossip sync daemon stopped")


class OverseerLoop:
    """Odin-only: monitors the task board and reports blocked tasks."""

    def __init__(self, store: WarRoomStore, interval: int = 60):
        self.store = store
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _check(self):
        """Check for tasks that have been blocked too long."""
        from datetime import datetime, timezone

        tasks = self.store.get_tasks(status="blocked")
        now = datetime.now(timezone.utc)
        alerts = []
        for task in tasks:
            try:
                updated_str = task["updated"]
                updated = datetime.fromisoformat(updated_str)
                # Handle naive datetimes (no tz info) from older nodes
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                age_minutes = (now - updated).total_seconds() / 60
                if age_minutes > 5:
                    alerts.append(
                        f"ΓÜá∩╕Å Task '{task['title']}' ({task['id']}) blocked for "
                        f"{age_minutes:.0f}m ΓÇö assigned to {task.get('assigned_to', 'unassigned')}"
                    )
            except (KeyError, ValueError) as e:
                log.warning("Overseer: could not parse task %s: %s", task.get("id"), e)
        if alerts:
            log.warning("OVERSEER ALERTS:\n%s", "\n".join(alerts))
        return alerts

    def _loop(self):
        log.info("Overseer loop started (interval=%ds)", self.interval)
        while self._running:
            try:
                self._check()
            except Exception as e:
                log.error("Overseer check error: %s", e)
            time.sleep(self.interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="war-room-overseer")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)