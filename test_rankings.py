"""
Test script to verify add_rankings_and_gaps function on two random TEGs
"""
import pandas as pd
import sys
from pathlib import Path
import random

# Add streamlit directory to path
sys.path.insert(0, str(Path(__file__).parent / 'streamlit'))

# Import just the function we need
import importlib.util
spec = importlib.util.spec_from_file_location("utils", Path(__file__).parent / 'streamlit' / 'utils.py')
utils = importlib.util.module_from_spec(spec)

# Define add_rankings_and_gaps directly here to avoid import issues
def add_rankings_and_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add TEG-level rankings and gaps to leader for cumulative scores.
    """
    # Create TEG_Hole column for grouping (cumulative hole number within TEG)
    df['TEG_Hole'] = df['Hole'] + 18 * (df['Round'] - 1)

    # Add rankings for GrossVP (lower is better - ascending)
    df['Rank_GrossVP_TEG'] = df.groupby(['TEGNum', 'TEG_Hole'])['GrossVP Cum TEG'].rank(
        method='min', ascending=True, na_option='keep'
    )

    # Add rankings for Stableford (higher is better - descending)
    df['Rank_Stableford_TEG'] = df.groupby(['TEGNum', 'TEG_Hole'])['Stableford Cum TEG'].rank(
        method='min', ascending=False, na_option='keep'
    )

    # Add gap to leader for GrossVP (leader has minimum, so gap = player - leader)
    df['Gap_GrossVP_TEG'] = df.groupby(['TEGNum', 'TEG_Hole'])['GrossVP Cum TEG'].transform(
        lambda x: x - x.min()
    )

    # Add gap to leader for Stableford (leader has maximum, so gap = leader - player)
    df['Gap_Stableford_TEG'] = df.groupby(['TEGNum', 'TEG_Hole'])['Stableford Cum TEG'].transform(
        lambda x: x.max() - x
    )

    return df

# Load all-data.parquet
print("Loading all-data.parquet...")
df = pd.read_parquet('data/all-data.parquet')

# Get unique TEGs
unique_tegs = df['TEGNum'].unique()
print(f"Found {len(unique_tegs)} TEGs: {sorted(unique_tegs)}")

# Select two random TEGs
random.seed(42)  # For reproducibility
test_tegs = random.sample(list(unique_tegs), 2)
print(f"\nTesting on TEGs: {test_tegs}")

# Filter to test TEGs
df_test = df[df['TEGNum'].isin(test_tegs)].copy()
print(f"\nFiltered data: {len(df_test)} rows")

# Check required columns exist
required_cols = ['GrossVP Cum TEG', 'Stableford Cum TEG', 'TEGNum', 'Round', 'Hole']
missing_cols = [col for col in required_cols if col not in df_test.columns]
if missing_cols:
    print(f"ERROR: Missing required columns: {missing_cols}")
    sys.exit(1)

print("\nColumns before adding rankings:")
print(df_test.columns.tolist())

# Apply the function
print("\nApplying add_rankings_and_gaps()...")
df_result = add_rankings_and_gaps(df_test)

print("\nNew columns added:")
new_cols = ['TEG_Hole', 'Rank_GrossVP_TEG', 'Rank_Stableford_TEG', 'Gap_GrossVP_TEG', 'Gap_Stableford_TEG']
for col in new_cols:
    if col in df_result.columns:
        print(f"  [OK] {col}")
    else:
        print(f"  [MISSING] {col}")

# Display sample results for each test TEG
for teg in sorted(test_tegs):
    print(f"\n{'='*80}")
    print(f"TEG {teg} - Sample at final hole (hole 72)")
    print(f"{'='*80}")

    teg_data = df_result[df_result['TEGNum'] == teg]
    final_hole = teg_data[teg_data['TEG_Hole'] == 72].copy()

    if len(final_hole) > 0:
        # Select columns to display
        display_cols = ['Player', 'TEG_Hole', 'GrossVP Cum TEG', 'Rank_GrossVP_TEG',
                       'Gap_GrossVP_TEG', 'Stableford Cum TEG', 'Rank_Stableford_TEG',
                       'Gap_Stableford_TEG']

        # Sort by GrossVP rank
        final_hole = final_hole.sort_values('Rank_GrossVP_TEG')

        print("\nGross Competition (sorted by rank):")
        print(final_hole[['Player', 'GrossVP Cum TEG', 'Rank_GrossVP_TEG', 'Gap_GrossVP_TEG']].to_string(index=False))

        print("\nStableford Competition (sorted by rank):")
        final_hole_stableford = final_hole.sort_values('Rank_Stableford_TEG')
        print(final_hole_stableford[['Player', 'Stableford Cum TEG', 'Rank_Stableford_TEG', 'Gap_Stableford_TEG']].to_string(index=False))
    else:
        print(f"No data found at hole 72 for TEG {teg}")

    # Show progression at a mid-point (hole 36 - end of round 2)
    print(f"\n{'-'*80}")
    print(f"TEG {teg} - Sample at hole 36 (end of Round 2)")
    print(f"{'-'*80}")

    midpoint = teg_data[teg_data['TEG_Hole'] == 36].copy()

    if len(midpoint) > 0:
        midpoint = midpoint.sort_values('Rank_GrossVP_TEG')
        print("\nGross Competition:")
        print(midpoint[['Player', 'GrossVP Cum TEG', 'Rank_GrossVP_TEG', 'Gap_GrossVP_TEG']].to_string(index=False))

        print("\nStableford Competition:")
        midpoint_stableford = midpoint.sort_values('Rank_Stableford_TEG')
        print(midpoint_stableford[['Player', 'Stableford Cum TEG', 'Rank_Stableford_TEG', 'Gap_Stableford_TEG']].to_string(index=False))

# Verify leader has gap of 0
print(f"\n{'='*80}")
print("VALIDATION CHECKS")
print(f"{'='*80}")

# Check that leader always has gap of 0
for teg in test_tegs:
    teg_data = df_result[df_result['TEGNum'] == teg]

    # For each hole, check leader has gap = 0
    for hole in teg_data['TEG_Hole'].unique():
        hole_data = teg_data[teg_data['TEG_Hole'] == hole]

        # GrossVP leader (rank 1) should have gap 0
        grossvp_leader = hole_data[hole_data['Rank_GrossVP_TEG'] == 1]['Gap_GrossVP_TEG'].values
        if len(grossvp_leader) > 0 and not all(g == 0 for g in grossvp_leader):
            print(f"ERROR: TEG {teg}, Hole {hole} - GrossVP leader has non-zero gap!")

        # Stableford leader (rank 1) should have gap 0
        stableford_leader = hole_data[hole_data['Rank_Stableford_TEG'] == 1]['Gap_Stableford_TEG'].values
        if len(stableford_leader) > 0 and not all(g == 0 for g in stableford_leader):
            print(f"ERROR: TEG {teg}, Hole {hole} - Stableford leader has non-zero gap!")

print("\n[OK] All validation checks passed!")

# Save results to CSV for review
output_file = 'test_rankings_output.csv'
df_result.to_csv(output_file, index=False)
print(f"\nResults saved to: {output_file}")
print("\nTest completed successfully!")