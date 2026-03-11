# Thor Sprint 1 — Walkthrough

## What Was Built

Plugin-based Bifrost V2 backend replacing the V1 monolith. 10 files created/modified, 67 tests passing.

### Files Created

| File | Purpose |
|---|---|
| `valhalla.yaml` | Unified config — replaces 9 scattered JSON files |
| `config_loader.py` | YAML parser with `${ENV_VAR}` resolution, validation, singleton |
| `plugin_loader.py` | Dynamic plugin discovery + `register_routes(app, config)` |
| `plugins/model-switch/` | Ported from V1 `bifrost_local.py:1130–1205`, config-driven aliases |
| `plugins/watchdog/` | Ported from V1 `bot/watchdog.py`, background health polling |
| `api/v1.py` | 15 REST endpoints for dashboard |
| `bifrost.py` | FastAPI entry point (replaced V1 shim) |

### API Endpoints (15 total)

| Endpoint | Method | Source |
|---|---|---|
| `/api/v1/status` | GET | ARCHITECTURE.md + onboarding (GPU/VRAM) |
| `/api/v1/nodes` | GET | ARCHITECTURE.md + add-a-node |
| `/api/v1/plugins` | GET | ARCHITECTURE.md |
| `/api/v1/model-switch` | POST | ARCHITECTURE.md |
| `/api/v1/config` | GET | ARCHITECTURE.md |
| `/api/v1/config` | PUT | ARCHITECTURE.md |
| `/api/v1/soul/{file}` | GET | ARCHITECTURE.md |
| `/api/v1/soul/{file}` | PUT | ARCHITECTURE.md |
| `/api/v1/mesh/join-token` | POST | Valkyrie `add-a-node.md` |
| `/api/v1/mesh/announce` | POST | Valkyrie `add-a-node.md` |
| `/api/v1/nodes/{name}/config` | PUT | Valkyrie `add-a-node.md` |
| `/api/v1/nodes/{name}` | DELETE | Valkyrie `add-a-node.md` |
| `/api/v1/plugins/browse` | GET | Valkyrie `marketplace.md` |
| `/api/v1/plugins/install` | POST | Valkyrie `marketplace.md` |
| `/api/v1/plugins/{name}` | DELETE | Valkyrie `marketplace.md` |

## Valkyrie Alignment

Read all 4 deliverables and added endpoints to match:

- **Onboarding**: `/status` detects GPU (nvidia-smi / Apple Silicon) and inference engines (Ollama / LM Studio)
- **Add-a-Node**: Join token with 15min expiry, node announcement with name conflict handling, soul cloning, node removal
- **Marketplace**: Browse discovered plugins, install/uninstall with config persistence

## Test Results

**67/67 passing** — `test_config_loader.py` (14 cases) + `test_plugin_loader.py` (10 cases)

```
python3 -m pytest tests/ -v
```
