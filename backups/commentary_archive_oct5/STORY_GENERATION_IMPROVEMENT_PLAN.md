# Story Generation Improvement Plan - FINAL VERSION

## 🎯 Executive Summary

**Goal:** Generate richer tournament stories that capture round-by-round dynamics, battle progression, and in-round momentum shifts.

**Key Discovery:** We already have 80% of needed data in existing commentary parquet files! Only need to calculate in-round momentum patterns.

**Approach:** Multi-pass round-based pipeline leveraging existing data + targeted new analysis.

**Impact:**
- Enables in-progress tournament commentary
- Captures missing battle dynamics and momentum shifts
- Significantly simpler than originally planned (reuse existing files)
- Can deprecate `teg_X_data.json` and `teg_X_condensed.json`

---

## 📊 Current State Analysis

### Problems Being Solved

#### Problem 1: Data Overload → Context Window Issues
**Current:** `full data → teg_x_data.json (4,000 points) → teg_x_condensed.json (loses nuance) → story_notes`

**Issues:**
- Can't separate signal from noise with everything at once
- Condensed version loses important battle dynamics
- Single-pass processing mixes all data types together

**Solution:** Multi-pass focused analysis using existing commentary parquets + targeted new calculations

#### Problem 2: Tournament-Level Stories Miss Round Richness
**Current:** Aggregate tournament data → tournament story

**Issues:**
- Missing in-round momentum shifts (within rounds, not just round summaries)
- Can't generate commentary for in-progress tournaments
- Round-by-round drama is lost in aggregation

**Solution:** Build detailed round stories first → synthesize into tournament story

---

## 🎉 Major Discovery: Existing Commentary Files

### What We Already Have (Auto-Generated on Data Changes)

When core data changes, `update_commentary_caches()` in `utils.py` automatically creates these files in `data/`:

#### 1. **commentary_round_summary.parquet** ⭐ GOLDMINE
**Already contains:**
- ✅ **Front 9 vs Back 9 splits** (`Front_9_Score_Stableford`, `Back_9_Score_Stableford`, `Front_9_vs_Back_9_Stableford`)
- ✅ **Round-by-round tournament context** (`Gap_To_Leader_Before_Round`, `Gap_To_Leader_After_Round`, `Cumulative_Tournament_Rank_Before_Round`)
- ✅ **Lead tracking per round** (`Holes_In_Lead_Stableford`, `Lead_Gained_Count`, `Lead_Lost_Count`)
- ✅ **Round performance stats** (`Eagles_Count`, `Birdies_Count`, `Triple_Bogeys_Or_Worse_Count`)

**Use for:**
- "Coming into Round X" context (already calculated!)
- "After Round X" standings (already calculated!)
- Front/back 9 analysis (already calculated!)
- Round-level lead changes

#### 2. **commentary_round_events.parquet**
**Already contains:**
- ✅ **Exact holes where leads changed** (Event: "Took Lead", "Lost Lead")
- ✅ **Significant events** (Eagles, disasters, etc.)
- ✅ **Ranking changes** (`Rank_Stableford_Before`, `Rank_Stableford_After`)

**Use for:**
- Specific hole-by-hole drama
- Lead change moments with exact locations

#### 3. **commentary_tournament_streaks.parquet & commentary_round_streaks.parquet**
**Already contains:**
- ✅ **Hot/cold spells with hole ranges** (`Location` field like "T17 R2 H7 to T17 R2 H11")
- ✅ **Streak types** (Birdies, Bogeys, TBPs, Pars or Better, etc.)

**Use for:**
- Identifying momentum spells (already has hole ranges!)
- Linking patterns to specific windows

#### 4. **commentary_tournament_summary.parquet**
**Already contains:**
- ✅ **Total tournament stats** (`Total_Holes_In_Lead`, `Final_Rank`, `Final_Gap`)
- ✅ **Competition outcomes** (`Won_Stableford`, `Wooden_Spoon`, `Margin`)

