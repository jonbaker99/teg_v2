# Phase 5 Tasks - Complete Execution Guide

**Quick Reference:** All tasks in one document for efficient execution

---

## 📋 TASK 1: Clean teg_analysis (Remove UI Dependencies)

**Time:** 2-3 hours
**Files:** 5 analysis modules
**Goal:** Remove all Streamlit dependencies from teg_analysis

### Steps

**1.1 Remove Streamlit Imports**
```bash
# Find all Streamlit imports
grep -rn "import streamlit\|from streamlit" teg_analysis/analysis/

# For each file, remove these lines:
- import streamlit as st
- from streamlit import cache_data
```

**1.2 Extract UI Functions from Calculations**

For each function that mixes calculation + UI:

**Pattern:**
```python
# BEFORE (in teg_analysis/analysis/aggregation.py):
def display_completeness_status():
    missing = check_winner_completeness()
    if missing:
        st.warning(f"Missing: {missing}")  # ❌ UI call
        if st.button("Fix"):               # ❌ UI call
            fix_winners()
            st.success("Fixed!")            # ❌ UI call

# AFTER - Split into two:

# In teg_analysis/analysis/aggregation.py (calculation only):
def check_winner_completeness() -> dict:
    """Returns status data."""
    missing = _calculate_missing()
    return {
        'missing_tegs': missing,
        'count': len(missing),
        'needs_attention': len(missing) > 0
    }

def calculate_and_fix_winners(missing_tegs: list) -> dict:
    """Fixes missing winners, returns results."""
    fixed = []
    errors = []
    for teg in missing_tegs:
        try:
            fix_winner(teg)
            fixed.append(teg)
        except Exception as e:
            errors.append({'teg': teg, 'error': str(e)})
    return {'fixed': fixed, 'errors': errors}

# New file: streamlit/utils.py (UI wrapper):
def display_completeness_status_ui():
    """Streamlit UI wrapper."""
    import streamlit as st
    from teg_analysis.analysis.aggregation import (
        check_winner_completeness,
        calculate_and_fix_winners
    )

    status = check_winner_completeness()

    if status['needs_attention']:
        st.warning(f"⚠️ Missing winners for TEGs: {status['missing_tegs']}")

        if st.button("Fix Missing Winners"):
            with st.spinner("Calculating winners..."):
                result = calculate_and_fix_winners(status['missing_tegs'])

            if result['fixed']:
                st.success(f"✅ Fixed {len(result['fixed'])} TEGs")
            if result['errors']:
                for err in result['errors']:
                    st.error(f"❌ TEG {err['teg']}: {err['error']}")
```

**Functions to Refactor** (in aggregation.py):
- `display_completeness_status()` → split
- `calculate_and_save_missing_winners()` → split
- `load_cached_winners()` → split (cache logic to utils)

**1.3 Replace st.error/warning/success**
```python
# BEFORE:
def calculate_something(data):
    if data.empty:
        st.error("No data!")  # ❌
        return None
    return data.sum()

# AFTER:
def calculate_something(data: pd.DataFrame) -> float:
    if data.empty:
        raise ValueError("No data provided")  # ✅ Raise exception
    return data.sum()
```

**1.4 Remove Progress Indicators**
```python
# BEFORE:
def long_calculation(data):
    with st.spinner("Processing..."):  # ❌
        result = expensive_op(data)
    st.success("Done!")  # ❌
    return result

# AFTER:
def long_calculation(data: pd.DataFrame) -> pd.DataFrame:
    # Just do the calculation, no UI
    return expensive_op(data)
```

**1.5 Remove Cache Clearing**
```python
# BEFORE (in teg_analysis):
def update_data(new_data):
    save_data(new_data)
    st.cache_data.clear()  # ❌

# AFTER:
# In teg_analysis:
def update_data(new_data):
    save_data(new_data)
    # Return signal that cache should be cleared
    return {'cache_clear_needed': True}

# In utils.py wrapper:
def update_data_ui(new_data):
    result = teg_analysis.update_data(new_data)
    if result.get('cache_clear_needed'):
        st.cache_data.clear()
```

### Files to Modify

1. **teg_analysis/analysis/aggregation.py** (42 st.* calls)
   - Line ~678-787: `display_completeness_status()`
   - Line ~970-1061: Second completeness check
   - Remove all st.warning, st.button, st.spinner, st.success, st.error, st.rerun

