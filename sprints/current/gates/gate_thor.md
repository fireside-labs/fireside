# Thor Gate — Sprint 11 Backend Complete (Connection Choice)
- [x] Setup bridge scripts — `scripts/setup_bridge.sh` (macOS/Linux) + `scripts/setup_bridge.ps1` (Windows)
- [x] GET /api/v1/network/status — returns local_ip, tailscale_ip, bridge_active
- [x] Bifrost listener — already binds to 0.0.0.0 with Tailscale 100.x.x.x CORS regex

## Files Created/Changed
- `scripts/setup_bridge.sh` — NEW: Tailscale install + auth + IP display (bash)
- `scripts/setup_bridge.ps1` — NEW: Tailscale install via winget + auth + IP display (PowerShell)
- `plugins/companion/handler.py` — `/api/v1/network/status` endpoint
- `tests/test_sprint11_bridge.py` — NEW: 26 tests

## Test Results
**295 tests passing** (Sprints 1-11: 15+27+27+29+26+36+31+16+25+37+26)

## Setup Script Features
- Checks if Tailscale already installed
- Auto-installs (brew/apt on unix, winget on windows)
- `tailscale up` with `--hostname=fireside-<hostname>` 
- Headless auth via `TAILSCALE_AUTHKEY` env var (stretch goal)
- Displays both local + Tailscale IPs

## New Endpoint for Freya
| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/v1/network/status` | Returns `{local_ip, tailscale_ip, bridge_active}` |

## Bifrost Binding (Task 3)
Already correct — `bifrost.py` defaults to `--host 0.0.0.0` and CORS regex matches `100.\d+.\d+.\d+` (Tailscale) + `192.168.\d+.\d+` (LAN). No changes needed.
