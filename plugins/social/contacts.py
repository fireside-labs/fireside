"""
social/contacts.py — Navi contact book and trust management.

Stores contacts locally at ~/.fireside/navi_contacts.json
Manages trust levels, StreetPass encounters, and friend lists.

No central server. Your contact book is YOUR data.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from plugins.social.protocol import (
    NaviIdentity, TrustLevel, MessageType,
    AUTO_APPROVE, ALWAYS_APPROVE,
)

log = logging.getLogger("valhalla.social.contacts")

# ═══════════════════════════════════════════════════════════════
# Storage
# ═══════════════════════════════════════════════════════════════

FIRESIDE_DIR = Path.home() / ".fireside"
CONTACTS_PATH = FIRESIDE_DIR / "navi_contacts.json"
STREETPASS_PATH = FIRESIDE_DIR / "navi_streetpass.json"
MY_IDENTITY_PATH = FIRESIDE_DIR / "navi_identity.json"


# ═══════════════════════════════════════════════════════════════
# My Navi Identity
# ═══════════════════════════════════════════════════════════════

def get_my_identity() -> Optional[NaviIdentity]:
    """Load this device's Navi identity."""
    if MY_IDENTITY_PATH.exists():
        try:
            data = json.loads(MY_IDENTITY_PATH.read_text(encoding="utf-8"))
            return NaviIdentity.from_dict(data)
        except Exception as e:
            log.warning("[contacts] Failed to load identity: %s", e)
    return None


def create_identity(name: str, species: str, owner: str,
                    level: int = 1) -> NaviIdentity:
    """Create and save this device's Navi identity."""
    from plugins.social.protocol import generate_navi_id
    navi = NaviIdentity(
        navi_id=generate_navi_id(name),
        name=name,
        species=species,
        owner=owner,
        level=level,
    )
    FIRESIDE_DIR.mkdir(parents=True, exist_ok=True)
    MY_IDENTITY_PATH.write_text(
        json.dumps(navi.to_dict(), indent=2), encoding="utf-8"
    )
    log.info("[contacts] Created identity: %s", navi.display_name())
    return navi


# ═══════════════════════════════════════════════════════════════
# Contact Book
# ═══════════════════════════════════════════════════════════════

