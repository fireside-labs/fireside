# Cloud Deploy Security Model

> **Module:** `middleware/task_integrity.py`  
> **Tests:** `tests/test_task_persistence_security.py` (38 tests)  
> **Sprint:** 11+12

---

## 1  Task Persistence

| Check | Implementation |
|-------|---------------|
| Checkpoint integrity | SHA256 hash of all fields, verified before resume |
| Tamper detection | Hash recomputed on load — any modification = rejection |
| File permissions | 600 (owner only) on checkpoint files |
| Stale task protection | Tasks > 24hr old flagged as stale |
| Resume validation | Status must be `in_progress`, step within bounds |

## 2  Context Compaction

9 injection patterns blocked during compression:
- `SYSTEM:`, `[INST]`/`[/INST]`, `<<SYS>>`, `<|im_start|>system`
- Prompt format injection (`Human: ... Assistant:`)
- "ignore previous", "new instructions:", "you are now"
- Compression ratio validation (5%–80%)

## 3  Discord Bot

| Check | Enforcement |
|-------|------------|
| Token storage | Must use `${DISCORD_BOT_TOKEN}`, not raw token |
| Permissions | 7 dangerous perms flagged (ADMINISTRATOR, BAN, KICK, MANAGE_*) |
| Guild allowlist | Warned if bot can join any server |
| DM blocking | Interactions without guild context rejected |

## 4  Cloud Deploy Hardening

### Required Firewall Rules
| Port | Status | Notes |
|------|--------|-------|
| 22/tcp | Open | SSH (key-auth only) |
| 443/tcp | Open | HTTPS (reverse proxy to API) |
| 8337 | **BLOCKED** | API — via reverse proxy only |
| 11434 | **BLOCKED** | Ollama — localhost only |
| 8080 | **BLOCKED** | llama-server — localhost only |

### SSH
- Password auth: **disabled**
- Root login: **disabled**
- Key-based auth only + fail2ban

### Secrets
- All secrets via `${ENV_VAR}` — hardcoded values rejected
- Auto security updates required
- Backups required

## 5  Rebrand Audit

6 leak patterns detected: `valhalla.ai`, `valhalla-mesh`, `api.valhalla`, `releases.valhalla`, old env vars. Internal refs (`valhalla.yaml`, theme name) exempted.

Install script audited for: HTTP downloads, `curl|bash` anti-pattern, missing checksums, root/sudo handling, temp file cleanup.

---

*Cloud deploy security model. Heimdall — Sprint 11+12 (2026-03-10).*
