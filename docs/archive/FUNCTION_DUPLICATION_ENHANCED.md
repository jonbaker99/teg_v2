================================================================================
ENHANCED DUPLICATION ANALYSIS - ADDITIONAL INSIGHTS
================================================================================

1. WITHIN-FILE DUPLICATES (Same function name, same file)
--------------------------------------------------------------------------------

  File: streamlit\player_history.py
  Function: teg_sort_key
  Occurrences: 2 times in the same file
  Line numbers:
    - Line 333 (5 lines)
    - Line 379 (5 lines)

  File: streamlit\commentary\generate_commentary.py
  Function: read_file
  Occurrences: 2 times in the same file
  Line numbers:
    - Line 51 (5 lines)
    - Line 109 (5 lines)

  File: streamlit\commentary\generate_round_report.py
  Function: get_api_key
  Occurrences: 2 times in the same file
  Line numbers:
    - Line 225 (9 lines)
    - Line 235 (3 lines)

  File: streamlit\commentary\generate_tournament_commentary_v2.py
  Function: get_api_key
  Occurrences: 2 times in the same file
  Line numbers:
    - Line 443 (9 lines)
    - Line 453 (3 lines)

  File: streamlit\commentary\generate_tournament_commentary_v2.py
  Function: calc_wins_before
  Occurrences: 2 times in the same file
  Line numbers:
    - Line 740 (7 lines)
    - Line 2000 (7 lines)

  File: streamlit\helpers\history_data_processing.py
  Function: extract_teg_num
  Occurrences: 2 times in the same file
  Line numbers:
    - Line 349 (8 lines)
    - Line 639 (8 lines)

  File: streamlit\helpers\history_data_processing.py
  Function: check_winner_completeness
  Occurrences: 2 times in the same file
  Line numbers:
    - Line 368 (34 lines)
    - Line 658 (34 lines)

  File: streamlit\helpers\history_data_processing.py
  Function: display_completeness_status
  Occurrences: 2 times in the same file
  Line numbers:
    - Line 404 (16 lines)
    - Line 694 (18 lines)

  File: streamlit\helpers\history_data_processing.py
  Function: calculate_and_save_missing_winners
  Occurrences: 2 times in the same file
  Line numbers:
    - Line 422 (80 lines)
    - Line 714 (80 lines)

2. DECORATOR USAGE ANALYSIS
--------------------------------------------------------------------------------

  Total unique decorators: 6

  Most common decorators:
    st.cache_data: 15 functions
    st.cache_data(show_spinner=False): 5 functions
    st.cache_data(ttl=60): 2 functions
    st.cache_data(ttl=300): 1 functions
    st.cache_data(ttl=30): 1 functions
    st.cache_data(ttl=20): 1 functions

  Functions with @st.cache_data: 15