2. **teg_analysis/analysis/pipeline.py**
   - Remove progress indicators
   - Return status dicts instead of showing UI

3. **teg_analysis/analysis/records.py**
   - Remove display helpers
   - Return formatted data

4. **teg_analysis/analysis/scoring.py**
   - Remove chart generation if it uses st.*
   - Keep pure calculations

5. **teg_analysis/analysis/streaks.py**
   - Remove any data display
   - Return data structures only

### Validation

```bash
# After Task 1, these should pass:
grep -r "import streamlit" teg_analysis/  # Should return 0 matches
grep -r "st\." teg_analysis/              # Should return 0 matches (check carefully)
python -c "import teg_analysis; print('OK')"  # Should work
```

---

## 📋 TASK 2: Migrate 39 Missing Functions

**Time:** 3-4 hours
**Goal:** Move calculation functions from utils.py to teg_analysis

### Function Migration List

**2.1 To core/data_loader.py** (5 functions):
```python
# From utils.py lines ~2000-2200
- get_number_of_completed_rounds_by_teg()
- get_incomplete_tegs() (note: check if duplicate)
- exclude_incomplete_tegs_function() (note: check if duplicate)
- load_and_prepare_handicap_data()
- get_google_sheet() (if used for data loading)
```

**2.2 To core/transformations.py** (8 functions):
```python
# From utils.py lines ~2400-2800
- reshape_round_data()
- summarise_existing_rd_data()
- check_for_complete_and_duplicate_data()
- add_round_info() (check if duplicate)
```

**2.3 To analysis/aggregation.py** (12 functions):
```python
# From utils.py lines ~3000-3500
- create_round_summary()
- create_round_events()
- create_tournament_summary()
- create_round_streaks_summary()
- create_tournament_streaks_summary()
- get_current_in_progress_teg_fast()
- get_last_completed_teg_fast()
- has_incomplete_teg_fast()
- get_next_teg_and_check_if_in_progress()
- get_next_teg_and_check_if_in_progress_fast()
- filter_data_by_teg()
- chosen_teg_context()
```

**2.4 To analysis/pipeline.py** (3 functions):
```python
# From utils.py lines ~2900-3000
- update_all_data()
- save_to_parquet()
- analyze_teg_completion()
```

**2.5 To NEW core/metadata.py** (3 functions):
```python
# Create new file: teg_analysis/core/metadata.py
- get_teg_metadata()
- load_course_info()
- get_scorecard_data()
```

**2.6 To NEW display/navigation.py** (8 functions):
```python
# Create new file: teg_analysis/display/navigation.py
- add_custom_navigation_links()
- add_section_navigation_links()
- apply_custom_navigation_css()
- create_custom_navigation_section()
- convert_filename_to_streamlit_url()
- get_app_base_url()
- convert_trophy_name()
- get_trophy_full_name()
```

### Migration Process (Per Function)

1. **Copy function** from utils.py to target file
2. **Remove UI calls** if any
3. **Add type hints**
4. **Update docstring**
5. **Test imports**
6. **Mark as migrated** (comment in utils.py)

### Example Migration

```python
# IN utils.py - BEFORE:
def create_round_summary(all_data_df=None, round_info_df=None):
    if all_data_df is None:
        all_data_df = load_all_data()
    # ... calculation ...
    return summary_df

# IN teg_analysis/analysis/aggregation.py - AFTER:
def create_round_summary(
    all_data_df: Optional[pd.DataFrame] = None,
    round_info_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """Creates summary of round data.

    Args:
        all_data_df: Complete scoring data (loads if None)
        round_info_df: Round metadata (loads if None)

    Returns:
        pd.DataFrame: Round summary with aggregated stats

    Raises:
        ValueError: If data is invalid
    """
    if all_data_df is None:
        from teg_analysis.core.data_loader import load_all_data
        all_data_df = load_all_data()

    # ... calculation (same logic) ...

    return summary_df

# IN utils.py - Mark as migrated:
# MIGRATED to teg_analysis.analysis.aggregation.create_round_summary
def create_round_summary(all_data_df=None, round_info_df=None):
    """Deprecated: Use teg_analysis.analysis.aggregation.create_round_summary"""
    from teg_analysis.analysis.aggregation import create_round_summary as _func
    return _func(all_data_df, round_info_df)
```

### Validation

