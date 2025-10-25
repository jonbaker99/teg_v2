# PHASE 5 CONTINUATION PROMPT - For Next Chat Session

## Context Summary

You are continuing the TEG Refactoring Project (Phase 5). **Phases I & II are COMPLETE**. **Phases III & IV framework are COMPLETE**. You are now implementing Phase III (Analysis Layer) and Phase IV (Display Layer).

---

## Current Status

### Completed (DO NOT REDO)
- ✅ Phase I: I/O Layer - 26 functions migrated to teg_analysis/io/ (3 modules)
- ✅ Phase II: Core Data Layer - 13 functions migrated to teg_analysis/core/ (2 modules)
- ✅ Phases III & IV: Module framework created (10 modules with stubs)
- ✅ All 91 tests passing (no regressions)
- ✅ All code committed to git (branch: refactor)

### Current Branch
- **Branch:** refactor
- **Last Commits:**
  - 4b0508b - docs: Add Phase 5 execution completion status
  - c07a76a - refactor(phases-3-4): Create Analysis and Display layer module stubs
  - 13f8cc7 - refactor(phase-2): Migrate Core Layer to teg_analysis package
  - 3970cce - refactor(phase-1): Migrate I/O layer to teg_analysis package

---

## What You Need to Do

### Phase III: Analysis Layer Migration (91 FUNCTIONS across 7 MODULES)

**Module Order (FOLLOW THIS - dependencies matter!):**

1. **analysis/scoring.py** (~14 functions)
   - Already has: format_vs_par(), get_net_competition_measure()
   - Add: All scoring functions from helpers/scoring_data_processing.py and utils.py
   - Lines in utils.py: search for "SECTION 7A" and "Section 6A"
   - NO DEPENDENCIES on other Phase III modules

2. **analysis/rankings.py** (~10 functions)
   - DEPENDS ON: scoring.py
   - Functions: add_ranks, get_ranked_teg_data, get_ranked_round_data, get_ranked_frontback_data, get_best, get_worst, ordinal, safe_ordinal
   - Search utils.py for "SECTION 7B"

3. **analysis/aggregation.py** (~10 functions)
   - DEPENDS ON: scoring.py, rankings.py, core data layer
   - Functions: aggregate_data, get_complete_teg_data, get_teg_data_inc_in_progress, get_round_data, get_9_data, get_teg_winners, get_teg_rounds, get_tegnum_rounds
   - Search utils.py for "SECTION 7A"

4. **analysis/streaks.py** (~16 functions)
   - DEPENDS ON: core data layer only
   - Functions from helpers/streak_analysis_processing.py
   - NO DEPENDENCY on scoring/rankings/aggregation

5. **analysis/records.py** (~10 functions)
   - DEPENDS ON: core data layer, aggregation
   - Functions from helpers/records_identification.py
   - Search utils.py for records-related functions

6. **analysis/commentary.py** (~6 functions)
   - DEPENDS ON: scoring, rankings, aggregation, streaks, records
   - Functions: create_round_summary, create_round_events, create_tournament_summary, create_round_streaks_summary, create_tournament_streaks_summary
   - Search utils.py for "SECTION 6A", "SECTION 6B", "SECTION 6C"
   - **LARGEST FUNCTIONS** - create_round_summary is 324 lines

7. **analysis/pipeline.py** (~7 functions)
   - DEPENDS ON: all other analysis modules
   - Functions: update_all_data, update_streaks_cache, update_bestball_cache, update_commentary_caches, get_google_sheet, summarise_existing_rd_data
   - Search utils.py for "SECTION 5"

### Phase IV: Display Layer Migration (44 FUNCTIONS across 3 MODULES)

1. **display/formatters.py** (~20+ functions)
   - DEPENDS ON: core, analysis/scoring, analysis/rankings
   - Functions from utils.py Section 8 and helpers/display_helpers.py, leaderboard_utils.py
   - Value formatting, display utilities

2. **display/tables.py** (~8 functions)
   - DEPENDS ON: core, analysis/scoring, display/formatters
   - Functions: create_stat_section, datawrapper_table, define_score_types, apply_score_types, score_type_stats
   - Search utils.py for table-related functions

3. **display/charts.py** (~3 functions)
   - DEPENDS ON: display/formatters
   - Functions from make_charts.py

---

## Key Functions Reference

### Constants (in streamlit/utils.py - use _get_constants() pattern from Phase II)
```
ALL_DATA_PARQUET, ROUND_INFO_CSV, PLAYER_DICT, TEGNUM_ROUNDS
STREAKS_PARQUET, BESTBALL_PARQUET, HANDICAPS_CSV
COMMENTARY_ROUND_EVENTS_PARQUET, COMMENTARY_ROUND_SUMMARY_PARQUET
COMMENTARY_TOURNAMENT_SUMMARY_PARQUET, COMMENTARY_ROUND_STREAKS_PARQUET
COMMENTARY_TOURNAMENT_STREAKS_PARQUET, ALL_DATA_CSV_MIRROR
```

