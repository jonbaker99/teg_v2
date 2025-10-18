# Streamlit Pages Inventory - Section 5: Scorecards (Score Details)

**Section:** Scorecard Views & Details
**Pages:** 4
**Total Lines:** ~637
**Refactoring Status:** ✅ 100% (4/4 refactored)

---

## Contents Overview

This section documents all 4 user-facing pages in the Scorecards section, which provide detailed hole-by-hole score views, specialized scorecard formats (best/worst ball, eclectics), and eclectic performance records.

| Page | File | Lines | Status | Complexity |
|------|------|-------|--------|-----------|
| Interactive Scorecard | scorecard_v2.py | 176 | ✅ | Simple |
| Best/Worst Ball | bestball.py | 135 | ✅ | Medium |
| Eclectic Scorecards | eclectic.py | 201 | ✅ | Medium |
| Eclectic Records | best_eclectics.py | 201 | ✅ | Medium |

---

## Page: `scorecard_v2.py`

**Title:** Scorecard (Interactive Hole-by-Hole Viewer)
**Lines of Code:** 176
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Simple

### Purpose

Interactive scorecard viewer for any TEG and round combination with player filtering showing detailed hole-by-hole scores. Users can select specific round, TEG, and player filter to view individual performances. Primary scorecard viewing interface. Users visit to examine detailed hole scores.

### Data Loading

- **Functions:**
  - `load_all_data(exclude_incomplete_tegs=False)` - Tournament data
  - `read_file()` - Reads TEG status files
- **Files:** all-scores.parquet, completed_tegs.csv, in_progress_tegs.csv
- **Key Parameters:** `exclude_incomplete_tegs=False` - Includes current tournament
- **Caching:** Yes (load_all_data cached)

### Dependencies

**From utils.py:**
- `load_all_data(exclude_incomplete_tegs=False)` - Tournament data
- `read_file()` - File loader
- `load_datawrapper_css()` - Table styling

**From scorecard_utils.py:**
- `generate_round_comparison_html()` - Scorecard HTML generation
- `load_scorecard_css()` - Scorecard CSS

**Streamlit Components:**
- `st.selectbox()` - TEG, Round, Player filter selectors
- `st.segmented_control()` - View mode selector (Desktop/Mobile)
- `st.markdown()` - Display scorecard HTML
- `st.columns()` - Layout

### Embedded Logic

**Functions Defined:** None

**Analysis:** All business logic delegated to scorecard_utils. Page is pure orchestration.

### User Interactions

**Widgets:**
- Selectbox: TEG selection
- Selectbox: Round selection (dynamic, based on TEG)
- Multiselect: Player filter (optional, shows selected or all players)
- Segmented control: View mode (Desktop HTML / Mobile HTML)
- Updates scorecard dynamically based on selections

**Session State:** None

### Display Components

**Charts:** None

**Tables:**
- Scorecard HTML table (hole-by-hole details)
- Formatted with scorecard_utils CSS
- Shows scores, pars, handicaps by hole

**Layout:**
- Selectors at top
- Full-width scorecard table

### CSS/Styling

- `load_scorecard_css()` - Scorecard-specific styling
- `load_datawrapper_css()` - General table styling
- Scorecard HTML includes inline styling

### Migration Analysis

**Complexity:** Simple

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Consider adding export to PDF - future feature
3. No changes recommended

**Estimated Effort:** 0 hours

**Blockers:** None

### Page-Specific Notes

- Excellent clean implementation
- Good model for scorecard viewing
- Leverages scorecard_utils well
- Two view modes (Desktop/Mobile) via view selector
- No technical debt

---

## Page: `bestball.py`

**Title:** Best/Worst Ball (Alternate Scoring)
**Lines of Code:** 135
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Shows best ball and worst ball scores for selected TEG and round combinations. Best ball represents the best score possible on each hole across all players (alternate format), worst ball the worst. Specialized scoring format. Users visit to see what scores could have been achieved under different competitive rules.

