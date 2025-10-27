# Streamlit Pages Inventory - Section 2: Records & Personal Bests

**Section:** Records & Personal Bests
**Pages:** 4
**Total Lines:** ~859
**Refactoring Status:** ✅ 100% (4/4 refactored)

---

## Contents Overview

This section documents all 4 user-facing pages in the Records section, which help users discover all-time records, top performances, personal bests, and remarkable finish comebacks.

| Page | File | Lines | Status | Complexity |
|------|------|-------|--------|-----------|
| TEG Records | 300TEG Records.py | 200 | ✅ | Medium |
| Top TEGs and Rounds | 301Best_TEGs_and_Rounds.py | 152 | ✅ | Simple |
| Personal Bests | 302Personal Best Rounds & TEGs.py | 261 | ✅ | Medium |
| Final Round Comebacks | 303Final Round Comebacks.py | 326 | ✅ | Complex |

---

## Page: `300TEG Records.py`

**Title:** TEG Records (All-Time Records)
**Lines of Code:** 200
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Comprehensive all-time records display across five categories: TEG scores, Round scores, 9-Hole scores, Streaks (good and bad), and Score Counts. For each category, displays both best records and worst records showing extreme performances.

### Data Loading

- **Functions:**
  - `get_ranked_teg_data()` - Pre-ranked TEG data
  - `get_ranked_round_data()` - Pre-ranked round data
  - `get_ranked_frontback_data()` - Front 9 and back 9 data
  - `get_filtered_teg_data()` - Filtered dataset
  - `get_round_data()` - Round details
  - `get_9_data()` - 9-hole data
  - `load_all_data(exclude_teg_50=True)` - All tournament data
- **Files:** Multiple ranking datasets, all-scores.parquet
- **Key Parameters:** `exclude_teg_50=True` - Excludes practice TEG
- **Caching:** Yes (all loaders cached)

### Dependencies

**From utils.py:**
- `get_ranked_teg_data()` - Pre-ranked TEG scores
- `get_ranked_round_data()` - Pre-ranked round scores
- `get_ranked_frontback_data()` - Front/back 9 data
- `load_datawrapper_css()` - Table styling
- `get_round_data()` - Round details
- `get_9_data()` - 9-hole data
- `load_all_data(exclude_teg_50=True)` - Tournament data

**From helpers/display_helpers.py:**
- `prepare_records_table()` - Formats best records table
- `prepare_worst_records_table()` - Formats worst records table
- `prepare_streak_records_table()` - Formats streak records
- `prepare_score_count_records_table()` - Formats score count records

**From helpers/worst_performance_processing.py:**
- `get_filtered_teg_data()` - Gets filtered dataset

**From helpers/streak_analysis_processing.py:**
- `prepare_record_best_streaks_data()` - Best streaks
- `prepare_record_worst_streaks_data()` - Worst streaks

**Streamlit Components:**
- `st.tabs()` - 5 tabs for record categories
- `st.markdown()` - Display content
- `st.caption()` - Info text

### Embedded Logic

**Functions Defined:**
1. `dashed_line()` (lines 55-59)
   - Returns HTML `<hr>` element for visual separation
   - Purpose: Visual separator between best/worst records
   - Extraction candidate: No (trivial 2-line helper)

**Analysis:**
- Total embedded logic: ~5 lines
- Non-business logic: Pure HTML generation
- Extraction recommendation: Keep inline (minimal)

### User Interactions

**Widgets:**
- 5 tabs: TEG Records | Round Records | 9-Hole Records | Streaks | Score Counts
- Each tab shows best and worst records

**Session State:** None

### Display Components

**Charts:** None

**Tables:**
- Best records table (HTML formatted)
- Worst records table (HTML formatted)
- One pair per tab
- Visual separation with dashed line

**Layout:**
- Tab-based organization
- Best records, separator line, worst records per tab

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Loads CSS
- Custom separator with HTML hr element

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Consider adding export functionality - future feature
3. Add docstrings to imported helper functions - 0.5 hours

**Estimated Effort:** 0.5-1 hour (documentation only, optional)

**Blockers:** None

### Page-Specific Notes

- Well-structured with good helper usage
- Multiple data sources consolidated cleanly
- Tab organization works well for 5 record categories
- No technical debt identified
- Good model for record display pages

---

## Page: `301Best_TEGs_and_Rounds.py`

**Title:** Top TEGs and Rounds (Best & Worst Performances)
**Lines of Code:** 152
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Simple

### Purpose

Interactive exploration of top N best and worst performances for both complete TEGs and individual rounds. Users select a scoring measure (Gross, Stableford, etc.) and number N to see the top N best and worst performers. This provides a flexible records browser.

### Data Loading

- **Functions:**
  - `get_ranked_teg_data()` - Pre-ranked TEG data
  - `get_ranked_round_data()` - Pre-ranked round data
- **Files:** Ranked datasets via helpers
- **Key Parameters:** None (user selects measure and N)
- **Caching:** Yes (ranked data cached)

### Dependencies

