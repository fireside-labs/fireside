# Desktop Installer Test

> **Test target:** The Tauri-packaged `Valhalla.app` (macOS) and `Valhalla.exe` (Windows).
>
> **Status:** Tested from source review. Tauri shell and security config verified. Build not yet run.

---

## Security Audit: ✅ PASS

Heimdall's Tauri capabilities config (`tauri/src-tauri/capabilities/main.json`) is the tightest webview security I've seen.

| Check | Status | Evidence |
|---|---|---|
| CSP restricts to localhost | ✅ | `connect-src: 'self' http://127.0.0.1:8337 ws://127.0.0.1:8337` |
| No `unsafe-eval` | ✅ | Only `'self'` in `script-src` |
| No remote code execution | ✅ | `shell:allow-execute` explicitly DENIED |
| No filesystem access from webview | ✅ | All `fs:*` DENIED |
| No external HTTP from webview | ✅ | `http:allow-fetch` DENIED |
| Prototype pollution blocked | ✅ | `freeze_prototype: true` |
| No iframe embedding | ✅ | `frame-src: 'none'` |
| Auto-update signed | ✅ | ed25519, reject unsigned + downgrade |
| Remote domain IPC blocked | ✅ | `dangerous_remote_domain_ipc_access: []` |

---

## Desktop Install Test Plan

| # | Step | Expected | Time Target | Pass? | Notes |
|---|---|---|---|---|---|
| 1 | Download installer | DMG (Mac) or NSIS installer (Win) | — | ⬜ | ~15 MB (Tauri, not Electron) |
| 2 | Open/install | macOS: drag to Applications. Win: next-next-finish. | < 30s | ⬜ | Needs code signing cert |
| 3 | First launch | App opens, backend starts on :8337, onboarding wizard | < 5s | ⬜ | — |
| 4 | Window behavior | Native title bar, resize, minimize, maximize | Immediate | ⬜ | Tauri system webview |
| 5 | Install brain | Same flow as web dashboard via BrainInstaller | < 2 min | ⬜ | — |
| 6 | Chat works | Messages route through installed brain | < 5s | ⬜ | — |
| 7 | Close app | Window closes, backend stops cleanly | Immediate | ⬜ | Tauri should SIGTERM |
| 8 | Reopen app | State preserved (name, brain, personality, achievements) | < 3s | ⬜ | localStorage + disk |
| 9 | Menu bar | File/Edit/Window menus functional | Immediate | ⬜ | Tauri defaults |
| 10 | Offline mode | App works without internet (local brain) | — | ⬜ | CSP already blocks external |
| 11 | Auto-update | "Update available" notification if newer version | — | ⬜ | Requires release server |
| 12 | Uninstall (Mac) | Drag to trash. Run cleanup script for ~/.valhalla | < 10s | ⬜ | — |
| 13 | Uninstall (Win) | Add/Remove Programs → clean uninstall | < 30s | ⬜ | NSIS uninstaller |

---

## App Size Comparison

| App | Size | Why |
|---|---|---|
| **Valhalla (Tauri)** | ~15 MB | Uses system webview (WebKit/WebView2) |
| ChatGPT (Electron) | ~180 MB | Bundles entire Chromium |
| VS Code (Electron) | ~300 MB | Bundles Chromium + Node |
| Slack (Electron) | ~250 MB | Bundles Chromium |

Tauri is 10-20x smaller. This is a real selling point.

---

## Platform-Specific Concerns

### macOS
- **Gatekeeper:** Without a code signing cert, macOS shows "Valhalla can't be opened because Apple cannot check it for malicious software." Fix: sign with Developer ID or distribute via TestFlight for beta.
- **System webview:** Uses WKWebView. Updates with macOS. CSS features may lag behind Chrome.
- **Universal binary:** Needs to work on both Intel and Apple Silicon. Tauri supports this via `--target universal-apple-darwin`.

### Windows
- **WebView2:** Uses Edge/Chromium webview. Pre-installed on Windows 11. May need WebView2 Runtime install on Windows 10.
- **SmartScreen:** Without EV code signing, Windows shows "Windows protected your PC." Fix: Extended Validation cert (~$300/yr) or distribute via Microsoft Store.
- **Firewall:** Windows Firewall may prompt when backend starts listening. llama-server on localhost should be fine.

### Linux
- **AppImage:** Portable, no install needed. Double-click to run.
- **WebView:** Uses WebKitGTK. Must be installed (`libwebkit2gtk-4.1`). AppImage should bundle it.

---

## Results

> **Status: ⬜ PENDING — Tauri build not yet runnable.**
>
> Security audit passed from config review. Full test requires:
> 1. Thor to run `npm run build:desktop`
> 2. A code signing cert (or accepting gatekeeper warning)
> 3. Testing on clean Mac + clean Windows machine
