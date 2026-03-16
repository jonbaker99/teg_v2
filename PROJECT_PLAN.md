# Project Plan: TEG Analysis Cleanup & API

*Last updated: 2026-03-16*

## Big Picture

The TEG project is evolving from a monolithic Streamlit app into a two-layer architecture:

1. **`teg_analysis/`** — A standalone Python package containing all core analysis logic, completely independent of Streamlit. This is the foundation everything else builds on.
2. **Frontends** — Starting with the existing Streamlit app (deployed, working), with the goal of building a proper REST API and eventually a clean, professional web app.

### Where we are now
- The Streamlit app is stable and deployed on Railway
- The `teg_analysis` package has been extracted and merged to `main`
- **Phases 1–5 DONE**: All cleanup work complete. Code is clean, optimized, dead code removed.
- **Phase 6 IN PROGRESS**: Documentation update
- Branch: `cleanup-teg-analysis` (pushed to remote)

### Where we're heading
- A REST API powered by `teg_analysis` (FastAPI)
- A professional web frontend that calls the API
- Eventually retire or reduce the Streamlit app

## Current Work: teg_analysis Cleanup

### Phase 1: Cut the Cord — DONE ✅
All streamlit imports removed from `teg_analysis/`. Committed as `642c67b`.

### Phase 2: Split aggregation.py — DONE ✅

**New files created** (committed as `4e896bd`):
- `analysis/history.py` — winners, history tables, eagles, completeness checking
- `analysis/performance.py` — parameterised `prepare_performance_table()` replacing 11 near-duplicate functions + `prepare_pb_summary_table()` replacing 3
- `analysis/leaderboards.py` — TEG and round leaderboard generation + `filter_data_by_teg`
- `analysis/bestball.py` — bestball/worstball team format analysis

**Gutted `aggregation.py`** (2,931 → 1,012 lines):
- Kept: lookup functions, core aggregation engine, cached accessors, TEG status, round/TEG selection helpers, comeback analysis, scorecard helpers
- Removed: all code moved to history.py, performance.py, leaderboards.py, bestball.py
- Updated `__init__.py` with new module imports and re-exports
- Updated all internal callers (pipeline.py, examples, tests)

### Phase 3: Refactor streaks.py — DONE ✅

**Committed as `4fae7d8`**: 1,152 → 423 lines (-63%)
- Merged 8 paired good/bad functions into 4 direction-parameterised functions
- Deleted 9 legacy calculation functions (replaced by `build_streaks` + `STREAK_CONFIGS` dict)
- Extracted shared cache loading into `_load_and_transform()` helper
- Kept backward-compatible aliases for all old function names
- Updated `records.py` to use new `prepare_record_streaks_data(all_data, direction)` API

### Phase 4: Clean up remaining files — DONE ✅

**Committed as `31bb5f3`**: Cleaned up scoring.py, records.py, commentary.py
- `scoring.py`: 963 → 516 lines (-447 lines, -46%)
- `records.py`: 655 → 479 lines (-176 lines, -27%)
- `commentary.py`: 1,155 → 1,023 lines (-132 lines, -11%)

### Phase 5: Dead code audit — DONE ✅

**Committed as `1e0ce1e`**: Removed all uncalled functions (-667 lines total)
- Deleted dead code from multiple modules
- Restored html_tables.py as useful utility for future API/frontend
- All callers updated and verified

### Phase 6: Documentation — IN PROGRESS
- Update this file
- Update CLAUDE.md architecture section

### Phase 7: Opus review
Read all modified/created files. Check for architectural issues, missed edge cases, broken imports.

## Package Structure (Target)

```
teg_analysis/
    constants.py
    io/
        file_operations.py
        github_operations.py
        volume_operations.py
    core/
        data_loader.py
        data_transforms.py
        metadata.py
    analysis/
        aggregation.py      # 1,012 lines (core engine only)
        bestball.py         # 48 lines (NEW)
        commentary.py       # 1,023 lines (trimmed)
        history.py          # 364 lines (NEW)
        leaderboards.py     # 10 lines (NEW)
        performance.py      # 90 lines (NEW, replaces 11 functions)
        pipeline.py         # 516 lines
        rankings.py         # 219 lines
        records.py          # 479 lines (trimmed)
        scoring.py          # 516 lines (trimmed)
        streaks.py          # 423 lines (refactored)
    display/
        formatters.py
        html_tables.py
        navigation.py
        tables.py
    api/
        __init__.py
```

## Verification

1. **No streamlit in package:** `grep -r "import streamlit" teg_analysis/ --include="*.py"` → empty
2. **Package importable without streamlit:** `python -c "import sys; sys.modules['streamlit']=None; from teg_analysis.core.data_loader import load_all_data"`
3. **Tests pass:** `pytest tests/ -v`
4. **Streamlit app unaffected:** `streamlit run streamlit/nav.py` still works

## Rules for Future Work

1. **Never break main.** All work on feature branches. Streamlit app on Railway keeps working.
2. **Don't boil the ocean.** One thing at a time.
3. **The package is the product.** `teg_analysis/` should be clean, tested, documented.
4. **Delete rather than archive.** Git history exists for a reason.
5. **Constants live in one place.** `teg_analysis/constants.py`.
6. **No streamlit in the package.** If analysis needs it, migrate it.
