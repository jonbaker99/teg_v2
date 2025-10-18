# Task 5: Duplication Analysis - Findings Table

**Complete reference table of all duplicates found**

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **Total Functions Analyzed** | 530 |
| **Files Analyzed** | 68 |
| **Exact Duplicate Sets** | 8 |
| **Near Duplicate Pairs** | 10 |
| **Same-Name Different Implementation** | 38 function names |
| **Within-File Duplicates** | 9 instances |
| **Estimated Duplicate Lines** | ~1,678 |
| **Potential Lines Saved** | ~1,198 (71%) |

---

## EXACT DUPLICATES (100% Identical)

| # | Function | Occurrences | Lines | Impact | Files |
|---|----------|-------------|-------|--------|-------|
| 1 | `calculate_and_save_missing_winners` | 2 | 80 | 160 | history_data_processing.py (same file!) |
| 2 | `calculate_hole_difficulty` | 2 | 32 | 64 | round_data_loader.py, unified_round_data_loader.py |
| 3 | `plan_wait` | 2 | 19 | 38 | generate_round_report.py, generate_tournament_commentary_v2.py |
| 4 | `check_winner_completeness` | 2 | 34 | 68 | history_data_processing.py (same file!) |
| 5 | `safe_int` | 3 | 8 | 24 | round_data_loader.py, round_pattern_analysis.py, unified_round_data_loader.py |
| 6 | `display_completeness_status` | 2 | 16-18 | 34 | history_data_processing.py (same file!) |
| 7 | `extract_teg_num` | 2 | 8 | 16 | history_data_processing.py (same file!) |
| 8 | `calc_wins_before` | 2 | 7 | 14 | generate_tournament_commentary_v2.py (same file!) |
| 9 | `get_api_key` | 2 | 3 | 6 | generate_round_report.py, generate_tournament_commentary_v2.py |
| 10 | `__init__` | 2 | 5 | 10 | generate_round_report.py, generate_tournament_commentary_v2.py |
| 11 | `_now` | 2 | 2 | 4 | generate_round_report.py, generate_tournament_commentary_v2.py |
| 12 | `_prune` | 2 | 4 | 8 | generate_round_report.py, generate_tournament_commentary_v2.py |
| 13 | `used_last_min` | 2 | 4 | 8 | generate_round_report.py, generate_tournament_commentary_v2.py |
| 14 | `teg_sort_key` | 2 | 5 | 10 | player_history.py (same file!) |
| 15 | `read_file` | 2 | 5 | 10 | generate_commentary.py (same file!) |
| 16 | `get_api_key` (v2) | 2 | 9 | 18 | generate_round_report.py (same file!), generate_tournament_commentary_v2.py (same file!) |

**Total Exact Duplicate Impact**: 492 lines

---

## NEAR DUPLICATES (80-99% Similar)

| # | Function | Similarity | Lines | Impact | File 1 | File 2 |
|---|----------|------------|-------|--------|--------|--------|
| 1 | `get_previous_round_scores` | 96.6% | 36 | 72 | round_data_loader.py | unified_round_data_loader.py |
| 2 | `calculate_and_save_missing_winners` | 93.9% | 80 | 160 | history_data_processing.py:422 | history_data_processing.py:714 |
| 3 | `acquire` | 92.3% | 13 | 26 | generate_round_report.py | generate_tournament_commentary_v2.py |
| 4 | `format_course_info_section` | 91.1% | 46 | 92 | add_course_info_to_story_notes.py | generate_tournament_commentary_v2.py |
| 5 | `safe_create_message` | 91.1% | 83 | 166 | generate_round_report.py | generate_tournament_commentary_v2.py |
| 6 | `render_report` | 88.9% | 14 | 28 | latest_teg_context.py | teg_reports.py |
| 7 | `get_api_key` | 88.9% | 9 | 18 | generate_round_report.py | generate_tournament_commentary_v2.py |
| 8 | `display_completeness_status` | 85.7% | 16 | 32 | history_data_processing.py:404 | history_data_processing.py:694 |
| 9 | `check_winner_completeness` | 85.2% | 34 | 68 | history_data_processing.py:368 | history_data_processing.py:658 |
| 10 | `load_markdown` | 80.0% | 2 | 4 | teg_reports_17brief.py | teg_reports_17full.py |

**Total Near Duplicate Impact**: 666 lines (could be reduced to ~333 lines)

---

## SAME NAME, DIFFERENT IMPLEMENTATION

