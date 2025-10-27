# Streamlit Pages Inventory - Section 4: Latest TEG (Current Tournament)

**Section:** Latest Tournament & Context
**Pages:** 4
**Total Lines:** ~1,024
**Refactoring Status:** ✅ 100% (4/4 refactored)

---

## Contents Overview

This section documents all 4 user-facing pages in the Latest TEG section, which provide current tournament information with comprehensive context and analysis of the ongoing or most recent tournament.

| Page | File | Lines | Status | Complexity |
|------|------|-------|--------|-----------|
| Latest Leaderboard | leaderboard.py | 371 | ✅ | Complex |
| Latest Round Context | latest_round.py | 447 | ✅ | Complex |
| Latest TEG Context | latest_teg_context.py | 386 | ✅ | Complex |
| Handicaps | 500Handicaps.py | 221 | ✅ | Medium |

---

## Page: `leaderboard.py`

**Title:** Latest Leaderboard (Auto-Current Tournament)
**Lines of Code:** 371
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Complex

### Purpose

Auto-selects and displays the most recent TEG tournament with live leaderboards for both Trophy (Gross) and Green Jacket (Net) competitions, cumulative charts with 3 different view modes each (Standard/Adjusted/Ranking), and hole-by-hole scorecards for all completed rounds. Users visit for current tournament standings and detailed analysis.

### Data Loading

- **Functions:**
  - `get_round_data(ex_50=True)` - Round data
  - `load_all_data(exclude_teg_50=True)` - Tournament data
  - `read_file()` - Reads TEG status files
- **Files:** all-scores.parquet, round_info.csv, completed_tegs.csv, in_progress_tegs.csv
- **Key Parameters:**
  - `ex_50=True` - Excludes practice TEG
  - `exclude_teg_50=True` - Excludes practice TEG
- **Caching:** Yes (both cached)

### Dependencies

**From utils.py:**
- `get_teg_rounds()` - Gets rounds in current TEG
- `get_round_data(ex_50=True)` - Round data
- `load_all_data(exclude_teg_50=True)` - Tournament data
- `load_datawrapper_css()` - Table styling
- `read_file()` - File loader

**From make_charts.py:**
- `create_cumulative_graph()` - Cumulative score charts
- `adjusted_grossvp()` - Gross vs Par calculation
- `adjusted_stableford()` - Stableford calculation

**From leaderboard_utils.py:**
- `display_leaderboard()` - Trophy competition display
- `display_net_leaderboard()` - Green Jacket net display

**From scorecard_utils.py:**
- `generate_round_comparison_html()` - Scorecard HTML
- `load_scorecard_css()` - Scorecard styling

**Streamlit Components:**
- `st.tabs()` - 3 main tabs (Trophy, Green Jacket, Scorecards)
- `st.segmented_control()` - Chart view mode selector
- `st.plotly_chart()` - Interactive charts
- `st.spinner()` - Loading indicator
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:**
1. `_add_series_markers()` (lines 36-48)
   - Adds player markers to Plotly charts
   - Purpose: Enhance chart readability with colored series
   - Type: Chart formatting
   - Extraction candidate: YES - Move to make_charts.py (also in 102TEG Results)

**Analysis:**
- Total embedded logic: ~13 lines
- Business logic: 0% (pure formatting)
- UI orchestration: 100%
- Extraction recommendation: Extract _add_series_markers() to make_charts.py

### User Interactions

**Widgets:**
- Tabs: 3 tabs
  - Trophy: Leaderboard + 3 chart modes
  - Green Jacket: Leaderboard + 3 chart modes
  - Scorecards: Scorecard display
- Segmented controls: Chart view mode (Standard/Adjusted/Ranking)
- Interactive chart legend: Click to show/hide player

**Session State:** None (chart state internal to Plotly)

### Display Components

**Charts:**
- 6 Plotly cumulative charts total
  - Trophy: Standard, Adjusted, Ranking modes
  - Green Jacket: Standard, Adjusted, Ranking modes
- Interactive legend, hover details

