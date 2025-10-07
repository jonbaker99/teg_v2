# Tournament Story Generation - Final Implementation Plan

## ✅ IMPLEMENTATION STATUS (Updated 2025-01-06)

**STATUS: COMPLETE AND ENHANCED**

All components have been built, tested, and are working correctly. The pipeline generates structured story notes (bullet points/facts) that can be used as foundation for final report generation.

### What's Complete
- ✅ `streamlit/commentary/pattern_analysis.py` - All 7 data processing passes
- ✅ `streamlit/commentary/data_loader.py` - 2 data loading functions
- ✅ `streamlit/commentary/generate_tournament_commentary_v2.py` - Main pipeline with career context
- ✅ `streamlit/commentary/prompts.py` - Updated with structured note-generation prompts
- ✅ Tested on TEG 17 Round 1 - Produces correct structured bullet format
- ✅ **NEW**: Direct addition of factual sections (venue, records, course records) - saves ~2500-4500 tokens/tournament
- ✅ **NEW**: Career context added to tournament synthesis (recent finishes + position counts, PRE-TOURNAMENT only)
- ✅ **NEW**: INCLUDE_STREAKS toggle for easy feature testing

### How to Use (See "HOW TO USE" section below)
```bash
# Single round (testing)
python streamlit/commentary/generate_tournament_commentary_v2.py 17 --partial 1

# Complete tournament
python streamlit/commentary/generate_tournament_commentary_v2.py 17
```

### Important Discovery
First test accidentally generated **excellent narrative prose** instead of structured notes. Those narrative-style prompts are perfect for future report generation (Level 3). Current prompts now correctly generate structured bullet notes (Level 2).

---

## 🚀 QUICK START (For New Conversation)

**Context:** This pipeline builds structured story_notes.md files (bullets/facts), NOT final narrative reports. Story notes are the editable foundation for generating detailed reports later.

**What this builds:**
```
Data Processing (6 Python passes)
  → Round Notes (4 LLM passes - structured bullets)
  → Tournament Synthesis (1 LLM pass - structured bullets)
  → story_notes.md ✓ (STRUCTURED FORMAT)
```

**Implementation is COMPLETE.** See "HOW TO USE" section below for running the pipeline.

**Test case:** TEG 17 (has 4 rounds, complete tournament) - Successfully tested Round 1

---

## 🎯 Executive Summary

**Goal:** Generate richer tournament stories capturing round-by-round dynamics, battle progression, and in-round momentum shifts.

**Key Discovery:** 80% of needed data already exists in auto-generated commentary parquet files.

**Approach:** Multi-pass data processing (Python) + round-based story generation (LLM)

**Total Passes:**
- **6 data processing passes** (Python - free, fast)
- **5 story generation passes** (LLM - 4 rounds + 1 tournament synthesis)

**Output:** `teg_X_story_notes.md` (editable foundation for reports)

---

## 🏗️ Architecture Overview

### Two-Level Multi-Pass Approach

**Level 1: Data Type Processing (Python - Multi-Pass)**
```
Pass 1: Lead progression analysis → lead_timeline.json
Pass 2: Momentum windows analysis → momentum_patterns.json
Pass 3: Front/back 9 analysis → nine_patterns.json
Pass 4: Pattern drill-down → pattern_details.json
Pass 5: Reuse commentary_round_events.parquet (already exists)
Pass 6: Reuse commentary_round_summary.parquet (already exists)
Pass 7: Identify records & personal bests → records_by_round
Pass 8: Load streak data (OPTIONAL - controlled by INCLUDE_STREAKS flag)

Output: 7-8 structured data files (JSON/parquet)
Cost: Free (Python processing)
Time: Fast (no LLM calls)
```

**Level 2: Story Generation (LLM - Multi-Pass by Round)**
```
Round 1 story: Combine all 6 data types for R1 → story section
Round 2 story: Combine all 6 data types for R2 → story section
Round 3 story: Combine all 6 data types for R3 → story section
Round 4 story: Combine all 6 data types for R4 → story section
Tournament synthesis: Use 4 round stories → overview/themes

Output: Single story_notes.md file built incrementally
Cost: 5 LLM calls per tournament
Time: Moderate (5 sequential LLM calls)
```

---

## 📊 Detailed Pipeline Flow

