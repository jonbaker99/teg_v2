# Streamlit Pages Inventory - Section 1: History Pages

**Section:** History & Reference
**Pages:** 6
**Total Lines:** ~1,400
**Refactoring Status:** ✅ 100% (6/6 refactored)

---

## Contents Overview

This section documents all 6 user-facing pages in the History section, which help users understand TEG history, view results, and track player rankings over time.

| Page | File | Lines | Status | Complexity |
|------|------|-------|--------|-----------|
| Site Map | contents.py | 78 | ✅ | Simple |
| TEG History | 101TEG History.py | 122 | ✅ | Medium |
| Honours Board | 101TEG Honours Board.py | 181 | ✅ | Medium |
| Full Results | 102TEG Results.py | 419 | ✅ | Complex |
| Player Rankings | player_history.py | 552 | ✅ | Complex |
| Tournament Reports | teg_reports.py | 224 | ✅ | Medium |

---

## Page: `contents.py`

**Title:** The El Golfo (Site Map)
**Lines of Code:** 78
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Simple

### Purpose

Landing page and site map displaying all navigable sections and pages with clickable links organized in a 3-column grid layout. Users visit this to navigate to specific pages or understand the app structure.

### Data Loading

- **Functions:** None (uses static configuration)
- **Files:** None (reads from page_config.PAGE_DEFINITIONS)
- **Key Parameters:** N/A
- **Caching:** No cache needed (static content)

### Dependencies

**From utils.py:**
- `apply_custom_navigation_css()` - Applies navigation styling
- `get_app_base_url()` - Gets base URL for links
- `convert_filename_to_streamlit_url()` - Converts file paths to URLs
- `get_page_layout()` - Gets layout configuration

**From page_config.py:**
- `PAGE_DEFINITIONS` - Page metadata and structure
- `SECTION_CONFIG` - Section organization

**Streamlit Components:**
- `st.columns()` - 3-column grid layout
- `st.markdown()` - Renders HTML links

**External:**
- Python string formatting

### Embedded Logic

**Functions Defined:** None

**Analysis:** Pure navigation page with no business logic. All content orchestration is inline HTML/Markdown generation from PAGE_DEFINITIONS.

### User Interactions

**Widgets:**
- Clickable HTML links (no form inputs)
- Pure navigation, no state

**Session State:** None used

### Display Components

**Charts:** None

**Tables:** None

**Layout:**
- 3-column grid layout
- Organized by SECTION_CONFIG
- HTML link lists with custom CSS classes

### CSS/Styling

- `navigation.css` - Navigation styling via apply_custom_navigation_css()
- Custom link styling for section headers
- Responsive 3-column layout

### Migration Analysis

**Complexity:** Simple

**Migration Tasks:**
1. Already well-structured (✅ complete)
2. Uses configuration-driven approach (✅ best practice)
3. No refactoring needed

**Estimated Effort:** 0 hours (no changes recommended)

**Blockers:** None

### Page-Specific Notes

- Entry point for many users
- Critical for app discoverability
- All structure driven by PAGE_DEFINITIONS config
- Zero technical debt

---

## Page: `101TEG History.py`

**Title:** TEG History (Complete Tournament List)
**Lines of Code:** 122
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Comprehensive chronological timeline of all completed TEG tournaments showing Trophy, Green Jacket, and Wooden Spoon winners. Automatically calculates missing winners and provides option to save calculations to cache for faster loading. Users visit to understand complete TEG history.

### Data Loading

- **Functions:**
  - `load_cached_winners()` - Loads pre-cached winners data
  - `prepare_complete_history_table_fast()` - Creates history table
- **Files:** `data/winners_cache.csv` (cached via helper)
- **Key Parameters:** None (loads all TEG history)
- **Caching:** @st.cache_data on load_cached_winners()

### Dependencies

**From utils.py:**
- `load_datawrapper_css()` - Loads table styling
- `add_custom_navigation_links()` - Bottom navigation

**From helpers/history_data_processing.py:**
- `prepare_complete_history_table_fast()` - Constructs history table with all TEG winners
- `load_cached_winners()` - Cached winners loader
- `calculate_and_save_missing_winners()` - Calculates missing winner data

**Streamlit Components:**
- `st.button()` - Save winners button
- `st.rerun()` - Refresh after save
- `st.markdown()` - Display title and intro

