# Task 5: Duplication Analysis - Quick Reference Guide

**Quick lookup for high-priority duplicates requiring immediate action**

---

## CRITICAL: Within-File Duplicates (Fix First!)

### File: `streamlit/helpers/history_data_processing.py`

**Problem**: Contains 4 sets of duplicate functions within the same file!

| Function | Lines | Locations | Action |
|----------|-------|-----------|--------|
| `extract_teg_num` | 8 | Lines 349, 639 | Keep first, delete second |
| `check_winner_completeness` | 34 | Lines 368, 658 | Keep first, delete second |
| `display_completeness_status` | 16-18 | Lines 404, 694 | Keep first, delete second |
| `calculate_and_save_missing_winners` | 80 | Lines 422, 714 | Keep first, delete second |

**Impact**: 180 lines of unnecessary code in one file
**Effort**: 30 minutes
**Risk**: Low (just delete duplicates)

### File: `streamlit/commentary/generate_tournament_commentary_v2.py`

| Function | Lines | Locations | Action |
|----------|-------|-----------|--------|
| `get_api_key` | 9 + 3 | Lines 443, 453 | Keep lines 443-451, delete 453-455 |
| `calc_wins_before` | 7 | Lines 740, 2000 | Keep first, delete second |

**Impact**: 16 lines
**Effort**: 10 minutes

### File: `streamlit/commentary/generate_round_report.py`

| Function | Lines | Locations | Action |
|----------|-------|-----------|--------|
| `get_api_key` | 9 + 3 | Lines 225, 235 | Keep lines 225-233, delete 235-237 |

**Effort**: 5 minutes

### File: `streamlit/player_history.py`

| Function | Lines | Locations | Action |
|----------|-------|-----------|--------|
| `teg_sort_key` | 5 | Lines 333, 379 | Keep first, delete second |

**Effort**: 5 minutes

### File: `streamlit/commentary/generate_commentary.py`

| Function | Lines | Locations | Action |
|----------|-------|-----------|--------|
| `read_file` | 5 | Lines 51, 109 | Keep first, delete second |

**Effort**: 5 minutes

**TOTAL WITHIN-FILE IMPACT**: ~370 lines can be eliminated in ~1 hour

---

## HIGH PRIORITY: Cross-File Exact Duplicates

### 1. `safe_int` (3 locations)

**Current locations**:
- `streamlit/commentary/round_data_loader.py:24`
- `streamlit/commentary/round_pattern_analysis.py:15`
- `streamlit/commentary/unified_round_data_loader.py:31`

**Action**:
1. Copy function to `streamlit/utils.py` (add around line 50 with other helper functions)
2. In each file, replace with: `from utils import safe_int`
3. Delete local versions

**Code to add to utils.py**:
```python
def safe_int(value, default=0):
    """Safely convert value to int, return default if conversion fails."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
```

### 2. `calculate_hole_difficulty` (2 locations)

**Current locations**:
- `streamlit/commentary/round_data_loader.py:63`
- `streamlit/commentary/unified_round_data_loader.py:479`

**Action**: Use only the unified version
1. Delete from `round_data_loader.py`
2. Verify all imports reference `unified_round_data_loader`

### 3. Rate-Limiting Functions (duplicated between 2 files)

**Functions**: `__init__`, `_now`, `_prune`, `used_last_min`, `plan_wait`, `acquire`

**Current locations** (all duplicated):
- `streamlit/commentary/generate_round_report.py`
- `streamlit/commentary/generate_tournament_commentary_v2.py`

**Action**: Create `streamlit/helpers/api_rate_limiting.py` with these functions

**New file to create**: `streamlit/helpers/api_rate_limiting.py`
```python
"""Rate limiting utilities for API calls."""
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self):
        self.usage: Dict[str, datetime] = {}
        self.limits = {
            'claude': 50  # requests per minute
        }

    # Copy all the rate limiting functions here
    # __init__, _now, _prune, used_last_min, plan_wait, acquire, etc.
```

Then import in both files:
```python
from helpers.api_rate_limiting import RateLimiter
```

---

## MEDIUM PRIORITY: Near Duplicates (80-99% Similar)

### Top 3 by Impact

| Function | Similarity | Lines | Files | Action |
|----------|------------|-------|-------|--------|
| `safe_create_message` | 91% | 83 | 2 | Extract common logic to helper |
| `calculate_and_save_missing_winners` | 94% | 80 | 1 (same file!) | Already covered above |
| `format_course_info_section` | 91% | 46 | 2 | Move to helpers/commentary_formatting.py |

### 1. `safe_create_message` (91% similar, 83 lines)

**Locations**:
- `streamlit/commentary/generate_round_report.py:138`
- `streamlit/commentary/generate_tournament_commentary_v2.py:353`

**Recommendation**: Leave as-is for now (part of larger commentary refactor)

### 2. `format_course_info_section` (91% similar, 46 lines)

**Locations**:
- `streamlit/commentary/add_course_info_to_story_notes.py:16`
- `streamlit/commentary/generate_tournament_commentary_v2.py:1680`

**Action**: Keep version in `generate_tournament_commentary_v2.py`, update imports

### 3. `get_previous_round_scores` (97% similar, 36 lines)

**Locations**:
- `streamlit/commentary/round_data_loader.py:97`
- `streamlit/commentary/unified_round_data_loader.py:513`

