# Utils.py Inventory - Section 8B: Helper Functions - Metadata & CSS

**Section:** Helper Functions - Metadata & Styling
**Function Count:** 8 functions
**Lines in utils.py:** 3434-3622
**Estimated Complexity:** Simple to Medium

---

## Functions

### 1. `get_teg_metadata(teg_num, round_num=None) -> dict` (Lines 3448-3476)
Extracts metadata for TEG from round_info.csv.
- **Parameters:**
  - teg_num: Tournament number
  - round_num: Optional specific round
- **Returns:** dict with Area, Course, Date, Year
- **Features:** Returns empty dict if not found (safe)
- **Used By:** Scorecard generation, metadata displays

### 2. `format_date_for_scorecard(date_str, input_format=None, output_format='%d/%m/%y') -> str` (Lines 3478-3540)
**Flexible date formatting** supporting multiple UK date formats.
- **Features:**
  - Auto-detects input format (tries 9 formats)
  - Custom output formatting
  - Preserves UK conventions (no leading zeros)
  - Falls back to original if parsing fails
- **Used By:** Scorecard generation

### 3. `get_scorecard_data(teg_num=None, round_num=None, player_code=None) -> pd.DataFrame` (Lines 3542-3586)
Retrieves filtered data for scorecard generation.
- **Parameters:** All optional, enables various filter combinations
- **Returns:** Appropriately sorted DataFrame
- **Features:**
  - Smart sorting (adapts to filters)
  - Comprehensive filtering options
- **Used By:** Scorecard pages

### 4. `convert_trophy_name(name: str) -> str` (Lines 3600-3622)
**Converts between trophy name formats** bidirectionally.
- **Conversions:**
  - "trophy" ↔ "TEG Trophy"
  - "jacket" ↔ "Green Jacket"
  - "spoon" ↔ "HMM Wooden Spoon"
- **Features:**
  - Case insensitive
  - Raises ValueError for unknown names
- **Used By:** Trophy/award displays

### 5. `get_trophy_full_name(trophy: str) -> str` (Lines 3624-3643)
Gets full trophy name from short or long form.
- **Returns:** Full name regardless of input format
- **Features:** Safe wrapper around convert_trophy_name()

### 6. `load_course_info() -> pd.DataFrame` (Lines 3646-3650)
**Cached loader** for unique course/area combinations.
- **Returns:** DataFrame with [Course, Area] unique pairs
- **Caching:** @st.cache_data
- **Used By:** Course selection dropdowns

### 7. `get_teg_filter_options(all_data) -> list` (Lines 3653-3668)
Generates TEG filtering options for dropdowns.
- **Returns:** ["All TEGs", "TEG 16", "TEG 17", ...] in reverse chronological order
- **Features:** Includes "All TEGs" option first
- **Used By:** Dropdown selections

### 8. `filter_data_by_teg(all_data, selected_tegnum) -> pd.DataFrame` (Lines 3671-3690)
Filters data to selected TEG or returns all if "All TEGs" selected.
- **Parameters:**
  - all_data: Complete dataset
  - selected_tegnum: "All TEGs" or TEG number
- **Returns:** Filtered DataFrame
- **Used By:** Analysis page filtering

---

## Section Summary

**Statistics:**
- Total Functions: 8
- Total Lines: ~190 lines
- Type Breakdown: 4 PURE + 4 IO/MIXED
- Complexity: Mostly Simple

**Key Functions:**
- `format_date_for_scorecard()`: Flexible date handling
- `get_scorecard_data()`: Smart data filtering
- `convert_trophy_name()`: Trophy format conversions
- `get_teg_filter_options()`: Dropdown generation

**Design Patterns:**
- Safe error handling (returns empty/original on failure)
- Case-insensitive string matching
- Flexible parameter combinations

---

