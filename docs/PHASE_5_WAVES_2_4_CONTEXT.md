# Phase 5 Waves 2-4 - Execution Context

**Current Status:** Wave 1 COMPLETE ✅
**Next:** Waves 2, 3, 4
**Estimated Time:** 8-12 hours total

---

## Wave 1 Completion Summary

### What Was Accomplished
- **teg_analysis package is now UI-independent** - imports without Streamlit
- **5 analysis files cleaned** - 40+ st.* calls removed
- **2 new modules created:**
  - `teg_analysis/core/metadata.py` (3 functions)
  - `teg_analysis/display/navigation.py` (4 functions)
- **9 functions migrated** from utils.py to teg_analysis
- **All validation tests pass**

### Key Patterns Established
```python
# 1. Conditional imports (safe for optional Streamlit)
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    st = None
    HAS_STREAMLIT = False

# 2. Pure functions return data (in teg_analysis)
def calculate_something(data: pd.DataFrame) -> dict:
    """Pure calculation - no UI."""
    result = do_calculation(data)
    return {'value': result, 'status': 'success'}

# 3. UI wrappers display data (in streamlit/utils.py)
@st.cache_data
def calculate_something_cached():
    """Streamlit wrapper with caching."""
    from teg_analysis.analysis import calculate_something
    return calculate_something(load_data())

def display_something():
    """UI wrapper shows results."""
    result = calculate_something_cached()
    if result['status'] == 'success':
        st.success(f"Value: {result['value']}")
```

### Current Validation Status
```bash
python -c "import teg_analysis"  # ✅ PASS
python -c "from teg_analysis.core import get_teg_metadata"  # ✅ PASS
python -c "from teg_analysis.analysis import get_current_in_progress_teg_fast"  # ✅ PASS
python -c "from teg_analysis.display import convert_trophy_name"  # ✅ PASS
grep -c "^def " streamlit/utils.py  # Returns: 100
```

---

## Wave 2: Consolidation (Agents E & F)

**Duration:** 3-5 hours
**Dependencies:** Wave 1 complete ✅

### Agent E: Deduplicate Functions (~2 hours)

**Objective:** Remove 20+ duplicate functions between utils.py and teg_analysis

**Process:**
1. Identify duplicates: Search for function names in both locations
2. Compare implementations: Keep the better one (usually teg_analysis)
3. Replace in utils.py with import wrapper
4. Test that pages still work

**Common Duplicates Expected:**
- Data aggregation functions
- Ranking functions
- Format functions
- TEG status functions (already migrated some in Wave 1)

**Pattern for utils.py after deduplication:**
```python
# MIGRATED to teg_analysis.analysis.aggregation.function_name
def function_name(*args, **kwargs):
    """Deprecated: Use teg_analysis.analysis.aggregation.function_name

    Kept as wrapper for backward compatibility.
    """
    from teg_analysis.analysis.aggregation import function_name as _func
    return _func(*args, **kwargs)
```

**Commands:**
```bash
# Find duplicates
grep -r "^def function_name" streamlit/utils.py
grep -r "^def function_name" teg_analysis/

# After changes, verify
python -c "from streamlit.utils import function_name; print('Works')"
```

### Agent F: Create Wrapper Layer (~2-3 hours)

**Objective:** Transform streamlit/utils.py into thin Streamlit wrapper

**Current:** ~100 functions
**Target:** ~50 functions (50% reduction)

**Categories to Keep in utils.py:**
1. **I/O with caching** (read_file, write_file wrappers)
2. **Streamlit-specific UI** (display functions, CSS, navigation)
3. **Cache management** (clear_all_caches, clear_volume_cache)
4. **Page helpers** (session state wrappers)
5. **GitHub operations** (commit wrappers for Railway)

**Categories to Remove (use teg_analysis instead):**
1. Pure calculations → teg_analysis.analysis
2. Data loading → teg_analysis.core.data_loader
3. Data transforms → teg_analysis.core.data_transforms
4. Metadata lookups → teg_analysis.core.metadata

**Wrapper Pattern:**
```python
# Before (in utils.py):
def complex_calculation(data):
    # 100 lines of calculation logic
    return result

# After (in teg_analysis):
def complex_calculation(data: pd.DataFrame) -> dict:
    """Pure calculation."""
    # 100 lines of calculation logic
    return result

# After (in utils.py - thin wrapper):
@st.cache_data
def complex_calculation_cached(data=None):
    """Streamlit wrapper with caching."""
    from teg_analysis.analysis import complex_calculation
    if data is None:
        data = load_all_data()
    return complex_calculation(data)
```

**Validation After Wave 2:**
```bash
grep -c "^def " streamlit/utils.py  # Should be ~50 (down from 100)
python -c "import streamlit; import utils"  # Should work
streamlit run streamlit/101TEG\ History.py  # Test a page
```

