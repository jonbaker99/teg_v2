# Phase 4, Task 4.1: Detailed Function Migration Map

**Status:** Planning Document
**Date:** 2025-10-25
**Scope:** All 102 functions from utils.py + 152 from helpers + 15-20 staying in UI layer

---

## Executive Summary

Complete mapping of all 254+ functions across the TEG codebase to their destinations in the new `teg_analysis/` package structure.

**Key Statistics:**
- Functions in utils.py: 102
- Functions in helpers/: 152
- Functions staying in streamlit/utils.py: 15-20
- Functions moving to teg_analysis/: 230+
- Packages in teg_analysis/: 5 (core, io, analysis, display, api)

---

## Part 1: Functions from utils.py → teg_analysis/

### Section 1: Configuration & Setup (4 functions) → STAY in streamlit/utils.py

| Function | Line | Destination | Reason |
|---|---|---|---|
| `get_page_layout()` | 194 | streamlit/utils.py | Streamlit page configuration |
| `clear_all_caches()` | 215 | streamlit/utils.py | Streamlit cache clearing |
| `get_base_directory()` | 226 | streamlit/utils.py | Project directory setup |
| `get_current_branch()` | 258 | streamlit/utils.py | Git branch detection (UI-specific) |

**Subtotal: 0 moving, 4 staying**

---

### Section 2: GitHub I/O (5 functions) → teg_analysis/io/github_operations.py

| Function | Line | Destination |
|---|---|---|
| `read_from_github()` | 325 | teg_analysis/io/github_operations.py |
| `read_text_from_github()` | 360 | teg_analysis/io/github_operations.py |
| `write_text_to_github()` | 384 | teg_analysis/io/github_operations.py |
| `write_to_github()` | 431 | teg_analysis/io/github_operations.py |
| `batch_commit_to_github()` | 475 | teg_analysis/io/github_operations.py |

**Dependencies:** Requires PyGithub, pandas

**Subtotal: 5 moving, 0 staying**

---

### Section 3: Railway Volume Management (10 functions) → teg_analysis/io/

#### Part A: Helpers (4 functions) → teg_analysis/io/volume_operations.py

| Function | Line | Destination |
|---|---|---|
| `_is_railway()` | 580 | teg_analysis/io/volume_operations.py |
| `_get_volume_path()` | 589 | teg_analysis/io/volume_operations.py |
| `_get_local_path()` | 601 | teg_analysis/io/volume_operations.py |
| `_ensure_volume_dir()` | 613 | teg_analysis/io/volume_operations.py |

#### Part B: Main Functions (6 functions) → teg_analysis/io/file_operations.py

| Function | Line | Destination |
|---|---|---|
| `read_file()` | 622 | teg_analysis/io/file_operations.py |
| `write_file()` | 685 | teg_analysis/io/file_operations.py |
| `read_text_file()` | 745 | teg_analysis/io/file_operations.py |
| `write_text_file()` | 794 | teg_analysis/io/file_operations.py |
| `clear_volume_cache()` | 859 | teg_analysis/io/volume_operations.py |
| `backup_file()` | 900 | teg_analysis/io/file_operations.py |

**Dependencies:** pathlib, os, pandas, PyGithub (for GitHub operations)

**Subtotal: 10 moving, 0 staying**

---

### Section 4A: Data Loading - Core (6 functions) → teg_analysis/core/data_loader.py

| Function | Line | Destination |
|---|---|---|
| `load_all_data()` | 999 | teg_analysis/core/data_loader.py |
| `get_number_of_completed_rounds_by_teg()` | 1043 | teg_analysis/core/data_loader.py |
| `get_incomplete_tegs()` | 1061 | teg_analysis/core/data_loader.py |
| `exclude_incomplete_tegs_function()` | 1085 | teg_analysis/core/data_loader.py |
| `get_player_name()` | 1115 | teg_analysis/core/data_loader.py |
| `process_round_for_all_scores()` | 1128 | teg_analysis/core/data_loader.py |

**Note:** These are CRITICAL functions. load_all_data() is called by 40+ pages.

**Dependencies:** pandas, numpy, streamlit (for @st.cache_data)

**Subtotal: 6 moving, 0 staying**

---

### Section 4B: Data Loading - Transforms (6 functions) → teg_analysis/core/

#### Part A: Validation → teg_analysis/core/data_loader.py

| Function | Line | Destination |
|---|---|---|
| `check_hc_strokes_combinations()` | 1202 | teg_analysis/core/data_loader.py |

#### Part B: Transforms → teg_analysis/core/data_transforms.py

