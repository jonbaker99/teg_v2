# Utils.py Inventory - Section 5: Cache Update Functions

**Section:** Cache Management & Data Updates
**Function Count:** 7 functions
**Lines in utils.py:** 1072-1529
**Estimated Complexity:** Medium to Complex

---

## Section Overview

This section documents functions that manage computed data caches and perform bulk data updates. These are primarily used during data ingestion and maintenance operations. Functions include:

- Updating streak calculation caches
- Updating best ball/worst ball caches
- Updating commentary summary caches
- Bulk data updates with deferred GitHub commits
- Google Sheets integration
- Data preparation and reshaping

---

## Functions

### 1. `update_streaks_cache(defer_github: bool = False) -> Optional[list]`

**Line Numbers:** 1072-1145 (74 lines)
**Function Type:** MIXED
**Complexity:** Complex

**Purpose:**
Regenerates the streaks cache (streaks.parquet) by recalculating all player streaks across the entire career. Supports deferred GitHub commits for batch operations.

**Workflow:**
1. Load all-data (complete dataset)
2. Get unique players
3. For each player, calculate all 10 streak types
4. Save to streaks.parquet
5. Optionally defer GitHub push for batch commit

**Used By:**
- `9999_generate_caches.py` - Manual cache regeneration
- Data update pipeline - After new round data added

**Output File:** `data/streaks.parquet`

**Returns:**
- `dict` (if defer_github=True): File info for batch commit
- `None` (if defer_github=False): Commits immediately

---

### 2. `update_bestball_cache(defer_github: bool = False) -> Optional[list]`

**Line Numbers:** 1148-1198 (51 lines)
**Function Type:** MIXED
**Complexity:** Medium

**Purpose:**
Regenerates best ball and worst ball calculations across the tournament. Computes eclectic low/high scores by hole.

**Output File:** `data/bestball.parquet`

**Technical Notes:**
- Best ball: minimum score at each hole
- Worst ball: maximum score at each hole
- Includes cumulative calculations
- Supports deferred commits

**Used By:**
- Cache regeneration scripts
- Data update pipeline

---

### 3. `update_commentary_caches(defer_github: bool = False) -> Optional[list]`

**Line Numbers:** 1200-1328 (129 lines)
**Function Type:** MIXED
**Complexity:** Complex

**Purpose:**
Regenerates all five commentary summary caches at once:
1. Round summary (round-level statistics)
2. Round events (key moments during rounds)
3. Tournament summary (tournament-level statistics)
4. Round streaks (streak data by round)
5. Tournament streaks (streak data by tournament)

**Output Files:**
- `data/commentary_round_summary.parquet`
- `data/commentary_round_events.parquet`
- `data/commentary_tournament_summary.parquet`
- `data/commentary_round_streaks.parquet`
- `data/commentary_tournament_streaks.parquet`

**Workflow:**
1. Load all-data
2. Call create_round_summary()
3. Call create_round_events()
4. Call create_tournament_summary()
5. Call create_round_streaks_summary()
6. Call create_tournament_streaks_summary()
7. Save all 5 parquet files
8. Defer or commit GitHub changes

**Used By:**
- `9999_generate_caches.py`
- Full data update pipeline
- Commentary generation functions

**Dependencies:**
- All five `create_*_summary()` functions from Section 6

---

### 4. `get_google_sheet(sheet_name: str, worksheet_name: str) -> pd.DataFrame`

**Line Numbers:** 1331-1376 (46 lines)
**Function Type:** IO
**Complexity:** Medium

**Purpose:**
Reads data from a Google Sheet using gspread library with service account authentication. Provides access to Google Sheets for data import/export operations.

**Parameters:**
- `sheet_name` (str): Google Sheet name/key
- `worksheet_name` (str): Worksheet name within sheet

**Returns:**
- `pd.DataFrame`: Sheet contents as DataFrame

**Dependencies:**
- gspread library (Google Sheets API)
- google-auth library
- Service account credentials from environment

**Used By:**
- Data import functions
- Configuration management

**Error Handling:**
- Authentication failures
- Missing sheet/worksheet
- Parse errors

---

### 5. `summarise_existing_rd_data(existing_rows: pd.DataFrame) -> pd.DataFrame`