**From utils.py:**
- `get_ranked_teg_data()` - Pre-ranked TEG data
- `get_ranked_round_data()` - Pre-ranked round data
- `load_datawrapper_css()` - Table styling

**From helpers/best_performance_processing.py:**
- `get_measure_name_mappings()` - Maps measure codes to display names
- `prepare_best_teg_table()` - Formats best TEG table
- `prepare_best_round_table()` - Formats best round table
- `prepare_worst_teg_table()` - Formats worst TEG table
- `prepare_worst_round_table()` - Formats worst round table
- `prepare_round_data_with_identifiers()` - Adds TEG/Round identifiers

**Streamlit Components:**
- `st.radio()` - Measure selection (Gross, Stableford, etc.)
- `st.number_input()` - Top N input
- `st.tabs()` - 4 tabs (Best TEGs/Rounds, Worst TEGs/Rounds)
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:** None

**Analysis:** All business logic successfully extracted to helpers. Page is pure orchestration.

### User Interactions

**Widgets:**
- Radio buttons: Measure selection (changes dynamically based on available measures)
- Number input: N (top N records to show)
- Tabs: Best TEGs | Best Rounds | Worst TEGs | Worst Rounds

**Session State:** None (simple controls)

### Display Components

**Charts:** None

**Tables:**
- 4 tables (one per tab): Best TEGs, Best Rounds, Worst TEGs, Worst Rounds
- Dynamic based on measure selection and N

**Layout:**
- Measure selector
- N input
- Tab-based table display

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Applied globally

### Migration Analysis

**Complexity:** Simple

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Consider adding caching refresh button - future feature
3. Documentation is good

**Estimated Effort:** 0 hours (no changes recommended)

**Blockers:** None

### Page-Specific Notes

- Clean and straightforward implementation
- Good model for interactive data exploration
- All logic properly extracted to helpers
- No technical debt
- User-friendly interface with clear controls

---

## Page: `302Personal Best Rounds & TEGs.py`

**Title:** Personal Bests (Per-Player Records)
**Lines of Code:** 261
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Each player's personal best and worst performances across TEGs, Rounds, and 9-holes with both summary view showing all measures at once and detailed measure-specific views. Users visit to understand individual player's best performances and compare to all-time records.

### Data Loading

- **Functions:**
  - `get_ranked_teg_data()` - Pre-ranked TEG data
  - `get_ranked_round_data()` - Pre-ranked round data
  - `get_ranked_frontback_data()` - Front/back 9 data
- **Files:** Ranked datasets via helpers
- **Key Parameters:** None
- **Caching:** Yes (ranked data cached)

### Dependencies

**From utils.py:**
- `get_ranked_teg_data()` - Pre-ranked TEG data
- `get_ranked_round_data()` - Pre-ranked round data
- `get_ranked_frontback_data()` - Front/back 9 data
- `load_datawrapper_css()` - Table styling

**From helpers/best_performance_processing.py:**
- `get_measure_name_mappings()` - Measure display names
- `prepare_personal_best_teg_table()` - Personal best TEGs
- `prepare_personal_best_round_table()` - Personal best rounds
- `prepare_personal_worst_teg_table()` - Personal worst TEGs
- `prepare_personal_worst_round_table()` - Personal worst rounds
- `prepare_round_data_with_identifiers()` - Round identifiers
- `prepare_pb_teg_summary_table()` - Summary across all measures (TEG)
- `prepare_pb_round_summary_table()` - Summary across all measures (Round)
- `prepare_pb_nine_summary_table()` - Summary for 9-holes

**Streamlit Components:**
- `st.tabs()` - 5 tabs (PB Summary, Best TEGs, Best Rounds, Worst TEGs, Worst Rounds)
- `st.segmented_control()` - View type selector (Summary/Best/Worst)
- `st.segmented_control()` - Measure selector (dynamically populated)
- `st.session_state` - Stores measure selection across tabs
- `st.rerun()` - Refresh on measure change

### Embedded Logic

**Functions Defined:** None

**Analysis:** All business logic extracted to helpers. Page handles complex session state management.

### User Interactions

**Widgets:**
- Tabs: 5 tabs for PB categories
  - Tab 0: PB Summary (all measures, one row per player)
  - Tabs 1-4: Best/Worst TEGs/Rounds (measure-specific detail)
- Segmented control: View type (Summary/Best/Worst) - updates tab focus
- Segmented control: Measure selector - synced across tabs via session state
- Tab switching with measure persistence

**Session State:**
- Current measure selection stored in st.session_state
- Synced across tab switches
- Uses st.rerun() when measure changes

### Display Components

**Charts:** None

**Tables:**
- Summary table (all measures, players as rows)
- Measure-specific tables (Best/Worst TEGs, Best/Worst Rounds per measure)

**Layout:**
- Segmented controls for navigation
- Tab-based detail view
- Dynamic based on selected measure

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Applied globally

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Consider extracting session state management pattern - 1 hour (creates session_state_utils)
3. Document complex state syncing - 0.5 hours

**Estimated Effort:** 1-2 hours (session state utility extraction, optional)