**Tables:**
- Leaderboard tables (Trophy & Green Jacket)
- Scorecard HTML tables

**Layout:**
- Tab-based: Trophy | Green Jacket | Scorecards
- Each tab has leaderboard + charts or scorecards

### CSS/Styling

- `load_datawrapper_css()` - Table styling
- `load_scorecard_css()` - Scorecard styling
- Plotly built-in styling

### Migration Analysis

**Complexity:** Complex

**Migration Tasks:**
1. Extract _add_series_markers() to make_charts.py - 1.5 hours
2. Coordinate extraction with 102TEG Results - 0.5 hour
3. Test all 6 chart modes thoroughly - 2 hours
4. Verify auto-latest TEG selection - 1 hour

**Estimated Effort:** 5-6 hours (including testing)

**Blockers:**
- Coordinate _add_series_markers() extraction with 102TEG Results
- Verify chart generation stability

### Page-Specific Notes

- Similar to 102TEG Results but auto-selects latest TEG
- Good performance (auto-selection eliminates user selection step)
- Shared _add_series_markers() function is good extraction candidate
- Complex but well-structured

---

## Page: `latest_round.py`

**Title:** Latest Round in Context (Comprehensive Round Analysis)
**Lines of Code:** 447
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Complex

### Purpose

Comprehensive analysis of any selected round showing how it compares to all other historical rounds. Includes cumulative performance scoreboards, detailed scorecard, tournament report, scoring distributions, streak analysis, and records/personal bests identification. Most detailed round analysis available. Users visit for in-depth round performance context.

### Data Loading

- **Functions:**
  - `get_ranked_round_data()` - Ranked round data
  - `load_all_data(exclude_incomplete_tegs=False)` - Tournament data
  - `read_file()` - File reading
- **Files:** all-scores.parquet, round_info.csv, streaks.parquet, commentary markdown
- **Key Parameters:** `exclude_incomplete_tegs=False` - Includes current tournament
- **Caching:** Yes (all cached)

### Dependencies

**From utils.py:**
- `get_ranked_round_data()` - Ranked round data
- `load_all_data(exclude_incomplete_tegs=False)` - All tournament data
- `load_datawrapper_css()` - Table styling
- `read_file()` - File loader
- `read_text_file()` - Text file loader
- `STREAKS_PARQUET` - Path constant
- `load_teg_reports_css()` - Report styling

**From make_charts.py:**
- `create_round_graph()` - Round analysis charts

**From helpers/latest_round_processing.py:**
- `get_round_metric_mappings()` - Metric mappings
- `initialize_round_selection_state()` - Session state init
- `update_session_state_defaults()` - State update
- `get_teg_and_round_options()` - Filter options
- `create_metric_tabs_data()` - Tab organization
- `prepare_round_context_display()` - Display preparation

**From scorecard_utils.py:**
- `load_scorecard_css()` - Scorecard styling
- `generate_round_comparison_html()` - HTML generation
- `generate_round_comparison_html_mobile()` - Mobile HTML

**From helpers/score_count_processing.py:**
- `count_scores_by_player()` - Scoring distribution

**From helpers/streak_analysis_processing.py:**
- `get_player_window_streaks()` - Streak analysis

**From helpers/records_identification.py:**
- `identify_aggregate_records_and_pbs()` - Record identification
- `identify_all_time_worsts()` - Worst performance ID
- `identify_9hole_records_and_pbs()` - 9-hole records
- `identify_streak_records()` - Streak records
- `identify_score_count_records()` - Score count records
- `display_records_and_pbs_summary()` - Display records

**Streamlit Components:**
- `st.columns()` - Layout organization
- `st.selectbox()` - TEG, Round selection
- `st.tabs()` - 6 main tabs
- `st.segmented_control()` - View options
- `st.plotly_chart()` - Charts
- `st.session_state` - State management
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:** None

**Analysis:** All business logic extracted to helpers. Page is pure orchestration.

### User Interactions

**Widgets:**
- Selectbox: TEG selection
- Selectbox: Round selection (dynamic, based on TEG)
- Tabs: 6 tabs
  - Scorecard
  - Context (cumulative charts with 4 metrics)
  - Scoring Distribution
  - Streaks
  - Records & PBs
  - Report
