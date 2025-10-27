# Streamlit Pages Inventory - Section 3A: Scoring Analysis (Player-Focused)

**Section:** Scoring Analysis & Distributions
**Pages:** 5
**Total Lines:** ~635
**Refactoring Status:** ✅ 100% (5/5 refactored)

---

## Contents Overview

This section documents 5 user-facing pages focusing on player-level scoring analysis including achievements, streaks, performance distributions, and trends over time.

| Page | File | Lines | Status | Complexity |
|------|------|-------|--------|-----------|
| Eagles/Birdies/Pars | birdies_etc.py | 129 | ✅ | Simple |
| Streaks | streaks.py | 237 | ✅ | Medium |
| Average by Par | ave_by_par.py | 79 | ✅ | Simple |
| Average by TEG | ave_by_teg.py | 182 | 🚧 | Medium |
| Scoring Distributions | sc_count.py | 208 | ✅ | Medium |

---

## Page: `birdies_etc.py`

**Title:** Eagles / Birdies / Pars (Scoring Achievements)
**Lines of Code:** 129
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Simple

### Purpose

Career achievement statistics for various score types showing eagles, birdies, pars, and triple bogeys. Displays career totals (aggregate count), most in a round (best single round performance), and most in a TEG (best single tournament performance). Users visit to explore scoring achievement patterns and compare players' strengths.

### Data Loading

- **Functions:**
  - `score_type_stats()` - Career statistics by score type
  - `max_scoretype_per_round()` - Best round per score type
  - `max_scoretype_per_teg()` - Best TEG per score type
- **Files:** Derived from all-scores.parquet via helpers
- **Key Parameters:** None
- **Caching:** Yes (all functions cached)

### Dependencies

**From utils.py:**
- `score_type_stats()` - Cached career stats loader
- `max_scoretype_per_round()` - Cached round max loader
- `max_scoretype_per_teg()` - Cached TEG max loader
- `load_datawrapper_css()` - Table styling

**From helpers/scoring_achievements_processing.py:**
- `get_scoring_achievement_fields()` - Gets list of score types (eagles, birdies, etc.)
- `create_achievement_tab_labels()` - Creates tab labels
- `prepare_achievement_table_data()` - Formats tables for display
- `create_section_title()` - Generates section headers

**Streamlit Components:**
- `st.tabs()` - 3 tabs (Career Totals, Most in Round, Most in TEG)
- `st.segmented_control()` - Score type selector (Eagles/Birdies/Pars/Triple Bogeys)
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:** None

**Analysis:** All business logic successfully extracted to helpers. Page is pure orchestration.

### User Interactions

**Widgets:**
- Segmented control: Score type selector (Eagles | Birdies | Pars | Triple Bogeys)
- Tabs: 3 tabs for different aggregation levels
- Segmented control drives which data is shown across all tabs

**Session State:** None (simple controls, segmented control handles state internally)

### Display Components

**Charts:** None

**Tables:**
- Career Totals table (players with aggregate counts)
- Most in Round table (best single round performances)
- Most in TEG table (best single tournament performances)
- Dynamic based on selected score type

**Layout:**
- Score type selector at top
- Tab-based view of three aggregation levels

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Applied globally

### Migration Analysis

**Complexity:** Simple

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Consider adding export functionality - future feature

**Estimated Effort:** 0 hours (no changes recommended)

**Blockers:** None

### Page-Specific Notes

- Clean implementation with all logic extracted
- Good model for score type filtering
- No technical debt identified
- Segmented control pattern works well for score type selection

---

## Page: `streaks.py`

**Title:** Streaks (Good & Bad Streak Analysis)
**Lines of Code:** 237
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Comprehensive streak analysis showing maximum and current streaks by player, all-time record streaks, and detailed exploration with TEG/Round/Player filtering. Covers both positive streaks (good scores) and negative streaks (bad scores). Users visit to analyze scoring consistency patterns and find streaks of similar performance.

### Data Loading

- **Functions:**
  - `load_all_data(exclude_teg_50=True)` - Tournament data
  - `read_file(STREAKS_PARQUET)` - Pre-calculated streaks data
