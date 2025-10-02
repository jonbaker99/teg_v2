"""
Filter ALL commentary data for TEG 17 and save to CSV files
"""

import sys
sys.path.append('streamlit')

import pandas as pd
from utils import (
    COMMENTARY_ROUND_EVENTS_PARQUET,
    COMMENTARY_ROUND_SUMMARY_PARQUET,
    COMMENTARY_ROUND_STREAKS_PARQUET,
    COMMENTARY_TOURNAMENT_STREAKS_PARQUET,
    COMMENTARY_TOURNAMENT_SUMMARY_PARQUET
)

def main():
    print("=" * 80)
    print("FILTERING ALL COMMENTARY DATA FOR TEG 17")
    print("=" * 80)

    # Read all five files
    print("\n[1/4] Reading commentary cache files...")
    round_events = pd.read_parquet(COMMENTARY_ROUND_EVENTS_PARQUET)
    round_summary = pd.read_parquet(COMMENTARY_ROUND_SUMMARY_PARQUET)
    round_streaks = pd.read_parquet(COMMENTARY_ROUND_STREAKS_PARQUET)
    tournament_streaks = pd.read_parquet(COMMENTARY_TOURNAMENT_STREAKS_PARQUET)
    tournament_summary = pd.read_parquet(COMMENTARY_TOURNAMENT_SUMMARY_PARQUET)

    print(f"   Round events: {len(round_events)} rows")
    print(f"   Round summary: {len(round_summary)} rows")
    print(f"   Round streaks: {len(round_streaks)} rows")
    print(f"   Tournament streaks: {len(tournament_streaks)} rows")
    print(f"   Tournament summary: {len(tournament_summary)} rows")

    # Filter to TEG 17
    print("\n[2/4] Filtering to TEG 17...")
    round_events_teg17 = round_events[round_events['TEG'] == 'TEG 17'].copy()
    round_summary_teg17 = round_summary[round_summary['TEG'] == 'TEG 17'].copy()
    round_streaks_teg17 = round_streaks[round_streaks['TEG'] == 'TEG 17'].copy()
    tournament_streaks_teg17 = tournament_streaks[tournament_streaks['TEG'] == 'TEG 17'].copy()
    tournament_summary_teg17 = tournament_summary[tournament_summary['TEG'] == 'TEG 17'].copy()

    print(f"   Round events (TEG 17): {len(round_events_teg17)} rows")
    print(f"   Round summary (TEG 17): {len(round_summary_teg17)} rows")
    print(f"   Round streaks (TEG 17): {len(round_streaks_teg17)} rows")
    print(f"   Tournament streaks (TEG 17): {len(tournament_streaks_teg17)} rows")
    print(f"   Tournament summary (TEG 17): {len(tournament_summary_teg17)} rows")

    # Save to CSV files with comms_test_teg17_ prefix
    print("\n[3/4] Saving to CSV files...")

    output_files = [
        ('comms_test_teg17_round_events.csv', round_events_teg17),
        ('comms_test_teg17_round_summary.csv', round_summary_teg17),
        ('comms_test_teg17_round_streaks.csv', round_streaks_teg17),
        ('comms_test_teg17_tournament_streaks.csv', tournament_streaks_teg17),
        ('comms_test_teg17_tournament_summary.csv', tournament_summary_teg17)
    ]

    for filename, df in output_files:
        df.to_csv(filename, index=False)
        print(f"   [OK] {filename} ({len(df)} rows, {len(df.columns)} columns)")

    # Display sample data from each file
    print("\n[4/4] Sample data preview:")
    print("-" * 80)

    print("\nRound Events (first 5 rows):")
    if len(round_events_teg17) > 0:
        print(round_events_teg17[['TEG', 'Round', 'Hole', 'Player', 'Event', 'Metric']].head())
    else:
        print("   No data for TEG 17")

    print("\nRound Summary (first 3 rows, selected columns):")
    if len(round_summary_teg17) > 0:
        display_cols = ['TEG', 'Round', 'Player', 'Round_Score_Gross', 'Round_Score_Stableford',
                       'Player_Round_Rank_Gross', 'Player_Round_Rank_Stableford']
        print(round_summary_teg17[display_cols].head(3))
    else:
        print("   No data for TEG 17")

    print("\nRound Streaks (first 5 rows):")
    if len(round_streaks_teg17) > 0:
        print(round_streaks_teg17[['TEG', 'Round', 'Player', 'Streak_Type', 'Max_Streak']].head())
    else:
        print("   No data for TEG 17")

    print("\nTournament Streaks (first 5 rows):")
    if len(tournament_streaks_teg17) > 0:
        print(tournament_streaks_teg17[['TEG', 'Player', 'Streak_Type', 'Max_Streak']].head())
    else:
        print("   No data for TEG 17")

    print("\nTournament Summary (first 5 rows, selected columns):")
    if len(tournament_summary_teg17) > 0:
        display_cols = ['TEG', 'Player', 'Tournament_Score_Gross', 'Final_Rank_Gross',
                       'Tournament_Score_Stableford', 'Final_Rank_Stableford', 'Won_Gross', 'Won_Stableford']
        print(tournament_summary_teg17[display_cols].head())
    else:
        print("   No data for TEG 17")

    print("\n" + "=" * 80)
    print("FILTERING COMPLETE")
    print("=" * 80)
    print("\nAll files created:")
    for filename, _ in output_files:
        print(f"   {filename}")

if __name__ == "__main__":
    main()
