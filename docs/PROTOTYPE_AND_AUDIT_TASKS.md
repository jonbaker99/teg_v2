# Prototype & Audit Tasks

**Purpose**: Two complementary tasks to improve codebase understanding and validation through auditing and interactive exploration.

---

## Background Context

During recent development, we discovered that several functions were **documented in FUNCTION_REFERENCE.md but not actually implemented** in the codebase. Examples:
- `get_teg_leaderboard()` - documented but not implemented (now fixed)
- `get_round_leaderboard()` - documented but not implemented (now fixed)

Additionally, some functions exist but with **different signatures than documented**, making them difficult to discover and use.

This led to two strategic initiatives:

1. **Function Audit** - Systematically identify and fix documentation/implementation mismatches
2. **NiceGUI Demo Pages** - Create interactive explorer pages that demonstrate function usage and validate their behavior

---

## Task 1: Function Audit

### Objectives

**Primary Goal**: Create a comprehensive audit report identifying all discrepancies between documented and implemented functions in the codebase.

**Specific Objectives**:
1. **Document vs Implementation Gaps**
   - Identify functions documented in FUNCTION_REFERENCE.md but not implemented
   - Identify functions implemented but not documented
   - Categorize and prioritize each gap

2. **Signature Mismatches**
   - Find functions where actual parameters differ from documented parameters
   - Find functions where return types differ from documentation
   - Document expected vs actual behavior

3. **Stub Implementations**
   - Identify functions that are implemented but appear incomplete (e.g., missing parameters, minimal logic)
   - Flag functions that call undefined dependencies or unimplemented functions
   - Categorize severity (critical blockers vs. minor issues)

4. **Actionable Report**
   - Provide a prioritized list of fixes needed
   - Suggest implementation fixes for critical functions
   - Recommend documentation updates

### Approach

**Phase 1: Discovery**
- Parse FUNCTION_REFERENCE.md to extract all documented functions with signatures
- Scan each analysis module (aggregation, rankings, scoring, streaks, records, commentary, pipeline) for actual function definitions
- Compare documented vs implemented function lists per module
- Create a detailed discrepancy map

