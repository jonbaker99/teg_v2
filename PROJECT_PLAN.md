# Project Plan: TEG Analysis API & Cleanup

*Last updated: 2026-03-15*

## Big Picture

The TEG project is evolving from a monolithic Streamlit app into a two-layer architecture:

1. **`teg_analysis/`** — A standalone Python package containing all core analysis logic, completely independent of Streamlit. This is the foundation everything else builds on.
2. **Frontends** — Starting with the existing Streamlit app (deployed, working), with the goal of building a proper REST API and eventually a clean, professional web app.

### Where we are now
- The Streamlit app is stable and deployed on Railway
- The `teg_analysis` package has been extracted and merged to `main`
- **The package is now fully independent of Streamlit** — all streamlit imports, `from utils import`, and `from helpers.` imports have been removed
- Next: build a proper REST API, prototype alternative frontends

### Where we're heading
- A REST API powered by `teg_analysis` (FastAPI)
- A professional web frontend that calls the API
- Eventually retire or reduce the Streamlit app in favour of the better frontend

## The Overarching Objective

**Extract the core golf analysis logic into a clean, standalone Python package (`teg_analysis/`) that can power any frontend — API, web app, CLI, or notebook — and is completely independent of Streamlit.**

This is NOT a Streamlit rewrite. The Streamlit app stays on main and keeps working as-is. The goal is to build a clean foundation underneath it, then build new things on top of that foundation.

### Why this matters

The original codebase had ~530 functions in ~79 Python files, with business logic tangled into Streamlit page files. This meant:
- You couldn't use the analysis logic outside Streamlit
- Functions were duplicated across files (8 exact duplicates, 10 near-duplicates found)
- Testing was difficult because everything required a Streamlit runtime
- Adding new features meant adding more to the mess

The `teg_analysis/` package solves this by giving the analysis logic a clean home.

## What's Been Done

The following work was completed on the `claude/golf-stats-api-cMQ4e` branch and **merged to `main`** via PR #1 on 2026-02-06.

1. **Extracted `teg_analysis/` package** from the `refactor` branch — cherry-picked just the package, not the 80+ doc files, NiceGUI prototype, or throwaway scripts.

2. **Broke the dependency on `streamlit/utils.py`** — Created `teg_analysis/constants.py` to centralise all constants (file paths, player dict, tournament metadata). Replaced all `_get_constants()` / `from streamlit.utils import` patterns with direct imports from the constants module.

3. **Removed Streamlit-specific code** from the package — Truncated `pipeline.py` to remove the data update workflow UI (session state, `st.spinner`, `st.success`). That code belongs in the Streamlit app, not the analysis package.

4. **Validated the package works standalone** — All modules import cleanly with Streamlit blocked (`sys.modules['streamlit'] = None`). `load_all_data()` successfully loads 6,390 rows across 17 TEGs and 7 players from local data files.

5. **Included tests and FastAPI example** from the refactor branch.

6. **Cleaned up repo root** — Deleted 295 cruft files, rewrote README.

### Package structure
```
teg_analysis/
    __init__.py
    constants.py          # <-- NEW: centralised constants
    io/
        __init__.py
        file_operations.py    # read_file(), write_file() (Railway-aware)
        github_operations.py  # GitHub API read/write
        volume_operations.py  # Railway volume management
    core/
        __init__.py
        data_loader.py        # load_all_data(), process_round_for_all_scores()
        data_transforms.py    # add_cumulative_scores(), add_rankings_and_gaps()
        metadata.py           # get_teg_metadata(), load_course_info()
    analysis/
        __init__.py
        aggregation.py        # aggregate_data(), get_teg_winners() (~90 functions)
        commentary.py         # create_round_summary(), create_tournament_summary()
        pipeline.py           # update_streaks_cache(), update_all_data()
        rankings.py           # add_ranks(), ordinal()
        records.py            # get_all_time_records(), get_personal_bests()
        scoring.py            # format_vs_par(), scoring calculations (~35 functions)
        streaks.py            # build_streaks(), streak analysis (~27 functions)
    display/
        __init__.py
        formatters.py         # Value formatting, display preparation
        html_tables.py        # HTML table generation with styling
        navigation.py         # Trophy names, URL utilities
        tables.py             # Table generation utilities (returns HTML, no st.write)
    api/
        __init__.py           # (placeholder for FastAPI endpoints)
tests/
    conftest.py
    test_imports.py
    test_independence.py
    test_no_streamlit_imports.py
    ... (9 test files total)
examples/
    example_fastapi.py        # Working FastAPI example with ~10 endpoints
```

## Known Issues / Incomplete Items

These are things that still need attention in the `teg_analysis/` package:

