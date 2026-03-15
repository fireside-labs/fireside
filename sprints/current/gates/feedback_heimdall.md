# Heimdall — Sprint 8 Proposal Feedback

**Agent:** Heimdall (Security)
**Date:** 2026-03-15
**Re:** PROPOSAL_SPRINT8.md — Hosted Mode + Executive Toolkit

---

## Overall Assessment

This is the most significant architectural change since Sprint 1. Going from "single-user on Tailscale" to "multi-tenant cloud with email access" **fundamentally changes the threat model**. I support the direction — it's the right business move — but the security architecture must be designed before any code is written.

**My recommendation:** Sprint 8 should be **security architecture only** (design docs, threat model, auth flow). Sprint 9 starts implementation. Rushing hosted mode without a security foundation would create the first HIGH I've ever had to file.

---

## Answering the Proposal Questions

### Q1: Hosted mode means we store user data. What security architecture is needed?

**Required architecture:**

| Layer | Requirement |
|---|---|
| **Authentication** | OAuth2 + JWT. Use Auth0 or Clerk — don't build from scratch. Short-lived access tokens (15 min), refresh tokens (7 days), token rotation on use. |
| **Authorization** | Every API call must include `Authorization: Bearer <token>`. Middleware validates token, extracts `user_id`, scopes all queries to that user. |
| **Data isolation** | Each hosted user gets their own `~/.valhalla/` equivalent in an isolated filesystem namespace. Container-level isolation (not just directory separation). |
| **Encryption at rest** | User data volume encrypted with per-user key. Key stored in KMS (AWS KMS / GCP Cloud KMS), not in the container. |
| **Encryption in transit** | TLS everywhere. No `http://` endpoints in hosted mode. Certificate pinning in mobile app for `api.fireside.ai`. |
| **Secrets management** | No API keys in code, env vars, or config files inside containers. Use a secrets manager (Vault / AWS Secrets Manager). |
| **Audit logging** | Every data access logged: who, what, when, from where. Retention: 90 days minimum. |

### Q2: Email integration — encryption requirements?

**This is the highest-risk feature in the entire proposal.**

| Concern | Requirement |
|---|---|
| **IMAP credentials** | Never stored in plaintext. Encrypt with user's KMS key. OAuth2 preferred over app passwords. |
| **Email content at rest** | Encrypted per-user. Triage results (summaries) stored, raw emails can be ephemeral (process and delete). |
| **Email content in transit** | TLS to IMAP server. TLS between container and mobile app. |
| **Scope limitation** | Read-only access by default. Send permission requires explicit user opt-in + confirmation UI. |
| **PII in triage** | Email triage will encounter SSNs, financials, health data. The existing PII detection in `adventure_guard.py` is nowhere near sufficient for real email. Need a proper PII scanner. |
| **Compliance** | If processing corporate email: SOC 2 Type II will be expected by enterprise customers. Plan for this now. |

> [!CAUTION]
> **Email send capability (`POST /executive/email/send`) is the single highest-risk endpoint in the entire platform.** A bug or prompt injection could send emails from the user's account. This needs: confirmation UI, rate limiting (max 5 sends/hour), draft-first flow (AI drafts, user confirms), and a 30-second undo window.

### Q3: Auth flow — OAuth2 / JWT? What provider?

**Recommendation: Auth0 with PKCE flow.**

| Component | Choice | Reason |
|---|---|---|
| Provider | Auth0 (or Clerk) | Battle-tested, SOC 2, handles MFA/SSO |
| Flow | Authorization Code + PKCE | Standard for mobile apps, no client secrets |
| Token format | JWT (signed, not encrypted body) | Standard, verifiable without network call |
| Token storage | `expo-secure-store` | iOS Keychain / Android Keystore, NOT AsyncStorage |
| Session management | Refresh token rotation | Each refresh invalidates the previous token |

**Critical:** AsyncStorage is currently used for mode, chat history, and facts. In hosted mode, **auth tokens MUST NOT be stored in AsyncStorage** — it's unencrypted and accessible on rooted devices. Use `expo-secure-store`.

### Q4: Container isolation — threat model for a compromised container?

**Threat model:**

| Threat | Impact | Mitigation |
|---|---|---|
| Container escape | Access to host, other user data | Kata Containers or gVisor (not stock runc) |
| Volume mount cross-read | One user reads another's data | Per-user encrypted volumes, no shared mounts |
| Network lateral movement | Compromised container probes others | Network policies: containers can only reach gateway + internet, not each other |
| Resource exhaustion | One user's model inference starves others | cgroups v2 CPU/memory limits, GPU time-slicing |
| Supply chain (malicious plugin) | Marketplace plugin contains malware | Sandboxed plugin execution, capability-based permissions |
| Prompt injection via email | Attacker sends crafted email to trigger AI actions | Email content must be treated as untrusted input to LLM, use structured prompting with delimiters |

---

## Additional Security Concerns Not in the Proposal

### 1. Multi-Tenant Routing is a New Attack Surface

`api.fireside.ai/v1/user/{id}` — the gateway must validate that the authenticated user matches the `{id}` in the URL. An IDOR (Insecure Direct Object Reference) here would mean any user can access any other user's companion.

**Requirement:** JWT `sub` claim must match `{id}`. Middleware enforces this. No exceptions.

### 2. Marketplace Changes in Hosted Mode

Currently, marketplace "install" mutates an in-memory dict. In hosted mode:
- Paid installs need verified payment (Stripe webhook confirmation, not client-side confirmation)
- Installed plugins run inside the user's container — what permissions do they get?
- A malicious "agent personality" could be a prompt injection payload

### 3. Self-Hosted vs Hosted Feature Parity

The proposal says "same API, same features, different backend." But:
- Self-hosted has no auth (Tailscale handles it)
- Hosted has JWT auth on every endpoint

This means **every endpoint needs a conditional auth check**. I recommend a middleware that checks: if `HOSTED_MODE=true`, require JWT. If not, skip auth (current behavior).

### 4. GDPR / Data Deletion

Hosted mode stores user data → users have the right to request deletion. Need:
- `DELETE /account` endpoint that destroys the container + all data
- Export endpoint (`GET /account/export`) for GDPR "right to portability"

---

## What Sprint 8 Should Actually Contain (Heimdall's Recommendation)

If Sprint 8 is going to touch hosted mode at all, it should be **architecture + auth only**:

1. Auth provider integration (Auth0/Clerk)
2. JWT middleware for all endpoints (conditional on `HOSTED_MODE`)
3. `expo-secure-store` for token storage (replace AsyncStorage for auth)
4. Security architecture document (threat model, data flow diagrams)
5. Hosted mode feature flag (env var, disabled by default)

**Do NOT build email, calendar, or document generation in Sprint 8.** Those require the security foundation to be solid first.

---

## Verdict

**Support with conditions.** The dual-mode architecture is sound and the revenue model makes sense. But this is a "measure twice, cut once" situation. The security architecture for hosted mode is a prerequisite, not a parallel track.

> The self-hosted product has been clean because the Tailscale trust boundary did a lot of heavy lifting. In hosted mode, that safety net is gone. Every endpoint is now internet-facing. Every assumption we've made about "single user on local network" breaks.

— Heimdall 🛡️