### Critical Functions (MUST WORK CORRECTLY)
- `load_all_data()` - 40+ pages depend on it (Phase II, works fine)
- `create_round_summary()` - 324 lines, complex, recently optimized
- `aggregate_data()` - Core analysis function
- `add_ranks()` - Used by many pages

### External Helper Functions (will be migrated later or referenced)
- `helpers.streak_analysis_processing.build_streaks()`
- `helpers.bestball_processing.*` (prepare, calculate_bestball, calculate_worstball)
- `helpers.records_identification.*` (all record functions)
- `helpers.*_processing.py` modules

---

## Implementation Strategy

### For Each Module:
1. **Read the function** from streamlit/utils.py using line numbers
2. **Extract complete implementation** (all internal logic, error handling)
3. **Create module file** in teg_analysis/[package]/[module].py
4. **Add imports** (logging, pandas, numpy, dependencies from teg_analysis)
5. **Handle constants** using _get_constants() pattern (see Phase II data_loader.py for example)
6. **Test imports** - Run: `python -c "from teg_analysis.[package] import [function]"`
7. **Run full test suite** - Run: `pytest tests/ -v --tb=short`
8. **Commit** when module is complete and tests pass

### Example Pattern (from Phase II):
```python
# In data_loader.py (Phase II)
def _get_constants():
    """Get constants from utils.py to avoid circular imports"""
    from streamlit.utils import ALL_DATA_PARQUET, ROUND_INFO_CSV, ...
    return {...}

def load_all_data(...):
    consts = _get_constants()
    ALL_DATA_PARQUET = consts['ALL_DATA_PARQUET']
    ...
```

---

## Critical Success Criteria

### Testing
- ✅ 91 tests must pass after each module (ZERO regressions)
- ✅ All imports must work
- ✅ No circular dependencies
- ✅ Backward compatibility maintained

### Code Quality
- ✅ Docstrings preserved
- ✅ Error handling preserved
- ✅ Logging intact
- ✅ Type hints maintained

### Git Hygiene
- ✅ Commit after each module completes
- ✅ Descriptive commit messages
- ✅ Verify tests pass before committing

---

## File Locations (Reference)

### Source Files to Extract From
- `streamlit/utils.py` - Main source for Phase III & IV functions
- `helpers/scoring_data_processing.py` - Scoring functions
- `helpers/streak_analysis_processing.py` - Streak functions
- `helpers/records_identification.py` - Record functions
- `helpers/bestball_processing.py` - Bestball functions
- `helpers/display_helpers.py` - Display functions
- `helpers/leaderboard_utils.py` - Leaderboard functions
- `make_charts.py` - Chart functions

### Target Locations
- `teg_analysis/analysis/` - 7 modules for Phase III
- `teg_analysis/display/` - 3 modules for Phase IV
- `streamlit/utils.py` - Add wrapper functions here (KEEP ORIGINAL as wrapper)

---

## Execution Instructions

### Start with:
```bash
# Verify current state
cd /c/Users/jonba/Documents/Projects\ -\ not\ on\ onedrive/teg_v2
git status
git log --oneline -5
python -m pytest tests/ -v --tb=short  # Should show 91 passing

# Then start Phase III with scoring module
# Read functions from utils.py (search for relevant sections)
# Create teg_analysis/analysis/scoring.py with all scoring functions
# Test and commit when ready
```

### After Each Module:
```bash
# Test
python -m pytest tests/ -v --tb=short

# If 91 tests pass
git add [module files]
git commit -m "refactor(phase-3): Migrate [ModuleName] to teg_analysis/analysis"

# If tests fail
# Fix issues, retest, then commit
```

---

## Bash Command Approval Question

**IMPORTANT:** You asked about avoiding manual bash approval.

To your team/administrators: You can add these bash commands to the pre-approved list in the system configuration:
- `pytest tests/ -v --tb=short` (test execution)
- `git add` (git staging)
- `git commit` (git commits)
- `git log --oneline` (git history)
- `git status` (git status)
- `python -c "from teg_analysis..."` (import testing)
- `timeout 120 python -m pytest` (long test runs)
- File operations for this specific project directory

This would allow me to execute these without waiting for approval each time, significantly speeding up development.

---

## Estimated Time

- **Phase III (91 functions):** 2-3 hours (complex, interdependent)
- **Phase IV (44 functions):** 1 hour (simpler, fewer dependencies)
- **Total remaining:** 3-4 hours

---

## IMPORTANT: DO NOT FORGET

1. ✅ Keep wrapper functions in `streamlit/utils.py` (for backward compatibility)
2. ✅ Use `_get_constants()` pattern for global constants
3. ✅ Test after EVERY module (not at the end)
4. ✅ Commit per module (makes history clearer)
5. ✅ Follow dependency order in Phase III (critical!)
6. ✅ All 91 tests must pass (ZERO regressions allowed)

---

## Copy This to Start Next Session

When starting a new chat, provide this entire file as context. It contains everything needed to continue without the previous chat history.

**You are ready to continue Phase III immediately.**