**Phase 2: Analysis**
- For each discrepancy, determine type:
  - Missing implementation (document exists, code doesn't)
  - Missing documentation (code exists, document doesn't)
  - Signature mismatch (both exist, but parameters/return differ)
  - Incomplete stub (function exists but core logic missing)

**Phase 3: Validation**
- Test each identified function to determine actual behavior
- Document actual vs expected behavior
- Create reproducible examples for documentation updates

**Phase 4: Reporting**
- Generate comprehensive audit report
- Provide prioritized fix recommendations
- Suggest quick wins vs. major refactoring items

### Starter Prompt

Use this prompt to begin the audit task:

```
I need you to audit the TEG Analysis codebase for documented vs implemented functions.

Here's what we know:
- FUNCTION_REFERENCE.md documents 235+ functions across 4 layers (IO, Core, Analysis, Display)
- The codebase has: teg_analysis/io/, teg_analysis/core/, teg_analysis/analysis/, teg_analysis/display/
- Past discovery: get_teg_leaderboard() and get_round_leaderboard() were documented but not implemented

Your task is to:

1. **Audit the Analysis Layer First** (most complex, 180+ documented functions)
   - Focus on: aggregation, rankings, scoring, streaks, records, commentary
   - For each module:
     a) Extract all documented function signatures from FUNCTION_REFERENCE.md
     b) Extract all actual function definitions from the .py file
     c) Compare and identify discrepancies

2. **Categorize Discrepancies**
   - Type 1: Documented but not implemented (code gap)
   - Type 2: Implemented but not documented (docs gap)
   - Type 3: Signature mismatch (both exist, but different)
   - Type 4: Stub implementation (minimal/incomplete code)

3. **For each discrepancy, document**:
   - Module and function name
   - Documented signature (if exists)
   - Actual signature (if exists)
   - Type of discrepancy
   - Severity (critical/high/medium/low)
   - Brief description

4. **Create an Audit Report** showing:
   - Summary statistics (e.g., "45 functions documented, 40 implemented, 5 gaps")
   - Module-by-module breakdown
   - Prioritized list of fixes needed
   - Quick-win recommendations

Focus on accuracy and clarity. Use the existing docs/FUNCTION_REFERENCE.md as the source of truth for what's documented.

Start with the Analysis Layer, before moving to Core and Display layers afterward.
```

---

## Task 2: NiceGUI Demo Pages

### Objectives

**Primary Goal**: Create a series of interactive NiceGUI pages that demonstrate how to use core functions from the codebase, show their raw output, and serve as a learning/validation tool.

**Specific Objectives**:
1. **Function Discovery & Learning**
   - Help new developers understand what functions exist and what they do
   - Show concrete input/output examples for each function
   - Demonstrate common patterns and workflows

2. **Data Validation**
   - Verify functions work with real data
   - Display raw function outputs to catch unexpected behavior
   - Catch API changes or implementation bugs early

3. **Interactive Exploration**
   - Allow filtering/selection to test functions with different inputs
   - Show both raw data (what function returns) and formatted display (what users see)
   - Enable quick hypothesis testing

4. **Educational Resource**
   - Serve as a reference for developers integrating functions
   - Show best practices for function usage
   - Demonstrate the data pipeline conceptually

### Approach

**Page Organization**:
- Create pages organized by **module** or **layer** (e.g., `demo_pages_aggregation.py`, `demo_pages_rankings.py`)
- Each page focuses on a related set of functions (e.g., all filtering/aggregation functions, all ranking functions)
- Pages are **standalone** (can run independently, no multi-page routing)

**Page Structure** (per existing prototype pattern):
```
┌─ Page Title
├─ Description (brief intro)
├─ INPUT CONTROLS
│  └─ Dropdowns/selections for filtering (TEG, Player, Round, etc.)
├─ FUNCTION 1: [Function Name]
│  ├─ Function signature & brief description
│  ├─ Section 1: Raw Data Output
│  │  └─ Display raw DataFrame from function
│  └─ Section 2: Formatted Display
│     └─ Pretty table or formatted output
├─ FUNCTION 2: [Function Name]
│  ├─ Function signature & brief description
│  ├─ Section 1: Raw Data Output
│  └─ Section 2: Formatted Display
└─ [More functions...]
```

**Content Per Function**:
1. Function name and module (e.g., `aggregation.get_teg_leaderboard`)
2. Brief description (from docstring)
3. Signature: `(df: pd.DataFrame, measure: str, teg_num: int = None) → pd.DataFrame`
4. Raw data section: Show exact output from function
5. Formatted section: Nice table display

**Priority Pages** (based on usage frequency & complexity):

**Tier 1: Core Data Flow**
- `demo_pages_aggregation.py`
  - `filter_data_by_teg()`, `filter_data_by_player()`, `filter_data_by_round()`
  - `aggregate_data()` with different levels
  - `get_teg_leaderboard()`, `get_round_leaderboard()`
  - `get_teg_winners()`

- `demo_pages_rankings.py`
  - `add_ranks()`
  - `get_best()`, `get_worst()`
  - `ordinal()`

**Tier 2: Analysis Functions**
- `demo_pages_records.py`
  - `identify_aggregate_records_and_pbs()`
  - `identify_all_time_worsts()`
  - `identify_streak_records()`

- `demo_pages_scoring.py`
  - `prepare_average_scores_by_par()`
  - `calculate_stableford_points()`
  - `get_net_competition_measure()`

**Tier 3: Supporting Functions**
- `demo_pages_metadata.py`
  - `get_teg_metadata()`
  - `load_course_info()`
  - `get_player_name()`

### Starter Prompt

Use this prompt to begin creating demo pages:

```
I want you to create NiceGUI demo pages that showcase functions from the TEG Analysis codebase.

Context:
- We have existing prototype pages at nicegui/prototype_page1_stableford_simple.py and prototype_page2_par_analysis.py
- Those pages follow a simple pattern: title → dropdowns → raw data → formatted table
- Goal: Create similar pages for different function modules to help developers understand the codebase

Your task is to create **demo_pages_aggregation.py** - a NiceGUI page demonstrating key aggregation functions.

Requirements:
1. **Page Structure**
   - Title: "Function Explorer: Aggregation Functions"
   - Brief intro explaining what these functions do
   - Input controls: dropdown for TEG selection (required)
   - Display multiple functions below

2. **Functions to Demonstrate** (in this order):
   - `filter_data_by_teg(df, teg_num)` - Filter to specific TEG
   - `aggregate_data(df, level='Round')` - Aggregate to round level
   - `get_teg_leaderboard(df, measure='Stableford', teg_num=None)` - Generate leaderboard

3. **For Each Function**:
   - Display function signature (copy/paste from code)
   - Brief description (from docstring)
   - **Raw Data Section**: Show exact function output as code block with shape/columns info
   - **Formatted Display**: Show nice table of the data
   - These should be in accordion or separate sections

4. **Code Quality**:
   - Import from teg_analysis.analysis.aggregation (and core.data_loader)
   - Use the standard multiprocessing guard: `if __name__ in {"__main__", "__mp_main__"}`
   - Keep it simple - no unnecessary complexity
   - Add comments explaining the data flow
   - Handle errors gracefully

5. **Example Pattern** (from existing prototype):
   ```python
   # Load data
   all_data = load_all_data()
   available_tegs = sorted(all_data['TEGNum'].unique())

   # UI controls
   ui.label('Select TEG').classes('text-sm font-semibold')
   teg_select = ui.select(options=available_tegs, value=available_tegs[-1])

   # Define refresh function
   def refresh():
       teg_num = teg_select.value

       # Show Function 1
       ui.label('Function: filter_data_by_teg()').classes('text-h6')
       teg_data = filter_data_by_teg(all_data, teg_num)
       # Display raw data and table...

       # Show Function 2
       ui.label('Function: aggregate_data()').classes('text-h6')
       result = aggregate_data(teg_data, level='Round')
       # Display raw data and table...

       # Show Function 3
       ui.label('Function: get_teg_leaderboard()').classes('text-h6')
       leaderboard = get_teg_leaderboard(result, 'Stableford')
       # Display raw data and table...

   refresh_btn = ui.button('Refresh')
   teg_select.on('update:model-value', lambda: refresh())
   refresh()
   ```

Make this page as **simple and educational as possible**. The goal is to help developers understand what these functions do and what data they return.
```

---

## Implementation Guidelines

### General Principles
- **Simplicity First**: Start with the smallest useful version, expand only if needed
- **Documentation**: Each task should document findings clearly for future reference
- **Iterative**: Complete Tier 1 before moving to Tier 2/3
- **Testable**: All functions should work with real data without crashing

### File Locations
- Audit reports: `docs/AUDIT_REPORTS/` (create directory as needed)
- NiceGUI demo pages: `nicegui/demo_pages_*.py` (following existing pattern)

### Success Criteria

**Task 1 (Audit) Success**:
- [ ] Complete audit report generated
- [ ] All discrepancies categorized
- [ ] Prioritized fix list provided
- [ ] At least 3 quick-win fixes identified

**Task 2 (Demo Pages) Success**:
- [ ] Aggregation functions page created and working
- [ ] Page runs without errors with real data
- [ ] All 3+ functions demonstrated with raw + formatted output
- [ ] Ready to create similar pages for other modules

---

## Related Documentation
- `docs/FUNCTION_REFERENCE.md` - Full function documentation (235+ functions)
- `docs/ARCHITECTURE.md` - Package structure and design
- `nicegui/prototype_page1_stableford_simple.py` - Example of desired simplicity
- `nicegui/prototype_page2_par_analysis.py` - Example of aggregated data display
