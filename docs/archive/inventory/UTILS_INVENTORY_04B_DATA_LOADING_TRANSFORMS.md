# Utils.py Inventory - Section 4B: Data Loading Transforms

**Section:** Data Transformation & Validation
**Function Count:** 6 functions
**Lines in utils.py:** 953-1424
**Estimated Complexity:** Medium to Complex

---

## Section Overview

This section documents functions that transform and enrich data after the initial load. These functions:

- Validate handicap stroke calculations
- Add cumulative scores and averages across multiple time periods
- Calculate tournament rankings and gaps to leader
- Save processed data to parquet format
- Reshape data between wide and long formats
- Prepare handicap reference data

These are the **transformation layer** between raw data and analysis-ready datasets.

---

## Functions

### 1. `check_hc_strokes_combinations(transformed_df: pd.DataFrame) -> pd.DataFrame`

**Line Numbers:** 953-966 (14 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
Validation function that extracts unique combinations of (HC, SI, HCStrokes) from the data. Used for data quality checking to ensure handicap stroke calculations are consistent and valid.

**Full Signature:**
```python
def check_hc_strokes_combinations(transformed_df: pd.DataFrame) -> pd.DataFrame:
    """Checks for unique combinations of HC, SI, and HCStrokes.

    Args:
        transformed_df (pd.DataFrame): DataFrame containing the transformed
            golf data.

    Returns:
        pd.DataFrame: A DataFrame with unique combinations of HC, SI, and
        HCStrokes.
    """
```

**Parameters:**
- `transformed_df` (pd.DataFrame): Data with columns ['HC', 'SI', 'HCStrokes']

**Returns:**
- `pd.DataFrame`: Unique combinations of those 3 columns (for validation)

**Example Output:**
```
    HC   SI  HCStrokes
0    0    1          0
1    2    3          1
2    4    1          1
3    7    5          1
...
```

**Dependencies:**
- **External Packages:** pandas
- **Internal Functions:** None
- **Streamlit-Specific:** No
- **File I/O:** No

**Use Cases:**
- Data quality verification
- Debugging handicap calculations
- Validating stroke index assignments
- Auditing data consistency

**Technical Notes:**
- `drop_duplicates()` removes duplicate rows (keeps first occurrence)
- Very fast O(n) operation
- No transformations, just extraction

**Used By:**
- Data validation scripts
- QA/testing functions
- Manual data auditing

**Migration Recommendation:**
- **Target Module:** Move to data validation utilities
- **Rationale:** QA/validation only, not critical path
- **Priority:** LOW - Optional function
- **Breaking Changes:** None - not used in core pipeline

---

### 2. `add_cumulative_scores(df: pd.DataFrame) -> pd.DataFrame`

**Line Numbers:** 969-1013 (45 lines)
**Function Type:** MIXED
**Complexity:** Complex

**Purpose:**
**CRITICAL SCORING CALCULATION.** Adds cumulative scores and moving averages across three time periods (Round, TEG, Career) for four key metrics (Sc, GrossVP, NetVP, Stableford). This enables tracking performance trends and comparisons.

**Full Signature:**
```python
def add_cumulative_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Adds cumulative scores and averages to the DataFrame.

    This function calculates cumulative scores and averages for various
    measures across different periods (Round, TEG, Career).

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: The DataFrame with added cumulative scores and
        averages.
    """
```

**Parameters:**
- `df` (pd.DataFrame): Data with ['Pl', 'TEGNum', 'Round', 'Hole', 'Sc', 'GrossVP', 'NetVP', 'Stableford']

**Returns:**
- `pd.DataFrame`: Original data with new cumulative/average columns added

**New Columns Added:**

For each measure (Sc, GrossVP, NetVP, Stableford):
- `{measure} Cum Round`: Cumulative within each round
- `{measure} Cum TEG`: Cumulative within each tournament
- `{measure} Cum Career`: Cumulative across all tournaments
- `{measure} Round Avg`: Average score in current round
- `{measure} TEG Avg`: Average score in current tournament
- `{measure} Career Avg`: Average score in career to date

Support columns:
- `Hole Order Ever`: Sequential hole number across entire career
- `TEG Count`: Hole count within current tournament
- `Career Count`: Hole count across career

**Examples:**

Hole 1 of round 1, TEG 16, player JB:
- Sc Cum Round: 72 (first hole)
- Sc Cum TEG: 72 (first hole of tournament)
- Sc Cum Career: 1,234 (if career total was 1,162)
- Sc Round Avg: 72/1 = 72.0
- Sc TEG Avg: 72/1 = 72.0
- Sc Career Avg: 1,234/17 (if on hole 17 of career)

Hole 18 of round 1, same tournament:
- Sc Cum Round: 1,292 (sum of all 18 holes)
- Sc Cum TEG: 1,292 (sum of all holes so far)
- Sc Cum Career: 2,426 (career total)
- Sc Round Avg: 1,292/18 = 71.8
- Sc TEG Avg: 1,292/18 = 71.8
- Sc Career Avg: 2,426/36 = 67.4 (if now on hole 36 of career)

**Dependencies:**
- **External Packages:** pandas, numpy
- **Internal Functions:** None
- **Streamlit-Specific:** No
- **File I/O:** No

**Workflow:**
1. Sort data by [Pl, TEGNum, Round, Hole]
2. Create 'Hole Order Ever': Sequential count per player
3. For each measure (Sc, GrossVP, NetVP, Stableford):
   - Create cumsum for Round: `groupby(['Pl', 'TEGNum', 'Round']).cumsum()`
   - Create cumsum for TEG: `groupby(['Pl', 'TEGNum']).cumsum()`
   - Create cumsum for Career: `groupby(['Pl']).cumsum()`
4. Calculate 'TEG Count': Hole count within TEG
5. Calculate 'Career Count': Hole count across career
6. For each measure, calculate averages:
   - `Round Avg = Cum Round / Hole`
   - `TEG Avg = Cum TEG / TEG Count`
   - `Career Avg = Cum Career / Career Count`

**Technical Notes:**
- Uses `groupby().cumsum()` for vectorized cumulative operations
- Preserves DataFrame structure (same row count)
- Must be called AFTER data is sorted correctly
- Modifies DataFrame in place

**Data Requirements:**
- Input must have proper grouping columns: Pl, TEGNum, Round, Hole
- Numeric measure columns must exist: Sc, GrossVP, NetVP, Stableford

**Performance:**
- O(n) vectorized operations
- Fast even for large datasets
- Adds ~20-30 columns per row

**Used By:**
- `update_all_data()` - Core transformation step
- Analysis functions - Needing cumulative metrics
- Ranking calculations - Build on cumulative data

**Validation:**
- Cumulative values should only increase (or stay same if score is 0)
- Averages should be realistic (typically 70-80 for golf)

**Migration Recommendation:**
- **Target Module:** Move to data processing module
- **Rationale:** Pure transformation, no Streamlit dependency
- **Priority:** HIGH - Core calculation
- **Breaking Changes:** Minor - import update

**Potential Improvements:**
1. Add data validation for required columns
2. Add error handling for missing Holes
3. Add logging of any warnings
4. Parameterize the time periods (Round, TEG, Career)
5. Add unit tests for cumulative calculations

---

### 3. `add_rankings_and_gaps(df: pd.DataFrame) -> pd.DataFrame`

**Line Numbers:** 1016-1058 (43 lines)
**Function Type:** MIXED
**Complexity:** Complex

**Purpose:**
**CRITICAL RANKING CALCULATION.** Adds tournament-level rankings and gaps to leader for both GrossVP (lower is better) and Stableford (higher is better). Calculates how far behind (or ahead of) the leader each player is at each point in the tournament.

**Full Signature:**
```python
def add_rankings_and_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """Adds TEG-level rankings and gaps to the leader for cumulative scores.

    This function adds the following columns:
    - Rank_GrossVP_TEG: Player's rank based on cumulative GrossVP.
    - Rank_Stableford_TEG: Player's rank based on cumulative Stableford.
    - Gap_GrossVP_TEG: Difference from the leader's cumulative GrossVP.
    - Gap_Stableford_TEG: Difference from the leader's cumulative Stableford.

    Args:
        df (pd.DataFrame): DataFrame with cumulative scores already
            calculated.

    Returns:
        pd.DataFrame: The DataFrame with added ranking and gap columns.
    """
```

**Parameters:**
- `df` (pd.DataFrame): Must have columns ['TEGNum', 'Round', 'Hole', 'GrossVP Cum TEG', 'Stableford Cum TEG']

**Returns:**
- `pd.DataFrame`: Original data plus 4 new ranking columns

**New Columns Added:**
- `TEG_Hole`: Cumulative hole number within tournament (bridges rounds)
- `Rank_GrossVP_TEG`: Ranking position based on GrossVP (1 = leader)
- `Rank_Stableford_TEG`: Ranking position based on Stableford (1 = leader)
- `Gap_GrossVP_TEG`: Strokes behind leader in GrossVP
- `Gap_Stableford_TEG`: Points behind leader in Stableford

**Example Output:**

```
At hole 18 of round 2 (hole 36 cumulative):
Player  GrossVP_Cum  Stableford_Cum  Rank_Gross  Rank_Stab  Gap_Gross  Gap_Stab
JB           +5            145            1          1          0         0     (Leader)
GW           +8            143            2          2          3         2     (3 shots back)
DM          +12            140            3          3          7         5
```

**Dependencies:**
- **External Packages:** pandas, numpy
- **Internal Functions:** None
- **Streamlit-Specific:** No
- **File I/O:** No

**Workflow:**
1. Create 'TEG_Hole': `(Round - 1) * 18 + Hole` (bridges round boundaries)
2. For GrossVP (lower is better - ascending rank):
   - `Rank_GrossVP_TEG = rank(..., ascending=True, method='min')`
   - `Gap_GrossVP_TEG = player_value - leader_value` (leader has min, gap = 0)
3. For Stableford (higher is better - descending rank):
   - `Rank_Stableford_TEG = rank(..., ascending=False, method='min')`
   - `Gap_Stableford_TEG = leader_value - player_value` (leader has max, gap = 0)

**Ranking Method:**
- `method='min'`: Ties get same rank, next rank skips (e.g., 1, 1, 3, 4)
- Grouping: By [TEGNum, TEG_Hole] so all players compared at each hole

**Technical Notes:**
- Rankings update hole-by-hole as cumulative scores change
- Method='min' handles ties gracefully
- Gap calculation is direction-aware (GrossVP ascending, Stableford descending)
- Leader always has Gap = 0

**Data Requirements:**
- Must have cumulative score columns from `add_cumulative_scores()`
- TEGNum, Round, Hole columns required

**Performance:**
- O(n log n) due to ranking operation
- Fast even for tournaments with 8 players × 72 holes = 576 rows

**Used By:**
- `update_all_data()` - Core transformation pipeline
- Analysis functions - Needing tournament standings
- Leaderboard generation - Shows real-time rankings
- Commentary functions - Tracking lead changes

**Example Use Case - Leaderboard:**
```python
# Get standings after hole 36 of tournament
hole_36_data = df[(df['TEG'] == 'TEG 16') & (df['Hole'] == 18) & (df['Round'] == 2)]
leaderboard = hole_36_data[['Player', 'Rank_GrossVP_TEG', 'Gap_GrossVP_TEG']].drop_duplicates()
# Shows who's leading and by how much
```

**Migration Recommendation:**
- **Target Module:** Move to data processing module
- **Rationale:** Pure ranking calculation
- **Priority:** HIGH - Core functionality
- **Breaking Changes:** Minor

**Potential Improvements:**
1. Add validation for required columns
2. Add handling for incomplete tournaments
3. Parameterize ranking methods
4. Add cumulative player count for context

---

### 4. `save_to_parquet(df: pd.DataFrame, output_file: str) -> None`

**Line Numbers:** 1061-1069 (9 lines)
**Function Type:** IO
**Complexity:** Simple

**Purpose:**
Simple wrapper that saves a DataFrame to parquet format using the centralized `write_file()` function. Ensures consistent file writing approach across the application.

**Full Signature:**
```python
def save_to_parquet(df: pd.DataFrame, output_file: str):
    """Saves a DataFrame to a Parquet file.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        output_file (str): The path to the output Parquet file.
    """
```

**Parameters:**
- `df` (pd.DataFrame): Data to save
- `output_file` (str): File path (e.g., "data/processed.parquet")

**Returns:**
- None

**Dependencies:**
- **External Packages:** pandas
- **Internal Functions:** `write_file()` - Centralized write with Railway/local handling
- **Streamlit-Specific:** Indirectly (write_file uses st.cache_data.clear)
- **File I/O:** Yes

**Used By:**
- `update_all_data()` - Saves processed data to parquet
- Data transformation scripts - Caching intermediate results

**Technical Notes:**
- Delegates to `write_file()` which handles:
  - Railway volume writes
  - GitHub backup
  - Cache clearing
- Wrapper ensures consistent behavior

**Migration Recommendation:**
- **Target Module:** Keep in utils.py or consolidate with write_file()
- **Rationale:** Simple wrapper, could be inlined
- **Priority:** LOW - Optional function
- **Breaking Changes:** None

---

### 5. `reshape_round_data(df: pd.DataFrame, id_vars: List[str]) -> pd.DataFrame`

**Line Numbers:** 1379-1400 (22 lines)
**Function Type:** PURE
**Complexity:** Medium

**Purpose:**
Reshapes round data from wide format (columns per player) to long format (one row per player-hole). Essential for data ingestion pipeline when raw score sheets are imported.

**Full Signature:**
```python
def reshape_round_data(
    df: pd.DataFrame,
    id_vars: List[str]
) -> pd.DataFrame:
    """Reshape round data from wide to long format.

    Parameters:
        df (pd.DataFrame): Original wide-format DataFrame.
        id_vars (List[str]): List of identifier variables.

    Returns:
        pd.DataFrame: Reshaped long-format DataFrame.
    """
```

**Parameters:**
- `df` (pd.DataFrame): Data in wide format (columns = [identifying columns + player initials])
- `id_vars` (List[str]): Columns to keep as identifiers (e.g., ['TEGNum', 'Round', 'Hole', 'Par', 'SI'])

**Returns:**
- `pd.DataFrame`: Long format with columns [id_vars + 'Pl' + 'Score']

**Example:**

**Input (Wide Format):**
```
TEGNum Round Hole Par SI  JB  GW  DM
    16     1   1   4  1  72  73  71
    16     1   2   5  3  75  74  76
```

**Output (Long Format):**
```
TEGNum Round Hole Par SI Pl Score
    16     1   1   4  1 JB     72
    16     1   1   4  1 GW     73
    16     1   1   4  1 DM     71
    16     1   2   5  3 JB     75
    16     1   2   5  3 GW     74
    16     1   2   5  3 DM     76
```

**Dependencies:**
- **External Packages:** pandas
- **Internal Functions:** None
- **Streamlit-Specific:** No
- **File I/O:** No

**Workflow:**
1. Use `pd.melt()` to unpivot from wide to long
2. Rename melted columns to 'Pl' (player) and 'Score'
3. Convert Score to numeric (coerce errors to NaN)
4. Drop rows with missing/zero scores
5. Return long-format DataFrame

**Data Cleaning:**
- Drops NaN scores (missing data)
- Drops zero scores (no score entered)
- Converts non-numeric to NaN (coerce mode)

**Used By:**
- Data update processing - Reshaping raw score imports
- Data ingestion pipeline - Converting spreadsheet format

**Technical Notes:**
- `pd.melt()` is standard pandas reshape
- `pd.to_numeric(..., errors='coerce')` handles invalid data gracefully
- Filter `!= 0` removes placeholder/missing values

**Migration Recommendation:**
- **Target Module:** Move to data processing module
- **Rationale:** Pure transformation, specialized for import pipeline
- **Priority:** MEDIUM - Only used during data ingestion
- **Breaking Changes:** None - only internal use

---

### 6. `load_and_prepare_handicap_data(file_path: str) -> pd.DataFrame`

**Line Numbers:** 1404-1424 (21 lines)
**Function Type:** MIXED
**Complexity:** Medium

**Purpose:**
Loads handicap reference data from CSV and reshapes it to long format for merging with round data. Handicaps are stored in wide format (one row per player, columns per TEG) and need to be reshaped for score calculations.

**Full Signature:**
```python
@st.cache_data
def load_and_prepare_handicap_data(file_path: str) -> pd.DataFrame:
    """Load and prepare handicap data from a CSV file.

    Parameters:
        file_path (str): Path to the handicap CSV file.

    Returns:
        pd.DataFrame: Melted and cleaned handicap DataFrame.
    """
```

**Parameters:**
- `file_path` (str): Path to handicap CSV (e.g., HANDICAPS_CSV constant)

**Returns:**
- `pd.DataFrame`: Long format with columns ['TEG', 'Pl', 'HC']

**Caching:**
- `@st.cache_data` decorator - persists until manually cleared

**Example:**

**Input (Wide Format - handicaps.csv):**
```
TEG     JB  GW  DM
TEG 1    5   8  12
TEG 2    4   7  11
TEG 3    3   6  10
```

**Output (Long Format):**
```
    TEG  Pl  HC
0  TEG 1  JB   5
1  TEG 1  GW   8
2  TEG 1  DM  12
3  TEG 2  JB   4
...
```

**Dependencies:**
- **External Packages:** pandas, streamlit
- **Internal Functions:** `read_file()` - Centralized file reading
- **Streamlit-Specific:** Yes - `@st.cache_data` decorator
- **File I/O:** Yes

**Workflow:**
1. Read file using `read_file(file_path)`
2. Melt from wide to long format
   - id_vars = ['TEG']
   - var_name = 'Pl'
   - value_name = 'HC'
3. Drop rows with NaN HC values
4. Drop rows with HC = 0 (no handicap)
5. Return cleaned long-format DataFrame

**Data Cleaning:**
- Drops missing handicaps (NaN)
- Drops zero values (no handicap assigned)
- Preserves order for consistency

**Used By:**
- `process_round_for_all_scores()` - Merging handicaps with round scores
- `update_all_data()` - Data transformation pipeline
- `get_hc()` - Handicap calculations
- `get_current_handicaps_formatted()` - Display formatting

**Technical Notes:**
- Caching ensures handicap data only loaded once per session
- Melt operation converts 1 row per player to N rows (N = TEGs)
- NaN handling crucial (missing players, incomplete data)

**Data Requirements:**
- CSV must have 'TEG' column
- Other columns assumed to be player initials
- Values must be numeric (handicaps)

**Error Handling:**
- FileNotFoundError - If file doesn't exist
- pandas errors bubble up

**Performance:**
- Fast operation (~10-50ms)
- Caching ensures subsequent calls are ~1ms

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** Core data preparation for scoring
- **Priority:** HIGH - Critical for handicap calculations
- **Breaking Changes:** Minor

**Potential Improvements:**
1. Add validation for expected columns
2. Add error handling for malformed data
3. Add logging for data quality metrics
4. Add option to load specific TEGs only

---

## Section Summary

**Section Statistics:**
- Total Functions: 6
- Total Lines: ~150 lines of code
- Complexity: Mostly Medium, 2 Complex
- Pure Functions: 2 (`check_hc_strokes_combinations`, `reshape_round_data`)
- Mixed Functions: 4 (`add_cumulative_scores`, `add_rankings_and_gaps`, `save_to_parquet`, `load_and_prepare_handicap_data`)

**Key Architectural Points:**

1. **Transformation Pipeline:**
   ```
   Raw Data
       ↓
   add_cumulative_scores()
       ↓
   add_rankings_and_gaps()
       ↓
   Analysis-Ready Data
   ```

2. **Handicap Integration:**
   ```
   Handicap CSV
       ↓
   load_and_prepare_handicap_data()
       ↓
   Merge with process_round_for_all_scores()
   ```

3. **Data Format Conversion:**
   ```
   Wide Format (spreadsheet)
       ↓
   reshape_round_data()
       ↓
   Long Format (database)
   ```

**Critical Dependencies:**
- These transformations form the core of data processing
- Called by `update_all_data()` in sequence
- Must maintain data integrity (no row loss)

**Performance Profile:**
- Most operations: O(n) vectorized
- Ranking: O(n log n) due to sorting
- Total time: <500ms for typical dataset

**Data Flow Integration:**
- Follows directly after `process_round_for_all_scores()` from Section 4A
- Prepares data for analysis functions (Section 7)
- Supports ranking/leaderboard generation

**Recommended Improvements:**
1. Add comprehensive data validation
2. Add progress logging for long operations
3. Add intermediate result caching
4. Parameterize time periods and methods
5. Add unit tests for all calculations

---