**Line Numbers:** 1427-1442 (16 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
Summarizes existing round data by aggregating scores by player and round. Used during data validation and import preview.

**Parameters:**
- `existing_rows` (pd.DataFrame): Existing round data

**Returns:**
- `pd.DataFrame`: Aggregated round summary

**Used By:**
- Data validation scripts
- Import preview functions

---

### 6. `add_round_info(all_data: pd.DataFrame) -> pd.DataFrame`

**Line Numbers:** 1445-1468 (24 lines)
**Function Type:** MIXED
**Complexity:** Medium

**Purpose:**
Enriches tournament data with round metadata (Area, Course, Date) from round_info.csv. Handles missing information gracefully.

**Parameters:**
- `all_data` (pd.DataFrame): Main tournament data

**Returns:**
- `pd.DataFrame`: Data with round_info columns merged

**Output Columns Added:**
- Area, Course, Date, Year

**Technical Notes:**
- Left merge preserves all rows
- Handles missing Area data
- Converts dates to datetime format

**Used By:**
- Data transformation pipeline
- Analysis functions needing course information

---

### 7. `update_all_data(csv_file: str, parquet_file: str, csv_output_file: str, defer_github: bool = False) -> Optional[list]`

**Line Numbers:** 1471-1529 (59 lines)
**Function Type:** MIXED
**Complexity:** Complex

**Purpose:**
**MAIN DATA UPDATE FUNCTION.** Performs complete data transformation pipeline:
1. Load raw CSV data
2. Reshape from wide to long format
3. Process scoring calculations (handicaps, GrossVP, Stableford)
4. Add cumulative scores
5. Add rankings and gaps
6. Save to both Parquet and CSV
7. Optionally defer GitHub commits for batch

**Workflow:**
1. Read raw CSV using `read_file()`
2. Reshape using `reshape_round_data()`
3. Load handicap data with `load_and_prepare_handicap_data()`
4. Process with `process_round_for_all_scores()`
5. Validate with `check_hc_strokes_combinations()`
6. Add cumulative with `add_cumulative_scores()`
7. Add rankings with `add_rankings_and_gaps()`
8. Add year column (datetime conversion)
9. Save to Parquet via `write_file(..., defer_github=defer_github)`
10. Save to CSV for review via `write_file(...)`
11. Clear cache if not deferred

**Parameters:**
- `csv_file` (str): Input raw CSV path
- `parquet_file` (str): Output parquet path
- `csv_output_file` (str): Output CSV (for review)
- `defer_github` (bool, optional): Defer GitHub push for batch

**Returns:**
- `list` (if defer_github=True): List of file_info dicts for batch commit
- `None` (if defer_github=False): Commits immediately

**Used By:**
- Data update processing module
- `1000Data update.py` page

**Error Handling:**
- Validates input CSV structure
- Logs transformation steps
- Handles missing values gracefully
- Preserves data integrity throughout

**Performance:**
- Typical processing: 1-2 seconds per round of data
- Scales with data volume

**Deferred Commit Example:**
```python
# Process multiple rounds, batch commit at end
file_infos = []
file_infos.extend(update_all_data('data/raw1.csv', 'data/all-data.parquet', 'data/all-data-review.csv', defer_github=True))
file_infos.extend(update_all_data('data/raw2.csv', 'data/all-data.parquet', 'data/all-data-review.csv', defer_github=True))
batch_commit_to_github(file_infos, "Data update: 2 rounds processed")
```

---

## Section Summary

**Section Statistics:**
- Total Functions: 7
- Total Lines: ~470 lines of code
- Complexity: Mostly Medium-Complex
- Pure Functions: 1 (`summarise_existing_rd_data`)
- Mixed Functions: 6 (involving file I/O, data processing, caching)

**Key Architectural Points:**

1. **Cache Regeneration:**
   - All caches have `@st.cache_data` decorators
   - No TTL - persist until manually cleared
   - Must be cleared after updates

2. **Deferred Commits:**
   - All functions support `defer_github` parameter
   - Returns file_info for batch commits
   - Enables atomic multi-file transactions

3. **Data Pipeline:**
   ```
   Raw CSV
       ↓
   Reshape (wide→long)
       ↓
   Handicap merge
       ↓
   Scoring calculations
       ↓
   Cumulative scores
       ↓
   Rankings & gaps
       ↓
   Parquet + CSV output
   ```

**Critical Functions:**
- `update_all_data()` - Most important, used by data pipeline
- `update_commentary_caches()` - Generates 5 analysis caches
- `update_streaks_cache()` - Streak calculations
- `update_bestball_cache()` - Eclectic calculations

**Performance Characteristics:**
- Streak update: ~30-60 seconds (full career calculation)
- Bestball update: ~10-20 seconds
- Commentary update: ~60-90 seconds (multiple summaries)
- Individual round processing: ~1-2 seconds

**Dependencies:**
- These functions orchestrate most other utils functions
- Called by data pipeline in specific order
- Must maintain data consistency

**Improvement Opportunities:**
1. Add progress indicators for long operations
2. Implement error recovery
3. Add data validation checkpoints
4. Optimize large-scale calculations
5. Add transaction rollback capability

---