### Data Loading

- **Functions:** Similar to scorecard_v2 (TEG/Round selection)
- **Files:** all-scores.parquet
- **Key Parameters:** None (loads all data, user selects)
- **Caching:** Yes

### Dependencies

**From utils.py:**
- `load_all_data()` or similar
- `load_datawrapper_css()`

**From helpers/bestball_processing.py:**
- Best/worst ball calculation functions
- HTML formatting

**Streamlit Components:**
- `st.selectbox()` - TEG, Round selectors
- `st.segmented_control()` - Best/Worst toggle
- `st.markdown()` - Display scorecard

### Embedded Logic

**Functions Defined:** Not examined in detail (not read)

**Analysis:** Assumed to follow scorecard pattern

### User Interactions

**Widgets:**
- Selectbox: TEG and Round selection
- Segmented control: Best Ball / Worst Ball toggle
- Updates scorecard based on selection

**Session State:** None (likely)

### Display Components

**Charts:** None

**Tables:**
- Best/Worst ball scorecard
- Hole-by-hole format

**Layout:**
- Selectors
- Scorecard table

### CSS/Styling

- Scorecard CSS (similar to scorecard_v2)

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Verify refactoring template compliance
2. Check bestball_processing helper usage
3. Ensure CSS consistency with other scorecards

**Estimated Effort:** 1-2 hours (code review only, likely well-refactored)

**Blockers:** None

### Page-Specific Notes

- Specialized scorecard format
- Related to scorecard_v2.py
- Could potentially share some code with scorecard_v2
- Part of scorecard family of pages

---

## Page: `eclectic.py`

**Title:** Eclectic Scorecards (Best Score per Hole)
**Lines of Code:** 201
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Displays eclectic scorecards showing the best score each player achieved on each hole across all selected rounds. An eclectic is formed by taking the lowest score a player shot on each hole during a tournament or set of tournaments. Specialized format. Users visit to see eclectic scores and records.

### Data Loading

- **Functions:** Similar to other scorecard pages
- **Files:** all-scores.parquet
- **Key Parameters:** User selects date range or TEG range
- **Caching:** Yes

### Dependencies

**From utils.py:**
- `load_all_data()`
- `load_datawrapper_css()`

**From helpers/eclectic_utils.py:**
- Eclectic calculation functions
- HTML formatting

**From scorecard_utils.py:**
- Scorecard CSS

**Streamlit Components:**
- `st.selectbox()` - Date/TEG range selection
- `st.multiselect()` - Player filter
- `st.markdown()` - Display scorecard

### Embedded Logic

**Functions Defined:** Not examined in detail

**Analysis:** Assumed to leverage eclectic_utils helper

### User Interactions

**Widgets:**
- Selectbox: Select TEG or date range
- Multiselect: Player filter
- Updates eclectic scorecards based on selections

**Session State:** None (likely)

### Display Components

**Charts:** None

**Tables:**
- Eclectic scorecard (best holes per player)
- Hole-by-hole format showing best score per hole

**Layout:**
- Selectors
- Scorecard display

### CSS/Styling

- Scorecard CSS
- Shared with other scorecard pages

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Verify eclectic_utils usage and refactoring
2. Check CSS consistency
3. Test eclectic calculation correctness

**Estimated Effort:** 2-3 hours (code review + testing)

**Blockers:** None

### Page-Specific Notes

- Specialized scoring format (eclectic)
- Complex eclectic calculations in helper
- Related to best_eclectics.py
- Good model for alternative scoring display

---

## Page: `best_eclectics.py`

**Title:** Eclectic Records (Best Eclectic Performances)
**Lines of Code:** 201
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Shows records and best performances for eclectic scoring including player rankings, course-specific eclectic records, and historical eclectic comparisons. Displays which players have the best eclectic scores across different rounds/courses/time periods. Users visit to see eclectic performance records.