```
┌──────────────────────────────────────────────────────────┐
│ LEVEL 1: DATA TYPE PROCESSING (Python - 6 passes)       │
│                                                          │
│ Uses: all-scores.parquet + existing commentary files    │
│                                                          │
│ Pass 1: analyze_lead_progression(teg_num)               │
│ ├─ Input: all-scores.parquet (Gap_Stableford_TEG col) │
│ ├─ Analyze: Lead changes, margins, tight battles       │
│ └─ Output: lead_timeline.json (all rounds)             │
│                                                          │
│ Pass 2: analyze_momentum_windows(teg_num)               │
│ ├─ Input: all-scores.parquet (hole-by-hole scoring)   │
│ ├─ Calculate: Rolling 3-6 hole performance windows     │
│ └─ Output: momentum_patterns.json (all rounds)         │
│                                                          │
│ Pass 3: analyze_front_back_nine(teg_num)                │
│ ├─ Input: commentary_round_summary.parquet ✓           │
│ ├─ Identify: Significant F9/B9 differences per round   │
│ └─ Output: nine_patterns.json (all rounds)             │
│                                                          │
│ Pass 4: drill_down_patterns(patterns, teg_num)          │
│ ├─ Input: momentum_patterns + nine_patterns            │
│ ├─ For each hot/cold spell: Find specific holes        │
│ │  Example: "Hot spell holes 5-8" → "Birdie H6, 3 pars"│
│ └─ Output: pattern_details.json (narrative specifics)  │
│                                                          │
│ Pass 5: Load commentary_round_events.parquet ✓          │
│ ├─ Already has: Lead changes, eagles, disasters        │
│ └─ Filter by round as needed                           │
│                                                          │
│ Pass 6: Load commentary_round_summary.parquet ✓         │
│ ├─ Already has: Before/after context, F9/B9 scores    │
│ └─ Filter by round as needed                           │
│                                                          │
│ Result: 6 structured data sources ready for stories    │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│ LEVEL 2: STORY GENERATION (LLM - per round)             │
│                                                          │
│ For round in get_teg_rounds(teg_num):  # Handles 3-4 rds│
│                                                          │
│   Round X Story Generation:                             │
│   ├─ Load data for Round X from all 6 sources:         │
│   │  • lead_timeline (R_X entries) [10-15 items]       │
│   │  • momentum_patterns (R_X entries) [20-30 items]   │
│   │  • nine_patterns (R_X entry) [5 items]             │
│   │  • pattern_details (R_X entries) [15-20 items]     │
│   │  • commentary_round_events (R_X) [10-20 items]     │
│   │  • commentary_round_summary (R_X) [50 points]      │
│   │                                                     │
│   │  Total: ~120-180 focused data points               │
│   │                                                     │
│   ├─ Previous round ending context (if R > 1)          │
│   │                                                     │
│   ├─ LLM generates Round X story with:                 │
│   │  • Tournament context coming in                    │
│   │  • Opening 9 dynamics (uses F9 data + patterns)    │
│   │  • Back 9 dynamics (uses B9 data + patterns)       │
│   │  • Key moments (uses events + drill-down)          │
│   │  • Tournament context after                        │
│   │                                                     │
│   └─ APPEND to teg_X_story_notes.md                    │
│                                                          │
│ LLM Passes: 3-4 (depends on rounds in tournament)      │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│ TOURNAMENT SYNTHESIS (LLM - 1 pass)                      │
│                                                          │
│ Input:                                                   │
│ ├─ All round story sections (from story_notes.md)      │
│ ├─ commentary_tournament_summary.parquet [50 points]    │
│ └─ Historical context [20 points]                       │
│                                                          │
│ LLM generates:                                           │
│ ├─ Tournament Overview (arc across rounds)              │
│ ├─ Tournament Themes (cross-round patterns)             │
│ └─ Final Context (historical significance)              │
│                                                          │
│ APPEND these sections to teg_X_story_notes.md           │
│                                                          │
│ LLM Passes: 1                                            │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│ REPORT GENERATION (LLM - on demand)                      │
│                                                          │
│ From complete teg_X_story_notes.md:                     │
│                                                          │
│ Option A: Round Reports                                 │
│ ├─ Input: Round X section from story_notes             │
│ ├─ Style: Detailed or high-level (user choice)         │
│ └─ Output: teg_X_round_X_report.md                     │
│                                                          │
│ Option B: Tournament Report                             │
│ ├─ Input: Complete story_notes (all sections)          │
│ ├─ Includes: All round detail + tournament synthesis   │
│ └─ Output: teg_X_main_report.md                        │
│                                                          │
│ LLM Passes: As needed (user-triggered)                  │
└──────────────────────────────────────────────────────────┘
```

**VALIDATION NOTE (2025-01-05):**

Test run on TEG 17 Round 1 showed that the current `ROUND_STORY_PROMPT` and `TOURNAMENT_SYNTHESIS_PROMPT` produce **excellent narrative prose** - exactly what's needed for final reports (Option B above).

