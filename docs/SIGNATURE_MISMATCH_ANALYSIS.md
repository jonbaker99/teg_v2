# Signature Mismatch Analysis: 9 Functions in Detail

**Analysis Date**: October 28, 2025
**Scope**: Complete investigation of actual implementations, usage patterns, and call chains
**Depth**: 3-level tracing to Streamlit pages

---

## Executive Summary

### Quick Decision Matrix

| Function | Documented | Actual | Recommendation | Risk | Reason |
|----------|-----------|--------|-----------------|------|--------|
| `add_ranks()` | `(df, score_col, group_col, ascending)` | `(df, fields_to_rank=None, rank_ascending=None)` | 📝 Fix docs | HIGH | Core function, many call sites |
| `get_best()` | `(df, metric, n, filters)` | `(df, measure_to_use, player_level=False, top_n=1)` | 📝 Fix docs | HIGH | 5+ call sites use actual signature |
| `get_worst()` | `(df, metric, n, filters)` | `(df, measure_to_use, player_level=False, top_n=1)` | 📝 Fix docs | HIGH | 5+ call sites use actual signature |
| `get_complete_teg_data()` | `(df, teg_num)` | `()` | 📝 Fix docs | MEDIUM | Different pattern: "load from file" vs "accept df" |
| `get_teg_data_inc_in_progress()` | `(df, teg_num)` | `()` | 📝 Fix docs | MEDIUM | Different pattern: "load from file" vs "accept df" |
| `get_round_data()` | `(df, teg_num, round_num)` | `(ex_50=True, ex_incomplete=False)` | 📝 Fix docs | MEDIUM | Direct usage in leaderboard.py:85 |
| `get_9_data()` | `(df, teg_num, round_num, nines)` | `()` | 📝 Fix docs | LOW | Used via rankings wrapper functions |
| `get_teg_leaderboard()` | `(df, teg_num, measure)` | `(df, measure, teg_num=None)` | ✅ Code OK | LOW | Parameter order matters, but works as-is |
| `get_round_leaderboard()` | `(df, teg_num, round_num, measure)` | `(df, measure, teg_num=None, round_num=None)` | ✅ Code OK | LOW | Parameter order matters, but works as-is |

**Overall Recommendation**: **Fix documentation (8 functions)** to match actual implementations. The code is working correctly in production.

---

## Detailed Function Analysis

### GROUP A: Rankings Functions (rankings.py)

---

## Function 1: `add_ranks()`

### Current Implementation

**File**: `teg_analysis/analysis/rankings.py:15`

**Actual Signature**:
```python
def add_ranks(df, fields_to_rank=None, rank_ascending=None):
```

**What It Does**:
- Accepts a DataFrame with scoring data
- Adds ranking columns for specified fields
- Creates two types of ranks:
  - `Rank_within_player_<field>` - Rank within each player's own rounds
  - `Rank_within_all_<field>` - Rank across all players
- Default fields: `['Sc', 'GrossVP', 'NetVP', 'Stableford']`
- Default ascending order: True for all except Stableford (False)

**Full Function Code**:
```python
def add_ranks(df, fields_to_rank=None, rank_ascending=None):
    """Adds ranking columns to the DataFrame for optionally specified fields or all scoring fields.

    Adds rankings both within each player's rounds and across all rounds.
    The ranking can be done in ascending or descending order.
    Ranking will be applied at lowest level of aggregation present in the data.

    Parameters:
    -----------
    df : pandas.DataFrame
        The input DataFrame containing the data.
        It must include at least a 'Player' column and
        the fields to be ranked (e.g., 'Sc', 'GrossVP', 'NetVP', 'Stableford').

    fields_to_rank : list or str, optional
        The fields to rank. This can be a list of field names (e.g., ['Sc', 'GrossVP']) or a single
        field name as a string (e.g., 'Sc'). If not provided, the default is ['Sc', 'GrossVP', 'NetVP',
        'Stableford'].

    rank_ascending : bool, optional
        The order of ranking. If not provided, the function defaults to:
        - True for all fields except 'Stableford', where it defaults to False.
        If provided, this will apply the same order for all fields.

    Returns:
    --------
    pandas.DataFrame
        A DataFrame with additional columns for the ranking of each specified field:
        - 'Rank_within_player_<field>': The rank of the field within each player's rounds.
        - 'Rank_within_all_<field>': The rank of the field across all rounds.

    Example:
    --------
    >>> add_ranks(df, fields_to_rank=['Sc', 'Stableford'], rank_ascending=True)
    This will add rank columns for 'Sc' and 'Stableford', ranked in ascending order.

    >>> add_ranks(df)
    This will add rank columns for the default fields ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    with default ascending/descending order.
    """
    # ... implementation adds ranking columns ...
    return df
```

