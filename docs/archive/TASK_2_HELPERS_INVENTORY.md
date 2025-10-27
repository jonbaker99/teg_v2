# TASK 2: Helper Modules Complete Inventory

**Assigned To:** Subagent 2 / Manual Documentation
**Priority:** 🔴 CRITICAL
**Estimated Time:** 3-4 hours
**Status:** ⏳ NOT STARTED

---

## Objective

Document every helper module in `streamlit/helpers/` directory, including:
- All functions with complete signatures
- Purpose and dependencies
- Usage analysis
- Migration recommendations

---

## Known Helper Modules

Based on project knowledge, these helper modules exist:

1. ✅ `__init__.py` - Package initialization
2. 🚧 `scoring_data_processing.py` - Scoring calculations
3. 🚧 `scoring_achievements_processing.py` - Eagles/birdies/pars
4. 🚧 `streak_analysis_processing.py` - Streak calculations
5. 🚧 `score_count_processing.py` - Score distribution
6. 🚧 `display_helpers.py` - Display formatting
7. 🚧 `latest_round_processing.py` - Current tournament
8. 🚧 `data_update_processing.py` - Data updates
9. 🚧 `data_deletion_processing.py` - Data deletion
10. 🚧 `commentary_generator.py` - Report generation
11. ❓ [Others - need to list all]

---

## Instructions

For EACH helper module:

### Module Template

```markdown
## Module: `helpers/module_name.py`

**Lines of Code:** XXX
**Purpose:** One paragraph overview
**Created/Refactored:** Date if known
**Status:** ✅ Well organized | ⚠️ Needs work | ❌ Messy

### Module-Level Information

**Imports:**
- External: pandas, numpy, etc.
- Internal: from utils import x, y, z
- Streamlit: Yes/No

**Used By (pages):**
- 400scoring.py
- streaks.py
- [All pages that import this module]

**Dependencies ON Other Helpers:**
- helpers/display_helpers.py
- [Any helper-to-helper dependencies]

---

### Functions in This Module

#### Function 1: `function_name()`

**Line Numbers:** 10-25
**Type:** PURE | UI | IO | MIXED

**Signature:**
```python
def function_name(param1: type, param2: type) -> return_type:
    """Docstring"""
```

**Purpose:**
What does this function do?

**Parameters:**
- param1 (type): Description
- param2 (type): Description

**Returns:**
- return_type: Description

**Dependencies:**
- External: pandas.groupby()
- Internal: helper_function()
- Streamlit: No

**Complexity:** Simple/Medium/Complex

**Migration Target:** teg_analysis/analysis/module.py
**Priority:** 🔴/🟡/🟢

**Notes:**
Special considerations

---

#### Function 2: [Continue for all functions]

---

### Module Analysis

**Summary:**
- Total Functions: X
- Pure Functions: Y (can migrate easily)
- Mixed Functions: Z (need splitting)
- Streamlit-Dependent: W (stay in streamlit/)

**Migration Plan:**
- Functions 1-5 → teg_analysis/analysis/scoring.py
- Functions 6-7 → Need splitting
- Function 8 → Stay in streamlit_utils.py

**Duplicates Identified:**
- function_x() similar to utils.function_y()
```

---

## Module Priority Order

Document in this order (most critical first):

### Priority 1: Core Analysis Helpers ✅
1. scoring_data_processing.py
2. scoring_achievements_processing.py
3. streak_analysis_processing.py
4. score_count_processing.py

### Priority 2: Support Helpers 🟡
5. display_helpers.py
6. latest_round_processing.py

### Priority 3: Administrative Helpers 🟢
7. data_update_processing.py
8. data_deletion_processing.py
9. commentary_generator.py

---

## Analysis Questions for Each Module

Answer these for each helper:

1. **Is this module pure (no Streamlit dependencies)?**
   - Yes → Easy migration candidate
   - No → Needs splitting

2. **Does this module have clear domain focus?**
   - Yes → Maps to single teg_analysis module
   - No → Needs refactoring first

3. **Are there duplicates with utils.py?**
   - Document all duplicates

4. **How many pages use this module?**
   - High usage → High priority migration

5. **Is the module well-organized?**
   - Yes → Can migrate as-is
   - No → Needs internal cleanup

---

## Tools/Commands

### List all helper modules
```bash
ls -la streamlit/helpers/
```

### Find who imports a helper
```bash
grep -r "from helpers.module_name import" streamlit/
grep -r "import helpers.module_name" streamlit/
```

### Count lines in a module
```bash
wc -l streamlit/helpers/module_name.py
```

### Check for Streamlit dependencies
```bash
grep "import streamlit" streamlit/helpers/*.py
grep "st\." streamlit/helpers/*.py
```

---

## Output File

Save to: `HELPERS_INVENTORY.md`

---

## Success Criteria

- ✅ All helper modules documented
- ✅ All functions categorized
- ✅ Dependencies mapped
- ✅ Migration targets identified
- ✅ Duplicates with utils.py noted
- ✅ Priority recommendations made