**Use for:**
- Tournament-level context
- Historical comparisons

### What We Still Need to Calculate (Only 20% of work!)

❌ **In-round momentum windows** - Rolling 3-6 hole performance patterns
- Why: Round summaries only have before/after, not during
- Source: Calculate from `all-scores.parquet` with rolling windows

❌ **Hole-by-hole lead margins** - Gap progression for tight battles
- Why: Round summaries only have end-of-round gaps
- Source: Calculate from `all-scores.parquet` with cumulative Gap_Stableford_TEG

### Files We Can Deprecate

❌ `teg_X_data.json` - Full unfiltered data dump (too large)
❌ `teg_X_condensed.json` - Stripped version (loses nuance)

**Replace with:** Direct use of commentary parquets + focused new analysis

---

## 🏗️ The New Architecture (Simplified!)

```
┌─────────────────────────────────────────────────┐
│ DATA PREPARATION (When core data changes)      │
│ Already happens automatically via utils.py:     │
│                                                  │
│ update_commentary_caches() generates:           │
│ ├─ commentary_round_summary.parquet            │
│ ├─ commentary_round_events.parquet             │
│ ├─ commentary_tournament_streaks.parquet        │
│ ├─ commentary_round_streaks.parquet             │
│ └─ commentary_tournament_summary.parquet        │
│                                                  │
│ ✅ 80% of data already prepared!                │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│ PHASE 1: Calculate Missing Patterns (Python)   │
│ Only need to add 20% new analysis!             │
│                                                  │
│ For tournament (or up to current round):        │
│                                                  │
│ analyze_round_momentum_windows(teg_num)         │
│ ├─ Input: all-scores.parquet (hole-by-hole)   │
│ ├─ Calculate: Rolling 3-6 hole performance     │
│ └─ Output: momentum_patterns.json              │
│                                                  │
│ analyze_hole_by_hole_gaps(teg_num)              │
│ ├─ Input: all-scores.parquet (with Gap cols)  │
│ ├─ Calculate: Lead margin progression          │
│ └─ Output: gap_progression.json                │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│ PHASE 2: Round Stories (LLM - 4 passes)        │
│                                                  │
│ For each round, APPEND to teg_17_story_notes.md │
│                                                  │
│ Round 1 Story (~150 data points):               │
│ ├─ commentary_round_summary (R1) [50 pts]      │
│ │  • Front/back 9 splits ✓                     │
│ │  • Before/after tournament context ✓         │
│ │  • Lead changes count ✓                      │
│ ├─ commentary_round_events (R1) [10-20 items]  │
│ │  • Lead change holes ✓                       │
│ │  • Significant events ✓                      │
│ ├─ commentary_round_streaks (R1) [10-15 items] │
│ │  • Hot/cold spells with locations ✓          │
│ ├─ momentum_patterns (R1) [20-30 windows] NEW  │
│ │  • Rolling 3-6 hole performance              │
│ └─ gap_progression (R1) [30-40 points] NEW     │
│    • Lead margin tracking                       │
│                                                  │
│ Each round section includes:                    │
│ - Tournament context coming in                  │
│ - In-round dynamics (momentum, battles)         │
│ - Tournament context after                      │
│                                                  │
│ Rounds build on each other:                     │
│ R2 uses R1 ending → R3 uses R2 ending → etc    │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│ PHASE 3: Tournament Synthesis (LLM - 1 pass)   │
│                                                  │
│ APPEND to teg_17_story_notes.md:               │
│                                                  │
│ Input:                                          │
│ ├─ 4 round story sections (text summaries)     │
│ ├─ commentary_tournament_summary [50 pts]      │
│ └─ Historical context [20 pts]                 │
│                                                  │
│ Add:                                            │
│ ├─ Tournament Overview section                  │
│ ├─ Tournament Themes section                    │
│ └─ Final Context section                        │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│ PHASE 4: Report Generation (LLM - on demand)   │
│                                                  │
│ From teg_17_story_notes.md:                    │
│                                                  │
│ ├─ Round Reports (optional)                    │
│ │  • Detailed or high-level                    │
│ │  • Generated from round sections             │
│ │                                               │
│ └─ Tournament Report                            │
│    • Uses complete story_notes                  │
│    • Includes round detail                      │
└─────────────────────────────────────────────────┘
```