**Blockers:** Coordinate with latest_round.py and latest_teg_context.py if extracting session state pattern

### Page-Specific Notes

- Complex session state management works well
- Good example of measure selector pattern
- Tab syncing pattern could be reused elsewhere
- All helper functions well-organized
- No technical debt identified
- User interface is intuitive despite complexity

---

## Page: `303Final Round Comebacks.py`

**Title:** Final Round Comebacks (Dramatic Finishes)
**Lines of Code:** 326
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Complex

### Purpose

Analyzes dramatic final round performances showing: biggest score improvements (players who gained the most strokes in round 4), biggest declines (players who lost the most), leads lost after round 3 (trophy contenders who fell back in final round), leads lost during round 4 (biggest chokes), and biggest comebacks (players who came from behind in final round). Displays both gross and stableford views.

### Data Loading

- **Functions:**
  - `load_all_data(exclude_teg_50=True)` - Tournament data
  - `read_file('data/round_info.csv')` - Round course information
- **Files:** all-scores.parquet, round_info.csv
- **Key Parameters:** `exclude_teg_50=True` - Excludes practice TEG
- **Caching:** Yes (load_all_data cached)

### Dependencies

**From utils.py:**
- `load_all_data(exclude_teg_50=True)` - Tournament data
- `read_file()` - CSV loader
- `load_datawrapper_css()` - Table styling

**From helpers/comeback_analysis.py:**
- `calculate_final_round_differentials()` - Calculates score changes
- `calculate_biggest_leads_lost_after_r3()` - Leads lost analysis
- `calculate_biggest_leads_lost_in_r4()` - R4 leads lost analysis
- `calculate_biggest_comebacks()` - Comeback calculation

**Streamlit Components:**
- `st.radio()` - Competition selection (Gross vs Stableford)
- `st.number_input()` - Records to show (top N)
- `st.markdown()` - Display content
- `st.caption()` - Info text

### Embedded Logic

**Functions Defined:** None

**Analysis:** All complex analysis logic extracted to comeback_analysis.py helper. Page is pure orchestration.

### User Interactions

**Widgets:**
- Radio buttons: Competition type
  - Gross (Trophy competition)
  - Stableford (Green Jacket net competition)
- Number input: Number of records to display (1-50)
- 4 sections: Biggest Improvements | Biggest Declines | Leads Lost After R3 | Leads Lost in R4 | Biggest Comebacks

**Session State:** None

### Display Components

**Charts:** None

**Tables:**
- 5 separate analysis sections with HTML tables
- Dynamic row count based on user input
- Different metrics per section

**Layout:**
- Competition and N selectors at top
- 5 sections with dividers
- Each section: title + description + table

### CSS/Styling

- `datawrapper_table()` - Standard table CSS
- `load_datawrapper_css()` - Applied globally
- HTML `<hr>` elements for section dividers

### Migration Analysis

**Complexity:** Complex

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Helper functions need docstrings - 1 hour
3. Verify rank calculation edge cases - 2 hours (testing)
4. Consider visualization enhancement (optional) - future feature

**Estimated Effort:** 2-3 hours (testing + documentation)

**Blockers:**
- Need to verify rank calculations with edge cases
- Test with small datasets to ensure calculations are correct

### Page-Specific Notes

- Complex analysis logic properly encapsulated in helpers
- Handles gross vs stableford competition difference elegantly
- Interesting use cases:
  - Biggest improvements/declines show volatility
  - Leads lost show choke potential
  - Comebacks show resilience
- Good candidate for data visualization enhancement
- Currently text-based, could benefit from charts

---

## Section Summary

### Refactoring Status
- ✅ All 4 pages fully refactored and following standard template
- Complex analysis logic well-extracted to helpers
- Clear separation between analysis and presentation

### Reusable Patterns
1. **Measure Selection Pattern** - Used by 301 and 302
   - Could be extracted to utility
   - Handles dynamic measure mapping

2. **Session State Sync Pattern** - Used by 302
   - Persists selection across tab switches
   - Could be templated for other pages

3. **Top-N Selection Pattern** - Used by 301
   - Flexible record browsing
   - Could be applied to other listing pages

### Common Dependencies
- All use `get_ranked_*_data()` pre-ranked datasets
- All use `load_datawrapper_css()` styling
- All use helpers/best_performance_processing.py or comeback_analysis.py

### Testing Priorities
- **303Final Round Comebacks**: Verify ranking calculations with edge cases
- **302Personal Best**: Test session state sync across tabs
- **301/300**: Verify measure mapping and dynamic updates
- All: CSS styling on different screen sizes

### Extraction Opportunities
1. **Medium Priority**: Extract measure selection pattern (utility function) - 1 hour
2. **Medium Priority**: Extract session state sync pattern - 1 hour
3. **Low Priority**: Add docstrings to comeback_analysis functions - 1 hour

### Total Effort to Refactor This Section
- Complete refactoring: 0 hours (already done ✅)
- Pattern extraction (optional): 2-3 hours
- Testing + documentation: 3-4 hours
- **Total: 3-7 hours (mostly optional improvements)**
