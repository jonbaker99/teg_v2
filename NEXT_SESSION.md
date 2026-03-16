# Next Session: Phase 4 — Clean up remaining files

**Branch:** `cleanup-teg-analysis` (pushed to remote)
**Model:** Sonnet (single-file edits, removing dead code)

## What's done

- **Phase 1**: All streamlit imports removed from `teg_analysis/`
- **Phase 2**: aggregation.py split complete (2,931 → 1,012 lines)
- **Phase 3**: streaks.py refactored (1,152 → 423 lines):
  - 8 paired good/bad functions → 4 direction-parameterised functions
  - 9 legacy calculation functions deleted
  - `STREAK_CONFIGS` dict + `_load_and_transform()` helper
  - Backward-compatible aliases kept
  - `records.py` updated to use new API

## What to do now

### Phase 4: Clean up remaining files (Sonnet)
- `scoring.py` (~963 lines): delete remaining duplication → ~500 lines
- `records.py` (~655 lines): delete broken-dependency functions → ~400 lines
- `commentary.py` (1,155 lines): delete uncalled functions → ~600 lines

## Full plan

See `PROJECT_PLAN.md` for Phases 4-7.
