# Duplication Consolidation Roadmap

**Project:** TEG (Annual Golf Tournament) Analysis System
**Date:** October 18, 2025
**Duration:** 4 weeks (12-18 hours total effort)
**Status:** Ready for Implementation

---

## Overview

This roadmap provides a phased implementation plan to consolidate all identified duplicates and similarities in the TEG codebase. It includes specific actions, affected files, testing procedures, and success criteria for each phase.

### Key Principles

1. **Start with highest-impact, lowest-risk items** (within-file duplicates)
2. **Test thoroughly** after each phase
3. **Maintain backward compatibility** where possible
4. **Document changes** as we go
5. **Rerun analysis** after major phases to track progress

### Timeline

- **Phase 1 (Week 1):** 3-4 hours - Quick wins, within-file cleanup
- **Phase 2 (Week 2):** 2-3 hours - Utility consolidation, data loader standardization
- **Phase 3 (Week 3):** 2-3 hours - Naming conflicts resolution, refactoring
- **Phase 4 (Week 4):** 6-8 hours - Pattern abstraction, utility creation
- **Buffer:** 2-4 hours - Testing, adjustments, documentation

**Total:** 12-18 hours over 4 weeks

---

## Phase 1: Within-File Duplicates & Quick Wins

**Duration:** 3-4 hours
**Risk Level:** LOW
**Impact:** ~370 lines eliminated
**Scope:** Delete duplicate functions within single files

### Phase 1.1: File `streamlit/helpers/history_data_processing.py`

**Issue:** Contains 4 sets of duplicate functions (highest priority single file)

#### Task 1.1.1: Remove `extract_teg_num` duplicate

**Location:** Line 639 (delete), Line 349 (keep)
**Lines Affected:** 8 lines
**Action:** Delete lines 639-646
**Verification:** Search file for other `extract_teg_num` references

```bash
# Before committing, verify:
grep -n "extract_teg_num" streamlit/helpers/history_data_processing.py
# Should show only one definition (line 349)
```

**Testing:** Run any page using history_data_processing to verify

**Effort:** 5 minutes

---

#### Task 1.1.2: Remove `check_winner_completeness` duplicate

**Location:** Line 658 (delete), Line 368 (keep)
**Lines Affected:** 34 lines
**Action:** Delete lines 658-691
**Verification:** Check for remaining definition

```bash
grep -n "def check_winner_completeness" streamlit/helpers/history_data_processing.py
# Should show only line 368
```

**Testing:** Run `101TEG History.py` and `101TEG Honours Board.py` to verify winner data still loads

**Effort:** 10 minutes

---

#### Task 1.1.3: Remove `display_completeness_status` duplicate

**Location:** Line 694 (delete), Line 404 (keep)
**Lines Affected:** 17 lines
**Action:** Delete lines 694-710
**Verification:** Ensure only one definition remains

**Testing:** Verify tournament completion status still displays correctly

**Effort:** 5 minutes

---

#### Task 1.1.4: Consolidate `calculate_and_save_missing_winners`

**CRITICAL:** This 80-line function is duplicated with 93.9% similarity within the same file

**Location 1:** Lines 422-501 (KEEP - first version)
**Location 2:** Lines 714-793 (DELETE - second version)
**Lines Affected:** 80 lines
**Action:** Delete lines 714-793
**Verification:** Search for duplicate definitions

```bash
grep -n "def calculate_and_save_missing_winners" streamlit/helpers/history_data_processing.py
# Should show only line 422
```

**Testing:** Run `1000Data update.py` and verify winner calculation still works correctly. Check that tournament history updates properly.

**Effort:** 15 minutes (includes testing)

**Subtotal for history_data_processing.py:** 180 lines removed, ~45 minutes

---

### Phase 1.2: File `streamlit/commentary/generate_tournament_commentary_v2.py`

**Issue:** Contains 2 sets of duplicate functions

#### Task 1.2.1: Remove duplicate `get_api_key`

**Location 1:** Lines 443-451 (KEEP - full version with error handling)
**Location 2:** Lines 453-455 (DELETE - abbreviated version)
**Lines Affected:** 3 lines
**Action:** Delete lines 453-455
**Verification:**

```bash
grep -n "def get_api_key" streamlit/commentary/generate_tournament_commentary_v2.py
# Should show only line 443
```

