# Task 5: Function Duplication & Similarity Analysis - Summary Report

**Date**: October 18, 2025
**Analysis Scope**: 530 functions across 68 Python files
**Analysis Tools**: AST-based extraction, difflib similarity matching, pattern recognition

---

## Executive Summary

This comprehensive analysis identified **significant code duplication** throughout the TEG codebase, with **8 sets of exact duplicates**, **10 near-duplicates**, and **38 functions with the same name but different implementations** across multiple files.

### Key Findings

1. **Within-File Duplicates**: 9 instances where the same function appears multiple times in a single file
2. **Cross-File Duplicates**: Multiple utility functions duplicated across commentary and helper modules
3. **Pattern Duplication**: Common patterns like vs_par formatting, TEG filtering, and player filtering appear in 18-31 files
4. **High-Impact Targets**: Top 15 duplicates account for 752 lines of duplicated code

### Statistics at a Glance

- **Total Functions**: 530
- **Functions in utils.py**: 102 (largest concentration)
- **Functions in helpers/**: 173
- **Functions in page files**: 235
- **Exact Duplicates**: 8 sets (affecting 19 function instances)
- **Near Duplicates (80-99% similar)**: 10 pairs
- **Same-Name Different Implementation**: 38 function names

---

## Detailed Findings

### 1. WITHIN-FILE DUPLICATES (Most Critical)

These are **identical or near-identical functions appearing multiple times in the same file** - clear refactoring targets.

#### File: `streamlit/helpers/history_data_processing.py`
**Most severe case** - Contains 3 sets of duplicated functions:

1. **`extract_teg_num`** (8 lines)
   - Line 349 and Line 639
   - **Recommendation**: Define once at module level

2. **`check_winner_completeness`** (34 lines, 85.2% similar)
   - Line 368 and Line 658
   - **Recommendation**: Keep only one version

3. **`display_completeness_status`** (16-18 lines, 85.7% similar)
   - Line 404 and Line 694
   - **Recommendation**: Consolidate to single function

4. **`calculate_and_save_missing_winners`** (80 lines, 93.9% similar!)
   - Line 422 and Line 714
   - **HIGH IMPACT**: 160 duplicated lines in one file
   - **Recommendation**: Immediate consolidation priority

#### File: `streamlit/commentary/generate_tournament_commentary_v2.py`

1. **`get_api_key`** - 2 versions (9 lines and 3 lines)
   - Lines 443 and 453
   - **Recommendation**: Keep longer version only

2. **`calc_wins_before`** (7 lines)
   - Lines 740 and 2000
   - **Recommendation**: Define once at top of file

#### File: `streamlit/commentary/generate_round_report.py`

1. **`get_api_key`** - 2 versions (9 lines and 3 lines)
   - Lines 225 and 235

#### Other Files:
- `streamlit/player_history.py`: `teg_sort_key` (2 times)
- `streamlit/commentary/generate_commentary.py`: `read_file` (2 times)

**Total Impact**: ~370 lines of duplicated code within files that can be immediately eliminated

---

### 2. CROSS-FILE EXACT DUPLICATES

These are **identical functions in different files** - candidates for consolidation into shared modules.

#### High-Impact Duplicates

| Function | Occurrences | Lines | Files | Impact Score |
|----------|-------------|-------|-------|--------------|
| `safe_int` | 3 | 8 | 3 files | 24 |
| `calculate_hole_difficulty` | 2 | 32 | 2 files | 64 |
| `plan_wait` | 2 | 19 | 2 files | 38 |
| `get_api_key` | 2 | 3 | 2 files | 6 |
| `__init__`, `_now`, `_prune`, `used_last_min` | 2 each | 2-5 | 2 files each | 8-10 each |

#### Detailed Analysis

**1. `safe_int` (3 occurrences, 24 line impact)**
- `streamlit/commentary/round_data_loader.py:24`
- `streamlit/commentary/round_pattern_analysis.py:15`
- `streamlit/commentary/unified_round_data_loader.py:31`
- **Recommendation**: Move to `streamlit/utils.py` as it's a general utility function

**2. `calculate_hole_difficulty` (2 occurrences, 64 line impact)**
- `streamlit/commentary/round_data_loader.py:63`
- `streamlit/commentary/unified_round_data_loader.py:479`
- **Recommendation**: Create `streamlit/helpers/golf_calculations.py` for golf-specific calculations

**3. Rate-limiting functions (`plan_wait`, `_now`, `_prune`, `used_last_min`, `acquire`)**
- All duplicated between:
  - `streamlit/commentary/generate_round_report.py`
  - `streamlit/commentary/generate_tournament_commentary_v2.py`
- **Recommendation**: Extract to `streamlit/helpers/api_rate_limiting.py`

**4. API key management (`get_api_key` - multiple versions)**
- Appears in 4 different places with slight variations
- **Recommendation**: Standardize and move to `streamlit/utils.py`

---

### 3. NEAR DUPLICATES (80-99% Similar)

These functions are **almost identical** with minor variations - candidates for parameterization.

#### Top 5 by Impact

| Rank | Function | Similarity | Lines | Impact | Recommendation |
|------|----------|------------|-------|--------|----------------|
| 1 | `safe_create_message` | 91.1% | 83 | 166 | Extract common logic, parameterize differences |
| 2 | `calculate_and_save_missing_winners` | 93.9% | 80 | 160 | Consolidate (same file!) |
| 3 | `format_course_info_section` | 91.1% | 46 | 92 | Move to helpers/commentary_formatting.py |
| 4 | `get_previous_round_scores` | 96.6% | 36 | 72 | Use unified version only |
| 5 | `check_winner_completeness` | 85.2% | 34 | 68 | Consolidate (same file!) |

**Total Near-Duplicate Impact**: 558 lines that could be reduced to ~280 lines (50% reduction)

---

### 4. SAME NAME, DIFFERENT IMPLEMENTATION

These functions have **identical names but different purposes** - potential naming issues or legitimate variations.

#### High-Priority Cases

**1. `render_report` (5 occurrences)**
- `streamlit/102TEG Results.py`
- `streamlit/latest_teg_context.py`
- `streamlit/teg_reports.py`
- `streamlit/teg_reports_17brief.py`
- `streamlit/teg_reports_17full.py`
- Similarity range: 43.5% - 78.3%
- **Analysis**: These are genuinely different report rendering functions
- **Recommendation**: Rename to be more specific:
  - `render_teg_results_report`
  - `render_latest_teg_report`
  - `render_brief_tournament_report`
  - `render_full_tournament_report`

**2. `format_value` (4 occurrences)**
- `streamlit/500Handicaps.py`
- `streamlit/leaderboard_utils.py`
- `streamlit/make_charts.py`
- `streamlit/helpers/records_identification.py`
- Similarity range: 0% - 26.3%
- **Recommendation**: Rename based on context:
  - `format_handicap_value`
  - `format_leaderboard_value`
  - `format_chart_value`
  - `format_record_value`

**3. `get_api_key` (4-5 occurrences with variations)**
- Multiple files, multiple implementations
- **Recommendation**: Create single canonical version in utils.py

**4. `load_markdown` (3 occurrences)**
- Different implementations for loading markdown files
- **Recommendation**: Consolidate to single utility function

**5. `get_incomplete_tegs` (2 occurrences)**
- `streamlit/utils.py:831`
- `streamlit/helpers/history_data_processing.py:224`
- Only 9.3% similar - completely different implementations
- **Recommendation**: Rename one (probably the helper version) to `check_incomplete_tegs_status`

---

### 5. COMMON CODE PATTERNS

Analysis identified **repeated coding patterns** that could be abstracted into reusable functions.

#### Pattern Distribution

| Pattern | Functions | Files | Example Use Case | Recommendation |
|---------|-----------|-------|------------------|----------------|
| `teg_filtering` | 130 | 31 | Filtering data by TEG number | Create `filter_by_teg()` helper |
| `vs_par_formatting` | 51 | 18 | Formatting scores relative to par | Create `format_score_vs_par()` utility |
| `player_filtering` | 45 | 18 | Filtering data by player | Create `filter_by_player()` helper |
| `github_operations` | 44 | 9 | Git commit/push operations | Already in utils.py, ensure usage |
| `cache_clearing` | 15 | 5 | Clearing Streamlit caches | Standardize on utils.clear_all_caches() |
| `chart_creation` | 6 | 3 | Altair/Plotly chart creation | Consider chart factory pattern |

#### Detailed Pattern Analysis

**1. TEG Filtering Pattern (130 occurrences in 31 files)**

Common pattern:
```python
df[df['TEGNum'] == selected_teg]
df[df['TEG'] == f'TEG {teg_num}']
```

**Recommendation**: Create utility functions in `utils.py`:
```python
def filter_by_teg_number(df: pd.DataFrame, teg_num: int) -> pd.DataFrame
def filter_by_teg_string(df: pd.DataFrame, teg_str: str) -> pd.DataFrame
```

**2. VS Par Formatting Pattern (51 occurrences in 18 files)**

Common variations:
```python
f"+{value}" if value > 0 else str(value)
f"+{abs(value)}" if value > 0 else f"-{abs(value)}"
```

**Recommendation**: Expand `format_vs_par_value()` in utils and use consistently

**3. Player Filtering Pattern (45 occurrences in 18 files)**

Common pattern:
```python
df[df['Player'] == selected_player]
df[df['Player'].isin(player_list)]
```

**Recommendation**: Create `filter_by_player()` and `filter_by_players()` utilities

---

### 6. FILE COMPLEXITY ANALYSIS

Files with highest function counts - **candidates for splitting**.

| Rank | File | Functions | Total Lines | Avg Size | Status |
|------|------|-----------|-------------|----------|--------|
| 1 | `utils.py` | 102 | 4,048 | 39.7 | **CRITICAL** - Split into modules |
| 2 | `generate_tournament_commentary_v2.py` | 52 | 2,142 | 41.2 | Split commentary logic |
| 3 | `streak_analysis_processing.py` | 29 | 1,100 | 37.9 | Consider splitting |
| 4 | `generate_round_report.py` | 19 | 1,112 | 58.5 | Refactor with v2 |
| 5 | `history_data_processing.py` | 19 | 759 | 39.9 | Remove duplicates first |

**`utils.py` Analysis (102 functions, 4,048 lines)**

This file is a **monolith** that should be split into focused modules. Based on function analysis, suggested split:

1. **`utils/data_loading.py`** (~25 functions)
   - File reading (GitHub/local)
   - CSV/Parquet loading
   - All-data loading functions

2. **`utils/github_operations.py`** (~15 functions)
   - GitHub API interactions
   - Commit/push operations
   - Branch management

3. **`utils/data_processing.py`** (~20 functions)
   - TEG data processing
   - Score calculations
   - Data transformations

4. **`utils/formatting.py`** (~15 functions)
   - Value formatting
   - String formatting
   - Display helpers

5. **`utils/caching.py`** (~10 functions)
   - Cache management
   - Data caching
   - Volume management

6. **`utils/summary_generation.py`** (~17 functions)
   - Round summaries
   - Tournament summaries
   - Report generation

7. **Keep in `utils.py`** (~20 core functions)
   - Most commonly used utilities
   - Re-export from modules for backward compatibility

---

## High-Impact Refactoring Opportunities

### PRIORITY 1: Within-File Duplicates (Immediate wins)

**Estimated Effort**: 2-3 hours
**Estimated Impact**: Eliminate ~370 lines of duplicate code

1. **`streamlit/helpers/history_data_processing.py`**
   - Remove duplicate `extract_teg_num`, `check_winner_completeness`, `display_completeness_status`
   - Consolidate two `calculate_and_save_missing_winners` functions (93.9% similar!)
   - **Savings**: ~180 lines

2. **`streamlit/commentary/generate_tournament_commentary_v2.py`**
   - Remove duplicate `get_api_key` and `calc_wins_before`
   - **Savings**: ~16 lines

3. **Other files** (player_history.py, generate_round_report.py, generate_commentary.py)
   - **Savings**: ~30 lines

### PRIORITY 2: Commentary Module Consolidation

**Estimated Effort**: 4-6 hours
**Estimated Impact**: Eliminate ~250 lines, simplify maintenance

**Files to consolidate**:
- `generate_round_report.py` (19 functions, 1,112 lines)
- `generate_tournament_commentary_v2.py` (52 functions, 2,142 lines)

**Duplicated functions between these two**:
- `__init__`, `_now`, `_prune`, `used_last_min`, `plan_wait`, `acquire`, `safe_create_message`, `get_api_key`, `format_course_info_section`

**Recommendation**: Create `streamlit/helpers/api_rate_limiting.py` to extract rate-limiting logic shared between both files.

### PRIORITY 3: Utility Function Standardization

**Estimated Effort**: 3-4 hours
**Estimated Impact**: Single source of truth for common operations

**Functions to centralize in `utils.py`**:

1. **`safe_int`** (currently in 3 files)
2. **`format_vs_par_value`** (currently in 2 helpers)
3. **`load_markdown`** (currently in 3 files with different implementations)
4. **`render_report`** (5 versions - needs renaming + potential consolidation)
5. **`altair_theme`** (2 versions - move to styles/)

### PRIORITY 4: Data Loader Consolidation

**Estimated Effort**: 4-5 hours
**Estimated Impact**: Reduce commentary data loading complexity

**Files to consolidate**:
- `round_data_loader.py`
- `unified_round_data_loader.py`

**Shared duplicated functions**:
- `safe_int`, `calculate_hole_difficulty`, `get_previous_round_scores`, `calculate_tournament_projections`

**Recommendation**: The "unified" version appears to be the newer, more complete version. Migrate all usage to unified version and deprecate the older one.

### PRIORITY 5: Pattern Abstraction

**Estimated Effort**: 6-8 hours
**Estimated Impact**: Reduce repetitive code across entire codebase

Create utility functions for the most common patterns:

1. **Data Filtering Utilities** (`utils/filtering.py`)
   ```python
   filter_by_teg_number(df, teg_num)
   filter_by_player(df, player_name)
   filter_by_course(df, course_name)
   ```

2. **Formatting Utilities** (expand `utils/formatting.py`)
   ```python
   format_vs_par(score, par)
   format_score_with_sign(value)
   format_rank(rank, total)
   ```

3. **Cache Management** (standardize)
   - Ensure all cache clearing uses `utils.clear_all_caches()`
   - Document cache strategy

---

## Refactoring Roadmap

### Phase 1: Quick Wins (Week 1)
**Goal**: Eliminate within-file duplicates

- [ ] Fix `history_data_processing.py` duplicates (~180 lines saved)
- [ ] Fix `generate_tournament_commentary_v2.py` duplicates
- [ ] Fix `generate_round_report.py` duplicates
- [ ] Fix `player_history.py` duplicates
- [ ] **Total saved**: ~370 lines
- [ ] **Tests**: Run full application to ensure no breaks

### Phase 2: Utility Consolidation (Week 2)
**Goal**: Centralize common utilities

- [ ] Move `safe_int` to `utils.py`
- [ ] Consolidate `format_vs_par_value` functions
- [ ] Consolidate `load_markdown` functions
- [ ] Standardize `get_api_key` implementation
- [ ] Move `altair_theme` to `styles/`
- [ ] **Tests**: Verify all imports work correctly

### Phase 3: Commentary Module Refactoring (Week 3)
**Goal**: Clean up commentary generation

- [ ] Extract rate-limiting functions to `helpers/api_rate_limiting.py`
- [ ] Update imports in `generate_round_report.py`
- [ ] Update imports in `generate_tournament_commentary_v2.py`
- [ ] Consolidate data loaders (use unified version)
- [ ] **Tests**: Generate test commentary to verify

### Phase 4: Pattern Abstraction (Week 4)
**Goal**: Replace repeated patterns with utilities

- [ ] Create `filter_by_teg_number()` utility
- [ ] Create `filter_by_player()` utility
- [ ] Create standardized formatting functions
- [ ] Update high-frequency files to use new utilities
- [ ] **Tests**: Comprehensive testing of affected pages

### Phase 5: utils.py Decomposition (Future)
**Goal**: Break down monolithic utils.py

- [ ] Create `utils/` package structure
- [ ] Split into focused modules (data_loading, github, etc.)
- [ ] Maintain backward compatibility via re-exports
- [ ] Update documentation
- [ ] **Tests**: Extensive testing across all pages

---

## Recommendations Summary

### Immediate Actions (Do This Week)

1. **Remove within-file duplicates** in `history_data_processing.py` (highest impact)
2. **Consolidate `safe_int`** to utils.py (used in 3 files)
3. **Fix `get_api_key`** duplicates (4-5 variations)
4. **Document** the refactoring in this task tracking

### Short-term Actions (Next 2-4 Weeks)

1. **Extract rate-limiting logic** from commentary modules
2. **Consolidate data loaders** (round_data_loader → unified version)
3. **Standardize formatting functions** (vs_par, values, etc.)
4. **Create filtering utilities** (by_teg, by_player)
5. **Rename ambiguous functions** (render_report variants, format_value variants)

### Long-term Actions (Next 1-3 Months)

1. **Split utils.py** into focused modules
2. **Create pattern libraries** for common operations
3. **Establish coding standards** to prevent future duplication
4. **Add pre-commit hooks** to detect duplicate code
5. **Regular duplication audits** (run this analysis quarterly)

---

## Code Quality Metrics

### Before Refactoring
- **Total functions**: 530
- **Estimated duplicated code**: ~1,100 lines (direct duplicates + near duplicates)
- **Functions with same name**: 17 function names with multiple implementations
- **Complexity hotspot**: utils.py (102 functions)

### After Phase 1-4 Refactoring (Projected)
- **Total functions**: ~480 (50 fewer due to consolidation)
- **Duplicated code**: ~300 lines (73% reduction)
- **Functions with same name**: ~5 (renamed for clarity)
- **Complexity**: utils.py split into 7 focused modules

### Key Metrics to Track
- Lines of code saved
- Number of import errors (should be 0)
- Page load time (should not increase)
- Test coverage (should increase)

---

## Technical Debt Assessment

### Current Technical Debt

**CRITICAL**:
- 370 lines of within-file duplicates (no excuse for this)
- 102-function monolithic utils.py file

**HIGH**:
- Duplicate functions across commentary modules
- Inconsistent naming (render_report, format_value)
- Repeated patterns instead of abstractions

**MEDIUM**:
- Data loader duplication (round vs unified)
- Scattered utility functions across page files

**LOW**:
- Minor variations in similar functions
- Some helper files could be further split

### Estimated Debt Payoff

| Category | Current Debt | After Refactor | Savings |
|----------|--------------|----------------|---------|
| Within-file duplicates | 370 lines | 0 lines | 370 lines |
| Cross-file duplicates | 250 lines | 0 lines | 250 lines |
| Near duplicates | 558 lines | 280 lines | 278 lines |
| Pattern duplication | ~500 lines | ~200 lines | 300 lines |
| **TOTAL** | **~1,678 lines** | **~480 lines** | **~1,198 lines (71%)** |

---

## Files Generated by This Analysis

1. **`docs/FUNCTION_DUPLICATION_ANALYSIS.md`** - Main analysis report
2. **`docs/FUNCTION_DUPLICATION_ENHANCED.md`** - Enhanced insights
3. **`docs/TASK_5_DUPLICATION_SUMMARY.md`** - This comprehensive summary
4. **`function_analysis.json`** - Detailed JSON data (all functions)
5. **`analyze_function_duplicates.py`** - Analysis script (reusable)
6. **`analyze_patterns.py`** - Pattern analysis script (reusable)

---

## Next Steps

1. **Review this analysis** with development team
2. **Prioritize refactoring** based on impact scores
3. **Create GitHub issues** for each priority item
4. **Establish** no-duplicate policy going forward
5. **Re-run analysis** after Phase 1 completion to measure progress

---

## Appendix: Analysis Methodology

### Tools Used
- **AST Parser**: Python's built-in `ast` module for function extraction
- **Difflib**: Sequence matching for similarity calculation
- **Pattern Matching**: Regular expressions for code pattern identification

### Similarity Calculation
- Line-by-line comparison after whitespace normalization
- SequenceMatcher ratio × 100 = similarity percentage
- Threshold: 80% = "near duplicate", 100% = "exact duplicate"

### Impact Scoring
- Impact = Occurrences × Line Count
- Higher score = higher refactoring priority
- Considers both duplication count and code volume

### Pattern Detection
- Keyword-based pattern matching in function source
- Groups patterns by semantic meaning
- Tracks file distribution for impact assessment

---

**Analysis completed**: October 18, 2025
**Total analysis time**: ~2 hours
**Functions analyzed**: 530 across 68 files
**Duplicates found**: 56 sets of duplicates/near-duplicates
**Recommended actions**: 25+ refactoring opportunities identified