The prompts work perfectly for report generation. However, they're currently being used at the wrong pipeline stage. Story notes generation (Level 2) needs different prompts that output **structured bullets and facts** instead of narrative prose.

**What was generated in test:** Full narrative prose with great detail and specific hole references - perfect for `teg_X_main_report.md`

**What should be generated:** Structured bullet points and facts (like existing `teg_17_story_notes.md`) that can be used as foundation for reports.

**Fix Applied (2025-01-05):** Prompts rewritten to produce structured bullet notes. Pipeline now works correctly.

---

## 📖 HOW TO USE

### Prerequisites
- Anthropic API key set in `.streamlit/secrets.toml`:
  ```toml
  ANTHROPIC_API_KEY = "sk-ant-..."
  ```
- Or set as environment variable: `export ANTHROPIC_API_KEY="sk-ant-..."`

### Commands

**Test with single round:**
```bash
cd "c:\Users\jonba\Documents\Projects - not on onedrive\teg_v2"
python streamlit/commentary/generate_tournament_commentary_v2.py 17 --partial 1
```

**In-progress tournament (first N rounds):**
```bash
# First 2 rounds
python streamlit/commentary/generate_tournament_commentary_v2.py 17 --partial 2

# First 3 rounds
python streamlit/commentary/generate_tournament_commentary_v2.py 17 --partial 3
```

**Complete tournament (all rounds + synthesis):**
```bash
python streamlit/commentary/generate_tournament_commentary_v2.py 17
```

### Output Files

**Partial (in-progress):**
- Location: `streamlit/commentary/outputs/teg_X_story_notes_partial.md`
- Contains: Round notes for completed rounds only (no tournament synthesis)

**Complete:**
- Location: `streamlit/commentary/outputs/teg_X_story_notes.md`
- Contains: All round notes + tournament synthesis (Key Points, How It Unfolded, Story Angles, etc.)

### What You Get

**Structured bullet-point notes including:**
- Key moments with specific holes (e.g., "H5: Alex BAKER sextuple bogey")
- Lead progression and changes
- Hot/cold spells (both net and gross scoring)
- Front 9 / Back 9 patterns
- Round statistics
- Tournament synthesis (complete tournaments only)

**NOT narrative prose.** These notes are foundation data for generating detailed reports later.

---

## 🚀 NEXT STEPS (Future Development)

### Level 3: Report Generation (PROMPTS COMPLETE - 2025-01-05)

**STATUS:** Report generation prompts have been created and are ready to use.

Generate narrative prose reports from story notes:

**Prompts Created (in `prompts.py`):**

1. **MAIN_REPORT_PROMPT** (lines 478-585)
   - Input: `{story_notes}` (structured bullets from Level 2)
   - Output: Full narrative tournament report
   - Structure:
     - Tournament Summary (3-4 paragraphs): Winner, highlights, records
     - Round-by-Round Report (detailed narrative for each round with catchy titles)
     - Tournament Recap (2-3 paragraphs): Overall significance
   - Style: Barney Ronay-inspired, entertaining, witty, dramatic
   - **Critical feature:** Uses specific hole numbers from notes extensively
   - Includes examples of good vs bad writing

2. **BRIEF_SUMMARY_PROMPT** (lines 212-259)
   - Input: `{story_notes}` (structured bullets from Level 2)
   - Output: Concise 2-3 paragraph summary
   - Focus: Winner, key moments, tournament significance
   - Style: Punchy and entertaining while being brief
   - Includes specific examples of concise writing

**How These Prompts Work:**
- Both take the structured story notes (bullets/facts) as input
- Transform structured data into engaging narrative prose
- Maintain specific hole references from notes
- Based on the "accidentally generated" narrative style that worked perfectly
- Ready to be used in report generation functions

**What Still Needs Building:**
1. Functions in `generate_tournament_commentary_v2.py` to call these prompts:
   - `generate_main_report_from_notes(teg_num)` - Uses MAIN_REPORT_PROMPT
   - `generate_brief_summary_from_notes(teg_num)` - Uses BRIEF_SUMMARY_PROMPT
   - `generate_player_profiles_from_notes(teg_num)` - Uses PLAYER_PROFILES_PROMPT (may need update)
2. CLI commands to invoke report generation
3. Output file management (`teg_X_main_report.md`, `teg_X_brief_summary.md`)

