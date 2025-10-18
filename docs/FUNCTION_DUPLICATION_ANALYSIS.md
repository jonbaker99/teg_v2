================================================================================
TEG CODEBASE - FUNCTION DUPLICATION & SIMILARITY ANALYSIS
================================================================================

SUMMARY STATISTICS
--------------------------------------------------------------------------------
Total functions analyzed: 530
Files analyzed: 68
Functions in utils.py: 122
Functions in helpers/: 173
Functions in page files: 235

1. EXACT DUPLICATES (100% identical code, different locations)
--------------------------------------------------------------------------------

Duplicate Set #1: __init__
  Occurrences: 2 times in 2 files
  Line count: 5 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:80
    - streamlit\commentary\generate_tournament_commentary_v2.py:297
  Decorators: None

Duplicate Set #2: _now
  Occurrences: 2 times in 2 files
  Line count: 2 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:86
    - streamlit\commentary\generate_tournament_commentary_v2.py:303
  Decorators: None

Duplicate Set #3: _prune
  Occurrences: 2 times in 2 files
  Line count: 4 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:89
    - streamlit\commentary\generate_tournament_commentary_v2.py:306
  Decorators: None

Duplicate Set #4: used_last_min
  Occurrences: 2 times in 2 files
  Line count: 4 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:94
    - streamlit\commentary\generate_tournament_commentary_v2.py:311
  Decorators: None

Duplicate Set #5: plan_wait
  Occurrences: 2 times in 2 files
  Line count: 19 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:99
    - streamlit\commentary\generate_tournament_commentary_v2.py:316
  Decorators: None

Duplicate Set #6: get_api_key
  Occurrences: 2 times in 2 files
  Line count: 3 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:235
    - streamlit\commentary\generate_tournament_commentary_v2.py:453
  Decorators: None

Duplicate Set #7: safe_int
  Occurrences: 3 times in 3 files
  Line count: 8 lines
  Locations:
    - streamlit\commentary\round_data_loader.py:24
    - streamlit\commentary\round_pattern_analysis.py:15
    - streamlit\commentary\unified_round_data_loader.py:31
  Decorators: None

Duplicate Set #8: calculate_hole_difficulty
  Occurrences: 2 times in 2 files
  Line count: 32 lines
  Locations:
    - streamlit\commentary\round_data_loader.py:63
    - streamlit\commentary\unified_round_data_loader.py:479
  Decorators: None

2. NEAR DUPLICATES (80-99% similar)
--------------------------------------------------------------------------------

Near Duplicate #1: get_previous_round_scores
  Similarity: 96.6%
  Location 1: streamlit\commentary\round_data_loader.py:97
  Location 2: streamlit\commentary\unified_round_data_loader.py:513
  Lines: 36 vs 36

Near Duplicate #2: calculate_and_save_missing_winners
  Similarity: 93.9%
  Location 1: streamlit\helpers\history_data_processing.py:422
  Location 2: streamlit\helpers\history_data_processing.py:714
  Lines: 80 vs 80

Near Duplicate #3: acquire
  Similarity: 92.3%
  Location 1: streamlit\commentary\generate_round_report.py:119
  Location 2: streamlit\commentary\generate_tournament_commentary_v2.py:336
  Lines: 13 vs 13

Near Duplicate #4: format_course_info_section
  Similarity: 91.1%
  Location 1: streamlit\commentary\add_course_info_to_story_notes.py:16
  Location 2: streamlit\commentary\generate_tournament_commentary_v2.py:1680
  Lines: 46 vs 44

Near Duplicate #5: safe_create_message
  Similarity: 91.1%
  Location 1: streamlit\commentary\generate_round_report.py:138
  Location 2: streamlit\commentary\generate_tournament_commentary_v2.py:353
  Lines: 83 vs 83

Near Duplicate #6: render_report
  Similarity: 88.9%
  Location 1: streamlit\latest_teg_context.py:47
  Location 2: streamlit\teg_reports.py:35
  Lines: 14 vs 15

Near Duplicate #7: get_api_key
  Similarity: 88.9%
  Location 1: streamlit\commentary\generate_round_report.py:225
  Location 2: streamlit\commentary\generate_tournament_commentary_v2.py:443
  Lines: 9 vs 9

Near Duplicate #8: display_completeness_status
  Similarity: 85.7%
  Location 1: streamlit\helpers\history_data_processing.py:404
  Location 2: streamlit\helpers\history_data_processing.py:694
  Lines: 16 vs 18

Near Duplicate #9: check_winner_completeness
  Similarity: 85.2%
  Location 1: streamlit\helpers\history_data_processing.py:368
  Location 2: streamlit\helpers\history_data_processing.py:658
  Lines: 34 vs 34

Near Duplicate #10: load_markdown
  Similarity: 80.0%
  Location 1: streamlit\teg_reports_17brief.py:34
  Location 2: streamlit\teg_reports_17full.py:36
  Lines: 2 vs 3

3. SAME NAME, DIFFERENT IMPLEMENTATION
--------------------------------------------------------------------------------

Function: __init__
  Implementations: 3
  Locations:
    - streamlit\commentary\generate_round_report.py:80 (5 lines)
    - streamlit\helpers\commentary_generator.py:37 (12 lines)
    - streamlit\commentary\generate_tournament_commentary_v2.py:297 (5 lines)
  Similarity range: 0.0% - 0.0%

Function: _add_series_markers
  Implementations: 2
  Locations:
    - streamlit\102TEG Results.py:81 (14 lines)
    - streamlit\leaderboard.py:36 (13 lines)
  Similarity range: 59.3% - 59.3%

