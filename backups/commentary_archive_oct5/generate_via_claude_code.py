"""
Generate commentary via Claude Code's API access
"""

import json
from pathlib import Path

# Load the prompts
import sys
sys.path.insert(0, str(Path(__file__).parent))
from prompts import STORY_ARCHITECT_PROMPT, GOLF_JOURNALIST_PROMPT

# Load tournament data
data_file = Path(__file__).parent / "outputs" / "teg_17_data.json"
with open(data_file) as f:
    tournament_data = json.load(f)

# Format for output
data_summary = json.dumps(tournament_data, indent=2)

# Print instructions for Claude Code
print("="*80)
print("STAGE 2: STORY ARCHITECT")
print("="*80)
print("\nPrompt:")
print(STORY_ARCHITECT_PROMPT)
print("\n" + "="*80)
print("\nTournament Data:")
print(data_summary[:2000] + "..." if len(data_summary) > 2000 else data_summary)
print("\n" + "="*80)
print("\nCLAUDE CODE: Please use the STORY_ARCHITECT_PROMPT above with the tournament")
print("data to create a story blueprint, then use the GOLF_JOURNALIST_PROMPT to write")
print("the final article.")
print("="*80)