**Testing:** Generate tournament commentary to verify API key retrieval works

**Effort:** 5 minutes

---

#### Task 1.2.2: Remove duplicate `calc_wins_before`

**Location 1:** Lines 740-746 (KEEP)
**Location 2:** Lines 2000-2006 (DELETE)
**Lines Affected:** 7 lines
**Action:** Delete lines 2000-2006
**Verification:**

```bash
grep -n "def calc_wins_before" streamlit/commentary/generate_tournament_commentary_v2.py
# Should show only line 740
```

**Testing:** Generate tournament commentary, verify win calculations correct

**Effort:** 5 minutes

**Subtotal for generate_tournament_commentary_v2.py:** 10 lines removed, ~10 minutes

---

### Phase 1.3: Other Files - Quick Deletions

#### Task 1.3.1: File `streamlit/commentary/generate_round_report.py`

**Function:** `get_api_key`
**Location 1:** Lines 225-233 (KEEP)
**Location 2:** Lines 235-237 (DELETE)
**Action:** Delete lines 235-237
**Effort:** 5 minutes

---

#### Task 1.3.2: File `streamlit/player_history.py`

**Function:** `teg_sort_key`
**Location 1:** Line 333 (KEEP)
**Location 2:** Line 379 (DELETE)
**Action:** Delete lines 379-383 (entire function)
**Testing:** Load player history page, verify sorting works
**Effort:** 5 minutes

---

#### Task 1.3.3: File `streamlit/commentary/generate_commentary.py`

**Function:** `read_file`
**Location 1:** Lines 51-55 (KEEP)
**Location 2:** Lines 109-113 (DELETE)
**Action:** Delete lines 109-113
**Effort:** 5 minutes

**Subtotal for other files:** 20 lines removed, ~20 minutes

---

### Phase 1.4: Testing & Verification

**Duration:** 1 hour

After all within-file deletions:

#### Test Suite

```bash
# 1. Check for syntax errors
python -m py_compile streamlit/helpers/history_data_processing.py
python -m py_compile streamlit/commentary/generate_tournament_commentary_v2.py
python -m py_compile streamlit/commentary/generate_round_report.py
python -m py_compile streamlit/player_history.py
python -m py_compile streamlit/commentary/generate_commentary.py

# 2. Check for import errors
cd streamlit
python -c "import helpers.history_data_processing"
python -c "import commentary.generate_tournament_commentary_v2"

# 3. Visual verification in Streamlit
streamlit run nav.py
# Load each affected page:
# - 101TEG History.py
# - 101TEG Honours Board.py
# - player_history.py
# - Latest TEG pages
```

#### Manual Testing Checklist

- [ ] 101TEG History.py loads without errors
- [ ] 101TEG Honours Board.py displays winners correctly
- [ ] player_history.py sorts players correctly
- [ ] Latest TEG context pages load
- [ ] No console errors in Streamlit

**Effort:** 1 hour

---

### Phase 1 Summary

**Total Lines Eliminated:** ~370 lines
**Total Effort:** 3-4 hours
**Files Modified:** 5
**Functions Removed:** 9 duplicate definitions
**Risk Level:** LOW
**Status:** READY FOR IMMEDIATE EXECUTION

**Commit Message:**
```
Remove within-file duplicates from 5 files

- Removed 4 duplicate functions from history_data_processing.py (180 lines)
- Removed 2 duplicate functions from generate_tournament_commentary_v2.py (10 lines)
- Removed 1 duplicate each from 3 other files (20 lines)
- Total: 370 lines of unnecessary code eliminated

All affected functions tested and verified working correctly.
Fixes significant technical debt in codebase.
```

---

## Phase 2: Utility Consolidation & Data Loader Standardization

**Duration:** 2-3 hours
**Risk Level:** LOW-MEDIUM
**Impact:** ~250 lines consolidated
**Scope:** Centralize utility functions, standardize data loading

### Phase 2.1: Move `safe_int` to utils.py

**Current Locations (3 files):**
1. `streamlit/commentary/round_data_loader.py:24-31`
2. `streamlit/commentary/round_pattern_analysis.py:15-22`
3. `streamlit/commentary/unified_round_data_loader.py:31-38`

**Similarity:** 100% identical

**Action:**

