"""
social/negotiate.py — Negotiation engine for inter-Navi coordination.

Handles:
    - Meeting scheduling (CEO use case)
    - Group formation (student use case)
    - Group ordering (pizza use case)
    - Guardian family alerts

All negotiations are stored locally as "conversations" that can
span multiple message exchanges between Navis.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from plugins.social.protocol import (
    NaviIdentity, NaviMessage, MessageType,
    negotiate_meeting, group_request, guardian_alert,
    approve, reject, create_message, TrustLevel,
)
from plugins.social.contacts import (
    get_trust_level, update_last_seen, should_auto_approve,
)

log = logging.getLogger("valhalla.social.negotiate")

# ═══════════════════════════════════════════════════════════════
# Negotiation State
# ═══════════════════════════════════════════════════════════════

NEGOTIATIONS_PATH = Path.home() / ".fireside" / "navi_negotiations.json"


def _load_negotiations() -> dict:
    if NEGOTIATIONS_PATH.exists():
        try:
            return json.loads(NEGOTIATIONS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_negotiations(negotiations: dict):
    NEGOTIATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    NEGOTIATIONS_PATH.write_text(
        json.dumps(negotiations, indent=2), encoding="utf-8"
    )


# ═══════════════════════════════════════════════════════════════
# Meeting Scheduler
# ═══════════════════════════════════════════════════════════════

def propose_meeting(
    my_navi: NaviIdentity,
    their_navi: NaviIdentity,
    topic: str,
    my_available_times: list[str],
    duration_minutes: int = 30,
) -> NaviMessage:
    """
    Start a meeting negotiation.

    Example:
        propose_meeting(ember, atlas, "Auth patterns discussion",
                       ["Tue 2 PM", "Thu 10 AM", "Fri 3 PM"])

    Returns the NaVi Protocol message to send.
    """
    msg = negotiate_meeting(
        my_navi, their_navi, topic,
        my_available_times, duration_minutes,
    )

    # Save negotiation state
    negotiations = _load_negotiations()
    negotiations[msg.msg_id] = {
        "type": "meeting",
        "status": "proposed",
        "topic": topic,
        "proposed_times": my_available_times,
        "duration": duration_minutes,
        "with": their_navi.to_dict(),
        "started": datetime.now().isoformat(),
        "messages": [msg.to_dict()],
    }
    _save_negotiations(negotiations)

    log.info("[negotiate] Meeting proposed: %s with %s",
             topic, their_navi.owner)
    return msg


def handle_meeting_proposal(
    msg: NaviMessage,
    my_navi: NaviIdentity,
    my_available_times: Optional[list[str]] = None,
) -> dict:
    """
    Handle an incoming meeting proposal.

    Returns a result dict containing the overlap and a suggested response.
    """
    proposed = msg.payload.get("proposed_times", [])
    topic = msg.payload.get("topic", "Meeting")
    duration = msg.payload.get("duration_minutes", 30)

    result = {
        "from": msg.sender.display_name(),
        "topic": topic,
        "proposed_times": proposed,
        "duration_minutes": duration,
    }

    if my_available_times:
        # Find overlapping times (simple string match)
        overlap = [t for t in proposed if t in my_available_times]
        result["matching_times"] = overlap
        result["has_match"] = len(overlap) > 0

        if overlap:
            result["suggestion"] = f"Both free at: {overlap[0]}"
            result["auto_response"] = approve(
                my_navi, msg.sender, msg.msg_id,
                {"accepted_time": overlap[0], "duration": duration},
            ).to_dict()
        else:
            result["suggestion"] = "No matching times. Counter-proposal needed."
    else:
        result["needs_user_input"] = True
        result["suggestion"] = (
            f"{msg.sender.owner}'s {msg.sender.name} wants to schedule: {topic}. "
            f"Proposed times: {', '.join(proposed)}. "
            f"Which time works for you?"
        )

    update_last_seen(msg.sender.navi_id)
    return result


# ═══════════════════════════════════════════════════════════════
# Group Coordinator
# ═══════════════════════════════════════════════════════════════

def start_group_poll(
    my_navi: NaviIdentity,
    participants: list[NaviIdentity],
    group_type: str,
    question: str,
) -> dict:
    """
    Start a group poll (ordering, study group, hangout).

    Example:
        start_group_poll(ember, [atlas, luna], "order",
                        "What does everyone want on the pizza?")
    """
    messages = []
    poll_id = f"poll-{datetime.now().strftime('%H%M%S')}"

    for navi in participants:
        msg = group_request(my_navi, navi, group_type, question)
        messages.append(msg)

    # Save poll state
    negotiations = _load_negotiations()
    negotiations[poll_id] = {
        "type": "group_poll",
        "status": "open",
        "group_type": group_type,
        "question": question,
        "participants": [n.to_dict() for n in participants],
        "responses": {},
        "started": datetime.now().isoformat(),
    }
    _save_negotiations(negotiations)

    log.info("[negotiate] Group poll started: %s (%d participants)",
             question, len(participants))

    return {
        "poll_id": poll_id,
        "messages": [m.to_dict() for m in messages],
        "participants": len(participants),
        "question": question,
    }


def record_poll_response(
    poll_id: str,
    responder_id: str,
    response: str,
) -> dict:
    """Record a response to a group poll."""
    negotiations = _load_negotiations()
    poll = negotiations.get(poll_id)

    if not poll:
        return {"error": f"Poll {poll_id} not found"}

    poll["responses"][responder_id] = {
        "response": response,
        "timestamp": datetime.now().isoformat(),
    }

    # Check if all participants responded
    expected = len(poll.get("participants", []))
    received = len(poll["responses"])

    if received >= expected:
        poll["status"] = "complete"

    _save_negotiations(negotiations)

    return {
        "poll_id": poll_id,
        "responses_received": received,
        "responses_expected": expected,
        "complete": poll["status"] == "complete",
        "all_responses": poll["responses"],
    }


def summarize_poll(poll_id: str) -> dict:
    """Summarize a completed poll for the user."""
    negotiations = _load_negotiations()
    poll = negotiations.get(poll_id)

    if not poll:
        return {"error": f"Poll {poll_id} not found"}

    responses = poll.get("responses", {})
    summary_text = []
    for navi_id, data in responses.items():
        summary_text.append(f"- {navi_id}: {data['response']}")

    return {
        "poll_id": poll_id,
        "question": poll.get("question", ""),
        "group_type": poll.get("group_type", ""),
        "status": poll.get("status", ""),
        "total_responses": len(responses),
        "summary": "\n".join(summary_text),
        "responses": responses,
    }


# ═══════════════════════════════════════════════════════════════
# Guardian Family Network
# ═══════════════════════════════════════════════════════════════

def send_guardian_alert(
    my_navi: NaviIdentity,
    family_contacts: list[NaviIdentity],
    threat_type: str,
    details: str,
) -> list[dict]:
    """
    Alert family members about a scam/threat.

    Example:
        send_guardian_alert(luna, [ember], "sms_scam",
            "Received text claiming to be IRS demanding $500")
    """
    alerts = []
    for family_navi in family_contacts:
        msg = guardian_alert(my_navi, family_navi, threat_type, details)
        alerts.append(msg.to_dict())

    log.info("[negotiate] Guardian alert sent to %d family members: %s",
             len(family_contacts), threat_type)

    return alerts


# ═══════════════════════════════════════════════════════════════
# Message Router — Process Incoming Messages
# ═══════════════════════════════════════════════════════════════

def process_incoming(msg: NaviMessage, my_navi: NaviIdentity) -> dict:
    """
    Process an incoming NaVi Protocol message.

    Returns:
        {
            "action": "auto_handled" | "needs_approval" | "notification",
            "display": "Human-readable summary for the UI",
            "response": optional auto-response message,
        }
    """
    sender_id = msg.sender.navi_id
    trust = get_trust_level(sender_id)

    # Check if expired
    if msg.is_expired():
        return {"action": "expired", "display": "Message expired."}

    # Update last seen
    update_last_seen(sender_id)

    # Route by message type
    if msg.msg_type == MessageType.PING:
        return {
            "action": "auto_handled",
            "display": f"👋 {msg.sender.display_name()} says hello!",
        }

    elif msg.msg_type == MessageType.NEGOTIATE:
        result = handle_meeting_proposal(msg, my_navi)
        return {
            "action": "needs_approval",
            "display": result.get("suggestion", "Meeting proposal received"),
            "negotiation": result,
        }

    elif msg.msg_type == MessageType.ASK:
        question = msg.payload.get("question", "")
        return {
            "action": "needs_approval",
            "display": (
                f"❓ {msg.sender.owner}'s {msg.sender.name} asks:\n"
                f"\"{question}\""
            ),
        }

    elif msg.msg_type == MessageType.TRADE:
        offering = msg.payload.get("offering", {})
        requesting = msg.payload.get("requesting")
        if requesting:
            display = (
                f"🔄 {msg.sender.name} offers {offering} "
                f"and wants {requesting}"
            )
        else:
            display = f"🎁 {msg.sender.name} wants to give you {offering}!"

        auto = should_auto_approve(sender_id, MessageType.TRADE)
        return {
            "action": "auto_handled" if auto else "needs_approval",
            "display": display,
        }

    elif msg.msg_type == MessageType.ADVENTURE:
        adventure_type = msg.payload.get("adventure_type", "adventure")
        return {
            "action": "needs_approval",
            "display": (
                f"⚔️ {msg.sender.name} (Lv.{msg.sender.level}) "
                f"challenges you to a {adventure_type}!"
            ),
        }

    elif msg.msg_type == MessageType.GUARDIAN_ALERT:
        threat = msg.payload.get("threat_type", "unknown")
        details = msg.payload.get("details", "")
        return {
            "action": "notification",
            "display": (
                f"🛡️ Guardian Alert from {msg.sender.owner}'s {msg.sender.name}:\n"
                f"{msg.sender.owner} received a {threat}.\n"
                f"Details: {details}\n"
                f"Status: Blocked ✅"
            ),
            "urgent": True,
        }

    elif msg.msg_type == MessageType.GROUP:
        question = msg.payload.get("question", "")
        return {
            "action": "needs_approval",
            "display": (
                f"👥 {msg.sender.owner}'s {msg.sender.name}: {question}"
            ),
        }

    elif msg.msg_type in (MessageType.APPROVE, MessageType.REJECT):
        status = "accepted" if msg.msg_type == MessageType.APPROVE else "declined"
        return {
            "action": "notification",
            "display": (
                f"📬 {msg.sender.owner}'s {msg.sender.name} "
                f"{status} your request."
            ),
            "response_data": msg.payload,
        }

    return {"action": "unknown", "display": f"Unknown message type: {msg.msg_type}"}
