# Project Plan: TEG Analysis Cleanup & API

*Last updated: 2026-03-16*

## Big Picture

The TEG project is evolving from a monolithic Streamlit app into a two-layer architecture:

1. **`teg_analysis/`** — A standalone Python package containing all core analysis logic, completely independent of Streamlit. This is the foundation everything else builds on.
2. **Frontends** — Starting with the existing Streamlit app (deployed, working), with the goal of building a proper REST API and eventually a clean, professional web app.

### Where we are now
- The Streamlit app is stable and deployed on Railway
- The `teg_analysis` package has been extracted and merged to `main`
- **Phase 1 DONE**: All streamlit imports removed from `teg_analysis/`
- **Phase 2 IN PROGRESS**: Splitting `aggregation.py` (2,940 → 5 files)
- Branch: `cleanup-teg-analysis` (pushed to remote)

### Where we're heading
- A REST API powered by `teg_analysis` (FastAPI)
- A professional web frontend that calls the API
- Eventually retire or reduce the Streamlit app

## Current Work: teg_analysis Cleanup

### Phase 1: Cut the Cord — DONE ✅
All streamlit imports removed from `teg_analysis/`. Committed as `642c67b`.

### Phase 2: Split aggregation.py — IN PROGRESS 🔧

**New files created** (committed as `4e896bd`):
- `analysis/history.py` — winners, history tables, eagles, completeness checking
- `analysis/performance.py` — parameterised `prepare_performance_table()` replacing 11 near-duplicate functions + `prepare_pb_summary_table()` replacing 3
- `analysis/leaderboards.py` — TEG and round leaderboard generation
- `analysis/bestball.py` — bestball/worstball team format analysis

**Still TODO for Phase 2** (pick up here):
1. **Rewrite `aggregation.py`** — Remove all code that's been moved to the new files. Keep only:
   - Lookup functions (`get_teg_rounds`, `get_tegnum_rounds`)
   - Core aggregation engine (`list_fields_by_aggregation_level`, `aggregate_data`)
   - Cached accessors (`get_complete_teg_data`, `get_teg_data_inc_in_progress`, `get_round_data`, `get_9_data`, `get_Pl_data`)
   - TEG status (`get_last_completed_teg_fast`, `get_current_in_progress_teg_fast`, `has_incomplete_teg_fast`)
   - Round/TEG selection helpers and comeback analysis (move to a `latest.py` or keep in aggregation — TBD)
2. **Update `__init__.py`** — Add imports for the new modules, update re-exports
3. **Update internal callers**:
   - `pipeline.py` imports bestball from aggregation → change to bestball
   - `rankings.py` imports from aggregation → stays (uses core accessors)
   - `html_tables.py` imports aggregate_data → stays
   - Tests and examples that import `get_teg_winners`, `filter_data_by_teg` → update
4. **Add backward-compat re-exports** in `aggregation.py` so nothing breaks during transition
5. **Verify**: `python -c "import sys; sys.modules['streamlit']=None; from teg_analysis.core.data_loader import load_all_data"` still works

### Phase 3: Refactor streaks.py (Opus)
- 1,152 lines, 27 functions with good/bad mirror duplication
- Replace paired functions with single functions that accept a `direction` parameter
- Target: ~400 lines

### Phase 4: Clean up remaining files (Sonnet)
- `scoring.py` (~963 lines): delete remaining duplication → ~500 lines
- `records.py` (~655 lines): delete broken-dependency functions → ~400 lines
- `commentary.py` (1,155 lines): delete uncalled functions → ~600 lines

### Phase 5: Dead code audit (Sonnet)
For every function in `teg_analysis/`, grep for callers. Delete functions with zero external callers.

### Phase 6: Documentation (Haiku)
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
        aggregation.py      # ~200 lines (core engine only)
        bestball.py          # ~60 lines (NEW)
        commentary.py        # ~600 lines (trimmed)
        history.py           # ~300 lines (NEW)
        leaderboards.py      # ~90 lines (NEW)
        performance.py       # ~220 lines (NEW, replaces 11 functions)
        pipeline.py
        rankings.py
        records.py           # ~400 lines (trimmed)
        scoring.py           # ~500 lines (trimmed)
        streaks.py           # ~400 lines (refactored)
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
