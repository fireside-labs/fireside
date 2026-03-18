"""
social/protocol.py — NaVi Protocol: inter-agent message format.

This defines the message types and validation for Navi-to-Navi
communication. All messages are JSON, end-to-end encrypted,
and require explicit user approval before data is shared.

Protocol version: navi/1.0
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

log = logging.getLogger("valhalla.social.protocol")


# ═══════════════════════════════════════════════════════════════
# Protocol Constants
# ═══════════════════════════════════════════════════════════════

PROTOCOL_VERSION = "navi/1.0"
DEFAULT_TTL_HOURS = 24  # messages expire after 24h


class MessageType(str, Enum):
    """All NaVi Protocol message types."""
    PING = "ping"               # "Are you there?"
    ASK = "ask"                 # "What does your owner know about X?"
    NEGOTIATE = "negotiate"     # "Can we meet Tuesday at 2 PM?"
    SHARE = "share"             # Send a file, link, or note
    TRADE = "trade"             # Exchange adventure items
    ADVENTURE = "adventure"     # Co-op adventure challenge
    APPROVE = "approve"         # Yes to a request
    REJECT = "reject"           # No to a request
    STATUS = "status"           # "My owner is busy/free"
    GROUP = "group"             # Group coordination (pizza ordering, study groups)
    GUARDIAN_ALERT = "guardian_alert"  # Family scam alert


class TrustLevel(int, Enum):
    """Trust levels for contacts."""
    STRANGER = 0        # Can only ping
    ACQUAINTANCE = 1    # See name/species only
    FRIEND = 2          # Free/busy, trades, adventures
    FAMILY = 3          # Calendar access, guardian alerts


# What each trust level auto-approves
AUTO_APPROVE = {
    TrustLevel.STRANGER: set(),
    TrustLevel.ACQUAINTANCE: {MessageType.PING},
    TrustLevel.FRIEND: {MessageType.PING, MessageType.STATUS, MessageType.TRADE, MessageType.ADVENTURE},
    TrustLevel.FAMILY: {
        MessageType.PING, MessageType.STATUS, MessageType.TRADE,
        MessageType.ADVENTURE, MessageType.NEGOTIATE,
        MessageType.GUARDIAN_ALERT, MessageType.GROUP,
    },
}

# These ALWAYS require manual approval regardless of trust
ALWAYS_APPROVE = {MessageType.ASK, MessageType.SHARE}


# ═══════════════════════════════════════════════════════════════
# Navi Identity
# ═══════════════════════════════════════════════════════════════

@dataclass
class NaviIdentity:
    """A Navi's public identity card."""
    navi_id: str            # Unique ID: "ember-7x3k"
    name: str               # "Ember"
    species: str            # "dragon"
    owner: str              # "Jordan"
    level: int = 1          # Pet evolution level
    title: str = ""         # "Ember the Fierce"
    public_key: str = ""    # For E2E encryption

    def to_dict(self) -> dict:
        return asdict(self)

    def display_name(self) -> str:
        if self.title:
            return self.title
        return f"{self.name} ({self.owner}'s {self.species})"

    @classmethod
    def from_dict(cls, d: dict) -> NaviIdentity:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def generate_navi_id(name: str) -> str:
    """Generate a unique Navi ID like 'ember-7x3k'."""
    suffix = uuid.uuid4().hex[:4]
    return f"{name.lower()}-{suffix}"


# ═══════════════════════════════════════════════════════════════
# Protocol Messages
# ═══════════════════════════════════════════════════════════════