- Segmented control: Scorecard view mode
- Segmented control: Scoring type selector

**Session State:**
- Current TEG and Round selections
- Metric selection synced across tabs

### Display Components

**Charts:**
- Cumulative performance charts (4 metrics × multiple modes)
- Plotly interactive charts

**Tables:**
- Scorecard HTML table
- Scoring distribution tables
- Streak tables
- Records tables

**Layout:**
- TEG/Round selectors
- 6-tab interface
- Dynamic content per tab

### CSS/Styling

- `load_datawrapper_css()` - Table styling
- `load_scorecard_css()` - Scorecard styling
- `load_teg_reports_css()` - Report styling
- Plotly styling

### Migration Analysis

**Complexity:** Complex

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Consider session state utility extraction - 1-2 hours (optional)
3. Add docstrings to helper functions - 1 hour

**Estimated Effort:** 1-2 hours (optional improvements)

**Blockers:** None critical

### Page-Specific Notes

- Most comprehensive round analysis page (447 lines)
- High complexity but well-structured
- Excellent use of multiple helpers
- Session state management works well
- Good testing opportunity (multiple data views)
- Key page for advanced analysis

---

## Page: `latest_teg_context.py`

**Title:** Latest TEG in Context (Comprehensive TEG Analysis)
**Lines of Code:** 386
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Complex

### Purpose

Comprehensive analysis of any selected TEG showing aggregate scores, scoring distributions, streak analysis, records/personal bests, and tournament report. Similar structure to latest_round.py but at tournament level rather than individual round. Users visit for overall tournament performance analysis.

### Data Loading

- **Functions:**
  - `get_ranked_teg_data()` - Ranked TEG data
  - `load_all_data(exclude_incomplete_tegs=False)` - Tournament data
  - `read_file()` - File reading
- **Files:** all-scores.parquet, streaks.parquet, commentary markdown
- **Key Parameters:** `exclude_incomplete_tegs=False` - Includes current tournament
- **Caching:** Yes (all cached)

### Dependencies

**From utils.py:**
- `get_ranked_teg_data()` - Ranked TEG data
- `load_datawrapper_css()` - Table styling
- `load_all_data(exclude_incomplete_tegs=False)` - Tournament data
- `read_file()` - File loader
- `STREAKS_PARQUET` - Path constant
- `read_text_file()` - Text file loader
- `load_teg_reports_css()` - Report styling

**From helpers/latest_round_processing.py:**
- `get_round_metric_mappings()` - Metric mappings
- `initialize_teg_selection_state()` - Session state init
- `update_teg_session_state_defaults()` - State update
- `create_teg_selection_reset_function()` - Reset function
- `get_teg_options()` - TEG list
- `create_metric_tabs_data()` - Tab organization
- `prepare_teg_context_display()` - Display prep

**From helpers/score_count_processing.py:**
- `count_scores_by_player()` - Scoring distribution

**From helpers/streak_analysis_processing.py:**
- `get_player_window_streaks()` - Streak analysis

**From helpers/records_identification.py:**
- `identify_aggregate_records_and_pbs()` - Record identification
- `identify_all_time_worsts()` - Worst performance ID
- `identify_streak_records()` - Streak records
- `identify_score_count_records()` - Score count records
- `display_records_and_pbs_summary()` - Display records

**Streamlit Components:**
- `st.columns()` - Layout
- `st.selectbox()` - TEG selection
- `st.button()` - Latest TEG reset button
- `st.tabs()` - 5 main tabs
- `st.segmented_control()` - Scoring type selector
- `st.session_state` - State management
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:**
1. `render_report()` (lines 47-60)
   - Converts markdown to HTML for display
   - Purpose: Format tournament reports
   - Extraction candidate: YES - Duplicate in 102TEG Results, teg_reports.py

**Analysis:**
- Total embedded logic: ~14 lines
- Business logic: 0% (pure formatting)
- UI orchestration: 100%
- Extraction recommendation: Extract render_report() to shared helper

