# Helpers Inventory: Analysis & Performance Modules

**Category:** Performance Analysis
**Total Modules:** 5
**Total LOC:** ~3,168 lines
**Streamlit Dependencies:** None
**Overall Status:** ✅ All Pure Functions

---

## Module: `helpers/streak_analysis_processing.py`

**Lines of Code:** 1,145
**Purpose:** Core streak calculation engine tracking consecutive achievements/failures across player careers and within specific windows (TEG/Round).
**Created/Refactored:** Comprehensive with multiple functions for different streak types
**Status:** ✅ Well organized but LARGE (consider splitting)

### Module-Level Information

**Imports:**
- External: `pandas`, `numpy`
- Internal: None
- Streamlit: No

**Used By (pages):**
- `streaks.py`
- `latest_round.py`
- Performance analysis pages

**Dependencies ON Other Helpers:**
- Imports from `utils.py` for data loading

---

### Core Functions (Score Type Definitions)

#### Function 1: `get_score_type_definitions()`

**Line Numbers:** 12-30
**Type:** PURE - Configuration

**Purpose:**
Centralizes score type definitions for consistent streak calculations across the module.

**Returns:**
```python
{
    'Pars_or_Better': lambda x: x <= 0,
    'Birdies': lambda x: x == -1,
    'TBPs': lambda x: x > 2,
    'Bogey or better': lambda x: x < 2,
    'Double Bogey or worse': lambda x: x >= 2
}
```

**Priority:** 🟢

---

#### Function 2: `get_inverse_score_type_definitions()`

**Line Numbers:** 33-51
**Type:** PURE - Configuration

**Purpose:**
Defines inverse conditions for "no eagles", "no birdies", etc. streaks.

**Priority:** 🟢

---

### Streak Calculation Functions

#### Function 3: `calculate_multi_score_running_sum()`

**Line Numbers:** 54-98
**Type:** PURE

**Purpose:**
Calculates running streak counts for multiple score types across all players, tracking consecutive achievements.

**Key Algorithm:**
1. Sort by player + Career Count
2. For each player, iterate through holes
3. Increment streak when condition met, reset when not
4. Merge results back to original dataframe

**Complexity:** Medium-High

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟢

---

#### Function 4: `calculate_inverse_multi_score_running_sum()`

**Line Numbers:** 101-145
**Type:** PURE

**Purpose:**
Inverse of above - tracks consecutive holes WITHOUT achievements (no birdies, no TBPs).

**Complexity:** Medium-High

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟢

---

#### Function 5: `summarize_multi_score_running_sum()`

**Line Numbers:** 148-181
**Type:** PURE

**Purpose:**
Summarizes maximum streak lengths for each player and score type.

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟢

---

#### Function 6: `summarize_inverse_multi_score_running_sum()`

**Line Numbers:** 184-217
**Type:** PURE

**Purpose:**
Inverse summary - max streaks for each "without" score type.

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟢

---

### Workflow Functions

#### Function 7: `prepare_streak_data_for_display()`

**Line Numbers:** 220-240
**Type:** PURE

**Purpose:**
Complete workflow combining calculation + summarization for display-ready output.

**Usage Pattern:**
```python
data_with_streaks = calculate_multi_score_running_sum(all_data)
streak_summary = summarize_multi_score_running_sum(data_with_streaks)
```

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟢

---

#### Function 8: `prepare_inverse_streak_data_for_display()`

**Line Numbers:** 243-263
**Type:** PURE

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟢

---

### Cached Data Functions

#### Function 9: `prepare_good_streaks_data()`

**Line Numbers:** 266-321
**Type:** MIXED - Try/catch with fallback

**Purpose:**
Uses cached streak data with asterisk marking for current streaks matching max streaks.

**Features:**
- Uses `STREAKS_PARQUET` cache for performance
- Falls back to calculation if cache unavailable
- Marks active streaks with asterisks

**Dependencies:**
- `read_file()` from utils
- Helper functions: `get_player_mapping()`, `get_max_streaks()`, `get_current_streaks()`

