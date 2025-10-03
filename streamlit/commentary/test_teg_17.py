"""
Test script to generate TEG 17 commentary
"""

import os
from generate_commentary import generate_tournament_commentary

# File paths
DATA_DIR = r"c:\Users\jonba\Documents\Projects - not on onedrive\teg_v2\data"

tournament_summary_path = os.path.join(DATA_DIR, "commentary_tournament_summary.parquet")
round_summary_path = os.path.join(DATA_DIR, "commentary_round_summary.parquet")
events_path = os.path.join(DATA_DIR, "commentary_round_events.parquet")
tournament_streaks_path = os.path.join(DATA_DIR, "commentary_tournament_streaks.parquet")
round_streaks_path = os.path.join(DATA_DIR, "commentary_round_streaks.parquet")
all_data_path = os.path.join(DATA_DIR, "all-data.parquet")

output_path = r"c:\Users\jonba\Documents\Projects - not on onedrive\teg_v2\streamlit\commentary\outputs\teg_17_main_report.md"

# Get API key from environment
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY environment variable not set")

# Generate commentary
print("="*80)
print("GENERATING TEG 17 TOURNAMENT COMMENTARY")
print("="*80)

result = generate_tournament_commentary(
    teg_num=17,
    tournament_summary_path=tournament_summary_path,
    round_summary_path=round_summary_path,
    api_key=api_key,
    events_path=events_path,
    tournament_streaks_path=tournament_streaks_path,
    round_streaks_path=round_streaks_path,
    all_data_path=all_data_path,
    output_path=output_path
)

print("\n" + "="*80)
print("STORY BLUEPRINT:")
print("="*80)
print(result['blueprint'])

print("\n" + "="*80)
print("FINAL ARTICLE:")
print("="*80)
print(result['article'])

print(f"\n\nArticle saved to: {output_path}")