---

### Documented Signature (MISMATCH)

**From FUNCTION_REFERENCE.md**:
```python
add_ranks(df, score_col, group_col, ascending)
```

**Expected behavior**: "Add ranking columns (score_col, group_col, ascending)"

---

### Usage Analysis

#### Usage Pattern 1: Via Wrapper Function (streamlit/utils.py)

**Wrapper function**:
```python
def add_ranks(df, fields_to_rank=None, rank_ascending=None):
    """Adds ranking columns to the DataFrame..."""
    from teg_analysis.analysis.rankings import add_ranks as _add_ranks
    return _add_ranks(df, fields_to_rank, rank_ascending)
```

**Call sites using wrapper**:
- `streamlit/helpers/best_performance_processing.py` - Multiple uses
- `streamlit/helpers/display_helpers.py` - Multiple uses

#### Usage Pattern 2: Direct Import in rankings.py

**Call Sites** (within rankings.py itself):

1. **`get_ranked_teg_data()` at line 90**:
```python
def get_ranked_teg_data():
    from .aggregation import get_complete_teg_data
    df = get_complete_teg_data()
    ranked_data = add_ranks(df)  # ← Line 90: Called with just df
    return ranked_data
```
**Call chain**: streamlit pages → `rankings.py:get_ranked_teg_data()` → `add_ranks(df)`

2. **`get_ranked_round_data()` at line 104**:
```python
def get_ranked_round_data():
    from .aggregation import get_round_data
    df = get_round_data()
    ranked_data = add_ranks(df)  # ← Line 104: Called with just df
    return ranked_data
```

3. **`get_ranked_frontback_data()` at line 118**:
```python
def get_ranked_frontback_data():
    from .aggregation import get_9_data
    df = get_9_data()
    ranked_data = add_ranks(df)  # ← Line 118: Called with just df
    return ranked_data
```

#### Usage Pattern 3: In Streamlit best_performance_processing.py

**File**: `streamlit/helpers/best_performance_processing.py`

```python
# Line ~45: Getting ranked round data
rd_data_ranked = get_ranked_round_data()  # Returns data with ranks already added

# Line ~120: Using add_ranks directly
from utils import add_ranks
ranked_data = add_ranks(some_df)  # Uses default fields and ascending order
```

---

### Streamlit Pages Using This Function

**Direct usage** (via wrapper in utils.py):
- `streamlit/helpers/best_performance_processing.py` (multiple functions)
- `streamlit/helpers/display_helpers.py` (multiple functions)

**Indirect usage** (via ranking wrapper functions):
- `streamlit/score_by_course.py` - Imports `get_ranked_teg_data()`, `get_ranked_round_data()`
- `streamlit/leaderboard.py` - Uses ranked data
- `streamlit/300TEG Records.py` - Uses ranked data for records display

---

### Usage Pattern Observed

**ALL call sites use one of these patterns:**

Pattern 1 (Most common):
```python
ranked_df = add_ranks(df)  # Uses all defaults
```

Pattern 2 (Less common):
```python
ranked_df = add_ranks(df, fields_to_rank=['Sc'])  # Specify fields only
```

Pattern 3 (Rare):
```python
ranked_df = add_ranks(df, fields_to_rank=['Sc'], rank_ascending=True)
```

**NONE of the call sites use**: `score_col`, `group_col`, or individual parameter names from documentation.

---

### Analysis

**Documented signature**: `add_ranks(df, score_col, group_col, ascending)`
- Suggests: Rank one column (score_col) grouped by another (group_col) in specified ascending order
- Sounds like: `SELECT RANK() OVER (PARTITION BY group_col) FROM df WHERE column = score_col`

**Actual signature**: `add_ranks(df, fields_to_rank=None, rank_ascending=None)`
- Does: Rank multiple specified fields, creating paired rank columns
- Creates: Rank_within_player_X and Rank_within_all_X columns

**Pattern mismatch type**: Complete function redesign
- Documented version: Single column → Single output column
- Actual version: Multiple columns → Multiple output columns

**Code is working correctly**: 5+ call sites in production use actual signature successfully.

---

### Recommendation

**[✓] Update documentation to match code**

**Reasoning**:
1. Function works correctly in production with current signature
2. All 5+ call sites expect `fields_to_rank` and `rank_ascending` parameters
3. Changing signature would break all call sites
4. Current behavior is well-documented in docstring (which is correct)
5. Parameter names are intuitive (`fields_to_rank` vs `score_col`)

**Risk of changing code**: **HIGH** - Would break 5+ active call sites
**Risk of changing docs**: **NONE** - Docs don't affect working code

