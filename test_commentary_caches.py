"""
Test script for commentary cache file generation.
Tests update_commentary_caches() function and verifies output files.
"""

import sys
from pathlib import Path

# Add streamlit directory to path so we can import utils
streamlit_dir = Path(__file__).parent / "streamlit"
sys.path.insert(0, str(streamlit_dir))

from utils import (
    update_commentary_caches,
    read_file,
    COMMENTARY_ROUND_EVENTS_PARQUET,
    COMMENTARY_ROUND_SUMMARY_PARQUET
)
import pandas as pd

def main():
    print("Testing commentary cache generation...")
    print("=" * 80)

    try:
        # Generate the commentary cache files
        print("\n1. Generating commentary cache files...")
        update_commentary_caches()

        # Check if files were created
        events_path = Path(COMMENTARY_ROUND_EVENTS_PARQUET)
        summary_path = Path(COMMENTARY_ROUND_SUMMARY_PARQUET)

        if not events_path.exists():
            print(f"X Error: {COMMENTARY_ROUND_EVENTS_PARQUET} was not created")
            return 1

        if not summary_path.exists():
            print(f"X Error: {COMMENTARY_ROUND_SUMMARY_PARQUET} was not created")
            return 1

        print(f"   [OK] Both files created successfully")

        # Load and verify the events file
        print(f"\n2. Verifying {COMMENTARY_ROUND_EVENTS_PARQUET}...")
        events_df = read_file(COMMENTARY_ROUND_EVENTS_PARQUET)
        print(f"   - Rows: {len(events_df)}")
        print(f"   - Columns: {len(events_df.columns)}")
        print(f"   - Unique event types: {events_df['Event'].nunique()}")
        print(f"   - Event types: {events_df['Event'].unique().tolist()}")

        # Load and verify the summary file
        print(f"\n3. Verifying {COMMENTARY_ROUND_SUMMARY_PARQUET}...")
        summary_df = read_file(COMMENTARY_ROUND_SUMMARY_PARQUET)
        print(f"   - Rows: {len(summary_df)}")
        print(f"   - Columns: {len(summary_df.columns)}")
        print(f"   - TEGs covered: {summary_df['TEGNum'].nunique()}")
        print(f"   - Players: {summary_df['Player'].nunique()}")

        # Check for key columns in summary
        key_cols = ['Lead_Gained_Count_Gross', 'Lead_Lost_Count_Gross',
                   'Lead_Gained_Count_Stableford', 'Lead_Lost_Count_Stableford',
                   'Round_Score_Sc', 'Front_9_Score_Sc', 'Back_9_Score_Sc']

        missing_cols = [col for col in key_cols if col not in summary_df.columns]
        if missing_cols:
            print(f"\n   X Error: Missing expected columns: {missing_cols}")
            return 1
        else:
            print(f"   [OK] All expected columns present")

        # Show some sample statistics
        print(f"\n4. Sample statistics from summary:")
        print(f"   - Average lead gains (Stableford): {summary_df['Lead_Gained_Count_Stableford'].mean():.2f}")
        print(f"   - Average round score: {summary_df['Round_Score_Sc'].mean():.1f}")
        print(f"   - Average eagles per round: {summary_df['Eagles_Count'].mean():.2f}")
        print(f"   - Average birdies per round: {summary_df['Birdies_Count'].mean():.2f}")

        # Show file sizes
        print(f"\n5. File sizes:")
        events_size = events_path.stat().st_size / 1024
        summary_size = summary_path.stat().st_size / 1024
        print(f"   - {COMMENTARY_ROUND_EVENTS_PARQUET}: {events_size:.1f} KB")
        print(f"   - {COMMENTARY_ROUND_SUMMARY_PARQUET}: {summary_size:.1f} KB")

        print("\n" + "=" * 80)
        print("[SUCCESS] Commentary cache files generated and verified successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\nX Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