---

## Wave 3: Page Updates (Agents G, H, I, J)

**Duration:** 4-6 hours
**Dependencies:** Wave 2 complete

### Overview
Update 57 Streamlit pages to use new architecture.

**Batch Assignment:**
- **Agent G:** 14 pages (simple data pages)
- **Agent H:** 15 pages (analysis pages)
- **Agent I:** 14 pages (records + history)
- **Agent J:** 14 pages (admin + misc)

### Update Pattern for Each Page

**Before:**
```python
from utils import function_name, load_all_data

data = load_all_data()
result = function_name(data)
st.write(result)
```

**After:**
```python
from utils import load_all_data_cached
from teg_analysis.analysis import function_name

data = load_all_data_cached()
result = function_name(data)
st.write(result)
```

### Key Changes Per Page
1. Update imports - add `_cached` suffix where needed
2. Update function calls - use teg_analysis functions
3. Test page loads correctly
4. No functional changes to UI

### Page List (57 total)

**Agent G - Simple Data (14):**
- ave_by_course.py
- ave_by_par.py
- ave_by_teg.py
- course_details.py
- frontback.py
- handicap_history.py
- handicaps_2.py
- hole_by_hole*.py (multiple)
- net_vs_gross.py
- player_head2head.py
- round_details.py
- teg_details.py

**Agent H - Analysis (15):**
- 400scoring.py
- bestball.py
- best_eclectics.py
- biggest_changes.py
- comebacks*.py
- courses_analysis.py
- eagles.py
- holes_in_one.py
- latest_*.py
- par_performance.py
- scoring_*.py
- streaks.py

**Agent I - Records/History (14):**
- 300-303 series (records pages)
- personal_*.py
- *_rankings.py
- 101-102 series (history)
- leaderboard.py
- scorecard_v2.py

**Agent J - Admin/Misc (14):**
- 1000-1001 series (data update)
- 9999_generate_caches.py
- admin_*.py
- delete_data.py
- nav.py
- 500Handicaps.py
- chosen_*.py
- remaining pages

### Testing Strategy
1. **Sample test:** Test 1 page per batch
2. **Full test:** Run all pages at end
3. **Validation:** No import errors, pages load

---

## Wave 4: Validation & Documentation

**Duration:** 2-3 hours
**Dependencies:** Wave 3 complete

### Agent K: Testing & Validation (~2 hours)

**Tests to Create:**

**1. test_independence.py**
```python
"""Test that teg_analysis imports without Streamlit."""
import sys
import importlib

# Ensure streamlit not in sys.modules
if 'streamlit' in sys.modules:
    del sys.modules['streamlit']

# Try importing teg_analysis
try:
    import teg_analysis
    print("SUCCESS: teg_analysis imports without Streamlit")
except ImportError as e:
    print(f"FAIL: {e}")
    sys.exit(1)

# Test key imports
from teg_analysis.core import get_teg_metadata, load_course_info
from teg_analysis.analysis import get_current_in_progress_teg_fast
from teg_analysis.display import convert_trophy_name

print("SUCCESS: All imports work")
```

**2. test_fastapi.py (example)**
```python
"""Example using teg_analysis with FastAPI."""
from fastapi import FastAPI
from teg_analysis.core import get_teg_metadata
from teg_analysis.analysis import get_current_in_progress_teg_fast

app = FastAPI()

@app.get("/teg/{teg_num}")
def get_teg(teg_num: int):
    metadata = get_teg_metadata(teg_num)
    return {"teg": teg_num, "metadata": metadata}

@app.get("/current")
def get_current():
    teg_num, rounds = get_current_in_progress_teg_fast()
    return {"current_teg": teg_num, "rounds_played": rounds}

print("SUCCESS: FastAPI example created")
```

**3. test_performance.py**
```python
"""Performance benchmarks."""
import time
from teg_analysis.core.data_loader import load_all_data

start = time.time()
data = load_all_data()
elapsed = time.time() - start

print(f"Load time: {elapsed:.2f}s")
print(f"Rows loaded: {len(data)}")
assert elapsed < 10, "Load time too slow"
print("SUCCESS: Performance acceptable")
```

**Validation Commands:**
```bash
# 1. Independence test
python test_independence.py  # Should print SUCCESS

# 2. No Streamlit in core
grep -r "import streamlit" teg_analysis/ | grep -v "try:" | wc -l  # Should be 0

# 3. Function count reduced
grep -c "^def " streamlit/utils.py  # Should be ~50

# 4. All pages work
streamlit run streamlit/nav.py  # Manual test

# 5. Performance
python test_performance.py  # Should be < 10s
```

### Agent L: Documentation (~1 hour)

