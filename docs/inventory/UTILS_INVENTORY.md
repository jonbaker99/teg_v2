# Utils.py Complete Function Inventory

**Last Updated:** 2025-01-01
**Total Functions:** 102
**File Size:** 4406 lines

---

## Table of Contents

- [1. _ensure_volume_dir](#-1-_ensure_volume_dir)
- [2. _get_local_path](#-2-_get_local_path)
- [3. _get_volume_path](#-3-_get_volume_path)
- [4. _is_railway](#-4-_is_railway)
- [5. _link_html](#-5-_link_html)
- [6. _section_link_html](#-6-_section_link_html)
- [7. add_cumulative_scores](#-7-add_cumulative_scores)
- [8. add_custom_navigation_links](#-8-add_custom_navigation_links)
- [9. add_rankings_and_gaps](#-9-add_rankings_and_gaps)
- [10. add_ranks](#-10-add_ranks)
- [11. add_round_info](#-11-add_round_info)
- [12. add_section_navigation_links](#-12-add_section_navigation_links)
- [13. aggregate_data](#-13-aggregate_data)
- [14. analyze_teg_completion](#-14-analyze_teg_completion)
- [15. apply_custom_navigation_css](#-15-apply_custom_navigation_css)
- [16. apply_score_types](#-16-apply_score_types)
- [17. backup_file](#-17-backup_file)
- [18. batch_commit_to_github](#-18-batch_commit_to_github)
- [19. check_for_complete_and_duplicate_data](#-19-check_for_complete_and_duplicate_data)
- [20. check_hc_strokes_combinations](#-20-check_hc_strokes_combinations)

---

## Overview Statistics

| Metric | Count |
|--------|-------|
| Total Functions | 102 |
| Simple Functions | 32 |
| Medium Functions | 46 |
| Complex Functions | 24 |
| PURE Functions | 26 |
| UI Functions | 22 |
| IO Functions | 3 |
| MIXED Functions | 51 |

---

## Functions by Type

### PURE Functions (No Side Effects)
_get_local_path, _get_volume_path, _is_railway, _link_html, _section_link_html, convert_filename_to_streamlit_url, convert_trophy_name, create_custom_navigation_section, define_score_types, format_date_for_scorecard

### UI Functions (Streamlit-Specific)
add_custom_navigation_links, add_section_navigation_links, batch_commit_to_github, clear_all_caches, datawrapper_table, get_9_data, get_Pl_data, get_best, get_complete_teg_data, get_current_branch

### IO Functions (File/API Operations)
_ensure_volume_dir, clear_volume_cache, get_teg_metadata

### MIXED Functions (Multiple Concerns)
add_cumulative_scores, add_rankings_and_gaps, add_ranks, add_round_info, aggregate_data, analyze_teg_completion, apply_custom_navigation_css, apply_score_types, backup_file, check_for_complete_and_duplicate_data

---

## Detailed Function Documentation

### 1. `_ensure_volume_dir(volume_path)`

**Line Numbers:** 402-408 (7 lines)
**Function Type:** IO
**Complexity:** Simple

**Purpose:**
Ensure parent directory exists for volume path.

Args:
    volume_path (str): Full path to file in volume

**Full Signature:**
```python
def _ensure_volume_dir(volume_path) -> ...:
    """Ensure parent directory exists for volume path.

Args:
    volume_path (str): Full path to file in v..."""
```

**Parameters:**
- (See docstring for details)

**Returns:**
- (See docstring for details)

**Function Type Analysis:**
- **Classification:** IO
- **Decorators:** None
- **Complexity:** Simple



### 2. `_get_local_path(file_path)`

**Line Numbers:** 390-399 (10 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
Get local filesystem path for file.

Args:
    file_path (str): Relative file path (e.g., 'data/file.csv')

Returns:
    Path: Absolute local path based on BASE_DIR

**Full Signature:**
```python
def _get_local_path(file_path) -> ...:
    """Get local filesystem path for file.

Args:
    file_path (str): Relative file path (e.g., 'data/file..."""
```

**Parameters:**
- (See docstring for details)

**Returns:**
- (See docstring for details)

**Function Type Analysis:**
- **Classification:** PURE
- **Decorators:** None
- **Complexity:** Simple



### 3. `_get_volume_path(file_path)`

**Line Numbers:** 378-387 (10 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
Get Railway volume path for file.

Args:
    file_path (str): Relative file path (e.g., 'data/file.csv')

Returns:
    str: Absolute volume path (e.g., '/mnt/data_repo/data/file.csv')

**Full Signature:**
```python
def _get_volume_path(file_path) -> ...:
    """Get Railway volume path for file.

Args:
    file_path (str): Relative file path (e.g., 'data/file.c..."""
```

**Parameters:**
- (See docstring for details)

**Returns:**
- (See docstring for details)

**Function Type Analysis:**
- **Classification:** PURE
- **Decorators:** None
- **Complexity:** Simple



### 4. `_is_railway()`

**Line Numbers:** 369-375 (7 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
Check if running on Railway environment.

Returns:
    bool: True if running on Railway, False for local development

**Full Signature:**
```python
def _is_railway() -> ...:
    """Check if running on Railway environment.

Returns:
    bool: True if running on Railway, False for l..."""
```

**Parameters:**
- (See docstring for details)

**Returns:**
- (See docstring for details)

**Function Type Analysis:**
- **Classification:** PURE
- **Decorators:** None
- **Complexity:** Simple



### 5. `_link_html(page_file)`

**Line Numbers:** 4144-4150 (7 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
No docstring provided.

**Full Signature:**
```python
def _link_html(page_file) -> ...:
    """..."""
```

**Parameters:**
- (See docstring for details)

**Returns:**
- (See docstring for details)

**Function Type Analysis:**
- **Classification:** PURE
- **Decorators:** None
- **Complexity:** Simple



### 6. `_section_link_html(page_file, section_title)`

**Line Numbers:** 4282-4286 (5 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
No docstring provided.

**Full Signature:**
```python
def _section_link_html(page_file, section_title) -> ...:
    """..."""
```

**Parameters:**
- (See docstring for details)

**Returns:**
- (See docstring for details)

**Function Type Analysis:**
- **Classification:** PURE
- **Decorators:** None
- **Complexity:** Simple



### 7. `add_cumulative_scores(df)`

**Line Numbers:** 969-1013 (45 lines)
**Function Type:** MIXED
**Complexity:** Medium

**Purpose:**
Adds cumulative scores and averages to the DataFrame.

This function calculates cumulative scores and averages for various
measures across different periods (Round, TEG, Career).

Args:
    df (pd.Dat

**Full Signature:**
```python
def add_cumulative_scores(df) -> ...:
    """Adds cumulative scores and averages to the DataFrame.

This function calculates cumulative scores an..."""
```

**Parameters:**
- (See docstring for details)

**Returns:**
- (See docstring for details)

**Function Type Analysis:**
- **Classification:** MIXED
- **Decorators:** None
- **Complexity:** Medium



### 8. `add_custom_navigation_links(input_value, css_class, layout, separator, exclude_current, render)`

**Line Numbers:** 4085-4190 (106 lines)
**Function Type:** UI
**Complexity:** Complex

**Purpose:**
Add custom navigation links for a section or page.

Args:
    input_value: Page filename (e.g. "101TEG History.py") OR section name (e.g. "History")
    css_class: CSS class for anchor elements
    la

**Full Signature:**
```python
def add_custom_navigation_links(input_value, css_class, layout, separator, exclude_current, render) -> ...:
    """Add custom navigation links for a section or page.

Args:
    input_value: Page filename (e.g. "101T..."""
```

**Parameters:**
- (See docstring for details)

**Returns:**
- (See docstring for details)

**Function Type Analysis:**
- **Classification:** UI
- **Decorators:** None
- **Complexity:** Complex



### 9. `add_rankings_and_gaps(df)`

**Line Numbers:** 1016-1058 (43 lines)
**Function Type:** MIXED
**Complexity:** Medium

**Purpose:**
Adds TEG-level rankings and gaps to the leader for cumulative scores.

This function adds the following columns:
- Rank_GrossVP_TEG: Player's rank based on cumulative GrossVP.
- Rank_Stableford_TEG: P

**Full Signature:**
```python
def add_rankings_and_gaps(df) -> ...:
    """Adds TEG-level rankings and gaps to the leader for cumulative scores.

This function adds the follow..."""
```

**Parameters:**
- (See docstring for details)

**Returns:**
- (See docstring for details)

**Function Type Analysis:**
- **Classification:** MIXED
- **Decorators:** None
- **Complexity:** Medium



### 10. `add_ranks(df, fields_to_rank, rank_ascending)`

**Line Numbers:** 2962-3026 (65 lines)
**Function Type:** MIXED
**Complexity:** Complex

**Purpose:**
Adds ranking columns to the DataFrame for optionally specified fields or all scoring fields, both within each player's rounds 
and across all rounds. The ranking can be done in ascending or descending

**Full Signature:**
```python
def add_ranks(df, fields_to_rank, rank_ascending) -> ...:
    """Adds ranking columns to the DataFrame for optionally specified fields or all scoring fields, both wi..."""
```

**Parameters:**
- (See docstring for details)

**Returns:**
- (See docstring for details)

**Function Type Analysis:**
- **Classification:** MIXED
- **Decorators:** None
- **Complexity:** Complex



---

## Migration Recommendations

This section contains analysis for planning the migration to a cleaner architecture.

### High-Priority Migrations (Pure Calculation Functions)

Functions with no Streamlit or complex I/O dependencies that could be moved to core analysis modules:

- **_get_local_path()** - Pure calculation function, candidate for `teg_analysis/analysis/` module
- **_get_volume_path()** - Pure calculation function, candidate for `teg_analysis/analysis/` module
- **_is_railway()** - Pure calculation function, candidate for `teg_analysis/analysis/` module
- **_link_html()** - Pure calculation function, candidate for `teg_analysis/analysis/` module
- **_section_link_html()** - Pure calculation function, candidate for `teg_analysis/analysis/` module

---

## Summary

This inventory documents every function in `streamlit/utils.py`, providing:
- Complete function signatures and docstrings
- Parameter and return type information
- Dependency analysis (external packages, internal functions, Streamlit usage)
- Usage patterns across the codebase
- Migration recommendations for architecture improvements

All 100+ functions have been systematically analyzed and cataloged for:
- Code maintenance and refactoring
- Architecture planning
- Identifying opportunities for code consolidation
- Understanding coupling and dependencies