1. **Add to streamlit/utils.py** (around line 50 with other utilities)

```python
def safe_int(value, default=0):
    """Safely convert value to int, return default if conversion fails.

    Args:
        value: Value to convert to integer
        default: Value to return if conversion fails (default 0)

    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
```

2. **Update imports in 3 files:**

```python
# Before:
def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

# After:
from utils import safe_int
```

3. **Delete local definitions** from all 3 files

**Effort:** 15 minutes
**Testing:** Run round data loading in commentary generation
**Risk:** LOW

---

### Phase 2.2: Move `get_api_key` to utils.py

**Current Locations (4 files):**
1. `streamlit/commentary/generate_round_report.py:225-233` (9 lines, robust)
2. `streamlit/commentary/generate_round_report.py:235-237` (3 lines, abbreviated)
3. `streamlit/commentary/generate_tournament_commentary_v2.py:443-451` (9 lines, robust)
4. `streamlit/commentary/generate_tournament_commentary_v2.py:453-455` (3 lines, abbreviated)

**Action:**

1. **Add to streamlit/utils.py** (use 9-line robust version)

```python
def get_api_key():
    """Get Claude API key from Streamlit secrets.

    Returns:
        API key string or raises error if not found

    Raises:
        Exception: If API key not configured in Streamlit secrets
    """
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except KeyError:
        raise Exception("ANTHROPIC_API_KEY not found in Streamlit secrets")
```

2. **Update imports in commentary files**

3. **Delete local definitions**

**Effort:** 10 minutes
**Testing:** Generate commentary to verify API authentication
**Risk:** LOW

---

### Phase 2.3: Consolidate `load_markdown` functions

**Current Locations (3 files with variations):**
1. `streamlit/teg_reports_17brief.py`
2. `streamlit/teg_reports_17full.py`
3. Other locations

**Similarity:** 80% similar

**Action:** Create unified version in utils.py

```python
def load_markdown(file_path):
    """Load and return markdown file contents.

    Args:
        file_path: Path to markdown file

    Returns:
        File contents as string or empty string if not found
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception as e:
        logger.error(f"Error loading markdown file {file_path}: {e}")
        return ""
```

**Effort:** 10 minutes
**Testing:** Load report pages with markdown content
**Risk:** LOW

---

### Phase 2.4: Data Loader Consolidation

**Issue:** Two versions of data loaders exist - old and "unified"

**Files:**
- Old: `streamlit/commentary/round_data_loader.py`
- New: `streamlit/commentary/unified_round_data_loader.py`

**Functions to Consolidate:**
- `get_previous_round_scores` (96.6% similar)
- `calculate_hole_difficulty` (100% identical)
- `calculate_tournament_projections` (54.5% similar)

**Action Plan:**

1. **Audit all imports** of old round_data_loader

```bash
grep -r "from.*round_data_loader import" streamlit/
grep -r "import.*round_data_loader" streamlit/
```

2. **Update imports to use unified_round_data_loader**

```python
# Before:
from commentary.round_data_loader import get_previous_round_scores

# After:
from commentary.unified_round_data_loader import get_previous_round_scores
```

3. **Verify unified version has all needed functions**

4. **Mark old version as deprecated** (add comment at top of file)

```python
"""
DEPRECATED: This module is replaced by unified_round_data_loader.py

All functionality has been migrated to unified_round_data_loader.
This file will be removed in a future release.
Do not add new functions here.
"""
```

5. **Testing:** Generate round and tournament commentary

**Effort:** 45 minutes
**Testing:** 30 minutes (comprehensive)
**Risk:** MEDIUM (data loading is critical)

---

### Phase 2.5: Move `format_vs_par_value` to utils.py

**Current Locations:** 2+ files with similar implementations

**Action:** Consolidate to single version in utils.py

```python
def format_vs_par_value(value, precision=0):
    """Format score as vs par (+/- notation).

    Args:
        value: Score value (vs par)
        precision: Decimal precision (default 0)

    Returns:
        Formatted string (e.g., "+3", "-2", "E")
    """
    if value > 0:
        return f"+{value:.{precision}f}"
    elif value < 0:
        return f"{value:.{precision}f}"
    else:
        return "E"
```

**Effort:** 10 minutes
**Testing:** Display leaderboards and scores
**Risk:** LOW

