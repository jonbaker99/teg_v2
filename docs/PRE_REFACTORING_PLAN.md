# TEG Pre-Refactoring Cleanup Plan

**Document Status:** ACTIVE PLAN
**Created:** 2025-10-19
**Purpose:** Prepare codebase for wholesale refactoring and API extraction
**Total Time:** ~28 hours over 4 weeks
**Expected ROI:** 50%+ reduction in refactoring time and risk

---

## Executive Summary

### Why Clean Before Refactoring?

The comprehensive documentation (52+ files analyzing 530 functions) reveals significant opportunities to **reduce complexity before reorganization**:

- **~600 lines of dead/duplicate code** that shouldn't be migrated
- **38 naming conflicts** that will cause confusion during API design
- **Zero test infrastructure** (cannot safely refactor without tests)
- **Competing implementations** (2 data loaders, unclear canonical versions)
- **O(n²) performance issues** documented but not fixed

**Core Principle:** Don't refactor code you'll delete anyway. Don't migrate code you don't understand. Don't reorganize code you can't test.

### Success Criteria

Before starting wholesale refactoring, achieve:
- ✅ Test coverage for all major page categories (prevents regressions)
- ✅ Zero within-file duplicates (eliminates obvious waste)
- ✅ 20 unused functions archived (reduces migration scope by 6%)
- ✅ Zero naming conflicts (clarifies API design)
- ✅ Single data loader implementation (eliminates architectural confusion)
- ✅ Documented utils.py structure (makes migration planning trivial)
- ✅ Defined target API surface (guides refactoring decisions)

---

## Phase 1: Quick Wins - Eliminate Obvious Waste

**Duration:** Week 1, ~8 hours
**Risk Level:** LOW
**Impact:** Remove ~600 lines before refactoring
**Dependencies:** None (can start immediately)

### Task 1.1: Delete Within-File Duplicates (~1 hour)

**Target:** 370 lines of identical functions duplicated within same files

#### Subtask 1.1.1: Fix `history_data_processing.py` (30 minutes)
**Location:** [streamlit/helpers/history_data_processing.py](../streamlit/helpers/history_data_processing.py)
**Problem:** 4 duplicate function pairs in one file (180 lines waste)

| Function | Keep | Delete | Lines Saved |
|----------|------|--------|-------------|
| `extract_teg_num` | Line 349 | Line 639 | 8 |
| `check_winner_completeness` | Line 368 | Line 658 | 34 |
| `display_completeness_status` | Line 404 | Line 694 | 17 |
| `calculate_and_save_missing_winners` | Lines 422-501 | Lines 714-793 | 80 |

**Action:**
```bash
# 1. Open streamlit/helpers/history_data_processing.py
# 2. Delete lines 639-646 (extract_teg_num duplicate)
# 3. Delete lines 658-691 (check_winner_completeness duplicate)
# 4. Delete lines 694-710 (display_completeness_status duplicate)
# 5. Delete lines 714-793 (calculate_and_save_missing_winners duplicate)
```

**Verification:**
```bash
# Each function should appear only once
grep -n "def extract_teg_num" streamlit/helpers/history_data_processing.py
grep -n "def check_winner_completeness" streamlit/helpers/history_data_processing.py
grep -n "def display_completeness_status" streamlit/helpers/history_data_processing.py
grep -n "def calculate_and_save_missing_winners" streamlit/helpers/history_data_processing.py
```

**Testing:**
- Run `101TEG History.py` - verify tournament history loads
- Run `101TEG Honours Board.py` - verify winner data displays
- Run `1000Data update.py` - verify winner calculations work