1. **`aggregation.py` is still very large** (~2,900 lines) — Contains bestball, scorecard, comeback, leaderboard, history, and performance table functions that could be split into separate modules. The code works but is hard to navigate.

2. **`scoring.py` still has some duplicate patterns** — The file was cleaned up (removed ~200 lines of exact duplicates) but some function pairs (e.g. `format_vs_par_value` defined at module level and also as a local function inside `format_par_performance_table`) could be consolidated further.

3. **`api/` is empty** — Just a placeholder `__init__.py`. The FastAPI endpoints in `examples/example_fastapi.py` show the pattern but aren't integrated.

4. **Some functions in aggregation.py have UI-oriented logic** — Functions like `prepare_scorecard_selection_options` and `determine_control_states` feel more like UI helpers than analysis. Consider whether they belong in the package or the Streamlit app.

## Next Steps (In Priority Order)

### Phase 1: Stabilise the Package ✅ DONE
- [x] Run the existing tests, fix any failures — 60 tests pass
- [x] Remove all `st.error()` / `st.success()` / `st.cache_data.clear()` calls — replaced with `logger.error()` / `logger.info()`
- [x] Remove all `from utils import` and `from helpers.` imports — replaced with `teg_analysis` internal imports
- [x] Remove all conditional `import streamlit` blocks from module level
- [x] Replace `st.secrets` with `os.environ` in `github_operations.py`
- [x] Make `datawrapper_table` always return HTML (no `st.write`)
- [x] Delete `display/charts.py` (empty stub)
- [x] Delete streamlit-specific test files (`test_helpers.py`, `test_pages_smoke.py`, `test_utils_mock.py`)
- [x] Remove duplicate code in `scoring.py` (~200 lines) and `aggregation.py` (duplicate `check_winner_completeness`)
- [x] Fix `pipeline.py` bestball import to use `teg_analysis.analysis.aggregation`

### Phase 2: Build the API
- [ ] Move the FastAPI example into `teg_analysis/api/` as proper endpoints
- [ ] Add endpoints for: leaderboard, scorecard, records, personal bests, streaks
- [ ] Add a simple `main.py` entry point (`uvicorn teg_analysis.api:app`)
- [ ] Test API endpoints against real data

### Phase 3: Deploy
- [ ] Add FastAPI + uvicorn to requirements
- [ ] Set up a second Railway service for the API (or use a Procfile for both)
- [ ] API reads from same data files (GitHub or volume) as Streamlit app

### Phase 4: (Optional) New Frontend
- [ ] Build a lightweight frontend that calls the API
- [ ] Could be static HTML + JavaScript, React, or even a cleaner Streamlit app
- [ ] Streamlit app on main continues to work as-is throughout

## Rules for Future Work

These are the lessons from the previous refactor attempt. Follow them.

1. **Never break main.** All work happens on feature branches. The Streamlit app on main/Railway must keep working at all times.

2. **Don't boil the ocean.** The previous refactor produced 93 commits, 150K lines of docs, a NiceGUI prototype, AND a package extraction — all on one branch. That's too much. Do one thing at a time.

3. **The package is the product.** `teg_analysis/` is the thing we're building. It should be clean, tested, and well-documented. Everything else (API, frontend, deployment) builds on top of it.

4. **Delete rather than archive.** The previous refactor kept 80+ doc files "for reference." Delete things you don't need. Git history exists for a reason.

5. **Constants live in one place.** `teg_analysis/constants.py` is the single source of truth for file paths, player data, and tournament metadata. Don't re-define them elsewhere.

6. **No `from streamlit.utils import` in the package.** The whole point is independence. If a function needs something from `streamlit/utils.py`, migrate the function or the data it needs into `teg_analysis/`.

## How to Resume This Work

Everything is on `main`. No branch checkout needed.

```bash
# 1. Install dependencies
pip install pandas numpy pyarrow plotly PyGithub

# 2. Verify the package works
python -c "
from teg_analysis.core.data_loader import load_all_data
df = load_all_data()
print(f'OK: {len(df)} rows, {df.TEGNum.nunique()} TEGs')
"

# 3. Run the FastAPI example
pip install fastapi uvicorn
python examples/example_fastapi.py
# Visit http://localhost:8000/docs

# 4. Run existing tests
pip install pytest
pytest tests/ -v
```

## File Reference

| File | Purpose |
|------|---------|
| `BRANCHES.md` | Documents all branches and their status |
| `PROJECT_PLAN.md` | This file — the plan and resume instructions |
| `CLAUDE.md` | Existing project instructions (Streamlit-focused) |
| `teg_analysis/` | The standalone analysis package |
| `tests/` | Tests for teg_analysis |
| `examples/example_fastapi.py` | FastAPI proof-of-concept |
| `streamlit/` | The existing Streamlit app (untouched) |
| `data/` | Data files (untouched) |
