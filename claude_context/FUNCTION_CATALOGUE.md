# TEG Codebase Function Catalogue

*Generated from comprehensive analysis of 148 functions across the TEG golf tournament analysis system*

---

## Core Data Loading

Primary data loading functions that handle file I/O, GitHub integration, and environment-aware data access

### `read_file` (`utils.py:144`)
Environment-aware file reading that automatically handles local files vs GitHub API calls for Railway deployment
- Used by: load_all_data, get_google_sheet, check_for_duplicate_data, execute_data_deletion, load_scores_data

### `write_file` (`utils.py:160`)
Environment-aware file writing with automatic GitHub commits for Railway deployment
- Used by: execute_data_update, execute_data_deletion, update_all_data

### `load_all_data` (`utils.py:246`)
Primary cached data loading function with filtering options for TEG 50 and incomplete tournaments
- Used by: Most analysis pages, get_complete_teg_data, get_round_data, score_type_stats, get_scorecard_data

### `get_scorecard_data` (`utils.py:1481`)
Specialized data loading for scorecard generation with flexible filtering by TEG/round/player
- Used by: scorecard_v2.py, scorecard_utils.py, scorecard_v2_mobile.py

### `read_from_github` (`utils.py:91`)
Direct GitHub API file reading for Railway production environment
- Used by: read_file

### `write_to_github` (`utils.py:114`)
Direct GitHub API file writing with commit creation for Railway production
- Used by: write_file

### `backup_file` (`utils.py:176`)
Creates timestamped backup copies of data files before modifications
- Used by: create_timestamped_backups

---

## Data Processing

Functions that process, transform, calculate, and analyze golf tournament data

### `process_round_for_all_scores` (`utils.py:307`)
Core scoring calculation engine that computes GrossVP, NetVP, Stableford points from raw scores and handicaps
- Used by: execute_data_update

### `aggregate_data` (`utils.py:819`)
Flexible data aggregation function supporting TEG, Round, Player, and 9-hole level analysis
- Used by: get_complete_teg_data, get_round_data, get_9_data, get_Pl_data

### `add_cumulative_scores` (`utils.py:375`)
Calculates running cumulative scores through rounds for trend analysis
- Used by: process_round_for_all_scores

### `get_teg_winners` (`utils.py:749`)
Extracts tournament winners (Trophy, Green Jacket, Wooden Spoon) from TEG data
- Used by: 101TEG History.py

### `add_ranks` (`utils.py:936`)
Adds ranking columns to DataFrames for performance comparison
- Used by: get_ranked_teg_data, get_ranked_round_data, get_ranked_frontback_data

### `reshape_round_data` (`utils.py:506`)
Converts wide-format Google Sheets data to long format by hole
- Used by: process_google_sheets_data

---

## Display Formatting

Functions that format data values and generate display-ready content

### `format_vs_par` (`utils.py:730`)
Formats vs-par values with +/- notation (e.g., +2, -1, E for even)
- Used by: Multiple display functions, scorecard_utils.py, bestball.py

### `datawrapper_table` (`utils.py:1349`)
Generates HTML tables with consistent Datawrapper styling
- Used by: ave_by_course.py, sc_count.py, 300TEG Records.py

### `create_stat_section` (`utils.py:1141`)
Creates formatted HTML stat sections for records displays
- Used by: 300TEG Records.py, teg_worsts.py

### `format_record_value` (`helpers/display_helpers.py:24`)
Formats performance values with appropriate +/- notation for records
- Used by: prepare_records_display

### `ordinal` (`utils.py:1081`)
Converts numbers to ordinal strings (1st, 2nd, 3rd, etc.)
- Used by: safe_ordinal

### `safe_ordinal` (`utils.py:1088`)
Safe ordinal conversion with error handling for None/NaN values
- Used by: chosen_rd_context, chosen_teg_context

---

## Scorecard Generation

Functions that generate HTML scorecards in various formats for different display scenarios

### `generate_single_round_html` (`scorecard_utils.py:144`)
Generates HTML for individual player round scorecards with hole-by-hole details
- Used by: scorecard_v2.py

### `generate_tournament_html` (`scorecard_utils.py:297`)
Creates comprehensive tournament scorecard showing all rounds for one player
- Used by: scorecard_v2.py

### `generate_round_comparison_html` (`scorecard_utils.py:450`)
Generates side-by-side comparison of all players for a specific round
- Used by: scorecard_v2.py

### `generate_single_round_html_mobile` (`scorecard_utils.py:650`)
Mobile-optimized individual round scorecard with responsive design
- Used by: scorecard_v2_mobile.py