**Action**: Use unified version only

---

## NAMING CONFLICTS: Same Name, Different Purpose

### `render_report` (5 different implementations)

**Current names** (all called `render_report`):
- `streamlit/102TEG Results.py`
- `streamlit/latest_teg_context.py`
- `streamlit/teg_reports.py`
- `streamlit/teg_reports_17brief.py`
- `streamlit/teg_reports_17full.py`

**Recommended renames**:
```python
# In 102TEG Results.py
def render_teg_results_report():

# In latest_teg_context.py
def render_latest_teg_report():

# In teg_reports.py
def render_tournament_report():

# In teg_reports_17brief.py
def render_brief_tournament_report():

# In teg_reports_17full.py
def render_full_tournament_report():
```

### `format_value` (4 different implementations)

**Current locations**:
- `streamlit/500Handicaps.py:46`
- `streamlit/leaderboard_utils.py:72`
- `streamlit/make_charts.py:13`
- `streamlit/helpers/records_identification.py:31`

**Recommended renames**:
```python
# In 500Handicaps.py
def format_handicap_value(value):

# In leaderboard_utils.py
def format_leaderboard_value(value):

# In make_charts.py
def format_chart_value(value):

# In helpers/records_identification.py
def format_record_value(value):
```

---

## UTILITY CONSOLIDATION CHECKLIST

Functions that should be in `utils.py` but aren't:

- [ ] `safe_int` (currently in 3 files)
- [ ] `format_vs_par_value` (currently in 2 files)
- [ ] `load_markdown` (currently in 3 files - consolidate)
- [ ] `teg_sort_key` (currently duplicated in player_history.py)

---

## RECOMMENDED ORDER OF OPERATIONS

### Week 1: Within-File Cleanup
1. [ ] Fix `history_data_processing.py` (4 duplicates) - **30 min**
2. [ ] Fix `generate_tournament_commentary_v2.py` (2 duplicates) - **10 min**
3. [ ] Fix `generate_round_report.py` (1 duplicate) - **5 min**
4. [ ] Fix `player_history.py` (1 duplicate) - **5 min**
5. [ ] Fix `generate_commentary.py` (1 duplicate) - **5 min**
6. [ ] Test all affected pages - **30 min**

**Total time**: ~1.5 hours
**Impact**: ~370 lines eliminated

### Week 2: Utility Consolidation
1. [ ] Add `safe_int` to utils.py - **15 min**
2. [ ] Update imports in 3 files - **10 min**
3. [ ] Consolidate `load_markdown` - **20 min**
4. [ ] Test affected pages - **20 min**

**Total time**: ~1 hour
**Impact**: Better code organization

### Week 3: Data Loader Consolidation
1. [ ] Migrate to unified_round_data_loader - **2 hours**
2. [ ] Remove old round_data_loader - **30 min**
3. [ ] Update all imports - **30 min**
4. [ ] Test commentary generation - **1 hour**

**Total time**: ~4 hours
**Impact**: Single source of truth for round data

### Week 4: Rename Conflicts
1. [ ] Rename `render_report` variants - **1 hour**
2. [ ] Rename `format_value` variants - **1 hour**
3. [ ] Update all references - **1 hour**
4. [ ] Test all affected pages - **1 hour**

**Total time**: ~4 hours
**Impact**: Clearer code, no naming conflicts

---

## TESTING CHECKLIST

After each change, verify:

- [ ] No import errors
- [ ] Affected pages load correctly
- [ ] Functionality unchanged
- [ ] No console errors in Streamlit

**Pages to test after history_data_processing.py changes**:
- [ ] `101TEG History.py`
- [ ] `101TEG Honours Board.py`
- [ ] `1000Data update.py`

**Pages to test after commentary changes**:
- [ ] `1001Report Generation.py`
- [ ] Commentary generation functionality

**Pages to test after utils.py additions**:
- [ ] All pages (quick smoke test)
- [ ] Focus on pages importing the new utilities

---

## QUICK WINS (< 30 minutes each)

1. **Delete duplicate `extract_teg_num`** in history_data_processing.py (line 639)
2. **Delete duplicate `teg_sort_key`** in player_history.py (line 379)
3. **Delete duplicate `read_file`** in generate_commentary.py (line 109)
4. **Delete duplicate `get_api_key`** in generate_round_report.py (line 235)
5. **Delete duplicate `calc_wins_before`** in generate_tournament_commentary_v2.py (line 2000)

**Run these 5 deletions → Test → Commit** = Quick 30-minute win with measurable impact!

---

## FILES TO REVIEW

**Created by analysis**:
- `docs/FUNCTION_DUPLICATION_ANALYSIS.md` - Full analysis
- `docs/FUNCTION_DUPLICATION_ENHANCED.md` - Enhanced insights
- `docs/TASK_5_DUPLICATION_SUMMARY.md` - Comprehensive summary
- `docs/TASK_5_QUICK_REFERENCE.md` - This file
- `function_analysis.json` - Raw data (530 functions)

**Analysis scripts** (reusable):
- `analyze_function_duplicates.py` - Main analysis
- `analyze_patterns.py` - Pattern analysis

---

**Last updated**: October 18, 2025
**Status**: Analysis complete, refactoring not yet started
**Priority**: Start with within-file duplicates (Week 1)
