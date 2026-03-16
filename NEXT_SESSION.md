# Next Session: Phase 5 — Dead code audit

**Branch:** `cleanup-teg-analysis` (pushed to remote)
**Model:** Sonnet (single-file edits, removing dead code)

## What's done

- **Phase 1**: All streamlit imports removed from `teg_analysis/`
- **Phase 2**: aggregation.py split complete (2,931 → 1,012 lines)
- **Phase 3**: streaks.py refactored (1,152 → 423 lines)
- **Phase 4**: scoring.py, records.py, commentary.py cleaned up (-810 lines net):
  - `scoring.py`: 963 → 516 lines — deleted 11 UI/chart functions (all duplicated in streamlit/helpers/)
  - `records.py`: 655 → 479 lines — deleted course analysis section + format_record_value
  - `commentary.py`: 1155 → 1023 lines — removed section header, extracted shared streak helpers
  - Note: commentary.py target of ~600 was miscalibrated; all 5 public functions are externally called

## What to do now

### Phase 5: Dead code audit (Sonnet)
For every function in `teg_analysis/`, grep for callers. Delete functions with zero external callers.

Files to check:
- `teg_analysis/analysis/aggregation.py` (~1012 lines)
- `teg_analysis/analysis/pipeline.py`
- `teg_analysis/analysis/rankings.py`
- `teg_analysis/analysis/history.py`
- `teg_analysis/analysis/performance.py`
- `teg_analysis/analysis/leaderboards.py`
- `teg_analysis/analysis/bestball.py`
- `teg_analysis/display/formatters.py`
- `teg_analysis/display/html_tables.py`
- `teg_analysis/display/tables.py`

## Full plan

See `PROJECT_PLAN.md` for Phases 5-7.
