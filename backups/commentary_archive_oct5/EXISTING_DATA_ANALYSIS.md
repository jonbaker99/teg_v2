# Existing Commentary Data Pipeline Analysis

## 📊 Current Commentary Data Files

When core data changes (rounds added/deleted), these analysis files are automatically generated in `data/`:

### 1. **commentary_tournament_summary.parquet**
**What it contains:**
- Tournament-level aggregates for each player
- Final rankings, gaps to leader, win flags
- Round performance stats (best/worst rounds, std dev)
- **Total holes in lead** (Gross & Stableford) ✅ **ALREADY HAS THIS!**
- **Rounds leading after** (Gross & Stableford) ✅ **ALREADY HAS THIS!**

**Key fields we need:**
- `Total_Holes_In_Lead_Stableford` - Total holes player led in tournament
- `Rounds_Leading_After_Stableford` - How many rounds they led after
- `Final_Rank_Stableford`, `Final_Gap_Stableford` - Final standings
- `Won_Stableford`, `Wooden_Spoon`, `Margin_Stableford` - Competition outcomes

**What's missing:**
- ❌ Lead changes (when, where, to whom)
- ❌ Tight battle periods (margin thresholds)
- ❌ Breakaway moments (when gaps widened significantly)

---

### 2. **commentary_round_summary.parquet** ⭐ **GOLDMINE!**
**What it contains:**
- Round-level performance for each player per round
- **Front 9 vs Back 9 splits** ✅ **ALREADY HAS THIS!**
- **Cumulative tournament context before/after each round** ✅ **ALREADY HAS THIS!**
- **Lead tracking per round** ✅ **ALREADY HAS THIS!**
- **Gaps to leader before/after round** ✅ **ALREADY HAS THIS!**

**Key fields we need:**
- `Front_9_Score_Stableford`, `Back_9_Score_Stableford` - Nine-hole splits
- `Front_9_vs_Back_9_Stableford` - Difference (identifies strong starters/finishers)
- `Gap_To_Leader_Before_Round_Stableford` - Deficit coming into round
- `Gap_To_Leader_After_Round_Stableford` - Deficit after round
- `Holes_In_Lead_Stableford` - Holes in lead during this round
- `Lead_Gained_Count_Stableford`, `Lead_Lost_Count_Stableford` - Lead changes
- `Cumulative_Tournament_Rank_Before_Round` - Where they stood entering round
- `Cumulative_Tournament_Rank_Stableford` - Where they stood after round
- `Eagles_Count`, `Birdies_Count`, `Triple_Bogeys_Or_Worse_Count` - Key events

**What's missing:**
- ❌ Within-round momentum spells (3-6 hole rolling windows)
- ❌ Specific hole ranges for hot/cold periods
- ❌ In-round lead margin tracking (only has before/after)

---

### 3. **commentary_round_events.parquet**
**What it contains:**
- Hole-by-hole significant events
- Lead changes (Took Lead, Lost Lead events)
- Ranking changes before/after each hole
- Final hole flags

**Key fields:**
- `Event` - Type of event (Took Lead, Eagle, Triple Bogey, etc.)
- `Rank_Stableford_Before`, `Rank_Stableford_After` - Position changes
- `Final_Hole_Flag` - Marks dramatic finishing holes

**What's missing:**
- ❌ Event severity/impact metrics
- ❌ Contextual timing (was this during a battle or runaway?)

---

### 4. **commentary_tournament_streaks.parquet**
**What it contains:**
- Longest streaks across entire tournament
- Types: Birdies, Bogeys, TBPs, Pars or Better, etc.
- Location strings (e.g., "T17 R2 H7 to T17 R2 H11")

**Key fields:**
- `Streak_Type` - What kind of streak
- `Max_Streak` - How many holes
- `Location` - Where it happened (includes round & hole info)

**Already useful, no major gaps**

---

### 5. **commentary_round_streaks.parquet**
**What it contains:**
- Similar to tournament streaks but scoped to individual rounds
- Useful for round-specific story building

**Already useful, no major gaps**

---

## 🎯 What We Already Have vs What We Need

### ✅ Already Available (No need to recreate!):