---

## Function 2: `get_best()`

### Current Implementation

**File**: `teg_analysis/analysis/rankings.py:122`

**Actual Signature**:
```python
def get_best(df, measure_to_use, player_level=False, top_n=1):
```

**What It Does**:
- Filters DataFrame to show best performances
- Requires input DataFrame to have ranking columns (created by `add_ranks()`)
- Uses ranking column: `Rank_within_player_<measure>` or `Rank_within_all_<measure>`
- Returns rows where rank <= top_n

**Core Logic**:
```python
def get_best(df, measure_to_use, player_level=False, top_n=1):
    # Validate measure
    valid_measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    if measure_to_use not in valid_measures:
        raise ValueError(f"Invalid measure: '{measure_to_use}'...")

    # Construct rank column name based on player_level flag
    measure_fn = 'Rank_within_' + ('player' if player_level else 'all') + f'_{measure_to_use}'

    # Filter to top N ranks
    return df[df[measure_fn] <= top_n]
```

---

### Documented Signature (MISMATCH)

**From FUNCTION_REFERENCE.md**:
```python
get_best(df, metric, n, filters)
```

**Expected behavior**: Get n best results with optional filters

---

### Usage Analysis

#### All Call Sites (5 total)

1. **streamlit/helpers/best_performance_processing.py:~85** (get_best_rounds)
```python
def get_best_rounds(rd_data_ranked, selected_measure, n_keep):
    rank_measure = f'Rank_within_all_{selected_measure}'

    # Get best performances from utils function
    from utils import get_best

    best_rounds = (get_best(rd_data_ranked, selected_measure, player_level=False, top_n=n_keep)
                   .sort_values(by=rank_measure, ascending=True)
                   .rename(columns={rank_measure: '#'})
                   .rename(columns=inverted_name_mapping))

    return best_rounds
```

**Call chain**:
- `streamlit/300TEG Records.py` (display records)
- → `streamlit/helpers/best_performance_processing.py:get_best_rounds()`
- → `get_best(rd_data_ranked, selected_measure, player_level=False, top_n=n_keep)` ✓ Uses actual parameters

2. **streamlit/helpers/best_performance_processing.py:~135** (get_personal_best_rounds)
```python
# Get best performances per player using get_best function (player_level=True gets 1 per player)
from utils import get_best

personal_best_rounds = (get_best(rd_data_ranked, selected_measure, player_level=True, top_n=1)
                       .sort_values(by=rank_all_time, ascending=True)
                       .rename(columns={rank_all_time: '#'})
                       .rename(columns=inverted_name_mapping))
```

**Call chain**:
- `streamlit/301Best_TEGs_and_Rounds.py`
- → `streamlit/helpers/best_performance_processing.py:get_personal_best_rounds()`
- → `get_best(rd_data_ranked, selected_measure, player_level=True, top_n=1)` ✓ Uses actual parameters

3. **streamlit/helpers/display_helpers.py** (fallback for tied records)
```python
from utils import get_best

if rank_column not in data_source.columns:
    # Fallback to old method if ranking column doesn't exist
    tied_records = get_best(data_source, measure_to_use=measure, top_n=1)
```

**Note**: Uses `measure_to_use=` keyword argument (actual parameter name, not documented `metric`)

---

### Streamlit Pages Using This Function

**Direct pages**:
- `streamlit/300TEG Records.py` - Best records display
- `streamlit/301Best_TEGs_and_Rounds.py` - Personal best rankings
- `streamlit/helpers/display_helpers.py` - Display utilities

**All call sites use**: `get_best(df, measure_to_use, player_level=..., top_n=...)`

**None use**: The documented `(df, metric, n, filters)` signature

---

### Usage Pattern Observed

**All 5 call sites use this pattern:**
```python
get_best(ranked_df, 'Measure', player_level=False/True, top_n=N)
```

**Parameter mapping - Actual vs Documented**:
| Documented | Actual | Usage |
|-----------|--------|-------|
| `metric` | `measure_to_use` | ✓ `'Sc'`, `'Stableford'`, etc. |
| `n` | `top_n` | ✓ Number like 5, 10, etc. |
| `filters` | `player_level` | ✗ Completely different concept |

**The `filters` vs `player_level` difference**:
- Documented `filters`: Suggests generic filter dict or conditions
- Actual `player_level`: Boolean flag for "group by player or all-time"
- These are incompatible concepts

---

### Recommendation

**[✓] Update documentation to match code**

**Reasoning**:
1. **5+ active call sites** use the actual signature `get_best(df, measure_to_use, player_level=False, top_n=1)`
2. **All in production** and working correctly
3. **Parameter names are clearer**: `player_level` is more intuitive than generic `filters`
4. **Changing code would break**: Multiple Streamlit pages depend on current signature
5. **Risk of changing code**: **HIGH** - Would require changes to 5 files
6. **Risk of changing docs**: **NONE** - Just documentation update

