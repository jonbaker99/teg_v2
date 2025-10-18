# Utils.py Inventory - Section 7A: Data Aggregation - Core Functions

**Section:** Data Aggregation & Analysis
**Function Count:** 10 functions
**Lines in utils.py:** 2692-2925
**Estimated Complexity:** Simple to Medium

---

## Functions

### 1. `get_teg_rounds(TEG: str) -> int` (Lines 2692-2703)
Returns number of expected rounds for a TEG using TEG_ROUNDS dictionary. Defaults to 4 if not found.
- **Type:** PURE | **Complexity:** Simple
- **Used By:** Data validation, incomplete TEG detection

### 2. `get_tegnum_rounds(TEGNum: int) -> int` (Lines 2705-2716)
Returns number of rounds using integer TEG number instead of string. Wrapper around TEG_ROUNDS dictionary lookup.
- **Type:** PURE | **Complexity:** Simple
- **Used By:** Same as above

### 3. `format_vs_par(value: float) -> str` (Lines 2718-2736)
Formats numeric score value as vs-par display: 0→"=", +5→"+5", -2→"-2".
- **Type:** PURE | **Complexity:** Simple
- **Used By:** All display functions showing vs-par scores

### 4. `get_net_competition_measure(teg_num: int) -> str` (Lines 2739-2761)
Returns scoring measure for net competition based on TEG number:
- TEG 1-7: 'NetVP' (net vs par)
- TEG 8+: 'Stableford' (rule changed)
- **Type:** PURE | **Complexity:** Simple
- **Used By:** Score calculation logic

### 5. `get_teg_winners(df: pd.DataFrame) -> pd.DataFrame` (Lines 2764-2840)
**Generates TEG winners table** showing Green Jacket (Gross), TEG Trophy (Net), and HMM Wooden Spoon for each tournament.
- **Type:** MIXED | **Complexity:** Medium
- **Parameters:** DataFrame with TEGNum, Player, GrossVP, NetVP, Stableford
- **Output Columns:** TEG, Year, TEG Trophy, Green Jacket, HMM Wooden Spoon
- **Features:**
  - Determines best gross player
  - Determines best net (using correct measure for TEG)
  - Determines worst net (wooden spoon)
  - Applies TEG_OVERRIDES for manual corrections
- **Used By:** Honours board, TEG history pages

### 6. `aggregate_data(data: pd.DataFrame, aggregation_level: str, measures: List[str] = None, additional_group_fields: List[str] = None) -> pd.DataFrame` (Lines 2845-2901)
**Generalized aggregation function** supporting multiple aggregation levels with dynamic field selection.
- **Type:** MIXED | **Complexity:** Medium
- **Parameters:**
  - data: Input DataFrame
  - aggregation_level: 'Player'|'TEG'|'Round'|'FrontBack'|'Hole'
  - measures: Fields to aggregate (default: ['Sc', 'GrossVP', 'NetVP', 'Stableford'])
  - additional_group_fields: Extra grouping columns
- **Returns:** Aggregated DataFrame at specified level
- **Hierarchy:** Player→TEG→Round→FrontBack→Hole
- **Used By:** Aggregated data generation functions

### 7. `get_complete_teg_data()` (Lines 2904-2907)
Cached aggregation of complete TEGs only (excludes in-progress).
- **Type:** MIXED | **Complexity:** Simple
- **Decorator:** @st.cache_data (no TTL)
- **Used By:** Display functions showing finished tournaments

### 8. `get_teg_data_inc_in_progress()` (Lines 2910-2913)
Cached aggregation including in-progress TEGs.
- **Type:** MIXED | **Complexity:** Simple
- **Decorator:** @st.cache_data
- **Used By:** Leaderboard, current tournament tracking

### 9. `get_round_data(ex_50=True, ex_incomplete=False)` (Lines 2916-2919)
Cached aggregation at round level with optional filtering.
- **Type:** MIXED | **Complexity:** Simple
- **Parameters:**
  - ex_50: Exclude TEG 50 (default True)
  - ex_incomplete: Exclude incomplete TEGs (default False)
- **Used By:** Round-by-round analysis pages

### 10. `get_9_data()` (Lines 2922-2925)
Cached aggregation by front/back 9.
- **Type:** MIXED | **Complexity:** Simple
- **Used By:** Front 9 vs Back 9 analysis

---

## Section Summary

**Statistics:**
- Total Functions: 10
- Total Lines: ~230 lines
- Type Breakdown: 3 PURE + 7 MIXED
- Complexity: Mostly Simple, 2 Medium

**Key Patterns:**
- First 5 functions: Lookup/formatting/helper utilities
- `get_teg_winners()`: Core aggregation producing key output
- `aggregate_data()`: Generalized aggregation engine
- Functions 7-10: Convenience wrappers with caching

**Caching Strategy:**
- Functions 7-10 use @st.cache_data
- No TTL on any cache
- Manual cache clearing required after data updates

**Used By Extent:**
- Extremely widespread (40+ pages)
- Core aggregation infrastructure
- Foundation for all analysis pages

---