- **Files:** all-scores.parquet, streaks.parquet (pre-calculated)
- **Key Parameters:** `exclude_teg_50=True` - Excludes practice TEG
- **Caching:** Yes (both cached)

### Dependencies

**From utils.py:**
- `load_datawrapper_css()` - Table styling
- `load_all_data(exclude_teg_50=True)` - Tournament data
- `read_file()` - File loader
- `STREAKS_PARQUET` - Path constant

**From helpers/streak_analysis_processing.py:**
- `prepare_good_streaks_data()` - Good streak formatting
- `prepare_bad_streaks_data()` - Bad streak formatting
- `prepare_current_good_streaks_data()` - Current streaks (good)
- `prepare_current_bad_streaks_data()` - Current streaks (bad)
- `calculate_window_streaks()` - Window-based streak analysis
- `prepare_record_best_streaks_data()` - All-time best streaks
- `prepare_record_worst_streaks_data()` - All-time worst streaks

**Streamlit Components:**
- `st.tabs()` - 3 main tabs (By Player, Record Streaks, Streak Detail)
- `st.segmented_control()` - Good/Bad toggle, Max/Current toggle
- `st.selectbox()` - TEG, Round, Player filters
- `st.spinner()` - Loading indicator

### Embedded Logic

**Functions Defined:**
1. `get_all_streak_tables()` (lines 38-58)
   - Cached calculation of all streak tables
   - Purpose: Pre-calculate all variations for performance
   - Type: Caching wrapper, not extraction candidate

**Analysis:**
- Total embedded logic: ~20 lines (caching wrapper only)
- Business logic: 0% (all in helpers)
- Extraction recommendation: Keep as is (caching optimization)

### User Interactions

**Widgets:**
- Tab 1: By Player
  - Segmented controls: Good/Bad selector, Max/Current selector
  - Table displays selected view
- Tab 2: Record Streaks
  - Shows all-time record streaks
  - No interactive elements
- Tab 3: Streak Detail
  - Selectbox: Filter by TEG (optional)
  - Selectbox: Filter by Round (optional)
  - Selectbox: Filter by Player (optional)
  - Applies multiple filters to detailed streaks

**Session State:** None (all controls independent)

### Display Components

**Charts:** None

**Tables:**
- Streak summary tables (By Player tab)
- Record streak tables (Record Streaks tab)
- Detailed filterable streaks (Streak Detail tab)

**Layout:**
- Tab-based organization
- Filters in third tab for detailed exploration

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Applied globally

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Consider visualizing streaks with charts - future feature
3. Add docstrings to streak_analysis helper functions - 1 hour

**Estimated Effort:** 0.5-1 hour (optional improvements)

**Blockers:** None

### Page-Specific Notes

- Well-structured with good helper usage
- Pre-calculated streaks.parquet enables fast loading
- Complex filtering in "Streak Detail" tab works well
- No technical debt identified
- Caching optimization (get_all_streak_tables) shows good performance thinking

---

## Page: `ave_by_par.py`

**Title:** Average by Par (Par Performance)
**Lines of Code:** 79
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Simple

### Purpose

Average performance matrix showing each player's average score on Par 3, Par 4, and Par 5 holes with optional TEG filtering. Helps identify which hole types each player struggles with or excels at. Users visit to understand hole-type performance patterns.

### Data Loading

- **Functions:**
  - `load_all_data(exclude_incomplete_tegs=False)` - Tournament data
  - `get_teg_filter_options()` - Available TEGs for filtering
  - `filter_data_by_teg()` - Applies TEG filter
- **Files:** all-scores.parquet
- **Key Parameters:** `exclude_incomplete_tegs=False` - Includes current tournament
- **Caching:** Yes (load_all_data cached)

### Dependencies

**From utils.py:**
- `load_all_data(exclude_incomplete_tegs=False)` - Tournament data (includes current)
- `load_datawrapper_css()` - Table styling
- `get_teg_filter_options()` - TEG list for selector
- `filter_data_by_teg()` - Filters data by TEG

**From helpers/par_analysis_processing.py:**
- `calculate_par_performance_matrix()` - Calculates averages by par
- `format_par_performance_table()` - Formats output table

