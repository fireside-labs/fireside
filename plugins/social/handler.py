"""
social/handler.py — Social Graph API routes.

Routes:
    POST /social/identity       — Create/get my Navi identity
    GET  /social/contacts       — List all contacts
    POST /social/contacts/add   — Add a contact
    POST /social/contacts/trust — Set trust level
    GET  /social/streetpass     — Get StreetPass encounters
    POST /social/streetpass     — Record a StreetPass encounter
    POST /social/send           — Send a NaVi Protocol message
    POST /social/receive        — Process an incoming message
    POST /social/negotiate      — Start a meeting negotiation
    POST /social/poll           — Start a group poll
    GET  /social/network        — Get full network summary
"""
# NOTE: Do NOT use 'from __future__ import annotations' here — it breaks
# FastAPI's Pydantic body detection for POST routes.


import logging

log = logging.getLogger("valhalla.social")


def register_routes(app, config: dict = None):
    """Register Social Graph routes with the FastAPI app."""
    from pydantic import BaseModel

    from plugins.social.protocol import (
        NaviIdentity, NaviMessage, MessageType, TrustLevel,
        ping, ask, negotiate_meeting, share_item, trade_item,
        adventure_challenge, guardian_alert, group_request,
    )
    from plugins.social.contacts import (
        get_my_identity, create_identity,
        add_contact, remove_contact, get_contact,
        set_trust_level, get_all_contacts,
        record_streetpass, get_streetpass_stats, get_network_summary,
    )
    from plugins.social.negotiate import (
        propose_meeting, start_group_poll, record_poll_response,
        summarize_poll, send_guardian_alert, process_incoming,
    )

    # ── Request Models ──

    class IdentityRequest(BaseModel):
        name: str
        species: str
        owner: str

    class AddContactRequest(BaseModel):
        navi_id: str
        name: str
        species: str
        owner: str
        trust_level: int = 1  # ACQUAINTANCE

    class TrustRequest(BaseModel):
        navi_id: str
        trust_level: int

    class StreetPassRequest(BaseModel):
        navi_id: str
        name: str
        species: str
        owner: str
        level: int = 1
        location: str = ""

    class SendMessageRequest(BaseModel):
        to_navi_id: str
        type: str  # "ping", "ask", "negotiate", etc.
        payload: dict = {}

    class NegotiateRequest(BaseModel):
        to_navi_id: str
        topic: str
        available_times: list[str]
        duration_minutes: int = 30

    class PollRequest(BaseModel):
        participant_ids: list[str]
        group_type: str  # "order", "study", "hangout"
        question: str

    # ── Identity ──

    @app.post("/social/identity")
    async def handle_identity(req: IdentityRequest):
        """Create or get my Navi identity."""
        existing = get_my_identity()
        if existing:
            return {"exists": True, "identity": existing.to_dict()}
        navi = create_identity(req.name, req.species, req.owner)
        return {"exists": False, "identity": navi.to_dict()}

    @app.get("/social/identity")
    async def handle_get_identity():
        """Get my Navi identity."""
        navi = get_my_identity()
        if navi:
            return {"identity": navi.to_dict()}
        return {"identity": None, "message": "No identity created yet"}

    # ── Contacts ──

    @app.get("/social/contacts")
    async def handle_contacts():
        """List all contacts."""
        return {"contacts": get_all_contacts()}

    @app.post("/social/contacts/add")
    async def handle_add_contact(req: AddContactRequest):
        """Add a Navi to contacts."""
        navi = NaviIdentity(
            navi_id=req.navi_id, name=req.name,
            species=req.species, owner=req.owner,
        )
        result = add_contact(navi, TrustLevel(req.trust_level))
        return {"added": True, "contact": result}

    @app.post("/social/contacts/trust")
    async def handle_set_trust(req: TrustRequest):
        """Update a contact's trust level."""
        success = set_trust_level(req.navi_id, TrustLevel(req.trust_level))
        return {"updated": success, "navi_id": req.navi_id,
                "trust_level": req.trust_level}

    @app.delete("/social/contacts/{navi_id}")
    async def handle_remove_contact(navi_id: str):
        """Remove a contact."""
        return {"removed": remove_contact(navi_id)}

    # ── StreetPass ──

    @app.get("/social/streetpass")
    async def handle_streetpass():
        """Get StreetPass stats and today's encounters."""
        return get_streetpass_stats()

    @app.post("/social/streetpass")
    async def handle_record_streetpass(req: StreetPassRequest):
        """Record a BLE StreetPass encounter."""
        navi = NaviIdentity(
            navi_id=req.navi_id, name=req.name,
            species=req.species, owner=req.owner, level=req.level,
        )
        encounter = record_streetpass(navi, req.location)
        return {"recorded": True, "encounter": encounter}

    # ── Messaging ──

    @app.post("/social/send")
    async def handle_send(req: SendMessageRequest):
        """Create a NaVi Protocol message to send."""
        my_navi = get_my_identity()
        if not my_navi:
            return {"ok": False, "error": "No identity. Create one first via POST /social/identity"}

        contact = get_contact(req.to_navi_id)
        if not contact:
            return {"ok": False, "error": f"Contact {req.to_navi_id} not found"}

        their_navi = NaviIdentity.from_dict(contact["identity"])
        msg_type = MessageType(req.type)

        # Build message based on type
        builders = {
            "ping": lambda: ping(my_navi, their_navi),
            "ask": lambda: ask(my_navi, their_navi, req.payload.get("question", "")),
            "share": lambda: share_item(my_navi, their_navi,
                                        req.payload.get("content_type", "note"),
                                        req.payload.get("content", "")),
            "trade": lambda: trade_item(my_navi, their_navi,
                                        req.payload.get("offering", {}),
                                        req.payload.get("requesting")),
            "adventure": lambda: adventure_challenge(my_navi, their_navi,
                                                     req.payload.get("adventure_type", "boss_fight")),
        }

        builder = builders.get(req.type)
        if builder:
            msg = builder()
            return {"ok": True, "message": msg.to_dict()}
        else:
            return {"ok": False, "error": f"Unknown message type: {req.type}"}

    @app.post("/social/receive")
    async def handle_receive(request):
        """Process an incoming NaVi Protocol message."""
        body = await request.json()
        my_navi = get_my_identity()
        if not my_navi:
            return {"ok": False, "error": "No identity"}

        try:
            msg = NaviMessage.from_dict(body)
            result = process_incoming(msg, my_navi)
            return {"ok": True, **result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Negotiation ──

    @app.post("/social/negotiate")
    async def handle_negotiate(req: NegotiateRequest):
        """Start a meeting negotiation with another Navi."""
        my_navi = get_my_identity()
        if not my_navi:
            return {"ok": False, "error": "No identity"}

        contact = get_contact(req.to_navi_id)
        if not contact:
            return {"ok": False, "error": f"Contact {req.to_navi_id} not found"}

        their_navi = NaviIdentity.from_dict(contact["identity"])
        msg = propose_meeting(
            my_navi, their_navi, req.topic,
            req.available_times, req.duration_minutes,
        )
        return {"ok": True, "message": msg.to_dict(), "topic": req.topic}

    @app.post("/social/poll")
    async def handle_poll(req: PollRequest):
        """Start a group poll."""
        my_navi = get_my_identity()
        if not my_navi:
            return {"ok": False, "error": "No identity"}

        participants = []
        for navi_id in req.participant_ids:
            contact = get_contact(navi_id)
            if contact:
                participants.append(NaviIdentity.from_dict(contact["identity"]))

        if not participants:
            return {"ok": False, "error": "No valid participants found"}

        result = start_group_poll(
            my_navi, participants, req.group_type, req.question,
        )
        return {"ok": True, **result}

    # ── Network Summary ──

    @app.get("/social/network")
    async def handle_network():
        """Get full network summary for the dashboard."""
        return get_network_summary()

    log.info("[social] Routes registered: /social/identity, /social/contacts, "
             "/social/streetpass, /social/send, /social/receive, "
             "/social/negotiate, /social/poll, /social/network")