Function: altair_theme
  Implementations: 2
  Locations:
    - streamlit\ave_by_teg.py:36 (26 lines)
    - streamlit\graph_test_line.py:37 (20 lines)
  Similarity range: 65.2% - 65.2%

Function: calculate_multi_score_running_sum
  Implementations: 2
  Locations:
    - streamlit\helpers\scoring_data_processing.py:99 (48 lines)
    - streamlit\helpers\streak_analysis_processing.py:54 (45 lines)
  Similarity range: 40.0% - 40.0%

Function: calculate_tournament_projections
  Implementations: 2
  Locations:
    - streamlit\commentary\round_data_loader.py:215 (85 lines)
    - streamlit\commentary\unified_round_data_loader.py:551 (112 lines)
  Similarity range: 54.5% - 54.5%

Function: clear_all_caches
  Implementations: 2
  Locations:
    - streamlit\admin_volume_management.py:34 (2 lines)
    - streamlit\utils.py:45 (7 lines)
  Similarity range: 50.0% - 50.0%

Function: format_value
  Implementations: 7
  Locations:
    - streamlit\500Handicaps.py:46 (12 lines)
    - streamlit\leaderboard_utils.py:72 (27 lines)
    - streamlit\make_charts.py:13 (23 lines)
    - streamlit\helpers\records_identification.py:31 (16 lines)
  Similarity range: 0.0% - 26.3%

Function: format_vs_par_value
  Implementations: 2
  Locations:
    - streamlit\helpers\par_analysis_processing.py:52 (10 lines)
    - streamlit\helpers\scoring_data_processing.py:13 (18 lines)
  Similarity range: 48.0% - 48.0%

Function: generate_brief_summary
  Implementations: 2
  Locations:
    - streamlit\commentary\generate_commentary.py:375 (36 lines)
    - streamlit\commentary\generate_tournament_commentary_v2.py:947 (90 lines)
  Similarity range: 33.6% - 33.6%

Function: get_api_key
  Implementations: 5
  Locations:
    - streamlit\commentary\generate_round_report.py:225 (9 lines)
    - streamlit\commentary\generate_round_report.py:235 (3 lines)
    - streamlit\commentary\generate_tournament_commentary_v2.py:453 (3 lines)
    - streamlit\commentary\generate_tournament_commentary_v2.py:443 (9 lines)
  Similarity range: 33.3% - 33.3%

Function: get_current_branch
  Implementations: 2
  Locations:
    - streamlit\admin_volume_management.py:31 (2 lines)
    - streamlit\utils.py:108 (26 lines)
  Similarity range: 0.0% - 0.0%

Function: get_incomplete_tegs
  Implementations: 2
  Locations:
    - streamlit\utils.py:831 (22 lines)
    - streamlit\helpers\history_data_processing.py:224 (37 lines)
  Similarity range: 9.3% - 9.3%

Function: load_markdown
  Implementations: 3
  Locations:
    - streamlit\102TEG Results.py:57 (10 lines)
    - streamlit\teg_reports_17brief.py:34 (2 lines)
    - streamlit\teg_reports_17full.py:36 (3 lines)
  Similarity range: 0.0% - 0.0%

Function: main
  Implementations: 4
  Locations:
    - streamlit\commentary\add_course_info_to_story_notes.py:95 (43 lines)
    - streamlit\commentary\create_alt_profiles.py:100 (29 lines)
    - streamlit\commentary\generate_alt_player_profiles.py:61 (32 lines)
  Similarity range: 7.0% - 36.4%

Function: read_file
  Implementations: 3
  Locations:
    - streamlit\utils.py:411 (61 lines)
    - streamlit\commentary\generate_commentary.py:51 (5 lines)
    - streamlit\commentary\generate_commentary.py:109 (5 lines)
  Similarity range: 3.6% - 3.6%

Function: render_report
  Implementations: 10
  Locations:
    - streamlit\102TEG Results.py:69 (10 lines)
    - streamlit\latest_teg_context.py:47 (14 lines)
    - streamlit\teg_reports.py:35 (15 lines)
    - streamlit\teg_reports_17brief.py:38 (9 lines)
    - streamlit\teg_reports_17full.py:41 (12 lines)
  Similarity range: 43.5% - 78.3%

Function: summarize_multi_score_running_sum
  Implementations: 2
  Locations:
    - streamlit\helpers\scoring_data_processing.py:149 (33 lines)
    - streamlit\helpers\streak_analysis_processing.py:148 (34 lines)
  Similarity range: 47.1% - 47.1%

4. SIMILAR FUNCTION NAMES (Potential naming inconsistencies)
--------------------------------------------------------------------------------
  No similar names found.

5. MOST COMMON FUNCTION NAMES (Potential for consolidation)
--------------------------------------------------------------------------------
  render_report: 5 occurrences
  format_value: 4 occurrences
  get_api_key: 4 occurrences
  load_markdown: 3 occurrences
  read_file: 3 occurrences
  main: 3 occurrences
  __init__: 3 occurrences
  safe_int: 3 occurrences
  _add_series_markers: 2 occurrences
  get_current_branch: 2 occurrences
  clear_all_caches: 2 occurrences
  altair_theme: 2 occurrences
  teg_sort_key: 2 occurrences
  get_incomplete_tegs: 2 occurrences
  format_course_info_section: 2 occurrences
  generate_brief_summary: 2 occurrences
  _now: 2 occurrences
  _prune: 2 occurrences
  used_last_min: 2 occurrences
  plan_wait: 2 occurrences
