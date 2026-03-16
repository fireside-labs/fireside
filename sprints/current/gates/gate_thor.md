# Thor Gate — Sprint 17 Complete ("Immersion")
- [x] T1 — Model name -> brain mapping:
    - [x] `fireside_model` saved in `InstallerWizard` / `OnboardingWizard`
    - [x] `valhalla.yaml` persists `models.active` {brain, model}
    - [x] `GET /api/v1/brains/active` returns correct mapping
- [x] Sync & Maintain:
    - [x] Verified auth_token validation in store API
    - [x] Verified hardware detection refinements (absolute path, max VRAM agg)
    - [x] Verified backend polling logic
    - [x] Fixed Sprint 15 test regression

## Files Modified
| File | Change |
|------|--------|
| `api/v1.py` | Added `GET /api/v1/brains/active` |
| `tauri/src-tauri/src/main.rs` | Updated `write_config` to persist brain/model |
| `dashboard/components/InstallerWizard.tsx` | Persist `fireside_model` + include in Tauri call |
| `dashboard/components/OnboardingWizard.tsx` | Persist `fireside_model` |
| `tests/test_sprint17_immersion.py` | NEW — 10 tests |
| `tests/test_sprint15_shipit.py` | Fix regression |

## Test Results
**479 tests passing** across 17 sprints.
