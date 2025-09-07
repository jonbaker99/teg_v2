# Data Flow Analysis - TEG Golf Analysis System

## Cached Functions (@st.cache_data)

### Primary Data Loading Layer
1. **load_all_data** (line 246) - TTL=300s
   - Entry point for all analysis
   - Reads from `ALL_DATA_PARQUET`
   - Filters TEG 50 and incomplete tournaments

2. **load_and_prepare_handicap_data** (line 504)
   - Loads handicap data from CSV
   - Used by data processing functions

3. **load_course_info** (line 1549)
   - Loads course/area combinations
   - Used for geographical analysis

### Aggregated Data Layer (Post-Parquet)
4. **get_complete_teg_data** (line 851)
   - Calls: load_all_data → aggregate_data('TEG')
   - TEG-level aggregation

5. **get_teg_data_inc_in_progress** (line 857)
   - Similar to above but includes incomplete TEGs

6. **get_round_data** (line 863) - CACHE COMMENTED OUT
   - Calls: load_all_data → aggregate_data('Round')
   - Round-level data

7. **get_9_data** (line 869)
   - Calls: load_all_data → aggregate_data('FrontBack')
   - 9-hole aggregation

8. **get_Pl_data** (line 875)
   - Calls: load_all_data → aggregate_data('Player')
   - Player-level aggregation

### Ranked Data Layer (Analysis Ready)
9. **get_ranked_teg_data** (line 976)
   - Calls: get_complete_teg_data → add_ranks
   - TEG data with performance rankings

10. **get_ranked_round_data** (line 982)
    - Calls: get_round_data → add_ranks
    - Round data with rankings

11. **get_ranked_frontback_data** (line 988)
    - Calls: get_9_data → add_ranks
    - 9-hole data with rankings

## Data Pipeline Architecture

```
RAW DATA FILES
├── ALL_DATA_PARQUET (master dataset)
├── HANDICAPS_CSV (player handicaps)
└── ROUND_INFO_CSV (course/date info)
        ↓
PRIMARY LOADING LAYER (cached)
├── load_all_data() ← Most critical function
├── load_and_prepare_handicap_data()
└── load_course_info()
        ↓
AGGREGATION LAYER (cached)
├── get_complete_teg_data()
├── get_round_data() 
├── get_9_data()
└── get_Pl_data()
        ↓
RANKING LAYER (cached)
├── get_ranked_teg_data()
├── get_ranked_round_data()
└── get_ranked_frontback_data()
        ↓
ANALYSIS FUNCTIONS (not cached)
├── get_best() / get_worst()
├── score_type_stats()
├── chosen_rd_context() / chosen_teg_context()
└── get_teg_winners()
        ↓
DISPLAY LAYER (not cached)
├── create_stat_section()
├── format_vs_par()
├── datawrapper_table()
└── load_datawrapper_css()
```

## Pre-Parquet vs Post-Parquet Functions

### PRE-PARQUET (Data Processing/Creation)
**Purpose**: Transform raw data into the master all-data.parquet file

1. **Data Input**:
   - get_google_sheet() - Import from Google Sheets
   - load_and_prepare_handicap_data() - Process handicaps

2. **Data Processing**:
   - process_round_for_all_scores() - Core scoring engine
   - reshape_round_data() - Wide to long format
   - add_cumulative_scores() - Calculate cumulative stats
   - add_round_info() - Add course/date metadata

3. **Data Pipeline**:
   - update_all_data() - Master update workflow
   - check_for_complete_and_duplicate_data() - Validation
   - summarise_existing_rd_data() - Data summaries

4. **File Operations**:
   - read_file() / write_file() - Environment-aware I/O
   - backup_file() - Data safety
   - save_to_parquet() - Final output

### POST-PARQUET (Analysis/Display)
**Purpose**: Analyze the master all-data.parquet file for insights

1. **Data Retrieval** (Cached):
   - load_all_data() - Primary data loading
   - get_complete_teg_data() / get_round_data() / get_9_data()
   - get_ranked_*_data() family

2. **Statistical Analysis**:
   - get_best() / get_worst() - Performance analysis
   - add_ranks() - Ranking calculations  
   - score_type_stats() - Score categorization
   - get_teg_winners() - Tournament winners

3. **Context & Comparison**:
   - chosen_rd_context() / chosen_teg_context()
   - aggregate_data() - Flexible aggregation

4. **Display & Formatting**:
   - create_stat_section() - HTML generation
   - format_vs_par() / ordinal() - Value formatting
   - datawrapper_table() / load_datawrapper_css() - Table styling

## Critical Caching Dependencies

### Cache Chain Relationships
1. **load_all_data** → **get_complete_teg_data** → **get_ranked_teg_data**
2. **load_all_data** → **get_round_data** → **get_ranked_round_data**  
3. **load_all_data** → **get_9_data** → **get_ranked_frontback_data**

### Cache Invalidation Points
- **clear_all_caches()** called after data updates
- **load_all_data** has TTL=300s (5 minutes)
- Other caches persist until manually cleared

### High-Risk Functions (Caching Dependencies)
- **load_all_data**: Used by 16+ files, basis for all analysis
- **get_ranked_*_data** family: Used by records and analysis pages
- **aggregate_data**: Core transformation function

## Function Groupings by Data Flow Stage

### Stage 1: Core I/O (Must Stay Together)
- read_file(), write_file(), backup_file()
- read_from_github(), write_to_github()
- get_base_directory(), get_current_branch()

### Stage 2: Data Processing (Pre-Parquet)
- process_round_for_all_scores(), add_cumulative_scores()
- reshape_round_data(), add_round_info()
- update_all_data(), check_for_complete_and_duplicate_data()

### Stage 3: Data Retrieval (Post-Parquet, Heavily Cached)
- load_all_data() ← MOST CRITICAL
- get_complete_teg_data(), get_round_data(), get_9_data()
- get_ranked_*_data() family

### Stage 4: Analysis Functions
- get_best(), get_worst(), add_ranks()
- score_type_stats(), get_teg_winners()
- chosen_*_context() functions

### Stage 5: Display/Formatting
- create_stat_section(), format_vs_par()
- datawrapper_table(), load_datawrapper_css()
- ordinal(), safe_ordinal()

## Migration Risk Assessment

### HIGHEST RISK (Don't Move Early)
- load_all_data() - Used by 16+ files, has TTL caching
- get_ranked_*_data() family - Complex cache dependencies
- aggregate_data() - Core transformation logic

### MEDIUM RISK  
- Display functions (load_datawrapper_css) - Used by 22+ files
- Statistical analysis functions - Complex interdependencies

### LOWEST RISK (Move First)
- Helper utilities (get_player_name, ordinal)
- Constants and simple formatting functions
- File I/O functions (if moved together)

## Recommendations for Module Organization

1. **Keep cache chains together** - Functions that call each other via cache
2. **Preserve exact caching behavior** - Critical for performance
3. **Move display functions as a group** - Often imported together
4. **Start with helper utilities** - Minimal dependencies, lowest risk