1. **Front 9 vs Back 9 analysis** ✅
   - Source: `commentary_round_summary.parquet`
   - Fields: `Front_9_Score_Stableford`, `Back_9_Score_Stableford`, `Front_9_vs_Back_9_Stableford`
   - Just need to filter for significant differences

2. **Round-by-round tournament context** ✅
   - Source: `commentary_round_summary.parquet`
   - Fields: `Gap_To_Leader_Before_Round`, `Gap_To_Leader_After_Round`, `Cumulative_Tournament_Rank_Before_Round`
   - Perfect for "coming into Round X" narratives

3. **Lead changes by round** ✅
   - Source: `commentary_round_summary.parquet`
   - Fields: `Lead_Gained_Count`, `Lead_Lost_Count`, `Holes_In_Lead`
   - Tells us IF leads changed, but not exact holes

4. **Lead changes by hole** ✅
   - Source: `commentary_round_events.parquet`
   - Event type: "Took Lead (Stableford)", "Lost Lead (Stableford)"
   - Has exact hole where lead changed

5. **Streaks with locations** ✅
   - Source: `commentary_tournament_streaks.parquet`, `commentary_round_streaks.parquet`
   - Already has hole ranges in Location field

### ❌ Still Need to Calculate:

1. **In-round momentum windows**
   - Need: Rolling 3-6 hole performance patterns
   - Source: Must calculate from `all-scores.parquet` (hole-by-hole)
   - Why: Round summaries only have before/after, not during

2. **Lead margin progression**
   - Need: Gap to leader at each hole (not just round end)
   - Source: Must calculate from `all-scores.parquet` with cumulative data
   - Why: Round summaries only have end-of-round gaps

3. **Tight battle periods**
   - Need: Identify when multiple players within X points
   - Source: Derive from hole-by-hole gap tracking
   - Why: Need real-time gaps, not just round snapshots

4. **Breakaway moments**
   - Need: Identify when gaps significantly widened
   - Source: Derive from hole-by-hole gap tracking
   - Why: Same as above

---

## 🔧 Implications for New Pipeline

### Files We Can Reuse Directly:
1. ✅ `commentary_round_summary.parquet` - Use for:
   - Front/back 9 analysis (already calculated!)
   - Round-by-round tournament context (before/after standings)
   - Round-level lead change counts
   - Eagles, birdies, disaster counts per round

2. ✅ `commentary_tournament_summary.parquet` - Use for:
   - Total tournament stats
   - Final standings
   - Tournament-wide holes in lead

3. ✅ `commentary_round_events.parquet` - Use for:
   - Exact holes where leads changed
   - Significant events (eagles, disasters)
   - Final hole drama

4. ✅ `commentary_tournament_streaks.parquet` & `commentary_round_streaks.parquet` - Use for:
   - Hot/cold spell identification (already has hole ranges!)
   - Linking patterns to specific windows

### Files We Still Need to Generate:
1. ❌ **In-round momentum analysis** (NEW)
   - Source: `all-scores.parquet` with rolling windows
   - Output: JSON with 3-6 hole performance windows per round
   - Why: Only place to get within-round spells

2. ❌ **Hole-by-hole lead margins** (NEW)
   - Source: `all-scores.parquet` with cumulative Gap calculations
   - Output: JSON with gap progression for lead battles
   - Why: Need real-time gaps for tight battles/breakaways

### Files We Can Deprecate:
1. ❌ `teg_X_data.json` - Full unfiltered data dump
   - Too large, causes context issues
   - Replace with focused analysis outputs

2. ❌ `teg_X_condensed.json` - Stripped down version
   - Loses too much nuance
   - Replace with targeted extracts from commentary parquets

---

## 💡 Recommended Approach

### Phase 1: Pattern Analysis (NEW - but lighter than planned!)

Instead of analyzing ALL data from scratch, we:

**Option A: Leverage Existing Commentary Files** ⭐ RECOMMENDED
```python
def prepare_round_data(teg_num, round_num):
    # Load from EXISTING commentary files
    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')
    round_data = round_summary[(TEGNum==teg_num) & (Round==round_num)]

    # Already have:
    # - Front/back 9 splits ✓
    # - Before/after tournament context ✓
    # - Lead changes count ✓
    # - Eagles/birdies/disasters ✓

    # Only calculate NEW:
    # - In-round momentum windows (from all-scores.parquet)
    # - Hole-by-hole gap progression (from all-scores.parquet)

    return combined_data
```