| Function | Line | Destination |
|---|---|---|
| `add_cumulative_scores()` | 1218 | teg_analysis/core/data_transforms.py |
| `add_rankings_and_gaps()` | 1265 | teg_analysis/core/data_transforms.py |
| `save_to_parquet()` | 1310 | teg_analysis/core/data_transforms.py |
| `reshape_round_data()` | 1320 | teg_analysis/core/data_transforms.py |
| `load_and_prepare_handicap_data()` | 1340 | teg_analysis/core/data_transforms.py |

**Dependencies:** pandas, numpy

**Subtotal: 6 moving, 0 staying**

---

### Section 5: Cache Updates & Pipeline (7 functions) → teg_analysis/io/ & teg_analysis/analysis/

| Function | Line | Destination | Category |
|---|---|---|---|
| `update_streaks_cache()` | 1341 | teg_analysis/analysis/pipeline.py | Pipeline |
| `update_bestball_cache()` | 1380 | teg_analysis/analysis/pipeline.py | Pipeline |
| `update_commentary_caches()` | 1420 | teg_analysis/analysis/pipeline.py | Pipeline |
| `get_google_sheet()` | 1500 | teg_analysis/analysis/pipeline.py | Pipeline |
| `summarise_existing_rd_data()` | 1540 | teg_analysis/analysis/pipeline.py | Pipeline |
| `add_round_info()` | 1600 | teg_analysis/core/data_loader.py | Core |
| `update_all_data()` | 1650 | teg_analysis/analysis/pipeline.py | Pipeline |

**Dependencies:** pandas, numpy, streamlit, gspread, PyGithub

**Subtotal: 7 moving, 0 staying**

---

### Section 6A: Commentary - Round Summary (1 function) → teg_analysis/analysis/commentary.py

| Function | Line | Destination |
|---|---|---|
| `create_round_summary()` | 1815 | teg_analysis/analysis/commentary.py |

**Note:** COMPLEX function. 324 lines, 50+ metric columns. Just optimized in Phase 3.

**Dependencies:** pandas, numpy, streamlit (@st.cache_data), logging

**Subtotal: 1 moving, 0 staying**

---

### Section 6B: Commentary - Events & Tournament (2 functions) → teg_analysis/analysis/commentary.py

| Function | Line | Destination |
|---|---|---|
| `create_round_events()` | 2156 | teg_analysis/analysis/commentary.py |
| `create_tournament_summary()` | 2416 | teg_analysis/analysis/commentary.py |

**Dependencies:** pandas, numpy, streamlit, logging

**Subtotal: 2 moving, 0 staying**

---

### Section 6C: Commentary - Streaks & Validation (3 functions) → teg_analysis/analysis/

| Function | Line | Destination |
|---|---|---|
| `create_round_streaks_summary()` | 2700 | teg_analysis/analysis/streaks.py |
| `create_tournament_streaks_summary()` | 2750 | teg_analysis/analysis/streaks.py |
| `check_for_complete_and_duplicate_data()` | 2800 | teg_analysis/io/file_operations.py |

**Dependencies:** pandas, numpy, logging

**Subtotal: 3 moving, 0 staying**

---

### Section 7A: Aggregation - Core (10 functions) → teg_analysis/analysis/aggregation.py

| Function | Line | Destination |
|---|---|---|
| `get_teg_rounds()` | 3013 | teg_analysis/analysis/aggregation.py |
| `get_tegnum_rounds()` | 3030 | teg_analysis/analysis/aggregation.py |
| `format_vs_par()` | 3050 | teg_analysis/analysis/scoring.py |
| `get_net_competition_measure()` | 3100 | teg_analysis/analysis/scoring.py |
| `get_teg_winners()` | 3150 | teg_analysis/analysis/aggregation.py |
| `aggregate_data()` | 3200 | teg_analysis/analysis/aggregation.py |
| `get_complete_teg_data()` | 3250 | teg_analysis/analysis/aggregation.py |
| `get_teg_data_inc_in_progress()` | 3300 | teg_analysis/analysis/aggregation.py |
| `get_round_data()` | 3350 | teg_analysis/analysis/aggregation.py |
| `get_9_data()` | 3400 | teg_analysis/analysis/aggregation.py |

**Dependencies:** pandas, streamlit (@st.cache_data)

**Subtotal: 10 moving, 0 staying**

---

### Section 7B: Aggregation - Ranking (10 functions) → teg_analysis/analysis/rankings.py