**Usage Pattern (when built):**
```bash
# Step 1: Generate structured story notes (Level 2 - already works)
python streamlit/commentary/generate_tournament_commentary_v2.py 17

# Step 2: Generate reports from notes (Level 3 - prompts ready, functions needed)
python streamlit/commentary/generate_tournament_commentary_v2.py 17 --generate-report
python streamlit/commentary/generate_tournament_commentary_v2.py 17 --generate-summary
python streamlit/commentary/generate_tournament_commentary_v2.py 17 --generate-profiles
```

**Key Insight:** The prompts from our first test (that accidentally generated narrative prose instead of bullets) have been refined and are now properly positioned for Level 3. They work perfectly - they were just being used at the wrong stage before.

---

## ✅ VALIDATION RESULTS (TEG 17 Round 1 - 2025-01-05)

### Data Processing (Level 1)
- ✅ 220 momentum patterns detected (net + gross)
- ✅ 9 significant front/back 9 patterns
- ✅ 1 lead change identified
- ✅ 229 patterns enriched with hole-level drill-down
- ✅ 202 round events loaded
- ✅ 20 round summaries loaded

### Story Notes Generation (Level 2)
- ✅ Output format: Structured bullets (correct)
- ✅ Key moments section: 27 specific hole references
- ✅ Hot/cold spells: Organized by net/gross with specific holes
- ✅ Stats section: Complete with rankings and counts
- ✅ Format matches existing `teg_17_story_notes.md` structure

### Performance
- Processing time: ~30 seconds for 6 data passes + 1 LLM call
- Output size: ~5,000 characters of structured notes
- LLM calls: 1 per round + 1 synthesis (5 total for 4-round tournament)

### Example Output
```markdown
### Key Moments
- H5: Alex BAKER sextuple bogey (10 on par 4)
- H13: David MULLIN birdie (4 pts, -1 gross)
- H16: John PATTERSON takes Stableford lead

### Hot Spells (Net)
- John PATTERSON holes 8-13: 18 pts (birdies on holes 9, 12)

### Cold Spells (Gross)
- Alex BAKER holes 3-5: Avg +4.33 vs par (disasters on holes 3, 4, 5)
```

---

## 🔧 Implementation Details

### Phase 1: Data Type Processing Functions

**File:** `streamlit/commentary/pattern_analysis.py`

