"""
Test script for complete commentary cache system including streaks
"""

import sys
import os
sys.path.append('streamlit')

from utils import (
    update_commentary_caches,
    COMMENTARY_ROUND_EVENTS_PARQUET,
    COMMENTARY_ROUND_SUMMARY_PARQUET,
    COMMENTARY_TOURNAMENT_SUMMARY_PARQUET,
    COMMENTARY_ROUND_STREAKS_PARQUET,
    COMMENTARY_TOURNAMENT_STREAKS_PARQUET
)
import pandas as pd

def main():
    print("=" * 80)
    print("TESTING COMPLETE COMMENTARY CACHE SYSTEM (INCLUDING STREAKS)")
    print("=" * 80)

    # Run the update function
    print("\n[1/2] Running update_commentary_caches()...")
    update_commentary_caches()

    print(f"\n[OK] Function completed successfully!")

    # Verify all five files exist and check content
    print("\n[2/2] Verifying cache files:")
    print("-" * 80)

    cache_files = [
        ("Round Events", COMMENTARY_ROUND_EVENTS_PARQUET),
        ("Round Summary", COMMENTARY_ROUND_SUMMARY_PARQUET),
        ("Tournament Summary", COMMENTARY_TOURNAMENT_SUMMARY_PARQUET),
        ("Round Streaks", COMMENTARY_ROUND_STREAKS_PARQUET),
        ("Tournament Streaks", COMMENTARY_TOURNAMENT_STREAKS_PARQUET)
    ]

    for name, file_path in cache_files:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / 1024  # KB
            df = pd.read_parquet(file_path)
            print(f"\n   [OK] {name} ({file_path})")
            print(f"      Size: {file_size:.1f} KB")
            print(f"      Rows: {len(df)}")
            print(f"      Columns: {len(df.columns)}")
            if len(df.columns) <= 10:
                print(f"      Column names: {', '.join(df.columns.tolist())}")
            else:
                print(f"      Column names: {', '.join(df.columns[:10].tolist())}...")
        else:
            print(f"\n   [ERROR] File not found: {file_path}")

    # Display detailed statistics for streak files
    print("\n" + "=" * 80)
    print("DETAILED STREAK STATISTICS")
    print("=" * 80)

    # Round Streaks
    round_streaks_df = pd.read_parquet(COMMENTARY_ROUND_STREAKS_PARQUET)
    print(f"\nRound Streaks ({COMMENTARY_ROUND_STREAKS_PARQUET}):")
    print(f"   Total records: {len(round_streaks_df)}")
    print(f"   Rounds covered: {round_streaks_df['Round'].nunique()}")
    print(f"   TEGs covered: {round_streaks_df['TEGNum'].nunique()}")
    print(f"   Players: {round_streaks_df['Player'].nunique()}")
    print(f"   Streak types: {round_streaks_df['Streak_Type'].nunique()}")
    print(f"   Unique streak types:")
    for streak_type in sorted(round_streaks_df['Streak_Type'].unique()):
        count = (round_streaks_df['Streak_Type'] == streak_type).sum()
        print(f"      {streak_type}: {count} records")

    # Sample: Best round streak (Pars or Better)
    best_pars = round_streaks_df[round_streaks_df['Streak_Type'] == 'Pars or Better'].nlargest(1, 'Max_Streak')
    if len(best_pars) > 0:
        print(f"\n   Best round streak (Pars or Better):")
        print(f"      {best_pars['Player'].values[0]} - {best_pars['TEG'].values[0]} Round {best_pars['Round'].values[0]}: {best_pars['Max_Streak'].values[0]} holes")
        print(f"      Location: {best_pars['Location'].values[0]}")

    # Tournament Streaks
    print(f"\n" + "-" * 80)
    tournament_streaks_df = pd.read_parquet(COMMENTARY_TOURNAMENT_STREAKS_PARQUET)
    print(f"\nTournament Streaks ({COMMENTARY_TOURNAMENT_STREAKS_PARQUET}):")
    print(f"   Total records: {len(tournament_streaks_df)}")
    print(f"   TEGs covered: {tournament_streaks_df['TEGNum'].nunique()}")
    print(f"   Players: {tournament_streaks_df['Player'].nunique()}")
    print(f"   Streak types: {tournament_streaks_df['Streak_Type'].nunique()}")
    print(f"   Unique streak types:")
    for streak_type in sorted(tournament_streaks_df['Streak_Type'].unique()):
        count = (tournament_streaks_df['Streak_Type'] == streak_type).sum()
        print(f"      {streak_type}: {count} records")

    # Sample: Best tournament streak (Pars or Better)
    best_pars_teg = tournament_streaks_df[tournament_streaks_df['Streak_Type'] == 'Pars or Better'].nlargest(1, 'Max_Streak')
    if len(best_pars_teg) > 0:
        print(f"\n   Best tournament streak (Pars or Better):")
        print(f"      {best_pars_teg['Player'].values[0]} - {best_pars_teg['TEG'].values[0]}: {best_pars_teg['Max_Streak'].values[0]} holes")
        print(f"      Location: {best_pars_teg['Location'].values[0]}")

    # Sample: Worst tournament streak (Over Par)
    worst_par = tournament_streaks_df[tournament_streaks_df['Streak_Type'] == 'Over Par'].nlargest(1, 'Max_Streak')
    if len(worst_par) > 0:
        print(f"\n   Worst tournament streak (Over Par):")
        print(f"      {worst_par['Player'].values[0]} - {worst_par['TEG'].values[0]}: {worst_par['Max_Streak'].values[0]} holes")
        print(f"      Location: {worst_par['Location'].values[0]}")

    print("\n" + "=" * 80)
    print("SUMMARY OF ALL COMMENTARY FILES")
    print("=" * 80)

    total_size = sum(os.path.getsize(f[1]) for f in cache_files if os.path.exists(f[1])) / 1024
    print(f"\nTotal size of all commentary cache files: {total_size:.1f} KB")
    print(f"\nFile breakdown:")
    for name, file_path in cache_files:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / 1024
            df = pd.read_parquet(file_path)
            print(f"   {name}: {len(df)} rows, {len(df.columns)} columns, {file_size:.1f} KB")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nAll five commentary cache files are ready for use by the commentary engine!")
    print("Files will auto-update when data is added or deleted.")

if __name__ == "__main__":
    main()
