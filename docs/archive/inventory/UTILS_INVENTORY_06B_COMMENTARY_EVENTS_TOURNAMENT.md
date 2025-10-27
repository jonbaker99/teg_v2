# Utils.py Inventory - Section 6B: Commentary Functions - Events & Tournament

**Section:** Commentary Generation - Events & Tournament Summary
**Function Count:** 2 VERY LARGE functions
**Lines in utils.py:** 1858-2401
**Estimated Complexity:** Very Complex

---

## Overview

This section documents two massive functions:
1. `create_round_events()` - 258 lines tracking key moments hole-by-hole
2. `create_tournament_summary()` - 284 lines aggregating tournament-wide metrics

---

## Function 1: `create_round_events(all_data_df: pd.DataFrame = None) -> pd.DataFrame`

**Line Numbers:** 1858-2115 (258 lines!)
**Function Type:** MIXED
**Complexity:** VERY COMPLEX

**Purpose:**
**EVENT LOG GENERATOR.** Creates comprehensive event log capturing:
- **Position changes:** Taking/losing lead, hitting/leaving bottom
- **Hole outcomes:** Eagles, birdies, triple bogeys, special scores
- **Stableford achievements:** High/low point holes
- **Ranking transitions:** Before/after rank at each hole

One row per event (can have multiple per hole for same player).

**Output Columns:**
- TEG, TEGNum, Round, Hole, Player, Pl
- Par, Sc, GrossVP, Stableford
- Final_Hole_Flag (boolean for hole 18)
- Event (text description)
- Metric (score value if applicable)
- Rank_Gross_Before, Rank_Gross_After
- Rank_Stableford_Before, Rank_Stableford_After

**Event Types (14 total):**

Position Events:
- "Took Lead (Gross)" - Moved to rank 1 in gross
- "Lost Lead (Gross)" - Dropped from rank 1
- "Took Lead (Stableford)" - Moved to rank 1 in stableford
- "Lost Lead (Stableford)" - Dropped from rank 1
- "Hit Bottom (Spoon)" - Moved to last place (wooden spoon)
- "Left Bottom (Spoon)" - Moved up from last place

Hole Outcome Events:
- "Hole in One" (Sc == 1)
- "Eagle" (GrossVP == -2)
- "Birdie" (GrossVP == -1)
- "Triple Bogey or Worse" (GrossVP >= 3)
- "Quintuple Bogey or Worse" (GrossVP >= 5)
- "Zero Points" (Stableford == 0)
- "4+ Points" (Stableford >= 4)
- "5+ Points" (Stableford >= 5)

**Workflow (8 Major Steps):**

1. **Load Data** - all-data.parquet with rankings
2. **Validate Columns** - Ensure required ranking columns exist
3. **Calculate Derived Fields:**
   - TEG_Hole (hole number bridging rounds)
   - NPlayers per round
   - Rank_Spoon_TEG (inverse of stableford rank)
4. **Calculate Rank "Before" Fields** - Shift rankings by 1 hole
5. **Detect Position Events** - Vectorized boolean masks for rank changes
6. **Detect Hole Outcome Events** - Score-based event detection
7. **Add Metric Column** - Map events to relevant score values
8. **Format & Return** - Sorted by TEG, Round, Hole, Event

**Performance:**
- Input: ~50,000-100,000 hole records
- Output: ~5,000-20,000 event records
- Execution time: 5-15 seconds

**Used By:**
- Lead change calculations in `create_round_summary()`
- Commentary analysis functions
- Saved to: `data/commentary_round_events.parquet`

**Key Implementation:**
- Uses vectorized boolean operations for position detection
- Base64-encoded flags for memory efficiency
- Reshape to tidy (melted) format for events

---

## Function 2: `create_tournament_summary(all_data_df: pd.DataFrame = None, round_info_df: pd.DataFrame = None) -> pd.DataFrame`

**Line Numbers:** 2118-2401 (284 lines!)
**Function Type:** MIXED
**Complexity:** VERY COMPLEX

**Purpose:**
**TOURNAMENT AGGREGATION ENGINE.** Creates summary for each (TEG, Player) combination. Aggregates from round-level data to tournament-level, calculating 40+ metrics including:

- Final scores and rankings (both gross and stableford)
- Performance consistency metrics (best/worst/range/std dev)
- Lead tracking across all rounds (total holes, rounds leading)
- Total scoring achievements (eagles, birdies, holes in one, etc.)
- Historical context (how this TEG ranks for this player)

**Output Columns (50+ total):**

