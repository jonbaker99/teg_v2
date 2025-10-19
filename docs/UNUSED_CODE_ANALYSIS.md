# Unused Code Identification Task

## Objective
Identify all functions, classes, and code elements that are NOT traceable back to active Streamlit pages defined in `streamlit/page_config.py`.

## Pre-Analysis: Leverage Existing Documentation ⚡

**CRITICAL:** This project has extensive documentation already completed. **DO NOT recreate work from scratch.**

### Required Reading Before Starting:
1. **`docs/README.md`** - Overview of documentation structure
2. **`docs/DEPENDENCIES.md`** (26 KB) - Complete dependency map already exists!
3. **`docs/MASTER_DOCUMENTATION_GUIDE.md`** - Context on what's been analyzed

### Available Resources to Use:
- **`docs/inventory/UTILS_INVENTORY_MASTER.md`** - All 102 utils.py functions catalogued
- **`docs/HELPERS_INVENTORY_SUMMARY.md`** - All 20 helper modules documented
- **`docs/HELPERS_INVENTORY_*.md`** - Detailed helper module breakdowns
- **`docs/PAGES_INVENTORY_00_SUMMARY.md`** - All 40 pages catalogued
- **`docs/PAGES_INVENTORY_*.md`** - Detailed page breakdowns
- **`docs/DUPLICATES.md`** - Known duplicate functions
- **`docs/function_analysis.json`** - Machine-readable function data

### How to Use Existing Documentation:
- **DEPENDENCIES.md** contains the dependency graph → validate your findings against it
- **Inventory files** list all functions → use as your "defined functions" checklist
- **DUPLICATES.md** shows known duplicates → cross-reference with unused findings
- **Don't re-analyze** what's already documented → build upon existing work

---

## Approach

### Methodology: Forward Trace (Recommended)

**Why Forward > Reverse?**

We use **forward tracing** (from pages outward) rather than **reverse tracing** (from functions backward) because:

#### Forward Trace Efficiency:
- **Start:** 40 pages → **Expand:** ~500 used functions
- **Complexity:** O(pages × depth × fan-out) ≈ 3,000 operations
- **Build once, check many** - Create one "used" set, then simple membership checks
- **Natural traversal** - Follows imports the way code actually executes
- **Incremental** - Accumulate "used" set as you discover dependencies

```
page_config.py (40 active pages)
  ↓ trace imports
  ↓ trace function calls  
  ↓ recursively expand dependencies
BUILD SET: {all reachable code} (~500 items)
RESULT: defined (530) - used (500) = unused (30)
```

#### Reverse Trace Drawbacks:
- **Start:** 530 functions → **Check each:** Has path to ANY page?
- **Complexity:** O(functions × importers × depth) - potentially much larger
- **Repeated work** - Multiple functions import same things (redundant tracing)
- **Dead ends** - Unused functions waste effort searching for non-existent paths
- **Harder to implement** - "Who imports me?" is less natural than "What do I import?"

#### Hybrid Validation (Best Practice):
1. **Forward trace** to build "used" set (efficient primary method)
2. **Spot-check reverse** for 5-10 "unused" candidates (validation)
3. **Cross-reference** with DEPENDENCIES.md (verify against existing work)

This gives confidence the analysis is accurate.

---

### 1. Map Active Entry Points
- Start with `streamlit/page_config.py` 
- Identify ALL pages that are actually registered/enabled
- Note which pages are commented out or disabled
- **Cross-check** against `docs/PAGES_INVENTORY_00_SUMMARY.md` (40 pages documented)

### 2. Build Dependency Tree (Forward Trace)
For each active page:
- Trace all imports and function calls
- Build a comprehensive tree of used functions/classes
- Include multi-level dependencies (functions that call functions that call functions, etc.)
- **Validate** against `docs/DEPENDENCIES.md` - this should match!
- **Depth:** Typically 3-5 levels deep
- **Breadth:** ~10-20 functions per level

### 3. Identify Unused Code
Compare all functions/classes in the codebase against the dependency tree:
- Functions/classes NOT in any active page's dependency tree = potentially unused
- Use inventory files as your "defined functions" checklist:
  - `docs/inventory/UTILS_INVENTORY_MASTER.md` - 102 functions
  - `docs/HELPERS_INVENTORY_*.md` - 173 functions across helpers
  - `docs/PAGES_INVENTORY_*.md` - Page-level functions
- Cross-reference against:
  - Utility functions that might be called indirectly
  - Configuration files
  - Data processing pipelines
  - Background jobs or scheduled tasks

### 4. Validate Findings (Hybrid Approach)
Before finalizing:
- **Spot-check reverse trace** for 5-10 "unused" functions (verify they truly have no path back)
- **Cross-reference** with DEPENDENCIES.md (does your "used" set match the documented dependencies?)
- **Check DUPLICATES.md** (are "unused" functions actually duplicates of used ones?)
- **Verify** no false positives

### 5. Document Findings
Create a report: `docs/analysis/UNUSED_CODE_REPORT.md`

---

## Output Format

