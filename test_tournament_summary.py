"""
Test script for create_tournament_summary function
"""

import sys
sys.path.append('streamlit')

from utils import create_tournament_summary

def main():
    print("=" * 80)
    print("TESTING create_tournament_summary()")
    print("=" * 80)

    # Run the function
    print("\n[1/4] Running create_tournament_summary()...")
    summary_df = create_tournament_summary()

    print(f"\n[OK] Function completed successfully!")
    print(f"      {len(summary_df)} rows, {len(summary_df.columns)} columns")

    # Display column list
    print("\n[2/4] Column list:")
    print("-" * 80)
    for i, col in enumerate(summary_df.columns, 1):
        print(f"   {i:2d}. {col}")

    # Display summary statistics
    print("\n[3/4] Summary statistics:")
    print("-" * 80)
    print(f"   TEGs covered: {summary_df['TEGNum'].nunique()}")
    print(f"   Players: {summary_df['Pl'].nunique()}")
    print(f"   Player-TEG combinations: {len(summary_df)}")
    print(f"\n   Tournament Score Stats (Gross):")
    print(f"      Min: {summary_df['Tournament_Score_Gross'].min()}")
    print(f"      Max: {summary_df['Tournament_Score_Gross'].max()}")
    print(f"      Mean: {summary_df['Tournament_Score_Gross'].mean():.1f}")
    print(f"\n   Tournament Score Stats (Stableford):")
    print(f"      Min: {summary_df['Tournament_Score_Stableford'].min()}")
    print(f"      Max: {summary_df['Tournament_Score_Stableford'].max()}")
    print(f"      Mean: {summary_df['Tournament_Score_Stableford'].mean():.1f}")

    # Display sample data
    print("\n[4/4] Sample data (first 5 rows):")
    print("-" * 80)

    # Select key columns for display
    display_cols = [
        'TEGNum', 'Player', 'Tournament_Score_Gross', 'Final_Rank_Gross',
        'Tournament_Score_Stableford', 'Final_Rank_Stableford',
        'Won_Gross', 'Won_Stableford', 'Wooden_Spoon',
        'Total_Holes_In_Lead_Gross', 'Total_Lead_Gained_Gross',
        'Total_Eagles', 'Total_Birdies'
    ]

    print(summary_df[display_cols].head(5).to_string(index=False))

    # Show some interesting findings
    print("\n" + "=" * 80)
    print("INTERESTING FINDINGS")
    print("=" * 80)

    # Most Gross wins
    gross_wins = summary_df[summary_df['Won_Gross'] == True].groupby('Player').size().sort_values(ascending=False)
    print("\nMost Gross Competition Wins:")
    for player, wins in gross_wins.head(3).items():
        print(f"   {player}: {wins} wins")

    # Most Stableford wins
    stableford_wins = summary_df[summary_df['Won_Stableford'] == True].groupby('Player').size().sort_values(ascending=False)
    print("\nMost Stableford Competition Wins:")
    for player, wins in stableford_wins.head(3).items():
        print(f"   {player}: {wins} wins")

    # Most Wooden Spoons
    spoons = summary_df[summary_df['Wooden_Spoon'] == True].groupby('Player').size().sort_values(ascending=False)
    print("\nMost Wooden Spoons:")
    for player, spoons_count in spoons.head(3).items():
        print(f"   {player}: {spoons_count} spoons")

    # Best tournament performance (Gross)
    best_gross = summary_df.nsmallest(1, 'Tournament_Score_Gross')
    print(f"\nBest Tournament Score (Gross):")
    print(f"   {best_gross['Player'].values[0]} - TEG {best_gross['TEGNum'].values[0]}: {best_gross['Tournament_Score_Gross'].values[0]}")

    # Best tournament performance (Stableford)
    best_stableford = summary_df.nlargest(1, 'Tournament_Score_Stableford')
    print(f"\nBest Tournament Score (Stableford):")
    print(f"   {best_stableford['Player'].values[0]} - TEG {best_stableford['TEGNum'].values[0]}: {best_stableford['Tournament_Score_Stableford'].values[0]}")

    # Most eagles
    most_eagles = summary_df.nlargest(1, 'Total_Eagles')
    print(f"\nMost Eagles in a Tournament:")
    print(f"   {most_eagles['Player'].values[0]} - TEG {most_eagles['TEGNum'].values[0]}: {most_eagles['Total_Eagles'].values[0]} eagles")

    # Most holes in lead
    most_lead = summary_df.nlargest(1, 'Total_Holes_In_Lead_Gross')
    print(f"\nMost Holes in Lead (Gross) in a Tournament:")
    print(f"   {most_lead['Player'].values[0]} - TEG {most_lead['TEGNum'].values[0]}: {most_lead['Total_Holes_In_Lead_Gross'].values[0]} holes")

    # Save to CSV
    output_file = 'test_tournament_summary.csv'
    print(f"\n\n[SAVE] Writing to {output_file}...")
    summary_df.to_csv(output_file, index=False)
    print(f"   [OK] Saved successfully!")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
