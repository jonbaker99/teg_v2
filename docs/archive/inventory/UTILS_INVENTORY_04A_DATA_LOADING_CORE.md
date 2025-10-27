# Utils.py Inventory - Section 4A: Data Loading Core Functions

**Section:** Core Data Loading & Filtering
**Function Count:** 6 functions
**Lines in utils.py:** 769-950
**Estimated Complexity:** Medium to Complex

---

## Section Overview

This section documents the foundational data loading and filtering functions that form the core of the data pipeline. These functions handle:

- Loading the main tournament dataset (all-data.parquet)
- Merging with round information (courses, dates, areas)
- Identifying incomplete tournaments
- Filtering/excluding incomplete data
- Mapping player codes to full names
- Processing raw round data with handicaps

**Architecture Context:** These are the **first functions called** by almost every page when starting analysis. They establish the baseline dataset that everything else builds upon.

---

## Functions

### 1. `load_all_data(exclude_teg_50: bool = True, exclude_incomplete_tegs: bool = False) -> pd.DataFrame`

**Line Numbers:** 769-810 (42 lines)
**Function Type:** MIXED
**Complexity:** Complex

**Purpose:**
**PRIMARY DATA LOADING FUNCTION.** Loads the main tournament dataset from parquet file and merges with round information (area, course, date metadata). Provides options to filter out incomplete tournaments and TEG 50 (if needed).

This is the most-called function in the entire application - virtually every page starts with this.

**Full Signature:**
```python
@st.cache_data
def load_all_data(
    exclude_teg_50: bool = True,
    exclude_incomplete_tegs: bool = False
) -> pd.DataFrame:
    """Loads all data from the Parquet file and prepares it for use.

    This function loads the main data file, merges it with round information,
    and provides options to exclude certain data.

    Args:
        exclude_teg_50 (bool, optional): Whether to exclude TEG 50.
            Defaults to True.
        exclude_incomplete_tegs (bool, optional): Whether to exclude
            incomplete TEGs. Defaults to False.

    Returns:
        pd.DataFrame: The loaded and prepared data as a pandas DataFrame.
    """
```

**Parameters:**
- `exclude_teg_50` (bool, optional): Filter out TEG 50 (special/test tournament). Default: True
- `exclude_incomplete_tegs` (bool, optional): Filter out TEGs with missing rounds. Default: False

**Returns:**
- `pd.DataFrame`: Complete tournament dataset with columns from both all-data.parquet and round_info.csv merged

**Caching:**
- `@st.cache_data` decorator - **NO TTL** - persists until manually cleared
- Shared cache across all users on Railway instance
- Must be manually cleared after data updates

**Dependencies:**
- **External Packages:** pandas, streamlit
- **Internal Functions:** `read_file()`, `exclude_incomplete_tegs_function()`
- **Data Files:**
  - `ALL_DATA_PARQUET` - Primary dataset
  - `ROUND_INFO_CSV` - Round metadata (Area, Course, Date)
- **Streamlit-Specific:** Yes - `@st.cache_data` decorator, `st.error()`
- **File I/O:** Yes - reads 2 parquet/CSV files

**Workflow:**
1. Load ALL_DATA_PARQUET using `read_file()`
2. Load ROUND_INFO_CSV using `read_file()`
3. Merge on ['TEGNum', 'Round'] to add Area information
4. Convert 'Year' column to nullable Int64
5. Filter out TEG 50 if `exclude_teg_50=True`
6. Filter out incomplete TEGs if `exclude_incomplete_tegs=True`
7. Return combined DataFrame

**Used By (Extremely extensive - ~40+ files):**
- `streamlit/101TEG Honours Board.py` - Load historical winners
- `streamlit/101TEG History.py` - Tournament history display
- `streamlit/102TEG Results.py` - Round-by-round results
- `streamlit/300TEG Records.py` - Record lookups
- `streamlit/303Final Round Comebacks.py` - Comeback analysis
- `streamlit/400scoring.py` - Scoring analysis
- `streamlit/ave_by_par.py` - Average vs par analysis
- `streamlit/ave_by_teg.py` - TEG averages
- `streamlit/best_eclectics.py` - Best eclectic calculations
- `streamlit/bestball.py` - Best ball analysis
- `streamlit/birdies_etc.py` - Achievement tracking
- `streamlit/biggest_changes.py` - Score changes
- `streamlit/eclectic.py` - Eclectic calculations
- `streamlit/leaderboard.py` - Tournament leaderboards
- `streamlit/player_history.py` - Player career stats
- `streamlit/score_by_course.py` - Course performance
- `streamlit/score_heatmaps.py` - Heat map visualization
- `streamlit/streak_analysis.py` - Streak calculations
- Helper functions extensively
- Commentary generation functions