```bash
# After each migration batch:
python -c "from teg_analysis.core.data_loader import get_incomplete_tegs; print('OK')"
python -c "from teg_analysis.analysis.aggregation import create_round_summary; print('OK')"

# Count migrations:
grep -c "MIGRATED to teg_analysis" streamlit/utils.py  # Should increase as you go
```

---

## 📋 TASK 3: Deduplicate Functions

**Time:** 1-2 hours
**Goal:** Remove 20+ duplicate functions

### Duplicate Function List

Found in both utils.py AND teg_analysis:
```
format_vs_par, get_teg_winners, aggregate_data, add_ranks,
get_complete_teg_data, get_9_data, get_incomplete_tegs,
add_cumulative_scores, process_round_for_all_scores,
check_hc_strokes_combinations, add_rankings_and_gaps,
create_round_summary, create_round_events,
create_tournament_summary, add_round_info,
get_net_competition_measure, get_teg_rounds,
get_tegnum_rounds, load_all_data
```

### Deduplication Process

For each duplicate:

1. **Verify teg_analysis version works**
```python
# Test in Python:
from teg_analysis.analysis.scoring import format_vs_par
assert format_vs_par(3) == '+3'
assert format_vs_par(0) == 'E'
assert format_vs_par(-2) == '-2'
```

2. **Replace utils.py version with wrapper**
```python
# IN utils.py - BEFORE:
def format_vs_par(value: float) -> str:
    if value > 0:
        return f'+{value}'
    elif value == 0:
        return 'E'
    else:
        return str(value)

# IN utils.py - AFTER:
def format_vs_par(value: float) -> str:
    """Wrapper for teg_analysis version."""
    from teg_analysis.analysis.scoring import format_vs_par as _func
    return _func(value)

# OR even simpler:
from teg_analysis.analysis.scoring import format_vs_par
```

3. **Add deprecation warning (optional)**
```python
import warnings

def format_vs_par(value: float) -> str:
    """Deprecated: Use teg_analysis.analysis.scoring.format_vs_par"""
    warnings.warn(
        "format_vs_par in utils.py is deprecated. "
        "Use teg_analysis.analysis.scoring.format_vs_par",
        DeprecationWarning,
        stacklevel=2
    )
    from teg_analysis.analysis.scoring import format_vs_par as _func
    return _func(value)
```

### Validation

```bash
# Verify no duplicates remain:
# (This should show only wrapper versions)
grep -A5 "^def format_vs_par" streamlit/utils.py
grep -A5 "^def format_vs_par" teg_analysis/analysis/scoring.py

# Test pages still work:
streamlit run streamlit/101TEG\ History.py
```

---

## 📋 TASK 4: Create Wrapper Layer

**Time:** 2-3 hours
**Goal:** Transform utils.py into clean Streamlit wrapper

### New utils.py Structure

```python
"""
Streamlit-specific utilities and wrappers for teg_analysis.

This module provides:
1. Cached wrappers for teg_analysis functions
2. UI helpers (error display, progress indicators)
3. Streamlit-specific features (session state, caching)
4. I/O operations with Railway/GitHub integration

Architecture:
- Imports from teg_analysis (pure calculations)
- Adds Streamlit optimizations
- Thin delegation layer
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, List

# === IMPORTS FROM TEG_ANALYSIS ===
from teg_analysis.core.data_loader import load_all_data as _load_all_data
from teg_analysis.analysis.aggregation import get_teg_winners as _get_teg_winners
# ... etc

# === I/O FUNCTIONS (Keep these - Streamlit/Railway specific) ===
def read_file(path: str) -> pd.DataFrame:
    """Railway-aware file reading."""
    # Implementation stays here
    pass

def write_file(path: str, data: pd.DataFrame):
    """Railway-aware file writing with GitHub sync."""
    # Implementation stays here
    pass

# === CACHE MANAGEMENT (Keep these - Streamlit specific) ===
def clear_all_caches():
    """Clear all Streamlit caches."""
    st.cache_data.clear()
    st.cache_resource.clear()

# === CSS/UI HELPERS (Keep these - Streamlit specific) ===
def load_css_file(css_path: str):
    """Load CSS into Streamlit."""
    # Implementation stays here
    pass

def load_datawrapper_css():
    """Load datawrapper CSS."""
    load_css_file('styles/datawrapper.css')

# === CACHED WRAPPERS ===
@st.cache_data(ttl=3600)
def load_all_data_cached(
    exclude_teg_50: bool = True,
    exclude_incomplete: bool = False
) -> pd.DataFrame:
    """Cached wrapper for teg_analysis.core.load_all_data."""
    try:
        return _load_all_data(exclude_teg_50, exclude_incomplete)
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return pd.DataFrame()

@st.cache_data
def get_teg_winners_cached(data: pd.DataFrame) -> pd.DataFrame:
    """Cached wrapper for teg_analysis.analysis.get_teg_winners."""
    try:
        return _get_teg_winners(data)
    except Exception as e:
        st.error(f"❌ Error calculating winners: {e}")
        return pd.DataFrame()

# === UI WRAPPERS (from Task 1) ===
def display_completeness_status_ui():
    """UI wrapper for winner completeness check."""
    from teg_analysis.analysis.aggregation import check_winner_completeness

    status = check_winner_completeness()
    if status['needs_attention']:
        st.warning(f"⚠️ Missing: {status['missing_tegs']}")
        # ... UI logic ...

# === SIMPLE DELEGATES (no caching needed) ===
def format_vs_par(value: float) -> str:
    """Delegate to teg_analysis."""
    from teg_analysis.analysis.scoring import format_vs_par as _func
    return _func(value)

# Or import directly:
from teg_analysis.analysis.scoring import format_vs_par
from teg_analysis.display.formatters import format_record_value
from teg_analysis.display.tables import create_stat_section
```