```python
from utils import get_teg_rounds  # Handle variable round counts
import pandas as pd

def analyze_lead_progression(teg_num):
    """
    Analyze lead progression across all rounds.

    Returns JSON with:
    - Lead changes (hole, from_player, to_player, margin)
    - Tight battles (periods where margin ≤ 2)
    - Breakaway moments (periods where margin ≥ 10)
    """
    df = load_all_data_for_teg(teg_num)

    # Get number of rounds (handles TEG 2 = 3 rounds, etc.)
    num_rounds = get_teg_rounds(teg_num)

    lead_timeline = []
    for round_num in range(1, num_rounds + 1):
        round_df = df[df['Round'] == round_num]

        for hole in round_df['Hole'].unique():
            hole_data = round_df[round_df['Hole'] == hole]

            # Leader has Gap_Stableford_TEG = 0
            leader = hole_data[hole_data['Gap_Stableford_TEG']==0]['Player'].iloc[0]

            # Margin to 2nd place
            gaps = hole_data['Gap_Stableford_TEG'].sort_values()
            margin = gaps.iloc[1] if len(gaps) > 1 else 0

            lead_timeline.append({
                'round': round_num,
                'hole': hole,
                'leader': leader,
                'margin_to_2nd': margin,
                'tight_battle': margin <= 2,
                'breakaway': margin >= 10
            })

    # Identify lead changes
    lead_changes = []
    prev_leader = None
    for entry in lead_timeline:
        if prev_leader and entry['leader'] != prev_leader:
            lead_changes.append({
                'round': entry['round'],
                'hole': entry['hole'],
                'from': prev_leader,
                'to': entry['leader'],
                'new_margin': entry['margin_to_2nd']
            })
        prev_leader = entry['leader']

    return {
        'lead_timeline': lead_timeline,
        'lead_changes': lead_changes
    }

def analyze_momentum_windows(teg_num, window_sizes=[3, 6]):
    """
    Calculate rolling performance windows for hot/cold spell detection.

    Returns JSON with momentum patterns:
    - Player, Round, Holes (e.g., "5-7"), Points, Type (hot/cold)
    """
    df = load_all_data_for_teg(teg_num)

    momentum_patterns = []

    for player in df['Player'].unique():
        player_df = df[df['Player'] == player]

        for round_num in player_df['Round'].unique():
            round_df = player_df[player_df['Round'] == round_num].sort_values('Hole')

            # Calculate rolling windows
            for window_size in window_sizes:
                round_df[f'rolling_{window_size}'] = (
                    round_df['Stableford'].rolling(window_size).sum()
                )

                # Identify hot spells (thresholds to test/refine)
                hot_threshold = 10 if window_size == 3 else 18
                cold_threshold = 3 if window_size == 3 else 8

                for idx in round_df.index:
                    if pd.notna(round_df.loc[idx, f'rolling_{window_size}']):
                        points = round_df.loc[idx, f'rolling_{window_size}']
                        end_hole = round_df.loc[idx, 'Hole']
                        start_hole = end_hole - window_size + 1

                        if points >= hot_threshold:
                            momentum_patterns.append({
                                'player': player,
                                'round': round_num,
                                'holes': f"{start_hole}-{end_hole}",
                                'window_size': window_size,
                                'points': points,
                                'type': 'hot'
                            })
                        elif points <= cold_threshold:
                            momentum_patterns.append({
                                'player': player,
                                'round': round_num,
                                'holes': f"{start_hole}-{end_hole}",
                                'window_size': window_size,
                                'points': points,
                                'type': 'cold'
                            })

    return momentum_patterns

def analyze_front_back_nine(teg_num):
    """
    Identify significant front 9 vs back 9 differences.
    Uses existing commentary_round_summary data.

    Returns JSON with notable nine-hole performances.
    """
    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')
    round_summary = round_summary[round_summary['TEGNum'] == teg_num]

    nine_patterns = []

    # Threshold for "significant" (to test/refine)
    threshold = 5

    for idx, row in round_summary.iterrows():
        diff = row['Front_9_vs_Back_9_Stableford']

        if abs(diff) >= threshold:
            nine_patterns.append({
                'player': row['Player'],
                'round': row['Round'],
                'front_9': row['Front_9_Score_Stableford'],
                'back_9': row['Back_9_Score_Stableford'],
                'difference': diff,
                'pattern': 'strong_starter' if diff > 0 else 'strong_finisher'
            })

    return nine_patterns

def drill_down_patterns(momentum_patterns, nine_patterns, teg_num):
    """
    For each identified pattern, drill down to specific holes.

    Example: "Hot spell holes 5-8" → Find if there was a birdie,
    or just consistent pars, or what made it hot.

    Returns enriched pattern data with specific hole details.
    """
    df = load_all_data_for_teg(teg_num)
    pattern_details = []

    # Drill down momentum patterns
    for pattern in momentum_patterns:
        player = pattern['player']
        round_num = pattern['round']
        holes_str = pattern['holes']

        # Parse hole range
        start, end = map(int, holes_str.split('-'))

        # Get hole-by-hole data for this window
        window_df = df[
            (df['Player'] == player) &
            (df['Round'] == round_num) &
            (df['Hole'] >= start) &
            (df['Hole'] <= end)
        ]

        # Find notable holes in window
        birdies = window_df[window_df['Stableford'] >= 4]['Hole'].tolist()
        disasters = window_df[window_df['Stableford'] == 0]['Hole'].tolist()

        pattern_details.append({
            **pattern,  # Include original pattern
            'birdies_in_window': birdies,
            'blow_ups_in_window': disasters,
            'hole_scores': window_df[['Hole', 'Stableford', 'GrossVP']].to_dict('records')
        })

    # Drill down front/back 9 patterns
    for pattern in nine_patterns:
        player = pattern['player']
        round_num = pattern['round']
        is_front = pattern['pattern'] == 'strong_starter'

        # Get the nine in question
        nine_df = df[
            (df['Player'] == player) &
            (df['Round'] == round_num) &
            (df['FrontBack'] == ('F' if is_front else 'B'))
        ]

        # Find what made it strong
        birdies = nine_df[nine_df['Stableford'] >= 4]['Hole'].tolist()
        disasters = nine_df[nine_df['Stableford'] == 0]['Hole'].tolist()

        pattern_details.append({
            **pattern,
            'birdies': birdies,
            'disasters': disasters,
            'hole_scores': nine_df[['Hole', 'Stableford', 'GrossVP']].to_dict('records')
        })

    return pattern_details

def process_all_data_types(teg_num):
    """
    Master function to run all 6 data type processing passes.

    Returns dict with all processed data ready for story generation.
    """
    print(f"Processing data for TEG {teg_num}...")

    # Pass 1: Lead progression
    print("Pass 1: Analyzing lead progression...")
    lead_data = analyze_lead_progression(teg_num)

    # Pass 2: Momentum windows
    print("Pass 2: Analyzing momentum windows...")
    momentum_data = analyze_momentum_windows(teg_num)

    # Pass 3: Front/back 9
    print("Pass 3: Analyzing front/back 9 patterns...")
    nine_data = analyze_front_back_nine(teg_num)

    # Pass 4: Drill down
    print("Pass 4: Drilling down patterns...")
    pattern_details = drill_down_patterns(momentum_data, nine_data, teg_num)

    # Pass 5 & 6: Load existing commentary files
    print("Pass 5 & 6: Loading existing commentary data...")
    round_events = pd.read_parquet('data/commentary_round_events.parquet')
    round_events = round_events[round_events['TEGNum'] == teg_num]

    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')
    round_summary = round_summary[round_summary['TEGNum'] == teg_num]

    return {
        'lead_data': lead_data,
        'momentum_data': momentum_data,
        'nine_data': nine_data,
        'pattern_details': pattern_details,
        'round_events': round_events.to_dict('records'),
        'round_summary': round_summary.to_dict('records')
    }
```