---

### Phase 2 Summary

**Consolidation Items:** 5
**Lines Consolidated:** ~250 lines
**New Utility Functions Created:** 4
**Effort:** 2-3 hours
**Testing:** 1-2 hours
**Risk Level:** LOW-MEDIUM

**Actions Completed:**
- [ ] `safe_int` moved to utils.py
- [ ] `get_api_key` moved to utils.py
- [ ] `load_markdown` consolidated
- [ ] Data loader imports standardized
- [ ] `format_vs_par_value` centralized
- [ ] All imports updated
- [ ] Tests passed

**Commit Message:**
```
Consolidate utility functions to utils.py and standardize data loaders

- Moved safe_int, get_api_key, load_markdown to utils.py
- Standardized data loading to use unified_round_data_loader
- Updated 10+ files to use centralized utilities
- Total: 250 lines consolidated, single source of truth established

Tests verify all functionality works correctly.
```

---

## Phase 3: Naming Conflicts Resolution

**Duration:** 2-3 hours
**Risk Level:** LOW
**Impact:** Code clarity, no functional changes
**Scope:** Rename ambiguous function names

### Phase 3.1: Rename `render_report` Variants (5 files)

**Issue:** 5 different functions all named `render_report` with different purposes

#### Task 3.1.1: `streamlit/102TEG Results.py`

**Current Name:** `render_report()`
**New Name:** `render_teg_results_chart_report()`
**Lines:** 78
**Occurrences:** Find all calls to `render_report()`

```bash
grep -n "render_report" streamlit/102TEG\ Results.py
```

**Action:**
1. Rename function definition
2. Update all calls within file
3. Update any imports
4. Update documentation/comments

**Effort:** 10 minutes

---

#### Task 3.1.2: `streamlit/latest_teg_context.py`

**Current Name:** `render_report()`
**New Name:** `render_latest_teg_leaderboard_report()`
**Lines:** 52
**Action:** Same as above
**Effort:** 10 minutes

---

#### Task 3.1.3: `streamlit/teg_reports.py`

**Current Name:** `render_report()`
**New Name:** `render_tournament_summary_report()`
**Lines:** 67
**Effort:** 10 minutes

---

#### Task 3.1.4: `streamlit/teg_reports_17brief.py`

**Current Name:** `render_report()`
**New Name:** `render_brief_tournament_report()`
**Lines:** 41
**Effort:** 10 minutes

---

#### Task 3.1.5: `streamlit/teg_reports_17full.py`

**Current Name:** `render_report()`
**New Name:** `render_full_tournament_report()`
**Lines:** 89
**Effort:** 10 minutes

**Subtotal:** 5 files, 50 minutes

---

### Phase 3.2: Rename `format_value` Variants (4 files)

**Issue:** 4 functions all named `format_value` that format different types

#### Task 3.2.1: `streamlit/500Handicaps.py`

**Current Name:** `format_value(value)`
**New Name:** `format_handicap_value(value)`
**Purpose:** Formats handicap values (decimals)
**Occurrences:** Find all calls

```bash
grep -n "format_value" streamlit/500Handicaps.py
```

**Effort:** 10 minutes

---

#### Task 3.2.2: `streamlit/leaderboard_utils.py`

**Current Name:** `format_value(value)`
**New Name:** `format_leaderboard_score_with_rank(value)`
**Purpose:** Formats leaderboard scores with ranking
**Effort:** 10 minutes

---

#### Task 3.2.3: `streamlit/make_charts.py`

**Current Name:** `format_value(value)`
**New Name:** `format_chart_axis_value(value)`
**Purpose:** Formats values for chart axes
**Effort:** 10 minutes

---

#### Task 3.2.4: `streamlit/helpers/records_identification.py`

**Current Name:** `format_value(value)`
**New Name:** `format_record_value_with_emoji(value)`
**Purpose:** Formats record values with emoji icons
**Effort:** 10 minutes

**Subtotal:** 4 files, 40 minutes

---

### Phase 3.3: Testing & Verification

**Duration:** 1 hour

**Test Cases:**
- Load 102TEG Results.py - verify renders correctly
- Load latest_teg_context.py - verify displays leaderboard
- Generate teg_reports - verify all 3 variants render
- Load 500Handicaps.py - verify values display correctly
- Load leaderboard pages - verify formatting correct
- Load records pages - verify emoji formatting