**Streamlit Components:**
- `st.selectbox()` - TEG filter selector (optional, includes "All TEGs")
- `st.markdown()` - Display title

### Embedded Logic

**Functions Defined:** None

**Analysis:** All business logic extracted to helpers. Page is pure orchestration.

### User Interactions

**Widgets:**
- Selectbox: Filter by TEG (optional, "All" option available)
- Updates table dynamically when TEG changes

**Session State:** None

### Display Components

**Charts:** None

**Tables:**
- Single performance matrix table
- Players as rows, Par 3/4/5 as columns
- Cells show average score for that par type

**Layout:**
- Title
- TEG selector
- Performance matrix table

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Applied globally

### Migration Analysis

**Complexity:** Simple

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. No changes recommended

**Estimated Effort:** 0 hours

**Blockers:** None

### Page-Specific Notes

- Excellent clean implementation
- Simple but insightful analysis
- Good model for optional filtering pattern
- No technical debt

---

## Page: `ave_by_teg.py`

**Title:** Average by TEG (Performance Trends)
**Lines of Code:** 182
**Refactoring Status:** 🚧 Partially Refactored
**Complexity:** Medium

### Purpose

Player performance trends over time displayed as interactive Altair line chart showing each player's Gross vs Par progression across all TEGs. Expandable data table shows underlying numbers. Users visit to see performance trending and identify improving/declining players.

### Data Loading

- **Functions:**
  - `load_all_data()` - Tournament data
- **Files:** all-scores.parquet
- **Key Parameters:** None
- **Caching:** Yes (load_all_data cached)

### Dependencies

**From utils.py:**
- `load_all_data()` - Tournament data
- `load_datawrapper_css()` - Table styling

**External Libraries:**
- `altair` - Chart library
- `pandas` - Data manipulation
- `numpy` - Numeric operations

**Streamlit Components:**
- `st.expander()` - Data table expander
- `st.altair_chart()` - Chart display
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:**
1. `altair_theme()` (lines 36-61)
   - Altair chart theming configuration
   - Purpose: Configure chart colors, fonts, sizing
   - Type: Chart configuration
   - Extraction candidate: YES - Move to styles/altair_theme.py

**Analysis:**
- Total embedded logic: ~25 lines (chart config)
- Theme configuration: 100% of embedded logic
- Extraction recommendation: Extract theme to shared styles module

### User Interactions

**Widgets:**
- Expander: Expand to see data table
- Chart legend interaction: Click players to toggle series

**Session State:** None (Altair handles state internally)

### Display Components

**Charts:**
- Altair interactive line chart
- X-axis: TEG number
- Y-axis: Gross vs Par
- One line per player (color-coded)
- Interactive legend: Click to show/hide player

**Tables:**
- Underlying data table in expander
- Not formatted with special CSS

**Layout:**
- Title and description
- Interactive chart
- Expander with data table

### CSS/Styling

- `load_datawrapper_css()` - Applied (though not used for line chart)
- Altair built-in styling

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Extract altair_theme() to styles/altair_theme.py - 1.5 hours
2. Create shared theme configuration file - 1 hour
3. Update import paths - 0.5 hours
4. Test chart styling after extraction - 1 hour

**Estimated Effort:** 3-4 hours (refactoring task)

**Blockers:** None

### Page-Specific Notes

- Good implementation but has embedded theme config
- Theme extraction is medium-priority refactoring task
- Would enable theme reuse in other Altair charts
- Currently well-structured aside from theme embedding
- Chart interaction works well

---

## Page: `sc_count.py`

**Title:** Scoring Distributions (Score Frequency Analysis)
**Lines of Code:** 208
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Score distribution analysis showing frequency counts and percentages of each score type (eagles, birdies, pars, bogeys, etc.) by player and by TEG with optional par filtering. Includes percentage distribution bar chart and ridgeline distribution visualization. Users visit to understand scoring patterns and consistency.

### Data Loading

- **Functions:**
  - `load_all_data(exclude_incomplete_tegs=False)` - Tournament data
  - `get_filtering_options()` - Available filter options
- **Files:** all-scores.parquet
- **Key Parameters:** `exclude_incomplete_tegs=False` - Includes current tournament
- **Caching:** Yes (load_all_data cached)

