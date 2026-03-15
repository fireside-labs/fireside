# Sprint 8 — Business Proposal: Hosted Mode + Executive Toolkit

> [!IMPORTANT]
> **ALL AGENTS:** Read this before starting Sprint 8.
> This document proposes a significant product expansion. Each agent should provide written feedback in `sprints/current/gates/feedback_[agent].md` before implementation begins.

---

## The Problem

The Valhalla Companion app currently **requires a home PC with an NVIDIA GPU**. This limits the addressable market to:
- Tech-savvy users who self-host
- People who own gaming PCs or workstations

This **excludes the highest-value customer**: executives, professionals, and non-technical users who would pay a premium for a private AI assistant on their phone but will never SSH into anything.

## Proposed Solution: Dual-Mode Architecture

### Mode 1: Self-Hosted (Existing)
- User runs Fireside on their own hardware
- Zero cost, full privacy, open source
- Phone connects via local IP / Tailscale / QR scan

### Mode 2: Hosted (New)
- User signs up with email on mobile app or web
- Fireside provisions a GPU container on RunPod/Modal
- Phone connects to `api.fireside.ai/v1/user/{id}`
- Subscription: $15-50/month depending on tier
- Data stored per-user in isolated containers

### The App Doesn't Change Much
The mobile app already talks to a `host` URL. For self-hosted users, it's `192.168.1.x:8765`. For hosted users, it's `api.fireside.ai`. Same API, same features, different backend location.

---

## Executive Toolkit (New Feature Set for Tool/Executive Mode)

### Why
An executive who pays $50/mo wants more than a chatbot. They want an **AI chief of staff** that:
- Triages their email overnight
- Manages their calendar
- Creates slide decks and spreadsheets on command
- Prepares meeting briefs
- All via voice on their phone

### Proposed Features

| Feature | API Endpoint | Backend Work (Thor) | Frontend (Freya) |
|---|---|---|---|
| Email triage | `GET /executive/inbox`, `POST /executive/email/send` | IMAP/SMTP integration plugin, AI triage | Inbox card, reply drafting UI |
| Calendar | `GET /executive/calendar`, `POST /executive/calendar/reschedule` | Google Calendar / CalDAV plugin | Timeline view, reschedule UI |
| Documents | `POST /executive/document/create` | Python-pptx, openpyxl generation | Command card, status tracking |
| Meeting prep | `GET /executive/meeting-prep/{id}` | Cross-reference emails + calendar | Briefing card before meetings |

### Privacy Angle
Even in hosted mode: "Your emails are processed by YOUR AI instance. We don't read them. We don't train on them. Your container is isolated."

---

## Revenue Model

| Tier | Price | What They Get |
|---|---|---|
| **Free** | $0 | Self-host on own hardware, all features |
| **Starter** | $15/mo | Hosted AI, chat + voice + companion |
| **Professional** | $30/mo | + Email triage + calendar + documents |
| **Executive** | $50/mo | + Priority GPU, larger models, dedicated support |
| **Marketplace** | 30% cut | Revenue share on paid plugins/themes/voices |

---

## Questions for Agent Review

### Thor (Backend)
1. Can the existing API layer support multi-tenant routing (one gateway → many user containers)?
2. What's the effort to build email (IMAP) and calendar (CalDAV) plugins?
3. Document generation (pptx, xlsx) — new plugin or extend existing?
4. How do we handle user data isolation in hosted containers?

### Heimdall (Security)
1. Hosted mode means we store user data. What security architecture is needed?
2. Email integration means accessing sensitive corporate data. Encryption at rest + in transit requirements?
3. Auth flow for hosted: OAuth2 / JWT? What provider?
4. Container isolation — what's the threat model for a compromised container?

### Valkyrie (QA/Review)
1. Does the executive toolkit dilute the companion identity? Or strengthen it?
2. Mode naming: "Pet Mode" vs "Executive Mode" vs "Companion" vs "Assistant" — what resonates?
3. Is the pricing right? Too cheap? Too expensive?
4. What's the MVP for hosted mode that we could ship as a beta?

---

## Decision Needed

> [!CAUTION]
> **Before Sprint 8 starts:** Each agent should drop their feedback file.
> Only proceed with implementation after the owner reviews all feedback.

Sprint 8 will then be finalized based on consensus.
