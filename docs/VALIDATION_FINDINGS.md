# Grep Validation Findings - Critical Discovery

**Date:** 2025-10-19
**Status:** CRITICAL BUG FOUND in AST analysis

---

## IMPORTANT: Call Graph Bug Discovered

During sample grep validation of unused candidates, discovered that **`compress_ranges`** was flagged as unused by AST analysis BUT is actually used!

### Evidence

**AST Analysis Result:**
- `compress_ranges` in `streamlit/utils_win_tables.py:50` flagged as UNUSED

**Grep Validation Result:**
```
streamlit/101TEG Honours Board.py:21:from utils_win_tables import summarise_teg_wins, compress_ranges
streamlit/101TEG Honours Board.py:90:summary_table['TEGs'] = summary_table['TEGs'].apply(compress_ranges, out_sep=", ")
```

**Actual Usage:** Function IS imported and called in "101TEG Honours Board.py"

### Root Cause Analysis

The issue is NOT with entry point detection (Honours Board WAS included as entry point). The bug is in the **call graph building** - specifically:

1. AST `FunctionCallExtractor` correctly finds the call: `compress_ranges(...)`
2. BUT the call graph builder maps this to caller function (the function INSIDE Honours Board that calls it)
3. Forward trace starts from functions in entry point files
4. HOWEVER, if `compress_ranges` is called via `.apply()` method, the AST might see it as:
   - `summary_table['TEGs'].apply(compress_ranges, ...)`
   - Which looks like passing `compress_ranges` as an ARGUMENT, not CALLING it directly
5. Our current AST visitor only catches `Call` nodes, NOT function references passed as arguments!

### Implication

**THE AST ANALYSIS HAS FALSE POSITIVES!**

This means some of the 46 "unused" functions are actually used but passed as callbacks/arguments rather than called directly.

Common Python patterns that would be missed:
- `df.apply(function_name)`
- `sorted(list, key=function_name)`
- `map(function_name, iterable)`
- `filter(function_name, iterable)`
- `st.button("Click", on_click=function_name)`
- Decorator patterns
- Registry patterns

---

## Next Steps (CRITICAL)

### 1. Fix AST Analysis Script
Need to enhance `ScopedFunctionCallExtractor` to catch:
- Function names used as arguments (ast.Name nodes in Call arguments)
- Function names in keyword arguments
- Function references without parentheses

### 2. Re-run Analysis
After fixing the script, must re-run the entire analysis to get accurate results.

### 3. Grep Validation is ESSENTIAL
This proves that grep validation is NOT optional - it's required to catch AST analysis bugs.

---

## Sample Validation Results (3 candidates checked)

| Function | File | Grep Result | Confidence | Status |
|----------|------|-------------|------------|--------|
| `prepare_records_display` | helpers/display_helpers.py:38 | Only definition found, 0 calls | HIGH | Likely unused ✓ |
| `load_records_page_css` | helpers/records_css.py:10 | Only definition found, 0 calls | HIGH | Likely unused ✓ |
| `compress_ranges` | utils_win_tables.py:50 | **3 calls found** | FALSE POSITIVE | **USED** ✗ |

**Accuracy:** 2/3 correct (66%) - **NOT ACCEPTABLE**

---

## Recommendation

**DO NOT proceed with current analysis results.**

Must fix the AST analysis to catch function-as-argument patterns before generating final report. This is exactly why the "NO SHORTCUTS" principle is critical.

---

## Learning

This validates the user's original concern: **Taking shortcuts leads to errors.**

The first analysis failed because I made assumptions. The second analysis is failing because the AST visitor doesn't handle all Python calling patterns. Only through rigorous grep validation did we discover this.

**Next session MUST:**
1. Fix the AST extractor to catch function references
2. Re-run analysis
3. Grep-validate ALL candidates
4. Only then generate final report

---

**Last Updated:** 2025-10-19
**Critical Issue:** AST analysis has false positives - DO NOT USE until fixed