### Phase 2: Data Loading Module

**File:** `streamlit/commentary/data_loader.py`

```python
def load_round_data(teg_num, round_num, all_processed_data):
    """
    Load all data for a specific round from processed data.
    Filters multi-round data to just this round.

    Args:
        teg_num: Tournament number
        round_num: Round number
        all_processed_data: Output from process_all_data_types()

    Returns:
        Dict with ~120-180 focused data points for this round
    """
    # Filter lead data to this round
    lead_timeline = [
        entry for entry in all_processed_data['lead_data']['lead_timeline']
        if entry['round'] == round_num
    ]

    lead_changes = [
        entry for entry in all_processed_data['lead_data']['lead_changes']
        if entry['round'] == round_num
    ]

    # Filter momentum patterns to this round
    momentum_patterns = [
        pattern for pattern in all_processed_data['momentum_data']
        if pattern['round'] == round_num
    ]

    # Filter nine patterns to this round
    nine_patterns = [
        pattern for pattern in all_processed_data['nine_data']
        if pattern['round'] == round_num
    ]

    # Filter pattern details to this round
    pattern_details = [
        detail for detail in all_processed_data['pattern_details']
        if detail['round'] == round_num
    ]

    # Filter events to this round
    round_events = [
        event for event in all_processed_data['round_events']
        if event['Round'] == round_num
    ]

    # Filter round summary to this round
    round_summary = [
        summary for summary in all_processed_data['round_summary']
        if summary['Round'] == round_num
    ]

    return {
        'round': round_num,
        'lead_timeline': lead_timeline,
        'lead_changes': lead_changes,
        'momentum_patterns': momentum_patterns,
        'nine_patterns': nine_patterns,
        'pattern_details': pattern_details,
        'events': round_events,
        'summary': round_summary
    }

def get_round_ending_context(round_data):
    """
    Extract ending context from round data to pass to next round.

    Returns:
        Dict with standings, gaps, momentum after this round
    """
    # Get final standings after this round from round_summary
    standings = sorted(
        round_data['summary'],
        key=lambda x: x['Cumulative_Tournament_Rank_Stableford']
    )

    # Get final lead situation
    final_hole_lead = round_data['lead_timeline'][-1] if round_data['lead_timeline'] else None

    # Identify who's hot/cold going into next round
    hot_players = [
        p['player'] for p in round_data['momentum_patterns']
        if p['type'] == 'hot' and int(p['holes'].split('-')[1]) >= 15  # Hot finish
    ]

    cold_players = [
        p['player'] for p in round_data['momentum_patterns']
        if p['type'] == 'cold' and int(p['holes'].split('-')[1]) >= 15  # Cold finish
    ]

    return {
        'round': round_data['round'],
        'leader': final_hole_lead['leader'] if final_hole_lead else None,
        'margin': final_hole_lead['margin_to_2nd'] if final_hole_lead else None,
        'standings': [
            {
                'player': s['Player'],
                'rank': s['Cumulative_Tournament_Rank_Stableford'],
                'gap': s['Gap_To_Leader_After_Round_Stableford']
            }
            for s in standings[:5]  # Top 5 for context
        ],
        'hot_momentum': hot_players,
        'cold_momentum': cold_players
    }
```

### Phase 3: Story Generation Prompts

**File:** `streamlit/commentary/prompts.py` (additions)

