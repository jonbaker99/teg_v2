"""Condense TEG 17 data to essentials only"""
import json
from pathlib import Path

# Load full data
data_file = Path(__file__).parent / "outputs" / "teg_17_data.json"
with open(data_file) as f:
    data = json.load(f)

# Create condensed version
condensed = {
    'teg_num': data['teg_num'],
    'tournament_summary': data['tournament_summary'],  # Already filtered
    'round_summaries': data['round_summaries'],  # Already filtered
    'events': data['events'][:20] if len(data['events']) > 20 else data['events'],  # Top 20 events
    'tournament_streaks': data['tournament_streaks'][:15] if len(data['tournament_streaks']) > 15 else data['tournament_streaks'],  # Top 15
    'round_streaks': data['round_streaks'][:20] if len(data['round_streaks']) > 20 else data['round_streaks'],  # Top 20
    # Skip hole-by-hole for now - too much data
    'hole_by_hole_summary': f"{len(data['hole_by_hole'])} hole-by-hole records available (omitted for brevity)"
}

# Save condensed version
output_file = Path(__file__).parent / "outputs" / "teg_17_data_condensed.json"
with open(output_file, 'w') as f:
    json.dump(condensed, f, indent=2, default=str)

print(f"Condensed data saved to: {output_file}")
print(f"Original size: {len(json.dumps(data))} chars")
print(f"Condensed size: {len(json.dumps(condensed))} chars")
