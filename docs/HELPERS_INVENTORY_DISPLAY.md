# Helpers Inventory: Display & UI Modules

**Category:** Display Formatting & User Interface
**Total Modules:** 4
**Total LOC:** ~996 lines
**Streamlit Dependencies:** 1 module (UI-only)
**Overall Status:** ✅ Mostly Pure, 1 UI-Only

---

## Module: `helpers/display_helpers.py`

**Lines of Code:** 467
**Purpose:** Provides core display formatting and record preparation functions for the Records pages, handling value formatting, table consolidation, and display-ready data transformations.
**Created/Refactored:** Well-documented with clear patterns
**Status:** ✅ Well organized - Pure functions

### Module-Level Information

**Imports:**
- External: `pandas`
- Internal: Uses `utils.get_best()`, `utils.get_worst()`, `utils.PLAYER_DICT`
- Streamlit: No

**Used By (pages):**
- `300TEG Records.py`
- Record display pages
- Achievement display pages

**Dependencies ON Other Helpers:**
- Imports from `score_count_processing.py` (line 226)

---

### Constants

**MEASURE_TITLES** (lines 11-16)
```python
{
    'Sc': "Best Score",
    'GrossVP': "Best Gross",
    'NetVP': "Best Net",
    'Stableford': "Best Stableford"
}
```

Used consistently throughout module for measure name translation.

---

### Core Formatting Functions

#### Function 1: `format_record_value()`

**Line Numbers:** 21-35
**Type:** PURE

**Signature:**
```python
def format_record_value(value: float, measure: str) -> str:
```

**Purpose:**
Formats numeric record values based on measure type (vs-par with +/-, or absolute scores).

**Returns:**
- "+3" or "-2" for GrossVP/NetVP
- "85" for scores

**Complexity:** Simple

**Migration Target:** `teg_analysis/display/formatters.py`
**Priority:** 🟢

---

#### Function 2: `prepare_records_display()`

**Line Numbers:** 38-71
**Type:** PURE

**Purpose:**
Formats record data for display, selecting columns based on record type (TEG, Round, or 9-hole).

**Parameters:**
- `best_records` (pd.DataFrame): Raw record data
- `record_type` (str): 'teg', 'round', or 'frontback'

**Returns:**
- `pd.DataFrame`: Formatted with appropriate columns

**Complexity:** Simple

**Migration Target:** `teg_analysis/display/formatters.py`
**Priority:** 🟢

---

### Record Table Functions

#### Function 3: `prepare_records_table()`

**Line Numbers:** 74-151
**Type:** PURE

**Purpose:**
Creates consolidated records table showing all measures for a record type, handling tied records with proper formatting.

**Key Features:**
- Shows all measures (Best Gross, Best Net, Best Stableford)
- Handles multiple tied record holders
- Formats "When" field based on record type (TEG, location, date)

**Complexity:** Medium

**Migration Target:** `teg_analysis/display/formatters.py`
**Priority:** 🟢

---

#### Function 4: `prepare_worst_records_table()`

**Line Numbers:** 385-467
**Type:** PURE

**Purpose:**
Inverse of above - shows worst records with appropriate measure titles.

**Key Difference:**
- For Stableford: lower is worse (uses `nsmallest`)
- For others: higher is worse (uses `nlargest`)

**Complexity:** Medium

**Migration Target:** `teg_analysis/display/formatters.py`
**Priority:** 🟢

---

### Streak Record Functions

#### Function 5: `prepare_streak_records_table()`

**Line Numbers:** 154-207
**Type:** PURE

**Purpose:**
Formats streak records for display, consolidating 3+ holders into summary rows.

**Key Features:**
- Groups streak records
- Shows tied records with player initials
- Formats "When" field with location info

**Complexity:** Medium

**Migration Target:** `teg_analysis/display/formatters.py`
**Priority:** 🟢

---

### Score Count Record Functions

#### Function 6: `prepare_score_count_records_table()`

**Line Numbers:** 210-382
**Type:** MIXED - Calls `count_scores_by_player()` helper

**Purpose:**
Finds and formats all-time records for score counts (most eagles, birdies, TBPs, etc.) at TEG and Round levels.

**Key Algorithm:**
1. Define score categories (Eagles, Birdies, Pars, TBPs)
2. For each TEG/Round combination, count scores in each category
3. Track records and consolidated rows for 3+ holders
4. Format for display

**Complexity:** High

**Dependencies:**
- Imports `count_scores_by_player` from `score_count_processing.py`

**Migration Target:** `teg_analysis/display/formatters.py`
**Priority:** 🟢

---

### Module Analysis

