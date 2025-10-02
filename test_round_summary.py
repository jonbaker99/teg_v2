"""
Test script for the create_round_summary function.
This script tests the round summary creation and outputs results to test_round_info.csv
"""

import sys
from pathlib import Path

# Add streamlit directory to path so we can import utils
streamlit_dir = Path(__file__).parent / "streamlit"
sys.path.insert(0, str(streamlit_dir))

from utils import create_round_summary
import pandas as pd

def main():
    print("Testing create_round_summary function...")
    print("-" * 80)

    try:
        # Call the function
        print("\n1. Loading data and creating round summary...")
        summary_df = create_round_summary()

        print(f"\n2. Summary created successfully!")
        print(f"   - Total rows: {len(summary_df)}")
        print(f"   - Total columns: {len(summary_df.columns)}")
        print(f"   - TEGs covered: {summary_df['TEGNum'].nunique()}")
        print(f"   - Players: {summary_df['Player'].nunique()}")

        # Show column names
        print(f"\n3. Columns in summary:")
        for i, col in enumerate(summary_df.columns, 1):
            print(f"   {i:2d}. {col}")

        # Show sample data
        print(f"\n4. Sample data (first 3 rows):")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(summary_df.head(3).to_string())

        # Show some statistics
        print(f"\n5. Sample statistics:")
        print(f"   - Rounds per player: {summary_df.groupby('Player').size().describe()}")
        print(f"\n   - Average eagles per round: {summary_df['Eagles_Count'].mean():.2f}")
        print(f"   - Average birdies per round: {summary_df['Birdies_Count'].mean():.2f}")
        print(f"   - Average pars or better per round: {summary_df['Pars_Or_Better_Count'].mean():.2f}")

        # Save to CSV
        output_file = "test_round_info.csv"
        print(f"\n6. Saving to {output_file}...")
        summary_df.to_csv(output_file, index=False)
        print(f"   [OK] Saved successfully!")

        # Show a specific example round in detail
        print(f"\n7. Example round detail (TEG 10, Round 1, first player):")
        example = summary_df[(summary_df['TEGNum'] == 10) & (summary_df['Round'] == 1)].iloc[0]
        for col in summary_df.columns:
            print(f"   {col}: {example[col]}")

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