### Embedded Logic

**Functions Defined:**
1. `wrap_player_name()` (lines 70-75)
   - Wraps player name in HTML span for formatting
   - Purpose: Apply inline styling to player names
   - Extraction candidate: Yes, move to display_helpers

**Analysis:**
- Total embedded logic: ~6 lines
- Non-business logic: Name formatting only
- Should be extracted: Yes, but low priority
- Extraction target: helpers/display_helpers.py

### User Interactions

**Widgets:**
- Button: "Save Missing Winners" (conditionally shown if missing winners detected)
- Uses session state via st.rerun()

**Session State:**
- Implicitly managed via st.rerun() after save

### Display Components

**Charts:** None

**Tables:**
- Single HTML table with history-table CSS class
- Formatted via datawrapper_table()

**Layout:**
- Title and intro text
- Single history table
- Save button section
- Bottom navigation links

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `history-table` - Custom history table styling
- load_datawrapper_css() applied

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Extract wrap_player_name() to display_helpers.py (1 hour)
2. Add docstrings to helper functions (0.5 hour)
3. Consider caching strategy review (check if TTL needed)

**Estimated Effort:** 1-2 hours (low priority improvements)

**Blockers:** None

### Page-Specific Notes

- Has write capability (save winners to cache)
- Cache clearing might be needed if winners change
- Currently uses no TTL on cache (persistent)
- Simple and well-structured page

---

## Page: `101TEG Honours Board.py`

**Title:** TEG Honours Board (Comprehensive Honors)
**Lines of Code:** 181
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Displays comprehensive honors and achievement records including Trophy winners, Green Jacket winners, Wooden Spoon winners, doubles (2-time winners), eagles, and holes-in-one across all tournaments. Users visit to understand all-time achievement records.

### Data Loading

- **Functions:**
  - `load_all_data()` with parameters
  - `get_teg_winners()` - Gets trophy/jacket/spoon winners
- **Files:** all-scores.parquet (via load_all_data)
- **Key Parameters:**
  - `exclude_incomplete_tegs=True` - Excludes current tournament
  - `exclude_teg_50=True` - Excludes practice TEG 50
- **Caching:** Yes (load_all_data cached with no TTL)

### Dependencies

**From utils.py:**
- `load_all_data(exclude_incomplete_tegs=True, exclude_teg_50=True)` - Main data loader
- `get_teg_winners()` - Extracts winners data
- `get_trophy_full_name()` - Formats trophy winner names
- `load_datawrapper_css()` - Table styling
- `add_custom_navigation_links()` - Navigation

