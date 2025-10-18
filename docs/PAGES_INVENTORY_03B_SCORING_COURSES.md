# Streamlit Pages Inventory - Section 3B: Scoring Analysis (Course-Focused)

**Section:** Course-Based Scoring & Comparisons
**Pages:** 5
**Total Lines:** ~1,055
**Refactoring Status:** ✅ 80% (4/5 refactored, 1 partially)

---

## Contents Overview

This section documents 5 user-facing pages focusing on course-level scoring analysis including course performance records, round databases, score matrices, and hole difficulty visualization.

| Page | File | Lines | Status | Complexity |
|------|------|-------|--------|-----------|
| Course Averages & Records | ave_by_course.py | 249 | 🚧 | Medium |
| All Rounds Database | score_by_course.py | 130 | ⏳ | Simple |
| Score Matrix | score_matrix.py | 170 | ✅ | Simple |
| Changes vs Previous | biggest_changes.py | 106 | 🚧 | Simple |
| Heatmap (WIP) | score_heatmaps.py | 369 | ⏳ | Complex |

---

## Page: `ave_by_course.py`

**Title:** Course Averages and Records (Course Performance)
**Lines of Code:** 249
**Refactoring Status:** 🚧 Partially Refactored
**Complexity:** Medium

### Purpose

Comprehensive course analysis showing gross and net records, player averages, best performances, and worst performances by course. Includes optional area filtering (e.g., "Local", "Out of State", etc.) to group courses by region. Users visit to understand course-specific performance and course difficulty comparisons.

### Data Loading

- **Functions:**
  - `get_round_data()` - Gets round-level data
  - `load_course_info()` - Gets course metadata
- **Files:** round_info.csv, course_info.csv
- **Key Parameters:**
  - `ex_50=True` - Excludes practice TEG 50
  - `ex_incomplete=False` - Includes current tournament
- **Caching:** Yes (get_round_data cached)

### Dependencies

**From utils.py:**
- `get_round_data(ex_50=True, ex_incomplete=False)` - Round data
- `load_course_info()` - Course metadata
- `load_datawrapper_css()` - Table styling
- `datawrapper_table()` - Table formatter

**From helpers/course_analysis_processing.py:**
- `prepare_area_filter_options()` - Available areas for filtering
- `filter_data_by_area()` - Applies area filter
- `calculate_course_round_counts()` - Counts rounds per course
- `create_course_performance_table()` - Performance data
- `create_course_summary_table()` - Summary statistics

**Streamlit Components:**
- `st.selectbox()` - Area filter selector
- `st.tabs()` - 6 tabs (Gross Records, Net Records, Summary, Averages, Bests, Worsts)
- `st.divider()` - Visual dividers
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:**
1. `create_course_records_table()` (lines 79-110)
   - Finds best gross scores per course
   - Purpose: Extract course records
   - Extraction candidate: YES - Move to course_analysis_processing

2. `create_net_course_records_table()` (lines 113-143)
   - Finds best net scores per course
   - Purpose: Extract net course records
   - Extraction candidate: YES - Move to course_analysis_processing

3. `create_course_records_summary()` (lines 146-172)
   - Counts records per player
   - Purpose: Summary statistics
   - Extraction candidate: YES - Move to course_analysis_processing

4. `create_net_course_records_summary()` (lines 175-201)
   - Counts net records per player
   - Purpose: Net summary statistics
   - Extraction candidate: YES - Move to course_analysis_processing

**Analysis:**
- Total embedded logic: ~130 lines
- Business logic: 60% (record calculation)
- UI orchestration: 40%
- Extraction recommendation: Extract all 4 functions to course_analysis_processing.py

### User Interactions

**Widgets:**
- Selectbox: Filter by area (optional, includes "All Areas")
- Tabs: 6 tabs for different views
- Tab contents: Gross Records | Net Records | Summary | Averages | Bests | Worsts
- All filters apply to all tab data

**Session State:** None

### Display Components

**Charts:** None

**Tables:**
- Course records tables (gross and net)
- Summary tables (records per player)
- Average performance tables
- Best/worst performance tables

**Layout:**
- Area selector
- Tab-based view
- Multiple tables per tab

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Applied globally
- `st.divider()` - Visual separators

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Extract create_course_records_table() to course_analysis_processing.py - 1 hour
2. Extract create_net_course_records_table() to course_analysis_processing.py - 1 hour
3. Extract create_course_records_summary() to course_analysis_processing.py - 1 hour
4. Extract create_net_course_records_summary() to course_analysis_processing.py - 1 hour
5. Update imports and verify functionality - 1 hour
6. Test all 6 tabs after extraction - 2 hours

**Estimated Effort:** 6-7 hours (including testing)

**Blockers:** None