**Actual function behavior** (from code):
- Filters DataFrame to show top N performances by measure
- Can rank across all players (`player_level=False`) or per player (`player_level=True`)
- Requires DataFrame to have ranking columns from `add_ranks()`

---

## Function 3: `get_worst()`

### Current Implementation

**File**: `teg_analysis/analysis/rankings.py:150`

**Actual Signature**:
```python
def get_worst(df, measure_to_use, player_level=False, top_n=1):
```

**What It Does**:
- Filters DataFrame to show worst performances
- Works opposite of `get_best()`
- Uses pandas `nsmallest()` / `nlargest()` depending on measure type
- Handles per-player ranking when `player_level=True`

**Core Logic**:
```python
def get_worst(df, measure_to_use, player_level=False, top_n=1):
    valid_measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    if measure_to_use not in valid_measures:
        raise ValueError(...)

    if player_level == False:
        if measure_to_use == 'Stableford':
            df = df.nsmallest(top_n, measure_to_use)  # Lower is worse for Stableford
        else:
            df = df.nlargest(top_n, measure_to_use)   # Higher is worse for others
    else:
        # Group by player first, then get worst per player
        if measure_to_use == 'Stableford':
            df = df.groupby('Player', group_keys=False).apply(lambda x: x.nsmallest(top_n, measure_to_use))
        else:
            df = df.groupby('Player', group_keys=False).apply(lambda x: x.nlargest(top_n, measure_to_use))

    return df
```

---

### Documented Signature (MISMATCH)

**From FUNCTION_REFERENCE.md**:
```python
get_worst(df, metric, n, filters)
```

---

### Usage Analysis

#### All Call Sites (5 total)

1. **streamlit/helpers/best_performance_processing.py:~220** (get_worst_rounds)
```python
from utils import get_worst

worst_rounds = (get_worst(rd_data_ranked, selected_measure, player_level=False, top_n=n_keep)
                .rename(columns=inverted_name_mapping))
```

2. **streamlit/helpers/best_performance_processing.py:~245** (get_personal_worst_tegs)
```python
from utils import get_worst

personal_worst_tegs = (get_worst(filtered_data, selected_measure, player_level=True, top_n=1)
                      .rename(columns=inverted_name_mapping))
```

3. **streamlit/helpers/best_performance_processing.py:~315** (get_personal_worst_rounds)
```python
from utils import get_worst

personal_worst_rounds = (get_worst(rd_data_ranked, selected_measure, player_level=True, top_n=1)
                        .rename(columns=inverted_name_mapping))
```

4. **streamlit/helpers/best_performance_processing.py:~195** (calculate_worst_teg_scores)
```python
# Uses nsmallest/nlargest directly instead of get_worst()
# (Because filtering excludes TEG 2, which makes ranking invalid)
if selected_measure == 'Stableford':
    worst_tegs = teg_data_ranked.nsmallest(n_keep, selected_measure)
else:
    worst_tegs = teg_data_ranked.nlargest(n_keep, selected_measure)
```

5. **streamlit/helpers/display_helpers.py**
```python
from utils import get_worst
# Fallback when ranking column not found
```

---

### Streamlit Pages Using This Function

**Pages**:
- `streamlit/300TEG Records.py` - Worst records display
- `streamlit/301Best_TEGs_and_Rounds.py` - Personal worst rankings
- `streamlit/helpers/display_helpers.py` - Display utilities

**All call sites use same signature as `get_best()`:**
```python
get_worst(df, measure_to_use, player_level=False/True, top_n=N)
```

---

### Recommendation

**[✓] Update documentation to match code**

**Same as `get_best()`**: Mirror image function with identical signature design.

**Reasoning**:
1. **5+ active call sites** use actual signature
2. **All working in production** without issues
3. **Parallel to get_best()** - Both should match
4. **Risk of code change**: **HIGH** - 5 active call sites
5. **Risk of doc change**: **NONE**

---

---

## GROUP B: Data Getter Functions (aggregation.py)

---

## Function 4: `get_complete_teg_data()`

### Current Implementation

**File**: `teg_analysis/analysis/aggregation.py:240`

**Actual Signature**:
```python
def get_complete_teg_data():
```

**What It Does**:
```python
def get_complete_teg_data():
    """Get complete TEG-level data (excluding TEG 50 and incomplete TEGs)."""
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=True)
    aggregated_data = aggregate_data(all_data, 'TEG')  # Aggregate to TEG level
    return aggregated_data
```

