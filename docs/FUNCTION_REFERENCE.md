# TEG Analysis Package - Function Reference

**Version:** 1.0.0 (Post-Refactor)
**Last Updated:** 2025-01-27
**Total Functions:** 235+ public functions across 4 layers

---

## Quick Navigation

**Jump to:**
- [I Want To... (Use Case Index)](#i-want-to)
- [Layer Overview](#layer-overview)
- [Complete Function Index](#complete-function-index)
- [Common Patterns](#common-patterns)

---

## I Want To...

### Load & Access Data

**Load tournament data:**
```python
from teg_analysis.core.data_loader import load_all_data
df = load_all_data()  # All completed TEGs
df = load_all_data(exclude_incomplete_tegs=False)  # Include in-progress
```

**Get specific TEG/round data:**
```python
from teg_analysis.analysis.aggregation import get_complete_teg_data, get_round_data
teg_df = get_complete_teg_data(df, teg_num=18)
round_df = get_round_data(df, teg_num=18, round_num=3)
```

**Read/write files (Railway-aware):**
```python
from teg_analysis.io.file_operations import read_file, write_file
df = read_file('data/handicaps.csv')  # Auto: volume cache or GitHub
write_file('data/results.csv', df, 'Update results')
```

---

### Filter & Aggregate Data

**Filter by player/TEG/round:**
```python
from teg_analysis.analysis.aggregation import (
    filter_data_by_teg,
    filter_data_by_player,
    filter_data_by_round
)
teg_data = filter_data_by_teg(df, 18)
player_data = filter_data_by_player(df, 'JB')
round_data = filter_data_by_round(df, 18, 3)
```

**Aggregate data:**
```python
from teg_analysis.analysis.aggregation import aggregate_data
# Aggregate to TEG level
teg_summary = aggregate_data(df, level='teg')
# Aggregate to round level
round_summary = aggregate_data(df, level='round')
# Aggregate to player level
player_summary = aggregate_data(df, level='player')
```

---

### Calculate Rankings & Winners

**Add rankings:**
```python
from teg_analysis.analysis.rankings import add_ranks
df_ranked = add_ranks(df, score_col='GrossVP', group_col='TEGNum')
```

**Get winners:**
```python
from teg_analysis.analysis.aggregation import get_teg_winners
winners = get_teg_winners(df)  # Best gross, best net, worst net per TEG
```

**Get best/worst rounds:**
```python
from teg_analysis.analysis.rankings import get_best, get_worst
best_rounds = get_best(df, metric='GrossVP', n=10)
worst_rounds = get_worst(df, metric='NetVP', n=10)
```

---

### Calculate Records & Streaks

**Identify records:**
```python
from teg_analysis.analysis.records import (
    identify_aggregate_records_and_pbs,
    identify_streak_records,
    identify_all_time_worsts
)
records_df = identify_aggregate_records_and_pbs(df)
streak_records = identify_streak_records(df)
worsts = identify_all_time_worsts(df)
```

**Calculate streaks:**
```python
from teg_analysis.analysis.streaks import (
    build_streaks,
    prepare_good_streaks_data,
    prepare_bad_streaks_data
)
streaks_df = build_streaks(df)
good_streaks = prepare_good_streaks_data(streaks_df)
bad_streaks = prepare_bad_streaks_data(streaks_df)
```

---

### Format & Display Data

**Format scores:**
```python
from teg_analysis.display.formatters import format_vs_par, format_record_value
score_text = format_vs_par(2)  # "+2"
score_text = format_vs_par(-1)  # "-1"
record_text = format_record_value('GrossVP', 68)
```

**Format ordinals:**
```python
from teg_analysis.analysis.rankings import ordinal
ordinal(1)  # "1st"
ordinal(22)  # "22nd"
```

**Apply score type styling:**
```python
from teg_analysis.display.tables import define_score_types, apply_score_types
df_styled = define_score_types(df)
df_styled = apply_score_types(df_styled)
```

---

### Get Metadata

**Get TEG/round metadata:**
```python
from teg_analysis.core.metadata import get_teg_metadata, load_course_info
metadata = get_teg_metadata(teg_num=18, round_num=3)
# Returns: {'TEGNum': 18, 'Round': 3, 'Date': ..., 'Course': ..., etc}

course_info = load_course_info()  # All course data
```

**Get current/in-progress TEG:**
```python
from teg_analysis.analysis.aggregation import get_current_in_progress_teg_fast
teg_num, rounds_played = get_current_in_progress_teg_fast()
```

**Convert player codes:**
```python
from teg_analysis.core.data_loader import get_player_name
name = get_player_name('JB')  # "Jon Baker"
```

---

### Generate Commentary

**Create summaries:**
```python
from teg_analysis.analysis.commentary import (
    create_round_summary,
    create_tournament_summary,
    create_round_events
)
round_summary = create_round_summary(df)
tournament_summary = create_tournament_summary(df)
events = create_round_events(df)
```

---

### Scoring & Competition

**Get competition type:**
```python
from teg_analysis.analysis.scoring import get_net_competition_measure
measure = get_net_competition_measure(teg_num=18)
# Returns: 'Stableford' for TEG 6+, 'NetVP' for TEG 1-5
```

**Calculate stableford points:**
```python
from teg_analysis.analysis.scoring import calculate_stableford_points
df['Stableford'] = calculate_stableford_points(df)
```

---

## Layer Overview

### IO Layer (12 functions)
**Purpose:** File operations and GitHub integration

**Modules:**
- `file_operations` (6 functions) - Local/volume/GitHub file I/O
- `github_operations` (5 functions) - GitHub API operations
- `volume_operations` (1 function) - Railway volume cache

**Key capabilities:**
- Environment-aware file reading (local vs Railway)
- Automatic volume caching for Railway deployment
- GitHub sync for production data updates
- Batch commits for data updates

---

### Core Layer (18 functions)
**Purpose:** Core data loading and transformation

**Modules:**
- `data_loader` (7 functions) - Load tournament data
- `data_transforms` (8 functions) - Transform and validate data
- `metadata` (3 functions) - TEG/round/course metadata

**Key capabilities:**
- Load all tournament data with filtering
- Process round data for analysis
- Add cumulative scores and rankings
- Get player/course/TEG metadata

---

### Analysis Layer (180+ functions)
**Purpose:** Business logic and calculations

**Modules:**
- `aggregation` (68 functions) - Data aggregation and filtering
- `rankings` (8 functions) - Ranking and sorting
- `scoring` (31 functions) - Scoring rules and calculations
- `streaks` (27 functions) - Streak calculations
- `records` (14 functions) - Records identification
- `commentary` (5 functions) - Commentary generation
- `pipeline` (22 functions) - Data processing pipelines

**Key capabilities:**
- Filter and aggregate data at any level
- Calculate rankings and identify winners
- Identify records and personal bests
- Calculate streaks (good and bad)
- Generate commentary and summaries
- Process data updates

---

### Display Layer (19 functions)
**Purpose:** Formatting and presentation utilities

**Modules:**
- `formatters` (8 functions) - Value formatting
- `tables` (7 functions) - Table generation and styling
- `navigation` (4 functions) - Navigation helpers

**Key capabilities:**
- Format scores (+2, -1, E, etc.)
- Format dates and records
- Apply score type styling
- Generate display-ready tables
- Trophy name conversions

---

## Complete Function Index

### IO Layer

#### file_operations.py (6 functions)
- `read_file(file_path)` - Read CSV/Parquet with auto-caching
- `write_file(file_path, data, commit_msg, defer_github)` - Write with GitHub sync
- `read_text_file(file_path)` - Read text files (MD, JSON, etc.)
- `write_text_file(file_path, content, commit_msg, defer_github)` - Write text with sync
- `backup_file(source_path, backup_path)` - Create file backup
- `check_for_complete_and_duplicate_data(df)` - Validate tournament data

#### github_operations.py (5 functions)
- `read_from_github(file_path)` - Read file from GitHub repo
- `read_text_from_github(file_path)` - Read text file from GitHub
- `write_to_github(file_path, data, commit_msg)` - Write CSV/Parquet to GitHub
- `write_text_to_github(file_path, content, commit_msg)` - Write text to GitHub
- `batch_commit_to_github(file_changes)` - Batch commit multiple files

#### volume_operations.py (1 function)
- `clear_volume_cache()` - Clear Railway volume cache

---

### Core Layer

#### data_loader.py (7 functions)
- `load_all_data(exclude_teg_50, exclude_incomplete_tegs)` - Load tournament dataset
- `get_number_of_completed_rounds_by_teg(df)` - Count completed rounds per TEG
- `get_incomplete_tegs(df)` - Identify TEGs with incomplete data
- `exclude_incomplete_tegs_function(df)` - Remove incomplete TEGs from dataset
- `get_player_name(player_code)` - Convert player code to full name
- `process_round_for_all_scores(round_data_dict)` - Process round data for storage
- `add_round_info(df)` - Add round metadata columns to dataframe

#### data_transforms.py (8 functions)
- `check_hc_strokes_combinations(df, handicaps_df)` - Validate handicap data
- `add_cumulative_scores(df)` - Add cumulative score columns
- `add_rankings_and_gaps(df)` - Add ranking and gap-to-leader columns
- `save_to_parquet(df, file_path)` - Save dataframe to parquet format
- `reshape_round_data(df)` - Reshape wide to long format
- `load_and_prepare_handicap_data(file_path)` - Load and validate handicaps
- `summarise_existing_rd_data(all_data_df)` - Summarize existing round data
- `check_for_complete_and_duplicate_data(df)` - Validate data completeness

#### metadata.py (3 functions)
- `get_teg_metadata(teg_num, round_num)` - Get TEG/round metadata dict
- `load_course_info()` - Load all course information
- `get_scorecard_data(teg_num, round_num)` - Get scorecard-specific data

---

### Analysis Layer

#### aggregation.py (68 functions - top 30 shown)
- `get_teg_rounds(teg_str)` - Get number of rounds for TEG string
- `get_tegnum_rounds(teg_num)` - Get number of rounds for TEG number
- `get_teg_winners(df)` - Calculate TEG winners (gross/net/worst)
- `list_fields_by_aggregation_level(level)` - Get fields for aggregation level
- `aggregate_data(df, level, fields)` - Aggregate data to specified level
- `get_complete_teg_data(df, teg_num)` - Get data for completed TEG
- `get_teg_data_inc_in_progress(df, teg_num)` - Get TEG data including in-progress
- `get_round_data(df, teg_num, round_num)` - Get specific round data
- `get_9_data(df, teg_num, round_num, nines)` - Get 9-hole data
- `process_winners_for_charts(winners_df)` - Format winners for charts
- `get_current_in_progress_teg_fast()` - Get current/in-progress TEG number
- `get_current_in_progress_teg(df)` - Get current TEG from data
- `filter_data_by_teg(df, teg_num)` - Filter data for specific TEG
- `filter_data_by_player(df, player_code)` - Filter data for specific player
- `filter_data_by_round(df, teg_num, round_num)` - Filter for specific round
- `filter_data_by_course(df, course_name)` - Filter for specific course
- `filter_data_by_date_range(df, start_date, end_date)` - Filter by date range
- `get_teg_leaderboard(df, teg_num, measure)` - Get TEG leaderboard
- `get_round_leaderboard(df, teg_num, round_num, measure)` - Get round leaderboard
- `get_player_teg_history(df, player_code)` - Get player's TEG history
- `get_player_round_history(df, player_code)` - Get player's round history
- `get_player_pb(df, player_code, metric)` - Get player's personal best
- `get_player_worst(df, player_code, metric)` - Get player's personal worst
- `get_area_statistics(df, area)` - Get statistics for geographic area
- `get_course_statistics(df, course)` - Get statistics for course
- `get_par_statistics(df, par)` - Get statistics by hole par
- `get_hole_statistics(df, hole_num)` - Get statistics for specific hole
- `calculate_gross_vs_par(df)` - Calculate gross vs par
- `calculate_net_vs_par(df)` - Calculate net vs par
- `calculate_handicap_allowance(df)` - Calculate handicap allowances
- ... and 38 more functions

#### rankings.py (8 functions)
- `add_ranks(df, score_col, group_col, ascending)` - Add ranking columns
- `get_ranked_teg_data(df, teg_num)` - Get ranked data for TEG
- `get_ranked_round_data(df, teg_num, round_num)` - Get ranked round data
- `get_ranked_frontback_data(df, teg_num, round_num, nine)` - Get ranked 9-hole data
- `get_best(df, metric, n, filters)` - Get n best results
- `get_worst(df, metric, n, filters)` - Get n worst results
- `ordinal(n)` - Convert number to ordinal (1st, 2nd, etc.)
- `safe_ordinal(n)` - Ordinal with null handling

#### scoring.py (31 functions - top 15 shown)
- `format_vs_par(value)` - Format score vs par (+2, -1, E)
- `get_net_competition_measure(teg_num)` - Get net measure (Stableford vs NetVP)
- `format_vs_par_value(value)` - Format vs par with color
- `prepare_average_scores_by_par(df)` - Calculate average scores by par
- `format_scoring_stats_columns(df)` - Format scoring statistics
- `calculate_multi_score_running_sum(df, score_types)` - Calculate running sum
- `summarize_multi_score_running_sum(df)` - Summarize running sums
- `calculate_stableford_points(df)` - Calculate stableford points
- `calculate_gross_score(df)` - Calculate gross score
- `calculate_net_score(df)` - Calculate net score
- `get_score_distribution(df, metric)` - Get score distribution
- `get_scoring_average(df, metric, group_by)` - Get scoring averages
- `identify_scoring_trends(df, player, metric)` - Identify trends
- `compare_player_scores(df, player1, player2)` - Compare two players
- `get_hole_difficulty_rankings(df)` - Rank holes by difficulty
- ... and 16 more functions

#### streaks.py (27 functions - top 15 shown)
- `build_streaks(df)` - Build complete streaks dataset
- `get_score_type_definitions()` - Get score type definitions
- `get_inverse_score_type_definitions()` - Get inverse score types
- `calculate_multi_score_running_sum(df, score_types)` - Calculate streak sums
- `calculate_inverse_multi_score_running_sum(df, score_types)` - Calculate bad streaks
- `summarize_multi_score_running_sum(df)` - Summarize good streaks
- `summarize_inverse_multi_score_running_sum(df)` - Summarize bad streaks
- `prepare_streak_data_for_display(df)` - Format streaks for display
- `prepare_inverse_streak_data_for_display(df)` - Format bad streaks for display
- `prepare_good_streaks_data(df)` - Prepare good streaks table
- `prepare_bad_streaks_data(df)` - Prepare bad streaks table
- `get_active_streaks(df)` - Get currently active streaks
- `get_ended_streaks(df)` - Get recently ended streaks
- `get_player_streaks(df, player)` - Get streaks for player
- `get_streak_records(df)` - Get all-time streak records
- ... and 12 more functions

#### records.py (14 functions)
- `get_friendly_metric_name(metric)` - Get display name for metric
- `format_record_value(metric, value)` - Format record value for display
- `identify_aggregate_records_and_pbs(df)` - Find records and personal bests
- `identify_9hole_records_and_pbs(df)` - Find 9-hole records
- `identify_streak_records(df)` - Find streak records
- `identify_all_time_worsts(df)` - Find all-time worst performances
- `identify_score_count_records(df)` - Find score count records (eagles, birdies, etc.)
- `get_all_time_score_count_record(df, score_type)` - Get record for score type
- `display_records_and_pbs_summary(df)` - Create records summary
- `prepare_area_filter_options(df)` - Get area filter options
- `get_record_holders(df, metric)` - Get all record holders
- `get_player_records(df, player)` - Get player's records
- `compare_to_records(value, metric)` - Compare value to records
- `is_new_record(df, metric, value)` - Check if new record

#### commentary.py (5 functions)
- `create_round_summary(all_data_df, round_info_df)` - Create round summary table
- `create_round_events(df)` - Identify notable round events
- `create_tournament_summary(df)` - Create tournament summary
- `create_round_streaks_summary(df)` - Summarize round streaks
- `create_tournament_streaks_summary(df)` - Summarize tournament streaks

#### pipeline.py (22 functions - top 12 shown)
- `update_streaks_cache(defer_github)` - Update streaks cache file
- `update_bestball_cache(defer_github)` - Update bestball cache file
- `update_commentary_caches(defer_github)` - Update all commentary caches
- `get_google_sheet(sheet_name)` - Get data from Google Sheet
- `reshape_round_data(df)` - Reshape round data for processing
- `load_and_prepare_handicap_data(file_path)` - Load handicaps
- `summarise_existing_rd_data(df)` - Summarize existing data
- `add_round_info(df)` - Add round information
- `update_all_data(round_data, commit_msg, defer_github)` - Update main dataset
- `initialize_update_state()` - Initialize data update state
- `validate_round_data(round_data)` - Validate round data
- `prepare_round_for_storage(round_data)` - Prepare round for storage
- ... and 10 more functions

---

### Display Layer

#### formatters.py (8 functions)
- `format_vs_par(value)` - Format score vs par (+2, -1, E)
- `format_date_for_scorecard(date_str)` - Format date for scorecard display
- `format_record_value(metric, value)` - Format record value with units
- `prepare_records_display(records_df)` - Prepare records for display
- `prepare_records_table(records_df)` - Create formatted records table
- `prepare_worst_records_table(worsts_df)` - Create worst records table
- `prepare_streak_records_table(streaks_df)` - Create streak records table
- `prepare_score_count_records_table(counts_df)` - Create score count records table

#### navigation.py (4 functions)
- `convert_trophy_name(trophy_name)` - Convert trophy display name
- `get_trophy_full_name(trophy_code)` - Get full trophy name
- `convert_filename_to_streamlit_url(filename)` - Convert file to Streamlit URL
- `get_app_base_url()` - Get application base URL

#### tables.py (7 functions)
- `create_stat_section(df, title, columns)` - Create statistics section
- `define_score_types(df)` - Define score type categories (eagle, birdie, etc.)
- `apply_score_types(df)` - Apply score type styling to dataframe
- `score_type_stats(df)` - Calculate score type statistics
- `max_scoretype_per_round(df)` - Get most common score type per round
- `max_scoretype_per_teg(df)` - Get most common score type per TEG
- `datawrapper_table(df, styling_rules)` - Create styled table for export

---

## Common Patterns

### Pattern 1: Load → Filter → Aggregate → Display

```python
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import filter_data_by_teg, aggregate_data
from teg_analysis.display.formatters import format_vs_par

# Load
df = load_all_data()

# Filter
teg_18_data = filter_data_by_teg(df, 18)

# Aggregate
player_summary = aggregate_data(teg_18_data, level='player')

# Display
player_summary['GrossVP_formatted'] = player_summary['GrossVP'].apply(format_vs_par)
```

### Pattern 2: Rankings Workflow

```python
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.rankings import add_ranks, ordinal

# Load data
df = load_all_data()

# Add rankings
df_ranked = add_ranks(df, score_col='GrossVP', group_col='TEGNum')

# Format rankings
df_ranked['Rank_formatted'] = df_ranked['Rank'].apply(ordinal)
```

### Pattern 3: Records Analysis

```python
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.records import identify_aggregate_records_and_pbs
from teg_analysis.display.formatters import prepare_records_table

# Load data
df = load_all_data()

# Identify records
records_df = identify_aggregate_records_and_pbs(df)

# Format for display
display_table = prepare_records_table(records_df)
```

### Pattern 4: Metadata Lookup

```python
from teg_analysis.core.metadata import get_teg_metadata, load_course_info
from teg_analysis.core.data_loader import get_player_name

# Get TEG info
teg_info = get_teg_metadata(teg_num=18, round_num=3)
course = teg_info['Course']
date = teg_info['Date']

# Get player name
player_name = get_player_name('JB')  # "Jon Baker"

# Get course info
course_info = load_course_info()
par = course_info[course_info['Course'] == course]['Par'].iloc[0]
```

### Pattern 5: File I/O (Railway-aware)

```python
from teg_analysis.io.file_operations import read_file, write_file

# Read (auto: local file, Railway volume, or GitHub)
df = read_file('data/results.csv')

# Write (auto: local file + GitHub sync in production)
write_file('data/results.csv', df, 'Update results', defer_github=False)
```

---

## Import Conventions

### Recommended Import Style

**For commonly used functions:**
```python
# Core data loading
from teg_analysis.core.data_loader import load_all_data, get_player_name
from teg_analysis.core.metadata import get_teg_metadata

# Analysis
from teg_analysis.analysis.aggregation import filter_data_by_teg, aggregate_data
from teg_analysis.analysis.rankings import add_ranks, ordinal
from teg_analysis.analysis.records import identify_aggregate_records_and_pbs

# Display
from teg_analysis.display.formatters import format_vs_par
```

**For module-level imports:**
```python
from teg_analysis.analysis import aggregation, rankings, records
from teg_analysis.display import formatters
```

---

## Tips for Discovery

### Finding Functions by Topic

1. **Data loading/access** → Start with `core.data_loader`
2. **Filtering/grouping** → Check `analysis.aggregation`
3. **Calculations** → Look in `analysis.scoring` or `analysis.rankings`
4. **Records/streaks** → See `analysis.records` or `analysis.streaks`
5. **Formatting output** → Use `display.formatters` or `display.tables`
6. **File operations** → Use `io.file_operations`

### Search Tips

- Use Ctrl+F / Cmd+F to search this document
- Search by verb: "calculate", "get", "format", "identify", "prepare"
- Search by noun: "winner", "streak", "record", "ranking", "metadata"
- Check the "I Want To..." section for common use cases

---

## Related Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Package architecture and design
- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - How to use the package
- **[README.md](README.md)** - Documentation overview
- **[REFACTOR_HISTORY.md](REFACTOR_HISTORY.md)** - Refactoring history

---

**Last Updated:** 2025-01-27
**Package Version:** 1.0.0 (Phase 5 Complete)
