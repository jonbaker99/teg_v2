# TASK 3: Streamlit Pages Complete Inventory

**Assigned To:** Subagent 3 / Manual Documentation
**Priority:** 🟡 HIGH
**Estimated Time:** 4-5 hours
**Status:** ⏳ NOT STARTED

---

## Objective

Document every Streamlit page file, focusing on:
- What each page does
- What data it loads and how
- What helper functions it uses
- What calculations are embedded in the page
- Migration complexity

---

## Page Inventory Template

For each page file, complete this analysis:

```markdown
## Page: `filename.py`

**Section:** History | Records | Analysis | Latest | Data
**Title:** Display name
**Icon:** Emoji if any
**Layout:** Wide | Centered
**Lines of Code:** XXX
**Refactoring Status:** ✅ Refactored | 🚧 In Progress | ⏳ Not Started

### Page Purpose

One paragraph describing what this page displays and why users would visit it.

### Data Loading

**Primary Data Sources:**
```python
data = load_all_data(exclude_incomplete_tegs=True)
scoring_stats = score_type_stats()
```

**Parameters:**
- exclude_incomplete_tegs: True/False - Why?
- exclude_teg_50: True/False - Why?

**Data Files:**
- all-scores.parquet
- streaks.parquet
- [Others]

### Dependencies Analysis

**From utils.py:**
- load_all_data()
- score_type_stats()
- load_datawrapper_css()
- [Complete list]

**From helpers/:**
- helpers.scoring_data_processing.format_vs_par_value()
- [Complete list]

**From other modules:**
- make_charts.create_round_graph()
- [Complete list]

**Streamlit Components Used:**
- st.selectbox()
- st.dataframe()
- st.altair_chart()
- [Complete list]

### Embedded Calculations

**Functions Defined in Page:**
```python
def calculate_something(data):
    # Lines 45-67
    # Should this be extracted?
```

**Analysis:**
- Lines of embedded logic: XX
- Should be extracted: Yes/No
- Extraction target: teg_analysis/analysis/module.py

### User Interactions

**Widgets:**
- Dropdown for TEG selection
- Radio buttons for metric selection
- [All interactive elements]

**Session State:**
- session_state variables used: [list]

### Display Components

**Charts:**
- Chart type 1 (Altair bar chart)
- Chart type 2 (Line graph)

**Tables:**
- Dataframe 1 (formatted with X)
- Table 2 (HTML table)

**CSS/Styling:**
- stylesheet.css
- navigation.css
- [All style dependencies]

### Migration Analysis

**Complexity Score:** Simple | Medium | Complex

**Migration Tasks:**
1. Extract embedded calculation to teg_analysis
2. Update imports from utils → teg_analysis
3. Keep UI orchestration in page
4. Update CSS loading to streamlit_utils

**Estimated Effort:** X hours

**Blockers:**
- Depends on utils.function_x being migrated first
- [Any dependencies]

### Page-Specific Notes

- Special features
- Known issues
- Technical debt
- Refactoring notes
```

---

## Page Categories

Document pages by category:

### History Section
1. `101TEG History.py` - ✅ Refactored
2. `101TEG Honours Board.py`
3. `102TEG Results.py` - ✅ Refactored
4. `103Cumulative Results.py`

### Records Section
5. `300TEG Records.py` - ✅ Refactored
6. `301Best_TEGs_and_Rounds.py`
7. `302Personal Best Rounds & TEGs.py`

### Analysis Section
8. `400scoring.py` - ✅ Refactored
9. `ave_by_course.py`
10. `ave_by_par.py`
11. `bestball.py`
12. `biggest_changes.py`
13. `sc_count.py`
14. `streaks.py` - ✅ Refactored
15. `teg_worsts.py`

### Latest Section (Current Tournament)
16. `latest_round.py`
17. `latest_teg_context.py`
18. `birdies_etc.py`
19. `scorecard_v2.py` - ✅ Refactored

### Data Section (Admin)
20. `1000Data update.py` - ✅ Refactored
21. `delete_data.py`
22. `500Handicaps.py`
23. [Others?]

### Special Pages
24. `main.py` - Entry point
25. `contents.py` - Site map
26. `navigation_test.py` - Testing
27. [Others?]

---

## Analysis Questions

For each page, answer:

1. **Is this page refactored per template?**
   - Check against REFACTORING_TEMPLATE.md

2. **How much business logic is embedded?**
   - Count lines of non-UI code

3. **What's the migration complexity?**
   - Simple: Mostly UI, uses existing functions
   - Medium: Some embedded logic to extract
   - Complex: Heavy calculations, multiple data sources

4. **Are there page-specific functions that should be in helpers?**
   - List candidates for extraction

5. **What are the unique features?**
   - Complex interactions, special displays, etc.

---

## Refactored vs Unrefactored

### Already Refactored ✅
Track which pages follow the template:
- 300TEG Records.py
- 102TEG Results.py
- 400scoring.py
- 1000Data update.py
- 101TEG History.py
- scorecard_v2.py

**Common Pattern:**
```python
# === IMPORTS ===
# === CONFIGURATION ===
# === DATA LOADING ===
# === USER INTERFACE ===
```

### Not Refactored ⏳
Remaining pages - need to document current state before refactoring

---

## Embedded Logic Extraction

Look for patterns like:

```python
# IN PAGE FILE - SHOULD BE EXTRACTED
def calculate_something(data):
    result = data.groupby('Player').agg({
        'Score': 'mean',
        'Rounds': 'count'
    })
    return result

# Then used in page:
stats = calculate_something(all_data)
st.dataframe(stats)
```

**Document:**
- Function name
- Lines of code
- Extraction target
- Priority

---

## Tools/Commands

### List all page files
```bash
ls streamlit/*.py
ls streamlit/pages/*.py  # If multipage structure
```

### Count lines in pages
```bash
wc -l streamlit/*.py | sort -n
```

### Find embedded function definitions
```bash
grep "^def " streamlit/*.py
```

### Check refactoring status
```bash
grep "# === IMPORTS ===" streamlit/*.py
```

### Find data loading patterns
```bash
grep "load_all_data" streamlit/*.py
grep "exclude_incomplete" streamlit/*.py
```

---

## Output File

Save to: `PAGES_INVENTORY.md`

---

## Summary Statistics to Include

At the end of the inventory, provide:

- Total pages: XX
- Refactored: XX
- Not refactored: XX
- Simple migrations: XX
- Medium migrations: XX
- Complex migrations: XX
- Total embedded functions: XX
- Average lines per page: XX
- Most complex page: filename.py (XXX lines)
- Most dependencies: filename.py (XX imports)

---

## Success Criteria

- ✅ All page files documented
- ✅ All dependencies mapped
- ✅ Embedded logic identified
- ✅ Migration complexity assessed
- ✅ Ready for refactoring prioritization
