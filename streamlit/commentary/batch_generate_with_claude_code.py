"""
Batch generate commentary for all tournaments using Claude Code's built-in API access.
This script loads tournament data and outputs it in a format that Claude Code can process.
"""

from pathlib import Path
import sys
import json
sys.path.insert(0, str(Path(__file__).parent))
from generate_commentary import load_tournament_data

# Configuration
DATA_DIR = Path("data")
OUTPUT_DIR = Path("data/commentary/drafts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define file paths
tournament_summary_path = DATA_DIR / "commentary_tournament_summary.parquet"
round_summary_path = DATA_DIR / "commentary_round_summary.parquet"
events_path = DATA_DIR / "commentary_round_events.parquet"
tournament_streaks_path = DATA_DIR / "commentary_tournament_streaks.parquet"
round_streaks_path = DATA_DIR / "commentary_round_streaks.parquet"
all_data_path = DATA_DIR / "all-data.parquet"
winners_csv_path = DATA_DIR / "teg_winners.csv"

def prepare_tournament_data(teg_num: int):
    """Load and save tournament data for a specific TEG."""
    try:
        data = load_tournament_data(
            teg_num=teg_num,
            tournament_summary_path=str(tournament_summary_path),
            round_summary_path=str(round_summary_path),
            events_path=str(events_path),
            tournament_streaks_path=str(tournament_streaks_path),
            round_streaks_path=str(round_streaks_path),
            all_data_path=str(all_data_path),
            winners_csv_path=str(winners_csv_path)
        )

        # Save data to file
        data_file = OUTPUT_DIR / f"teg_{teg_num}_data.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        return True, len(data['tournament_summary'])
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    # TEG 1 doesn't have data, so start from TEG 2
    start_teg = 2
    end_teg = 17

    print(f"Preparing tournament data for TEG {start_teg} to TEG {end_teg}...")
    print("="*80)

    successful = []
    failed = []

    for teg_num in range(start_teg, end_teg + 1):
        success, result = prepare_tournament_data(teg_num)
        if success:
            print(f"[OK] TEG {teg_num}: Data prepared ({result} players)")
            successful.append(teg_num)
        else:
            print(f"[FAIL] TEG {teg_num}: Failed - {result}")
            failed.append((teg_num, result))

    print("="*80)
    print(f"\nSummary:")
    print(f"  Successful: {len(successful)} tournaments")
    print(f"  Failed: {len(failed)} tournaments")

    if successful:
        print(f"\nData files created for TEG {successful[0]}-{successful[-1]}")
        print(f"Location: {OUTPUT_DIR}")
        print(f"\nReady for Claude Code to generate commentary!")