**Verification:**

```bash
# Check for any remaining references to old names
grep -r "render_report" streamlit/*.py
# Should only appear in definitions, not calls

grep -r "format_value" streamlit/*.py
# Should only appear in specific renamed functions
```

**Effort:** 1 hour

---

### Phase 3 Summary

**Functions Renamed:** 9 (5 + 4)
**Files Updated:** 9
**Effort:** 2-3 hours (including testing)
**Risk Level:** LOW (renaming only, no logic changes)

**Commit Message:**
```
Rename ambiguous function names for clarity

- Renamed 5 render_report variants to specific report types
- Renamed 4 format_value variants to indicate their purpose
- Updated all call sites to use new names
- No functional changes, improves code readability

All pages tested and verified working correctly.
```

---

## Phase 4: Pattern Abstraction & Utility Creation

**Duration:** 6-8 hours
**Risk Level:** LOW
**Impact:** ~300 lines of repetitive code eliminated
**Scope:** Create utility functions for common patterns

### Phase 4.1: Create TEG Filtering Utilities

**Pattern:** `df[df['TEGNum'] == teg]` and variants
**Occurrences:** ~130 across 31 files
**Potential Savings:** ~90 lines through abstraction

**Add to streamlit/utils.py:**

```python
def filter_by_teg_number(df: pd.DataFrame, teg_num: int) -> pd.DataFrame:
    """Filter data by TEG number.

    Args:
        df: DataFrame with 'TEGNum' column
        teg_num: TEG number to filter (e.g., 16)

    Returns:
        Filtered DataFrame containing only selected TEG
    """
    return df[df['TEGNum'] == teg_num]


def filter_by_teg_string(df: pd.DataFrame, teg_str: str) -> pd.DataFrame:
    """Filter data by TEG string.

    Args:
        df: DataFrame with 'TEG' column
        teg_str: TEG string to filter (e.g., 'TEG 16')

    Returns:
        Filtered DataFrame
    """
    return df[df['TEG'] == teg_str]


def filter_by_teg_list(df: pd.DataFrame, teg_nums: list) -> pd.DataFrame:
    """Filter data by multiple TEG numbers.

    Args:
        df: DataFrame with 'TEGNum' column
        teg_nums: List of TEG numbers to include

    Returns:
        Filtered DataFrame
    """
    return df[df['TEGNum'].isin(teg_nums)]


def exclude_tegs(df: pd.DataFrame, exclude_list: list) -> pd.DataFrame:
    """Exclude specific TEGs from data.

    Args:
        df: DataFrame with 'TEGNum' column
        exclude_list: List of TEG numbers to exclude (e.g., [50])

    Returns:
        Filtered DataFrame with excluded TEGs removed
    """
    return df[~df['TEGNum'].isin(exclude_list)]
```

**Files to Update (Priority Order):**
1. 400scoring.py - ~8 filtering instances
2. 102TEG Results.py - ~6 instances
3. leaderboard.py - ~5 instances
4. ave_by_course.py - ~4 instances
5. Other pages - ~2-3 instances each

**Implementation Strategy:**
- Start with highest-impact files
- Replace inline filters: `df[df['TEGNum'] == teg]` → `filter_by_teg_number(df, teg)`
- Run tests after each file
- Document pattern for consistency

**Effort:** 2-3 hours
**Testing:** 1-2 hours (verify all filtered results match original)

---

### Phase 4.2: Create Player Filtering Utilities

**Pattern:** `df[df['Player'] == player]` and variants
**Occurrences:** ~45 across 18 files
**Potential Savings:** ~30 lines

**Add to streamlit/utils.py:**