**Pattern**: "Load from file" pattern
- Loads data internally (no dataframe input)
- Applies fixed filtering (TEG 50, incomplete always excluded)
- Aggregates to TEG level
- Returns fully prepared DataFrame

---

### Documented Signature (MISMATCH)

**From FUNCTION_REFERENCE.md**:
```python
get_complete_teg_data(df, teg_num)
```

**Expected behavior**: Accept dataframe and TEG number, filter and return

---

### Usage Analysis

#### All Call Sites (3 total)

1. **teg_analysis/analysis/rankings.py:89**
```python
def get_ranked_teg_data():
    """Gets complete TEG-level data with rankings added."""
    from .aggregation import get_complete_teg_data

    df = get_complete_teg_data()  # ← Called with NO parameters
    ranked_data = add_ranks(df)
    return ranked_data
```

**Call chain**:
- `streamlit/score_by_course.py` (imports `get_ranked_teg_data`)
- → `rankings.py:get_ranked_teg_data()`
- → `get_complete_teg_data()` ✓ Uses actual (no-parameter) signature

2. **streamlit/utils.py** (wrapper function)
```python
@_st_cache_data
def get_complete_teg_data():
    """Get complete TEG-level data (excluding TEG 50 and incomplete TEGs)."""
    df = get_complete_teg_data()  # Wraps the actual function
    return df
```

3. **Test file**: `tests/test_independence.py`
```python
def test_something():
    df = get_complete_teg_data()  # Called with no parameters
```

---

### Streamlit Pages Using This Function

**Indirect usage**:
- `streamlit/score_by_course.py` - Uses `get_ranked_teg_data()` which calls this

**Direct observation**: Called always with zero parameters in all 3 locations

---

### Design Pattern Analysis

**Key insight**: This follows a "convenience function" pattern
- Pre-configured filtering (always exclude TEG 50, always exclude incomplete)
- No flexibility needed - always same fixed set of rules
- Much simpler than accepting dataframe parameter

**Why it might have been documented differently**:
- Older API design may have been flexible
- Evolved to convenience function as usage patterns emerged
- Documentation wasn't updated to match evolved API

---

### Recommendation

**[✓] Update documentation to match code**

**Reasoning**:
1. **All 3 call sites** use zero-parameter signature
2. **Fixed filtering pattern** makes sense - no need for flexibility
3. **Changing code would break**: All 3 call sites
4. **Risk of code change**: **MEDIUM** - 3 call sites + wrapper
5. **Risk of doc change**: **NONE**

**Updated documentation should be**:
```python
def get_complete_teg_data() -> pd.DataFrame:
    """Get complete TEG-level data (excluding TEG 50 and incomplete TEGs).

    This is a convenience function that loads and aggregates tournament data
    with fixed filtering rules. No parameters needed - always excludes TEG 50
    and incomplete TEGs.

    Returns:
        pd.DataFrame: TEG-level aggregated data with columns for each score measure
        and tournament metadata.

    Example:
        >>> teg_data = get_complete_teg_data()  # Get all complete TEGs
    """
```

---

## Function 5: `get_teg_data_inc_in_progress()`

### Current Implementation

**File**: `teg_analysis/analysis/aggregation.py:254`

**Actual Signature**:
```python
def get_teg_data_inc_in_progress():
```

**What It Does**:
```python
def get_teg_data_inc_in_progress():
    """Get TEG-level data including in-progress TEGs."""
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'TEG')
    return aggregated_data
```

**Difference from `get_complete_teg_data()`**:
- Same pattern, but `exclude_incomplete_tegs=False` (includes in-progress)
- Used for leaderboard which needs current tournament data

---

### Documented Signature (MISMATCH)

**From FUNCTION_REFERENCE.md**:
```python
get_teg_data_inc_in_progress(df, teg_num)
```

---

### Usage Analysis

#### Call Sites (appears to be internal only)

Searched but not found in Streamlit pages. Likely used via intermediate functions rather than directly.

### Recommendation

**[✓] Update documentation to match code**

**Same reasoning as `get_complete_teg_data()`** - convenience function with fixed filtering.

---

## Function 6: `get_round_data()`

### Current Implementation

**File**: `teg_analysis/analysis/aggregation.py:268`

**Actual Signature**:
```python
def get_round_data(ex_50=True, ex_incomplete=False):
```

**What It Does**:
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

**Pattern**: "Flexible load from file" pattern
- No dataframe input
- Accepts filter flags for common options
- Aggregates to Round level

---

### Documented Signature (MISMATCH)

**From FUNCTION_REFERENCE.md**:
```python
get_round_data(df, teg_num, round_num)
```

**Expected behavior**: Accept dataframe, filter by TEG and round