### `generate_tournament_html_mobile` (`scorecard_utils.py:790`)
Mobile-optimized tournament scorecard with condensed layout
- Used by: scorecard_v2_mobile.py

### `generate_round_comparison_html_mobile` (`scorecard_utils.py:1028`)
Mobile-optimized round comparison with horizontal scrolling
- Used by: scorecard_v2_mobile.py

### `load_scorecard_css` (`scorecard_utils.py:131`)
Loads CSS styling for scorecard display consistency
- Used by: scorecard_v2.py, scorecard_v2_mobile.py

### `generate_scorecard_html` (`scorecard_utils.py:13`)
Generic scorecard HTML generator with configurable layouts
- Used by: Internal scorecard functions

---

## Chart Visualization

Functions that create interactive charts and visualizations using Plotly

### `create_cumulative_graph` (`make_charts.py:26`)
Creates cumulative performance charts across tournament rounds
- Used by: 102TEG Results.py, leaderboard.py

### `create_round_graph` (`make_charts.py:111`)
Creates round-specific performance charts with annotations
- Used by: latest_round.py

### `format_value` (`make_charts.py:13`)
Formats values for chart display based on chart type
- Used by: create_cumulative_graph, create_round_graph

### `add_round_annotations` (`make_charts.py:6`)
Adds vertical line annotations to mark rounds on charts
- Used by: create_cumulative_graph, create_round_graph

### `adjusted_stableford` (`make_charts.py:103`)
Adjusts Stableford scores for chart display
- Used by: Chart formatting functions

### `adjusted_grossvp` (`make_charts.py:106`)
Adjusts GrossVP values for chart display
- Used by: Chart formatting functions

### `create_percentage_distribution_chart` (`helpers/score_count_processing.py:75`)
Creates percentage distribution bar charts for score analysis
- Used by: sc_count.py

---

## Helper Utilities

General purpose utility functions that support various operations

### `clear_all_caches` (`utils.py:25`)
Clears all Streamlit caches - critical after data updates
- Used by: 1000Data update.py, delete_data.py, execute_data_deletion

### `get_player_name` (`utils.py:294`)
Converts player codes to full names (e.g., 'JB' -> 'Jon Baker')
- Used by: Display functions

### `load_course_info` (`utils.py:1585`)
Loads course information including areas for geographical filtering
- Used by: ave_by_course.py

### `get_trophy_full_name` (`utils.py:1563`)
Converts trophy abbreviations to full names for display
- Used by: 101TEG History.py

### `load_datawrapper_css` (`utils.py:1345`)
Loads standard CSS styling for consistent table appearance
- Used by: Most display pages

### `get_base_directory` (`utils.py:30`)
Gets base directory path for file operations across environments
- Used by: File I/O functions

### `compress_ranges` (`utils_win_tables.py:51`)
Compresses number ranges for display (e.g., '1,2,3,5' -> '1-3, 5')
- Used by: 101TEG History.py

---

## State Management

Functions that manage Streamlit session state and user interface workflows

### `initialize_update_state` (`helpers/data_update_processing.py:38`)
Initializes session state for data update workflow state machine
- Used by: 1000Data update.py

### `initialize_deletion_state` (`helpers/data_deletion_processing.py:22`)
Initializes session state for data deletion workflow state machine
- Used by: delete_data.py

### `initialize_scorecard_session_state` (`helpers/scorecard_data_processing.py:153`)
Sets up session state for scorecard tab selection and preferences
- Used by: scorecard_v2.py

### `initialize_round_selection_state` (`helpers/latest_round_processing.py:32`)
Initializes session state for round selection interface
- Used by: latest_round.py

### `initialize_teg_selection_state` (`helpers/latest_round_processing.py:186`)
Initializes session state for TEG selection interface
- Used by: latest_teg_context.py

### `create_round_selection_reset_function` (`helpers/latest_round_processing.py:70`)
Creates callback function for 'Latest Round' button reset
- Used by: latest_round.py

---

## File Management

Functions for data validation, integrity checking, and file management

### `check_for_complete_and_duplicate_data` (`utils.py:642`)
Validates data integrity across files and detects duplicates
- Used by: 1000Data update.py

### `update_all_data` (`utils.py:598`)
Updates master data files after new data insertion
- Used by: execute_data_update

### `save_to_parquet` (`utils.py:419`)
Saves DataFrame to parquet format with error handling
- Used by: Data processing functions

### `create_timestamped_backups` (`helpers/data_deletion_processing.py:79`)
Creates timestamped backup files before data deletion operations
- Used by: execute_data_deletion

---

## Leaderboard Generation

Functions for creating tournament leaderboards and standings

### `create_leaderboard` (`leaderboard_utils.py:14`)
Creates formatted leaderboard with rankings and position indicators
- Used by: display_leaderboard

