# Thor Gate — Sprint 16 Complete (Polish & Ship)
- [x] T1 — Store wired: 6 default plugins, purchase 404/409, purchases.json persistence
- [x] T2 — Auto-start verified: setup() hook, spawn_backend, restart-on-crash, exit cleanup
- [x] T3 — BrainPicker match: InstallerWizard writes `fireside_brain`, SettingsForm reads it

## Files Modified
| File | Change |
|------|--------|
| `api/v1.py` | T1: expanded store defaults from 4 → 6 plugins (prompt-optimizer, cost-tracker) |
| `dashboard/components/InstallerWizard.tsx` | T3: writes `fireside_brain` to localStorage on onboarding complete |
| `dashboard/components/SettingsForm.tsx` | T3: reads `fireside_brain` from localStorage for BrainPicker init |
| `tests/test_sprint16_polish.py` | NEW — 27 tests |

## Test Results
**471 tests passing** (Sprints 1-16)