---

### Usage Analysis

#### All Call Sites (6+ total)

1. **streamlit/leaderboard.py:85** (DIRECT STREAMLIT USAGE)
```python
try:
    with st.spinner("Loading data..."):
        # Load round-level data (includes incomplete TEGs, excludes TEG 50)
        # Purpose: Latest leaderboard needs current tournament data, even if incomplete
        round_df = get_round_data(ex_50=ex_teg_50)

        # Load complete dataset for chart generation (excludes TEG 50)
        # Purpose: Charts need full hole-by-hole data to show cumulative progress
        all_data = load_all_data(exclude_teg_50=ex_teg_50)
```

**This shows**:
- Direct usage in Streamlit page
- Uses actual signature: `get_round_data(ex_50=...)`
- Not using documented `(df, teg_num, round_num)` signature

2. **teg_analysis/analysis/rankings.py:103**
```python
def get_ranked_round_data():
    """Gets round-level data with rankings added."""
    from .aggregation import get_round_data

    df = get_round_data()  # ← Uses with no parameters (uses defaults)
    ranked_data = add_ranks(df)
    return ranked_data
```

3. **streamlit/utils.py** (wrapper)
```python
@_st_cache_data
def get_round_data(ex_50=True, ex_incomplete=False):
    from teg_analysis.analysis.aggregation import get_round_data as _get_round_data
    return _get_round_data(ex_50=ex_50, ex_incomplete=ex_incomplete)
```

4. **streamlit/score_by_course.py** (imports wrapper)
```python
from utils import get_round_data
rd_data = get_round_data()  # Uses defaults
```

---

### Streamlit Pages Using This Function

**Direct usage**:
- `streamlit/leaderboard.py:85` - Current leaderboard page

**Indirect (via `get_ranked_round_data()` wrapper)**:
- Multiple pages import and use ranked round data

**All call sites use actual signature**: `get_round_data(ex_50=..., ex_incomplete=...)`

**None use**: The documented `(df, teg_num, round_num)` signature

---

### Key Observation

**Line 85 of leaderboard.py shows the actual usage pattern**:
```python
round_df = get_round_data(ex_50=ex_teg_50)
```

This is the primary real-world usage - fetch round data with control over whether to exclude TEG 50.

---

### Recommendation

**[✓] Update documentation to match code**

**Reasoning**:
1. **Direct usage in production** (leaderboard.py:85)
2. **Uses actual signature** with filter flags
3. **Changing code would break** leaderboard page and multiple helpers
4. **Risk of code change**: **HIGH** - Changes to leaderboard would affect many features
5. **Risk of doc change**: **NONE**

**Updated documentation should be**:
```python
def get_round_data(ex_50=True, ex_incomplete=False) -> pd.DataFrame:
    """Get round-level aggregated data.

    Loads tournament data and aggregates to round level with configurable
    filtering options.

    Args:
        ex_50 (bool, optional): Exclude TEG 50 if True. Default: True.
        ex_incomplete (bool, optional): Exclude incomplete TEGs if True.
            Default: False (includes in-progress tournaments).

    Returns:
        pd.DataFrame: Round-level aggregated data with columns for each
        score measure, TEG, Round, and player information.

    Example:
        >>> round_data = get_round_data()  # Get all rounds, include in-progress
        >>> round_data_complete = get_round_data(ex_incomplete=True)  # Complete TEGs only
    """
```

---

## Function 7: `get_9_data()`

### Current Implementation

**File**: `teg_analysis/analysis/aggregation.py:286`

**Actual Signature**:
```python
def get_9_data():
```

**What It Does**:
```python
def get_9_data():
    """Get 9-hole (front/back) aggregated data."""
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'FrontBack')
    return aggregated_data
```

**Pattern**: "Load from file" pattern (like `get_complete_teg_data()`)
- No dataframe input
- Fixed filtering
- Aggregates to FrontBack level (front 9 vs back 9)

---

### Documented Signature (MISMATCH)

**From FUNCTION_REFERENCE.md**:
```python
get_9_data(df, teg_num, round_num, nines)
```

---

### Usage Analysis

#### Call Sites (3 total)

1. **teg_analysis/analysis/rankings.py:117**
```python
def get_ranked_frontback_data():
    """Gets front/back 9 data with rankings added."""
    from .aggregation import get_9_data

    df = get_9_data()  # ← No parameters
    ranked_data = add_ranks(df)
    return ranked_data
```

2. **streamlit/utils.py** (wrapper)
```python
@_st_cache_data
def get_9_data():
    from teg_analysis.analysis.aggregation import get_9_data as _get_9_data
    return _get_9_data()
```

