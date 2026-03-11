# Installer Security Model

> **Module:** `plugins/brain-installer/credential_store.py`  
> **Tests:** `tests/test_credential_store.py` (36 tests)  
> **Sprint:** 7

---

## 1  Credential Storage

### Architecture
```
~/.valhalla/                 (dir mode 700)
├── credentials              (file mode 600, AES-256-GCM encrypted JSON)
└── .salt                    (file mode 600, 32-byte random salt)
```

### Encryption
- **Algorithm:** AES-256-GCM (via `cryptography` package)
- **Key derivation:** PBKDF2-SHA256, 100,000 iterations
- **Key source:** Machine-specific ID + random salt
  - macOS: `IOPlatformSerialNumber` from `ioreg`
  - Linux: `/etc/machine-id`
  - Fallback: hostname + platform + username hash
- **Graceful fallback:** XOR obfuscation if `cryptography` not installed (warning logged)

### Rules
| Rule | Enforcement |
|------|-------------|
| API keys never in `valhalla.yaml` | Config validator checks for literal keys |
| Dashboard never sees full keys | `get_masked()` returns `nvap...f456` format |
| File permissions always 600 | Set on every save, verified by `_check_permissions()` |
| Directory permissions 700 | Set on creation |
| Empty values rejected | `ValueError` on `set("", ...)` |

---

## 2  GGUF Download Verification

| Check | Implementation |
|-------|---------------|
| SHA256 checksum | `verify_gguf_checksum(path, expected)` streaming hash |
| File existence | Checked before hash |
| Mismatch detection | CRITICAL log with expected vs actual hash |

---

## 3  Binary Verification (llama-server)

| Check | Implementation |
|-------|---------------|
| File exists | Path check |
| Size reasonable | 1 MB – 500 MB (prevents truncation/bloat) |
| Executable permission | `os.access(X_OK)` check |
| macOS code signature | `codesign -v` (warning if unsigned — common for community builds) |

---

## 4  PyPI Package Validation

| Check | Implementation |
|-------|---------------|
| Trusted list | `mlx-lm`, `mlx`, `transformers`, `huggingface-hub`, etc. |
| PyPI existence | HTTP check against `pypi.org/pypi/{name}/json` |
| Typosquat warning | Flagged if not in trusted list |

---

## 5  Process Isolation

| Check | Default | Enforcement |
|-------|---------|-------------|
| Not running as root | Required | `os.getuid()` check |
| Localhost binding | `localhost` | Config validation |
| Model dir permissions | Not world-readable | `stat()` check on `~/.cache/huggingface`, `~/.cache/mlx`, `~/.ollama` |

---

## 6  Telegram Security

| Threat | Mitigation |
|--------|-----------|
| Bot token in config file | Rejected — must use `${TELEGRAM_BOT_TOKEN}` env ref; stored in credential store |
| Sensitive data via Telegram | `sanitize_telegram_message()` redacts API keys, passwords, tokens, long strings |
| Unauthorized users | `allowed_users` whitelist (Telegram user IDs). Empty = open mode (warned). |
| Risky notification events | `config.changed`, `credential.stored`, `debug` flagged as potentially leaking data |
| Spam/abuse | Rate limiting (via existing `middleware/rate_limiter.py`) |

---

*Installer security model. Heimdall — Sprint 7 (2026-03-10).*
