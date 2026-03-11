"""
tests/test_rate_limiter.py — Unit tests for rate limiting middleware.

Run: cd /Users/odin/Documents/ProjectOpenClaw/valhalla-mesh-v2 && python3 -m pytest tests/test_rate_limiter.py -v
"""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from middleware.rate_limiter import TokenBucket, BucketRegistry


class TestTokenBucket(unittest.TestCase):
    """Tests for the token bucket implementation."""

    def test_allows_within_capacity(self):
        """Should allow requests within capacity."""
        bucket = TokenBucket(capacity=5, window_seconds=60)
        for _ in range(5):
            self.assertTrue(bucket.consume())

    def test_blocks_over_capacity(self):
        """Should block after capacity is exceeded."""
        bucket = TokenBucket(capacity=3, window_seconds=60)
        for _ in range(3):
            bucket.consume()
        self.assertFalse(bucket.consume())

    def test_refills_over_time(self):
        """Should refill tokens over time."""
        bucket = TokenBucket(capacity=2, window_seconds=2)
        bucket.consume()
        bucket.consume()
        self.assertFalse(bucket.consume())

        # Wait for refill (1 second = 1 token at 2/2s rate)
        time.sleep(1.1)
        self.assertTrue(bucket.consume())

    def test_retry_after(self):
        """Should report sane retry-after values."""
        bucket = TokenBucket(capacity=1, window_seconds=60)
        bucket.consume()
        self.assertFalse(bucket.consume())
        retry = bucket.retry_after
        self.assertGreater(retry, 0)
        self.assertLessEqual(retry, 61)

    def test_never_exceeds_capacity(self):
        """Tokens should never exceed capacity even after long idle."""
        bucket = TokenBucket(capacity=5, window_seconds=10)
        bucket.consume()
        # Simulate long idle
        bucket.last_refill = time.monotonic() - 1000
        bucket.consume()  # Trigger refill
        # Tokens should be capped at capacity (5), minus the 1 consumed
        self.assertEqual(bucket.tokens, 4.0)


class TestBucketRegistry(unittest.TestCase):
    """Tests for the bucket registry."""

    def test_creates_new_buckets(self):
        registry = BucketRegistry()
        b1 = registry.get_or_create("POST /test", "1.2.3.4", 5, 60)
        self.assertIsInstance(b1, TokenBucket)

    def test_reuses_existing_buckets(self):
        registry = BucketRegistry()
        b1 = registry.get_or_create("POST /test", "1.2.3.4", 5, 60)
        b2 = registry.get_or_create("POST /test", "1.2.3.4", 5, 60)
        self.assertIs(b1, b2)

    def test_different_ips_get_different_buckets(self):
        registry = BucketRegistry()
        b1 = registry.get_or_create("POST /test", "1.2.3.4", 5, 60)
        b2 = registry.get_or_create("POST /test", "5.6.7.8", 5, 60)
        self.assertIsNot(b1, b2)

    def test_stats(self):
        registry = BucketRegistry()
        registry.get_or_create("POST /a", "1.1.1.1", 5, 60)
        registry.get_or_create("POST /b", "2.2.2.2", 5, 60)
        stats = registry.stats()
        self.assertEqual(stats["total_buckets"], 2)


class TestRateLimitIntegration(unittest.TestCase):
    """Integration-style tests for rate limit behavior."""

    def test_rapid_requests_blocked(self):
        """Simulate rapid requests exceeding the limit."""
        bucket = TokenBucket(capacity=3, window_seconds=60)
        results = [bucket.consume() for _ in range(5)]
        self.assertEqual(results[:3], [True, True, True])
        self.assertEqual(results[3:], [False, False])


if __name__ == "__main__":
    unittest.main()