**Complexity:** Medium

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟡 (depends on cache availability)

---

#### Function 10: `prepare_bad_streaks_data()`

**Line Numbers:** 324-380
**Type:** MIXED

**Purpose:**
Cached negative streaks with asterisk marking for current status.

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟡

---

#### Function 11: `get_current_streaks_data()`

**Line Numbers:** 383-419
**Type:** PURE

**Purpose:**
Calculates current (ongoing) streaks for all players and score types.

**Returns:**
- DataFrame with current streak values at most recent hole

**Complexity:** Medium

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟢

---

#### Function 12: `prepare_current_good_streaks_data()`

**Line Numbers:** 422-473
**Type:** MIXED

**Purpose:**
Current positive streaks from cache with asterisk marking.

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟡

---

#### Function 13: `prepare_current_bad_streaks_data()`

**Line Numbers:** 476-528
**Type:** MIXED

**Purpose:**
Current negative streaks from cache with asterisk marking.

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟡

---

### Cached Streak Helpers

#### Function 14-20: Cached Data Helper Functions

**Lines:** 531-756

Functions for working with `STREAKS_PARQUET` cached data:

- `build_streaks()` (535-600) - Creates streak flags and counters from raw data
- `get_max_streaks()` (602-609) - Returns max streaks for each player
- `get_current_streaks()` (611-615) - Returns latest streaks per player
- `get_player_mapping()` (618-620) - Player ID to name mapping
- `transform_cached_good_streaks()` (623-671) - Format good streaks with asterisks
- `get_current_equals_max_streaks()` (674-704) - Identify active record streaks
- `transform_cached_bad_streaks()` (707-756) - Format bad streaks with asterisks

**All PURE - High Quality Code**

**Priority:** 🟢

---

### Window Streak Functions

#### Function 21-27: TEG/Round Window Streak Analysis

**Lines:** 759-1002

Functions for analyzing streaks within specific windows:

- `adjust_opening_streak()` (761-802) - Adjust for pre-existing streaks at window start
- `find_streak_location()` (805-841) - Find exact holes where max streak occurred
- `format_hole_location()` (844-865) - Convert HoleID format
- `calculate_window_streaks()` (868-945) - Calculate streaks for a specific window
- `get_player_window_streaks()` (948-1001) - Quick lookup for TEG/Round window
- `prepare_record_best_streaks_data()` (1004-1073) - Find record good streaks
- `prepare_record_worst_streaks_data()` (1076-1145) - Find record bad streaks

**All PURE - Complex but well-organized**

**Priority:** 🟢

---

### Module Analysis

**Summary:**
- Total Functions: 27+
- Pure Functions: ~24 (90%)
- Mixed Functions: ~3 (try/catch with fallback)
- Streamlit-Dependent: No

**Migration Plan:**
- All functions → `teg_analysis/analysis/streaks.py` (OR split into 2-3 files if too large)
- Consider: `streaks_core.py`, `streaks_window.py`, `streaks_cache.py`

**Key Characteristics:**
- Highly cohesive (all about streaks)
- Well-documented
- Consistent code quality
- Good separation of concerns (calculation vs. display)
- Can be ported as-is with minimal refactoring

**Risk:** LOW | **Effort:** MEDIUM | **Complexity:** MEDIUM-HIGH

---

## Module: `helpers/records_identification.py`

**Lines of Code:** 627
**Purpose:** Identifies and ranks all-time records (best/worst) at TEG, round, and 9-hole levels across multiple scoring measures.
**Created/Refactored:** Well-structured
**Status:** ✅ Well organized

### Module-Level Information

**Imports:**
- External: `pandas`
- Internal: None
- Streamlit: No

**Used By (pages):**
- `300TEG Records.py`
- Records analysis pages

**Dependencies ON Other Helpers:**
- None

---

### Core Functions

#### Function 1: `rank_records_by_measure()`

**Line Numbers:** ~50-150
**Type:** PURE