---

## 📄 Story Notes Structure

### Single Master File: `teg_17_story_notes.md`

```markdown
# TEG 17 Story Notes

## Tournament Overview
[High-level arc - added after all rounds in Phase 3]

## Round 1 Story
### Tournament Context Coming In
- Pre-tournament standings, expectations
- [From commentary_round_summary: Gap_To_Leader_Before_Round]

### How Round 1 Unfolded
#### Opening Nine
- [From commentary_round_summary: Front_9_Score_Stableford]
- [From momentum_patterns: Hot/cold spells in holes 1-9]
- [From gap_progression: Lead margins during opening nine]

#### Back Nine
- [From commentary_round_summary: Back_9_Score_Stableford]
- [From commentary_round_events: Lead changes with hole numbers]
- [From commentary_round_streaks: Birdie/bogey runs]

### Key Round 1 Moments
- [From commentary_round_events: Eagles, disasters]
- [From momentum_patterns: 3-6 hole hot/cold windows]

### Tournament Context After Round 1
- [From commentary_round_summary: Gap_To_Leader_After_Round]
- [From commentary_round_summary: Cumulative_Tournament_Rank]
- Momentum check going into R2

## Round 2 Story
### Tournament Context Coming In
- [Links to Round 1 ending context above]
- How field looks entering R2

### How Round 2 Unfolded
[Same structure as R1, using R2 data from same sources]

## Round 3 Story
[Same structure]

## Round 4 Story
[Same structure]

## Tournament Themes
[Added in Phase 3 - patterns across rounds]
- [From commentary_tournament_summary: Total_Holes_In_Lead, etc.]

## Final Context
[Added in Phase 3 - historical significance]
- [Historical comparisons, records]
```

**Coherence mechanisms:**
- Each round uses previous round's "after" as "before"
- Standard sections ensure consistency
- Explicit references prevent contradictions

---

## 📊 Data Volume Comparison

### Old Approach:
- `teg_X_data.json`: ~4,000 points (overwhelms)
- `teg_X_condensed.json`: ~500 points (loses nuance)

### New Approach (per round):
- commentary_round_summary: ~50 points ✅ Already exists
- commentary_round_events: ~10-20 items ✅ Already exists
- commentary_round_streaks: ~10-15 items ✅ Already exists
- momentum_patterns (NEW): ~20-30 windows
- gap_progression (NEW): ~30-40 points

**Total per round: ~150-200 focused points** ✅ Manageable!

**Key advantage:** Most data already prepared and auto-updates!

---

## 🔄 How It Works for Different Use Cases

### Use Case 1: In-Progress Tournament
**Scenario:** TEG 17, Round 2 just finished

**Workflow:**
1. Commentary parquets auto-updated (already happens)
2. Run Phase 1: Calculate momentum/gaps for R1-2
3. Generate R1 story → append to story_notes
4. Generate R2 story → append to story_notes
5. Generate R1 & R2 reports for publishing
6. When R3 completes → repeat (add R3 story)
7. When tournament done → add tournament synthesis

### Use Case 2: Historical Tournament (Complete)
**Scenario:** Regenerating TEG 10

**Workflow:**
1. Load existing commentary parquets (already exist)
2. Run Phase 1: Calculate momentum/gaps for all rounds
3. Generate R1-4 stories sequentially → build story_notes
4. Generate tournament synthesis → complete story_notes
5. Generate tournament report (includes all round detail)

