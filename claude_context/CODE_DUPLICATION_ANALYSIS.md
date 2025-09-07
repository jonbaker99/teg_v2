# TEG Codebase Duplication Analysis & Consolidation Recommendations

**Analysis Date**: December 30, 2024  
**Total Functions Analyzed**: 148  
**Approach**: Distinguish true code duplication (90%+ identical) from similar naming with different logic

## Executive Summary

The codebase has grown organically and contains significant **true code duplication** that impacts maintainability. However, many functions with similar names actually serve different purposes and should remain separate for readability. Focus consolidation efforts on functions with 90%+ identical code.

**Estimated Impact**: Reduce ~15-20 functions without losing functionality or readability.

---

## 🚨 Critical Issues (Fix Immediately)

### 1. Duplicate Function Definition
**Location**: `utils.py:1020` and `utils.py:1037`  
**Issue**: `get_best` function is defined **twice** with different logic  
**Impact**: Bug - second definition overwrites first  
**Action**: Merge logic or rename one function

---

## 🔥 High Priority Consolidation (90%+ Code Duplication)

### 1. Data Aggregation Functions
**Location**: `utils.py:878-905`  
**Functions**: 
- `get_complete_teg_data()`
- `get_teg_data_inc_in_progress()`  
- `get_round_data(ex_50, ex_incomplete)`
- `get_9_data()`
- `get_Pl_data()`

**Current Pattern** (identical 3-line functions):
```python
def get_X_data():
    all_data = load_all_data(exclude_teg_50=X, exclude_incomplete_tegs=Y)
    aggregated_data = aggregate_data(all_data, 'LEVEL')
    return aggregated_data
```

**Consolidation Recommendation**:
```python
@st.cache_data
def get_aggregated_data(level, exclude_teg_50=True, exclude_incomplete_tegs=False):
    """
    Get aggregated data at specified level with filtering options.
    
    Args:
        level: 'TEG', 'Round', 'FrontBack', or 'Player'
        exclude_teg_50: Exclude TEG 50 from analysis
        exclude_incomplete_tegs: Exclude incomplete tournaments
    """
    all_data = load_all_data(exclude_teg_50, exclude_incomplete_tegs)
    return aggregate_data(all_data, level)

# Convenience wrappers with clear names (optional)
def get_complete_teg_data():
    return get_aggregated_data('TEG', exclude_incomplete_tegs=True)

def get_round_data(ex_50=True, ex_incomplete=False):
    return get_aggregated_data('Round', ex_50, ex_incomplete)
```

### 2. Ranking Functions
**Location**: `utils.py:1003-1018`  
**Functions**:
- `get_ranked_teg_data()`
- `get_ranked_round_data()` 
- `get_ranked_frontback_data()`

**Current Pattern** (identical 3-line functions):
```python
def get_ranked_X_data():
    df = get_X_data()
    ranked_data = add_ranks(df)
    return ranked_data
```

**Consolidation Recommendation**:
```python
@st.cache_data
def get_ranked_data(level, **aggregation_kwargs):
    """Get ranked data at specified aggregation level"""
    df = get_aggregated_data(level, **aggregation_kwargs)
    return add_ranks(df)

# Convenience wrappers (optional)
def get_ranked_teg_data():
    return get_ranked_data('TEG', exclude_incomplete_tegs=True)
```

---

## 📋 Medium Priority Consolidation

### 3. Scorecard Title Generation
**Location**: `scorecard_utils.py:154-171` and `scorecard_utils.py:659-676`  
**Issue**: Identical title/subheader generation logic in desktop and mobile functions

**Consolidation Recommendation**:
```python
def generate_scorecard_metadata(player_code, teg_num, round_num, title=None, subheader=None):
    """Extract common title/subheader generation logic"""
    # Move identical logic here
    return title, subheader, player_name, metadata
```

Keep separate HTML generation functions but extract the common metadata logic.

---

## ✅ Keep Separate (Good Naming, Different Logic)

### State Management Functions
- `initialize_update_state()` vs `initialize_deletion_state()`
- **Reason**: Different state variables, different workflows
- **Verdict**: Clear naming, different purposes - keep separate

### Formatting Functions  
- `format_vs_par()`, `format_record_value()`, `format_value()` (charts), `format_value()` (leaderboards)
- **Reason**: Different formatting logic for different contexts
- **Verdict**: Context-specific formatting - keep separate

### Analysis Functions
- `get_best()` vs `get_worst()`
- **Reason**: Different ranking logic (min vs max, Stableford handling)
- **Verdict**: Logically different operations - keep separate

### Scorecard Generation Functions
- Desktop vs Mobile HTML functions
- **Reason**: Different HTML structure and CSS classes needed
- **Verdict**: Keep separate rendering, extract common metadata logic only

---

## Implementation Approach

### Phase 1: Critical Fixes
1. Fix duplicate `get_best` function definition
2. Test existing functionality to ensure no breaks

### Phase 2: High-Impact Consolidation  
1. Consolidate data aggregation functions (5→1 with wrappers)
2. Consolidate ranking functions (3→1 with wrappers)
3. Update all calling code
4. Comprehensive testing

### Phase 3: Medium-Impact Improvements
1. Extract common scorecard metadata logic
2. Review any other identified duplication

### Testing Strategy
- Keep existing function names as wrappers initially
- Gradual migration with extensive testing
- Remove wrappers only after confirming no breaks

---

## Expected Benefits

**Maintainability**: Reduce 90%+ duplicate code blocks  
**Bug Reduction**: Fix critical duplicate function issue  
**Performance**: Minimal impact (mostly cached functions)  
**Readability**: Maintain clear function names while reducing implementation duplication  

**Estimated Function Reduction**: 15-20 functions (148 → ~128-133)  
**Code Reduction**: ~200-300 lines of duplicate code

---

## Notes

- Analysis based on comprehensive function catalogue of 148 functions
- Prioritizes maintainability over pure function count reduction
- Maintains existing naming conventions for readability
- Focuses on true duplication rather than similar naming
- Preserves caching decorators and existing interfaces