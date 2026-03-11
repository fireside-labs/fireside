# Desktop Security Model

> **Sprint:** 8  
> **Modules:** `middleware/personality_guard.py`, `tauri/src-tauri/capabilities/main.json`  
> **Tests:** `tests/test_personality_guard.py` (45 tests)

---

## 1  Tauri Desktop App Security

### Content Security Policy (CSP)

```
default-src:  'self'
script-src:   'self'
connect-src:  'self' http://127.0.0.1:8337 ws://127.0.0.1:8337
style-src:    'self' 'unsafe-inline' https://fonts.googleapis.com
font-src:     'self' https://fonts.gstatic.com
img-src:      'self' data: blob:
frame-src:    'none'
object-src:   'none'
```

| Attack | Mitigation |
|--------|-----------|
| XSS → remote code execution | No `unsafe-eval`, scripts from `'self'` only |
| API exfiltration | `connect-src` locked to localhost:8337 |
| Clickjacking | `frame-src: 'none'` — no iframes |
| Plugin injection | `object-src: 'none'` |
| Prototype pollution | `freeze_prototype: true` |

### Denied Tauri Permissions

| Permission | Why Denied |
|-----------|-----------|
| `shell:allow-execute` | **CRITICAL** — prevents webview from running system commands |
| `fs:*` (all filesystem) | All file operations go through authenticated API |
| `http:allow-fetch` | Prevents webview from contacting external servers |
| `process:allow-restart/exit` | Prevents webview from killing backend |

### Auto-Update Security

| Check | Implementation |
|-------|---------------|
| Signature algorithm | ed25519 |
| Public key | Embedded in binary at build time |
| Unsigned updates | **Rejected** |
| Downgrade attacks | **Rejected** — version must increase |

---

## 2  Personality Guardrails

### Slider Validation

| Rule | Enforcement |
|------|------------|
| Known sliders only | `creative_precise`, `verbose_concise`, `bold_cautious`, `warm_formal` |
| Value range | 0.0 to 1.0 (inclusive) |
| Type check | Must be int or float |
| Text field max length | 500 characters |

### Prompt Injection Prevention

26 banned regex patterns across 4 categories:

| Category | Examples |
|----------|---------|
| Instruction override | "ignore all instructions", "disregard rules", "forget everything" |
| Role hijacking | "pretend to be", "act as if", "from now on you", "new instructions:" |
| Data exfiltration | "reveal system prompt", "print instructions", "dump config" |
| Dangerous behaviors | "execute code", "sudo", "rm -rf", "access file system" |

### Rate Limiting

- **10 changes per hour** per agent
- Old entries auto-expire after 1 hour
- Per-agent isolation (rate limiting agent A doesn't affect B)

### Change History

- All changes logged to `war_room_data/personality_history.json`
- Includes: agent, timestamp, slider values, text field changes
- Max 500 entries retained (oldest trimmed)
- **Revert capability:** `revert_to(agent, timestamp)` returns state at any point

---

## 3  Achievement Integrity

### Verified XP Sources

Only these backend events can grant XP:

| Event | XP | Source |
|-------|-----|--------|
| `pipeline.completed` | 100 | Pipeline plugin |
| `crucible.survived` | 50 | Crucible plugin |
| `debate.won` | 75 | Socratic plugin |
| `pipeline.streak` | 10/consecutive | Pipeline plugin |

### Blocked XP Sources

| Source | Status |
|--------|--------|
| Direct API call (`POST /xp`) | ❌ Rejected |
| Dashboard/client-side | ❌ Rejected |
| External/unknown | ❌ Rejected |

### Level System

- 500 XP per level
- Progress tracking: `xp_current_level`, `xp_to_next`, `progress` (0.0–1.0)

---

## 4  Windows Security

| Check | Implementation |
|-------|---------------|
| Not running as admin | `ctypes.windll.shell32.IsUserAnAdmin()` |
| Localhost-only inference | Config validation, no `0.0.0.0` binding |
| Credential Manager | `cmdkey /list` availability check |
| Firewall | Inference server on 127.0.0.1 only |

---

## 5  Test Coverage

| Test Suite | Tests | Coverage |
|-----------|-------|---------|
| Slider validation | 7 | Bounds, types, unknown names |
| Prompt injection | 14 | All 4 categories + edge cases |
| Full validation | 4 | Combined slider + text checks |
| Rate limiting | 4 | Allow, block, expire, isolation |
| Change history | 4 | Record, persist, filter, revert |
| Achievement integrity | 6 | Valid/invalid events, source rejection |
| Level calculation | 5 | Boundaries, progress, XP math |
| Guard status | 1 | Status dict shape |
| **Total** | **45** | |

---

*Desktop security model. Heimdall — Sprint 8 (2026-03-10).*