### Page-Specific Notes

- Has significant embedded logic (4 functions, ~130 lines)
- High-priority refactoring target
- Well-structured despite embedding
- Good test coverage opportunity
- Functions are well-contained and extractable

---

## Page: `score_by_course.py`

**Title:** All Rounds (Searchable Round Database)
**Lines of Code:** 130
**Refactoring Status:** ⏳ Not Refactored (Functional Template Candidate)
**Complexity:** Simple

### Purpose

Searchable database of all rounds played at any course with filtering options for player, course, and area. Shows personal best (PB) ranking for each round. Users visit to browse round history and find specific rounds or courses.

### Data Loading

- **Functions:**
  - `get_ranked_round_data()` - Gets ranked round data
  - `load_course_info()` - Gets course metadata
- **Files:** Ranked round data, course_info.csv
- **Key Parameters:** None
- **Caching:** Yes (get_ranked_round_data cached)

### Dependencies

**From utils.py:**
- `get_ranked_round_data()` - Ranked round data
- `load_datawrapper_css()` - Table styling
- `load_course_info()` - Course metadata

**From helpers/course_analysis_processing.py:**
- `prepare_area_filter_options()` - Area filtering options
- `filter_data_by_area()` - Applies area filter

**Streamlit Components:**
- `st.expander()` - Filters expander
- `st.selectbox()` - Area, Course, Player filters
- `st.number_input()` - N rounds to show
- `st.radio()` - Scoring measure selector
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:** None

**Analysis:** No embedded logic, all inline processing is simple data filtering.

### User Interactions

**Widgets:**
- Expander: Show/hide filters section
- Selectbox: Filter by area (optional)
- Selectbox: Filter by course (optional)
- Selectbox: Filter by player (optional)
- Number input: N rounds to display (1-100+)
- Radio: Scoring measure (Gross, Net, etc.)
- Filters apply dynamically to table

**Session State:** None

### Display Components

**Charts:** None

**Tables:**
- Searchable/filterable round database table
- Columns: Player, Course, TEG, Round, Score, PB Rank

**Layout:**
- Collapsed filters section
- Results table

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Applied globally

### Migration Analysis

**Complexity:** Simple

**Migration Tasks:**
1. Apply refactoring template structure - 1-2 hours
2. Clean up inline filtering logic - 0.5 hour
3. Add docstrings - 0.5 hour
4. Test filtering combinations - 1 hour

**Estimated Effort:** 2-3 hours (optional template adoption)

**Blockers:** None

### Page-Specific Notes

- Functional but not following standard refactoring template
- Good candidate for template adoption
- Could benefit from code organization
- No technical debt, just style/organization
- Simple filtering logic could be extracted to helper

---

## Page: `score_matrix.py`

**Title:** Score Matrix (Pivot Table View)
**Lines of Code:** 170
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Simple

### Purpose

Pivot table view of scores showing players as columns and TEGs/Rounds/9s as rows with selected score type aggregations (average, count, etc.). Allows viewing data from multiple perspectives with segmented control selectors. Users visit to compare scores across dimensions (players vs time periods).

### Data Loading

- **Functions:**
  - `load_all_data(exclude_incomplete_tegs=False)` - Tournament data
- **Files:** all-scores.parquet
- **Key Parameters:** `exclude_incomplete_tegs=False` - Includes current tournament
- **Caching:** Yes (load_all_data cached)

### Dependencies

**From utils.py:**
- `load_all_data(exclude_incomplete_tegs=False)` - Tournament data
- `load_datawrapper_css()` - Table styling

**Streamlit Components:**
- `st.segmented_control()` - Aggregation level selector (TEG/Round/9)
- `st.segmented_control()` - Score type selector (Average, Count, etc.)
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:**
1. `format_player_value()` (lines 129-139)
   - Formats individual player scores in cells
   - Purpose: Apply cell formatting (decimal places, styling)
   - Extraction candidate: Move to display_helpers

2. `format_average_value()` (lines 141-151)
   - Formats average column in cells
   - Purpose: Apply special formatting to average
   - Extraction candidate: Move to display_helpers

**Analysis:**
- Total embedded logic: ~25 lines
- Business logic: 30% (formatting logic)
- UI orchestration: 70%
- Extraction recommendation: Extract formatting functions to display_helpers

### User Interactions

**Widgets:**
- Segmented control: Aggregation level (TEG | Round | 9-Hole)
- Segmented control: Score type (Average | Count | Min | Max | etc.)
- Updates table dynamically based on selections

**Session State:** None

### Display Components

**Charts:** None

**Tables:**
- Pivot table: Players as columns, time periods as rows
- Cell values: Selected aggregation (average, count, etc.)
- Dynamic based on segmented control selections

