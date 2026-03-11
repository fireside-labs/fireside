"""
Tests for the event-bus plugin — pub/sub core.
"""
from __future__ import annotations

import sys
import os
import threading
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestEventBusPubSub:
    """Core pub/sub functionality."""

    def _get_handler(self):
        """Import event-bus handler module."""
        import importlib.util
        handler_path = os.path.join(
            os.path.dirname(__file__), "..", "plugins", "event-bus", "handler.py"
        )
        spec = importlib.util.spec_from_file_location("eb_handler", handler_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_subscribe_and_publish(self):
        """Test basic subscribe/publish cycle."""
        mod = self._get_handler()
        received = []

        def handler(payload):
            received.append(payload)

        mod.subscribe("test.basic", handler)
        mod.publish("test.basic", {"msg": "hello"})

        # Wait for async handler
        time.sleep(0.1)
        assert len(received) == 1
        assert received[0]["msg"] == "hello"

    def test_wildcard_subscribe(self):
        """Test wildcard topic matching."""
        mod = self._get_handler()
        received = []

        def handler(payload):
            received.append(payload)

        mod.subscribe("hypothesis.*", handler)
        mod.publish("hypothesis.confirmed", {"id": "h1"})
        mod.publish("hypothesis.refuted", {"id": "h2"})
        mod.publish("prediction.scored", {"id": "p1"})  # should NOT match

        time.sleep(0.15)
        assert len(received) == 2

    def test_get_log(self):
        """Test event log retrieval."""
        mod = self._get_handler()

        mod.publish("log.test1", {"a": 1})
        mod.publish("log.test2", {"b": 2})

        log = mod.get_log(limit=10)
        topics = [e["topic"] for e in log]
        assert "log.test1" in topics
        assert "log.test2" in topics

    def test_get_log_with_filter(self):
        """Test topic-filtered log retrieval."""
        mod = self._get_handler()

        mod.publish("filter.alpha", {"x": 1})
        mod.publish("filter.beta", {"x": 2})
        mod.publish("other.gamma", {"x": 3})

        log = mod.get_log(limit=100, topic_filter="filter")
        topics = [e["topic"] for e in log]
        assert all(t.startswith("filter") for t in topics)

    def test_subscriber_count(self):
        """Test subscriber counting."""
        mod = self._get_handler()

        mod.subscribe("count.test", lambda p: None)
        mod.subscribe("count.test", lambda p: None)

        counts = mod.subscriber_count()
        assert counts.get("count.test", 0) >= 2

    def test_event_has_timestamp(self):
        """Test event log entries have timestamps."""
        mod = self._get_handler()

        mod.publish("ts.test", {"data": True})

        log = mod.get_log(limit=5, topic_filter="ts.test")
        assert len(log) >= 1
        assert "ts" in log[-1]
        assert log[-1]["ts"] > 0

    def test_handler_exception_doesnt_crash(self):
        """Test that a failing handler doesn't crash the bus."""
        mod = self._get_handler()
        good_received = []

        def bad_handler(payload):
            raise ValueError("boom!")

        def good_handler(payload):
            good_received.append(payload)

        mod.subscribe("crash.test", bad_handler)
        mod.subscribe("crash.test", good_handler)
        mod.publish("crash.test", {"should": "survive"})

        time.sleep(0.15)
        assert len(good_received) == 1