```markdown
# Unused Code Analysis Report

**Analysis Date:** YYYY-MM-DD
**Method:** Forward trace from `streamlit/page_config.py` with validation against existing documentation

## Summary
- Total functions analyzed: X
- Used functions: Y
- Unused functions: Z
- Uncertainty cases: N
- Documentation sources: DEPENDENCIES.md, inventory files, DUPLICATES.md

## Validation
- ✓ Cross-referenced with docs/DEPENDENCIES.md
- ✓ Validated against docs/inventory/*.md
- ✓ Spot-checked 5+ unused functions with reverse trace
- ✓ Compared with docs/DUPLICATES.md

## Active Pages
List of pages from page_config.py that are currently enabled:
- page1.py
- page2.py
...

## Unused Code

### Module: [module_name]
**File**: `path/to/file.py`
**Inventory Reference**: docs/inventory/[relevant_file].md

#### Unused Functions:
- `function_name()` - Line X
  - Description: [what it does]
  - Last apparent use case: [if evident from comments/context]
  - Confidence: HIGH/MEDIUM/LOW
  - Note: [any relevant context from inventory docs]

#### Unused Classes:
- `ClassName` - Line X
  - Description: [what it does]
  - Confidence: HIGH/MEDIUM/LOW

## Uncertain Cases
Functions that might be used but the analysis couldn't confirm:
- `function_name()` in `file.py`
  - Reason for uncertainty: [e.g., dynamic imports, string-based calls]
  - Inventory notes: [context from docs]

## Cross-Reference with Known Issues
Compare findings with:
- Duplicates from docs/DUPLICATES.md
- Dependencies from docs/DEPENDENCIES.md
- Any discrepancies noted

## Recommendations
- Archive candidates: [list functions safe to archive]
- Needs review: [list functions that need human review before archival]
- Potential duplicates: [cross-reference with DUPLICATES.md]
```

---

## Analysis Rules

### HIGH Confidence Unused
- Function/class defined but never imported anywhere
- Imported but never called in any active code path
- Only used in disabled/commented pages
- **AND** validated with reverse trace spot-check

### MEDIUM Confidence Unused  
- Used only in test files (if tests are outdated)
- Used in utility scripts outside main app flow
- Apparent duplicate functionality
- Mentioned in inventory but no clear usage path

### LOW Confidence / Uncertain
- Functions with string-based names (might be called dynamically)
- Functions in files with partial usage
- Decorator functions or metaclasses
- Functions potentially used by external systems
- Discrepancy between your analysis and DEPENDENCIES.md

---

## Special Considerations

1. **Don't mark as unused:**
   - Streamlit page functions (even if seemingly simple wrappers)
   - Database initialization/migration functions
   - Configuration loaders
   - Error handlers and validators
   - Public API endpoints
   - Functions referenced in existing documentation as "critical"

2. **Trace carefully:**
   - Callback functions passed as arguments
   - Functions stored in dictionaries/registries
   - Methods called via inheritance
   - Functions used in config files as strings

3. **Context matters:**
   - Check git history for when function was last modified
   - Look for TODO/FIXME comments indicating future use
   - Consider if function is part of incomplete feature
   - Review inventory documentation for function purpose

4. **When in doubt:**
   - Check DEPENDENCIES.md to see if it's mentioned
   - Look in inventory files for usage notes
   - Mark as UNCERTAIN rather than UNUSED

---

## Execution Steps

### Phase 1: Preparation (5 minutes)
1. Read `docs/README.md` for context
2. Skim `docs/DEPENDENCIES.md` to understand existing dependency map
3. Review `docs/MASTER_DOCUMENTATION_GUIDE.md` for project overview
4. Note the 530 total functions documented

### Phase 2: Forward Trace (Main Analysis - 15-20 minutes)
5. Read `streamlit/page_config.py` to identify active pages
6. For each active page, recursively trace all dependencies (forward)
7. Build master list of "used" code (should be ~500 functions)
8. Scan all Python files to find "defined" code (use inventory files as checklist)
9. Compare: defined - used = potentially unused

### Phase 3: Validation (10 minutes)
10. Cross-reference your "used" set with DEPENDENCIES.md (should mostly match)
11. Spot-check 5-10 "unused" functions with reverse trace (verify they're truly unreachable)
12. Check DUPLICATES.md (are unused functions duplicates of used ones?)
13. Apply confidence levels based on rules above

### Phase 4: Documentation (10 minutes)
14. Generate report at `docs/analysis/UNUSED_CODE_REPORT.md`
15. Include validation notes
16. Cross-reference with existing documentation
17. **DO NOT DELETE OR MOVE ANY CODE** - only document findings

**Total Time Estimate:** 40-50 minutes for thorough analysis

---

## Verification Checklist

Before finalizing the report:
- [ ] Spot-checked 5+ "unused" functions to verify they're truly not called
- [ ] Cross-referenced findings with docs/DEPENDENCIES.md
- [ ] Validated against inventory files (utils, helpers, pages)
- [ ] Checked DUPLICATES.md for overlap
- [ ] Ensured no false positives
- [ ] Verified all active pages from page_config.py were properly traced
- [ ] Applied appropriate confidence levels
- [ ] Documented any discrepancies with existing documentation

---

## Deliverable

Single markdown file: `docs/analysis/UNUSED_CODE_REPORT.md`

The report should be:
- **Actionable** - Clear what's safe to archive vs needs review
- **Validated** - Cross-referenced with existing documentation
- **Confident** - Appropriate confidence levels applied
- **Thorough** - All 530 documented functions accounted for

---

## Expected Outcomes

Based on the existing documentation:
- **530 total functions** documented
- **~500 likely used** (traceable from 40 active pages)
- **~30 potentially unused** (good candidates for archival)
- **~10-20 uncertain** (need human review)

If your numbers differ significantly from these estimates, investigate discrepancies with DEPENDENCIES.md.