**Purpose:**
Ranks all records within a category (TEG, Round, 9-hole) by score measure.

**Key Algorithm:**
- Groups data by category
- Ranks by score (best/worst)
- Handles ties appropriately

**Migration Target:** `teg_analysis/analysis/records.py`
**Priority:** 🟢

---

#### Function 2-5: Record Preparation Functions

**Type:** PURE

**Purpose:**
Format record data for display at different levels:
- `prepare_teg_records()`
- `prepare_round_records()`
- `prepare_frontback_records()`
- `prepare_individual_hole_records()`

**Migration Target:** `teg_analysis/analysis/records.py`
**Priority:** 🟢

---

### Module Analysis

**Summary:**
- Total Functions: 8-10
- Pure Functions: 100%
- Mixed Functions: 0
- Streamlit-Dependent: No

**Migration Plan:**
- All functions → `teg_analysis/analysis/records.py`

**Key Characteristics:**
- Clean, modular design
- No external dependencies beyond pandas
- Highly reusable
- Can be ported as-is

**Risk:** LOW | **Effort:** LOW | **Complexity:** MEDIUM

---

## Module: `helpers/best_performance_processing.py`

**Lines of Code:** 633
**Purpose:** Processes and ranks best performing TEGs and rounds for display, with measure-specific sorting and formatting.
**Created/Refactored:** Well-documented
**Status:** ✅ Well organized

### Module-Level Information

**Imports:**
- External: `pandas`
- Internal: None
- Streamlit: No

**Used By (pages):**
- `301Best_TEGs_and_Rounds.py`
- Performance ranking pages

**Dependencies ON Other Helpers:**
- None

---

### Core Functions

#### Function 1: `get_measure_name_mappings()`

**Line Numbers:** ~11-32
**Type:** PURE - Configuration

**Purpose:**
Maps display names (Gross, Score, Net, Stableford) to internal column names.

**Migration Target:** `teg_analysis/analysis/performance.py`
**Priority:** 🟢

---

#### Function 2-5: Table Preparation Functions

**Type:** PURE

**Purpose:**
Format and sort performance data:
- `prepare_best_teg_table()`
- `prepare_best_round_table()`
- `prepare_best_frontback_table()`
- `prepare_comparison_tables()`

**Key Algorithm:**
- Rank by selected measure
- Sort appropriately (ascending/descending based on measure)
- Format for display

**Migration Target:** `teg_analysis/analysis/performance.py`
**Priority:** 🟢

---

### Module Analysis

**Summary:**
- Total Functions: 6-8
- Pure Functions: 100%
- Mixed Functions: 0
- Streamlit-Dependent: No

**Migration Plan:**
- All functions → `teg_analysis/analysis/performance.py`

**Risk:** LOW | **Effort:** LOW | **Complexity:** MEDIUM

---

## Module: `helpers/worst_performance_processing.py`

**Lines of Code:** 175
**Purpose:** Analyzes and ranks worst performing TEGs, rounds, and 9-holes across scoring measures.
**Created/Refactored:** Well-documented
**Status:** ✅ Well organized

### Module-Level Information

**Imports:**
- External: `pandas`
- Internal: None
- Streamlit: No

**Used By (pages):**
- Worst performance analysis pages

**Dependencies ON Other Helpers:**
- None

---

### Core Functions

#### Function 1-4: Worst Performance Functions

**Type:** PURE

**Purpose:**
Format and rank worst performances:
- `prepare_worst_teg_table()`
- `prepare_worst_round_table()`
- `prepare_worst_frontback_table()`

**Key Difference from Best:**
- For GrossVP/NetVP/Sc: Higher values are worse
- For Stableford: Lower values are worse
- Sorting logic adjusted accordingly

**Migration Target:** `teg_analysis/analysis/performance.py`
**Priority:** 🟢

---

### Module Analysis

**Summary:**
- Total Functions: 4-5
- Pure Functions: 100%
- Mixed Functions: 0
- Streamlit-Dependent: No