**Output DataFrame Columns:**
From all-data.parquet:
- TEGNum, TEG, Round, Hole, Pl, Player, Sc, PAR, GrossVP, Net, NetVP, Stableford, HC, HCStrokes, HoleID, FrontBack
- Cumulative scores: `Sc Cum Round`, `Sc Cum TEG`, `Sc Cum Career`
- Averages: `Sc Round Avg`, `Sc TEG Avg`, `Sc Career Avg`
- Rankings: `Rank_GrossVP_TEG`, `Rank_Stableford_TEG`
- Gaps: `Gap_GrossVP_TEG`, `Gap_Stableford_TEG`

From round_info.csv (merged):
- Area, Course, Date, Year

**Error Handling:**
- FileNotFoundError - If parquet file doesn't exist → shows `st.error()` and returns empty DataFrame
- Merge conflicts → Handled gracefully with `how='left'`
- Missing Area data → Warning logged but continues

**Performance Characteristics:**
- First call (cache miss): 1-2 seconds (GitHub download + merge)
- Subsequent calls (cache hit): ~50ms (memory access only)
- DataFrame size: ~50,000-100,000 rows depending on TEG count and excluded data

**Important Notes:**
- **Caching note:** Cache persists until `st.cache_data.clear()` is called
- **Year conversion:** Converts to nullable Int64 to handle potential NaN values
- **Area merge:** Uses left join to preserve rows even if round_info is incomplete
- **Incomplete TEG filtering:** Uses `exclude_incomplete_tegs_function()` which is more sophisticated

**Filtering Behavior:**

| exclude_teg_50 | exclude_incomplete_tegs | Result |
|---|---|---|
| True | False | All TEGs except 50, including incomplete |
| True | True | Only complete TEGs except 50 |
| False | False | All TEGs including 50 and incomplete |
| False | True | All complete TEGs including 50 |

**Migration Recommendation:**
- **Target Module:** Keep in utils.py - CRITICAL
- **Rationale:** Core data loading; too widely used to migrate
- **Priority:** CRITICAL - Application won't work without this
- **Breaking Changes:** Would break almost everything if removed

**Potential Improvements:**
1. Add file validation (checksum verification)
2. Add explicit error messages for common failure modes
3. Could add `as_of_date` parameter for historical snapshots
4. Could implement incremental loading for very large datasets
5. Could add data quality checks (missing columns, invalid types)

---

### 2. `get_number_of_completed_rounds_by_teg(df: pd.DataFrame) -> pd.DataFrame`