**From utils_win_tables.py:**
- `summarise_teg_wins()` - Aggregates win counts
- `compress_ranges()` - Formats win ranges (TEG #1-5, #15-18)

**From helpers/history_data_processing.py:**
- `calculate_trophy_jacket_doubles()` - Finds double winners
- `get_eagles_data()` - Extracts eagle records
- `get_holes_in_one_data()` - Extracts hole-in-one records

**Streamlit Components:**
- `st.tabs()` - 6 tabs for different honor types
- `st.caption()` - Additional info text
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:** None

**Analysis:** All business logic successfully extracted to helpers. Page is pure orchestration.

### User Interactions

**Widgets:**
- 6 tabs: Trophy, Green Jacket, Wooden Spoon, Doubles, Eagles, Holes in One
- No interactive inputs

**Session State:** None

### Display Components

**Charts:** None

**Tables:**
- 6 separate HTML tables (one per tab)
- Styled with datawrapper_table CSS

**Layout:**
- Tab-based organization
- One table per tab
- Captions with record information

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- load_datawrapper_css() applied
- Responsive layout

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Consider adding export functionality (future feature)
3. Add docstrings to helper functions

**Estimated Effort:** 0.5-1 hour (documentation only)

**Blockers:** None

### Page-Specific Notes

- Depends on exclude_teg_50 parameter for clean data
- Tab structure works well for multiple honor types
- Clean helper function usage
- No technical debt

---

## Page: `102TEG Results.py`

**Title:** Full Results (Complete Tournament Viewer)
**Lines of Code:** 419
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Complex

### Purpose

Most comprehensive results page displaying full tournament details for any TEG including leaderboards (Trophy & Green Jacket), cumulative charts with 3 different view modes each, hole-by-hole scorecards for all rounds, and tournament reports. This is the main page users visit to deeply analyze a tournament.

### Data Loading

- **Functions:**
  - `get_round_data()` - Gets round-level data
  - `load_all_data()` - Gets all tournament data
  - `read_text_file()` - Reads markdown reports
- **Files:** all-scores.parquet, round_info.csv, tournament reports (markdown)
- **Key Parameters:** None (loads complete dataset, user selects TEG via UI)
- **Caching:** Yes (load_all_data cached with no TTL)

### Dependencies

**From utils.py:**
- `get_teg_rounds()` - Gets rounds for selected TEG
- `get_round_data()` - Round-level data
- `load_all_data()` - Tournament data
- `load_datawrapper_css()` - Table styling
- `load_teg_reports_css()` - Report markdown styling
- `read_text_file()` - Report loading

**From make_charts.py:**
- `create_cumulative_graph()` - Cumulative score chart generation
- `adjusted_grossvp()` - Gross vs Par calculation
- `adjusted_stableford()` - Stableford calculation

**From leaderboard_utils.py:**
- `display_leaderboard()` - Trophy competition leaderboard
- `display_net_leaderboard()` - Green Jacket net leaderboard

**From scorecard_utils.py:**
- `generate_round_comparison_html()` - Scorecard HTML generation
- `load_scorecard_css()` - Scorecard styling

**Streamlit Components:**
- `st.radio()` - TEG selection
- `st.tabs()` - 4 main tabs
- `st.segmented_control()` - Chart view mode selection
- `st.plotly_chart()` - Interactive charts
- `st.spinner()` - Loading indicator

### Embedded Logic

**Functions Defined:**
1. `load_markdown()` (lines 56-66)
   - Cached markdown file loader with error handling
   - Purpose: Cache markdown files in session
   - Uses: @st.cache_data decorator

2. `render_report()` (lines 69-78)
   - Converts markdown to HTML for display
   - Purpose: Format tournament reports
   - Extraction candidate: YES - appears in 3 pages

3. `_add_series_markers()` (lines 81-94)
   - Adds player markers to Plotly charts
   - Purpose: Enhance chart readability with colored series
   - Extraction candidate: YES - appears in leaderboard.py too

**Analysis:**
- Total embedded logic: ~40 lines
- Business logic: 10% (marker styling)
- UI orchestration: 90%
- Extraction recommendation: Extract render_report() and _add_series_markers()

### User Interactions

**Widgets:**
- Radio buttons: TEG selection
- Tabs: 4 main tabs (Trophy, Green Jacket, Scorecards, Reports)
- Segmented controls: Chart view modes (Standard, Adjusted, Ranking) × 2 competitions
- Interactive chart legend clicking

**Session State:** Chart interactions stored in Plotly's internal state

### Display Components

**Charts:**
- 6 Plotly cumulative charts (Trophy Standard/Adjusted/Ranking, Jacket same)
- Each with interactive legend and hover info
- All use _add_series_markers() for formatting

**Tables:**
- Leaderboard tables (Trophy & Green Jacket)
- Scorecards (HTML-formatted, hole-by-hole)

**Layout:**
- Tab-based: Trophy | Green Jacket | Scorecards | Reports
- Each tab contains full tournament view
- Responsive design

### CSS/Styling

- `load_datawrapper_css()` - Table styling
- `load_scorecard_css()` - Scorecard specific
- `load_teg_reports_css()` - Report markdown
- Plotly built-in styling for charts

### Migration Analysis

**Complexity:** Complex

**Migration Tasks:**
1. Extract render_report() to helpers (shared with teg_reports.py, latest_teg_context.py) - 1.5 hours
2. Extract _add_series_markers() to make_charts.py - 1 hour
3. Add comprehensive docstrings - 1 hour
4. Review chart generation for edge cases - 2 hours
5. Test all 6 chart modes thoroughly - 3 hours

**Estimated Effort:** 8-10 hours (including testing)

**Blockers:**
- Plotly chart interactions need thorough testing
- Ensure marker styling matches across all pages
- Verify scorecard generation still works post-refactoring

### Page-Specific Notes

- Most comprehensive page (419 lines)
- High complexity but well-refactored
- Multiple chart generation modes (potential optimization opportunity)
- render_report() duplication priority refactoring target
- Critical page for data exploration - needs careful testing after changes

---

## Page: `player_history.py`

**Title:** Player Rankings (Historical Rankings Matrix)
**Lines of Code:** 552
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Complex

### Purpose

Historical rankings matrix showing each player's finishing position in every completed TEG separately for Trophy competition (Gross) and Green Jacket competition (Net). Shows detailed statistics including finish counts, average positions, and combined rankings. Users visit to understand long-term player performance trends.

### Data Loading

- **Functions:**
  - `get_complete_teg_data()` - Gets all completed TEG data
- **Files:** Derived from all-scores.parquet (via helper)
- **Key Parameters:** None
- **Caching:** Yes (load_all_data cached with no TTL)

### Dependencies

**From utils.py:**
- `get_complete_teg_data()` - Main data loading
- `load_datawrapper_css()` - Table styling
- `datawrapper_table()` - Table formatting function
- `get_net_competition_measure()` - Gets current net metric (NetVP or Stableford)

**From helpers:** Internal data processing functions

**Streamlit Components:**
- `st.tabs()` - Trophy vs Green Jacket tabs
- `st.selectbox()` - Advanced options expander
- `st.expander()` - Show/hide options section

### Embedded Logic

**Functions Defined:**
1. `post_process_ranking_table()` (lines 42-82)
   - Applies CSS classes to ranking cells
   - Purpose: Highlight 1st/last place with formatting
   - Extraction candidate: Move to display_helpers

2. `create_position_count_summary()` (lines 84-152)
   - Counts how many times each player finished in each position
   - Purpose: Summary statistics
   - Extraction candidate: Move to best_performance_processing

3. `create_average_position_summary()` (lines 155-205)
   - Calculates average finishing position per player
   - Purpose: Trend analysis
   - Extraction candidate: Move to best_performance_processing

4. `create_combined_position_summary()` (lines 207-267)
   - Combines average and count data
   - Purpose: Comprehensive view
   - Extraction candidate: Move to best_performance_processing

5. `create_net_competition_ranking_table()` (lines 269-344)
   - Handles dynamic net competition measure selection
   - Purpose: Support NetVP (TEG1-5) vs Stableford (TEG6+) transition
   - Extraction candidate: Keep in page (complex logic)

6. `create_teg_ranking_table()` (lines 348-429)
   - Core ranking calculation with tie detection (= symbol)
   - Purpose: Generate main ranking matrix
   - Extraction candidate: Keep in page (core feature)

**Analysis:**
- Total embedded logic: ~250 lines
- Business logic: 60% (ranking calculations)
- UI orchestration: 40%
- Extraction recommendation: Extract position summary functions (functions 2-4)

### User Interactions

**Widgets:**
- Tabs: Trophy competition vs Green Jacket (Net) competition
- Advanced options expander:
  - Toggle row selection (show/hide specific players)
  - Toggle column selection (show/hide specific TEGs)

**Session State:** Selection state maintained across tab switches

### Display Components

**Charts:** None

**Tables:**
- Main ranking matrix (players × TEGs)
- Player names as rows, TEG numbers as columns
- Cells show finishing position with rank notation

**Tie Handling:**
- Displayed as "=" when multiple players tie for position
- Prevents rank number gaps

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- Custom CSS classes for 1st/last place highlighting
- Responsive layout

### Migration Analysis

**Complexity:** Complex

**Migration Tasks:**
1. Extract create_position_count_summary() to best_performance_processing - 1.5 hours
2. Extract create_average_position_summary() to best_performance_processing - 1.5 hours
3. Extract create_combined_position_summary() to best_performance_processing - 1.5 hours
4. Extract post_process_ranking_table() to display_helpers - 0.5 hours
5. Add comprehensive docstrings - 1 hour
6. Test tie detection and edge cases - 2 hours

**Estimated Effort:** 8-10 hours (including testing)

**Blockers:**
- Tie detection logic needs thorough testing
- NetVP/Stableford transition at TEG 6 requires verification
- Advanced options interaction edge cases

### Page-Specific Notes

- Most lines per page (552 lines)
- Complex ranking calculations well-encapsulated in functions
- Handles net competition measure transition (TEG 5 → TEG 6)
- Good extraction candidate for further refactoring
- Well-designed UI despite complexity

---

## Page: `teg_reports.py`

**Title:** Tournament Reports (Round & Full Reports)
**Lines of Code:** 224
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Displays detailed round-by-round and full tournament reports with commentary and analysis. Supports both normal and satirical report versions (for completed tournaments). Users visit to read in-depth tournament narratives and round summaries.

### Data Loading

- **Functions:**
  - `load_all_data()` - Tournament data
  - `read_file()` - Reads completed/in-progress TEG lists
  - `read_text_file()` - Reads markdown report files
- **Files:** all-scores.parquet, completed_tegs.csv, in_progress_tegs.csv, markdown reports
- **Key Parameters:**
  - `exclude_teg_50=True` - Excludes practice TEG
- **Caching:** Yes (load_all_data cached)

### Dependencies

**From utils.py:**
- `read_text_file()` - Markdown report loader
- `read_file()` - CSV loader for TEG status
- `load_all_data(exclude_teg_50=True)` - Tournament data
- `get_teg_rounds()` - Gets rounds for selected TEG
- `load_datawrapper_css()` - Table styling
- `load_teg_reports_css()` - Report markdown styling

**Streamlit Components:**
- `st.selectbox()` - TEG selection
- `st.tabs()` - Round reports + full report tabs
- `st.segmented_control()` - Report type toggle (Normal vs Satire)
- `st.session_state` - Stores report type selection

### Embedded Logic

**Functions Defined:**
1. `render_report()` (lines 35-49)
   - Converts markdown to HTML for display
   - Purpose: Format reports for display
   - Extraction candidate: YES - duplicate in 102TEG Results, latest_teg_context

**Analysis:**
- Total embedded logic: ~15 lines
- Renders markdown files
- Extraction recommendation: Create shared helper

### User Interactions

**Widgets:**
- Selectbox: Choose which TEG to view
- Tabs: Dynamic tabs for each round + full report (created from available reports)
- Segmented control: Toggle between Normal and Satirical versions (only for completed TEGs)

**Session State:**
- Stores current report type (Normal/Satire)
- Maintains tab focus across changes

### Display Components

**Charts:** None

**Tables:** None (markdown rendered reports)

**Layout:**
- TEG selector
- Segmented control for report type
- Dynamic tabs for each round report
- Full tournament report tab

### CSS/Styling

- `load_teg_reports_css()` - Report-specific markdown styling
- Markdown renders to HTML with custom CSS

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Extract render_report() to helpers/display_helpers.py (shared with 102TEG Results, latest_teg_context) - 1 hour
2. Consider moving report type logic to session_state_utils - 1 hour
3. Add error handling for missing reports - 1 hour

**Estimated Effort:** 2-3 hours

**Blockers:**
- Coordinate render_report() extraction with other pages
- Ensure report availability checking is robust

### Page-Specific Notes

- Clean and straightforward implementation
- Dynamic tab creation based on available reports
- Session state used effectively for report type
- Good opportunity to extract shared render_report() function
- Requires report files to be pre-generated (separate process)

---

## Section Summary

### Refactoring Status
- ✅ All 6 pages fully refactored and following standard template
- Clean separation between UI orchestration and business logic
- Helper functions well-utilized

### Extraction Opportunities
1. **High Priority:** Extract duplicate `render_report()` function (appears in 3 pages)
2. **High Priority:** Extract `_add_series_markers()` (appears in 102TEG Results + leaderboard.py)
3. **Medium Priority:** Extract position summary functions from player_history.py
4. **Low Priority:** Extract `wrap_player_name()` from 101TEG History.py

### Common Dependencies
- All pages use `load_datawrapper_css()`
- All use `add_custom_navigation_links()`
- Core data: `load_all_data()`, `get_round_data()`, `get_complete_teg_data()`

### Testing Priorities
- 102TEG Results: Test all 6 chart modes, scorecard generation
- player_history.py: Test tie detection, TEG 5→6 transition, sorting
- teg_reports.py: Test report availability, Normal vs Satire toggle
- All: Verify CSS styling on different screen sizes

### Total Effort to Refactor This Section
- Extract duplicates: 2-3 hours
- Improve documentation: 1-2 hours
- Testing: 3-4 hours
- **Total: 6-9 hours**