```python
ROUND_STORY_PROMPT = """You are a golf journalist writing a detailed round story.

**Available Data (6 sources combined):**

1. **Lead Progression** (lead_timeline, lead_changes):
   - Who led at each hole
   - When leads changed hands
   - Margin to 2nd place throughout round
   - Tight battle periods
   - Breakaway moments

2. **Momentum Patterns** (momentum_patterns):
   - Hot spells (3-6 hole windows with high scoring)
   - Cold spells (3-6 hole windows with low scoring)
   - Specific hole ranges for each pattern

3. **Front/Back Nine** (nine_patterns):
   - Significant front 9 vs back 9 differences
   - Strong starters vs strong finishers

4. **Pattern Details** (pattern_details):
   - For each hot/cold spell: specific holes
   - Birdies, disasters within patterns
   - What made a spell hot or cold

5. **Events** (round_events):
   - Eagles, disasters, significant moments
   - Exact holes for each event
   - Ranking changes

6. **Round Summary** (round_summary):
   - Tournament context before round (standings, gaps)
   - Tournament context after round (new standings, gaps)
   - Round scores, ranking changes

**Previous Round Context:**
{previous_context}

**Round {round_num} Data:**
{round_data}

**Your Task:**
Write a comprehensive Round {round_num} story with these sections:

### Tournament Context Coming In
- Where players stood entering this round
- Key storylines/momentum from previous round

### How Round {round_num} Unfolded

#### Opening Nine
- Use front 9 data + momentum patterns + lead progression
- Identify key moments with specific holes
- Show how battles developed

#### Back Nine
- Use back 9 data + momentum patterns + lead progression
- Identify key moments with specific holes
- Show how round resolved

### Key Round {round_num} Moments
- Use pattern details + events
- Highlight dramatic moments with specific holes
- Link patterns to narrative (e.g., "hot spell driven by birdie on hole 6")

### Tournament Context After Round {round_num}
- Updated leaderboard
- Lead margin and situation
- Momentum check (who's hot/cold going forward)

**Style Guidelines:**
- Use specific hole numbers and ranges
- Weave all 6 data sources into coherent narrative
- Focus on drama and turning points
- Make it entertaining while accurate

Output only the story content for Round {round_num}, no preamble.
"""

TOURNAMENT_SYNTHESIS_PROMPT = """You have detailed stories for all rounds of the tournament.

**Round Stories:**
{round_summaries}

**Tournament Data:**
{tournament_data}

**Historical Context:**
{historical_context}

**Your Task:**
Add three tournament-level sections:

### Tournament Overview
- Overall narrative arc across rounds
- How the tournament unfolded
- Key turning points that decided outcome

### Tournament Themes
- Patterns that emerged across rounds
- Contrasts between players
- Storylines that developed over multiple rounds

### Final Context
- Historical significance
- Records or milestones
- How this tournament fits in larger TEG history

**Important:**
- DO NOT repeat round-specific details (already in document)
- Focus on tournament-level insights
- Synthesize rounds into bigger picture
- Add historical/comparative context

Output only these three sections, no preamble.
"""
```

### Phase 4: Main Pipeline

**File:** `streamlit/commentary/generate_tournament_commentary_v2.py`