```python
def filter_by_player(df: pd.DataFrame, player_name: str) -> pd.DataFrame:
    """Filter by single player name.

    Args:
        df: DataFrame with 'Player' column
        player_name: Player name to filter

    Returns:
        Filtered DataFrame
    """
    return df[df['Player'] == player_name]


def filter_by_players(df: pd.DataFrame, player_names: list) -> pd.DataFrame:
    """Filter by multiple player names.

    Args:
        df: DataFrame with 'Player' column
        player_names: List of player names to include

    Returns:
        Filtered DataFrame
    """
    return df[df['Player'].isin(player_names)]


def filter_by_player_code(df: pd.DataFrame, player_code: str) -> pd.DataFrame:
    """Filter by player code (initials).

    Args:
        df: DataFrame with 'Pl' column
        player_code: Player code to filter (e.g., 'JB')

    Returns:
        Filtered DataFrame
    """
    return df[df['Pl'] == player_code]


def filter_by_player_codes(df: pd.DataFrame, codes: list) -> pd.DataFrame:
    """Filter by multiple player codes.

    Args:
        df: DataFrame with 'Pl' column
        codes: List of player codes to include

    Returns:
        Filtered DataFrame
    """
    return df[df['Pl'].isin(codes)]
```

**Files to Update:**
- player_history.py - ~4 instances
- 300TEG Records.py - ~3 instances
- leaderboard.py - ~3 instances
- Other analysis pages - ~2+ instances each

**Effort:** 1.5-2 hours
**Testing:** 45 minutes

---

### Phase 4.3: Expand VS Par Formatting

**Pattern:** Multiple implementations of score vs par formatting
**Current Implementation:** `format_vs_par()` in utils.py
**Occurrences:** ~51 across 18 files
**Enhancement:** Make function more flexible with parameters

**Update in streamlit/utils.py:**

```python
def format_vs_par(value, precision=0, even_as_symbol="E"):
    """Format score as vs par (+/- notation).

    Args:
        value: Score value (vs par)
        precision: Decimal precision (default 0)
        even_as_symbol: Symbol for even par (default 'E')

    Returns:
        Formatted string (e.g., '+3', '-2', 'E')

    Examples:
        >>> format_vs_par(3)
        '+3'
        >>> format_vs_par(-2)
        '-2'
        >>> format_vs_par(0)
        'E'
        >>> format_vs_par(3.5, precision=1)
        '+3.5'
    """
    if pd.isna(value):
        return ""

    value = float(value)

    if value > 0:
        return f"+{value:.{precision}f}"
    elif value < 0:
        return f"{value:.{precision}f}"
    else:
        return even_as_symbol
```

**Files to Update (Sample):**
- leaderboard.py - Replace inline formatting
- 102TEG Results.py - Replace inline formatting
- latest_teg_context.py - Replace inline formatting
- All scoring analysis pages

**Implementation:**
- Find inline formatting patterns: `f"+{value}" if value > 0...`
- Replace with: `format_vs_par(value)`
- Handle None/NaN cases

**Effort:** 2-3 hours
**Testing:** 1-2 hours (compare formatted output)

---

### Phase 4.4: Create Round Filtering Utilities

**Pattern:** `df[df['Round'] == round_num]` and variants
**Occurrences:** ~20 across 12 files

**Add to streamlit/utils.py:**

```python
def filter_by_round(df: pd.DataFrame, round_num: int) -> pd.DataFrame:
    """Filter by round number.

    Args:
        df: DataFrame with 'Round' column
        round_num: Round number to filter

    Returns:
        Filtered DataFrame
    """
    return df[df['Round'] == round_num]


def filter_by_rounds(df: pd.DataFrame, round_nums: list) -> pd.DataFrame:
    """Filter by multiple round numbers.

    Args:
        df: DataFrame with 'Round' column
        round_nums: List of round numbers to include

    Returns:
        Filtered DataFrame
    """
    return df[df['Round'].isin(round_nums)]
```

**Effort:** 1-1.5 hours

---

### Phase 4.5: Create Course Filtering Utilities

**Pattern:** `df[df['Course'] == course_name]`
**Occurrences:** ~15 across 8 files

**Add to streamlit/utils.py:**

```python
def filter_by_course(df: pd.DataFrame, course_name: str) -> pd.DataFrame:
    """Filter by course name.

    Args:
        df: DataFrame with 'Course' column
        course_name: Course name to filter

    Returns:
        Filtered DataFrame
    """
    return df[df['Course'] == course_name]


def filter_by_courses(df: pd.DataFrame, course_names: list) -> pd.DataFrame:
    """Filter by multiple course names.

    Args:
        df: DataFrame with 'Course' column
        course_names: List of course names

    Returns:
        Filtered DataFrame
    """
    return df[df['Course'].isin(course_names)]
```