### User Interactions

**Widgets:**
- Selectbox: TEG selection
- Button: Set to Latest TEG (convenience reset)
- Tabs: 5 tabs
  - Context (aggregate scores)
  - Scoring Distribution
  - Streaks
  - Records & PBs
  - Report
- Segmented control: Scoring type selector
- Segmented control: Metric selector (synced across tabs)

**Session State:**
- Current TEG selection
- Metric selection synced across tabs
- Uses st.rerun() on TEG change

### Display Components

**Charts:** None (score display only)

**Tables:**
- Context tables (scores, ranks)
- Scoring distribution tables
- Streak tables
- Records tables
- Report markdown

**Layout:**
- TEG selector with Latest button
- 5-tab interface
- Dynamic content per tab

### CSS/Styling

- `load_datawrapper_css()` - Table styling
- `load_teg_reports_css()` - Report styling

### Migration Analysis

**Complexity:** Complex

**Migration Tasks:**
1. Extract render_report() to helpers/display_helpers.py - 1.5 hours
   - Coordinate with 102TEG Results and teg_reports.py
2. Consider session state utility extraction - 1-2 hours (optional)
3. Add docstrings - 1 hour

**Estimated Effort:** 2-4 hours (depending on coordination)

**Blockers:**
- Coordinate render_report() extraction with other pages

### Page-Specific Notes

- Similar structure to latest_round.py but TEG-level
- Excellent use of helper functions
- Session state management parallel to latest_round.py
- render_report() duplication is high-priority refactoring target
- Key page for tournament analysis
- Good testing opportunity

---

## Page: `500Handicaps.py`

**Title:** Handicaps (Current & Historical Handicaps)
**Lines of Code:** 221
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Displays current handicaps with changes from previous period, historical handicap progression table, and draft handicaps for next TEG if tournament is in progress. Provides ability to save calculated handicaps. Users visit to check current handicaps and track progression.

### Data Loading

- **Functions:**
  - `read_file()` - Reads handicaps CSV
  - `get_current_handicaps_formatted()` - Gets current HCP
  - `get_hc()` - Gets handicap value
  - `get_next_teg_and_check_if_in_progress_fast()` - Checks tournament status
  - `write_file()` - Writes updated handicaps
- **Files:** handicaps.csv
- **Key Parameters:** None
- **Caching:** Yes (all functions cached)

### Dependencies

**From utils.py:**
- `get_base_directory()` - Base path
- `load_datawrapper_css()` - Table styling
- `HANDICAPS_CSV` - Path constant
- `get_current_handicaps_formatted()` - Current HCP getter
- `read_file()` - File loader
- `get_hc()` - HCP value getter
- `get_next_teg_and_check_if_in_progress_fast()` - Status check
- `get_current_in_progress_teg_fast()` - Current TEG check
- `write_file()` - File writer
- `get_player_name()` - Player name lookup
- `clear_all_caches()` - Cache clearing

**Streamlit Components:**
- `st.columns()` - Layout (metrics display)
- `st.metric()` - Display handicaps
- `st.button()` - Save handicaps button
- `st.expander()` - History/draft expanders
- `st.rerun()` - Refresh after save
- `st.caption()` - Info text
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:**
1. `format_change()` (lines 30-44)
   - Formats handicap change with color indicator
   - Purpose: Display HCP change (+/- with color)
   - Extraction candidate: Move to display_helpers

2. `format_value()` (lines 46-57)
   - Formats historic handicap values
   - Purpose: Format cells in history table
   - Extraction candidate: Move to display_helpers

3. `format_name()` (lines 84-85)
   - Formats names for metric labels
   - Purpose: Clean name display
   - Extraction candidate: Move to display_helpers

4. `transform_handicaps_to_csv_format()` (lines 138-160)
   - Transforms calculated handicaps to CSV format
   - Purpose: Prepare handicaps for saving
   - Extraction candidate: Move to helpers/data_update_processing

**Analysis:**
- Total embedded logic: ~50 lines
- Business logic: 30% (HCP transformation)
- UI formatting: 70%
- Extraction recommendation: Extract formatting functions and transform function