### Use Case 3: Iteration & Improvement
**Scenario:** Edit TEG 17 after review

**Workflow:**
1. Edit `teg_17_story_notes.md` (any section)
2. Regenerate affected report:
   - Edited R2? → Regenerate R2 report only
   - Edited tournament sections? → Regenerate tournament report
   - No need to rerun full pipeline!

---

## ✅ What This Achieves

**Problems Solved:**
- ✅ Data overload → Multi-pass + existing parquets
- ✅ Round richness → Detailed round stories with in-round momentum
- ✅ Battle dynamics → Lead changes, gaps, tight periods
- ✅ Momentum shifts → Rolling windows + front/back 9
- ✅ In-progress tournaments → Round-by-round generation
- ✅ Iteration speed → Single editable story_notes file

**New Capabilities:**
- ✅ Generate round commentary as tournament unfolds
- ✅ Update tournament story after each round
- ✅ Both round and tournament reports from same notes
- ✅ Flexible detail level (detailed or high-level)

**Efficiency Gains:**
- ✅ 80% of data already prepared (commentary parquets)
- ✅ Auto-updates when data changes
- ✅ Only 20% new calculation needed
- ✅ Can deprecate data.json and condensed.json files

---

## 🚀 Implementation Phases

### Phase 1: Build Missing Pattern Analysis ✨ NEW (20% of work)

**File to create:** `streamlit/commentary/pattern_analysis.py`

```python
def analyze_round_momentum_windows(teg_num, round_num=None):
    """
    Calculate rolling 3-6 hole performance windows.

    Args:
        teg_num: Tournament number
        round_num: Specific round (None = all rounds)

    Returns:
        List of momentum windows with:
        - Player, Round, Holes (e.g., "5-7"),
        - Points scored, Rank change, Pattern type (hot/cold)
    """
    # Load hole-by-hole data
    df = load_all_data_for_teg(teg_num)
    if round_num:
        df = df[df['Round'] == round_num]

    # Calculate rolling windows (3 and 6 holes)
    df['rolling_3_pts'] = df.groupby(['Player','Round'])['Stableford'].rolling(3).sum()
    df['rolling_6_pts'] = df.groupby(['Player','Round'])['Stableford'].rolling(6).sum()

    # Identify hot/cold spells (thresholds to test)
    windows = []
    # Hot: 3 holes with 10+ points
    # Cold: 3 holes with ≤3 points
    # Etc.

    return windows

def analyze_hole_by_hole_gaps(teg_num, round_num=None):
    """
    Calculate lead margin progression hole-by-hole.

    Uses existing Gap_Stableford_TEG from all-scores.parquet.

    Returns:
        List of gap snapshots with:
        - Hole, Leader, Margin to 2nd, Field spread
    """
    df = load_all_data_for_teg(teg_num)  # Has Gap_Stableford_TEG already!
    if round_num:
        df = df[df['Round'] == round_num]

    # Track gaps hole by hole
    gaps = []
    for hole in df['Hole'].unique():
        hole_data = df[df['Hole'] == hole]
        leader = hole_data[hole_data['Gap_Stableford_TEG']==0]['Player'].iloc[0]
        margin = hole_data['Gap_Stableford_TEG'].nsmallest(2).iloc[1]

        gaps.append({
            'hole': hole,
            'leader': leader,
            'margin_to_2nd': margin,
            'tight_battle': margin <= 2,
            'breakaway': margin >= 10
        })

    return gaps
```

### Phase 2: Create Data Loading Module ✨ NEW

**File to create:** `streamlit/commentary/data_loader.py`