**Summary:**
- Total Functions: 6 major functions
- Pure Functions: 5
- Mixed Functions: 1 (calls helper from score_count_processing)
- Streamlit-Dependent: No

**Migration Plan:**
- All functions → `teg_analysis/display/formatters.py`

**Key Characteristics:**
- Highly reusable formatting functions
- Clear separation of concerns
- Consistent patterns for tied records
- No Streamlit dependencies

**Risk:** LOW | **Effort:** LOW | **Complexity:** MEDIUM

---

## Module: `helpers/latest_round_processing.py`

**Lines of Code:** 309
**Purpose:** Manages UI state for round and TEG selection, providing defaults, callbacks, and context data for display pages.
**Created/Refactored:** Well-documented
**Status:** ✅ UI-Only (Must Stay in Streamlit)

### Module-Level Information

**Imports:**
- External: `pandas`
- Internal: `streamlit as st`
- Streamlit: Yes (imports `st`, uses session state)

**Used By (pages):**
- `latest_round.py`
- `latest_teg_context.py`
- Any pages with round/TEG selection

**Dependencies ON Other Helpers:**
- Imports from `utils.py` for fast TEG status functions

---

### Round Selection Functions

#### Function 1: `get_round_metric_mappings()`

**Line Numbers:** 13-30
**Type:** PURE - Configuration

**Purpose:**
Maps user-friendly metric names to internal column names.

**Returns:**
```python
({
    'Gross vs Par': 'GrossVP',
    'Score': 'Sc',
    'Net vs Par': 'NetVP',
    'Stableford': 'Stableford'
}, inverse_mapping)
```

**Migration Target:** Could move to `teg_analysis/config/` or stay in `streamlit/`
**Priority:** 🟡

---

#### Function 2: `initialize_round_selection_state()`

**Line Numbers:** 33-42
**Type:** STREAMLIT ONLY

**Purpose:**
Initializes session state variables for round selection UI.

**Must Stay In:** `streamlit/helpers/`

---

#### Function 3: `get_latest_round_defaults()`

**Line Numbers:** 45-80
**Type:** MIXED

**Purpose:**
Determines latest round for default selection, using fast status file check or fallback.

**Migration Target:** Core logic could move to `teg_analysis/`, UI parts stay in Streamlit
**Priority:** 🟡

---

#### Function 4: `update_session_state_defaults()`

**Line Numbers:** 83-97
**Type:** STREAMLIT ONLY

**Purpose:**
Sets session state to latest round if not already initialized.

**Must Stay In:** `streamlit/helpers/`

---

#### Function 5: `create_round_selection_reset_function()`

**Line Numbers:** 100-119
**Type:** STREAMLIT ONLY

**Purpose:**
Creates callback function for "Latest Round" button.

**Must Stay In:** `streamlit/helpers/`

---

#### Function 6: `get_teg_and_round_options()`

**Line Numbers:** 122-141
**Type:** PURE DATA

**Purpose:**
Gets available TEG and round options for dropdowns.

**Migration Target:** Could move to analysis layer
**Priority:** 🟡

---

#### Function 7: `create_metric_tabs_data()`

**Line Numbers:** 144-161
**Type:** PURE

**Purpose:**
Prepares metric data for tabbed display.

**Migration Target:** Could move to analysis layer
**Priority:** 🟢

---

#### Function 8: `prepare_round_context_display()`

**Line Numbers:** 164-188
**Type:** PURE DATA

**Purpose:**
Prepares round context data for display in metric tabs.

**Migration Target:** `teg_analysis/analysis/`
**Priority:** 🟢

---

### TEG Selection Functions

#### Function 9-14: TEG Versions of Round Functions

**Lines:** 191-309

Similar to round functions but for TEG-level selection:
- `initialize_teg_selection_state()` - STREAMLIT ONLY
- `get_latest_teg_default()` - MIXED
- `update_teg_session_state_defaults()` - STREAMLIT ONLY
- `create_teg_selection_reset_function()` - STREAMLIT ONLY
- `get_teg_options()` - PURE DATA
- `prepare_teg_context_display()` - PURE DATA

**Must Stay In:** `streamlit/helpers/` for session state functions

---

### Module Analysis

**Summary:**
- Total Functions: 14
- Pure Functions: 4 (data/configuration only)
- Mixed Functions: 2 (with fallback logic)
- Streamlit-Dependent: 8 (session state management)

**Migration Plan:**
- Pure/mixed functions (4-6) → `teg_analysis/analysis/`
- Session state functions → MUST STAY in `streamlit/helpers/latest_round_processing.py`

**Key Characteristics:**
- Highly Streamlit-dependent (session state)
- Cannot be fully migrated to analysis layer
- Some pure data functions could be extracted

