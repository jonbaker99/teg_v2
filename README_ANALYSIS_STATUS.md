# Analysis Scripts Status - READ BEFORE USE

**Last Updated:** 2025-10-19

---

## ⚠️ CRITICAL: Do Not Use These Files

### Unreliable Analysis Results

**Files with KNOWN BUGS - DO NOT USE:**

1. **`analyze_unused_code.py`** - ⚠️ HAS BUG
   - Status: Incomplete AST extractor
   - Issue: Misses function-as-argument patterns
   - Output: `unused_code_analysis.json` - **UNRELIABLE**

2. **`analyze_unused_refined.py`** - ⚠️ HAS BUG
   - Status: Incomplete AST extractor
   - Issue: Misses function-as-argument patterns (df.apply, callbacks, etc.)
   - Output: `unused_code_analysis_refined.json` - **UNRELIABLE**
   - **Known false positive:** `compress_ranges` flagged as unused but actually used

3. **`validate_unused.py`** - ⚠️ ENCODING ISSUES
   - Status: Windows encoding errors with findstr
   - Issue: UnicodeDecodeError on binary file content
   - Recommendation: Use Grep tool instead

### What Went Wrong

**Discovery:** During grep validation, found that `compress_ranges` was:
- Flagged as UNUSED by AST analysis
- Actually IS used via `summary_table['TEGs'].apply(compress_ranges, ...)`

**Root Cause:** AST visitor only catches `Call` nodes (direct calls like `foo()`), but misses:
- Function references passed as arguments: `df.apply(func)`
- Callback functions: `st.button(on_click=func)`
- Key functions: `sorted(list, key=func)`
- Map/filter: `map(func, iterable)`
- Any function reference without parentheses

**Impact:** Unknown number of false positives in current 46 "unused" candidates

---

## ✅ Reliable Analysis Results

**Files that CAN be used:**

1. **`analyze_dependencies.py`** - ✅ RELIABLE
   - Status: Complete and validated
   - Output: `dependency_graph.json`, `docs/DEPENDENCIES.md`

2. **`analyze_function_duplicates.py`** - ✅ RELIABLE
   - Status: Complete and validated
   - Output: `function_analysis.json`, `docs/DUPLICATES.md`

3. **`analyze_patterns.py`** - ✅ RELIABLE
   - Status: Complete and validated
   - Output: Various inventory files in `docs/inventory/`

---

## What's Next

### Required Before Unused Code Analysis Can Be Trusted

1. **Fix AST Extractor** (PENDING)
   - Add visitor for `ast.Name` nodes in function arguments
   - Track function references (not just calls)
   - Handle keyword arguments with function values

2. **Re-run Analysis** (PENDING)
   - Use fixed script on active codebase
   - Generate new candidate list

3. **Grep-Validate ALL Candidates** (PENDING)
   - Use Grep tool for each candidate
   - Assign confidence levels: HIGH/MEDIUM/LOW
   - Document usage examples

4. **Manual Review** (PENDING)
   - Review edge cases (decorators, registries, dynamic imports)
   - Cross-reference with DEPENDENCIES.md
   - Verify no commonly-used patterns missed

5. **Generate Final Report** (PENDING - ONLY AFTER STEPS 1-4)

---

## Session Progress Tracking

**Session 1 (2025-10-19):**
- ✅ Created AST analysis scripts
- ✅ Analyzed 505 functions in active codebase
- ✅ Started grep validation
- ⚠️ **Discovered critical bug** - AST misses function-as-argument patterns
- ❌ Cannot proceed with current results

**Session 2 (PENDING):**
- Fix AST extractor
- Re-run analysis
- Complete validation
- Generate final report

---

## How to Know When Analysis is Reliable

**Checklist before using unused code analysis results:**

- [ ] AST extractor fixed to catch function references
- [ ] Analysis re-run with fixed script
- [ ] All candidates grep-validated (not just sampled)
- [ ] Confidence levels assigned to each candidate
- [ ] Manual review of edge cases completed
- [ ] Results documented in `docs/analysis/UNUSED_CODE_REPORT.md`
- [ ] Report explicitly marked as "VALIDATED AND RELIABLE"

**Until ALL boxes checked:** DO NOT archive any code based on these results.

---

## Documentation Files

**Progress Tracking:**
- `docs/UNUSED_CODE_AST_ANALYSIS_SESSION1.md` - Session 1 detailed progress
- `docs/VALIDATION_FINDINGS.md` - Critical bug discovery details
- `README_ANALYSIS_STATUS.md` - This file (status dashboard)

**When Complete (not yet):**
- `docs/analysis/UNUSED_CODE_REPORT.md` - Final validated report
- `docs/analysis/ANALYSIS_SUMMARY.md` - Quick reference

---

## Key Lesson

**NO SHORTCUTS works:**
- First attempt (guessing) → User caught errors → Deleted
- Second attempt (AST only) → Grep validation caught bugs → Must fix
- Third attempt (AST + grep + validation) → Will be reliable

**Trust the process. Rigor prevents mistakes.**

---

**Status:** Analysis in progress - DO NOT USE current results
**Next Update:** After Session 2 when AST is fixed and validation complete
