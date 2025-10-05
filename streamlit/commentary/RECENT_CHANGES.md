# Recent Changes to Commentary Generation Pipeline

**Date:** 2025-01-06

## Summary

Enhanced the tournament commentary generation pipeline with optimizations for token usage and improved historical context. Changes focus on separating factual data (direct addition) from synthesized patterns (LLM processing).

---

## 1. Token Optimization: Direct Addition of Factual Sections

**Problem:** Passing factual data (venue info, records, course records) to LLM wastes tokens on information that needs no synthesis.

**Solution:** Restructured to add factual sections directly to story notes AFTER LLM generation.

### Changes Made:

**Files Modified:**
- `streamlit/commentary/generate_tournament_commentary_v2.py`
- `streamlit/commentary/prompts.py`

**New Functions in generate_tournament_commentary_v2.py:**
- `format_venue_section(teg_num)` - Formats venue context as markdown
- `format_records_and_pbs_section(all_processed_data, teg_num)` - Formats records/PBs by round
- `append_factual_sections(story_notes, teg_num, all_processed_data)` - Inserts factual data after LLM generation
- Updated `build_story_notes_file()` to call `append_factual_sections()`

**Removed from LLM Prompts:**
- Venue context parameter from `TOURNAMENT_SYNTHESIS_PROMPT`
- Records/PBs parameters from `ROUND_STORY_PROMPT`
- Course records parameters from `ROUND_STORY_PROMPT`

**What's Now Added Directly (NOT passed to LLM):**
1. **Venue Context** (tournament-level):
   - Area name and year
   - Return context (e.g., "9-year gap since TEG 4")
   - Course history (which courses, previous TEGs played)

2. **Records & Personal Bests** (per round):
   - All-time TEG records
   - Personal bests/worsts
   - Rankings with context (e.g., "3 of 61")

3. **Course Records** (per round):
   - Course name, record holder, score
   - Whether set/tied this round
   - Only courses played >2 times, gross only

**Token Savings:** ~2500-4500 tokens per 4-round tournament

---

## 2. Career Context Enhancement

**Problem:** LLM lacked historical context about players' career trajectories and recent form.

**Solution:** Added pre-tournament career context to tournament synthesis.

### Changes Made:

**New Function in generate_tournament_commentary_v2.py:**
```python
def build_career_context(teg_num, players_in_teg):
    """
    Build career context for players BEFORE this tournament.

    IMPORTANT: Only includes data from TEGs BEFORE this one (TEGNum < teg_num).
    """
```

**Data Included:**
- **Recent finishes**: Last 3-5 TEG positions in reverse chronological order
  - Example: "TEG 16: 2nd, TEG 15: 4th, TEG 14: DNC, TEG 13: 1st"
- **Career position counts**: Count of each finishing position
  - Example: "1st: 3, 2nd: 5, 3rd: 2, 4th: 1, 5th: 4"
- **Debut flag**: Identifies first-time players

**Critical Design Decision:**
- All data filtered to `TEGNum < teg_num` to ensure no "future" information leaks
- Clearly labeled as "PRE-TOURNAMENT Career Context" in prompt
- LLM can infer total TEGs played from position count sum

**Updated Prompts:**
- Added `{career_context}` parameter to `TOURNAMENT_SYNTHESIS_PROMPT`
- Labeled as "Career Context (PRE-TOURNAMENT)"

---

## 3. Feature Toggle: INCLUDE_STREAKS

**Problem:** Need ability to test whether streak data (Birdies, Eagles, +2s or Worse) adds value to story generation.

**Solution:** Added feature toggle in config.

**New Config Variable in generate_tournament_commentary_v2.py:**
```python
# Feature toggles
INCLUDE_STREAKS = True  # Include streak data in round story generation
                        # Set to False to exclude if it doesn't add value
```

**Status:**
- Toggle created and documented
- Streak data integration NOT YET IMPLEMENTED
- Ready for implementation when needed

---

## 4. Commentary Data Files Usage Analysis

**Question:** Which commentary parquet files are actually used?

**Answer:**

