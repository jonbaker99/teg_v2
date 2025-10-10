"""
Build complete player dictionary from template + TEG history data
"""

import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import load_all_data, read_file
from utils_win_tables import summarise_teg_wins
from player_info_template import PLAYER_INFO

# Load TEG data
print("Loading TEG data...")
all_data = load_all_data(exclude_incomplete_tegs=True, exclude_teg_50=True)

# IMPORTANT: Load winners from CSV (source of truth), not calculated from scores
# This is because some tournaments awarded trophies on a different basis
print("Loading TEG winners from data/teg_winners.csv...")
winners_csv = read_file('data/teg_winners.csv')

# Map CSV columns to expected format
winners = winners_csv.rename(columns={
    'TEG Trophy': 'TEG Trophy',
    'Green Jacket': 'Green Jacket',
    'HMM Wooden Spoon': 'HMM Wooden Spoon'
})[['TEG', 'TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon']]

competitions = ['TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon']

# Build TEG history for each player
player_teg_history = {}

for comp in competitions:
    summary = summarise_teg_wins(winners, comp)

    for _, row in summary.iterrows():
        player = row['Player']
        wins = row['Wins']
        tegs = row['TEGs']

        if player not in player_teg_history:
            player_teg_history[player] = {
                'teg_trophy_wins_total': 0,
                'green_jacket_wins_total': 0,
                'wooden_spoons_total': 0,
                'teg_trophy_tegs_total': [],
                'green_jacket_tegs_total': [],
                'wooden_spoon_tegs_total': []
            }

        if comp == 'TEG Trophy':
            player_teg_history[player]['teg_trophy_wins_total'] = wins
            player_teg_history[player]['teg_trophy_tegs_total'] = tegs
        elif comp == 'Green Jacket':
            player_teg_history[player]['green_jacket_wins_total'] = wins
            player_teg_history[player]['green_jacket_tegs_total'] = tegs
        elif comp == 'HMM Wooden Spoon':
            player_teg_history[player]['wooden_spoons_total'] = wins
            player_teg_history[player]['wooden_spoon_tegs_total'] = tegs

# Calculate tournaments played for each player
tournaments_played = all_data.groupby('Player')['TEGNum'].nunique().to_dict()

# Combine everything into final dictionary
# NOTE: These win counts are CAREER TOTALS across all TEGs
# The commentary generation code uses teg_winners.csv to calculate wins BEFORE each tournament
COMPLETE_PLAYER_INFO = {}

for player, info in PLAYER_INFO.items():
    COMPLETE_PLAYER_INFO[player] = {
        **info,  # Personal info
        'tournaments_played': tournaments_played.get(player, 0),
        **player_teg_history.get(player, {
            'teg_trophy_wins_total': 0,
            'green_jacket_wins_total': 0,
            'wooden_spoons_total': 0,
            'teg_trophy_tegs_total': [],
            'green_jacket_tegs_total': [],
            'wooden_spoon_tegs_total': []
        })
    }

# Print summary
print("\nPlayer Dictionary Built Successfully!\n")
print("="*80)
for player, data in COMPLETE_PLAYER_INFO.items():
    print(f"\n{player} ({data.get('what_people_call_them', player)})")
    print(f"  From: {data.get('where_theyre_from', 'Unknown')}")
    print(f"  Lives: {data.get('where_they_live', 'Unknown')}")
    print(f"  Tournaments: {data['tournaments_played']}")
    print(f"  TEG Trophies (total): {data['teg_trophy_wins_total']}")
    print(f"  Green Jackets (total): {data['green_jacket_wins_total']}")
    print(f"  Wooden Spoons (total): {data['wooden_spoons_total']}")
    if data.get('low_level_facts'):
        print(f"  Facts: {', '.join(data['low_level_facts'][:2])}")  # First 2 only

print("\n" + "="*80)
print("\nDictionary saved to player_dictionary.py")

# Save to file
with open(Path(__file__).parent / "player_dictionary.py", 'w') as f:
    f.write('"""\nComplete Player Dictionary for TEG Commentary\n\n')
    f.write('Combined player information and TEG history.\n')
    f.write('Generated automatically from player_info_template.py and TEG data.\n')
    f.write('"""\n\n')
    f.write('PLAYER_DICTIONARY = ')
    f.write(repr(COMPLETE_PLAYER_INFO))
    f.write('\n')

print("\nTo use: from player_dictionary import PLAYER_DICTIONARY")
