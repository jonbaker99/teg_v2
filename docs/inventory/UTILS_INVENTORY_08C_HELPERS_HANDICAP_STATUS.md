# Utils.py Inventory - Section 8C: Helper Functions - Handicap & Status Management

**Section:** Helper Functions - Handicap Calculations & TEG Status
**Function Count:** 9 functions
**Lines in utils.py:** 3693-3895
**Estimated Complexity:** Medium to Complex

---

## Functions

### 1. `get_hc(TEG_needed: int = None) -> pd.DataFrame` (Lines 3693-3753)
**Calculates handicaps** for upcoming TEG using weighted average of previous two TEGs.
- **Parameters:** TEG_needed (defaults to next after current)
- **Returns:** DataFrame with [Pl, hc_raw, hc]
- **Algorithm:**
  - Uses Stableford scores from previous 2 TEGs
  - Calculates average stableford per round
  - Adjusts gross via stableford formula
  - Weights: 75% most recent, 25% before that
  - Rounds to nearest integer
- **Used By:** Handicap calculation pages

### 2. `get_next_teg_and_check_if_in_progress()` (Lines 3756-3770)
**DEPRECATED.** Gets TEG completion status using slow method.
- **Returns:** (last_completed_teg, next_teg, in_progress)
- **Note:** Use get_next_teg_and_check_if_in_progress_fast() instead

### 3. `get_current_handicaps_formatted(last_completed_teg, next_teg) -> Tuple[pd.DataFrame, bool]` (Lines 3772-3823)
**Formats handicaps** for display showing current and previous with change.
- **Parameters:** Complete and next TEG numbers
- **Returns:** (DataFrame with formatted results, handicaps_were_calculated)
- **Features:**
  - Loads/calculates handicaps as needed
  - Shows HC changes from previous
  - Converts initials to full names
  - Perfect format for display tables
- **Used By:** Handicap display pages

### 4. `analyze_teg_completion(all_data: pd.DataFrame) -> pd.DataFrame` (Lines 3830-3873)
Analyzes completion status of each TEG.
- **Returns:** DataFrame with [TEGNum, TEG, Year, Status, Rounds]
- **Status:** "complete" or "in_progress"
- **Used By:** TEG status tracking

### 5. `save_teg_status_file(status_data: pd.DataFrame, filename: str, defer_github: bool = False)` (Lines 3876-3895)
Saves TEG status CSV to file with optional GitHub deferral.
- **Parameters:**
  - status_data: Status DataFrame
  - filename: Output file name
  - defer_github: Defer GitHub push for batch
- **Used By:** Status file management

### 6-9. Fast TEG Status Functions (Lines 3898-4020)
High-performance status checking using status files instead of full data loads.

**`update_teg_status_files(defer_github=False)`** (Lines 3898-3940)
Updates completed and in-progress TEG status files after data changes.
- **Returns:** file_infos if deferred, else None
- **Workflow:**
  1. Load all data
  2. Analyze completion
  3. Split into completed/in-progress
  4. Save both status files
- **Used By:** Data update pipeline

**`get_next_teg_and_check_if_in_progress_fast()`** (Lines 3943-3963)
Fast version reading from status files.
- **Returns:** (last_completed_teg, next_teg, in_progress)
- **Performance:** ~10ms (vs ~2 seconds for slow method)
- **Fallback:** Reverts to slow method if files missing

**`get_last_completed_teg_fast()`** (Lines 3966-3983)
Gets highest completed TEG number with round count.
- **Returns:** (teg_num, rounds) or (None, 0) if none
- **Performance:** ~10ms file read

**`get_current_in_progress_teg_fast()`** (Lines 3986-4004)
Gets current in-progress TEG number with round count.
- **Returns:** (teg_num, rounds) or (None, 0) if none

**`has_incomplete_teg_fast()`** (Lines 4007-4020)
Boolean check if any TEGs in progress.
- **Returns:** True if in_progress_tegs.csv has data
- **Used By:** Leaderboard headers, status indicators

---

## Section Summary

**Statistics:**
- Total Functions: 9
- Total Lines: ~205 lines
- Type Breakdown: 4 PURE + 5 MIXED/IO
- Complexity: Mostly Medium, 2 Complex

**Key Architectural Points:**

1. **Handicap Calculations:**
   - `get_hc()`: Weighted average from 2 previous TEGs
   - 75/25 weighting favors recent performance
   - Converts stableford scores back to gross

2. **Status Management:**
   - Old method: Load all data, determine status
   - New method: Read lightweight status CSV files
   - ~200x performance improvement with caching

3. **Performance Optimization:**
   - Status files enable fast checks
   - Fallback ensures robustness
   - Used everywhere for TEG tracking

**Performance Comparison:**

| Operation | Slow Method | Fast Method |
|-----------|---|---|
| get_next_teg() | ~2s | ~10ms |
| Load all data | Required | Not needed |
| File I/O | GitHub | Local |
| Reliability | Always works | Falls back |

---