@dataclass
class NaviMessage:
    """A single NaVi Protocol message."""
    msg_id: str
    protocol: str
    msg_type: MessageType
    sender: NaviIdentity
    recipient: NaviIdentity
    payload: dict
    requires_approval: bool
    timestamp: str
    expires: str
    reply_to: Optional[str] = None  # msg_id this is replying to

    def to_dict(self) -> dict:
        return {
            "msg_id": self.msg_id,
            "protocol": self.protocol,
            "type": self.msg_type.value,
            "from": self.sender.to_dict(),
            "to": self.recipient.to_dict(),
            "payload": self.payload,
            "requires_approval": self.requires_approval,
            "timestamp": self.timestamp,
            "expires": self.expires,
            "reply_to": self.reply_to,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def is_expired(self) -> bool:
        try:
            exp = datetime.fromisoformat(self.expires)
            return datetime.now() > exp
        except Exception:
            return False

    @classmethod
    def from_dict(cls, d: dict) -> NaviMessage:
        return cls(
            msg_id=d["msg_id"],
            protocol=d.get("protocol", PROTOCOL_VERSION),
            msg_type=MessageType(d["type"]),
            sender=NaviIdentity.from_dict(d["from"]),
            recipient=NaviIdentity.from_dict(d["to"]),
            payload=d.get("payload", {}),
            requires_approval=d.get("requires_approval", True),
            timestamp=d.get("timestamp", datetime.now().isoformat()),
            expires=d.get("expires", ""),
            reply_to=d.get("reply_to"),
        )


# ═══════════════════════════════════════════════════════════════
# Message Factory
# ═══════════════════════════════════════════════════════════════

def create_message(
    msg_type: MessageType,
    sender: NaviIdentity,
    recipient: NaviIdentity,
    payload: dict,
    trust_level: TrustLevel = TrustLevel.STRANGER,
    ttl_hours: int = DEFAULT_TTL_HOURS,
    reply_to: Optional[str] = None,
) -> NaviMessage:
    """Create a properly formatted NaVi Protocol message."""
    now = datetime.now()

    # Determine if approval is needed
    if msg_type in ALWAYS_APPROVE:
        needs_approval = True
    elif msg_type in AUTO_APPROVE.get(trust_level, set()):
        needs_approval = False
    else:
        needs_approval = True

    return NaviMessage(
        msg_id=str(uuid.uuid4()),
        protocol=PROTOCOL_VERSION,
        msg_type=msg_type,
        sender=sender,
        recipient=recipient,
        payload=payload,
        requires_approval=needs_approval,
        timestamp=now.isoformat(),
        expires=(now + timedelta(hours=ttl_hours)).isoformat(),
        reply_to=reply_to,
    )


# ═══════════════════════════════════════════════════════════════
# Convenience message builders
# ═══════════════════════════════════════════════════════════════

def ping(sender: NaviIdentity, recipient: NaviIdentity) -> NaviMessage:
    """Simple ping — "Hey, are you there?" """
    return create_message(
        MessageType.PING, sender, recipient,
        payload={"message": f"{sender.name} says hello!"},
        ttl_hours=1,
    )


def ask(sender: NaviIdentity, recipient: NaviIdentity,
        question: str) -> NaviMessage:
    """Ask the other Navi's owner a question (ALWAYS needs approval)."""
    return create_message(
        MessageType.ASK, sender, recipient,
        payload={"question": question},
    )


def negotiate_meeting(
    sender: NaviIdentity, recipient: NaviIdentity,
    topic: str, proposed_times: list[str],
    duration_minutes: int = 30,
) -> NaviMessage:
    """Propose a meeting time."""
    return create_message(
        MessageType.NEGOTIATE, sender, recipient,
        payload={
            "topic": topic,
            "proposed_times": proposed_times,
            "duration_minutes": duration_minutes,
        },
    )


def share_item(
    sender: NaviIdentity, recipient: NaviIdentity,
    content_type: str, content: str, description: str = "",
) -> NaviMessage:
    """Share a link, note, or file reference."""
    return create_message(
        MessageType.SHARE, sender, recipient,
        payload={
            "content_type": content_type,  # "link", "note", "file"
            "content": content,
            "description": description,
        },
    )


def trade_item(
    sender: NaviIdentity, recipient: NaviIdentity,
    offering: dict, requesting: Optional[dict] = None,
) -> NaviMessage:
    """Propose a trade of adventure items."""
    return create_message(
        MessageType.TRADE, sender, recipient,
        payload={
            "offering": offering,      # {"item": "moonpetal", "qty": 1}
            "requesting": requesting,  # {"item": "sunstone", "qty": 1} or None for gift
        },
    )


def adventure_challenge(
    sender: NaviIdentity, recipient: NaviIdentity,
    adventure_type: str,
) -> NaviMessage:
    """Challenge another Navi to a co-op adventure."""
    return create_message(
        MessageType.ADVENTURE, sender, recipient,
        payload={
            "adventure_type": adventure_type,  # "boss_fight", "treasure_hunt", "riddle_duel"
            "sender_level": sender.level,
        },
    )


def guardian_alert(
    sender: NaviIdentity, recipient: NaviIdentity,
    threat_type: str, details: str,
) -> NaviMessage:
    """Alert a family member about a scam/threat."""
    return create_message(
        MessageType.GUARDIAN_ALERT, sender, recipient,
        payload={
            "threat_type": threat_type,  # "sms_scam", "email_phish", "suspicious_call"
            "details": details,
            "status": "blocked",
        },
    )


def group_request(
    sender: NaviIdentity, recipient: NaviIdentity,
    group_type: str, question: str,
) -> NaviMessage:
    """Group coordination message (ordering, study groups, etc.)."""
    return create_message(
        MessageType.GROUP, sender, recipient,
        payload={
            "group_type": group_type,  # "order", "study", "hangout"
            "question": question,
        },
    )


def approve(
    sender: NaviIdentity, recipient: NaviIdentity,
    original_msg_id: str, response_data: Optional[dict] = None,
) -> NaviMessage:
    """Approve a request."""
    return create_message(
        MessageType.APPROVE, sender, recipient,
        payload={"response": response_data or {}},
        reply_to=original_msg_id,
    )


def reject(
    sender: NaviIdentity, recipient: NaviIdentity,
    original_msg_id: str, reason: str = "",
) -> NaviMessage:
    """Reject a request."""
    return create_message(
        MessageType.REJECT, sender, recipient,
        payload={"reason": reason},
        reply_to=original_msg_id,
    )
