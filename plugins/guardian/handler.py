"""
guardian/handler.py — Scam Shield API routes.

Routes:
    POST /guardian/scan          — Scan a single message
    POST /guardian/scan-email    — Scan an email (subject + body)
    POST /guardian/scan-batch    — Scan multiple messages at once
    GET  /guardian/stats         — Get scan statistics

All scanning happens locally. No data leaves the device.
Designed to power both the Fireside companion and the standalone
Scam Shield app.
"""
# NOTE: Do NOT use 'from __future__ import annotations' here — it breaks
# FastAPI's Pydantic body detection for POST routes.


import json
import logging
import time
from datetime import datetime
from pathlib import Path

log = logging.getLogger("valhalla.guardian")

# Local stats file
STATS_PATH = Path.home() / ".fireside" / "guardian_stats.json"


def _load_stats() -> dict:
    """Load scan statistics."""
    if STATS_PATH.exists():
        try:
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "total_scanned": 0,
        "scams_caught": 0,
        "suspects_flagged": 0,
        "safe_confirmed": 0,
        "last_scan": None,
    }


def _save_stats(stats: dict):
    """Save scan statistics."""
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(json.dumps(stats, indent=2), encoding="utf-8")


def _record_scan(result: dict):
    """Record a scan result in stats."""
    stats = _load_stats()
    stats["total_scanned"] += 1
    stats["last_scan"] = datetime.now().isoformat()

    threat = result.get("threat", "safe")
    if threat == "scam":
        stats["scams_caught"] += 1
    elif threat == "suspect":
        stats["suspects_flagged"] += 1
    else:
        stats["safe_confirmed"] += 1

    _save_stats(stats)


# ═══════════════════════════════════════════════════════════════
# Route Registration
# ═══════════════════════════════════════════════════════════════

def register_routes(app, config: dict = None):
    """Register Guardian routes with the FastAPI app."""
    from pydantic import BaseModel
    from typing import Optional, List
    from plugins.guardian.scanner import scan_message, scan_email, scan_batch

    class ScanRequest(BaseModel):
        text: str
        sender: str = ""
        known_contacts: Optional[List[str]] = None
        message_type: str = "sms"  # "sms", "email", "chat"

    class EmailScanRequest(BaseModel):
        subject: str
        body: str
        sender: str = ""
        known_contacts: Optional[List[str]] = None

    class BatchScanRequest(BaseModel):
        messages: List[dict]

    @app.post("/guardian/scan")
    async def handle_scan(req: ScanRequest):
        """
        Scan a single message for scam indicators.

        Returns color-coded threat level:
            🟢 green (#22c55e) = Safe
            🟡 yellow (#eab308) = Suspicious
            🔴 red (#ef4444) = Scam

        For the Scam Shield app UI:
            Use result.color for the border/badge color
            Use result.label for the text badge
            Use result.advice for the Fable speech bubble
        """
        start = time.time()
        result = scan_message(
            text=req.text,
            sender=req.sender,
            known_contacts=req.known_contacts,
            message_type=req.message_type,
        )
        result["elapsed_ms"] = round((time.time() - start) * 1000, 1)
        _record_scan(result)

        log.info("[guardian] Scanned %s message → %s (%.1f%%)",
                 req.message_type, result["threat"],
                 result["score"] * 100)
        return result

    @app.post("/guardian/scan-email")
    async def handle_scan_email(req: EmailScanRequest):
        """
        Scan an email for scam/phishing indicators.
        Includes sender-domain mismatch detection.
        """
        start = time.time()
        result = scan_email(
            subject=req.subject,
            body=req.body,
            sender=req.sender,
            known_contacts=req.known_contacts,
        )
        result["elapsed_ms"] = round((time.time() - start) * 1000, 1)
        _record_scan(result)
        return result

    @app.post("/guardian/scan-batch")
    async def handle_scan_batch(req: BatchScanRequest):
        """
        Scan multiple messages at once.
        Returns an array of results in the same order.

        Useful for scanning an inbox or message list.
        """
        start = time.time()
        results = scan_batch(req.messages)

        for r in results:
            _record_scan(r)

        scam_count = sum(1 for r in results if r["threat"] == "scam")
        suspect_count = sum(1 for r in results if r["threat"] == "suspect")

        return {
            "results": results,
            "total": len(results),
            "scams": scam_count,
            "suspects": suspect_count,
            "safe": len(results) - scam_count - suspect_count,
            "elapsed_ms": round((time.time() - start) * 1000, 1),
        }

    @app.get("/guardian/stats")
    async def handle_stats():
        """
        Get Guardian scan statistics.

        Shows how many scams have been caught — great for the dashboard:
        "Fable has protected you from 23 scam attempts this month! 🛡️"
        """
        stats = _load_stats()
        stats["protection_message"] = (
            f"Your Guardian has scanned {stats['total_scanned']} messages "
            f"and caught {stats['scams_caught']} scam attempts."
        )
        return stats

    log.info("[guardian] Routes registered: /guardian/scan, /guardian/scan-email, "
             "/guardian/scan-batch, /guardian/stats")