**Line Numbers:** 813-828 (16 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
Counts the number of completed rounds for each tournament. Returns a DataFrame showing rounds per TEG, useful for identifying which tournaments are complete/in-progress.

**Full Signature:**
```python
def get_number_of_completed_rounds_by_teg(df: pd.DataFrame) -> pd.DataFrame:
    """Gets the number of completed rounds for each TEG.

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: A DataFrame with the number of completed rounds for
        each TEG.
    """
```

**Parameters:**
- `df` (pd.DataFrame): DataFrame with at least ['TEGNum', 'TEG', 'Round'] columns

**Returns:**
- `pd.DataFrame`: Columns: [TEGNum, TEG, num_rounds]
  - TEGNum: Tournament number (e.g., 16)
  - TEG: Tournament name (e.g., "TEG 16")
  - num_rounds: Count of unique rounds in this TEG

**Example Output:**
```
   TEGNum   TEG  num_rounds
0      1   TEG 1          1
1      2   TEG 2          3
2      3   TEG 3          4
3      4   TEG 4          4
```

**Dependencies:**
- **External Packages:** pandas
- **Internal Functions:** None
- **Streamlit-Specific:** No
- **File I/O:** No

**Used By:**
- `get_hc()` - For handicap calculations needing round counts
- `analyze_teg_completion()` - For TEG status analysis
- Data update processing - For validation

**Technical Notes:**
- Simple groupby + nunique operation
- Fast O(n) operation
- No filtering or transformations

**Migration Recommendation:**
- **Target Module:** Keep in utils.py or move to data utilities module
- **Rationale:** Pure data aggregation function
- **Priority:** MEDIUM - Could be migrated
- **Breaking Changes:** Minor - just need import update

---

### 3. `get_incomplete_tegs(df: pd.DataFrame) -> pd.Series`

**Line Numbers:** 831-852 (22 lines)
**Function Type:** PURE
**Complexity:** Medium

**Purpose:**
Identifies TEGs that don't have all expected rounds. Uses TEGNUM_ROUNDS dictionary to determine expected round count for each tournament, then finds those that don't match actual rounds in the data.

**Full Signature:**
```python
def get_incomplete_tegs(df: pd.DataFrame) -> pd.Series:
    """Gets a list of incomplete TEGs.

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: A DataFrame with the TEG numbers of incomplete TEGs.
    """
```

**Parameters:**
- `df` (pd.DataFrame): DataFrame with ['TEGNum', 'Round'] columns

**Returns:**
- `pd.Series`: Integer series of TEGNum values that are incomplete

**Example:**
```python
get_incomplete_tegs(all_data)
# Returns: Series([18, 19, 20])  # These TEGs don't have all expected rounds
```

**Dependencies:**
- **External Packages:** pandas
- **Internal Functions:** `get_tegnum_rounds()` - Gets expected rounds per TEG
- **Data Dependencies:** `TEGNUM_ROUNDS` constant
- **Streamlit-Specific:** No
- **File I/O:** No

**Workflow:**
1. Group by TEGNum and count unique Rounds
2. For each TEGNum, get expected rounds from TEGNUM_ROUNDS
3. Compare actual vs expected
4. Return TEGNums where actual ≠ expected

**Used By:**
- `exclude_incomplete_tegs_function()` - To filter incomplete TEGs
- `get_incomplete_tegs()` - When loading data with flag
- Analysis functions - To check completion status

**Error Handling:**
- TEGNums not in TEGNUM_ROUNDS → Assumes 4 rounds (default)
- Missing Round data → Filtered out naturally by groupby

**Technical Notes:**
- Uses `nunique()` to count distinct rounds
- Compares with dictionary lookup for expected rounds
- Returns Series (index=TEGNum, values=Series boolean mask converted to list)

**Migration Recommendation:**
- **Target Module:** Move to data utilities
- **Rationale:** Pure data validation function
- **Priority:** LOW - Could be consolidated
- **Breaking Changes:** Minor

---

### 4. `exclude_incomplete_tegs_function(df: pd.DataFrame) -> pd.DataFrame`

**Line Numbers:** 855-882 (28 lines)
**Function Type:** PURE
**Complexity:** Medium

**Purpose:**
Filters out TEGs with incomplete rounds from a DataFrame. Used internally by `load_all_data()` when `exclude_incomplete_tegs=True` flag is set.

**Full Signature:**
```python
def exclude_incomplete_tegs_function(df: pd.DataFrame) -> pd.DataFrame:
    """Excludes TEGs with incomplete rounds from the DataFrame.

    This function identifies and removes TEGs that do not have the expected
    number of rounds.

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: A DataFrame with incomplete TEGs excluded.
    """
```

**Parameters:**
- `df` (pd.DataFrame): Input data with hole-by-hole records

**Returns:**
- `pd.DataFrame`: Filtered data with only complete TEGs

**Workflow:**
1. Use `get_incomplete_tegs()` to identify incomplete tournaments
2. Filter out rows where TEGNum is in incomplete list
3. Return filtered DataFrame

**Used By:**
- `load_all_data()` - When `exclude_incomplete_tegs=True`
- Data analysis pages - When only complete data needed
- Report generation - For finalized statistics

**Technical Notes:**
- Uses `~df['TEGNum'].isin(incomplete_tegs)` for filtering
- Preserves DataFrame structure completely
- No data transformation, just filtering

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** Used directly by load_all_data()
- **Priority:** MEDIUM
- **Breaking Changes:** Minor

---

### 5. `get_player_name(initials: str) -> str`

**Line Numbers:** 885-895 (11 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
Converts player initials (e.g., "JB") to full player name (e.g., "Jon BAKER") using the PLAYER_DICT constant. Simple lookup function with fallback to "Unknown Player".

**Full Signature:**
```python
def get_player_name(initials: str) -> str:
    """Retrieves the full name of a player from their initials.

    Args:
        initials (str): The initials of the player.

    Returns:
        str: The full name of the player, or 'Unknown Player' if the
        initials are not found.
    """
```

**Parameters:**
- `initials` (str): Player initials (e.g., "JB", "DM", "GW")

**Returns:**
- `str`: Full player name or "Unknown Player" if not found

**Examples:**
```python
get_player_name("JB")   # Returns: "Jon BAKER"
get_player_name("GW")   # Returns: "Gregg WILLIAMS"
get_player_name("XX")   # Returns: "Unknown Player"
get_player_name("jb")   # Returns: "Jon BAKER" (case insensitive)
```

**Dependencies:**
- **External Packages:** None
- **Internal Functions:** None
- **Data Dependencies:** `PLAYER_DICT` constant
- **Streamlit-Specific:** No
- **File I/O:** No

**PLAYER_DICT Contents:**
```python
{
    'AB': 'Alex BAKER',
    'JB': 'Jon BAKER',
    'DM': 'David MULLIN',
    'GW': 'Gregg WILLIAMS',
    'HM': 'Henry MELLER',
    'SN': 'Stuart NEUMANN',
    'JP': 'John PATTERSON',
    'GP': 'Graham PATTERSON',
}
```

**Technical Notes:**
- Uses `.upper()` for case-insensitive lookup
- Dictionary `.get()` with fallback ensures no KeyError
- Very fast O(1) lookup

**Used By (Extensive):**
- `process_round_for_all_scores()` - Maps Pl → Player
- All pages that display player names
- Data validation functions
- HTML/display generation

**Error Handling:**
- Unknown initials → Returns "Unknown Player"
- Never raises exceptions
- Safe to call with any input

**Migration Recommendation:**
- **Target Module:** Keep in utils.py OR move to config/constants
- **Rationale:** Simple lookup function; could be inlined
- **Priority:** LOW - Not critical
- **Breaking Changes:** None

**Potential Improvements:**
1. Could add reverse mapping (name → initials)
2. Could support multiple name formats
3. Could log unknown initials for monitoring
4. Could make PLAYER_DICT more maintainable

---

### 6. `process_round_for_all_scores(long_df: pd.DataFrame, hc_long: pd.DataFrame) -> pd.DataFrame`

**Line Numbers:** 898-950 (53 lines)
**Function Type:** MIXED
**Complexity:** Complex

**Purpose:**
**CORE DATA TRANSFORMATION FUNCTION.** Processes raw round data by:
- Merging with handicap information
- Calculating handicap strokes for each hole
- Computing gross vs par, net score, and stableford points
- Creating player name mappings
- Preparing data for analysis

This is critical for converting raw scores into analyzable metrics.

**Full Signature:**
```python
def process_round_for_all_scores(
    long_df: pd.DataFrame,
    hc_long: pd.DataFrame
) -> pd.DataFrame:
    """Processes round data to calculate various scores and metrics.

    This function takes long-format round data and handicap data, merges them,
    and calculates a variety of scores including Gross, Net, and Stableford.

    Args:
        long_df (pd.DataFrame): DataFrame containing round data.
        hc_long (pd.DataFrame): DataFrame containing handicap data.

    Returns:
        pd.DataFrame: A processed DataFrame with additional computed columns.
    """
```

**Parameters:**
- `long_df` (pd.DataFrame): Raw round data in long format with columns:
  - TEGNum, Round, Hole, Score, Par, SI (Stroke Index), Pl, PAR
- `hc_long` (pd.DataFrame): Handicap data from load_and_prepare_handicap_data()
  - Columns: TEG, Pl, HC

**Returns:**
- `pd.DataFrame`: Enhanced data with calculated scoring columns

**Output Columns Added:**
- TEG: Tournament name (e.g., "TEG 16")
- HC: Player handicap
- HoleID: Unique hole identifier (e.g., "T16|R1|H01")
- FrontBack: "Front" or "Back" (holes 1-9 vs 10-18)
- Player: Full player name (from initials)
- HCStrokes: Handicap strokes applicable to this hole
- GrossVP: Gross vs par (Score - Par)
- Net: Net score (Gross - HCStrokes)
- NetVP: Net vs par (Net - Par)
- Stableford: Stableford points (max 0, formula: 2 - NetVP capped at 0)

**Dependencies:**
- **External Packages:** pandas, numpy
- **Internal Functions:**
  - `get_player_name()` - Map player codes to names
  - Uses constants: `PLAYER_DICT`
- **Streamlit-Specific:** No
- **File I/O:** No

**Workflow:**
1. Rename Score → Sc, Par → PAR for consistency
2. Create TEG column from TEGNum
3. Merge with handicap data on [TEG, Pl]
4. Fill missing HC values with 0
5. Create HoleID: "T{tegnum}|R{round}|H{hole}"
6. Create FrontBack: 1-9="Front", 10-18="Back"
7. Map player codes to names via PLAYER_DICT
8. Calculate HCStrokes from HC and SI:
   - `HCStrokes = (HC // 18) + ((HC % 18 >= SI) ? 1 : 0)`
9. Calculate scoring metrics:
   - GrossVP = Score - Par
   - Net = Score - HCStrokes
   - NetVP = Net - Par
   - Stableford = max(0, 2 - NetVP)

**Technical Notes:**
- Uses vectorized numpy operations for performance
- HC calculation handles both full handicap and stroke distribution
- Stableford formula: 2 - NetVP, capped at 0 minimum
- String formatting for HoleID uses zfill for consistent padding
- Logging set to DEBUG level

**Error Scenarios:**
- Missing handicap data → Filled with 0 (assumes no handicap)
- Invalid column names → Logged but may cause failure
- Non-numeric data in Score/Par → pandas will error

**Performance:**
- Vectorized operations: O(n)
- Typical processing: <500ms for 10,000 holes

**Used By:**
- Data update processing - After loading new round data
- All data transformations - Core calculation step
- Commentary generation - Needs processed metrics

**Validation:**
- Function logs number of rows at each step
- Should preserve row count (1:1 with long_df)

**Migration Recommendation:**
- **Target Module:** Move to data processing module
- **Rationale:** Pure calculation function with no Streamlit dependency
- **Priority:** HIGH - Core calculation but no UI coupling
- **Breaking Changes:** Minor - just import update

**Potential Improvements:**
1. Add data validation for expected columns
2. Add error handling for invalid handicap values
3. Add logging of any dropped rows
4. Add unit tests for scoring calculations
5. Could parameterize stableford formula

---

## Section Summary

**Section Statistics:**
- Total Functions: 6
- Total Lines: ~180 lines of code
- Complexity: Mostly Medium, 2 Complex
- Pure Functions: 4 (`get_number_of_completed_rounds_by_teg`, `get_incomplete_tegs`, `exclude_incomplete_tegs_function`, `get_player_name`)
- Mixed Functions: 2 (`load_all_data`, `process_round_for_all_scores`)

**Key Architectural Points:**

1. **load_all_data()** is the entry point for almost all analysis
2. **Caching strategy:** load_all_data uses @st.cache_data with no TTL
3. **Filtering options:** Can exclude TEG 50 and/or incomplete TEGs
4. **Data enrichment:** Round info merged to add Area/Course/Date context
5. **Normalization:** process_round_for_all_scores creates consistent scoring columns

**Data Flow:**
```
Raw CSV/Parquet
    ↓
load_all_data()
    ├─ Read all-data.parquet
    ├─ Read round_info.csv
    ├─ Merge on [TEGNum, Round]
    ├─ Filter TEG 50 (optional)
    └─ Filter incomplete (optional)
        ↓
   Cleaned DataFrame
    ├─ Used directly by pages
    └─ Passed to process_round_for_all_scores()
        ├─ Merge with handicaps
        ├─ Calculate metrics
        ├─ Create scoring columns
        └─ Output: Analysis-ready data
```

**Critical Dependencies:**
- These 6 functions form the foundation of all analysis
- ~40+ pages depend on load_all_data()
- Data update pipeline depends on process_round_for_all_scores()
- Cannot remove any without breaking application

**Performance Profile:**
- Initial load: 1-2 seconds (GitHub + merge)
- Cached access: ~50ms
- Processing: <500ms for typical datasets
- Memory: ~50-100MB for full dataset

**Recommended Improvements:**
1. Add data quality validation in load_all_data()
2. Add error recovery for partial loads
3. Implement incremental data loading
4. Add data versioning/change tracking
5. Document expected data schema explicitly
6. Add comprehensive error messages

---