### Categories of Functions in New utils.py

1. **Keep (50 functions):**
   - I/O: 17 functions
   - Cache: 4 functions
   - CSS: 3 functions
   - UI helpers: 6 functions
   - Cached wrappers: ~20 functions

2. **Remove (migrated to teg_analysis):**
   - All calculation functions
   - All pure data transformations
   - All aggregation logic

### Validation

```python
# Test imports work:
from utils import load_all_data_cached, get_teg_winners_cached
data = load_all_data_cached()
winners = get_teg_winners_cached(data)
print(winners)

# Verify caching works:
import streamlit as st
st.cache_data.clear()
data1 = load_all_data_cached()  # Should load from source
data2 = load_all_data_cached()  # Should load from cache
```

---

## 📋 TASK 5: Update 57 Streamlit Pages

**Time:** 4-6 hours
**Goal:** Update all pages to use new architecture

### Update Pattern

```python
# BEFORE (old pattern):
from utils import load_all_data, get_teg_winners

data = load_all_data()
winners = get_teg_winners(data)
st.dataframe(winners)

# AFTER (new pattern):
from utils import load_all_data_cached, get_teg_winners_cached
# OR import teg_analysis directly for advanced use
# from teg_analysis.analysis.aggregation import get_teg_winners

data = load_all_data_cached()  # Use cached wrapper
winners = get_teg_winners_cached(data)
st.dataframe(winners)
```

### Pages to Update (57 files)

**Batch 1 (simple data pages - 10 files):**
- ave_by_course.py
- ave_by_par.py
- ave_by_teg.py
- course_details.py
- frontback.py
- handicap_history.py
- handicaps_2.py
- hole_by_hole_*.py
- net_vs_gross.py
- player_head2head.py

**Batch 2 (analysis pages - 15 files):**
- 400scoring.py
- bestball.py
- best_eclectics.py
- biggest_changes.py
- comebacks.py
- comebacks_full_teg.py
- courses_analysis.py
- eagles.py
- holes_in_one.py
- latest_round.py
- latest_teg.py
- par_performance.py
- scoring_achievements.py
- scoring_counts.py
- streaks.py

**Batch 3 (records pages - 10 files):**
- 300TEG Records.py
- 301Best_TEGs_and_Rounds.py
- 302Personal Best Rounds & TEGs.py
- 303Final Round Comebacks.py
- personal_bests.py
- personal_worsts.py
- rounds_rankings.py
- teg_rankings.py

**Batch 4 (history/admin - 22 files):**
- 101TEG History.py
- 101TEG Honours Board.py
- 102TEG Results.py
- 1000Data update.py
- 1001Report Generation.py
- 9999_generate_caches.py
- admin_volume_management.py
- delete_data.py
- Plus 14 more misc pages

### Per-Page Checklist

For EACH page:

1. **Update imports:**
```python
# Change:
from utils import load_all_data
# To:
from utils import load_all_data_cached
```

2. **Update function calls** (add `_cached` suffix where applicable)