### ✅ USED:
1. **`commentary_round_events.parquet`** - YES (Pass 5)
   - Eagles, disasters, significant moments
   - Passed to LLM in round data

2. **`commentary_round_summary.parquet`** - YES (Passes 5 & 7)
   - Round-level player stats
   - Used for records/PBs identification

3. **`commentary_tournament_summary.parquet`** - YES (Synthesis)
   - Tournament totals, final ranks
   - Used for career context and historical win counts

### ❌ NOT USED:
4. **`commentary_round_streaks.parquet`** - NO
   - Contains: Birdies, Eagles, +2s or Worse streaks by round
   - Ready to integrate via INCLUDE_STREAKS toggle

5. **`commentary_tournament_streaks.parquet`** - NO
   - Tournament-level streaks
   - Not currently integrated

---

## Data Flow Diagram (Updated)

```
LEVEL 1: Data Processing (Python - 7 passes)
├── Pass 1-4: Pattern analysis (lead, momentum, nine-patterns, details)
├── Pass 5-6: Load commentary files (events, summary)
└── Pass 7: Identify records/PBs from ranking data

LEVEL 2: Story Generation (LLM)
├── Round Stories (4 passes)
│   └── Input: 5 data types (lead, momentum, nine, events, summary)
│       Note: Records/PBs/streaks NOT passed - added directly
└── Tournament Synthesis (1 pass)
    └── Input: Round stories + tournament data + historical wins + career context
        Note: Venue context NOT passed - added directly

LEVEL 2.5: Direct Addition (Python)
├── Venue context → Inserted after synthesis
├── Records/PBs → Appended to each round
└── Course records → Appended to each round

OUTPUT: story_notes.md with LLM-synthesized + directly-added sections
```

---

## Testing Notes

**To Test Career Context:**
- Generate story notes for any TEG with players who have history
- Check synthesis section for career context usage
- Verify no "future" data appears (TEGNum >= current)

**To Test Token Savings:**
- Compare prompt sizes before/after in debug output
- Should see ~500-1000 token reduction per round
- Should see ~300-500 token reduction in synthesis

**To Enable Streak Data:**
- Set `INCLUDE_STREAKS = True` in generate_tournament_commentary_v2.py
- Complete remaining implementation (see IMPLEMENTATION_PLAN_FINAL.md)

---

## Files Modified

1. `streamlit/commentary/generate_tournament_commentary_v2.py`
   - Added factual section formatting functions
   - Added career context building function
   - Updated `build_story_notes_file()` signature and implementation
   - Added INCLUDE_STREAKS config toggle

2. `streamlit/commentary/prompts.py`
   - Removed venue context from TOURNAMENT_SYNTHESIS_PROMPT
   - Removed records/PBs from ROUND_STORY_PROMPT
   - Added career context parameter to TOURNAMENT_SYNTHESIS_PROMPT
   - Updated documentation in prompts

3. `streamlit/commentary/IMPLEMENTATION_PLAN_FINAL.md`
   - Updated status to "COMPLETE AND ENHANCED"
   - Added Pass 7 and Pass 8 (optional) to architecture
   - Listed new features

4. `streamlit/commentary/RECENT_CHANGES.md` (NEW)
   - This file - comprehensive changelog

---

## Next Steps (Optional Enhancements)

1. **Complete Streak Data Integration** (if INCLUDE_STREAKS proves valuable):
   - Implement Pass 8 in pattern_analysis.py
   - Add to data_loader.py
   - Update prompts.py with streak documentation
   - Pass through generate_round_story()

2. **Test Career Context Impact**:
   - Generate reports with career context
   - Evaluate if LLM uses it effectively
   - Adjust recent finish count (currently 3-5) if needed

3. **Consider Additional Historical Context**:
   - Head-to-head records between players?
   - Course-specific player history?
   - Recent form trends?

---

## Backward Compatibility

**Breaking Changes:** None - existing story note files remain compatible

**Required Updates:** None - pipeline works with existing data files

**Config Changes:** New INCLUDE_STREAKS toggle (default: True, but not yet used)