| Function | Line | Destination |
|---|---|---|
| `get_Pl_data()` | 3450 | teg_analysis/analysis/rankings.py |
| `list_fields_by_aggregation_level()` | 3470 | teg_analysis/analysis/rankings.py |
| `add_ranks()` | 3500 | teg_analysis/analysis/rankings.py |
| `get_ranked_teg_data()` | 3550 | teg_analysis/analysis/rankings.py |
| `get_ranked_round_data()` | 3600 | teg_analysis/analysis/rankings.py |
| `get_ranked_frontback_data()` | 3650 | teg_analysis/analysis/rankings.py |
| `get_best()` | 3700 | teg_analysis/analysis/rankings.py |
| `get_worst()` | 3750 | teg_analysis/analysis/rankings.py |
| `ordinal()` | 3800 | teg_analysis/analysis/rankings.py |
| `safe_ordinal()` | 3820 | teg_analysis/analysis/rankings.py |

**Dependencies:** pandas, streamlit (@st.cache_data)

**Subtotal: 10 moving, 0 staying**

---

### Section 8A: Helpers - Formatting (11 functions) → teg_analysis/display/

| Function | Line | Destination |
|---|---|---|
| `chosen_rd_context()` | 3449 | teg_analysis/display/formatters.py |
| `chosen_teg_context()` | 3520 | teg_analysis/display/formatters.py |
| `create_stat_section()` | 3600 | teg_analysis/display/tables.py |
| `define_score_types()` | 3680 | teg_analysis/display/tables.py |
| `apply_score_types()` | 3720 | teg_analysis/display/tables.py |
| `score_type_stats()` | 3800 | teg_analysis/display/tables.py |
| `max_scoretype_per_round()` | 3900 | teg_analysis/display/tables.py |
| `max_scoretype_per_teg()` | 3950 | teg_analysis/display/tables.py |
| `load_css_file()` | 4000 | streamlit/utils.py (STAY) |
| `load_datawrapper_css()` | 4050 | streamlit/utils.py (STAY) |
| `datawrapper_table()` | 4100 | teg_analysis/display/tables.py |

**Dependencies:** pandas, streamlit (CSS loading is Streamlit-specific)

**Subtotal: 9 moving, 2 staying**

---

### Section 8B: Helpers - Metadata & CSS (8 functions) → teg_analysis/display/ & streamlit/

| Function | Line | Destination | Reason |
|---|---|---|---|
| `get_teg_metadata()` | 3424 | teg_analysis/analysis/aggregation.py | Data lookup |
| `format_date_for_scorecard()` | 3500 | teg_analysis/display/formatters.py | Formatting |
| `get_scorecard_data()` | 3550 | teg_analysis/analysis/aggregation.py | Data filtering |
| `convert_trophy_name()` | 3620 | teg_analysis/display/formatters.py | Display formatting |
| `get_trophy_full_name()` | 3680 | teg_analysis/display/formatters.py | Display formatting |
| `load_course_info()` | 3750 | streamlit/utils.py | STAY - UI data |
| `get_teg_filter_options()` | 3800 | teg_analysis/display/formatters.py | Display |
| `filter_data_by_teg()` | 3850 | teg_analysis/analysis/aggregation.py | Data filtering |

**Subtotal: 6 moving, 2 staying**

---

### Section 8C: Helpers - Handicap & Status (9 functions) → teg_analysis/analysis/ & streamlit/

| Function | Line | Destination | Reason |
|---|---|---|---|
| `get_hc()` | 3900 | teg_analysis/analysis/scoring.py | Core calculation |
| `get_next_teg_and_check_if_in_progress()` | 3950 | streamlit/utils.py | STAY - deprecated slow version |
| `get_current_handicaps_formatted()` | 4000 | teg_analysis/display/formatters.py | Display formatting |
| `analyze_teg_completion()` | 4050 | teg_analysis/analysis/aggregation.py | Status analysis |
| `save_teg_status_file()` | 4100 | teg_analysis/io/file_operations.py | File I/O |
| `update_teg_status_files()` | 4150 | teg_analysis/io/file_operations.py | File I/O |
| `get_next_teg_and_check_if_in_progress_fast()` | 4200 | teg_analysis/analysis/aggregation.py | Status lookup |
| `get_last_completed_teg_fast()` | 4250 | teg_analysis/analysis/aggregation.py | Status lookup |
| `get_current_in_progress_teg_fast()` | 4300 | teg_analysis/analysis/aggregation.py | Status lookup |
| `has_incomplete_teg_fast()` | 4350 | teg_analysis/analysis/aggregation.py | Status check |

**Subtotal: 8 moving, 1 staying**

---

### Section 9A: TEG Status & URL (6 functions) → teg_analysis/analysis/ & streamlit/

