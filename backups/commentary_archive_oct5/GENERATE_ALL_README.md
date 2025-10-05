# Tournament Commentary Generation - Complete Guide

## Status

✅ **TEG 2**: All 3 reports generated
- Main report: `outputs/teg_2_main_report.md`
- Brief summary: `outputs/teg_2_brief_summary.md`
- Player profiles: `outputs/teg_2_player_profiles.md`

⏳ **TEG 3-17**: Data prepared and ready for generation

## How to Generate Remaining Tournaments

### Option 1: Ask Claude Code to Continue
Simply ask Claude Code to continue generating commentary for the remaining tournaments (TEG 3-17). The condensed data files are ready at:
- `outputs/teg_3_condensed.json` through `outputs/teg_17_condensed.json`

### Option 2: Use the Python Script with API Key
If you have an Anthropic API key, use the original batch generation script:

```bash
# Set your API key
export ANTHROPIC_API_KEY="your-key-here"  # or set in environment

# Run the batch generator
python streamlit/commentary/generate_all_tournaments.py
```

This will generate all three report types for each tournament automatically.

## Data Files

### Condensed Data (for efficient processing)
- TEG 2-17: `outputs/teg_X_condensed.json`
- Includes: tournament summary, round summaries, key events, streaks, player info
- Excludes: Hole-by-hole data (too large)

### Full Data (for reference)
- TEG 2-17: `outputs/teg_X_data.json`
- Includes: All data including hole-by-hole details

## Report Types Generated

For each tournament, three reports are created:

1. **Main Report** (`teg_X_main_report.md`)
   - Full narrative article
   - ~1000-1500 words
   - Entertaining, dramatic storytelling

2. **Brief Summary** (`teg_X_brief_summary.md`)
   - 2-3 paragraph summary
   - Key storylines and results
   - Quick-read format

3. **Player Profiles** (`teg_X_player_profiles.md`)
   - Individual player summaries
   - 2-4 sentences per player
   - Tournament highlights for each participant

## Generation Queue

A queue file tracks generation status:
- `outputs/generation_queue.json`
- Lists all pending tournaments
- Can be used to track progress

## Prompts Used

All prompts are defined in `prompts.py`:
- `STORY_ARCHITECT_PROMPT`: Creates story blueprint
- `GOLF_JOURNALIST_PROMPT`: Writes main article
- `BRIEF_SUMMARY_PROMPT`: Creates brief summary
- `PLAYER_PROFILES_PROMPT`: Generates player profiles