**Documents to Create:**

**1. ARCHITECTURE.md**
- Package structure
- Layer responsibilities
- Import patterns
- Best practices

**2. PHASE_5_COMPLETION.md**
- What was accomplished
- Before/after metrics
- Validation results
- Migration guide

**3. API_REFERENCE.md**
- All teg_analysis functions
- Parameters, returns, examples
- Organized by module

**4. ALTERNATIVE_UIS.md**
- FastAPI example
- Dash example
- Jupyter notebook example
- CLI example

---

## Critical File Locations

### teg_analysis Package Structure
```
teg_analysis/
├── __init__.py
├── io/
│   ├── file_operations.py
│   └── github_operations.py
├── core/
│   ├── data_loader.py
│   ├── data_transforms.py
│   └── metadata.py          # NEW in Wave 1
├── analysis/
│   ├── aggregation.py       # Enhanced in Wave 1
│   ├── pipeline.py
│   ├── records.py
│   ├── scoring.py
│   └── streaks.py
└── display/
    ├── formatters.py
    ├── tables.py
    └── navigation.py         # NEW in Wave 1
```

### Streamlit Structure
```
streamlit/
├── nav.py                    # Main entry point
├── utils.py                  # To be reduced in Wave 2
├── 101TEG History.py
├── 102TEG Results.py
└── ... (55 more pages)
```

---

## Key Functions Migrated in Wave 1

**Core (metadata.py):**
- get_teg_metadata(teg_num, round_num)
- load_course_info()
- get_scorecard_data(teg_num, round_num, player_code)

**Core (data_transforms.py):**
- summarise_existing_rd_data(existing_rows)
- check_for_complete_and_duplicate_data(scores_path, data_path)

**Analysis (aggregation.py):**
- get_current_in_progress_teg_fast()
- get_last_completed_teg_fast()
- has_incomplete_teg_fast()
- filter_data_by_teg(all_data, selected_tegnum)

**Display (navigation.py):**
- convert_trophy_name(name)
- get_trophy_full_name(trophy)
- convert_filename_to_streamlit_url(page_file)
- get_app_base_url()

---

## Success Criteria for Completion

### Wave 2 Complete When:
- [ ] utils.py reduced to ~50 functions (from 100)
- [ ] All duplicates removed or wrapped
- [ ] Sample pages still work
- [ ] No breaking changes

### Wave 3 Complete When:
- [ ] All 57 pages updated
- [ ] All pages load without errors
- [ ] Import statements use teg_analysis
- [ ] Sample testing passed

### Wave 4 Complete When:
- [ ] All validation tests pass
- [ ] test_independence.py succeeds
- [ ] test_fastapi.py demonstrates usage
- [ ] All 4 documentation files created
- [ ] Performance benchmarks acceptable

### Phase 5 Complete When:
- [ ] All Waves 1-4 complete
- [ ] teg_analysis imports standalone
- [ ] Zero direct Streamlit in calculations
- [ ] Alternative UI examples working
- [ ] Documentation comprehensive

---

## Commands Quick Reference

```bash
# Count functions in utils.py
grep -c "^def " streamlit/utils.py

# Find function in codebase
grep -rn "^def function_name" .

# Check for Streamlit imports
grep -r "import streamlit" teg_analysis/ | grep -v "try:"

# Test package import
python -c "import teg_analysis; print('OK')"

# Test function import
python -c "from teg_analysis.core import function_name; print('OK')"

# Run Streamlit app
streamlit run streamlit/nav.py

# List all Python files
find streamlit -name "*.py" -type f | wc -l

# Git commit with co-author
git commit -m "message

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Estimation

**Wave 2:** 3-5 hours
- Agent E: 2 hours (deduplication)
- Agent F: 2-3 hours (wrapper layer)

**Wave 3:** 4-6 hours
- 57 pages ÷ 4 agents = ~14 pages each
- ~15-20 minutes per page
- Parallel execution would be 1.5 hours, sequential 6 hours

**Wave 4:** 2-3 hours
- Agent K: 2 hours (tests)
- Agent L: 1 hour (docs)

**Total:** 9-14 hours remaining

---

## Current Git Status

**Branch:** refactor
**Recent Commits:**
- 0d0b997 - Wave 1 complete (all agents A-D)
- 5e71dcf - Wave 1 partial (agents A-B)
- 954cdc1 - Phase III & IV complete

**To Push:** 32 commits ahead of origin/refactor

---

## Notes for Execution

1. **Commit frequently** - After each agent or major milestone
2. **Test incrementally** - Don't wait until end to test
3. **Update docs** - Keep progress docs current
4. **Validate early** - Run tests after each wave
5. **Keep it simple** - Don't over-engineer, follow patterns

**Ready to execute Waves 2-4!**
