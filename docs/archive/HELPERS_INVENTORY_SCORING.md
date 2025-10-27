# Helpers Inventory: Scoring Analysis Modules

**Category:** Scoring Analysis
**Total Modules:** 4
**Total LOC:** ~933 lines
**Streamlit Dependencies:** None
**Overall Status:** ✅ All Pure Functions

---

## Module: `helpers/scoring_data_processing.py`

**Lines of Code:** 180
**Purpose:** Provides core score formatting and aggregation functions for consistent display of vs-par values and scoring statistics across the application.
**Created/Refactored:** Well-documented with clear docstrings
**Status:** ✅ Well organized

### Module-Level Information

**Imports:**
- External: `pandas`, `numpy`
- Internal: None
- Streamlit: No

**Used By (pages):**
- `400scoring.py`
- `streaks.py`
- Various analysis pages

**Dependencies ON Other Helpers:**
- None (pure core functions)

---

### Functions in This Module

#### Function 1: `format_vs_par_value()`

**Line Numbers:** 13-30
**Type:** PURE

**Signature:**
```python
def format_vs_par_value(value: float) -> str:
    """Formats vs-par values for display."""
```

**Purpose:**
Formats numerical vs-par scores for consistent display (e.g., "+1.50", "-0.50", "=").

**Parameters:**
- `value` (float): The vs-par value to format

**Returns:**
- `str`: Formatted string with +/- signs and equals

**Dependencies:**
- None (pure formatting)

**Complexity:** Simple

**Migration Target:** `teg_analysis/analysis/scoring.py`
**Priority:** 🟢

**Notes:**
- Used throughout codebase for consistent formatting
- Consider consolidating with similar formatting functions from other modules

---

#### Function 2: `prepare_average_scores_by_par()`

**Line Numbers:** 33-65
**Type:** PURE

**Signature:**
```python
def prepare_average_scores_by_par(all_data: pd.DataFrame) -> pd.DataFrame:
    """Calculates and formats average scores by par value for each player."""
```

**Purpose:**
Aggregates hole-by-hole data to show average performance by par value (Par 3, 4, 5).

**Parameters:**
- `all_data` (pd.DataFrame): Complete hole-by-hole scoring data

**Returns:**
- `pd.DataFrame`: Formatted table with average scores by par, sorted by performance

**Dependencies:**
- Uses `format_vs_par_value()` from this module
- Pandas groupby, unstack operations

**Complexity:** Medium

**Migration Target:** `teg_analysis/analysis/scoring.py`
**Priority:** 🟢

**Notes:**
- Good candidate for caching in analysis layer
- Combines aggregation + formatting in one function

---

#### Function 3: `format_scoring_stats_columns()`

**Line Numbers:** 68-94
**Type:** PURE

**Signature:**
```python
def format_scoring_stats_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Formats columns in scoring statistics DataFrame for display."""
```

**Purpose:**
Standardizes number formatting and column names for scoring statistics tables, handling edge cases like infinite values.

**Parameters:**
- `df` (pd.DataFrame): Raw scoring statistics data

**Returns:**
- `pd.DataFrame`: Formatted DataFrame ready for display

**Dependencies:**
- Pandas dtype operations
- Numpy for infinity checking

**Complexity:** Simple

**Migration Target:** `teg_analysis/analysis/scoring.py`
**Priority:** 🟢

**Notes:**
- Handles special case: infinite values → "n/a"
- Used for consistency in display

---

#### Function 4: `calculate_multi_score_running_sum()`

**Line Numbers:** 99-146
**Type:** PURE

**Signature:**
```python
def calculate_multi_score_running_sum(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates running streaks for different score types."""
```

**Purpose:**
Tracks consecutive achievements (birdies, pars or better, triple bogeys) for streak analysis.

**Parameters:**
- `df` (pd.DataFrame): Hole-by-hole data with 'Career Count' for ordering

**Returns:**
- `pd.DataFrame`: Original data with added 'RunningSum' columns for each score type

**Dependencies:**
- Pandas groupby operations
- Uses GrossVP column for conditions

**Complexity:** Medium

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟢

**Notes:**
- Score type definitions (Pars_or_Better, Birdies, TBPs) are hardcoded
- Consider moving to `streak_analysis_processing.py` for consolidation
- Potential duplicate of functionality in `streak_analysis_processing.py`

---

#### Function 5: `summarize_multi_score_running_sum()`

**Line Numbers:** 149-181
**Type:** PURE

**Signature:**
```python
def summarize_multi_score_running_sum(df: pd.DataFrame) -> pd.DataFrame:
    """Summarizes maximum streak lengths for each player and score type."""
```

**Purpose:**
Creates final "Longest Streaks" table showing each player's best streaks by type.

**Parameters:**
- `df` (pd.DataFrame): Data with 'RunningSum' columns from `calculate_multi_score_running_sum()`

**Returns:**
- `pd.DataFrame`: Summary showing longest streak for each player and score type

**Dependencies:**
- Pandas groupby agg operations

**Complexity:** Simple

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🟢

**Notes:**
- Potential duplicate of functionality in `streak_analysis_processing.py`