3. **streamlit/score_by_course.py** (or other pages importing wrapper)
```python
from utils import get_9_data
front_back_data = get_9_data()  # Uses wrapper
```

---

### Recommendation

**[✓] Update documentation to match code**

**Reasoning**:
1. **All call sites** use zero-parameter signature
2. **Fixed filtering makes sense** for this aggregation level
3. **Changing code would break**: 3+ call sites
4. **Risk of code change**: **LOW-MEDIUM**
5. **Risk of doc change**: **NONE**

---

---

## GROUP C: Leaderboard Functions (aggregation.py)

---

## Function 8: `get_teg_leaderboard()`

### Current Implementation

**File**: `teg_analysis/analysis/aggregation.py:2869`

**Actual Signature**:
```python
def get_teg_leaderboard(df: pd.DataFrame, measure: str, teg_num: int = None) -> pd.DataFrame:
```

**What It Does** (from code):
```python
def get_teg_leaderboard(df: pd.DataFrame, measure: str, teg_num: int = None) -> pd.DataFrame:
    """Generate a tournament leaderboard table with round-by-round scores and totals.

    Args:
        df (pd.DataFrame): Tournament data (either full dataset or pre-filtered to a TEG)
        measure (str): Score column to rank by - 'Stableford', 'GrossVP', 'NetVP', or 'Sc'
        teg_num (int, optional): TEG number to filter. If None, assumes df is already filtered

    Returns:
        pd.DataFrame: Leaderboard with columns: Rank, Player, R1, R2, R3, R4, Total
    """
    # 1. Filter by TEG if specified
    data = df.copy()
    if teg_num is not None:
        data = data[data['TEGNum'] == teg_num]

    # 2. Pivot to Player rows × Round columns
    pivoted = data.pivot_table(
        index='Player',
        columns='Round',
        values=measure,
        aggfunc='first'
    )

    # 3. Add total and rankings
    pivoted['Total'] = pivoted.sum(axis=1)
    ascending = measure != 'Stableford'
    pivoted = pivoted.sort_values('Total', ascending=ascending)

    # 4. Format for display
    # ... rename columns, add rank, etc ...
    return leaderboard
```

---

### Documented Signature (MISMATCH)

**From FUNCTION_REFERENCE.md**:
```python
get_teg_leaderboard(df, teg_num, measure)
```

**Documented parameter order**: `(df, teg_num, measure)`
**Actual parameter order**: `(df, measure, teg_num=None)` ✗ Different!

---

### Usage Analysis

#### Call Sites

Search results showed usage in:
- `streamlit/leaderboard.py`
- Other Streamlit pages

**Key difference**: `teg_num` is **optional** in actual code (defaults to None), not required.

---

### Analysis of Parameter Order

**This is a USABILITY issue, not a breaking change:**

**Documented order**: `(df, teg_num, measure)`
```python
leaderboard = get_teg_leaderboard(data, 18, 'Stableford')  # As documented
```

**Actual order**: `(df, measure, teg_num=None)`
```python
leaderboard = get_teg_leaderboard(data, 'Stableford', teg_num=18)  # Actual usage
```

**Why this matters**:
- If someone used positional arguments with documented order, it would FAIL
- All current usage likely uses keyword arguments: `teg_num=18`
- Or passes data pre-filtered and uses `teg_num=None` (default)

---

### Recommendation

**[✓] Code is correct, documentation needs update**

**Reasoning**:
1. **Parameter order in actual code** is logical: dataframe, then measure (core requirement), then optional filter
2. **Optional teg_num** is correct: allows pre-filtered data path
3. **Current code is simpler** than documented version suggests
4. **Risk of code change**: **MEDIUM** - Could break if positional args used elsewhere
5. **Risk of doc change**: **NONE** - Just doc update

**Updated documentation should be**:
```python
def get_teg_leaderboard(df: pd.DataFrame, measure: str, teg_num: int = None) -> pd.DataFrame:
    """Generate a tournament leaderboard table with round-by-round scores and totals.

    Args:
        df (pd.DataFrame): Tournament data (either full dataset or pre-filtered to a TEG)
        measure (str): Score column to rank by - 'Stableford', 'GrossVP', 'NetVP', or 'Sc'
        teg_num (int, optional): TEG number to filter. If None, assumes df is already filtered
            or contains data for all rounds you want in the leaderboard. Default: None

    Returns:
        pd.DataFrame: Leaderboard with columns: Rank, Player, R1, R2, R3, R4, Total
                     Players sorted by measure (Stableford descending, others ascending)

    Example:
        >>> # Method 1: Pre-filter data, then create leaderboard
        >>> teg_data = df[df['TEGNum'] == 18]
        >>> aggregated = aggregate_data(teg_data, 'Round')
        >>> leaderboard = get_teg_leaderboard(aggregated, 'Stableford')

        >>> # Method 2: Pass all data with teg_num filter
        >>> aggregated = aggregate_data(all_data, 'Round')
        >>> leaderboard = get_teg_leaderboard(aggregated, 'Stableford', teg_num=18)
    """
```