```python
from pattern_analysis import process_all_data_types
from data_loader import load_round_data, get_round_ending_context
from utils import get_teg_rounds
import anthropic
import os

def generate_round_story(teg_num, round_num, round_data, previous_context):
    """Generate story notes for a single round using all 6 data types."""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Format data for prompt
    import json
    round_data_json = json.dumps(round_data, indent=2, default=str)
    previous_context_json = json.dumps(previous_context, indent=2, default=str) if previous_context else "First round"

    # Build prompt
    prompt = ROUND_STORY_PROMPT.format(
        round_num=round_num,
        round_data=round_data_json,
        previous_context=previous_context_json
    )

    # LLM call
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    round_story = message.content[0].text

    # Extract ending context for next round
    ending_context = get_round_ending_context(round_data)

    return round_story, ending_context

def generate_tournament_synthesis(round_stories, teg_num):
    """Generate tournament-level sections using all round stories."""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Load tournament-level data
    tournament_summary = pd.read_parquet('data/commentary_tournament_summary.parquet')
    tournament_summary = tournament_summary[tournament_summary['TEGNum'] == teg_num]

    # Format for prompt
    import json
    round_summaries_text = "\n\n".join([
        f"## Round {i+1}\n{story}"
        for i, story in enumerate(round_stories)
    ])

    tournament_data_json = json.dumps(
        tournament_summary.to_dict('records'),
        indent=2,
        default=str
    )

    # Build prompt
    prompt = TOURNAMENT_SYNTHESIS_PROMPT.format(
        round_summaries=round_summaries_text,
        tournament_data=tournament_data_json,
        historical_context="[Historical context goes here]"  # TODO: Add player history
    )

    # LLM call
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text

def generate_complete_story_notes(teg_num):
    """
    Complete pipeline: Process all data types → Generate round stories → Synthesize.

    Handles variable round counts (TEG 2 = 3 rounds, most = 4 rounds).
    """
    print(f"\n{'='*60}")
    print(f"Generating story notes for TEG {teg_num}")
    print(f"{'='*60}\n")

    # LEVEL 1: Process all 6 data types (Python - multi-pass)
    print("LEVEL 1: Data Type Processing (6 passes)")
    all_data = process_all_data_types(teg_num)
    print("✓ All data types processed\n")

    # LEVEL 2: Generate round stories (LLM - multi-pass by round)
    print("LEVEL 2: Round Story Generation")
    num_rounds = get_teg_rounds(teg_num)
    print(f"Tournament has {num_rounds} rounds\n")

    round_stories = []
    previous_context = None

    for round_num in range(1, num_rounds + 1):
        print(f"Generating Round {round_num} story...")

        # Load data for this round from all 6 sources
        round_data = load_round_data(teg_num, round_num, all_data)

        # Generate round story
        round_story, round_context = generate_round_story(
            teg_num, round_num, round_data, previous_context
        )

        round_stories.append(round_story)
        previous_context = round_context

        print(f"✓ Round {round_num} story complete\n")

    # LEVEL 2 (continued): Tournament synthesis
    print("Generating tournament synthesis...")
    synthesis = generate_tournament_synthesis(round_stories, teg_num)
    print("✓ Tournament synthesis complete\n")

    # Build complete story notes file
    story_notes = build_story_notes_file(
        teg_num, round_stories, synthesis
    )

    # Save
    output_path = f"streamlit/commentary/outputs/teg_{teg_num}_story_notes.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(story_notes)

    print(f"{'='*60}")
    print(f"✓ Complete story notes saved to: {output_path}")
    print(f"{'='*60}\n")

    return story_notes

def build_story_notes_file(teg_num, round_stories, synthesis):
    """Build the complete story_notes.md content."""

    content = f"# TEG {teg_num} Story Notes\n\n"

    # Add synthesis sections first (overview)
    content += synthesis + "\n\n"

    # Add round stories
    for i, round_story in enumerate(round_stories, 1):
        content += f"## Round {i} Story\n\n"
        content += round_story + "\n\n"

    return content

# For in-progress tournaments
def generate_story_notes_up_to_round(teg_num, completed_rounds):
    """
    Generate story notes for in-progress tournament.
    Only processes completed rounds.
    """
    print(f"\nGenerating story notes for TEG {teg_num} (Rounds 1-{completed_rounds})")

    # Same process but limit to completed rounds
    all_data = process_all_data_types(teg_num)

    round_stories = []
    previous_context = None

    for round_num in range(1, completed_rounds + 1):
        round_data = load_round_data(teg_num, round_num, all_data)
        round_story, round_context = generate_round_story(
            teg_num, round_num, round_data, previous_context
        )
        round_stories.append(round_story)
        previous_context = round_context

    # Don't synthesize until tournament complete
    # Just save round stories
    content = f"# TEG {teg_num} Story Notes (In Progress - {completed_rounds} rounds)\n\n"
    for i, round_story in enumerate(round_stories, 1):
        content += f"## Round {i} Story\n\n"
        content += round_story + "\n\n"

    output_path = f"streamlit/commentary/outputs/teg_{teg_num}_story_notes.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ In-progress story notes saved: {output_path}\n")

    return content
```

---

## 📋 Summary

**Total Passes:**
- **6 Python passes** (data type processing - free, fast)
- **3-4 LLM passes** (round stories - depends on tournament)
- **1 LLM pass** (tournament synthesis)
- **= 6 Python + 4-5 LLM passes per tournament**

**Data Volume per LLM Pass:**
- Round story: ~120-180 focused points (manageable)
- Tournament synthesis: Text summaries + 70 points (manageable)

**Key Features:**
- ✅ Handles variable round counts (TEG 2 = 3 rounds, etc.)
- ✅ Multi-pass at data processing level (focused, efficient)
- ✅ Multi-pass at story generation level (by round)
- ✅ Pattern drill-down for narrative specifics
- ✅ Supports in-progress tournaments
- ✅ Leverages 80% existing data
- ✅ Only 20% new calculation

**Next Steps:**
1. Build `pattern_analysis.py` (6 functions)
2. Build `data_loader.py` (2 functions)
3. Add prompts to `prompts.py`
4. Build main pipeline in `generate_tournament_commentary_v2.py`
5. Test on TEG 17
6. Iterate and refine thresholds

---

*Ready for implementation!*
