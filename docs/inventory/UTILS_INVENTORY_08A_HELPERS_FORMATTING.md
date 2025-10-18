# Utils.py Inventory - Section 8A: Helper Functions - Formatting & Scoring

**Section:** Helper & Display Functions - Formatting
**Function Count:** 11 functions
**Lines in utils.py:** 3103-3351
**Estimated Complexity:** Simple to Medium

---

## Functions

### 1. `chosen_rd_context(ranked_rd_df, teg='TEG 16', rd=4, measure=None) -> pd.DataFrame` (Lines 3103-3129)
Formats round context data showing player rankings for specific round.
- **Returns:** DataFrame with [Player, Score, Pl rank, All-time rank]
- **Features:** Formats vs-par scores, calculates player count context
- **Used By:** Round leaderboard displays

### 2. `chosen_teg_context(ranked_teg_df, teg='TEG 15', measure=None) -> pd.DataFrame` (Lines 3131-3157)
Formats tournament context similarly to chosen_rd_context.
- **Returns:** DataFrame with tournament standings

### 3. `create_stat_section(title, value=None, df=None, divider=None) -> str` (Lines 3160-3241)
**Generates HTML for stat display sections** with title, optional value, and details from DataFrame.
- **Parameters:**
  - title: Section title
  - value: Optional primary value
  - df: Details DataFrame (each row formatted as HTML)
  - divider: Separator between elements (default space)
- **Output:** HTML string for Streamlit markdown display
- **Features:**
  - CSS classes for styling
  - Player names bolded
  - Multiple rows supported
- **Used By:** Commentary/stats displays

### 4. `define_score_types(gross_vp) -> dict` (Lines 3248-3263)
Defines score type counts from GrossVP series.
- **Returns:** dict with keys: 'Pars_or_Better', 'Birdies', 'Eagles', 'TBPs'
- **Type:** PURE | **Complexity:** Simple
- **Used By:** Score analysis functions

### 5. `apply_score_types(df, groupby_cols=['Player']) -> pd.DataFrame` (Lines 3265-3288)
Applies score type definitions to DataFrame grouped by columns.
- **Returns:** Aggregated counts by group
- **Features:** Expands dict results into separate columns
- **Used By:** Score type statistics

### 6. `score_type_stats(df=None) -> pd.DataFrame` (Lines 3290-3314)
**Comprehensive score statistics** including rates and frequency.
- **Calculates:**
  - Birdie/Eagle/TBP rates
  - Holes per birdie/eagle/TBP
  - Pars or better rate
- **Output Columns:** All percentage and frequency metrics
- **Used By:** Scoring analysis pages

### 7-8. `max_scoretype_per_round()` & `max_scoretype_per_teg()` (Lines 3316-3351)
Find maximum score type counts per player.
- **Returns:** Best scores of each type
- **Used By:** Personal best tracking

### 9-10. `load_css_file()` & CSS loading functions (Lines 3371-3402)
Load external CSS files for styling.
- **load_css_file():** Generic CSS loader with path resolution
- **load_datawrapper_css():** Specific table styling
- **load_teg_reports_css():** Report styling
- **Type:** IO | **Complexity:** Simple
- **Features:**
  - Fallback encoding (UTF-8 sig for BOM)
  - Error handling with st.error()

### 11. `datawrapper_table(df, left_align=None, css_classes=None, return_html=False) -> Union[None, str]` (Lines 3404-3432)
**Renders DataFrame as HTML table** with datawrapper styling.
- **Parameters:**
  - left_align: Force left alignment
  - css_classes: Additional CSS classes
  - return_html: Return string instead of rendering
- **Features:**
  - Configurable styling
  - Optional HTML return
  - Left/right alignment support
- **Used By:** All table displays

---

## Section Summary

**Statistics:**
- Total Functions: 11
- Total Lines: ~280 lines
- Type Breakdown: 4 PURE + 7 IO/MIXED
- Complexity: Mostly Simple, 2 Medium

**Key Functions:**
- `create_stat_section()`: HTML generation
- `score_type_stats()`: Comprehensive statistics
- `datawrapper_table()`: Table display

**Used By Extent:**
- Widely used across display pages
- Core formatting infrastructure

---