### `display_leaderboard` (`leaderboard_utils.py:139`)
Complete leaderboard display with title, table, and champion callouts
- Used by: 102TEG Results.py, leaderboard.py

### `get_champions` (`leaderboard_utils.py:100`)
Extracts and formats champion/leader information from leaderboard
- Used by: display_leaderboard

### `get_last_place` (`leaderboard_utils.py:114`)
Extracts and formats last place information from leaderboard
- Used by: display_leaderboard

### `format_value` (`leaderboard_utils.py:72`)
Formats leaderboard values based on score type (GrossVP, Stableford, etc.)
- Used by: create_leaderboard, generate_table_html

---

## Analysis Functions

Statistical analysis and performance calculation functions

### `get_best` (`utils.py:1020`)
Finds best performances for specified measure, with player-level or overall analysis
- Used by: 301Best_TEGs_and_Rounds.py, 302Personal Best Rounds & TEGs.py

### `get_worst` (`utils.py:1053`)
Finds worst performances for specified measure, with player-level or overall analysis
- Used by: teg_worsts.py

### `score_type_stats` (`utils.py:1263`)
Calculates career statistics for eagles, birdies, pars, and poor scores
- Used by: birdies_etc.py

### `max_scoretype_per_round` (`utils.py:1289`)
Finds maximum achievement counts in single rounds (most birdies, etc.)
- Used by: birdies_etc.py

### `chosen_rd_context` (`utils.py:1096`)
Provides context for how a specific round compares to other rounds
- Used by: latest_round.py

### `chosen_teg_context` (`utils.py:1118`)
Provides context for how a specific TEG compares to other TEGs
- Used by: latest_teg_context.py

### `calculate_multi_score_running_sum` (`helpers/streak_analysis_processing.py:35`)
Calculates consecutive achievement streaks (consecutive pars, birdies, etc.)
- Used by: prepare_streak_data_for_display

---

## Cached Data Functions

Streamlit cached functions for optimized data loading

### `get_complete_teg_data` (`utils.py:878`)
Cached function returning complete TEG-level data excluding incomplete tournaments
- Used by: teg_worsts.py

### `get_round_data` (`utils.py:890`)
Cached function returning round-level aggregated data with filtering options
- Used by: ave_by_course.py, teg_worsts.py

### `get_9_data` (`utils.py:896`)
Cached function returning 9-hole (front/back) aggregated data
- Used by: teg_worsts.py

### `get_ranked_teg_data` (`utils.py:1003`)
Cached function returning TEG data with performance rankings added
- Used by: 301Best_TEGs_and_Rounds.py, 302Personal Best Rounds & TEGs.py, latest_teg_context.py

### `get_ranked_round_data` (`utils.py:1009`)
Cached function returning round data with performance rankings added
- Used by: 301Best_TEGs_and_Rounds.py, 302Personal Best Rounds & TEGs.py, latest_round.py

### `get_ranked_frontback_data` (`utils.py:1015`)
Cached function returning 9-hole data with performance rankings added
- Used by: Records and analysis pages

### `get_google_sheet` (`utils.py:431`)
Cached function for loading data from Google Sheets with authentication
- Used by: 1000Data update.py

### `calculate_bestball_scores` (`helpers/bestball_processing.py:55`)
Cached calculation of bestball team format scores (best score per hole)
- Used by: bestball.py

### `calculate_worstball_scores` (`helpers/bestball_processing.py:85`)
Cached calculation of worstball team format scores (worst score per hole)
- Used by: bestball.py

---

## Specialized Processing

Functions for specific analysis types and specialized data processing

### `summarise_teg_wins` (`utils_win_tables.py:6`)
Creates summary tables of TEG wins by player with win counts and TEG lists
- Used by: 101TEG History.py

### `process_google_sheets_data` (`helpers/data_update_processing.py:56`)
Processes and validates data from Google Sheets for import
- Used by: 1000Data update.py

### `execute_data_update` (`helpers/data_update_processing.py:119`)
Executes complete data update workflow with backup and processing
- Used by: 1000Data update.py

### `prepare_streak_data_for_display` (`helpers/streak_analysis_processing.py:118`)
Complete workflow for calculating and summarizing performance streaks
- Used by: streaks.py

### `count_scores_by_player` (`helpers/score_count_processing.py:38`)
Creates score distribution matrices showing frequency of each score by player
- Used by: sc_count.py

### `validate_and_prepare_single_round_data` (`helpers/scorecard_data_processing.py:53`)
Validates scorecard data for completeness and formats for display
- Used by: scorecard_v2.py

---

*Total: 148 functions across 11 functional categories*