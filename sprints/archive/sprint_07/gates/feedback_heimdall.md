# Heimdall — Sprint 8 Proposal Feedback

**Read:** AGENTS.md → PROPOSAL_SPRINT8.md → SPRINT_HEIMDALL.md

---

## Summary: 🔴 HIGH Concerns — Proceed with Caution

Hosted mode + email integration is the **highest-risk feature set we've ever shipped**. We're moving from "user's own data on their own hardware" to "we store and process user email credentials and corporate data." This fundamentally changes the threat model.

---

## Security Architecture Requirements

### 1. Email Credential Storage — 🔴 CRITICAL
**Problem:** We will store IMAP/SMTP credentials or OAuth tokens that give us access to users' email.

**Requirements:**
- Credentials MUST be encrypted at rest with **AES-256-GCM** (Fernet is acceptable as a Python wrapper)
- Encryption key MUST be derived per-user (not a single master key for all users)
- OAuth tokens are preferred over passwords — they can be scoped and revoked
- Token refresh flow must handle expiration gracefully
- **NEVER log email credentials, even in debug mode**
- If a container is compromised, only THAT user's tokens are exposed (isolation)

**Recommendation:** Use OAuth2 exclusively. Store refresh tokens encrypted. Never store raw passwords.

### 2. Container Isolation — 🔴 CRITICAL
**Problem:** If we use shared infrastructure, one user's data could leak to another.

**Requirements:**
- Each hosted user MUST get their own isolated container (no shared memory/filesystem)
- No shared database — each container has its own SQLite/state files
- Network isolation between containers (no inter-container traffic)
- Container filesystem wiped on user account deletion

**Recommendation:** RunPod Serverless with ephemeral containers is good. Persistent state should be in encrypted object storage (S3/R2) per-user, not on container local disk.

### 3. Auth Flow — 🟡 MEDIUM
**Requirements:**
- JWT with **short expiration** (15 min access token, 7 day refresh token)
- Refresh token rotation (each refresh invalidates the old token)
- Rate limiting on auth endpoints (prevent brute force)
- Email verification required before accessing executive features
- Password requirements: 12+ characters or passphrase, bcrypt with cost factor ≥ 12

**Recommendation:** Strongly consider **Supabase Auth or Firebase Auth** instead of rolling our own. They handle email verification, password reset, OAuth, rate limiting, and MFA out of the box. Rolling our own auth is where startups get breached.

### 4. Data in Transit — 🟡 MEDIUM
- Hosted mode MUST use HTTPS (TLS 1.2+). No HTTP fallback.
- WebSocket connections MUST use WSS, not WS.
- Self-hosted mode can remain HTTP (local network), but hosted mode CANNOT.

### 5. GDPR/Privacy Compliance — 🟡 MEDIUM
- If we serve EU users, we need: data export, data deletion, consent management
- Privacy policy must be updated to cover hosted mode data handling
- "We don't read your emails" needs to be technically enforced, not just promised

---

## Threat Model for Hosted Mode

| Threat | Impact | Mitigation |
|---|---|---|
| Compromised container | User's email/calendar data exposed | Per-user isolation, encrypted credentials |
| API gateway breach | All user routing exposed | Gateway has no user data, only routing tokens |
| Stolen JWT | Session hijack | Short expiration, refresh rotation, IP binding |
| Insider threat (us) | We could read user emails | Audit logging, encryption keys held by user? |
| RunPod compromise | All containers exposed | Encrypted state at rest, credential rotation |

## The Insider Threat Question

> [!WARNING]
> The moment we process user emails, we face a fundamental trust question: **can users trust that WE don't read their emails?** Even with encryption, the LLM running in our container sees the plaintext. We need to decide: is the privacy promise "your data doesn't leave your container" or "your data doesn't leave your hardware"?

For self-hosted users, the answer is clear — it's their hardware. For hosted users, we need to be transparent: "Your data is processed in an isolated container that only your AI accesses. We cannot see it. But it runs on cloud infrastructure, not your personal hardware."

---

## Verdict

✅ **Proceed** — but with these mandatory security requirements:
1. OAuth tokens only (no stored passwords) for email/calendar
2. Supabase/Firebase Auth (don't roll our own)
3. Per-user container isolation (no multi-tenancy in shared process)
4. HTTPS/WSS mandatory for hosted mode
5. Updated privacy policy before hosted mode beta