---

### Module Analysis

**Summary:**
- Total Functions: 5
- Pure Functions: 5 (100% - easy migration)
- Mixed Functions: 0
- Streamlit-Dependent: 0

**Migration Plan:**
- Functions 1-3 → `teg_analysis/analysis/scoring.py`
- Functions 4-5 → Consolidate with `streak_analysis_processing.py` (avoid duplication)

**Duplicates Identified:**
- `calculate_multi_score_running_sum()` and `summarize_multi_score_running_sum()` - Similar to functions in `streak_analysis_processing.py`
- **Recommendation:** Keep in `scoring_data_processing.py` if used by different pages, or consolidate for DRY principle

---

## Module: `helpers/scoring_achievements_processing.py`

**Lines of Code:** 115
**Purpose:** Processes scoring achievement statistics (eagles, birdies, pars) and creates tabbed displays for different achievement types.
**Created/Refactored:** Well-documented
**Status:** ✅ Well organized

### Module-Level Information

**Imports:**
- External: `pandas`, `numpy`
- Internal: None
- Streamlit: No

**Used By (pages):**
- `400scoring.py` and related achievement pages

**Dependencies ON Other Helpers:**
- None

---

### Functions in This Module

#### Function 1: `get_scoring_achievement_fields()`

**Line Numbers:** 12-29
**Type:** PURE

**Signature:**
```python
def get_scoring_achievement_fields() -> list[list[str]]:
    """Defines score achievement fields for tabbed display."""
```

**Purpose:**
Centralizes definition of achievement categories for consistent use across pages.

**Parameters:** None

**Returns:**
- `list`: Field pairs [achievement_count, frequency_metric]

**Dependencies:** None

**Complexity:** Simple

**Migration Target:** `teg_analysis/analysis/achievements.py`
**Priority:** 🟢

---

#### Function 2: `create_achievement_tab_labels()`

**Line Numbers:** 32-45
**Type:** PURE

**Signature:**
```python
def create_achievement_tab_labels(chart_fields_all: list[list[str]]) -> list[str]:
    """Creates user-friendly tab labels from field names."""
```

**Purpose:**
Converts internal field names to display-ready tab labels.

**Parameters:**
- `chart_fields_all` (list): List of achievement field pairs

**Returns:**
- `list`: User-friendly tab labels

**Dependencies:** None

**Complexity:** Simple

**Migration Target:** `teg_analysis/analysis/achievements.py`
**Priority:** 🟢

---

#### Function 3: `format_achievement_dataframe_columns()`

**Line Numbers:** 48-74
**Type:** PURE

**Signature:**
```python
def format_achievement_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Formats achievement DataFrame for display."""
```

**Purpose:**
Standardizes formatting of achievement counts and ratios, handling infinite values.

**Parameters:**
- `df` (pd.DataFrame): Raw achievement data

**Returns:**
- `pd.DataFrame`: Formatted DataFrame

**Dependencies:**
- Pandas dtype operations
- Numpy for infinity checking

**Complexity:** Simple

**Migration Target:** `teg_analysis/analysis/achievements.py`
**Priority:** 🟢

---

#### Function 4: `prepare_achievement_table_data()`

**Line Numbers:** 77-100
**Type:** PURE

**Signature:**
```python
def prepare_achievement_table_data(scoring_stats: pd.DataFrame, chart_fields: list) -> pd.DataFrame:
    """Prepares achievement table data for specific score type."""
```

**Purpose:**
Extracts and formats achievement data for display in tabs.

**Parameters:**
- `scoring_stats` (pd.DataFrame): Complete scoring statistics
- `chart_fields` (list): Field pair for specific achievement type

**Returns:**
- `pd.DataFrame`: Formatted table ready for display

**Dependencies:**
- Uses `format_achievement_dataframe_columns()` from this module

**Complexity:** Simple

**Migration Target:** `teg_analysis/analysis/achievements.py`
**Priority:** 🟢

---

#### Function 5: `create_section_title()`

**Line Numbers:** 103-115
**Type:** PURE

**Signature:**
```python
def create_section_title(chart_fields: list) -> str:
    """Creates section title from field names."""
```

**Purpose:**
Converts internal field names to user-friendly titles.

**Parameters:**
- `chart_fields` (list): Field pair

**Returns:**
- `str`: Cleaned section title

**Dependencies:** None

**Complexity:** Simple

**Migration Target:** `teg_analysis/analysis/achievements.py`
**Priority:** 🟢

---

### Module Analysis

**Summary:**
- Total Functions: 5
- Pure Functions: 5 (100%)
- Mixed Functions: 0
- Streamlit-Dependent: 0

**Migration Plan:**
- All 5 functions → `teg_analysis/analysis/achievements.py`

**Duplicates Identified:**
- Title/label creation functions similar to other modules
- Consider consolidating formatting utilities across modules

---

## Module: `helpers/score_count_processing.py`

**Lines of Code:** 565
**Purpose:** Analyzes score distributions by player, creates percentage charts and ridgeline visualizations, and formats data for display.
**Created/Refactored:** Well-documented
**Status:** ⚠️ Mixed (data processing + Plotly UI)