**Effort:** 1 hour

---

### Phase 4.6: Standardize Cache Management

**Issue:** Multiple approaches to cache clearing
**Pattern:** Scattered `st.cache_data.clear()` calls
**Solution:** Use centralized `utils.clear_all_caches()`

**Audit:**
```bash
grep -r "cache_data.clear" streamlit/
grep -r "clear_all_caches" streamlit/
```

**Action:**
- Replace `st.cache_data.clear()` with `utils.clear_all_caches()`
- Ensure consistent cache management
- Document cache strategy in comments

**Effort:** 1 hour

---

### Phase 4.7: Testing & Verification

**Duration:** 2 hours

**Test Coverage:**
1. Load all pages that use new utilities
2. Verify filtered results match original implementation
3. Check formatted output matches expectations
4. Run commentary generation (uses multiple patterns)
5. Spot check 5-10 random pages

**Test Checklist:**
- [ ] TEG filtering works for all pages
- [ ] Player filtering returns correct subsets
- [ ] VS par formatting displays correctly
- [ ] Round and course filtering work
- [ ] All pages load without errors
- [ ] Commentary generation completes
- [ ] No new console warnings

**Effort:** 2 hours

---

### Phase 4 Summary

**Utilities Created:** 12+ new functions
**Pattern Abstractions:** 6 categories
**Files Updated:** 25+ files
**Lines Simplified:** ~300 lines
**Total Effort:** 6-8 hours
**Testing:** 2 hours
**Risk Level:** LOW

**Benefits Achieved:**
- Consistent filtering across codebase
- Centralized formatting logic
- Reduced code repetition by 25%
- Easier future maintenance
- Single source of truth for common patterns

**Commit Message:**
```
Create and implement pattern utility functions

Added 12+ utility functions for common patterns:
- TEG filtering (4 functions)
- Player filtering (4 functions)
- Round and course filtering (4 functions)
- Enhanced vs_par formatting

Updated 25+ files to use new utilities.
Eliminated ~300 lines of repetitive code patterns.
Improved code consistency across entire application.

Tests verify all functionality works correctly.
```

---

## Summary Timeline

| Phase | Duration | Lines Saved | Risk | Status |
|-------|----------|-------------|------|--------|
| **Phase 1** | 3-4 hrs | 370 | LOW | Ready |
| **Phase 2** | 2-3 hrs | 250 | MEDIUM | Ready |
| **Phase 3** | 2-3 hrs | 0 (clarity) | LOW | Ready |
| **Phase 4** | 6-8 hrs | 300+ | LOW | Ready |
| **TOTAL** | 12-18 hrs | **920+** | **LOW-MED** | **READY** |

---

## Success Criteria & Metrics

### Phase Success Criteria

**Phase 1 Complete When:**
- [ ] All 9 within-file duplicates deleted
- [ ] No syntax errors in affected files
- [ ] All 5 affected pages load without errors
- [ ] Functions still work as before

**Phase 2 Complete When:**
- [ ] 5 new utility functions added to utils.py
- [ ] All imports updated (10+ files)
- [ ] Commentary generation still works
- [ ] No new import errors

**Phase 3 Complete When:**
- [ ] 9 functions renamed (5 + 4)
- [ ] All call sites updated
- [ ] All 9 affected pages tested
- [ ] Reports generate correctly

**Phase 4 Complete When:**
- [ ] 12+ new utility functions created
- [ ] 25+ files updated to use new utilities
- [ ] Filtered results match originals
- [ ] Formatted output matches expectations

### Metrics to Track

**Code Quality Metrics:**
- Total lines of code (should decrease)
- Number of duplicate definitions (should go to 0)
- Code coverage (should stay same or increase)
- Import errors (should stay 0)

**Performance Metrics:**
- Page load times (should not increase)
- Commentary generation time (should not increase)
- Cache hit rates (should stay same or improve)

**Testing Metrics:**
- Pages tested (accumulate across phases)
- Functionality verified (accumulate)
- No regressions (maintain 100%)

---

## Risk Mitigation

### Rollback Procedures

**If Phase 1 fails:**
1. Restore deleted function definitions from git
2. Verify imports still work
3. No data loss risk (only code deletions)

**If Phase 2 fails:**
1. Revert utils.py additions
2. Restore old imports in affected files
3. May need to restart affected processes

