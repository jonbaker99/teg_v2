"""
Run TEG 17 commentary generation using Claude Code's built-in API access
"""

import pandas as pd
import json
from pathlib import Path

# Add parent directory to path to import from commentary module
import sys
sys.path.insert(0, str(Path(__file__).parent))

from generate_commentary import load_tournament_data
from prompts import STORY_ARCHITECT_PROMPT, GOLF_JOURNALIST_PROMPT

# File paths
DATA_DIR = Path(r"c:\Users\jonba\Documents\Projects - not on onedrive\teg_v2\data")

tournament_summary_path = DATA_DIR / "commentary_tournament_summary.parquet"
round_summary_path = DATA_DIR / "commentary_round_summary.parquet"
events_path = DATA_DIR / "commentary_round_events.parquet"
tournament_streaks_path = DATA_DIR / "commentary_tournament_streaks.parquet"
round_streaks_path = DATA_DIR / "commentary_round_streaks.parquet"
all_data_path = DATA_DIR / "all-data.parquet"

output_dir = Path(__file__).parent / "outputs"
output_path = output_dir / "teg_17_main_report.md"

# Load tournament data
print("="*80)
print("LOADING TEG 17 DATA")
print("="*80)

tournament_data = load_tournament_data(
    teg_num=17,
    tournament_summary_path=str(tournament_summary_path),
    round_summary_path=str(round_summary_path),
    events_path=str(events_path),
    tournament_streaks_path=str(tournament_streaks_path),
    round_streaks_path=str(round_streaks_path),
    all_data_path=str(all_data_path)
)

# Save the data for Claude Code to process
data_file = output_dir / "teg_17_data.json"
with open(data_file, 'w') as f:
    json.dump(tournament_data, f, indent=2, default=str)

print(f"\nData loaded successfully!")
print(f"Tournament data saved to: {data_file}")
print(f"\nData summary:")
print(f"  - Tournament summary: {len(tournament_data['tournament_summary'])} records")
print(f"  - Round summaries: {len(tournament_data['round_summaries'])} records")
print(f"  - Events: {len(tournament_data['events'])} records")
print(f"  - Tournament streaks: {len(tournament_data['tournament_streaks'])} records")
print(f"  - Round streaks: {len(tournament_data['round_streaks'])} records")
print(f"  - Hole-by-hole: {len(tournament_data['hole_by_hole'])} records")

print("\n" + "="*80)
print("READY FOR CLAUDE CODE TO GENERATE COMMENTARY")
print("="*80)
print("\nClaude Code will now use the prompts to generate the commentary...")