### Dependencies

**From utils.py:**
- `load_all_data(exclude_incomplete_tegs=False)` - Tournament data
- `load_datawrapper_css()` - Table styling
- `datawrapper_table()` - Table formatter

**From helpers/score_count_processing.py:**
- `get_filtering_options()` - Available filter values
- `apply_teg_and_par_filters()` - Applies filters
- `count_scores_by_player()` - Counts by player
- `create_percentage_distribution_chart()` - Percentage chart
- `prepare_score_count_display()` - Formats display
- `prepare_chart_data_with_special_handling()` - Chart data prep
- `convert_counts_to_percentages()` - Percentage conversion
- `create_stacked_bar_chart()` - Bar chart creation
- `format_percentage_for_display()` - Formatting
- `calculate_player_distributions()` - Distribution calculation
- `create_ridgeline_distribution_chart()` - Ridgeline chart
- Other formatting and utility functions

**Streamlit Components:**
- `st.segmented_control()` - Score type selector
- `st.selectbox()` - Player, TEG, Par selectors
- `st.radio()` - View type (Count vs Percentage)
- `st.tabs()` - 2 tabs (By Player, By TEG)
- `st.plotly_chart()` - Chart display
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:** None

**Analysis:** All business logic successfully extracted to helpers. Page is pure orchestration.

### User Interactions

**Widgets:**
- Segmented control: Score type (Eagles, Birdies, Pars, etc.)
- Selectbox: Player filter (optional)
- Selectbox: TEG filter (optional)
- Selectbox: Par filter (Par 3/4/5 or All)
- Radio: View type (Count vs Percentage)
- Tabs: By Player | By TEG
- All filters apply to displayed views

**Session State:** None (controls independent)

### Display Components

**Charts:**
- Percentage distribution bar chart (stacked or grouped)
- Ridgeline distribution chart (by player)
- Interactive Plotly charts with hover

**Tables:**
- Score count/percentage tables

**Layout:**
- Filter controls at top
- Tabs for different views
- Charts and tables in each tab

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Applied globally
- Plotly built-in styling for charts

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Consider adding export functionality - future feature
3. Add docstrings to score_count_processing functions - 1 hour

**Estimated Effort:** 0.5-1 hour (optional improvements)

**Blockers:** None

### Page-Specific Notes

- Excellent helper usage with 10+ functions
- Complex filtering with multiple dimensions
- Chart generation well-encapsulated
- No technical debt identified
- Good model for multi-dimensional analysis

---

## Section Summary

### Refactoring Status
- ✅ 4 pages fully refactored (birdies_etc, streaks, ave_by_par, sc_count)
- 🚧 1 page partially refactored (ave_by_teg - embedded theme config)

### Extraction Opportunities
1. **High Priority:** ave_by_teg.py - Extract altair_theme() to styles module - 3-4 hours
2. **Low Priority:** Add docstrings to helper functions - 2-3 hours

### Common Patterns
1. **Segmented Control for Score Type** - Used by birdies_etc and sc_count
   - Could be templated as reusable component

2. **Tab-based View Organization** - Used by streaks and sc_count
   - Standard pattern for multiple perspectives

3. **Optional Filtering** - Used by ave_by_par and sc_count
   - Works well for conditional analysis

### Common Dependencies
- All use `load_datawrapper_css()`
- Most use helpers/scoring_achievements_processing.py or streak_analysis_processing.py
- All use load_all_data() with varying exclude parameters

### Testing Priorities
1. **ave_by_teg.py**: Test chart interactivity before/after theme extraction
2. **sc_count.py**: Verify filter combinations work correctly
3. **streaks.py**: Test "Streak Detail" tab filtering logic
4. All: CSS styling on different screen sizes

### Total Effort to Refactor This Section
- Complete refactoring of ave_by_teg.py: 3-4 hours
- Documentation improvements: 2-3 hours
- Testing: 2-3 hours
- **Total: 7-10 hours (mostly optional improvements)**

### Notes
- This section is in good shape overall
- Main work is extracting embedded Altair theme from ave_by_teg.py
- Most pages are clean with good helper usage
- No critical technical debt, only quality improvements possible
