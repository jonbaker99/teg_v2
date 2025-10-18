# TASK 1: Utils.py Complete Function Inventory

**Assigned To:** Subagent 1 / Manual Documentation
**Priority:** 🔴 CRITICAL (blocks all other work)
**Estimated Time:** 4-6 hours
**Status:** ⏳ NOT STARTED

---

## Objective

Create a complete, exhaustive inventory of every function in `streamlit/utils.py`, including:
- Function signature
- Purpose/description
- Parameters and return types
- Dependencies (external packages, internal functions, Streamlit usage)
- Which pages/files use this function
- Whether it's pure/UI/IO/mixed
- Migration target recommendation
- Line count

---

## Instructions

For EVERY function in utils.py, fill out this template:

### Function Template

```markdown
### `function_name(param1, param2, param3=default)`

**Line Numbers:** 45-67
**Function Type:** PURE | UI | IO | MIXED
**Complexity:** Simple | Medium | Complex

**Purpose:**
Brief 1-2 sentence description of what this function does.

**Full Signature:**
```python
def function_name(
    param1: type,
    param2: type,
    param3: type = default_value
) -> return_type:
    """Docstring if exists"""
```

**Parameters:**
- `param1` (type): Description
- `param2` (type): Description  
- `param3` (type, optional): Description. Defaults to X.

**Returns:**
- return_type: Description of return value

**Dependencies:**
- **External Packages:** pandas, numpy, streamlit
- **Internal Functions:** other_function_from_utils(), helper_function()
- **Streamlit-Specific:** Yes/No - (if yes, list st.* calls)
- **File I/O:** Yes/No - (reads/writes files)

**Used By (import analysis):**
- streamlit/pages/400scoring.py (line 15)
- streamlit/pages/streaks.py (line 22)
- streamlit/helpers/display_helpers.py (line 8)
[Use grep/search to find all imports]

**Similar/Duplicate Functions:**
- helpers/scoring_data_processing.format_value() - POSSIBLE DUPLICATE
- None identified

**Migration Recommendation:**
- **Target Module:** teg_analysis/analysis/scoring.py
- **Rationale:** Pure calculation, no UI dependencies
- **Priority:** 🔴 HIGH - Used by 15+ pages
- **Breaking Changes:** Will require import updates in N files

**Notes:**
Any special considerations, edge cases, or technical debt.
```

---

## Expected Output Structure

Group functions by logical sections as they appear in utils.py:

## Section 1: Configuration & Setup (Lines X-Y)
### `get_page_layout()`
[Full documentation]

### `clear_all_caches()`
[Full documentation]

## Section 2: Constants & Path Management (Lines X-Y)
[Document constants]

## Section 3: Data Loading Functions (Lines X-Y)
### `read_from_github()`
[Full documentation]

### `load_all_data()`
[Full documentation]

## Section 4: Data Writing Functions (Lines X-Y)
[Continue for ALL sections]

---

## Checklist

- [ ] Read through entire utils.py file
- [ ] Identify all logical sections
- [ ] Document every function (no exceptions)
- [ ] Document all constants/globals
- [ ] Run dependency analysis (grep for imports)
- [ ] Identify duplicates across codebase
- [ ] Categorize each function (PURE/UI/IO/MIXED)
- [ ] Recommend migration targets
- [ ] Calculate line counts
- [ ] Note any deprecated/unused functions

---

## Tools/Commands to Help

### Find all imports of a function
```bash
grep -r "from utils import.*function_name" streamlit/
grep -r "utils.function_name" streamlit/
```

### Count function lines
```python
# In Python
def count_function_lines(file_path, function_name):
    # Implementation to count lines
```

### List all functions
```bash
grep "^def " streamlit/utils.py
```

---

## Output File

Save completed inventory to: `UTILS_INVENTORY.md`

**Format:** Markdown with consistent structure
**Length:** Expected 50-100 functions = 200-400 pages of documentation

---

## Success Criteria

- ✅ Every function documented
- ✅ Every constant documented
- ✅ All dependencies identified
- ✅ All usage sites found
- ✅ Migration targets recommended
- ✅ Duplicates flagged
- ✅ Ready for migration planning
