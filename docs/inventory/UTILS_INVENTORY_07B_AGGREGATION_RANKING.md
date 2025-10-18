# Utils.py Inventory - Section 7B: Data Aggregation - Ranking & Best/Worst

**Section:** Ranking & Player Comparison Functions
**Function Count:** 10 functions
**Lines in utils.py:** 2928-3101
**Estimated Complexity:** Simple to Medium

---

## Functions

### 1-2. `get_Pl_data()` & `list_fields_by_aggregation_level(df)` (Lines 2928-2959)
- **get_Pl_data():** Player-level cached aggregation
- **list_fields_by_aggregation_level():** Utility identifying unique fields at each aggregation level
- **Type:** PURE/MIXED | **Complexity:** Simple

### 3. `add_ranks(df: pd.DataFrame, fields_to_rank: List[str] = None, rank_ascending: bool = None) -> pd.DataFrame` (Lines 2962-3026)
**Adds ranking columns** for specified fields within players and across all players.
- **Parameters:**
  - fields_to_rank: Which measures to rank (default: Sc, GrossVP, NetVP, Stableford)
  - rank_ascending: Direction (True=lower better, False=higher better)
- **Output Columns:** Rank_within_player_{field}, Rank_within_all_{field}
- **Features:**
  - Defaults: Stableford descending, others ascending
  - Handles NaN gracefully
  - Fast vectorized ranking
- **Used By:** All analysis pages

### 4-6. `get_ranked_teg_data()`, `get_ranked_round_data()`, `get_ranked_frontback_data()` (Lines 3029-3044)
Cached convenience functions combining aggregation + ranking.
- **Type:** MIXED | **Complexity:** Simple
- **Used By:** Specific analysis pages

### 7. `get_best(df: pd.DataFrame, measure_to_use: str, player_level: bool = False, top_n: int = 1) -> pd.DataFrame` (Lines 3046-3060)
Filters for top-N best performances by measure.
- **Parameters:**
  - measure_to_use: Which score (Sc, GrossVP, NetVP, Stableford)
  - player_level: Best within player vs best overall
  - top_n: How many top results (default 1)
- **Logic:** Filters by ranking column <= top_n
- **Used By:** Best scores/performances

### 8. `get_worst(df: pd.DataFrame, measure_to_use: str, player_level: bool = False, top_n: int = 1) -> pd.DataFrame` (Lines 3062-3086)
Filters for worst performances.
- **Parameters:** Same as get_best
- **Logic:** Uses nsmallest/nlargest depending on measure (Stableford lower=worse)
- **Used By:** Worst scores analysis

### 9. `ordinal(n: int) -> str` (Lines 3088-3093)
Converts integer to ordinal string: 1→"1st", 2→"2nd", 11→"11th".
- **Type:** PURE | **Complexity:** Simple
- **Used By:** Display formatting

### 10. `safe_ordinal(n: float) -> str` (Lines 3095-3101)
Safe wrapper around ordinal handling NaN values.
- **Type:** PURE | **Complexity:** Simple
- **Used By:** Formatting with potential missing data

---

## Supporting Functions (Not Listed Above)

### `chosen_rd_context()` & `chosen_teg_context()` (in Section 8A)
Context builders for specific round/TEG performance displays.

---

## Section Summary

**Statistics:**
- Total Functions: 10
- Total Lines: ~140 lines
- Type Breakdown: 3 PURE + 7 MIXED
- Complexity: Mostly Simple, 1 Medium

**Key Functions:**
- `add_ranks()`: Core ranking algorithm (vectorized)
- `get_best()`/`get_worst()`: Filtering utilities
- Ordinal functions: Display formatting

**Used By Extent:**
- `add_ranks()`: Used by 30+ pages
- Best/worst: Common analysis patterns
- Ranking: Foundation for all comparisons

---