**Layout:**
- Segmented controls at top
- Large pivot table

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Applied globally

### Migration Analysis

**Complexity:** Simple

**Migration Tasks:**
1. Extract format_player_value() to display_helpers.py - 1 hour
2. Extract format_average_value() to display_helpers.py - 1 hour
3. Update imports - 0.5 hour
4. Test formatting after extraction - 1 hour

**Estimated Effort:** 2-3 hours (low-priority formatting extraction)

**Blockers:** None

### Page-Specific Notes

- Clean implementation with minor formatting logic
- Low-priority refactoring (formatting only)
- Works well for multi-dimensional viewing
- No technical debt

---

## Page: `biggest_changes.py`

**Title:** Changes vs Previous Round (Round-to-Round Volatility)
**Lines of Code:** 106
**Refactoring Status:** 🚧 Partially Refactored
**Complexity:** Simple

### Purpose

Shows rounds with biggest score swings compared to player's previous round with options to include/exclude TEG boundaries (i.e., whether R1→R2 change across TEGs counts as volatility). Displays both improvements and declines. Users visit to find volatile performances or identify consistency patterns.

### Data Loading

- **Functions:**
  - `get_round_data()` - Gets round data
- **Files:** round_info.csv
- **Key Parameters:**
  - `ex_50=True` - Excludes practice TEG
  - `ex_incomplete=False` - Includes current tournament
- **Caching:** Yes (get_round_data cached)

### Dependencies

**From utils.py:**
- `get_round_data(ex_50=True, ex_incomplete=False)` - Round data
- `load_datawrapper_css()` - Table styling
- `datawrapper_table()` - Table formatter

**Streamlit Components:**
- `st.selectbox()` - TEG filter
- `st.columns()` - Layout organization
- `st.radio()` - Options selector (Include/Exclude TEG boundaries)
- `st.radio()` - View type selector (Top N vs All)
- `st.tabs()` - 2 tabs (Improvements vs Worsenings)
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:** None (all logic is inline)

**Analysis:**
- Total embedded logic: ~40 lines
- Business logic: 80% (score diff calculations, groupby)
- UI orchestration: 20%
- Extraction recommendation: Extract score diff calculation to helper

### User Interactions

**Widgets:**
- Selectbox: Filter by TEG (optional)
- Radio: Include/Exclude TEG boundaries option
- Radio: View mode (Top N vs All rounds)
- Tabs: Improvements | Worsenings
- All filters apply to both tabs

**Session State:** None

### Display Components

**Charts:** None

**Tables:**
- Score change tables (Improvements tab)
- Score decline tables (Worsenings tab)
- Columns: Player, Previous Round, Current Round, Change

**Layout:**
- Filter and option controls
- Tab-based view

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Applied globally

### Migration Analysis

**Complexity:** Simple

**Migration Tasks:**
1. Extract score diff calculation to helpers - 1-2 hours
2. Remove commented-out duplicate code (lines 84-130) - 0.5 hour
3. Apply refactoring template - 1 hour
4. Test filtering logic - 1 hour

**Estimated Effort:** 3-4 hours (including code cleanup)

**Blockers:** None

### Page-Specific Notes

- Has commented-out duplicate code block at bottom (lines 84-130) that should be removed
- Good candidate for helper extraction
- Working implementation despite minor issues
- Code cleanup opportunity

---

## Page: `score_heatmaps.py`

**Title:** Heatmap Visualization (WIP - In Progress)
**Lines of Code:** 369
**Refactoring Status:** ⏳ Not Refactored (WIP Status)
**Complexity:** Complex

### Purpose

Interactive heatmap and line chart visualization of hole difficulty showing average GrossVP by hole, stroke index (SI), or par with extensive filtering and customization options. Marked as WIP (Work In Progress) indicating incomplete implementation. Users would visit to visually identify which holes are most difficult across the course.

### Data Loading

- **Functions:**
  - `load_all_data()` - Tournament data
- **Files:** all-scores.parquet
- **Key Parameters:** None
- **Caching:** Yes (load_all_data cached)

### Dependencies

**From utils.py:**
- `load_all_data()` - Tournament data
- `get_page_layout()` - Layout configuration

**External Libraries:**
- `altair` - Chart visualization library
- `pandas` - Data manipulation
- `numpy` - Numeric operations

**Streamlit Components:**
- `st.expander()` - Filter expander sections
- `st.multiselect()` - Multi-select filters
- `st.checkbox()` - Boolean filter options
- `st.segmented_control()` - X-axis selector
- `st.selectbox()` - Advanced options
- `st.number_input()` - Numeric parameters
- `st.altair_chart()` - Chart display
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:**
1. `load_data()` (lines 30-62)
   - Cached data loader with type conversions
   - Purpose: Load and prepare data for charting
   - Type: Data preparation
   - Extraction candidate: YES - Move to helper