3. **Add error handling** (if not using wrappers):
```python
try:
    data = load_data()
    result = calculate_something(data)
    st.dataframe(result)
except ValueError as e:
    st.error(f"Error: {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")
    logger.exception("Error in page")
```

4. **Test the page:**
```bash
streamlit run streamlit/[page_name].py
# Check: loads without errors, displays correctly
```

5. **Mark complete** in tracking spreadsheet

### Validation

```bash
# After all updates:
# Test a sample of pages:
streamlit run streamlit/101TEG\ History.py
streamlit run streamlit/300TEG\ Records.py
streamlit run streamlit/400scoring.py

# Check no import errors:
python -c "import streamlit; import sys; sys.path.insert(0, 'streamlit'); from utils import *; print('OK')"
```

---

## 📋 TASK 6: Testing & Validation

**Time:** 2-3 hours
**Goal:** Comprehensive testing

### Test 1: Import Independence

```python
# test_independence.py
"""Test that teg_analysis works without Streamlit."""

import sys
sys.path.insert(0, 'streamlit')  # For utils imports only

# Should work WITHOUT Streamlit installed
import teg_analysis

# Test core functions
from teg_analysis.core.data_loader import load_all_data
data = load_all_data()
print(f"✓ Loaded {len(data)} rows")

# Test analysis functions
from teg_analysis.analysis.aggregation import get_teg_winners
winners = get_teg_winners(data)
print(f"✓ Calculated winners for {len(winners)} TEGs")

# Test display functions
from teg_analysis.display.formatters import format_vs_par
assert format_vs_par(3) == '+3'
print("✓ Formatters work")

print("\n✅ SUCCESS: teg_analysis is UI-independent!")
```

### Test 2: Streamlit App Still Works

```bash
# Start Streamlit
streamlit run streamlit/nav.py

# Manually test pages:
# - Navigate to different pages
# - Check data loads
# - Verify calculations correct
# - Ensure no errors in logs
```

### Test 3: Alternative UI Example

```python
# test_fastapi.py
"""Example: Using teg_analysis with FastAPI."""

from fastapi import FastAPI
from teg_analysis.analysis.aggregation import get_teg_winners
from teg_analysis.core.data_loader import load_all_data

app = FastAPI()

@app.get("/winners")
def api_get_winners():
    """API endpoint using teg_analysis."""
    data = load_all_data()
    winners = get_teg_winners(data)
    return winners.to_dict('records')

# Run: uvicorn test_fastapi:app --reload
# Test: curl http://localhost:8000/winners
```

### Test 4: Performance Benchmark

```python
# test_performance.py
import time
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import get_teg_winners

# Benchmark data loading
start = time.time()
data = load_all_data()
load_time = time.time() - start
print(f"Load time: {load_time:.2f}s")

# Benchmark calculation
start = time.time()
winners = get_teg_winners(data)
calc_time = time.time() - start
print(f"Calculation time: {calc_time:.2f}s")

# Should be similar to before refactor
```

### Validation Checklist

- [ ] `import teg_analysis` works standalone
- [ ] No `import streamlit` in teg_analysis
- [ ] All 57 pages load without errors
- [ ] Calculations produce same results
- [ ] Caching still works efficiently
- [ ] Alternative UI example works
- [ ] Performance no worse than before
- [ ] All tests pass

---

## 📋 TASK 7: Documentation

**Time:** 1-2 hours
**Goal:** Complete documentation

Create these documents:

1. **docs/ARCHITECTURE.md** - System architecture
2. **docs/PHASE_5_COMPLETION.md** - What changed
3. **docs/API_REFERENCE.md** - Function reference
4. **docs/ALTERNATIVE_UIS.md** - Usage examples

---

## 🎯 FINAL VALIDATION

After ALL tasks complete:

```bash
# 1. Import test
python -c "import teg_analysis; print('✓ Package imports')"

# 2. No Streamlit in core
grep -r "import streamlit" teg_analysis/ | wc -l  # Should be 0

# 3. Function count
grep -c "^def " streamlit/utils.py  # Should be ~50 (down from 100)

# 4. Streamlit app works
streamlit run streamlit/nav.py  # Test manually

# 5. Alternative UI works
python test_independence.py  # Should print "SUCCESS"

# 6. Performance check
python test_performance.py  # Check times reasonable
```

---

**STATUS:** 📋 **READY FOR EXECUTION**
**NEXT:** Assign tasks to agents and begin execution