**Reference:** [TASK_5_QUICK_REFERENCE.md](TASK_5_QUICK_REFERENCE.md#critical-within-file-duplicates-fix-first)

#### Subtask 1.1.2: Fix Commentary Modules (20 minutes)
**Files:**
- `streamlit/commentary/generate_tournament_commentary_v2.py` (2 duplicates)
- `streamlit/commentary/generate_round_report.py` (1 duplicate)

| File | Function | Keep | Delete | Lines Saved |
|------|----------|------|--------|-------------|
| generate_tournament_commentary_v2.py | `get_api_key` | 443-451 | 453-455 | 3 |
| generate_tournament_commentary_v2.py | `calc_wins_before` | 740-746 | 2000-2006 | 7 |
| generate_round_report.py | `get_api_key` | 225-233 | 235-237 | 3 |

**Testing:** Run `1001Report Generation.py` to verify commentary generation works

#### Subtask 1.1.3: Fix Other Quick Duplicates (10 minutes)
- `streamlit/player_history.py`: Delete `teg_sort_key` duplicate at line 379 (keep line 333)
- `streamlit/commentary/generate_commentary.py`: Delete `read_file` duplicate at line 109 (keep line 51)

**Testing:** Quick smoke test of affected pages

**Total Impact:** ~370 lines eliminated in 1 hour

---

### Task 1.2: Archive HIGH-Confidence Unused Code (~2 hours)

**Target:** 20 functions with ZERO usage (grep-validated, >95% confidence)

**Strategy:**
1. Create archive directory: `streamlit/archive/unused_2025_10_19/`
2. For single-function files: Move entire file
3. For multi-function files: Comment out function with `# ARCHIVED 2025-10-19: Unused` header

**Functions to Archive:**

#### Single-Function Files (Move Entire File)
- `streamlit/scorecard_utils.py` - `generate_scorecard_html()` unused

#### Multi-Function Files (Comment Out)
**utils.py** (4 functions):
- Line 953: `check_hc_strokes_combinations()`
- Line 1061: `save_to_parquet()`
- Line 2928: `get_Pl_data()`
- Line 3095: `safe_ordinal()`
- Line 4330: `create_custom_navigation_section()`

**helpers/** modules (11 functions):
- `display_helpers.py:38` - `prepare_records_display()`
- `history_data_processing.py:12` - `process_winners_for_charts()`
- `history_data_processing.py:131` - `create_bar_chart()`
- `latest_round_processing.py:100` - `create_round_selection_reset_function()`
- `records_css.py:10` - `load_records_page_css()`
- `streak_analysis_processing.py:220` - `prepare_streak_data_for_display()`
- `streak_analysis_processing.py:243` - `prepare_inverse_streak_data_for_display()`
- `worst_performance_processing.py:11` - `get_performance_measure_titles()`
- `worst_performance_processing.py:85` - `load_worst_performance_custom_css()`
- `worst_performance_processing.py:136` - `create_worst_performance_section()`

**Other files** (4 functions):
- `1001Report Generation.py:130` - `get_draft_files()`
- `admin_volume_management.py:85` - `_to_utc()`
- `player_history.py:84` - `create_position_count_summary()`
- `player_history.py:155` - `create_average_position_summary()`

**Archive Template:**
```python
# ============================================================================
# ARCHIVED 2025-10-19: Unused function (zero calls found in codebase)
# Analysis: Task 6 unused code analysis (>95% confidence)
# Reason: [Brief reason - e.g., "Replaced by new version", "Feature removed"]
# Can restore from git history if needed
# ============================================================================
# def function_name(...):
#     """Original docstring"""
#     # ... function body ...
```

**Testing:**
```bash
# After archiving each function, verify no import errors:
streamlit run streamlit/nav.py

# Quick smoke test of major pages
# If any errors occur, check if archived function was actually used
```

**Reference:** [analysis/ANALYSIS_SUMMARY_FINAL.md](analysis/ANALYSIS_SUMMARY_FINAL.md#high-confidence---archive-these-20)

**Impact:** 6.1% reduction in codebase size (20 of 522 functions)

---

### Task 1.3: Add Missing Utility Functions (~1 hour)

**Target:** Consolidate duplicated utility functions into canonical versions

#### Subtask 1.3.1: Add `safe_int()` to utils.py (20 minutes)
**Current:** Duplicated in 3 files:
- `streamlit/commentary/round_data_loader.py:24`
- `streamlit/commentary/round_pattern_analysis.py:15`
- `streamlit/commentary/unified_round_data_loader.py:31`

**Action:**
```python
# Add to streamlit/utils.py around line 50 (near other helper functions)

def safe_int(value, default=0):
    """Safely convert value to int, return default if conversion fails.

    Args:
        value: Value to convert to integer
        default: Default value if conversion fails (default: 0)

    Returns:
        int: Converted value or default

    Example:
        >>> safe_int("42")
        42
        >>> safe_int("not a number", default=0)
        0
        >>> safe_int(None, default=-1)
        -1
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
```

**Update Imports:**
```python
# In each of the 3 files, replace local definition with:
from utils import safe_int
```

**Testing:** Run commentary generation to verify no regressions

#### Subtask 1.3.2: Add Other Utilities (40 minutes)
- Add `format_vs_par_value()` (if duplicated - check docs)
- Move `teg_sort_key` to utils.py (after deleting duplicate in Task 1.1.3)

**Impact:** Establishes canonical versions before refactoring

---

### Task 1.4: Create Testing Infrastructure (~4 hours)

**CRITICAL:** No test infrastructure currently exists. Cannot safely refactor without tests.

#### Subtask 1.4.1: Setup Test Framework (30 minutes)

**Create:** `tests/` directory structure
```
tests/
├── __init__.py
├── conftest.py              # pytest fixtures
├── test_data_loading.py     # Core data loading tests
├── test_utils.py            # Utils function tests
├── test_helpers.py          # Helper module tests
└── test_pages_smoke.py      # Page smoke tests
```

**Install Dependencies:**
```bash
pip install pytest pytest-cov
```

**Create conftest.py:**
```python
"""pytest configuration and shared fixtures"""
import pytest
import pandas as pd
import sys
from pathlib import Path

# Add streamlit directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "streamlit"))

@pytest.fixture
def sample_all_data():
    """Sample all-data dataframe for testing"""
    # Return minimal valid dataframe
    pass

@pytest.fixture
def sample_round_info():
    """Sample round info for testing"""
    pass
```

#### Subtask 1.4.2: Create Data Loading Tests (1 hour)

**Create:** `tests/test_data_loading.py`
```python
"""Tests for core data loading functions"""
import pytest
from utils import load_all_data, read_file, load_and_prepare_handicap_data

def test_load_all_data_returns_dataframe():
    """Verify load_all_data returns a pandas DataFrame"""
    df = load_all_data()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0

def test_load_all_data_has_required_columns():
    """Verify load_all_data returns expected columns"""
    df = load_all_data()
    required_cols = ['TEG', 'Player', 'Round', 'Hole', 'Score']
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"

def test_read_file_csv():
    """Test read_file with CSV format"""
    df = read_file("data/handicaps.csv")
    assert isinstance(df, pd.DataFrame)

def test_read_file_parquet():
    """Test read_file with Parquet format"""
    df = read_file("data/all-scores.parquet")
    assert isinstance(df, pd.DataFrame)

def test_exclude_incomplete_tegs():
    """Test that exclude_incomplete_tegs parameter works"""
    df_with = load_all_data(exclude_incomplete_tegs=False)
    df_without = load_all_data(exclude_incomplete_tegs=True)
    assert len(df_with) >= len(df_without)
```

#### Subtask 1.4.3: Create Helper Module Tests (1 hour)

**Create:** `tests/test_helpers.py`
```python
"""Tests for helper module functions"""
import pytest
from helpers.scoring_data_processing import format_vs_par_value, prepare_average_scores_by_par
from helpers.streak_analysis_processing import identify_streaks

def test_format_vs_par_value():
    """Test vs par formatting"""
    assert format_vs_par_value(0) == "E"
    assert format_vs_par_value(1) == "+1"
    assert format_vs_par_value(-2) == "-2"

def test_prepare_average_scores_by_par(sample_all_data):
    """Test average scores calculation"""
    result = prepare_average_scores_by_par(sample_all_data)
    assert isinstance(result, pd.DataFrame)
    assert 'Par' in result.columns

# Add tests for other critical helper functions
```

#### Subtask 1.4.4: Create Page Smoke Tests (1 hour)

**Create:** `tests/test_pages_smoke.py`
```python
"""Smoke tests for page imports and basic functionality"""
import pytest
import sys
from pathlib import Path

# Test that each page can be imported without errors
def test_import_history_pages():
    """Test History category pages import successfully"""
    import sys
    sys.path.insert(0, "streamlit")

    # These imports should not raise exceptions
    # Note: Full execution requires Streamlit context
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("teg_history", "streamlit/101TEG History.py")
        # Just verify file can be loaded
        assert spec is not None
    except Exception as e:
        pytest.fail(f"Failed to load history page: {e}")

def test_import_utils():
    """Test utils module imports successfully"""
    import utils
    assert hasattr(utils, 'load_all_data')
    assert hasattr(utils, 'read_file')

# Add similar tests for each major page category
```

#### Subtask 1.4.5: Create Import Verification Tests (30 minutes)

**Create:** `tests/test_imports.py`
```python
"""Verify all imports are resolvable"""
import pytest
from pathlib import Path

def test_no_circular_imports():
    """Verify no circular import issues"""
    # Try importing all modules
    # Should complete without errors
    pass

def test_helper_imports_resolve():
    """Verify all helper module imports resolve"""
    from helpers import scoring_data_processing
    from helpers import streak_analysis_processing
    # ... all helper modules
```

#### Subtask 1.4.6: Setup CI/Test Running (30 minutes)

**Create:** `pytest.ini`
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
```

**Create:** `run_tests.sh` (or `.bat` for Windows)
```bash
#!/bin/bash
# Run all tests with coverage report
pytest tests/ --cov=streamlit --cov-report=html --cov-report=term
```

**Documentation:** Add testing section to README

**Testing the Tests:**
```bash
# Run test suite
pytest tests/ -v

# Should see results for all test files
# Target: At least 50% of tests passing initially
# Goal: 100% passing before refactoring starts
```

**Impact:** Enables safe refactoring. This is the MOST CRITICAL task in Phase 1.

---

### Phase 1 Success Criteria

- [ ] All within-file duplicates removed (~370 lines)
- [ ] 20 unused functions archived (6% reduction)
- [ ] `safe_int()` and utilities consolidated in utils.py
- [ ] Test framework installed and configured
- [ ] Data loading tests passing (100%)
- [ ] Helper module tests created (≥10 tests)
- [ ] Page smoke tests created (≥7 categories)
- [ ] Documentation updated with testing instructions

**Deliverables:**
- Cleaned codebase (−600 lines)
- Working test suite (≥25 tests)
- Test coverage report
- Updated git commit with changes

---

## Phase 2: Resolve Naming Conflicts

**Duration:** Week 2, ~6 hours
**Risk Level:** LOW-MEDIUM
**Impact:** Eliminate confusion during API design
**Dependencies:** Phase 1 complete (testing infrastructure exists)

### Task 2.1: Rename `render_report` Functions (~2 hours)

**Problem:** 5 different functions, all named `render_report` (impossible to import cleanly)

**Current Locations:**
1. `streamlit/102TEG Results.py`
2. `streamlit/latest_teg_context.py`
3. `streamlit/teg_reports.py`
4. `streamlit/teg_reports_17brief.py`
5. `streamlit/teg_reports_17full.py`

**Rename Strategy:**

| File | Old Name | New Name | Rationale |
|------|----------|----------|-----------|
| 102TEG Results.py | `render_report` | `render_teg_results_report` | Clarifies it's for historical results |
| latest_teg_context.py | `render_report` | `render_latest_teg_report` | Clarifies it's for current TEG |
| teg_reports.py | `render_report` | `render_tournament_report` | Generic tournament report |
| teg_reports_17brief.py | `render_report` | `render_brief_tournament_report` | Brief version |
| teg_reports_17full.py | `render_report` | `render_full_tournament_report` | Full version |

**Implementation:**
```python
# Example for 102TEG Results.py
# OLD:
def render_report():
    """Render TEG results report"""
    # ...

# NEW:
def render_teg_results_report():
    """Render historical TEG results report.

    Displays tournament results in formatted table with winner highlighting.
    Used by the TEG Results page for historical tournament display.
    """
    # ...
```

**Testing:**
```bash
# Run each affected page
streamlit run "streamlit/102TEG Results.py"
streamlit run streamlit/latest_teg_context.py
streamlit run streamlit/teg_reports.py
# etc.

# Verify no import errors
grep -r "render_report" streamlit/*.py | grep "from\|import"
```

**Reference:** [TASK_5_QUICK_REFERENCE.md](TASK_5_QUICK_REFERENCE.md#naming-conflicts-same-name-different-purpose)

---

### Task 2.2: Rename `format_value` Functions (~1 hour)

**Problem:** 4 different implementations, all named `format_value`

**Current Locations:**
1. `streamlit/500Handicaps.py:46`
2. `streamlit/leaderboard_utils.py:72`
3. `streamlit/make_charts.py:13`
4. `streamlit/helpers/records_identification.py:31`

**Rename Strategy:**

| File | New Name | Purpose |
|------|----------|---------|
| 500Handicaps.py | `format_handicap_value` | Format handicap display values |
| leaderboard_utils.py | `format_leaderboard_value` | Format leaderboard scores |
| make_charts.py | `format_chart_value` | Format values for chart display |
| records_identification.py | `format_record_value` | Format record statistics |

**Implementation:** Similar to Task 2.1, update each function and add clear docstrings

**Testing:**
```bash
# Test each affected page/module
streamlit run streamlit/500Handicaps.py
streamlit run streamlit/leaderboard.py
# etc.
```

---

### Task 2.3: Review MEDIUM-Confidence Unused Code (~3 hours)

**Target:** 11 functions marked as "imported but not called" - needs team review

**Categories:**

#### Class Initializers (3 functions)
- `commentary/generate_round_report.py:80` - `__init__`
- `commentary/generate_tournament_commentary_v2.py:297` - `__init__`
- `helpers/commentary_generator.py:37` - `__init__`

**Question:** Are these classes actually instantiated? Or is this dead code?

**Action:**
1. Search for class instantiation: `grep "ClassName()" streamlit/**/*.py`
2. If zero hits: Archive class entirely
3. If used: Keep and document usage

#### Duplicate Definitions (2 functions)
- `display_completeness_status` appears at lines 404 AND 694 in same file

**Action:** Already handled in Phase 1 Task 1.1.1 (verify completion)

#### Imported But Not Called (6 functions)
1. `format_percentage_for_display` - helpers/score_count_processing.py:230
2. `create_stacked_bar_chart` - helpers/score_count_processing.py:254
3. `create_achievement_tab_labels` - helpers/scoring_achievements_processing.py:32
4. `theme_for` - styles/altair_theme.py:193
5. `clear_volume_cache` - utils.py:650 (usage commented out!)
6. `add_section_navigation_links` - utils.py:4193

**Action:**
```bash
# For each function, verify usage:
grep -r "function_name" streamlit/**/*.py | grep -v "^.*:.*def function_name"

# If grep finds:
# - Zero hits: Archive (HIGH confidence unused)
# - Commented usage: Uncomment or archive
# - Active usage: Mark as false positive, keep function
```

**Outcome:** Clear decision on each function (archive or keep with rationale)

**Documentation:** Update ANALYSIS_SUMMARY_FINAL.md with decisions

---

### Phase 2 Success Criteria

- [ ] Zero functions named `render_report` (5 renamed)
- [ ] Zero functions named `format_value` (4 renamed)
- [ ] All MEDIUM-confidence unused functions reviewed
- [ ] Decision documented for each of 11 functions
- [ ] All tests still passing (verify with pytest)
- [ ] Git commit with clear naming

**Deliverables:**
- Codebase with clear, unambiguous function names
- Documentation of unused code decisions
- Updated tests (if any renames affected tests)

---

## Phase 3: Address Critical Technical Debt

**Duration:** Week 3, ~8 hours
**Risk Level:** MEDIUM
**Impact:** Simplify architecture before refactoring
**Dependencies:** Phase 1 and 2 complete

### Task 3.1: Consolidate Data Loaders (~4 hours)

**Problem:** Two competing data loader implementations:
- `streamlit/commentary/round_data_loader.py` (old version)
- `streamlit/commentary/unified_round_data_loader.py` (new version)

**Current State:**
- Some files import from `round_data_loader`
- Some files import from `unified_round_data_loader`
- `unified_round_data_loader` has more features and bug fixes
- Duplicated functions: `calculate_hole_difficulty`, `get_previous_round_scores`

**Goal:** Single source of truth for round data loading

#### Subtask 3.1.1: Identify All Usages (30 minutes)

**Action:**
```bash
# Find all imports of old loader
grep -r "from.*round_data_loader import" streamlit/**/*.py
grep -r "import.*round_data_loader" streamlit/**/*.py

# Document each file that needs updating
```

**Create Migration Checklist:**
```markdown
Files using round_data_loader:
- [ ] streamlit/commentary/generate_round_report.py
- [ ] streamlit/commentary/some_other_file.py
# ... etc.
```

#### Subtask 3.1.2: Update Imports (1 hour)

**For each file using old loader:**
```python
# OLD:
from commentary.round_data_loader import load_round_data, calculate_hole_difficulty

# NEW:
from commentary.unified_round_data_loader import load_round_data, calculate_hole_difficulty
```

**Testing After Each Change:**
```bash
# Verify file still works
python -m streamlit.file_that_was_changed

# Run related tests
pytest tests/test_commentary.py -v
```

#### Subtask 3.1.3: Archive Old Loader (30 minutes)

**Once all imports updated:**
```bash
# Move old file to archive
mkdir -p streamlit/archive/deprecated_2025_10_19
git mv streamlit/commentary/round_data_loader.py streamlit/archive/deprecated_2025_10_19/

# Add note in archive
```

**Verification:**
```bash
# Should return no results
grep -r "round_data_loader" streamlit/**/*.py | grep -v "unified_round_data_loader"
```

#### Subtask 3.1.4: Comprehensive Testing (2 hours)

**Test All Commentary Generation:**
- Generate round reports for multiple TEGs
- Generate tournament commentary
- Verify hole difficulty calculations correct
- Check previous round score lookups

**Regression Testing:**
- Compare output before/after migration
- Verify no data differences
- Check performance (should be same or better)

**Reference:** [TASK_5_QUICK_REFERENCE.md](TASK_5_QUICK_REFERENCE.md#week-3-data-loader-consolidation)

**Impact:** Single, well-tested data loader. Eliminates architectural confusion.

---

### Task 3.2: Document utils.py Function Categories (~2 hours)

**Problem:** utils.py is 4,406 lines with 102 functions, no clear organization

**Goal:** Add section headers and docstrings for navigation

#### Subtask 3.2.1: Add Section Headers (1 hour)

**Use existing documentation as guide:** [inventory/UTILS_INVENTORY_MASTER.md](inventory/UTILS_INVENTORY_MASTER.md)

**Add to utils.py:**
```python
# ============================================================================
# CONFIGURATION & SETUP (4 functions)
# ============================================================================
# Functions for page layout, directory setup, and cache management
#
# Functions:
# - get_page_layout() - Get layout setting for page
# - clear_all_caches() - Clear all Streamlit data caches
# - get_base_directory() - Get project base directory
# - CONSTANTS section - File paths, GitHub repo, etc.

def get_page_layout(page_file: str) -> str:
    # ...

# ============================================================================
# GITHUB I/O (5 functions)
# ============================================================================
# Functions for reading/writing files via GitHub API
#
# Functions:
# - read_from_github() - Read file content from GitHub
# - write_to_github() - Write file to GitHub
# - batch_commit_to_github() - Batch multiple file writes
# - read_text_from_github() - Read text file from GitHub
# - write_text_to_github() - Write text file to GitHub

def read_from_github(file_path: str) -> pd.DataFrame:
    # ...

# ... continue for all 16 sections
```

**Section Organization (from docs):**
1. Configuration & Setup (4 functions)
2. GitHub I/O (5 functions)
3. Railway Volume Management (10 functions)
4. Core Data Loading (6 functions)
5. Data Transforms (6 functions)
6. Cache Updates (7 functions)
7. Commentary - Round Summary (1 function)
8. Commentary - Events & Tournament (2 functions)
9. Commentary - Streaks & Validation (3 functions)
10. Aggregation Core (10 functions)
11. Aggregation Ranking (10 functions)
12. Helpers - Formatting (11 functions)
13. Helpers - Scoring & CSS (8 functions)
14. Helpers - Handicap & Status (9 functions)
15. TEG Status & URL (6 functions)
16. Navigation & UI (5 functions)

#### Subtask 3.2.2: Add Table of Contents (30 minutes)

**Add at top of utils.py after imports:**
```python
"""
TEG Analysis Utilities Module

This module contains all core utility functions for the TEG golf tournament
analysis system. Functions are organized into 16 logical sections.

TABLE OF CONTENTS:
=================

CONFIGURATION & SETUP (Lines 24-76)
├── get_page_layout()           - Page layout configuration
├── clear_all_caches()          - Cache management
└── get_base_directory()        - Directory setup

GITHUB I/O (Lines 110-250)
├── read_from_github()          - Read files from GitHub
├── write_to_github()           - Write files to GitHub
└── ... (see section for full list)

DATA LOADING (Lines 300-600)
├── load_all_data()             - Main data loading function
├── read_file()                 - Environment-aware file reading
└── ... (see section for full list)

... [continue for all sections]

MIGRATION NOTES:
===============
During refactoring, functions will be migrated to:
- teg_analysis/io/ - I/O functions (Section 2-3)
- teg_analysis/core/ - Data loading (Section 4-5)
- teg_analysis/analysis/ - Commentary & aggregation (Section 7-11)
- UI functions stay in utils.py (Section 15-16)

See docs/migration_impact.md for detailed migration plan.
"""
```

#### Subtask 3.2.3: Update Function Docstrings (30 minutes)

**For any functions missing docstrings or with minimal docs:**
```python
# BEFORE:
def format_vs_par(value):
    # Basic formatting
    pass

# AFTER:
def format_vs_par(value: int) -> str:
    """Format a score relative to par for display.

    Converts integer score vs par to formatted string:
    - 0 → "E" (even par)
    - Positive → "+N" (over par)
    - Negative → "-N" (under par)

    Args:
        value: Score relative to par (integer)

    Returns:
        str: Formatted string for display

    Example:
        >>> format_vs_par(0)
        'E'
        >>> format_vs_par(3)
        '+3'
        >>> format_vs_par(-2)
        '-2'

    Used by: 13 files (see DEPENDENCIES.md)
    Migration target: teg_analysis/display/formatters.py
    """
    # Implementation...
```

**Testing:**
```bash
# Verify no syntax errors
python -c "import streamlit.utils"

# Run basic tests
pytest tests/test_utils.py -v
```

**Impact:** Makes utils.py navigable. Migration planning becomes trivial.

---

### Task 3.3: Fix O(n²) Performance Issues (~2 hours)

**Problem:** Documented performance issues that will be enshrined in refactored code

#### Critical Function: `create_round_summary()`

**Location:** utils.py (exact line TBD from docs)
**Issue:** O(n²) algorithm, documented 10-20x speedup potential
**Reference:** [MASTER_DOCUMENTATION_GUIDE.md](MASTER_DOCUMENTATION_GUIDE.md#performance-insights)

#### Subtask 3.3.1: Profile Current Performance (30 minutes)

**Create:** `tests/test_performance.py`
```python
"""Performance benchmarks for critical functions"""
import pytest
import time
from utils import create_round_summary, load_all_data

def test_create_round_summary_performance():
    """Benchmark create_round_summary"""
    df = load_all_data()

    start = time.time()
    result = create_round_summary(df)
    elapsed = time.time() - start

    print(f"\ncreate_round_summary took {elapsed:.2f} seconds")

    # Document baseline performance
    assert elapsed < 30  # Currently takes 10-30 seconds per docs
```

**Run baseline:**
```bash
pytest tests/test_performance.py -v -s
# Record baseline time
```

#### Subtask 3.3.2: Optimize Algorithm (1 hour)

**Analysis:** Review function implementation
- Identify nested loops
- Replace with vectorized pandas operations
- Use groupby() instead of iterrows()
- Leverage numpy for calculations

**Example Optimization Pattern:**
```python
# BEFORE (O(n²)):
def create_round_summary_slow(df):
    results = []
    for player in df['Player'].unique():
        for round_num in df['Round'].unique():
            subset = df[(df['Player'] == player) & (df['Round'] == round_num)]
            results.append(subset.sum())
    return pd.DataFrame(results)

# AFTER (O(n)):
def create_round_summary_fast(df):
    return df.groupby(['Player', 'Round']).sum().reset_index()
```

**Testing:**
```bash
# Verify correctness (results identical)
pytest tests/test_round_summary_correctness.py -v

# Measure performance improvement
pytest tests/test_performance.py -v -s
# Target: <3 seconds (10x speedup)
```

#### Subtask 3.3.3: Regression Testing (30 minutes)

**Verify no behavior changes:**
- Compare output before/after on multiple TEGs
- Check edge cases (single round, missing data)
- Verify all pages using function still work

**Impact:** Don't migrate slow code. Fix performance issues while code is still in one place.

---

### Phase 3 Success Criteria

- [ ] Single data loader (unified version only)
- [ ] Old round_data_loader archived
- [ ] All commentary generation tested and working
- [ ] utils.py has 16 clear section headers
- [ ] utils.py has table of contents
- [ ] All major functions have complete docstrings
- [ ] create_round_summary() optimized (≥10x faster)
- [ ] Performance benchmarks passing
- [ ] All tests passing (100%)

**Deliverables:**
- Consolidated, well-documented codebase
- Performance improvements measured and verified
- Updated git history with optimization commits

---

## Phase 4: Create Migration Architecture

**Duration:** Week 4, ~6 hours
**Risk Level:** LOW (planning only, no code changes)
**Impact:** Clear blueprint for refactoring
**Dependencies:** Phases 1-3 complete (clean codebase)

### Task 4.1: Design `teg_analysis/` Package Structure (~3 hours)

**Goal:** Define target architecture for refactored code

#### Subtask 4.1.1: Define Module Structure (1 hour)

**Proposed Structure:**
```
teg_analysis/
├── __init__.py                  # Package initialization
│
├── core/                        # Core data structures and loading
│   ├── __init__.py
│   ├── data_loader.py          # Main data loading (from utils.py)
│   ├── data_transforms.py      # Data transformation functions
│   └── models.py               # Data models/classes (if needed)
│
├── io/                         # Input/output operations
│   ├── __init__.py
│   ├── file_operations.py      # File I/O (environment-aware)
│   ├── github_operations.py    # GitHub API operations
│   └── volume_operations.py    # Railway volume management
│
├── analysis/                   # Analysis and calculation functions
│   ├── __init__.py
│   ├── scoring.py              # Scoring calculations
│   ├── streaks.py              # Streak analysis
│   ├── records.py              # Records identification
│   ├── rankings.py             # Ranking calculations
│   ├── aggregation.py          # Aggregation functions
│   └── commentary.py           # Commentary generation
│
├── display/                    # Display and formatting functions
│   ├── __init__.py
│   ├── formatters.py           # Value formatting functions
│   ├── tables.py               # Table generation
│   └── charts.py               # Chart generation helpers
│
└── api/                        # Public API (future)
    ├── __init__.py
    ├── routes.py               # API endpoints
    └── schemas.py              # API data schemas
```

**Decision Points:**
1. **Streamlit Dependencies:** Where do functions that use `@st.cache_data` go?
   - Option A: Keep caching in new modules (requires streamlit dependency)
   - Option B: Remove caching, add back in calling code
   - **Recommendation:** Option A - keep caching for now, refactor later

2. **Helper Modules:** Map each current helper to target module
   - `scoring_data_processing.py` → `teg_analysis/analysis/scoring.py`
   - `streak_analysis_processing.py` → `teg_analysis/analysis/streaks.py`
   - `display_helpers.py` → `teg_analysis/display/formatters.py`
   - etc. (see full mapping below)

3. **Utils.py Functions:** Categorize all 102 functions by destination
   - See [inventory/UTILS_INVENTORY_MASTER.md](inventory/UTILS_INVENTORY_MASTER.md) for details

#### Subtask 4.1.2: Map Functions to Modules (1 hour)

**Create:** `docs/REFACTORING_FUNCTION_MAP.md`

**Format:**
```markdown
# Function Migration Map

## From utils.py

### → teg_analysis/io/file_operations.py
- read_file()                    [Line 123]
- write_file()                   [Line 456]
- backup_file()                  [Line 789]

### → teg_analysis/core/data_loader.py
- load_all_data()                [Line 234]
- process_round_for_all_scores() [Line 567]
- add_cumulative_scores()        [Line 890]

... [continue for all 102 functions]

## From helpers/

### scoring_data_processing.py → teg_analysis/analysis/scoring.py
- All functions (12 total)

### streak_analysis_processing.py → teg_analysis/analysis/streaks.py
- All functions (15 total)

... [continue for all 20 helper modules]

## Functions Staying in utils.py (Streamlit UI layer)
- get_page_layout()              [Stay - UI config]
- add_custom_navigation_links()  [Stay - UI helper]
- load_datawrapper_css()         [Stay - UI styling]
```

**Validation:**
- Every function accounted for
- No overlapping destinations
- Dependencies resolved (see Task 4.2)

#### Subtask 4.1.3: Resolve Streamlit Caching Dependencies (1 hour)

**Problem:** Many functions use `@st.cache_data` decorator

**Strategy:**
```python
# Option 1: Keep caching in new modules
# teg_analysis/core/data_loader.py
import streamlit as st

@st.cache_data
def load_all_data() -> pd.DataFrame:
    """Load all data with caching"""
    pass

# Option 2: Remove caching, add in calling code
# teg_analysis/core/data_loader.py
def load_all_data() -> pd.DataFrame:
    """Load all data (no caching)"""
    pass

# streamlit/utils.py
import streamlit as st
from teg_analysis.core import load_all_data as _load_all_data

@st.cache_data
def load_all_data() -> pd.DataFrame:
    """Cached wrapper for load_all_data"""
    return _load_all_data()
```

**Decision:** Document approach for refactoring phase

---

### Task 4.2: Create Dependency-Ordered Migration Plan (~2 hours)

**Goal:** Sequence migrations to avoid breaking dependencies

#### Subtask 4.2.1: Update Migration Plan (1 hour)

**Base Document:** [migration_impact.md](migration_impact.md) (already exists)

**Update with:**
- Cleaned function list (post-Phase 1-3)
- Updated line numbers (after deletions)
- Testing requirements per phase
- Rollback procedures

**Create:** `docs/REFACTORING_MIGRATION_SEQUENCE.md`

**Format:**
```markdown
# Migration Execution Sequence

## Migration Phase 1: I/O Functions (Week 1)
**Duration:** 5 hours
**Risk:** Medium
**Blockers:** None

### Pre-requisites
- [ ] Tests passing (100%)
- [ ] Git branch: refactor/phase-1-io
- [ ] Backup created

### Functions to Migrate (10 functions)
1. read_file() [utils.py:123]
2. write_file() [utils.py:456]
... [all I/O functions]

### Migration Steps
1. Create teg_analysis/io/file_operations.py
2. Copy functions (keep originals)
3. Update imports in teg_analysis/
4. Test new module independently
5. Update imports in streamlit/ files (one at a time)
6. Test after each file update
7. Delete original functions from utils.py
8. Final full test suite

### Testing Checklist
- [ ] New module imports successfully
- [ ] All 22 dependent files updated
- [ ] No import errors
- [ ] All pages load correctly
- [ ] Data read/write operations work
- [ ] Railway environment tested

### Success Criteria
- [ ] All tests passing
- [ ] Zero import errors
- [ ] All pages functional
- [ ] Performance unchanged

... [continue for all migration phases]
```

#### Subtask 4.2.2: Create Migration Checklist (1 hour)

**Create:** `docs/REFACTORING_CHECKLIST.md`

**Format:**
```markdown
# Refactoring Execution Checklist

## Pre-Migration Setup
- [ ] All Phase 1-4 tasks complete
- [ ] Test suite at 100% passing
- [ ] Git working directory clean
- [ ] Backup created
- [ ] Team notified

## Phase 1: I/O Functions
- [ ] Branch created: refactor/phase-1-io
- [ ] Module structure created
- [ ] Functions copied
- [ ] Tests passing
- [ ] Imports updated (0/22 files)
- [ ] Original functions removed
- [ ] Final tests passing
- [ ] PR created and reviewed
- [ ] Merged to main

## Phase 2: Core Data Loading
... [similar checklist]

## Post-Migration Validation
- [ ] All tests passing
- [ ] No import errors
- [ ] All pages functional
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Team trained on new structure
```

---

### Task 4.3: Define API Surface (~1 hour)

**Goal:** Identify functions that will become public API

#### Subtask 4.3.1: Identify Core API Functions (30 minutes)

**Criteria for Public API:**
1. Used by ≥3 files (high reuse)
2. Pure functions (no side effects)
3. Clear, stable interface
4. Well-documented

**Based on docs, likely candidates:**

**Data Loading API:**
```python
# teg_analysis/api/data.py
def load_tournament_data(
    teg_number: Optional[int] = None,
    include_incomplete: bool = False
) -> pd.DataFrame:
    """Load TEG tournament data"""

def load_player_statistics(
    player_code: str,
    stat_types: List[str]
) -> dict:
    """Load player statistics"""
```

**Analysis API:**
```python
# teg_analysis/api/analysis.py
def calculate_handicaps(
    player_data: pd.DataFrame
) -> pd.DataFrame:
    """Calculate player handicaps"""

def identify_records(
    data: pd.DataFrame,
    record_types: List[str]
) -> dict:
    """Identify tournament records"""

def analyze_streaks(
    player_data: pd.DataFrame,
    streak_type: str
) -> pd.DataFrame:
    """Analyze scoring streaks"""
```

**Formatting API:**
```python
# teg_analysis/api/display.py
def format_score(
    value: int,
    format_type: str = "vs_par"
) -> str:
    """Format score for display"""

def generate_scorecard(
    round_data: pd.DataFrame,
    options: dict
) -> str:
    """Generate HTML scorecard"""
```

#### Subtask 4.3.2: Document API Expectations (30 minutes)

**Create:** `docs/API_DESIGN.md`

**Format:**
```markdown
# TEG Analysis API Design

## Design Principles
1. Simple, intuitive function names
2. Clear input/output contracts
3. Comprehensive docstrings
4. Type hints for all parameters
5. Backward compatibility where possible

## API Modules

### teg_analysis.api.data
Functions for loading and accessing tournament data.

**load_tournament_data()**
```python
def load_tournament_data(
    teg_number: Optional[int] = None,
    include_incomplete: bool = False,
    columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """Load TEG tournament data.

    Args:
        teg_number: Specific TEG to load (None = all TEGs)
        include_incomplete: Include TEGs in progress
        columns: Specific columns to load (None = all)

    Returns:
        DataFrame with requested data

    Raises:
        ValueError: If teg_number doesn't exist

    Example:
        >>> df = load_tournament_data(teg_number=17)
        >>> df.shape
        (1440, 25)
    """
```

... [continue for all API functions]
```

---

### Phase 4 Success Criteria

- [ ] Package structure defined (`teg_analysis/` hierarchy)
- [ ] All 102 utils.py functions mapped to destinations
- [ ] All 20 helper modules mapped
- [ ] Streamlit caching strategy decided
- [ ] Migration sequence documented
- [ ] Phase-by-phase checklists created
- [ ] Core API surface defined (20-30 functions)
- [ ] API documentation written

**Deliverables:**
- `docs/REFACTORING_FUNCTION_MAP.md` (complete function mapping)
- `docs/REFACTORING_MIGRATION_SEQUENCE.md` (execution plan)
- `docs/REFACTORING_CHECKLIST.md` (tracking tool)
- `docs/API_DESIGN.md` (API specification)
- Updated migration_impact.md

---

## Summary: Pre-Refactoring Readiness

### Before Starting This Plan
- 79 files, 530 functions
- ~600 lines of duplicate/dead code
- 38 naming conflicts
- Zero tests
- 4,406-line utils.py with no organization
- Competing implementations
- Documented but unfixed performance issues

### After Completing This Plan
- Clean codebase (−600 lines)
- Zero within-file duplicates
- Clear, unambiguous names
- Test coverage (≥50 tests)
- Organized, documented utils.py
- Single data loader
- Optimized algorithms
- Detailed refactoring blueprint
- Defined API surface

### Estimated Time Investment

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Phase 1: Quick Wins** | Week 1, ~8h | Delete waste, create tests |
| **Phase 2: Naming** | Week 2, ~6h | Resolve conflicts |
| **Phase 3: Technical Debt** | Week 3, ~8h | Consolidate, optimize |
| **Phase 4: Architecture** | Week 4, ~6h | Plan refactoring |
| **TOTAL** | 4 weeks, ~28h | Ready for refactoring |

### Expected ROI

**Time Saved:**
- 50%+ faster refactoring (clear targets, no confusion)
- Fewer bugs (testing infrastructure catches issues)
- Less rework (don't migrate code that gets deleted)

**Risk Reduced:**
- Test coverage prevents regressions
- Clear names prevent mistakes
- Consolidated code reduces migration complexity

**Quality Improved:**
- Cleaner starting point
- Optimized algorithms
- Better documentation

---

## Next Steps

1. **Review this plan** with team
2. **Adjust timelines** based on availability
3. **Start Phase 1 Task 1.4** (testing infrastructure) - MOST CRITICAL
4. **Execute phases sequentially** (don't skip ahead)
5. **Track progress** using TODO lists
6. **Update documentation** as you complete tasks

---

## References

**Key Documentation:**
- [README.md](README.md) - Documentation overview
- [MASTER_DOCUMENTATION_GUIDE.md](MASTER_DOCUMENTATION_GUIDE.md) - Complete task summary
- [TASK_5_QUICK_REFERENCE.md](TASK_5_QUICK_REFERENCE.md) - Duplication quick reference
- [analysis/ANALYSIS_SUMMARY_FINAL.md](analysis/ANALYSIS_SUMMARY_FINAL.md) - Unused code summary
- [migration_impact.md](migration_impact.md) - Original migration plan
- [DEPENDENCIES.md](DEPENDENCIES.md) - Dependency map

**Analysis Data:**
- `function_analysis.json` - All 530 functions analyzed
- `dependency_graph.json` - Complete dependency map
- `unused_code_analysis_simple.json` - Unused code data
- `validation_results.json` - Grep validation results

---

**Document Status:** ACTIVE PLAN
**Last Updated:** 2025-10-19
**Next Review:** After Phase 1 completion