3. UTILITY FUNCTION CONSOLIDATION CANDIDATES
--------------------------------------------------------------------------------
Functions that appear multiple times and could be centralized in utils.py


  Function: __init__
  Occurrences: 2
  Average size: 5.0 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:80
    - streamlit\commentary\generate_tournament_commentary_v2.py:297

  Function: _add_series_markers
  Occurrences: 2
  Average size: 13.5 lines
  Locations:
    - streamlit\102TEG Results.py:81
    - streamlit\leaderboard.py:36

  Function: _now
  Occurrences: 2
  Average size: 2.0 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:86
    - streamlit\commentary\generate_tournament_commentary_v2.py:303

  Function: _prune
  Occurrences: 2
  Average size: 4.0 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:89
    - streamlit\commentary\generate_tournament_commentary_v2.py:306

  Function: acquire
  Occurrences: 2
  Average size: 13.0 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:119
    - streamlit\commentary\generate_tournament_commentary_v2.py:336

  Function: altair_theme
  Occurrences: 2
  Average size: 23.0 lines
  Locations:
    - streamlit\ave_by_teg.py:36
    - streamlit\graph_test_line.py:37

  Function: calc_wins_before
  Occurrences: 2
  Average size: 7.0 lines
  Locations:
    - streamlit\commentary\generate_tournament_commentary_v2.py:740
    - streamlit\commentary\generate_tournament_commentary_v2.py:2000

  Function: extract_teg_num
  Occurrences: 2
  Average size: 8.0 lines
  Locations:
    - streamlit\helpers\history_data_processing.py:349
    - streamlit\helpers\history_data_processing.py:639

  Function: format_vs_par_value
  Occurrences: 2
  Average size: 14.0 lines
  Locations:
    - streamlit\helpers\par_analysis_processing.py:52
    - streamlit\helpers\scoring_data_processing.py:13

  Function: get_api_key
  Occurrences: 2
  Average size: 3.0 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:235
    - streamlit\commentary\generate_tournament_commentary_v2.py:453

  Function: load_markdown
  Occurrences: 3
  Average size: 5.0 lines
  Locations:
    - streamlit\102TEG Results.py:57
    - streamlit\teg_reports_17brief.py:34
    - streamlit\teg_reports_17full.py:36

  Function: main
  Occurrences: 1
  Average size: 29.0 lines
  Locations:
    - streamlit\commentary\create_alt_profiles.py:100

  Function: plan_wait
  Occurrences: 2
  Average size: 19.0 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:99
    - streamlit\commentary\generate_tournament_commentary_v2.py:316

  Function: read_file
  Occurrences: 2
  Average size: 5.0 lines
  Locations:
    - streamlit\commentary\generate_commentary.py:51
    - streamlit\commentary\generate_commentary.py:109

  Function: safe_int
  Occurrences: 3
  Average size: 8.0 lines
  Locations:
    - streamlit\commentary\round_data_loader.py:24
    - streamlit\commentary\round_pattern_analysis.py:15
    - streamlit\commentary\unified_round_data_loader.py:31

  Function: teg_sort_key
  Occurrences: 2
  Average size: 5.0 lines
  Locations:
    - streamlit\player_history.py:333
    - streamlit\player_history.py:379

  Function: used_last_min
  Occurrences: 2
  Average size: 4.0 lines
  Locations:
    - streamlit\commentary\generate_round_report.py:94
    - streamlit\commentary\generate_tournament_commentary_v2.py:311

4. COMMON CODE PATTERNS
--------------------------------------------------------------------------------

  Pattern: vs_par_formatting
  Occurrences: 51 functions
  Files affected: 18
  Example functions:
    - generate_round_comparison_html_mobile (streamlit\scorecard_utils.py, 256 lines)
    - generate_tournament_html_mobile (streamlit\scorecard_utils.py, 246 lines)
    - generate_round_comparison_html (streamlit\scorecard_utils.py, 199 lines)

  Pattern: player_filtering
  Occurrences: 45 functions
  Files affected: 18
  Example functions:
    - create_round_summary (streamlit\utils.py, 324 lines)
    - generate_round_comparison_html_mobile (streamlit\scorecard_utils.py, 256 lines)
    - generate_tournament_html_mobile (streamlit\scorecard_utils.py, 246 lines)

  Pattern: teg_filtering
  Occurrences: 130 functions
  Files affected: 31
  Example functions:
    - create_round_summary (streamlit\utils.py, 324 lines)
    - create_tournament_summary (streamlit\utils.py, 284 lines)
    - generate_batch_reports_via_api (streamlit\commentary\generate_round_report.py, 277 lines)

  Pattern: dataframe_styling
  Occurrences: 1 functions
  Files affected: 1
  Example functions:
    - create_course_performance_table (streamlit\helpers\course_analysis_processing.py, 51 lines)

  Pattern: cache_clearing
  Occurrences: 15 functions
  Files affected: 5
  Example functions:
    - execute_data_update (streamlit\helpers\data_update_processing.py, 175 lines)
    - execute_data_deletion (streamlit\helpers\data_deletion_processing.py, 88 lines)
    - calculate_and_save_missing_winners (streamlit\helpers\history_data_processing.py, 80 lines)

  Pattern: github_operations
  Occurrences: 44 functions
  Files affected: 9
  Example functions:
    - generate_batch_reports_via_api (streamlit\commentary\generate_round_report.py, 277 lines)
    - generate_story_notes_via_batch_api (streamlit\commentary\generate_tournament_commentary_v2.py, 259 lines)
    - generate_reports_via_batch_api (streamlit\commentary\generate_tournament_commentary_v2.py, 246 lines)

  Pattern: chart_creation
  Occurrences: 6 functions
  Files affected: 3
  Example functions:
    - create_ridgeline_distribution_chart (streamlit\helpers\score_count_processing.py, 183 lines)
    - create_cumulative_graph (streamlit\make_charts.py, 80 lines)
    - create_round_graph (streamlit\make_charts.py, 76 lines)