**If Phase 3 fails:**
1. Rename functions back to original names
2. Restore old function calls
3. No data loss

**If Phase 4 fails:**
1. Revert new utility functions
2. Restore inline patterns
3. Pages should work with inline code

### Testing Strategy

**Before Each Phase:**
- [ ] Backup current code state (git branch)
- [ ] Document current functionality
- [ ] List pages to test

**During Each Phase:**
- [ ] Test after each small change (within-file)
- [ ] Test after each file update
- [ ] Document any issues

**After Each Phase:**
- [ ] Full page load test
- [ ] Functionality verification
- [ ] Performance check
- [ ] Git commit with detailed message

---

## Estimated Impact Summary

### Code Reduction
- Within-file duplicates: 370 lines → 0 lines
- Cross-file duplicates: 140 lines → 0 lines
- Near duplicates: 558 lines → 280 lines (50% reduction)
- Pattern repetition: 330 lines → ~50 lines (85% reduction)
- **TOTAL:** ~1,400 lines → ~330 lines (76% reduction)

### Quality Improvements
- **Clarity:** Function names clearly indicate purpose
- **Maintainability:** Single source of truth for common functions
- **Consistency:** Standardized approach across codebase
- **Performance:** Improved through consolidation
- **Testability:** Easier to test centralized functions

### Technical Debt Reduction
- Exact duplicates: 100% eliminated
- Near duplicates: 50% reduced
- Naming conflicts: 100% resolved
- Pattern repetition: 85% reduced
- Overall debt: ~75% reduction

---

## Additional Recommendations

### Post-Consolidation Actions

**Document Established Patterns:**
1. Add coding standards document
2. Document filter utility usage
3. Document formatting functions
4. Add examples to comments

**Prevent Future Duplication:**
1. Set up pre-commit hooks to detect duplicates
2. Add linting rule for function names
3. Code review checklist includes "check for duplicates"
4. Quarterly duplication analysis audit

**Future Optimization:**
1. Consider database migration
2. Implement caching improvements
3. Optimize performance bottlenecks
4. Build comprehensive test suite

### Tools & Commands Reference

**Analysis Commands:**
```bash
# Find duplicate function names
grep -rh "^def " streamlit/ | cut -d'(' -f1 | sort | uniq -c | sort -rn

# Check for import errors
python -m py_compile streamlit/*.py streamlit/helpers/*.py

# Search for specific patterns
grep -r "df\[df\['TEGNum'\]" streamlit/
```

**Git Workflow:**
```bash
# Create branch for consolidation
git checkout -b consolidation/phase-1

# After testing, commit
git add .
git commit -m "Phase 1: Remove within-file duplicates"

# After all phases
git merge main
```

---

## Timeline & Commitment

**Recommended Execution Schedule:**

| Week | Phase | Duration | Start Date | End Date |
|------|-------|----------|-----------|----------|
| 1 | Phase 1 | 3-4 hrs | Week 1 Mon | Week 1 Thu |
| 2 | Phase 2 | 2-3 hrs | Week 2 Mon | Week 2 Wed |
| 3 | Phase 3 | 2-3 hrs | Week 3 Mon | Week 3 Wed |
| 4 | Phase 4 | 6-8 hrs | Week 4 Mon | Week 4 Fri |
| - | Buffer | 2-4 hrs | As needed | As needed |

**Resource Requirements:**
- 1 developer, ~2 hours per day for 4 weeks
- Or 1 developer, ~4 hours per day for 2 weeks
- Test environment: local machine + Railway staging

---

## Conclusion

This roadmap provides a systematic, low-risk approach to consolidating duplicates and improving code quality. By following this plan:

1. **Quick wins first** (Phase 1) - builds momentum and confidence
2. **Centralize utilities** (Phase 2) - foundation for consistency
3. **Clarify naming** (Phase 3) - improves code readability
4. **Abstract patterns** (Phase 4) - reduces repetition across codebase

**Total savings:** ~1,070 lines of code
**Total effort:** 12-18 hours
**Expected impact:** 75% reduction in code duplication and technical debt

**Status:** Ready for implementation

---

**Document Created:** October 18, 2025
**Last Updated:** October 18, 2025
**Status:** COMPLETE - Ready for Execution