"""Test script for the complete commentary cache system.

This script tests the `update_commentary_caches()` function and verifies all
three of its output files to ensure that the entire commentary cache
generation process is working correctly. It performs the following steps:
1.  Generates the commentary cache files.
2.  Checks if all three expected Parquet files were created.
3.  Loads and verifies the content of each file.
4.  Displays summary statistics and interesting findings from the generated
    data.
"""
import sys
import os
sys.path.append('streamlit')

from utils import update_commentary_caches, COMMENTARY_ROUND_EVENTS_PARQUET, COMMENTARY_ROUND_SUMMARY_PARQUET, COMMENTARY_TOURNAMENT_SUMMARY_PARQUET
import pandas as pd

def main():
    print("=" * 80)
    print("TESTING COMPLETE COMMENTARY CACHE SYSTEM")
    print("=" * 80)

    # Run the update function
    print("\n[1/2] Running update_commentary_caches()...")
    update_commentary_caches()

    print(f"\n[OK] Function completed successfully!")

    # Verify all three files exist and check content
    print("\n[2/2] Verifying cache files:")
    print("-" * 80)

    cache_files = [
        COMMENTARY_ROUND_EVENTS_PARQUET,
        COMMENTARY_ROUND_SUMMARY_PARQUET,
        COMMENTARY_TOURNAMENT_SUMMARY_PARQUET
    ]

    for file_path in cache_files:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / 1024  # KB
            df = pd.read_parquet(file_path)
            print(f"\n   [OK] {file_path}")
            print(f"      Size: {file_size:.1f} KB")
            print(f"      Rows: {len(df)}")
            print(f"      Columns: {len(df.columns)}")
            print(f"      Column names: {', '.join(df.columns[:10].tolist())}...")
        else:
            print(f"\n   [ERROR] File not found: {file_path}")

    # Display summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    # Round Events
    events_df = pd.read_parquet(COMMENTARY_ROUND_EVENTS_PARQUET)
    print(f"\nRound Events ({COMMENTARY_ROUND_EVENTS_PARQUET}):")
    print(f"   Total events: {len(events_df)}")
    print(f"   Event types: {events_df['Event'].nunique()}")
    print(f"   Top 5 events:")
    for event, count in events_df['Event'].value_counts().head(5).items():
        print(f"      {event}: {count}")

    # Round Summary
    round_summary_df = pd.read_parquet(COMMENTARY_ROUND_SUMMARY_PARQUET)
    print(f"\nRound Summary ({COMMENTARY_ROUND_SUMMARY_PARQUET}):")
    print(f"   Total rounds: {len(round_summary_df)}")
    print(f"   TEGs covered: {round_summary_df['TEGNum'].nunique()}")
    print(f"   Players: {round_summary_df['Player'].nunique()}")
    print(f"   Key columns present:")
    key_cols = ['Round_Score_Gross', 'Round_Score_Stableford', 'Lead_Gained_Count_Gross',
                'Lead_Lost_Count_Stableford', 'Holes_In_Lead_Gross']
    for col in key_cols:
        if col in round_summary_df.columns:
            print(f"      [OK] {col}")
        else:
            print(f"      [MISSING] {col}")

    # Tournament Summary
    tournament_summary_df = pd.read_parquet(COMMENTARY_TOURNAMENT_SUMMARY_PARQUET)
    print(f"\nTournament Summary ({COMMENTARY_TOURNAMENT_SUMMARY_PARQUET}):")
    print(f"   Total player-tournament combinations: {len(tournament_summary_df)}")
    print(f"   TEGs covered: {tournament_summary_df['TEGNum'].nunique()}")
    print(f"   Players: {tournament_summary_df['Player'].nunique()}")
    print(f"   Key columns present:")
    key_cols = ['Tournament_Score_Gross', 'Final_Rank_Gross', 'Won_Gross', 'Wooden_Spoon',
                'Total_Lead_Gained_Gross', 'Total_Eagles', 'StdDev_Round_Gross']
    for col in key_cols:
        if col in tournament_summary_df.columns:
            print(f"      [OK] {col}")
        else:
            print(f"      [MISSING] {col}")

    print("\n" + "=" * 80)
    print("INTERESTING FINDINGS FROM TOURNAMENT SUMMARY")
    print("=" * 80)

    # Most wins
    gross_wins = tournament_summary_df[tournament_summary_df['Won_Gross'] == True].groupby('Player').size().sort_values(ascending=False)
    print("\nMost Gross Wins:")
    for player, wins in gross_wins.head(3).items():
        print(f"   {player}: {wins}")

    # Most dramatic round (highest lead change count)
    most_dramatic = round_summary_df.nlargest(1, 'Lead_Gained_Count_Gross')
    if len(most_dramatic) > 0:
        print(f"\nMost Dramatic Round (Lead Changes - Gross):")
        print(f"   {most_dramatic['Player'].values[0]} - TEG {most_dramatic['TEGNum'].values[0]} Round {most_dramatic['Round'].values[0]}: {most_dramatic['Lead_Gained_Count_Gross'].values[0]} lead gains")

    # Most consistent tournament (lowest StdDev by hole)
    most_consistent = tournament_summary_df.nsmallest(1, 'StdDev_Hole_Gross')
    if len(most_consistent) > 0:
        print(f"\nMost Consistent Tournament (by hole):")
        print(f"   {most_consistent['Player'].values[0]} - TEG {most_consistent['TEGNum'].values[0]}: StdDev {most_consistent['StdDev_Hole_Gross'].values[0]:.2f}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nAll three commentary cache files are ready for use by the commentary engine!")

if __name__ == "__main__":
    main()
