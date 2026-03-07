"""
test_store.py — Unit tests for the Valhalla War Room store.

Run: python3 -m pytest war_room/test_store.py -v
  or: cd /Users/odin/.openclaw/workspace/bot/bot && python3 -m war_room.test_store
"""

import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

# Adjust import path for running from bot/bot/
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from war_room.store import WarRoomStore


class TestMessages(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = WarRoomStore(self.tmp, max_messages=10)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_post_and_read(self):
        msg = self.store.post_message("odin", "all", "update", "test", "hello war room")
        self.assertEqual(msg["from"], "odin")
        self.assertEqual(msg["to"], "all")
        self.assertIn("id", msg)

        msgs = self.store.read_messages()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["body"], "hello war room")

    def test_filter_by_sender(self):
        self.store.post_message("odin", "all", "update", "a", "from odin")
        self.store.post_message("freya", "all", "finding", "b", "from freya")

        msgs = self.store.read_messages(from_agent="freya")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["from"], "freya")

    def test_filter_by_recipient(self):
        self.store.post_message("odin", "thor", "request", "a", "for thor")
        self.store.post_message("odin", "all", "update", "b", "for everyone")

        # Thor should see both (direct + broadcast)
        msgs = self.store.read_messages(to="thor")
        self.assertEqual(len(msgs), 2)

    def test_filter_by_thread(self):
        m1 = self.store.post_message("odin", "all", "update", "a", "start thread")
        thread = m1["thread_id"]
        self.store.post_message("freya", "all", "update", "b", "different thread")

        msgs = self.store.read_messages(thread_id=thread)
        self.assertEqual(len(msgs), 1)

    def test_message_cap(self):
        for i in range(15):
            self.store.post_message("odin", "all", "update", f"msg{i}", f"body{i}")
        msgs = self.store.read_messages()
        self.assertEqual(len(msgs), 10)  # capped at max_messages

    def test_merge_messages(self):
        self.store.post_message("odin", "all", "update", "local", "local msg")

        remote = [
            {"id": "remote_001", "from": "thor", "to": "all", "type": "update",
             "subject": "remote", "body": "from thor", "timestamp": "2026-03-05T12:00:00Z",
             "thread_id": "t1"},
        ]
        new_count = self.store.merge_messages(remote)
        self.assertEqual(new_count, 1)
        self.assertEqual(len(self.store.read_messages()), 2)

        # Merge same again — should be 0 new
        new_count = self.store.merge_messages(remote)
        self.assertEqual(new_count, 0)

    def test_persistence(self):
        self.store.post_message("odin", "all", "update", "persist", "test persistence")

        # Create new store from same dir
        store2 = WarRoomStore(self.tmp)
        msgs = store2.read_messages()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["subject"], "persist")


class TestTasks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = WarRoomStore(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_post_task(self):
        task = self.store.post_task("Fix CSS", "Fix dashboard styles", "odin", affinity=["freya"])
        self.assertEqual(task["title"], "Fix CSS")
        self.assertEqual(task["status"], "open")
        self.assertEqual(task["affinity"], ["freya"])

    def test_task_lifecycle(self):
        task = self.store.post_task("Build API", "REST endpoints", "odin", affinity=["thor"])

        # Claim
        claimed = self.store.claim_task(task["id"], "thor")
        self.assertEqual(claimed["status"], "claimed")
        self.assertEqual(claimed["assigned_to"], "thor")

        # Complete
        done = self.store.complete_task(task["id"], "thor", "API built and tested")
        self.assertEqual(done["status"], "done")
        self.assertEqual(done["result"], "API built and tested")

    def test_affinity_enforcement(self):
        task = self.store.post_task("UI Work", "Frontend only", "odin", affinity=["freya"])

        # Thor can't claim Freya's task
        with self.assertRaises(PermissionError):
            self.store.claim_task(task["id"], "thor")

        # Freya can
        claimed = self.store.claim_task(task["id"], "freya")
        self.assertEqual(claimed["assigned_to"], "freya")

    def test_anyone_affinity(self):
        task = self.store.post_task("Any task", "No restriction", "odin", affinity=["any"])
        claimed = self.store.claim_task(task["id"], "heimdall")
        self.assertEqual(claimed["assigned_to"], "heimdall")

    def test_empty_affinity_means_anyone(self):
        task = self.store.post_task("Open task", "Anyone can take", "odin")
        claimed = self.store.claim_task(task["id"], "thor")
        self.assertEqual(claimed["assigned_to"], "thor")

    def test_cant_claim_done_task(self):
        task = self.store.post_task("Done task", "Already done", "odin")
        self.store.claim_task(task["id"], "thor")
        self.store.complete_task(task["id"], "thor", "finished")
        with self.assertRaises(ValueError):
            self.store.claim_task(task["id"], "freya")

    def test_task_status_update(self):
        task = self.store.post_task("Blocked task", "Needs help", "odin")
        self.store.claim_task(task["id"], "freya")
        updated = self.store.update_task_status(task["id"], "blocked", "freya")
        self.assertEqual(updated["status"], "blocked")

    def test_merge_tasks(self):
        local_task = self.store.post_task("Local", "Local task", "odin")
        remote_tasks = {
            "task_remote1": {
                "id": "task_remote1", "title": "Remote", "description": "From Thor",
                "posted_by": "thor", "assigned_to": None, "affinity": [],
                "status": "open", "result": None,
                "created": "2026-03-05T12:00:00Z", "updated": "2026-03-05T12:00:00Z",
            }
        }
        updated = self.store.merge_tasks(remote_tasks)
        self.assertEqual(updated, 1)
        tasks = self.store.get_tasks()
        self.assertEqual(len(tasks), 2)

    def test_get_tasks_filtered(self):
        self.store.post_task("Task A", "a", "odin")
        t = self.store.post_task("Task B", "b", "odin")
        self.store.claim_task(t["id"], "freya")

        open_tasks = self.store.get_tasks(status="open")
        self.assertEqual(len(open_tasks), 1)

        freya_tasks = self.store.get_tasks(assigned_to="freya")
        self.assertEqual(len(freya_tasks), 1)

    def test_summary(self):
        self.store.post_message("odin", "all", "update", "test", "hello")
        self.store.post_task("Task 1", "desc", "odin")
        summary = self.store.summary()
        self.assertEqual(summary["total_messages"], 1)
        self.assertEqual(summary["active_tasks"], 1)


class TestConcurrency(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = WarRoomStore(self.tmp, max_messages=100)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_concurrent_writes(self):
        errors = []

        def writer(agent_id, count):
            try:
                for i in range(count):
                    self.store.post_message(agent_id, "all", "update", f"msg{i}", f"body from {agent_id}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=("odin", 20)),
            threading.Thread(target=writer, args=("thor", 20)),
            threading.Thread(target=writer, args=("freya", 20)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        msgs = self.store.read_messages()
        self.assertEqual(len(msgs), 60)


if __name__ == "__main__":
    unittest.main()