### User Interactions

**Widgets:**
- Metrics: Display current handicaps with change
- Button: "Save Missing Handicaps" (shows calculated drafts)
- Expander: Historical handicaps progression
- Expander: Draft handicaps for next TEG (if in progress)
- Uses st.rerun() after save

**Session State:** Implicit via st.rerun()

### Display Components

**Charts:** None

**Tables:**
- Handicap metrics display
- Historical progression table
- Draft handicaps table

**Layout:**
- Current handicaps as metrics (colored with changes)
- Save button
- Collapsible sections for history and draft

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Applied globally
- Custom color formatting for changes

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Extract format_change() to display_helpers.py - 1 hour
2. Extract format_value() to display_helpers.py - 1 hour
3. Extract format_name() to display_helpers.py - 0.5 hour
4. Extract transform_handicaps_to_csv_format() to data_update_processing - 1 hour
5. Update imports - 0.5 hour
6. Test save functionality - 1 hour

**Estimated Effort:** 4-5 hours (including testing)

**Blockers:** None

### Page-Specific Notes

- Has write capability (save handicaps)
- Uses cache clearing after save (cache_data.clear())
- Session state via st.rerun() pattern
- Good extraction opportunity (4 functions)
- Low-priority refactoring (already functional)
- Important admin function for handicap management

---

## Section Summary

### Refactoring Status
- ✅ All 4 pages fully refactored and following standard template
- Clean separation between analysis and presentation
- Excellent use of helper functions

### Key Findings

1. **Duplicate Code Identified**
   - `render_report()` appears in 3 pages (102TEG Results, teg_reports.py, latest_teg_context.py)
   - `_add_series_markers()` appears in 2 pages (leaderboard.py, 102TEG Results)
   - HIGH PRIORITY refactoring targets

2. **Session State Patterns**
   - latest_round.py and latest_teg_context.py use similar state management
   - Could be templatized for reuse

3. **Complex Helper Dependencies**
   - latest_round.py uses 7 helper modules (most in codebase)
   - latest_teg_context.py uses 5 helper modules
   - Indicates well-structured, extracted logic

### Extraction Opportunities

1. **High Priority:**
   - Extract render_report() to display_helpers.py - 1.5 hours
   - Extract _add_series_markers() to make_charts.py - 1.5 hours

2. **Medium Priority:**
   - Extract formatting functions from 500Handicaps.py - 2-3 hours
   - Extract session state pattern to utility - 2-3 hours

3. **Low Priority:**
   - Add docstrings to all helper functions - 2 hours

### Common Patterns
1. **Multi-Tab Analysis Interface** - Used by all 4 pages
2. **Segmented Control for Selection** - Used by latest_round.py, latest_teg_context.py
3. **Session State + Selector Sync** - Used by latest_round.py, latest_teg_context.py
4. **Chart View Modes (Standard/Adjusted/Ranking)** - Used by leaderboard.py, 102TEG Results

### Testing Priorities
1. **leaderboard.py**: Test all 6 chart modes + auto-selection
2. **latest_round.py**: Test session state sync, all 6 tabs
3. **latest_teg_context.py**: Test latest TEG button, tab sync
4. **500Handicaps.py**: Test save functionality + cache clearing

### Reusable Template Opportunities
1. **Multi-Metric Analysis Page** - Could template latest_round.py pattern
2. **Report Rendering** - Could create generic report display component
3. **Chart View Mode Selector** - Could template Standard/Adjusted/Ranking pattern

### Total Effort to Refactor This Section
- Extract duplicate functions: 3-4 hours
- Format extraction from 500Handicaps: 2-3 hours
- Session state templating: 2-3 hours (optional)
- Testing + documentation: 3-4 hours
- **Total: 10-14 hours (mostly duplicate extraction)**

### Notes
- This section is well-refactored overall
- Main work is extracting duplicate functions (render_report, _add_series_markers)
- Good opportunity to create shared helpers
- Complex pages but properly structured
- Key section for current tournament browsing