**Basic Info:**
- TEGNum, Player, Pl, TEG, Year

**Tournament Scores:**
- Tournament_Score_Sc, Tournament_Score_Gross, Tournament_Score_Stableford

**Scores Rankings:**
- Final_Rank_Gross, Final_Rank_Stableford
- Final_Gap_Gross, Final_Gap_Stableford
- Margin_Gross, Margin_Stableford

**Outcomes:**
- Won_Gross (boolean), Won_Stableford (boolean)
- Wooden_Spoon (boolean - last in stableford)

**Performance Consistency:**
- Best_Round_Gross, Worst_Round_Gross, Range_Round_Gross
- Best_Round_Stableford, Worst_Round_Stableford, Range_Round_Stableford
- StdDev_Round_Gross, StdDev_Round_Stableford
- StdDev_Hole_Gross, StdDev_Hole_Stableford

**Lead Tracking:**
- Total_Holes_In_Lead_Gross, Total_Holes_In_Lead_Stableford
- Rounds_Leading_After_Gross, Rounds_Leading_After_Stableford
- Total_Lead_Gained_Gross, Total_Lead_Lost_Gross
- Total_Lead_Gained_Stableford, Total_Lead_Lost_Stableford

**Scoring Achievements:**
- Total_Eagles, Total_Birdies, Total_Pars, Total_Bogeys
- Total_Double_Bogeys, Total_Worse_Than_Double
- Holes_In_One
- Total_Stableford_5s, Total_Stableford_0s

**Historical Context:**
- Rank_Among_Player_TEGs_Gross (e.g., "3rd best TEG for this player")
- Rank_Among_Player_TEGs_Stableford
- Rank_Among_All_TEGs_To_Date_Gross
- Rank_Among_All_TEGs_To_Date_Stableford

**Example Row:**
```
TEG=16, Player='Jon BAKER', Pl='JB'
Tournament_Score_Gross=+12, Final_Rank=2, Won_Gross=False
Best_Round=-2, Worst_Round=+5, StdDev=2.3
Total_Holes_In_Lead=54, Rounds_Leading=3
Total_Eagles=2, Total_Birdies=8
Rank_Among_Player_TEGs="5 of 16" (5th best tournament for JB)
```

**Workflow (9 Major Steps):**

1. **Load Data** - all-data, round summaries, round_info
2. **Get Basic Info** - TEG, Year, Player per tournament
3. **Calculate Scores & Rankings:**
   - Sum round scores to get tournament totals
   - Rank within tournament (Gross ascending, Stableford descending)
   - Calculate gaps to winner
   - Determine win/loss/wooden spoon
4. **Calculate Consistency:**
   - Best/worst round performance
   - Range (spread)
   - Standard deviation by round
   - Standard deviation by hole
5. **Calculate Lead Tracking:**
   - Sum across all rounds
   - Total holes in lead
   - Rounds leading after
6. **Calculate Scoring Achievements:**
   - Count eagles, birdies, holes in one
   - Count stableford extremes
7. **Calculate Historical Rankings:**
   - For each TEG, rank against player's previous TEGs
   - Rank against all TEGs (chronologically)
8. **Merge All Components:**
   - Combine all calculations
   - Reorder columns
9. **Return Sorted** - By TEGNum

**Performance:**
- Input: ~1,000-2,000 round summary rows (from round_summary)
- Output: ~500-1,000 tournament rows (varies by TEGs)
- Execution time: 5-10 seconds

**Used By:**
- Commentary analysis
- Tournament analysis pages
- Historical comparisons
- Saved to: `data/commentary_tournament_summary.parquet`

**Key Implementation:**
- Aggregates from round-level `create_round_summary()` data
- Uses groupby + agg for performance
- Handles tie rankings with `method='min'`
- Pre-calculates leader scores for gap calculations

---

## Comparison

| Aspect | Round Events | Tournament Summary |
|--------|---|---|
| Granularity | Per hole | Per tournament |
| Rows | 5-20K | 500-1K |
| Columns | 18 | 50+ |
| Time | 5-15s | 5-10s |
| Focus | Moments/events | Overall performance |
| Data Source | Hole-by-hole | Round summaries |

---

## Critical Notes

These two functions are:
- **Massive** - 258 and 284 lines each
- **Complex** - Multi-step algorithms with careful calculations
- **Important** - Core commentary/analysis backbone
- **Slow** - Take 10-25 seconds each to execute

Consider optimization opportunities:
- Vectorization of historical ranking calculations
- Caching intermediate results
- Parallel processing of calculations
- Incremental updates (only new rounds)

---

