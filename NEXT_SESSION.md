# Next Session: Phase 3 — Refactor streaks.py

**Branch:** `cleanup-teg-analysis` (pushed to remote)
**Model:** Opus (this is multi-file refactor work)

## What's done

- **Phase 1**: All streamlit imports removed from `teg_analysis/`
- **Phase 2**: aggregation.py split complete:
  - `analysis/history.py` — winners, history tables, eagles, caching
  - `analysis/performance.py` — parameterised `prepare_performance_table()` replacing 11 functions
  - `analysis/leaderboards.py` — TEG/round leaderboards, `filter_data_by_teg`
  - `analysis/bestball.py` — bestball/worstball
  - `aggregation.py` gutted from 2,931 → 1,012 lines (core engine, cached accessors, selection helpers, comeback analysis, TEG status)
  - `__init__.py` updated with new module imports/re-exports
  - All internal callers updated (pipeline.py, examples, tests)
  - All tests pass

## What to do now

### Phase 3: Refactor streaks.py (Opus)
- 1,152 lines, 27 functions with good/bad mirror duplication
- Replace paired functions with single functions that accept a `direction` parameter
- Target: ~400 lines

## Full plan

See `PROJECT_PLAN.md` for Phases 3-7.