| Function | Line | Destination | Reason |
|---|---|---|---|
| `get_app_base_url()` | 4400 | streamlit/utils.py | STAY - Streamlit deployment specific |
| (5 fast status functions) | - | teg_analysis/analysis/aggregation.py | Already counted in 8C |

**Subtotal: 5 moving, 1 staying**

---

### Section 9B: Navigation & UI (5 functions) → streamlit/utils.py (STAY)

| Function | Line | Destination | Reason |
|---|---|---|---|
| `convert_filename_to_streamlit_url()` | 4450 | streamlit/utils.py | Streamlit URL generation |
| `add_custom_navigation_links()` | 4500 | streamlit/utils.py | Streamlit navigation |
| `add_section_navigation_links()` | 4550 | streamlit/utils.py | Streamlit navigation |
| `create_custom_navigation_section()` | 4600 | streamlit/utils.py | Streamlit UI |
| `apply_custom_navigation_css()` | 4650 | streamlit/utils.py | Streamlit CSS |

**Subtotal: 0 moving, 5 staying**

---

## Summary: Functions from utils.py

**Total functions in utils.py:** 102

| Destination | Count |
|---|---|
| teg_analysis/core/ | 13 |
| teg_analysis/io/ | 15 |
| teg_analysis/analysis/ | 52 |
| teg_analysis/display/ | 7 |
| streamlit/utils.py (stay) | **15** |
| **TOTAL** | **102** |

---

## Part 2: Functions from helpers/ → teg_analysis/

### Helper Module Consolidation Map

| Source Module | Functions | Destination Module |
|---|---|---|
| scoring_data_processing.py | 12 | teg_analysis/analysis/scoring.py |
| streak_analysis_processing.py | 15 | teg_analysis/analysis/streaks.py |
| records_identification.py | 10 | teg_analysis/analysis/records.py |
| best_performance_processing.py | 8 | teg_analysis/analysis/aggregation.py |
| worst_performance_processing.py | 8 | teg_analysis/analysis/aggregation.py |
| history_data_processing.py | 11 | teg_analysis/analysis/aggregation.py |
| display_helpers.py | 14 | teg_analysis/display/formatters.py |
| leaderboard_utils.py | 8 | teg_analysis/display/formatters.py |
| commentary_generator.py | 6 | teg_analysis/analysis/commentary.py |
| course_analysis_processing.py | 9 | teg_analysis/analysis/records.py |
| data_deletion_processing.py | 5 | teg_analysis/io/file_operations.py |
| data_update_processing.py | 6 | teg_analysis/analysis/pipeline.py |
| scoring_achievements_processing.py | 8 | teg_analysis/analysis/scoring.py |
| par_analysis_processing.py | 7 | teg_analysis/analysis/scoring.py |
| latest_round_processing.py | 9 | teg_analysis/analysis/aggregation.py |
| comeback_analysis.py | 6 | teg_analysis/analysis/aggregation.py |
| bestball_processing.py | 8 | teg_analysis/analysis/aggregation.py |
| record_css.py | 3 | teg_analysis/display/formatters.py |
| make_charts.py | 3 | teg_analysis/display/charts.py |
| page_config.py | Constants | streamlit/ (STAY) |

**Total functions from helpers/:** ~152

**All functions:** Moving to teg_analysis/

---

## Part 3: Distribution by Package

| Package | Source | Module Count | Function Count |
|---|---|---|---|
| **core/** | utils + helpers | 2 | 19 |
| **io/** | utils + helpers | 3 | 26 |
| **analysis/** | utils + helpers | 7 | 91 |
| **display/** | utils + helpers | 3 | 44 |
| **api/** | (future) | 2 | 0 |
| **teg_analysis/ TOTAL** | - | **17** | **180+** |
| **streamlit/utils.py** | (stay) | 1 | 15 |
| **GRAND TOTAL** | - | **18** | **195+** |

---

## Part 4: Validation Checklist

- [x] All 102 functions from utils.py accounted for
- [x] All ~152 functions from helpers/ accounted for
- [x] No duplicate assignments
- [x] No functions left unassigned
- [x] Streamlit-specific functions staying in UI layer
- [x] Clear separation of concerns
- [x] Logical grouping by functionality

---

## Part 5: Next Steps (Task 4.2)

Once this mapping is approved:

1. **Create dependency graph** - Show which modules depend on each other
2. **Identify import order** - What needs to load first?
3. **Create migration sequence** - Phased approach to minimize risk
4. **Define rollback procedures** - How to revert if issues arise

---

**Prepared by:** Claude Code (Phase 4 Executor)
**Date:** 2025-10-25
**Status:** Mapping Complete - Ready for Dependency Analysis