5. HIGH-IMPACT DUPLICATES (Prioritize for refactoring)
--------------------------------------------------------------------------------
Duplicates sorted by potential impact (number of occurrences × line count)


  #1: safe_create_message
  Type: NEAR duplicate
  Occurrences: 2
  Line count: 83
  Similarity: 91.1%
  Impact score: 166 (count × lines)
  Affected files:
    - streamlit\commentary\generate_round_report.py
    - streamlit\commentary\generate_tournament_commentary_v2.py

  #2: calculate_and_save_missing_winners
  Type: NEAR duplicate
  Occurrences: 2
  Line count: 80
  Similarity: 93.9%
  Impact score: 160 (count × lines)
  Affected files:
    - streamlit\helpers\history_data_processing.py
    - streamlit\helpers\history_data_processing.py

  #3: format_course_info_section
  Type: NEAR duplicate
  Occurrences: 2
  Line count: 46
  Similarity: 91.1%
  Impact score: 92 (count × lines)
  Affected files:
    - streamlit\commentary\add_course_info_to_story_notes.py
    - streamlit\commentary\generate_tournament_commentary_v2.py

  #4: get_previous_round_scores
  Type: NEAR duplicate
  Occurrences: 2
  Line count: 36
  Similarity: 96.6%
  Impact score: 72 (count × lines)
  Affected files:
    - streamlit\commentary\round_data_loader.py
    - streamlit\commentary\unified_round_data_loader.py

  #5: check_winner_completeness
  Type: NEAR duplicate
  Occurrences: 2
  Line count: 34
  Similarity: 85.2%
  Impact score: 68 (count × lines)
  Affected files:
    - streamlit\helpers\history_data_processing.py
    - streamlit\helpers\history_data_processing.py

  #6: calculate_hole_difficulty
  Type: EXACT duplicate
  Occurrences: 2
  Line count: 32
  Impact score: 64 (count × lines)
  Affected files:
    - streamlit\commentary\round_data_loader.py
    - streamlit\commentary\unified_round_data_loader.py

  #7: plan_wait
  Type: EXACT duplicate
  Occurrences: 2
  Line count: 19
  Impact score: 38 (count × lines)
  Affected files:
    - streamlit\commentary\generate_round_report.py
    - streamlit\commentary\generate_tournament_commentary_v2.py

  #8: display_completeness_status
  Type: NEAR duplicate
  Occurrences: 2
  Line count: 16
  Similarity: 85.7%
  Impact score: 32 (count × lines)
  Affected files:
    - streamlit\helpers\history_data_processing.py
    - streamlit\helpers\history_data_processing.py

  #9: render_report
  Type: NEAR duplicate
  Occurrences: 2
  Line count: 14
  Similarity: 88.9%
  Impact score: 28 (count × lines)
  Affected files:
    - streamlit\latest_teg_context.py
    - streamlit\teg_reports.py

  #10: acquire
  Type: NEAR duplicate
  Occurrences: 2
  Line count: 13
  Similarity: 92.3%
  Impact score: 26 (count × lines)
  Affected files:
    - streamlit\commentary\generate_round_report.py
    - streamlit\commentary\generate_tournament_commentary_v2.py

  #11: safe_int
  Type: EXACT duplicate
  Occurrences: 3
  Line count: 8
  Impact score: 24 (count × lines)
  Affected files:
    - streamlit\commentary\round_data_loader.py
    - streamlit\commentary\round_pattern_analysis.py
    - streamlit\commentary\unified_round_data_loader.py

  #12: get_api_key
  Type: NEAR duplicate
  Occurrences: 2
  Line count: 9
  Similarity: 88.9%
  Impact score: 18 (count × lines)
  Affected files:
    - streamlit\commentary\generate_round_report.py
    - streamlit\commentary\generate_tournament_commentary_v2.py

  #13: __init__
  Type: EXACT duplicate
  Occurrences: 2
  Line count: 5
  Impact score: 10 (count × lines)
  Affected files:
    - streamlit\commentary\generate_round_report.py
    - streamlit\commentary\generate_tournament_commentary_v2.py

  #14: _prune
  Type: EXACT duplicate
  Occurrences: 2
  Line count: 4
  Impact score: 8 (count × lines)
  Affected files:
    - streamlit\commentary\generate_round_report.py
    - streamlit\commentary\generate_tournament_commentary_v2.py

  #15: used_last_min
  Type: EXACT duplicate
  Occurrences: 2
  Line count: 4
  Impact score: 8 (count × lines)
  Affected files:
    - streamlit\commentary\generate_round_report.py
    - streamlit\commentary\generate_tournament_commentary_v2.py