**Migration Plan:**
- All functions → Consolidate with `best_performance_processing.py` into `teg_analysis/analysis/performance.py`

**Risk:** LOW | **Effort:** LOW | **Complexity:** LOW

---

## Module: `helpers/comeback_analysis.py`

**Lines of Code:** 436
**Purpose:** Analyzes comeback patterns where players improved scores after rounds/holes above their average.
**Created/Refactored:** Well-documented
**Status:** ✅ Well organized

### Module-Level Information

**Imports:**
- External: `pandas`, `numpy`
- Internal: None
- Streamlit: No

**Used By (pages):**
- `comebacks.py`
- Performance pattern analysis pages

**Dependencies ON Other Helpers:**
- None

---

### Core Functions

#### Function 1: `calculate_player_averages()`

**Line Numbers:** ~30-50
**Type:** PURE

**Purpose:**
Calculate rolling/historical averages for each player.

**Migration Target:** `teg_analysis/analysis/comeback.py`
**Priority:** 🟢

---

#### Function 2: `identify_below_average_holes()`

**Line Numbers:** ~55-80
**Type:** PURE

**Purpose:**
Identify holes scored above player average.

**Migration Target:** `teg_analysis/analysis/comeback.py`
**Priority:** 🟢

---

#### Function 3: `identify_comeback_sequences()`

**Line Numbers:** ~85-150
**Type:** PURE

**Purpose:**
Find sequences where player improved after poor performance.

**Algorithm:**
- Identify runs of below-average holes
- Check for improvement after
- Calculate improvement magnitude

**Complexity:** Medium

**Migration Target:** `teg_analysis/analysis/comeback.py`
**Priority:** 🟢

---

#### Function 4-6: Analysis Functions

**Type:** PURE

**Purpose:**
Various comeback analysis functions for display

**Migration Target:** `teg_analysis/analysis/comeback.py`
**Priority:** 🟢

---

### Module Analysis

**Summary:**
- Total Functions: 6-8
- Pure Functions: 100%
- Mixed Functions: 0
- Streamlit-Dependent: No

**Migration Plan:**
- All functions → `teg_analysis/analysis/comeback.py`

**Risk:** LOW | **Effort:** LOW | **Complexity:** MEDIUM

---

## Cross-Module Summary

### Total Analysis: 3,168 lines

| Module | LOC | Status | Complexity | Migration Target |
|--------|-----|--------|------------|------------------|
| streak_analysis_processing.py | 1,145 | ✅ Pure | High | teg_analysis/analysis/streaks.py |
| records_identification.py | 627 | ✅ Pure | Medium | teg_analysis/analysis/records.py |
| best_performance_processing.py | 633 | ✅ Pure | Medium | teg_analysis/analysis/performance.py |
| worst_performance_processing.py | 175 | ✅ Pure | Low | teg_analysis/analysis/performance.py |
| comeback_analysis.py | 436 | ✅ Pure | Medium | teg_analysis/analysis/comeback.py |

### Key Insights

1. **All Pure Functions** - Zero Streamlit dependencies
2. **High Cohesion** - Each module focuses on specific analysis type
3. **Low Inter-Dependencies** - Minimal coupling between modules
4. **Good Consolidation Opportunities:**
   - `best_performance_processing.py` + `worst_performance_processing.py` → single `performance.py`
   - Consider: `analysis/` package with subdirectories for large modules

### Recommended Migration Order

1. **Phase 1 (Immediate):**
   - `worst_performance_processing.py` (small, simple)
   - `comeback_analysis.py` (medium, isolated)

2. **Phase 2 (Quick wins):**
   - `records_identification.py` (large but simple)
   - `best_performance_processing.py` (large but simple)

3. **Phase 3 (Complex):**
   - `streak_analysis_processing.py` (largest, most complex - may need splitting)

### Total Effort: LOW | Total Risk: VERY LOW

All analysis modules are excellent migration candidates with minimal refactoring needed.

