# Implementation Deviation Log

**Purpose**: Track functions where implementation differs from documentation. This log helps with troubleshooting, refactoring, and API consistency issues.

**Last Updated**: October 28, 2025
**Status**: ✅ All deviations documented and resolved (docs updated to match implementation)

---

## Overview

This document tracks instances where the actual implementation of a function diverges from its documented specification. These deviations typically occur due to:

- API evolution (implementation changed, documentation wasn't updated)
- Design pattern changes (e.g., from "accept dataframe" to "load from file")
- Convenience enhancements (adding default parameters or optional filters)
- Refactoring (simplifying function signatures)

### Resolution Approach

**For each deviation, we track**:
1. Which layer and module the function is in
2. What the documented vs actual signatures are
3. Why the deviation exists
4. How it was resolved
5. Any related functions with similar patterns

---

## Resolved Deviations (Updated Oct 28, 2025)

### ANALYSIS LAYER - rankings.py

---

#### 1. `add_ranks()`

**Status**: ✅ **RESOLVED** - Documentation updated to match code

**File**: `teg_analysis/analysis/rankings.py:15`

**Documented Signature (OLD)**:
```python
add_ranks(df, score_col, group_col, ascending)
```

**Actual Signature**:
```python
add_ranks(df, fields_to_rank=None, rank_ascending=None)
```

**Root Cause**: API redesigned from ranking single column with grouping to ranking multiple columns with defaults

**Why Code is Better**:
- Multiple column ranking is more efficient than calling repeatedly
- Default fields handle 95% of use cases
- Parameter names (`fields_to_rank`, `rank_ascending`) are more intuitive

**Production Impact**:
- Used in 5+ Streamlit pages via wrapper in `streamlit/utils.py`
- All call sites use actual signature with default parameters
- Zero breaking changes

**Resolution**: Updated FUNCTION_REFERENCE.md (line 372)

**Notes for Future**: If refactoring ranking system, maintain backward compatibility with both single-column and multi-column modes, or deprecate single-column mode formally.

---

#### 2. `get_best()`

**Status**: ✅ **RESOLVED** - Documentation updated to match code

**File**: `teg_analysis/analysis/rankings.py:122`

**Documented Signature (OLD)**:
```python
get_best(df, metric, n, filters)
```

**Actual Signature**:
```python
get_best(df, measure_to_use, player_level=False, top_n=1)
```

**Root Cause**: Generic `filters` concept replaced with specific `player_level` boolean flag

**Why Code is Better**:
- Specific `player_level` parameter is clearer than generic `filters` dict
- Handles the exact use cases needed: per-player best vs all-time best
- Simpler to use and more performant

**Parameter Mapping**:
- Documented `metric` → Actual `measure_to_use` (same concept)
- Documented `n` → Actual `top_n` (same concept)
- Documented `filters` → Actual `player_level` (different implementation)

**Production Impact**:
- Used in Records pages (300TEG Records.py, 301Best TEGs and Rounds.py)
- All 5+ call sites use `player_level=True/False` parameter
- Some call sites use fallback: `get_best(df, measure_to_use=measure, top_n=1)`

**Resolution**: Updated FUNCTION_REFERENCE.md (line 376)

**Related Functions**: `get_worst()` has identical pattern

---

#### 3. `get_worst()`

**Status**: ✅ **RESOLVED** - Documentation updated to match code

**File**: `teg_analysis/analysis/rankings.py:150`

**Documented Signature (OLD)**:
```python
get_worst(df, metric, n, filters)
```

**Actual Signature**:
```python
get_worst(df, measure_to_use, player_level=False, top_n=1)
```

**Root Cause**: Mirror image of `get_best()` - same refactoring pattern

**Production Impact**:
- Used in worst performance processing
- All call sites use actual signature

**Resolution**: Updated FUNCTION_REFERENCE.md (line 377)

**Related Functions**: `get_best()` - keep these in sync during future changes

---

### ANALYSIS LAYER - aggregation.py

---

#### 4. `get_complete_teg_data()`

**Status**: ✅ **RESOLVED** - Documentation updated to match code

**File**: `teg_analysis/analysis/aggregation.py:240`

**Documented Signature (OLD)**:
```python
get_complete_teg_data(df, teg_num)
```

**Actual Signature**:
```python
get_complete_teg_data()
```

**Root Cause**: Evolved from generic filtering function to fixed convenience function

**Pattern Type**: "Load from file" convenience pattern (NOT "accept dataframe" pattern)

**Why Code is Better**:
- Eliminates need to pre-filter data before calling
- Consistent filtering rules (always exclude TEG 50, always exclude incomplete)
- Much simpler API for common use case

**Implementation Details**:
```python
def get_complete_teg_data():
    """Get complete TEG-level data (excluding TEG 50 and incomplete TEGs)."""
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=True)
    aggregated_data = aggregate_data(all_data, 'TEG')
    return aggregated_data
```

**Fixed Parameters**:
- `exclude_teg_50=True` - Always exclude
- `exclude_incomplete_tegs=True` - Always exclude

**Production Impact**:
- Used in 3 locations: `get_ranked_teg_data()`, wrapper in `streamlit/utils.py`, test files
- All call sites expect zero parameters
- Zero breaking changes

**Resolution**: Updated FUNCTION_REFERENCE.md (line 341)

**Related Functions**: `get_teg_data_inc_in_progress()` - similar pattern with different filter

**Design Note**: This represents a design pattern shift in the codebase from generic "accept dataframe" functions to specific "load from file with fixed rules" convenience functions.

---

#### 5. `get_teg_data_inc_in_progress()`

**Status**: ✅ **RESOLVED** - Documentation updated to match code

**File**: `teg_analysis/analysis/aggregation.py:254`

**Documented Signature (OLD)**:
```python
get_teg_data_inc_in_progress(df, teg_num)
```

**Actual Signature**:
```python
get_teg_data_inc_in_progress()
```

**Root Cause**: Same as `get_complete_teg_data()` - evolved to convenience function

**Pattern Type**: "Load from file" convenience pattern

**Implementation Details**:
```python
def get_teg_data_inc_in_progress():
    """Get TEG-level data including in-progress TEGs."""
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'TEG')
    return aggregated_data
```

**Fixed Parameters**:
- `exclude_teg_50=True` - Always exclude
- `exclude_incomplete_tegs=False` - Include in-progress tournaments

**Use Case**: For leaderboards that need current tournament data

**Production Impact**: Internal usage, low risk

**Resolution**: Updated FUNCTION_REFERENCE.md (line 342)

---

#### 6. `get_round_data()`

**Status**: ✅ **RESOLVED** - Documentation updated to match code

**File**: `teg_analysis/analysis/aggregation.py:268`

**Documented Signature (OLD)**:
```python
get_round_data(df, teg_num, round_num)
```

**Actual Signature**:
```python
get_round_data(ex_50=True, ex_incomplete=False)
```

**Root Cause**: Changed from accepting dataframe + specific filters to accepting filter flags

**Pattern Type**: "Load from file with flexible filters" pattern

**Why Code is Better**:
- Two most common use cases encapsulated as flags
- Loads data internally rather than requiring pre-filtered dataframe
- More convenient for common operations

**Implementation Details**:
```python
def get_round_data(ex_50=True, ex_incomplete=False):
    """Get round-level aggregated data.

    Args:
        ex_50 (bool): Exclude TEG 50 if True.
        ex_incomplete (bool): Exclude incomplete TEGs if True.

    Returns:
        pd.DataFrame: Round-level aggregated data.
    """
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=ex_50, exclude_incomplete_tegs=ex_incomplete)
    aggregated_data = aggregate_data(all_data, 'Round')
    return aggregated_data
```

**Default Behavior**:
- Excludes TEG 50 ✅
- Includes in-progress tournaments ✅

**Production Impact**:
- ⚠️ **DIRECT USAGE** in `streamlit/leaderboard.py:85`
  ```python
  round_df = get_round_data(ex_50=ex_teg_50)
  ```
- Also used via `get_ranked_round_data()` wrapper
- HIGH importance - used in active Streamlit page

**Resolution**: Updated FUNCTION_REFERENCE.md (line 343)

**Important Notes for Future Development**:
- This is the primary data getter for leaderboards
- Parameter defaults designed for leaderboard use case
- If changing filtering logic, verify leaderboard.py behavior doesn't break

---

#### 7. `get_9_data()`

**Status**: ✅ **RESOLVED** - Documentation updated to match code

**File**: `teg_analysis/analysis/aggregation.py:286`

**Documented Signature (OLD)**:
```python
get_9_data(df, teg_num, round_num, nines)
```

**Actual Signature**:
```python
get_9_data()
```

**Root Cause**: Simplified to fixed convenience function (same pattern as `get_complete_teg_data()`)

**Pattern Type**: "Load from file" convenience pattern

**Implementation Details**:
```python
def get_9_data():
    """Get 9-hole (front/back) aggregated data."""
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'FrontBack')
    return aggregated_data
```

**Fixed Parameters**:
- `exclude_teg_50=True` - Always exclude
- `exclude_incomplete_tegs=False` - Include in-progress

**Production Impact**:
- Used via `get_ranked_frontback_data()` wrapper in rankings.py:117
- Used directly in pages like `300TEG Records.py`, `teg_worsts.py`
- LOW-MEDIUM importance

**Resolution**: Updated FUNCTION_REFERENCE.md (line 344)

---

#### 8. `get_teg_leaderboard()`

**Status**: ✅ **RESOLVED** - Documentation updated to match code

**File**: `teg_analysis/analysis/aggregation.py:2869`

**Documented Signature (OLD)**:
```python
get_teg_leaderboard(df, teg_num, measure)
```

**Actual Signature**:
```python
get_teg_leaderboard(df, measure, teg_num=None)
```

**Root Cause**: Parameter order changed, `teg_num` made optional

**Why Code is Better**:
- Parameter order matches intuitive pattern: dataframe, then core requirement (measure), then optional filters
- `teg_num=None` allows pre-filtered data to be passed in, reducing redundant filtering

**Parameter Changes**:
- **Order changed**: `(df, teg_num, measure)` → `(df, measure, teg_num=None)`
- **Optional flag**: `teg_num` is now optional (defaults to None)

**Implementation Logic**:
```python
def get_teg_leaderboard(df: pd.DataFrame, measure: str, teg_num: int = None) -> pd.DataFrame:
    data = df.copy()
    if teg_num is not None:
        data = data[data['TEGNum'] == teg_num]
    # ... create leaderboard from data ...
    return leaderboard
```

**Usage Patterns** (both valid):
1. Pre-filter then call:
   ```python
   teg_data = df[df['TEGNum'] == 18]
   leaderboard = get_teg_leaderboard(teg_data, 'Stableford')
   ```

2. Pass teg_num to function:
   ```python
   leaderboard = get_teg_leaderboard(df, 'Stableford', teg_num=18)
   ```

**Production Impact**: Used in multiple Streamlit pages, leaderboard display

**Resolution**: Updated FUNCTION_REFERENCE.md (line 356)

**Important**: If code uses positional arguments with old parameter order, it will fail. Recommend keyword arguments: `teg_num=18`

---

#### 9. `get_round_leaderboard()`

**Status**: ✅ **RESOLVED** - Documentation updated to match code

**File**: `teg_analysis/analysis/aggregation.py:2948`

**Documented Signature (OLD)**:
```python
get_round_leaderboard(df, teg_num, round_num, measure)
```

**Actual Signature**:
```python
get_round_leaderboard(df, measure, teg_num=None, round_num=None)
```

**Root Cause**: Same as `get_teg_leaderboard()` - parameter order and optional flags

**Why Code is Better**: Same reasoning as `get_teg_leaderboard()`

**Parameter Changes**:
- **Reordered**: measure moved to position 2
- **Optional flags**: `teg_num` and `round_num` are now optional

**Production Impact**: Used for single-round leaderboards

**Resolution**: Updated FUNCTION_REFERENCE.md (line 357)

**Related Functions**: Keep in sync with `get_teg_leaderboard()` for consistency

---

## Summary Table

| # | Function | Module | Documented → Actual | Type | Resolution | Priority |
|---|----------|--------|---------------------|------|-----------|----------|
| 1 | `add_ranks()` | rankings | `(df, score_col, group_col, asc)` → `(df, fields=None, asc=None)` | API redesign | Docs updated | HIGH |
| 2 | `get_best()` | rankings | `(df, metric, n, filters)` → `(df, measure, player_level=F, top_n=1)` | Param rename | Docs updated | HIGH |
| 3 | `get_worst()` | rankings | `(df, metric, n, filters)` → `(df, measure, player_level=F, top_n=1)` | Param rename | Docs updated | HIGH |
| 4 | `get_complete_teg_data()` | aggregation | `(df, teg_num)` → `()` | Convenience fn | Docs updated | MEDIUM |
| 5 | `get_teg_data_inc_in_progress()` | aggregation | `(df, teg_num)` → `()` | Convenience fn | Docs updated | MEDIUM |
| 6 | `get_round_data()` | aggregation | `(df, teg_num, round)` → `(ex_50=T, ex_incomplete=F)` | Filter flags | Docs updated | **HIGH** |
| 7 | `get_9_data()` | aggregation | `(df, teg_num, round, nines)` → `()` | Convenience fn | Docs updated | MEDIUM |
| 8 | `get_teg_leaderboard()` | aggregation | `(df, teg_num, measure)` → `(df, measure, teg_num=None)` | Param order | Docs updated | LOW |
| 9 | `get_round_leaderboard()` | aggregation | `(df, teg_num, round, measure)` → `(df, measure, teg_num=None, round=None)` | Param order | Docs updated | LOW |

---

## Future Prevention

### How to Prevent New Deviations

1. **Update documentation when changing signatures**
   - FUNCTION_REFERENCE.md must be updated simultaneously with code changes
   - Add entry to this log when deviation is discovered/resolved

2. **Use semantic versioning**
   - Breaking changes (signature changes) bump minor version
   - Non-breaking changes (default param additions) are patch version

3. **Deprecation warnings**
   - If changing function signature, add deprecation period
   - Log warning when old-style calls are detected

4. **Code review checklist**
   - [ ] Function signature changed?
   - [ ] FUNCTION_REFERENCE.md updated?
   - [ ] Function docstring updated?
   - [ ] This log updated?
   - [ ] Tests verify both old and new patterns?

---

## Related Documents

- **SIGNATURE_MISMATCH_ANALYSIS.md** - Detailed analysis of all 9 deviations with call chains
- **FUNCTION_REFERENCE.md** - Authoritative function documentation (updated Oct 28, 2025)
- **AUDIT_REPORT_COMPLETE.md** - Complete codebase audit results

---

## Questions to Answer During Future Refactoring

1. **Should we unify the "Load from file" functions?**
   - `get_complete_teg_data()`, `get_teg_data_inc_in_progress()`, `get_round_data()`, `get_9_data()` all follow same pattern
   - Could create a single parametrized `get_aggregated_data(level, ex_50=True, ex_incomplete=False)` function
   - Would simplify API but lose semantic clarity of specific functions

2. **Should we standardize parameter ordering?**
   - Current: `(df, measure, optional_filters...)`
   - Proposal: All functions use this pattern consistently
   - Would require changes to `get_teg_leaderboard()`, `get_round_leaderboard()` if they haven't been yet

3. **Should we add backward compatibility layer?**
   - Option: Detect old-style calls and warn/adapt
   - Would help migration but adds complexity
   - Currently not needed - no production code using old signatures found

---

*This log serves as institutional memory for why functions evolved the way they did, helping future developers understand the rationale behind current APIs.*
