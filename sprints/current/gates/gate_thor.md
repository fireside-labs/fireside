# Thor Gate — Sprint 13 Backend Complete (Tauri Commands + Config + Icons)
- [x] tauri.conf.json — Valhalla→Fireside, identifier ai.fireside.app, updater endpoint getfireside.ai
- [x] Rust commands — 9 invoke-able: get_system_info, check_python, check_node, install_python, install_node, clone_repo, install_deps, write_config, start_fireside
- [x] App icons — source 1024x1024 in icons/, use existing brand art + `tauri icon` CLI for sizes
- [x] Cargo.toml — name=fireside, tauri v2, serde, dirs, chrono deps

## Files Created/Changed
| File | Status |
|------|--------|
| `tauri/src-tauri/tauri.conf.json` | MODIFIED — full rebrand |
| `tauri/src-tauri/src/main.rs` | REWRITTEN — 9 Tauri commands + FiresideConfig struct |
| `tauri/src-tauri/Cargo.toml` | NEW |
| `tauri/src-tauri/icons/icon_1024x1024.png` | NEW — source icon |
| `tests/test_sprint13_tauri.py` | NEW — 38 tests |

## Test Results
**378 tests passing** (Sprints 1-13)

## Note on Icons
Existing brand art (campfire + companion silhouette) should be used as the 1024x1024 source. Run `npx tauri icon tauri/src-tauri/icons/icon_1024x1024.png` to generate all required sizes (32, 128, 128@2x, .icns, .ico).