```python
def load_round_data(teg_num, round_num):
    """
    Load all data needed for a round story.
    Uses existing commentary parquets + new patterns.
    """
    # Load from EXISTING parquets (already have 80% of data!)
    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')
    round_summary = round_summary[(round_summary['TEGNum']==teg_num) &
                                   (round_summary['Round']==round_num)]

    round_events = pd.read_parquet('data/commentary_round_events.parquet')
    round_events = round_events[(round_events['TEGNum']==teg_num) &
                                 (round_events['Round']==round_num)]

    round_streaks = pd.read_parquet('data/commentary_round_streaks.parquet')
    round_streaks = round_streaks[(round_streaks['TEGNum']==teg_num) &
                                   (round_streaks['Round']==round_num)]

    # Calculate NEW patterns (only 20% of work)
    momentum_windows = analyze_round_momentum_windows(teg_num, round_num)
    gap_progression = analyze_hole_by_hole_gaps(teg_num, round_num)

    return {
        'summary': round_summary.to_dict('records'),      # Front/back 9, context
        'events': round_events.to_dict('records'),        # Lead changes, eagles
        'streaks': round_streaks.to_dict('records'),      # Hot/cold spells
        'momentum': momentum_windows,                      # NEW: Rolling windows
        'gaps': gap_progression                            # NEW: Margin tracking
    }
```

### Phase 3: Update Prompts 🔧 MODIFY

**File to modify:** `streamlit/commentary/prompts.py`

**Add:**
```python
ROUND_STORY_PROMPT = """
You are writing a detailed round story for a tournament.

**Available Data Sources:**

From commentary_round_summary (already calculated):
- Front 9 vs Back 9 performance
- Tournament context before this round (standings, gaps)
- Tournament context after this round (new standings, gaps)
- Lead changes count for this round

From commentary_round_events (already calculated):
- Exact holes where leads changed
- Eagles, disasters, significant moments

From commentary_round_streaks (already calculated):
- Hot/cold spells with specific hole ranges

From momentum analysis (newly calculated):
- Rolling 3-6 hole performance windows
- In-round momentum patterns

From gap progression (newly calculated):
- Hole-by-hole lead margins
- Tight battle periods
- Breakaway moments

**Your Task:**
Write Round {round_num} story with:

1. Tournament Context Coming In
2. How the Round Unfolded (Opening 9, Back 9)
3. Key Moments (with specific holes)
4. Tournament Context After

Use specific hole ranges, leverage the detailed data provided.
"""

TOURNAMENT_SYNTHESIS_PROMPT = """
You have 4 detailed round stories.

Synthesize into tournament-level sections:
- Tournament Overview (arc across rounds)
- Tournament Themes (patterns, storylines)
- Final Context (historical significance)

Avoid repeating round details (already in document).
Focus on how rounds connected and overall narrative.
"""
```

### Phase 4: Build Main Pipeline ✨ NEW

**File to create:** `streamlit/commentary/generate_tournament_commentary_v2.py`

```python
def generate_round_story_notes(teg_num, round_num, previous_context=None):
    """Generate story notes for a single round."""
    # Load data (80% from existing parquets, 20% new analysis)
    round_data = load_round_data(teg_num, round_num)

    # Build prompt
    prompt = build_round_story_prompt(
        round_num=round_num,
        round_data=round_data,
        previous_context=previous_context
    )

    # LLM generates round story
    round_story = call_llm_with_prompt(ROUND_STORY_PROMPT, prompt)

    # Extract ending context for next round
    ending_context = extract_ending_context(round_data)

    return round_story, ending_context

def generate_complete_tournament_story_notes(teg_num, rounds=[1,2,3,4]):
    """Generate complete story notes file."""
    story_sections = []
    previous_context = None

    # Phase 2: Round stories
    for round_num in rounds:
        round_story, round_context = generate_round_story_notes(
            teg_num, round_num, previous_context
        )
        story_sections.append(round_story)
        previous_context = round_context

    # Phase 3: Tournament synthesis
    tournament_data = load_tournament_data(teg_num)
    synthesis = generate_tournament_synthesis(
        round_stories=story_sections,
        tournament_data=tournament_data
    )

    # Combine into master file
    complete_notes = build_story_notes_file(
        teg_num=teg_num,
        round_sections=story_sections,
        tournament_sections=synthesis
    )

    # Save
    save_story_notes(teg_num, complete_notes)

    return complete_notes
```