### Module-Level Information

**Imports:**
- External: `pandas`, `numpy`, `plotly.express`, `plotly.graph_objects`, `plotly.subplots`
- Internal: None (uses `utils.format_vs_par()`)
- Streamlit: Yes (imports `streamlit as st`)

**Used By (pages):**
- `score_distribution.py`
- Other distribution analysis pages

**Dependencies ON Other Helpers:**
- None

---

### Functions in This Module (Key Selection)

#### Data Processing Functions (Migratable)

**1. `get_filtering_options()`** (lines 16-33) - PURE
- Returns TEG and par filter options
- **Migration Target:** Core filtering utility

**2. `apply_teg_and_par_filters()`** (lines 36-71) - PURE
- Applies filters to data with descriptive labels
- **Migration Target:** Core filtering utility

**3. `count_scores_by_player()`** (lines 74-98) - PURE
- Counts score distributions by player
- **Migration Target:** Core analysis function

**4. `convert_counts_to_percentages()`** (lines 207-227) - PURE
- Converts counts to percentage distributions
- **Migration Target:** Core analysis function

**5. `sort_players_by_average()`** (lines 349-381) - PURE
- Sorts players by average score
- **Migration Target:** Core analysis function

**6. `calculate_player_distributions()`** (lines 315-346) - PURE
- Prepares distribution data for analysis
- **Migration Target:** Core analysis function

---

#### Chart/Visualization Functions (Stay in Streamlit)

- `create_percentage_distribution_chart()` - Uses Plotly
- `create_stacked_bar_chart()` - Uses Plotly
- `create_ridgeline_distribution_chart()` - Complex Plotly visualization
- `prepare_score_count_display()` - Display formatting

---

### Module Analysis

**Summary:**
- Total Functions: 15+
- Pure Functions: ~8 (can migrate)
- Mixed Functions: ~7 (Plotly/UI - keep in streamlit/)
- Streamlit-Dependent: Yes

**Migration Plan:**
- Core functions 1-6 → `teg_analysis/analysis/scoring.py`
- Chart functions → Create `streamlit/visualizations/score_count_charts.py`
- Keep display functions in streamlit utilities

**Duplicates Identified:**
- Format functions similar to `scoring_data_processing.py`

---

## Module: `helpers/par_analysis_processing.py`

**Lines of Code:** 73
**Purpose:** Analyzes performance on different par values (Par 3, 4, 5) for scoring insights.
**Created/Refactored:** Well-documented
**Status:** ✅ Well organized

### Module-Level Information

**Imports:**
- External: `pandas`
- Internal: None
- Streamlit: No

**Used By (pages):**
- Par-specific analysis pages

**Dependencies ON Other Helpers:**
- None

---

### Functions in This Module

#### Function 1: `prepare_par_analysis_data()`

**Line Numbers:** ~30-73
**Type:** PURE

**Signature:**
```python
def prepare_par_analysis_data(all_data: pd.DataFrame) -> pd.DataFrame:
    """Prepares par-specific performance analysis."""
```

**Purpose:**
Aggregates performance metrics by par value (3, 4, 5).

**Parameters:**
- `all_data` (pd.DataFrame): Tournament data with PAR column

**Returns:**
- `pd.DataFrame`: Performance data grouped by par

**Dependencies:**
- Pandas groupby operations

**Complexity:** Simple

**Migration Target:** `teg_analysis/analysis/par.py`
**Priority:** 🟢

---

### Module Analysis

**Summary:**
- Total Functions: ~3-4
- Pure Functions: 100%
- Mixed Functions: 0
- Streamlit-Dependent: No

**Migration Plan:**
- All functions → `teg_analysis/analysis/par.py`

---

## Cross-Module Summary

### Total Scoring Analysis: 933 lines

| Module | LOC | Status | Migration Target |
|--------|-----|--------|------------------|
| scoring_data_processing.py | 180 | ✅ Pure | teg_analysis/analysis/scoring.py |
| scoring_achievements_processing.py | 115 | ✅ Pure | teg_analysis/analysis/achievements.py |
| score_count_processing.py | 565 | ⚠️ Mixed | Split: 60% core, 40% UI |
| par_analysis_processing.py | 73 | ✅ Pure | teg_analysis/analysis/par.py |

### Consolidation Opportunities

1. **Formatting Functions:** Consolidate vs-par, infinite-value, and column name formatting
2. **Streak Calculations:** Remove duplicates from `scoring_data_processing.py` vs `streak_analysis_processing.py`
3. **Achievement Fields:** Consider config file for field definitions

### Key Dependencies

- All modules depend on: `pandas`, `numpy`
- `score_count_processing.py` adds: `plotly`, `streamlit`
- No inter-helper dependencies (except via utils.py)

### Recommended Execution Order

1. Migrate `scoring_achievements_processing.py` (small, pure, isolated)
2. Migrate `par_analysis_processing.py` (small, pure, isolated)
3. Migrate scoring core functions from `scoring_data_processing.py`
4. Refactor & migrate `score_count_processing.py` (largest, most complex)