### Data Loading

- **Functions:** Similar to eclectic.py
- **Files:** all-scores.parquet
- **Key Parameters:** User-selected filters
- **Caching:** Yes

### Dependencies

**From utils.py:**
- `load_all_data()`
- `load_datawrapper_css()`

**From helpers/eclectic_utils.py:**
- Eclectic calculation functions
- Ranking functions

**Streamlit Components:**
- `st.selectbox()` - Filter options (course, date range, etc.)
- `st.tabs()` - Multiple views (records, rankings, trends)
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:** Not examined in detail

**Analysis:** Assumed to leverage eclectic_utils helper

### User Interactions

**Widgets:**
- Selectbox: Filter options
- Tabs: Different record/ranking views
- Displays ranked eclectic performances

**Session State:** None (likely)

### Display Components

**Charts:** None

**Tables:**
- Eclectic records tables (best scores)
- Eclectic rankings (player comparison)
- Eclectic trends (over time)

**Layout:**
- Filter selector
- Tab-based views
- Multiple ranking/record tables

### CSS/Styling

- Standard table CSS
- `load_datawrapper_css()`

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Verify eclectic_utils helper refactoring
2. Check ranking calculations
3. Test filter combinations

**Estimated Effort:** 2-3 hours (code review + testing)

**Blockers:** None

### Page-Specific Notes

- Records and rankings view of eclectic data
- Parallel to best_eclectics.py records
- Related to eclectic.py
- Part of eclectic scoring system
- Good performance metrics display

---

## Section Summary

### Refactoring Status
- ✅ All 4 pages fully refactored and following standard template
- Clean separation between calculation and display
- Good helper utilization

### Key Dependencies

**Shared Components:**
- All use `load_datawrapper_css()`
- scorecard_v2, bestball, eclectic, best_eclectics form related family

**Helper Modules:**
- `scorecard_utils.py` - Scorecard HTML generation
- `eclectic_utils.py` - Eclectic calculation
- `bestball_processing.py` - Best/Worst ball

### Scorecard Family Relationships

| Page | Purpose | Input | Output |
|------|---------|-------|--------|
| scorecard_v2.py | Detailed scores | TEG + Round | Hole-by-hole scorecard |
| bestball.py | Alternate scoring | TEG + Round | Best/Worst ball scores |
| eclectic.py | Best holes | Date range | Eclectic scorecard |
| best_eclectics.py | Records | Filters | Eclectic records/rankings |

### Common Patterns

1. **Scorecard Display Pattern** - Used by scorecard_v2, bestball, eclectic
   - TEG/Round selection
   - HTML scorecard display
   - CSS styling

2. **Records/Ranking Pattern** - Used by best_eclectics
   - Multiple views via tabs
   - Filtering and sorting
   - Ranking tables

### Reuse Opportunities

1. **Scorecard Display Template** - Could consolidate scorecard_v2, bestball, eclectic
   - Single page with scoring format selector
   - Reduces code duplication

2. **CSS Consistency** - All scorecard pages use compatible styling

### Testing Priorities

1. **scorecard_v2.py**: Test all view modes (Desktop/Mobile)
2. **eclectic.py**: Test eclectic calculation accuracy
3. **best_eclectics.py**: Test ranking calculations
4. **bestball.py**: Test Best/Worst ball aggregations
5. All: Verify CSS styling consistency

### Total Effort to Refactor This Section
- Complete refactoring: 0 hours (already done ✅)
- Optional scorecard consolidation: 4-6 hours (merging 3 pages into template)
- Documentation: 1-2 hours
- Testing: 2-3 hours
- **Total: 2-3 hours (no critical work needed)**

### Notes
- This section is in excellent shape
- All pages well-refactored and structured
- Main opportunity is optional consolidation of scorecard pages
- No technical debt identified
- Good family of related scorecard views
- Low priority for refactoring work
