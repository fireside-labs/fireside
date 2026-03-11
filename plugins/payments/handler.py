"""
payments/handler.py — Stripe payments for marketplace + store.

Routes:
  POST /api/v1/payments/connect   — Stripe Connect OAuth for sellers
  POST /api/v1/payments/checkout  — Create checkout session for buyers
  POST /api/v1/payments/webhook   — Handle Stripe webhooks
  GET  /api/v1/purchases          — User's purchased items
  GET  /api/v1/earnings           — Seller earnings dashboard
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

log = logging.getLogger("valhalla.payments")

_STRIPE_KEY: str = ""
_STRIPE_WEBHOOK_SECRET: str = ""
_PLATFORM_FEE_PCT = 30  # 30% platform fee


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _purchases_file() -> Path:
    f = Path.home() / ".valhalla" / "purchases.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    return f


def _earnings_file() -> Path:
    f = Path.home() / ".valhalla" / "earnings.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    return f


def _load_purchases() -> list:
    f = _purchases_file()
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_purchase(purchase: dict) -> None:
    purchases = _load_purchases()
    purchases.append(purchase)
    _purchases_file().write_text(json.dumps(purchases, indent=2), encoding="utf-8")


def _load_earnings() -> list:
    f = _earnings_file()
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_earning(earning: dict) -> None:
    earnings = _load_earnings()
    earnings.append(earning)
    _earnings_file().write_text(json.dumps(earnings, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Stripe helpers
# ---------------------------------------------------------------------------

def _stripe_request(method: str, endpoint: str, data: dict | None = None) -> dict:
    """Make Stripe API request."""
    if not _STRIPE_KEY:
        return {"ok": False, "error": "Stripe not configured"}

    url = f"https://api.stripe.com/v1/{endpoint}"
    headers = {
        "Authorization": f"Bearer {_STRIPE_KEY}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    body = None
    if data:
        body = "&".join(f"{k}={v}" for k, v in data.items()).encode()

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Stripe webhook signature."""
    try:
        elements = dict(item.split("=", 1) for item in signature.split(","))
        timestamp = elements.get("t", "")
        sig = elements.get("v1", "")

        signed = f"{timestamp}.{payload.decode()}".encode()
        expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CheckoutRequest(BaseModel):
    item_id: str
    item_type: str  # agent, theme, avatar, voice, personality
    price_cents: int
    seller_id: Optional[str] = None


class ConnectRequest(BaseModel):
    return_url: str = "http://localhost:3000/store/sell"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _STRIPE_KEY, _STRIPE_WEBHOOK_SECRET

    payments_cfg = config.get("payments", {})
    _STRIPE_KEY = payments_cfg.get("stripe_key", "")
    _STRIPE_WEBHOOK_SECRET = payments_cfg.get("webhook_secret", "")

    router = APIRouter(tags=["payments"])

    @router.post("/api/v1/payments/connect")
    async def api_connect(req: ConnectRequest):
        """Create Stripe Connect onboarding link for sellers."""
        if not _STRIPE_KEY:
            raise HTTPException(status_code=503, detail="Stripe not configured")

        result = _stripe_request("POST", "account_links", {
            "type": "account_onboarding",
            "return_url": req.return_url,
            "refresh_url": req.return_url,
        })
        return result

    @router.post("/api/v1/payments/checkout")
    async def api_checkout(req: CheckoutRequest):
        """Create a checkout session."""
        if not _STRIPE_KEY:
            raise HTTPException(status_code=503, detail="Stripe not configured")

        platform_fee = int(req.price_cents * _PLATFORM_FEE_PCT / 100)

        session_data = {
            "mode": "payment",
            "line_items[0][price_data][currency]": "usd",
            "line_items[0][price_data][unit_amount]": str(req.price_cents),
            "line_items[0][price_data][product_data][name]": f"{req.item_type}: {req.item_id}",
            "line_items[0][quantity]": "1",
            "success_url": "http://localhost:3000/store?purchased=true",
            "cancel_url": "http://localhost:3000/store",
        }

        if req.seller_id:
            session_data["payment_intent_data[application_fee_amount]"] = str(platform_fee)
            session_data["payment_intent_data[transfer_data][destination]"] = req.seller_id

        result = _stripe_request("POST", "checkout/sessions", session_data)
        return result

    @router.post("/api/v1/payments/webhook")
    async def api_webhook(request: Request):
        """Handle Stripe webhooks."""
        body = await request.body()
        sig = request.headers.get("stripe-signature", "")

        if _STRIPE_WEBHOOK_SECRET and not verify_webhook_signature(body, sig, _STRIPE_WEBHOOK_SECRET):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

        try:
            event = json.loads(body)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        event_type = event.get("type", "")

        if event_type == "checkout.session.completed":
            session = event.get("data", {}).get("object", {})
            purchase = {
                "id": session.get("id"),
                "amount": session.get("amount_total", 0),
                "status": "completed",
                "timestamp": time.time(),
            }
            _save_purchase(purchase)
            _publish("payment.completed", purchase)
            return {"ok": True, "handled": event_type}

        elif event_type == "payment_intent.payment_failed":
            _publish("payment.failed", event.get("data", {}).get("object", {}))
            return {"ok": True, "handled": event_type}

        return {"ok": True, "handled": False, "type": event_type}

    @router.get("/api/v1/purchases")
    async def api_purchases():
        """User's purchased items."""
        purchases = _load_purchases()
        return {
            "purchases": purchases,
            "count": len(purchases),
            "total_spent_cents": sum(p.get("amount", 0) for p in purchases),
        }

    @router.get("/api/v1/earnings")
    async def api_earnings():
        """Seller earnings dashboard."""
        earnings = _load_earnings()
        total = sum(e.get("amount", 0) for e in earnings)
        return {
            "earnings": earnings,
            "count": len(earnings),
            "total_earned_cents": total,
            "platform_fee_pct": _PLATFORM_FEE_PCT,
        }

    app.include_router(router)
    log.info("[payments] Plugin loaded. Stripe: %s",
             "configured" if _STRIPE_KEY else "not set")
