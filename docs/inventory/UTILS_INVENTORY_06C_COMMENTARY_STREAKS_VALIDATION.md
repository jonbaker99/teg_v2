# Utils.py Inventory - Section 6C: Commentary - Streaks & Validation

**Section:** Commentary Generation - Streaks & Data Validation
**Function Count:** 3 functions
**Lines in utils.py:** 2404-2689
**Estimated Complexity:** Medium to Complex

---

## Functions

### 1. `create_round_streaks_summary(all_data_df: pd.DataFrame = None, streaks_df: pd.DataFrame = None) -> pd.DataFrame`

**Line Numbers:** 2404-2516 (113 lines)
**Function Type:** MIXED
**Complexity:** Medium

**Purpose:**
Creates round-level streaks summary by applying streak window calculations to each (TEG, Round) combination. Shows maximum streak lengths by type for each round.

**Output Columns:**
- TEG, TEGNum, Round, Player, Pl, Streak_Type, Max_Streak, Location

**Streak Types (10 total):**
1. Eagles
2. Birdies
3. Pars or Better
4. No +2s (no double bogeys)
5. No TBPs (no triple+ bogeys)
6. No Eagles
7. No Birdies
8. Over Par
9. +2s or Worse
10. TBPs (triple+ bogeys)

**Used By:**
- Commentary analysis
- Saved to: `data/commentary_round_streaks.parquet`

**Performance:**
- Input: ~1-2K round records
- Output: ~10-20K streak records (multiple streak types per round)
- Time: 2-5 seconds

---

### 2. `create_tournament_streaks_summary(all_data_df: pd.DataFrame = None, streaks_df: pd.DataFrame = None) -> pd.DataFrame`

**Line Numbers:** 2519-2627 (109 lines)
**Function Type:** MIXED
**Complexity:** Medium

**Purpose:**
Creates tournament-level streaks summary by aggregating across all rounds in a tournament. Shows longest streaks by type for entire tournament.

**Output Columns:**
- TEG, TEGNum, Player, Pl, Streak_Type, Max_Streak, Location

**Used By:**
- Tournament analysis
- Best streaks identification
- Saved to: `data/commentary_tournament_streaks.parquet`

**Performance:**
- Similar to round streaks but aggregated at tournament level
- Output: ~5-10K records
- Time: 2-5 seconds

---

### 3. `check_for_complete_and_duplicate_data(all_scores_path: str, all_data_path: str) -> Dict[str, pd.DataFrame]`

**Line Numbers:** 2630-2689 (60 lines)
**Function Type:** IO
**Complexity:** Medium

**Purpose:**
**DATA QUALITY VALIDATION.** Checks both all-scores (CSV) and all-data (Parquet) files for:
- Incomplete rounds (fewer than 18 holes)
- Duplicate rounds (more than 18 holes)
- Data consistency between files

**Parameters:**
- `all_scores_path` (str): Path to all-scores CSV
- `all_data_path` (str): Path to all-data Parquet

**Returns:**
- `Dict[str, pd.DataFrame]`:
  - 'incomplete_scores': Incomplete rounds in CSV
  - 'duplicate_scores': Duplicate rounds in CSV
  - 'incomplete_data': Incomplete rounds in Parquet
  - 'duplicate_data': Duplicate rounds in Parquet

**Used By:**
- Data validation scripts
- QA/testing
- Data import verification

**Technical Notes:**
- Groups by [TEGNum, Round, Pl]
- Counts entries (should be 18 for complete round)
- Filters for <18 (incomplete) or >18 (duplicate)
- Logs warnings for issues found

---

## Section Summary

**Statistics:**
- Total Functions: 3
- Total Lines: ~280 lines of code
- Complexity: Mostly Medium
- Type: 1 IO, 2 MIXED

**Key Points:**
- Streak functions build on streak calculations from Section 5
- Validation function checks data integrity
- All three functions are critical for data quality
- Generate cacheable parquet files

**Output Files:**
- `data/commentary_round_streaks.parquet`
- `data/commentary_tournament_streaks.parquet`
- (Validation returns dict, no file output)

---