**Option B: Full Recalculation from Scratch**
- Don't do this - wasteful!
- We already have 80% of what we need in commentary files

### Phase 2: Round Story Building (SIMPLIFIED)

```python
def generate_round_story(teg_num, round_num):
    # Get data from EXISTING files
    round_summary = get_round_summary(teg_num, round_num)  # commentary_round_summary.parquet
    round_events = get_round_events(teg_num, round_num)    # commentary_round_events.parquet
    round_streaks = get_round_streaks(teg_num, round_num)  # commentary_round_streaks.parquet

    # Calculate ONLY what's missing
    momentum_windows = analyze_round_momentum(teg_num, round_num)  # NEW
    gap_progression = analyze_lead_margins(teg_num, round_num)     # NEW

    # Combine and feed to LLM
    round_data = {
        'summary': round_summary.to_dict('records'),  # Front/back 9, before/after context
        'events': round_events.to_dict('records'),    # Lead changes, eagles, disasters
        'streaks': round_streaks.to_dict('records'),  # Hot/cold spells with locations
        'momentum': momentum_windows,                  # 3-6 hole windows (NEW)
        'gap_progression': gap_progression             # Lead margin tracking (NEW)
    }

    # LLM generates round story
    return round_story_text
```

### Phase 3: Data Volume Comparison

**Current approach:**
- `teg_X_data.json`: ~4,000 data points (overwhelms context)
- `teg_X_condensed.json`: ~500 data points (loses nuance)

**New approach (per round):**
- From commentary_round_summary: ~50 points (5 players × 10 key fields)
- From commentary_round_events: ~10-20 events
- From commentary_round_streaks: ~10-15 streaks
- NEW momentum windows: ~20-30 windows
- NEW gap progression: ~30-40 data points
- **Total: ~150-200 focused data points per round** ✅

---

## 🚀 Updated Implementation Plan

### What Changes:

1. **Leverage existing commentary parquet files** for 80% of data needs
2. **Only calculate new patterns** for in-round momentum & gap progression
3. **Deprecate `teg_X_data.json` and `teg_X_condensed.json`** - use commentary parquets directly
4. **Simplify pattern analysis** - don't recalculate what we already have

### What Stays the Same:

1. Multi-pass round-based architecture ✓
2. Incremental story note building ✓
3. Round stories → tournament synthesis ✓
4. All use cases (in-progress, historical, iteration) ✓

### New Advantage:

**When data changes (rounds added/deleted), commentary parquets auto-update!**
- `update_commentary_caches()` already rebuilds these files
- Our pipeline just needs to reload them
- No manual recalculation of front/back 9, lead changes, etc.

---

## 📋 Action Items

### Immediate:
1. ✅ Document existing commentary file structure (this file)
2. ⬜ Identify exactly which fields from commentary files to use
3. ⬜ Build ONLY the missing analysis:
   - `analyze_round_momentum_windows()` - Rolling 3-6 hole performance
   - `analyze_hole_by_hole_gaps()` - Lead margin progression
4. ⬜ Create data loading functions that pull from commentary parquets
5. ⬜ Test with TEG 17 data

### Files to Create:
- `streamlit/commentary/pattern_analysis.py` - ONLY new patterns (momentum windows, gap progression)
- `streamlit/commentary/data_loader.py` - Load from commentary parquets

### Files to Deprecate:
- Stop generating `teg_X_data.json` (full dump)
- Stop generating `teg_X_condensed.json` (stripped version)
- Use commentary parquets directly instead

---

## 🎯 Summary

**Great news:** We already have 80% of the data we need!

- ✅ Front/back 9 splits
- ✅ Round-by-round tournament context
- ✅ Lead changes by hole
- ✅ Streaks with locations
- ✅ Events with rankings

**Only need to add:**
- ❌ In-round momentum windows (rolling 3-6 hole analysis)
- ❌ Hole-by-hole lead margin progression

**This significantly simplifies the implementation!**
