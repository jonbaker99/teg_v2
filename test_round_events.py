"""Test script for the `create_round_events` function.

This script tests the creation of round events and outputs the results to a
CSV file for verification. It performs the following steps:
1.  Calls the `create_round_events` function to generate the events log.
2.  Verifies the created events log and prints summary statistics.
3.  Displays sample data for different types of events (position changes,
    scoring achievements).
4.  Saves the complete events log to `test_round_events.csv`.
"""
import sys
from pathlib import Path

# Add streamlit directory to path so we can import utils
streamlit_dir = Path(__file__).parent / "streamlit"
sys.path.insert(0, str(streamlit_dir))

from utils import create_round_events
import pandas as pd

def main():
    print("Testing create_round_events function...")
    print("-" * 80)

    try:
        # Call the function
        print("\n1. Loading data and creating round events log...")
        events_df = create_round_events()

        print(f"\n2. Events log created successfully!")
        print(f"   - Total event occurrences: {len(events_df)}")
        print(f"   - Unique event types: {events_df['Event'].nunique()}")
        print(f"   - TEGs covered: {events_df['TEGNum'].nunique()}")
        print(f"   - Players: {events_df['Player'].nunique()}")

        # Show event type breakdown
        print(f"\n3. Event type breakdown:")
        event_counts = events_df['Event'].value_counts().sort_values(ascending=False)
        for event_type, count in event_counts.items():
            print(f"   - {event_type}: {count}")

        # Show sample data
        print(f"\n4. Sample events (first 5 rows):")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(events_df.head(5).to_string())

        # Show position change events
        print(f"\n5. Sample position change events:")
        position_events = events_df[events_df['Event'].str.contains('Lead|Bottom')]
        if len(position_events) > 0:
            print(position_events[['TEG', 'Round', 'Hole', 'Player', 'Event',
                                  'Rank_Gross_Before', 'Rank_Gross_After',
                                  'Rank_Stableford_Before', 'Rank_Stableford_After']].head(10).to_string())
        else:
            print("   No position change events found")

        # Show scoring events
        print(f"\n6. Sample scoring achievement events:")
        scoring_events = events_df[events_df['Event'].isin(['Eagle', 'Birdie', 'Hole in One'])]
        if len(scoring_events) > 0:
            print(scoring_events[['TEG', 'Round', 'Hole', 'Player', 'Event', 'Par', 'Sc', 'GrossVP', 'Metric']].head(10).to_string())
        else:
            print("   No eagles/birdies/holes-in-one found")

        # Check final hole flag
        print(f"\n7. Final hole events:")
        final_hole_events = events_df[events_df['Final_Hole_Flag'] == True]
        print(f"   - Events on hole 18: {len(final_hole_events)}")
        print(f"   - Percentage of total: {len(final_hole_events) / len(events_df) * 100:.1f}%")

        # Save to CSV
        output_file = "test_round_events.csv"
        print(f"\n8. Saving to {output_file}...")
        events_df.to_csv(output_file, index=False)
        print(f"   [OK] Saved successfully!")

        # Show a specific interesting event
        print(f"\n9. Example lead change event:")
        lead_changes = events_df[events_df['Event'].str.contains('Took Lead')]
        if len(lead_changes) > 0:
            example = lead_changes.iloc[0]
            print(f"   {example['Player']} - {example['Event']}")
            print(f"   TEG {example['TEGNum']}, Round {example['Round']}, Hole {example['Hole']}")
            print(f"   Rank before: Gross={example['Rank_Gross_Before']}, Stableford={example['Rank_Stableford_Before']}")
            print(f"   Rank after: Gross={example['Rank_Gross_After']}, Stableford={example['Rank_Stableford_After']}")

        print("\n" + "=" * 80)
        print("[SUCCESS] Test completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\nX Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