---

## 📝 Next Steps

### Immediate Actions (Ordered):

1. ✅ Document existing commentary files (DONE - see EXISTING_DATA_ANALYSIS.md)
2. ✅ Update main plan with discovery (DONE - this document)
3. ⬜ **Build pattern_analysis.py:**
   - Start with `analyze_round_momentum_windows()`
   - Test on TEG 17 Round 2 data
   - Validate output shows hot/cold spells
4. ⬜ **Build `analyze_hole_by_hole_gaps()`:**
   - Test on TEG 17 data
   - Identify tight battles and breakaways
5. ⬜ **Build data_loader.py:**
   - Load from existing commentary parquets
   - Integrate new pattern analysis
   - Test on TEG 17 Round 2
6. ⬜ **Create round story prompt:**
   - Add to prompts.py
   - Test with TEG 17 R2 data
7. ⬜ **Create tournament synthesis prompt:**
   - Add to prompts.py
8. ⬜ **Build main pipeline:**
   - generate_tournament_commentary_v2.py
   - Test on TEG 17 (all rounds)
9. ⬜ **Test in-progress scenario:**
   - Simulate TEG 17 with only R1-2
   - Verify can add R3-4 later
10. ⬜ **Compare outputs:**
    - New story notes vs old
    - New reports vs old
    - Iterate and refine

### Success Criteria:

- [ ] Pattern analysis identifies meaningful momentum spells
- [ ] Round stories capture in-round dynamics with specific holes
- [ ] Rounds link coherently without contradictions
- [ ] Tournament synthesis adds value without repetition
- [ ] Can generate both round and tournament reports
- [ ] Human review confirms: "This captures what I see in charts"

---

## 📚 Files Reference

### Existing Files (Leverage):
- `data/commentary_round_summary.parquet` - Round stats with front/back 9 ✓
- `data/commentary_round_events.parquet` - Lead changes, events ✓
- `data/commentary_round_streaks.parquet` - Hot/cold spells ✓
- `data/commentary_tournament_summary.parquet` - Tournament stats ✓
- `data/commentary_tournament_streaks.parquet` - Tournament streaks ✓
- `streamlit/utils.py` - Already has `update_commentary_caches()` ✓
- `data/all-scores.parquet` - Source for new analysis ✓

### New Files to Create:
- `streamlit/commentary/pattern_analysis.py` - NEW momentum & gap analysis
- `streamlit/commentary/data_loader.py` - NEW load from parquets
- `streamlit/commentary/generate_tournament_commentary_v2.py` - NEW pipeline

### Files to Modify:
- `streamlit/commentary/prompts.py` - ADD round & synthesis prompts

### Files to Deprecate:
- Stop generating `teg_X_data.json` (replaced by commentary parquets)
- Stop generating `teg_X_condensed.json` (replaced by focused loading)

---

## 🎯 Summary

**The Plan:**
1. Leverage 80% existing data from commentary parquets (auto-updated!)
2. Calculate only 20% new patterns (momentum windows, gap progression)
3. Build round stories using combined data (~150-200 focused points each)
4. Synthesize tournament story from round stories
5. Generate flexible reports (round or tournament, detailed or high-level)

**Why This Works:**
- ✅ Uses data that already auto-updates
- ✅ Significantly simpler than originally planned
- ✅ Focused data per round (no overload)
- ✅ Captures missing in-round momentum
- ✅ Enables all use cases (in-progress, historical, iteration)
- ✅ Single editable story_notes foundation

**Next Action:**
Build `pattern_analysis.py` with momentum window calculation, test on TEG 17 R2.

---

*Document created: 2025-10-05*
*Last updated: 2025-10-05 (with existing data discovery)*