| Function Name | Occurrences | Similarity Range | Status | Recommendation |
|--------------|-------------|------------------|--------|----------------|
| `render_report` | 5 | 43.5% - 78.3% | Legitimate | Rename for clarity |
| `format_value` | 4 | 0% - 26.3% | Different purposes | Rename all |
| `get_api_key` | 4-5 | 33.3% - 88.9% | Should consolidate | Standardize |
| `load_markdown` | 3 | 0% - 80.0% | Similar purpose | Consolidate |
| `main` | 3 | 7.0% - 36.4% | Legitimate | OK (entry points) |
| `read_file` | 3 | 3.6% | Local overrides | Use utils version |
| `__init__` | 3 | 0% | Class constructors | Legitimate |
| `calculate_tournament_projections` | 2 | 54.5% | Evolving code | Use unified |
| `calculate_multi_score_running_sum` | 2 | 40.0% | Different contexts | Keep separate or parameterize |
| `clear_all_caches` | 2 | 50.0% | Simple vs complete | Use utils version |
| `format_vs_par_value` | 2 | 48.0% | Should consolidate | Move to utils |
| `generate_brief_summary` | 2 | 33.6% | Different contexts | Keep separate |
| `get_current_branch` | 2 | 0% | Simple vs complete | Use utils version |
| `get_incomplete_tegs` | 2 | 9.3% | Different purposes | Rename one |
| `summarize_multi_score_running_sum` | 2 | 47.1% | Different contexts | Keep or parameterize |
| `_add_series_markers` | 2 | 59.3% | Similar purpose | Consider consolidating |
| `altair_theme` | 2 | 65.2% | Chart theming | Move to styles/ |

---

## WITHIN-FILE DUPLICATES (Same file, same function name)

| File | Function | Occurrences | Lines | Line Numbers |
|------|----------|-------------|-------|--------------|
| `history_data_processing.py` | `extract_teg_num` | 2 | 8 | 349, 639 |
| `history_data_processing.py` | `check_winner_completeness` | 2 | 34 | 368, 658 |
| `history_data_processing.py` | `display_completeness_status` | 2 | 16-18 | 404, 694 |
| `history_data_processing.py` | `calculate_and_save_missing_winners` | 2 | 80 | 422, 714 |
| `generate_tournament_commentary_v2.py` | `get_api_key` | 2 | 9+3 | 443, 453 |
| `generate_tournament_commentary_v2.py` | `calc_wins_before` | 2 | 7 | 740, 2000 |
| `generate_round_report.py` | `get_api_key` | 2 | 9+3 | 225, 235 |
| `player_history.py` | `teg_sort_key` | 2 | 5 | 333, 379 |
| `generate_commentary.py` | `read_file` | 2 | 5 | 51, 109 |

**Total Within-File Impact**: ~370 lines (can be eliminated with simple deletions)

---

## CODE PATTERNS (Repeated across files)

| Pattern | Functions | Files | Example Files | Potential Abstraction |
|---------|-----------|-------|---------------|----------------------|
| `teg_filtering` | 130 | 31 | utils.py, scorecard_utils.py, etc. | `filter_by_teg(df, teg_num)` |
| `vs_par_formatting` | 51 | 18 | scorecard_utils.py, helpers/ | `format_vs_par(score, par)` |
| `player_filtering` | 45 | 18 | utils.py, various pages | `filter_by_player(df, player)` |
| `github_operations` | 44 | 9 | utils.py, commentary/ | Already in utils.py |
| `cache_clearing` | 15 | 5 | data_update, deletion, helpers/ | Use `utils.clear_all_caches()` |
| `chart_creation` | 6 | 3 | score_count, make_charts | Consider chart factory |

---

## FILE COMPLEXITY (Functions per file)

| Rank | File | Functions | Total Lines | Avg Size | Action |
|------|------|-----------|-------------|----------|--------|
| 1 | `utils.py` | 102 | 4,048 | 39.7 | **SPLIT INTO MODULES** |
| 2 | `generate_tournament_commentary_v2.py` | 52 | 2,142 | 41.2 | Extract shared logic |
| 3 | `streak_analysis_processing.py` | 29 | 1,100 | 37.9 | Consider splitting |
| 4 | `admin_volume_management.py` | 20 | 274 | 13.7 | OK |
| 5 | `generate_round_report.py` | 19 | 1,112 | 58.5 | Share code with v2 |
| 6 | `history_data_processing.py` | 19 | 759 | 39.9 | **Remove duplicates first** |

---

## REFACTORING PRIORITY MATRIX

| Priority | Category | Impact | Effort | ROI |
|----------|----------|--------|--------|-----|
| 1 | Within-file duplicates | 370 lines | 1 hour | **Very High** |
| 2 | `safe_int` consolidation | 24 lines | 30 min | High |
| 3 | Rate-limiting extraction | 100+ lines | 3 hours | High |
| 4 | Data loader consolidation | 150+ lines | 4 hours | Medium |
| 5 | Pattern abstraction | 500+ lines | 8 hours | Medium |
| 6 | utils.py decomposition | N/A | 20+ hours | Low (long-term) |

