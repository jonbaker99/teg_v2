# Utils.py Inventory - Section 6A: Commentary Functions - Round Summary

**Section:** Commentary Generation - Round Summary
**Function Count:** 1 VERY LARGE function
**Lines in utils.py:** 1532-1855 (324 lines!)
**Estimated Complexity:** Very Complex

---

## Overview

This section documents `create_round_summary()` - one of the most comprehensive and complex functions in the entire codebase. This single function generates a massive summary table containing 50+ calculated metrics for every player's round.

---

## Function

### `create_round_summary(all_data_df: pd.DataFrame = None, round_info_df: pd.DataFrame = None) -> pd.DataFrame`

**Line Numbers:** 1532-1855 (324 lines!)
**Function Type:** MIXED
**Complexity:** VERY COMPLEX

**Purpose:**
**COMPREHENSIVE ROUND ANALYSIS ENGINE.** Creates a detailed summary table for each unique (TEG, Round, Player) combination. Calculates 50+ metrics including:

- Round scores (Sc, Gross, Stableford) by 9-hole sections
- Cumulative tournament scores at round end
- Tournament rankings before and after the round
- Lead tracking (holes in lead, lead gained/lost counts)
- Score type distributions (eagles, birdies, pars, etc.)
- Historical context (how this round ranks in player's history)

**Full Signature:**
```python
def create_round_summary(
    all_data_df: pd.DataFrame = None,
    round_info_df: pd.DataFrame = None
) -> pd.DataFrame:
    """Create a comprehensive summary table for each round (TEG + Round + Player).

    Calculates and captures metrics for each round including scores, rankings,
    lead tracking, and historical context.

    Args:
        all_data_df (optional): DataFrame from all-data.parquet
        round_info_df (optional): DataFrame from round_info.csv

    Returns:
        pd.DataFrame: One row per player per round with 50+ columns
    """
```

**Parameters:**
- `all_data_df` (pd.DataFrame, optional): Hole-by-hole data. Auto-loads if None
- `round_info_df` (pd.DataFrame, optional): Round metadata. Auto-loads if None

**Returns:**
- `pd.DataFrame`: Summary with columns for all calculated metrics

**Output Columns (60+ total):**

**Basic Info:**
- TEG, TEGNum, Round, Date, Course, Area, Year, Player, Pl

**Round Scores (Actual Score - Par):**
- Round_Score_Sc, Front_9_Score_Sc, Back_9_Score_Sc, Front_9_vs_Back_9_Sc

**Round Scores (Gross/vs Par):**
- Round_Score_Gross, Front_9_Score_Gross, Back_9_Score_Gross, Front_9_vs_Back_9_Gross

**Round Scores (Stableford):**
- Round_Score_Stableford, Front_9_Score_Stableford, Back_9_Score_Stableford, Front_9_vs_Back_9_Stableford

**Cumulative Tournament Scores (at end of round):**
- Cumulative_Tournament_Score_Gross
- Cumulative_Tournament_Score_Stableford

**Cumulative Tournament Rankings (at end of round):**
- Cumulative_Tournament_Rank_Gross
- Cumulative_Tournament_Rank_Stableford

**Rankings at Start of Round (from previous round):**
- Cumulative_Tournament_Rank_Before_Round_Gross
- Cumulative_Tournament_Rank_Before_Round_Stableford

**Gaps to Leader:**
- Gap_To_Leader_Before_Round_Gross
- Gap_To_Leader_After_Round_Gross
- Gap_To_Leader_Before_Round_Stableford
- Gap_To_Leader_After_Round_Stableford

**Lead Tracking:**
- Holes_In_Lead_Gross, Holes_In_Lead_Stableford
- Leading_At_Start_Of_Round_Gross, Leading_At_Start_Of_Round_Stableford
- Leading_At_End_Of_Round_Gross, Leading_At_End_Of_Round_Stableford
- Lead_Gained_Count_Gross, Lead_Lost_Count_Gross
- Lead_Gained_Count_Stableford, Lead_Lost_Count_Stableford

**Historical Rankings:**
- Round_Rank_In_Player_History_Gross (e.g., "5 of 72")
- Round_Rank_In_Player_History_Stableford
- Round_Rank_In_All_History_Gross
- Round_Rank_In_All_History_Stableford
- Total_Player_Rounds_To_Date
- Total_Rounds_To_Date

**Score Type Counts:**
- Eagles_Count, Birdies_Count, Pars_Or_Better_Count, Triple_Bogeys_Or_Worse_Count
- Zero_Stableford_Points_Count, Four_Plus_Stableford_Points_Count, Five_Plus_Stableford_Points_Count

**Support Fields:**
- Total_Player_Rounds_To_Date, Total_Rounds_To_Date

**Example Row:**
```
TEG='TEG 16', Round=2, Player='Jon BAKER', Pl='JB'
Round_Score_Gross=+4, Front_9=+2, Back_9=+2
Rank_Gross=2, Gap_To_Leader=3 strokes
Holes_In_Lead=8, Leading_At_End=True
Round_Rank_In_History="5 of 48" (5th best round in this player's career)
Eagles=1, Birdies=3, Pars=10
```

**Dependencies:**
- **External Packages:** pandas, numpy
- **Internal Functions:**
  - `load_all_data()` (if all_data_df not provided)
  - `read_file()` (for round_info if not provided)
  - `create_round_events()` - For lead change calculations
- **Streamlit-Specific:** No (but calls logging)
- **File I/O:** Yes (reads if params not provided)

**Workflow (9 Major Steps):**

**Step 1: Load Data (Lines 1555-1565)**
- Load all-data and round_info
- Ensure sorted by [TEGNum, Round]

**Step 2: Calculate Round Scores (Lines 1574-1606)**
- Group by [TEGNum, Round, Pl]
- Sum Sc, GrossVP, Stableford by round
- Split Front 9 (holes 1-9) vs Back 9 (holes 10-18)
- Calculate difference (Front - Back)

**Step 3: Extract Cumulative Scores at Round End (Lines 1614-1629)**
- Get data at hole 18 of each round
- Extract: GrossVP_Cum_TEG, Stableford_Cum_TEG
- Extract: Rank_GrossVP_TEG, Rank_Stableford_TEG
- Extract: Gap_GrossVP_TEG, Gap_Stableford_TEG

**Step 4: Calculate Round Rankings (Lines 1634-1644)**
- Rank within each round (Gross ascending, Stableford descending)
- Extract "before round" ranks using shift(1) within each player/TEG

**Step 5: Calculate Lead Tracking (Lines 1653-1797)**
- Count holes where player was in lead (rank==1)
- Flag if leading at round start/end
- Count lead gains/losses using `create_round_events()`

**Step 6: Calculate Historical Rankings (Lines 1672-1727)**
- For each round, rank it against player's previous rounds
- For each round, rank it against all rounds to date
- Format as "X of Y" strings

**Step 7: Calculate Score Type Counts (Lines 1734-1755)**
- Count eagles, birdies, pars, triple bogeys
- Count stableford distribution

**Step 8: Merge All Components (Lines 1788-1851)**
- Merge all calculated dataframes
- Reorder columns for clarity
- Ensure consistent sorting

**Step 9: Return (Line 1855)**
- Output sorted by TEG, Round, Player

**Performance Characteristics:**
- Input: ~50,000-100,000 hole records
- Output: ~500-1,000 round summary rows
- Execution time: 10-30 seconds (due to historical ranking loop)

**Key Implementation Details:**

1. **Historical Rankings Loop (Lines 1693-1727):**
   - Iterates through EACH row
   - For each row, filters historical data up to that date
   - Calculates rank against player's history
   - Performance bottleneck (O(n²) worst case)

2. **Lead Change Calculation:**
   - Calls `create_round_events()` internally
   - Very expensive operation (full event generation)
   - Could be optimized with memoization

3. **Merges:**
   - Multiple left merges preserve all rows
   - Handles missing round_info gracefully
   - NaN filling for missing data

**Data Quality Notes:**
- Handles incomplete rounds gracefully
- Missing players result in NaN values
- Robust to missing Area/Course data

**Used By:**
- Commentary generation system
- Analysis functions needing round-level metrics
- Saved to: `data/commentary_round_summary.parquet`

**Caching:**
- Results typically cached by `update_commentary_caches()`
- Not directly cached (left to caller)

**Error Handling:**
- FileNotFoundError → st.error() and early return
- Merge conflicts → Handled with left joins
- Missing columns → Logged and continues

**Optimization Opportunities:**
1. **Remove historical rankings loop** - Major performance bottleneck
   - Currently O(n²) for n rounds
   - Could pre-compute with vectorized ops
   - Potential 10-20x speedup

2. **Cache event generation** - Don't regenerate events for every call

3. **Vectorize date comparisons** - Currently per-row iteration

4. **Add incremental calculation** - Only recalculate new rounds

5. **Add parallel processing** - Calculate metrics independently

**Migration Recommendation:**
- **Target Module:** Move to `teg_analysis/commentary/` module
- **Rationale:** Pure analysis function with no Streamlit dependency; very specialized
- **Priority:** HIGH - Core commentary engine
- **Breaking Changes:** None (already standalone)

**Testing Considerations:**
- Validate cumulative score calculations
- Verify ranking algorithms (ties)
- Test historical ranking logic with various dates
- Validate edge cases (first round, only player, etc.)

---

## Critical Notes

This is one of the most important and complex functions in the application. It:
- Generates 60+ calculated columns from raw data
- Orchestrates multiple calculation functions
- Uses expensive O(n²) historical ranking algorithm
- Takes 10-30 seconds per full execution

**Recommended Action:** This function would benefit from significant optimization and refactoring, but is currently a critical part of the commentary generation system.

---