**Risk:** MEDIUM | **Effort:** MEDIUM | **Complexity:** MEDIUM

**Recommendation:**
Keep this module in `streamlit/helpers/` as-is. It's the one module designed specifically for Streamlit UI management. Any pure functions can be extracted if needed, but the core module should stay.

---

## Module: `helpers/scorecard_data_processing.py`

**Lines of Code:** 155
**Purpose:** Prepares hole-by-hole scorecard data for display in scorecard pages and views.
**Created/Refactored:** Well-documented
**Status:** ✅ Pure functions

### Module-Level Information

**Imports:**
- External: `pandas`
- Internal: None
- Streamlit: No

**Used By (pages):**
- `scorecard_v2.py`
- Scorecard display pages

**Dependencies ON Other Helpers:**
- None

---

### Core Functions

#### Function 1: `prepare_scorecard_data()`

**Line Numbers:** ~30-80
**Type:** PURE

**Purpose:**
Filters and formats hole-by-hole data for scorecard display.

**Key Features:**
- Selects relevant columns for scorecard
- Sorts by player and hole order
- Formats values for display

**Migration Target:** `teg_analysis/display/scorecard.py`
**Priority:** 🟢

---

#### Function 2: `format_scorecard_row()`

**Line Numbers:** ~85-120
**Type:** PURE

**Purpose:**
Formats individual scorecard rows with consistent value display.

**Migration Target:** `teg_analysis/display/scorecard.py`
**Priority:** 🟢

---

#### Function 3: `calculate_scorecard_totals()`

**Line Numbers:** ~125-155
**Type:** PURE

**Purpose:**
Calculates round totals and statistics for scorecard footer.

**Migration Target:** `teg_analysis/display/scorecard.py`
**Priority:** 🟢

---

### Module Analysis

**Summary:**
- Total Functions: 3-4
- Pure Functions: 100%
- Mixed Functions: 0
- Streamlit-Dependent: No

**Migration Plan:**
- All functions → `teg_analysis/display/scorecard.py`

**Risk:** LOW | **Effort:** LOW | **Complexity:** LOW

---

## Module: `helpers/records_css.py`

**Lines of Code:** 65
**Purpose:** Contains CSS styling definitions for records page display.
**Created/Refactored:** Simple CSS constants
**Status:** ✅ Pure CSS/Styling

### Module-Level Information

**Imports:**
- None (or minimal)
- Streamlit: Possibly (for st.markdown with unsafe_allow_html)

**Used By (pages):**
- `300TEG Records.py`
- Record display pages

---

### Content

This module contains CSS styling rules for:
- Record table formatting
- Color schemes for records
- Responsive layout styles
- Typography

**Example:**
```python
RECORD_TABLE_STYLE = """
<style>
...CSS rules...
</style>
"""
```

### Module Analysis

**Summary:**
- Pure CSS/Styling content
- Static definitions
- Used with `st.markdown(css_string, unsafe_allow_html=True)`

**Migration Plan:**
- Move to `streamlit/assets/css/records.css`
- Update imports to load from CSS file
- Consider CSS bundling strategy

**Risk:** LOW | **Effort:** LOW | **Complexity:** NONE

---

## Cross-Module Summary

### Total Display: 996 lines

| Module | LOC | Status | Type | Migration Target |
|--------|-----|--------|------|------------------|
| display_helpers.py | 467 | ✅ Pure | Formatting | teg_analysis/display/formatters.py |
| latest_round_processing.py | 309 | ✅ UI-Only | Streamlit | Stay in streamlit/helpers/ |
| scorecard_data_processing.py | 155 | ✅ Pure | Formatting | teg_analysis/display/scorecard.py |
| records_css.py | 65 | ✅ Pure | Styling | streamlit/assets/css/ |

### Key Insights

1. **Pure Display Functions:** Most modules are pure data formatters
2. **One UI-Only Module:** `latest_round_processing.py` is specifically for Streamlit session management
3. **CSS Consolidation:** CSS should move to assets directory
4. **Clear Separation:** Display logic is well-separated from analysis logic

### Recommended Migration Order

1. **Immediate:**
   - `scorecard_data_processing.py` (small, pure)
   - `display_helpers.py` (medium, pure)

2. **Quick Win:**
   - Move `records_css.py` to `streamlit/assets/css/`

3. **Leave As-Is:**
   - `latest_round_processing.py` (keep in streamlit/helpers/)

### Total Effort: LOW | Total Risk: VERY LOW

All display modules except `latest_round_processing.py` are excellent migration candidates. The latter is specifically designed for Streamlit and should remain in the streamlit package.