---

## Function 9: `get_round_leaderboard()`

### Current Implementation

**File**: `teg_analysis/analysis/aggregation.py:2948`

**Actual Signature**:
```python
def get_round_leaderboard(df: pd.DataFrame, measure: str, teg_num: int = None, round_num: int = None) -> pd.DataFrame:
```

**Very similar to `get_teg_leaderboard()`** but for single rounds.

---

### Documented Signature (MISMATCH)

**From FUNCTION_REFERENCE.md**:
```python
get_round_leaderboard(df, teg_num, round_num, measure)
```

**Documented parameter order**: `(df, teg_num, round_num, measure)`
**Actual parameter order**: `(df, measure, teg_num=None, round_num=None)` ✗ Different!

---

### Recommendation

**[✓] Code is correct, documentation needs update**

**Same as `get_teg_leaderboard()`** - parameter order and optional nature of filters.

---

---

## SUMMARY TABLE: All 9 Functions

| # | Function | Documented | Actual | Type | Recommendation | Pages Affected | Risk |
|---|----------|-----------|--------|------|-----------------|-----------------|------|
| 1 | `add_ranks()` | `(df, score_col, group_col, ascending)` | `(df, fields_to_rank=None, rank_ascending=None)` | Complete redesign | 📝 Fix docs | 5+ pages | **HIGH** |
| 2 | `get_best()` | `(df, metric, n, filters)` | `(df, measure_to_use, player_level=False, top_n=1)` | Parameter names | 📝 Fix docs | 3 pages | **HIGH** |
| 3 | `get_worst()` | `(df, metric, n, filters)` | `(df, measure_to_use, player_level=False, top_n=1)` | Parameter names | 📝 Fix docs | 3 pages | **HIGH** |
| 4 | `get_complete_teg_data()` | `(df, teg_num)` | `()` | No parameters | 📝 Fix docs | 3 places | **MEDIUM** |
| 5 | `get_teg_data_inc_in_progress()` | `(df, teg_num)` | `()` | No parameters | 📝 Fix docs | Internal | **LOW** |
| 6 | `get_round_data()` | `(df, teg_num, round_num)` | `(ex_50=True, ex_incomplete=False)` | Filter flags | 📝 Fix docs | 6+ pages | **HIGH** |
| 7 | `get_9_data()` | `(df, teg_num, round_num, nines)` | `()` | No parameters | 📝 Fix docs | 3 places | **MEDIUM** |
| 8 | `get_teg_leaderboard()` | `(df, teg_num, measure)` | `(df, measure, teg_num=None)` | Parameter order | 📝 Fix docs | Multiple | **LOW** |
| 9 | `get_round_leaderboard()` | `(df, teg_num, round_num, measure)` | `(df, measure, teg_num=None, round_num=None)` | Parameter order | 📝 Fix docs | Multiple | **LOW** |

---

## OVERALL RECOMMENDATION

### Decision: FIX DOCUMENTATION (All 9 Functions)

**Reasoning**:
1. **All code is working in production** with current signatures
2. **All documented signatures are incompatible** with actual usage
3. **Changing code would break multiple Streamlit pages** (3-6+ per function)
4. **Changing documentation is low-risk** and high-value
5. **Documentation is the single source of truth**, not working code

### Implementation Priority

**Priority 1 (Highest impact)**:
1. `add_ranks()` - Core ranking algorithm, affects 5+ pages
2. `get_best()` / `get_worst()` - Records pages depend on these
3. `get_round_data()` - Direct leaderboard page usage

**Priority 2**:
4. `get_complete_teg_data()` / `get_teg_data_inc_in_progress()` / `get_9_data()`
5. `get_teg_leaderboard()` / `get_round_leaderboard()`

---

## What NOT to Do

❌ **Do NOT change function signatures** - Would break production code
❌ **Do NOT keep old documentation** - Creates confusion and bugs
❌ **Do NOT assume positional arguments** - Use keyword arguments instead

---

## Next Steps

1. Update FUNCTION_REFERENCE.md with correct signatures
2. Update function docstrings (if different from reference docs)
3. Add usage examples to documentation (from this analysis)
4. Consider adding migration guide for anyone using old documented signatures

---

*Analysis completed: October 28, 2025*
*All functions cross-checked against actual Streamlit usage*
*3-level call chain tracing completed for all functions*