2. `make_row_label()` (lines 162-175)
   - Creates row labels for heatmap grouping
   - Purpose: Format row identifiers
   - Extraction candidate: YES - Move to helper

3. `pretty_sel()` (lines 249-252)
   - Formats filter selections for display
   - Purpose: Display-friendly filter summary
   - Extraction candidate: YES - Move to display_helpers

**Analysis:**
- Total embedded logic: ~150 lines
- Business logic: 50% (data prep, calculations)
- UI orchestration: 50%
- Extraction recommendation: Extract all 3 functions + create heatmap helper module

### User Interactions

**Widgets:**
- Extensive filter controls:
  - Multiselects for filtering (players, holes, etc.)
  - Checkboxes for row selection options
  - Segmented control for X-axis grouping
  - Selectbox for advanced options
  - Number input for parameters
- Dynamic chart based on all selections

**Session State:** None (Altair handles state internally)

### Display Components

**Charts:**
- Altair heatmap visualization (primary)
- Altair line chart (secondary)
- Interactive legend and tooltips

**Tables:** None

**Layout:**
- Filter expanders at top
- Two charts below

### CSS/Styling

- Altair built-in styling
- Custom Altair theme configuration (embedded)

### Migration Analysis

**Complexity:** Complex

**Migration Tasks:**
1. Complete WIP implementation - 4-6 hours (main work)
2. Extract load_data() to helpers - 1 hour
3. Extract make_row_label() to helpers - 0.5 hour
4. Extract pretty_sel() to display_helpers - 0.5 hour
5. Create heatmap_processing.py helper module - 2 hours
6. Apply refactoring template - 1 hour
7. Comprehensive testing - 3-4 hours

**Estimated Effort:** 12-15 hours (major refactoring + completion work)

**Blockers:**
- WIP status - implementation incomplete
- Needs functional completion before refactoring
- Extensive charting logic needs validation

### Page-Specific Notes

- Marked as WIP (Work In Progress)
- Highest complexity page in this section
- Extensive inline configuration and data prep
- Good candidate for helper extraction after completion
- Would benefit from Altair theme extraction (similar to ave_by_teg.py)
- Needs significant refactoring before production use

---

## Section Summary

### Refactoring Status
- ✅ 1 page fully refactored (score_matrix.py)
- 🚧 2 pages partially refactored (ave_by_course.py, biggest_changes.py)
- ⏳ 2 pages not refactored (score_by_course.py, score_heatmaps.py - WIP)

### High-Priority Refactoring Tasks

1. **ave_by_course.py** - Extract 4 embedded functions
   - Effort: 6-7 hours (including testing)
   - Impact: Remove 130 lines of embedded logic

2. **score_heatmaps.py** - Complete WIP + refactor
   - Effort: 12-15 hours (completion + refactoring)
   - Impact: Unblocks missing visualization feature

3. **biggest_changes.py** - Remove commented code + extract logic
   - Effort: 3-4 hours (including cleanup)
   - Impact: ~50 lines of commented code removal

### Medium-Priority Tasks

1. **score_by_course.py** - Apply refactoring template
   - Effort: 2-3 hours (just organization)
   - Impact: Consistency with other pages

2. **score_matrix.py** - Extract formatting functions
   - Effort: 2-3 hours
   - Impact: Reusable formatting helpers

### Common Dependencies
- All use `load_datawrapper_css()`
- Most use `get_round_data()` or `load_all_data()`
- ave_by_course and score_by_course use course_analysis_processing.py

### Shared Helper Opportunities
1. **Course Analysis Module** - ave_by_course, score_by_course
2. **Display Formatting** - score_matrix, biggest_changes
3. **Altair Charting** - score_heatmaps, ave_by_teg

### Testing Priorities
1. **ave_by_course.py**: Verify all 6 tabs after extraction
2. **score_heatmaps.py**: Test chart interactivity (when completed)
3. **score_by_course.py**: Test filter combinations
4. All: CSS styling on different screen sizes

### Total Effort to Refactor This Section
- Complete refactoring: 26-34 hours (significant work)
  - ave_by_course: 6-7 hours
  - score_heatmaps: 12-15 hours (completion + refactoring)
  - biggest_changes: 3-4 hours
  - score_by_course: 2-3 hours
  - score_matrix: 2-3 hours
- Testing & documentation: 4-6 hours
- **Total: 30-40 hours (substantial refactoring needed)**

### Notes
- This section has more refactoring work than others
- score_heatmaps.py is the biggest blocker (WIP status)
- ave_by_course.py has most embedded logic
- Other pages are in better shape
- Refactoring here will significantly improve code quality