---

## FUNCTION CATEGORIES

### Utility Functions (should be in utils.py)
- `safe_int` (3 locations)
- `format_vs_par_value` (2 locations)
- `teg_sort_key` (2 locations in same file)
- `load_markdown` (3 locations)

### Rate-Limiting Functions (should be in helpers/api_rate_limiting.py)
- `__init__`, `_now`, `_prune`, `used_last_min`, `plan_wait`, `acquire`
- All duplicated between generate_round_report.py and generate_tournament_commentary_v2.py

### Data Loading Functions (consolidate to unified version)
- `calculate_hole_difficulty` (2 versions)
- `get_previous_round_scores` (2 versions)
- `calculate_tournament_projections` (2 versions)

### Commentary Functions (extract to helpers)
- `format_course_info_section` (2 versions)
- `safe_create_message` (2 versions)

### Display Functions (rename for clarity)
- `render_report` (5 different versions - rename all)
- `format_value` (4 different versions - rename all)

---

## IMPACT ANALYSIS

### Top 10 Duplicates by Impact Score

| Rank | Function | Impact | Type | Files |
|------|----------|--------|------|-------|
| 1 | `safe_create_message` | 166 | Near (91%) | 2 commentary files |
| 2 | `calculate_and_save_missing_winners` | 160 | Near (94%) | Same file! |
| 3 | `format_course_info_section` | 92 | Near (91%) | 2 commentary files |
| 4 | `get_previous_round_scores` | 72 | Near (97%) | 2 data loaders |
| 5 | `check_winner_completeness` | 68 | Near (85%) | Same file! |
| 6 | `calculate_hole_difficulty` | 64 | Exact | 2 data loaders |
| 7 | `plan_wait` | 38 | Exact | 2 commentary files |
| 8 | `display_completeness_status` | 32 | Near (86%) | Same file! |
| 9 | `render_report` | 28 | Near (89%) | 2 report files |
| 10 | `acquire` | 26 | Near (92%) | 2 commentary files |

**Top 10 Total Impact**: 746 lines (could be reduced to ~373 lines with consolidation)

---

## RECOMMENDED ACTIONS BY FILE

### `streamlit/helpers/history_data_processing.py`
**Priority**: CRITICAL
- [ ] Delete duplicate `extract_teg_num` at line 639
- [ ] Delete duplicate `check_winner_completeness` at line 658
- [ ] Delete duplicate `display_completeness_status` at line 694
- [ ] Delete duplicate `calculate_and_save_missing_winners` at line 714
- **Impact**: 180 lines eliminated

### `streamlit/commentary/generate_tournament_commentary_v2.py`
**Priority**: HIGH
- [ ] Delete duplicate `get_api_key` at line 453
- [ ] Delete duplicate `calc_wins_before` at line 2000
- [ ] Extract rate-limiting functions to shared module
- **Impact**: 16 lines + better organization

### `streamlit/commentary/generate_round_report.py`
**Priority**: HIGH
- [ ] Delete duplicate `get_api_key` at line 235
- [ ] Extract rate-limiting functions to shared module
- **Impact**: Better code sharing with v2

### `streamlit/utils.py`
**Priority**: MEDIUM (long-term)
- [ ] Add `safe_int` function
- [ ] Add consolidated `format_vs_par_value`
- [ ] Eventually split into focused modules
- **Impact**: Central location for utilities

### `streamlit/commentary/unified_round_data_loader.py`
**Priority**: MEDIUM
- [ ] Become the canonical data loader
- [ ] Deprecate `round_data_loader.py`
- **Impact**: Single source of truth

---

## SUCCESS METRICS

### Quantitative Goals
- [ ] Reduce duplicate code by 70% (from ~1,678 to ~480 lines)
- [ ] Eliminate all within-file duplicates (370 lines)
- [ ] Consolidate 10+ utility functions to central location
- [ ] Zero functions with same name (rename conflicts resolved)

### Qualitative Goals
- [ ] Clear naming conventions established
- [ ] No duplicate functions within single file
- [ ] Consistent import patterns
- [ ] Single source of truth for common operations

### Verification
- [ ] Run analysis script again after refactoring
- [ ] Compare before/after function counts
- [ ] Ensure all pages still load correctly
- [ ] No increase in page load times

---

**Analysis Date**: October 18, 2025
**Total Functions**: 530
**Total Files**: 68
**Duplicates Found**: 56 sets
**Estimated Savings**: 1,198 lines (71% reduction)
**Recommended Start**: Within-file duplicates (Week 1)
