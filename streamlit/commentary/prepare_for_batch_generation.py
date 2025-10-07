"""
Prepare all tournament data in condensed format for Claude Code batch generation.
Creates summary files that Claude Code can process efficiently.
"""

from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent))
from generate_commentary import load_tournament_data

# Configuration
DATA_DIR = Path("data")
OUTPUT_DIR = Path("data/commentary/drafts")

# File paths
tournament_summary_path = DATA_DIR / "commentary_tournament_summary.parquet"
round_summary_path = DATA_DIR / "commentary_round_summary.parquet"
events_path = DATA_DIR / "commentary_round_events.parquet"
tournament_streaks_path = DATA_DIR / "commentary_tournament_streaks.parquet"
round_streaks_path = DATA_DIR / "commentary_round_streaks.parquet"
all_data_path = DATA_DIR / "all-data.parquet"
winners_csv_path = DATA_DIR / "teg_winners.csv"

def condense_tournament_data(teg_num: int):
    """Load and condense tournament data for efficient processing."""
    try:
        # Load full data
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

        # Create condensed version - remove hole-by-hole and limit events/streaks
        condensed = {
            'teg_num': data['teg_num'],
            'tournament_summary': data['tournament_summary'],
            'round_summaries': data['round_summaries'],
            'events': data['events'][:20] if len(data.get('events', [])) > 20 else data.get('events', []),
            'tournament_streaks': data.get('tournament_streaks', []),
            'round_streaks': data.get('round_streaks', [])[:10] if len(data.get('round_streaks', [])) > 10 else data.get('round_streaks', []),
            'player_info': data.get('player_info', {})
        }

        # Save condensed version
        output_file = OUTPUT_DIR / f"teg_{teg_num}_condensed.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(condensed, f, indent=2, default=str)

        return True, len(condensed['tournament_summary'])

    except Exception as e:
        return False, str(e)


def create_generation_queue():
    """Create a queue file listing all tournaments to process."""
    start_teg = 3  # TEG 2 already done
    end_teg = 17

    queue = []
    for teg_num in range(start_teg, end_teg + 1):
        success, result = condense_tournament_data(teg_num)
        if success:
            queue.append({
                'teg_num': teg_num,
                'players': result,
                'status': 'pending'
            })
            print(f"[OK] TEG {teg_num}: Data condensed ({result} players)")
        else:
            print(f"[FAIL] TEG {teg_num}: {result}")

    # Save queue
    queue_file = OUTPUT_DIR / "generation_queue.json"
    with open(queue_file, 'w', encoding='utf-8') as f:
        json.dump(queue, f, indent=2)

    print(f"\n{len(queue)} tournaments ready for generation")
    print(f"Queue saved to: {queue_file}")

    return queue


if __name__ == "__main__":
    print("Preparing tournament data for batch generation...")
    print("="*80)
    queue = create_generation_queue()
    print("="*80)
    print("\nReady for Claude Code to generate commentary for TEG 3-17!")