6. FILE COMPLEXITY ANALYSIS
--------------------------------------------------------------------------------
Files with the most functions (candidates for splitting)


  #1: streamlit\utils.py
  Functions: 102
  Total function lines: 4048
  Average function size: 39.7 lines

  #2: streamlit\commentary\generate_tournament_commentary_v2.py
  Functions: 52
  Total function lines: 2142
  Average function size: 41.2 lines

  #3: streamlit\helpers\streak_analysis_processing.py
  Functions: 29
  Total function lines: 1100
  Average function size: 37.9 lines

  #4: streamlit\admin_volume_management.py
  Functions: 20
  Total function lines: 274
  Average function size: 13.7 lines

  #5: streamlit\commentary\generate_round_report.py
  Functions: 19
  Total function lines: 1112
  Average function size: 58.5 lines

  #6: streamlit\helpers\history_data_processing.py
  Functions: 19
  Total function lines: 759
  Average function size: 39.9 lines

  #7: streamlit\helpers\latest_round_processing.py
  Functions: 16
  Total function lines: 275
  Average function size: 17.2 lines

  #8: streamlit\helpers\best_performance_processing.py
  Functions: 13
  Total function lines: 600
  Average function size: 46.2 lines

  #9: streamlit\commentary\batch_api.py
  Functions: 12
  Total function lines: 356
  Average function size: 29.7 lines

  #10: streamlit\helpers\score_count_processing.py
  Functions: 12
  Total function lines: 529
  Average function size: 44.1 lines

  #11: streamlit\helpers\commentary_generator.py
  Functions: 11
  Total function lines: 408
  Average function size: 37.1 lines

  #12: streamlit\commentary\unified_round_data_loader.py
  Functions: 10
  Total function lines: 855
  Average function size: 85.5 lines

  #13: streamlit\player_history.py
  Functions: 9
  Total function lines: 393
  Average function size: 43.7 lines

  #14: streamlit\commentary\generate_commentary.py
  Functions: 9
  Total function lines: 486
  Average function size: 54.0 lines

  #15: streamlit\commentary\pattern_analysis.py
  Functions: 9
  Total function lines: 775
  Average function size: 86.1 lines
