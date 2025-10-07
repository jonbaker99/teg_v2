# Round Report System - Implementation TODO

**IMPORTANT: Always keep this file up to date as actions are completed**

## Project Goal
Build a round-level report generation system for live tournament analysis that:
- Generates reports after each round completes
- Includes forward-looking analysis (what's at stake, what's needed to win)
- Uses LLM for storyline identification and report writing
- Follows proven tournament report architecture

## Status: Planning Complete ✓

---

## Agreed Final Data Stack

### Input Data (All Available for Round N):
1. **Round Summary Data** (`commentary_round_summary.parquet`)
   - Round scores (gross, stableford, vs par)
   - Cumulative tournament standings after this round
   - Gaps to leader
   - Round ranks
   - Front 9 / Back 9 splits

2. **Hole-by-Hole Data** (`all-scores.parquet` filtered to this round)
   - Every shot, every hole
   - Scoring (gross, stableford, vs par)
   - Hole difficulty (par, stroke index)
   - Position changes hole-by-hole

3. **Events Data** (`commentary_round_events.parquet` filtered to this round)
   - Eagles, birdies, blow-ups
   - Lead changes
   - Significant moments
   - Rank changes

4. **Streaks Within Round** (from streak analysis functions)
   - Birdie runs
   - Bogey-free stretches
   - Disaster sequences
   - All within this single round

5. **Records & PBs Set This Round** (from pattern_analysis functions)
   - All-time records
   - Personal bests/worsts
   - Course records

6. **Tournament Context** (critical for live analysis)
   - Standings BEFORE round (from previous round or tournament start)
   - Standings AFTER round
   - Gap changes
   - Number of rounds remaining
   - Total tournament holes played/remaining

7. **Round Metadata**
   - Date
   - Course name, par, details
   - Weather (if available)
   - Round number / total rounds

### Data Excluded (Too Granular or Not Useful):
- Player pairings (not tracked)
- Weather data (not systematically recorded)
- Intra-round leaderboard (hole-by-hole positions calculated on-demand only)

---

## Implementation Phases

### ✅ Phase 1: Planning & Design (COMPLETE)
- [x] Analyze existing tournament report system
- [x] Define round report requirements
- [x] Agree data stack
- [x] Create implementation plan

### Phase 2: Data Pipeline (NEXT)
- [ ] Create `round_data_loader.py` in `streamlit/commentary/`
  - [ ] Function: `load_round_report_data(teg_num, round_num)` - Main data assembly
  - [ ] Function: `calculate_tournament_projections(teg_num, round_num)` - Forward-looking math
  - [ ] Function: `analyze_round_difficulty(teg_num, round_num)` - Course/hole stats
- [ ] Create `round_pattern_analysis.py` in `streamlit/commentary/`
  - [ ] Function: `identify_round_momentum_shifts(round_data)` - Key turning points
  - [ ] Function: `analyze_position_changes(round_data)` - Who gained/lost ground
  - [ ] Test data pipeline with TEG 17, Round 2

### Phase 3: LLM Prompts
- [ ] Add to `prompts.py`:
  - [ ] `ROUND_STORY_NOTES_PROMPT` - Structured notes generation (similar to tournament version)
  - [ ] `ROUND_REPORT_PROMPT` - Full narrative report with forward-looking analysis
- [ ] Define story notes structure for rounds
- [ ] Test prompts with sample data

### Phase 4: Report Generator
- [ ] Create `generate_round_report.py` in `streamlit/commentary/`
  - [ ] Function: `generate_round_story_notes(teg_num, round_num)` - LLM story notes
  - [ ] Function: `generate_round_narrative_report(teg_num, round_num)` - LLM full report
  - [ ] Function: `build_round_report_file(teg_num, round_num)` - Assemble complete output
  - [ ] CLI interface for running reports
- [ ] Test with multiple rounds/tournaments

### Phase 5: Testing & Refinement
- [ ] Generate reports for TEG 17 rounds 1-3 (in-progress tournament simulation)
- [ ] Review output quality
- [ ] Refine prompts based on output
- [ ] Document usage

### Phase 6: Integration (Optional)
- [ ] Add Streamlit UI for viewing round reports
- [ ] Add to existing pages (latest_round.py or new page)

---

## Key Design Decisions

### Report Structure (agreed):
```
# Round [N] Report - TEG [X]
**Course • Date**

## Round Summary
[2-3 paragraphs: What happened, who won the round, key moments]

## How It Unfolded
[Chronological narrative: Front 9 → Back 9 → Key holes and moments]

## Standings After Round [N]
**Trophy (Stableford):** [Player] leads by [X] points
**Green Jacket (Gross):** [Player] leads by [X] strokes
[Table with top 5-6 positions]

## What's At Stake
[Forward-looking analysis with [Y] rounds remaining:
- What each contender needs to do
- Gap analysis (is it catchable?)
- Key matchups to watch
- Spoon battle if relevant]

## Records & Stats
[Notable achievements from this round]

## Player Summaries
[2-3 sentences per player in the round]
```

### LLM Strategy:
- **Story Notes Generation** (LLM Pass 1): Identify 3-5 key storylines from data, structured bullets
- **Report Generation** (LLM Pass 2): Transform notes into narrative with forward-looking analysis
- Use prompt caching for efficiency (similar to tournament system)

### File Organization:
```
streamlit/commentary/
├── round_data_loader.py          [NEW - Round data assembly]
├── round_pattern_analysis.py     [NEW - Round-specific patterns]
├── generate_round_report.py      [NEW - Main generator with CLI]
├── prompts.py                     [UPDATE - Add round prompts]
├── pattern_analysis.py            [REUSE - Records/PBs functions]
└── data_loader.py                 [REUSE - Some helper functions]

data/commentary/round_reports/
├── teg_17_round_1_report.md
├── teg_17_round_2_report.md
└── ...
```

---

## Notes & Decisions Log

**2025-01-07**: Initial planning
- Agreed on live tournament focus
- Forward-looking analysis is key differentiator
- Single report format (no brief/full variants)
- Reuse tournament report architecture patterns