def _load_contacts() -> dict:
    """Load the contact book. {navi_id: contact_data}"""
    if CONTACTS_PATH.exists():
        try:
            return json.loads(CONTACTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_contacts(contacts: dict):
    FIRESIDE_DIR.mkdir(parents=True, exist_ok=True)
    CONTACTS_PATH.write_text(json.dumps(contacts, indent=2), encoding="utf-8")


def add_contact(
    navi: NaviIdentity,
    trust_level: TrustLevel = TrustLevel.ACQUAINTANCE,
    nickname: str = "",
) -> dict:
    """Add a Navi to the contact book."""
    contacts = _load_contacts()
    contacts[navi.navi_id] = {
        "identity": navi.to_dict(),
        "trust_level": trust_level.value,
        "nickname": nickname or navi.owner,
        "added": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat(),
        "interaction_count": 0,
        "group": _trust_group_name(trust_level),
    }
    _save_contacts(contacts)
    log.info("[contacts] Added %s (trust: %s)", navi.display_name(), trust_level.name)
    return contacts[navi.navi_id]


def remove_contact(navi_id: str) -> bool:
    """Remove a Navi from contacts."""
    contacts = _load_contacts()
    if navi_id in contacts:
        name = contacts[navi_id].get("identity", {}).get("name", navi_id)
        del contacts[navi_id]
        _save_contacts(contacts)
        log.info("[contacts] Removed %s", name)
        return True
    return False


def get_contact(navi_id: str) -> Optional[dict]:
    """Get a contact by Navi ID."""
    return _load_contacts().get(navi_id)


def get_trust_level(navi_id: str) -> TrustLevel:
    """Get trust level for a Navi. Defaults to STRANGER."""
    contact = get_contact(navi_id)
    if contact:
        return TrustLevel(contact.get("trust_level", 0))
    return TrustLevel.STRANGER


def set_trust_level(navi_id: str, level: TrustLevel) -> bool:
    """Update a contact's trust level."""
    contacts = _load_contacts()
    if navi_id in contacts:
        contacts[navi_id]["trust_level"] = level.value
        contacts[navi_id]["group"] = _trust_group_name(level)
        _save_contacts(contacts)
        log.info("[contacts] Set %s trust → %s", navi_id, level.name)
        return True
    return False


def update_last_seen(navi_id: str):
    """Update the last_seen timestamp for a contact."""
    contacts = _load_contacts()
    if navi_id in contacts:
        contacts[navi_id]["last_seen"] = datetime.now().isoformat()
        contacts[navi_id]["interaction_count"] = (
            contacts[navi_id].get("interaction_count", 0) + 1
        )
        _save_contacts(contacts)


def get_all_contacts() -> list[dict]:
    """Get all contacts, grouped by trust level."""
    contacts = _load_contacts()
    result = []
    for navi_id, data in contacts.items():
        entry = {
            "navi_id": navi_id,
            **data,
        }
        result.append(entry)

    # Sort: Family first, then Friends, then Acquaintances
    result.sort(key=lambda c: -c.get("trust_level", 0))
    return result


def get_contacts_by_trust(level: TrustLevel) -> list[dict]:
    """Get contacts at a specific trust level."""
    return [c for c in get_all_contacts() if c.get("trust_level") == level.value]


def should_auto_approve(navi_id: str, msg_type: MessageType) -> bool:
    """Check if a message type should be auto-approved for this contact."""
    if msg_type in ALWAYS_APPROVE:
        return False  # Always needs manual approval

    trust = get_trust_level(navi_id)
    return msg_type in AUTO_APPROVE.get(trust, set())


# ═══════════════════════════════════════════════════════════════
# StreetPass — Passive BLE Encounters
# ═══════════════════════════════════════════════════════════════

def _load_streetpass() -> list:
    if STREETPASS_PATH.exists():
        try:
            return json.loads(STREETPASS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_streetpass(encounters: list):
    FIRESIDE_DIR.mkdir(parents=True, exist_ok=True)
    STREETPASS_PATH.write_text(json.dumps(encounters, indent=2), encoding="utf-8")


def record_streetpass(navi: NaviIdentity, location_hint: str = "") -> dict:
    """Record a StreetPass encounter (BLE discovery)."""
    encounters = _load_streetpass()
    encounter = {
        "navi_id": navi.navi_id,
        "name": navi.name,
        "species": navi.species,
        "owner": navi.owner,
        "level": navi.level,
        "timestamp": datetime.now().isoformat(),
        "location": location_hint,  # "Starbucks", "Library", etc. (user-set, not GPS)
    }
    encounters.append(encounter)

    # Keep last 100 encounters
    if len(encounters) > 100:
        encounters = encounters[-100:]

    _save_streetpass(encounters)
    log.info("[contacts] StreetPass! Met %s (%s's %s)",
             navi.name, navi.owner, navi.species)
    return encounter


def get_today_streetpass() -> list[dict]:
    """Get today's StreetPass encounters."""
    encounters = _load_streetpass()
    today = datetime.now().date().isoformat()
    return [e for e in encounters if e.get("timestamp", "").startswith(today)]


def get_streetpass_stats() -> dict:
    """Get StreetPass statistics."""
    encounters = _load_streetpass()
    today = get_today_streetpass()
    unique_navis = len(set(e.get("navi_id", "") for e in encounters))

    return {
        "total_encounters": len(encounters),
        "today": len(today),
        "unique_navis_met": unique_navis,
        "today_navis": [
            {"name": e["name"], "species": e["species"],
             "time": e["timestamp"], "location": e.get("location", "")}
            for e in today
        ],
    }


# ═══════════════════════════════════════════════════════════════
# Network Summary (for the UI)
# ═══════════════════════════════════════════════════════════════

def get_network_summary() -> dict:
    """Get a summary of the Navi Network for the dashboard/mobile."""
    contacts = get_all_contacts()
    streetpass = get_streetpass_stats()
    my_id = get_my_identity()

    family = [c for c in contacts if c.get("trust_level") == TrustLevel.FAMILY.value]
    friends = [c for c in contacts if c.get("trust_level") == TrustLevel.FRIEND.value]
    acquaintances = [c for c in contacts if c.get("trust_level") == TrustLevel.ACQUAINTANCE.value]

    return {
        "my_navi": my_id.to_dict() if my_id else None,
        "total_contacts": len(contacts),
        "family": len(family),
        "friends": len(friends),
        "acquaintances": len(acquaintances),
        "contacts": contacts,
        "streetpass": streetpass,
        "online": [c for c in contacts
                   if _is_recently_seen(c.get("last_seen", ""))],
    }


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _trust_group_name(level: TrustLevel) -> str:
    return {
        TrustLevel.STRANGER: "Strangers",
        TrustLevel.ACQUAINTANCE: "Acquaintances",
        TrustLevel.FRIEND: "Friends",
        TrustLevel.FAMILY: "Family",
    }.get(level, "Unknown")


def _is_recently_seen(timestamp: str, minutes: int = 15) -> bool:
    """Check if a Navi was seen within the last N minutes."""
    if not timestamp:
        return False
    try:
        seen = datetime.fromisoformat(timestamp)
        delta = datetime.now() - seen
        return delta.total_seconds() < minutes * 60
    except Exception:
        return False
