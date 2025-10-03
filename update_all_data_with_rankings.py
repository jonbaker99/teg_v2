"""One-off script to add rankings and gaps to the main data files.

This script is designed to be run once to add TEG-level rankings and gap-to-
leader columns to the `all-data.parquet` and `all-data.csv` files. It
loads the data, applies the `add_rankings_and_gaps` function, and saves the
updated files back to the `data/` directory.
"""
import pandas as pd
import sys
from pathlib import Path

# Define the function directly here to avoid import issues
def add_rankings_and_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add TEG-level rankings and gaps to leader for cumulative scores.
    """
    print("   Creating TEG_Hole column...")
    df['TEG_Hole'] = df['Hole'] + 18 * (df['Round'] - 1)

    print("   Calculating GrossVP rankings...")
    df['Rank_GrossVP_TEG'] = df.groupby(['TEGNum', 'TEG_Hole'])['GrossVP Cum TEG'].rank(
        method='min', ascending=True, na_option='keep'
    )

    print("   Calculating Stableford rankings...")
    df['Rank_Stableford_TEG'] = df.groupby(['TEGNum', 'TEG_Hole'])['Stableford Cum TEG'].rank(
        method='min', ascending=False, na_option='keep'
    )

    print("   Calculating GrossVP gaps to leader...")
    df['Gap_GrossVP_TEG'] = df.groupby(['TEGNum', 'TEG_Hole'])['GrossVP Cum TEG'].transform(
        lambda x: x - x.min()
    )

    print("   Calculating Stableford gaps to leader...")
    df['Gap_Stableford_TEG'] = df.groupby(['TEGNum', 'TEG_Hole'])['Stableford Cum TEG'].transform(
        lambda x: x.max() - x
    )

    return df

print("="*80)
print("ONE-OFF UPDATE: Adding Rankings and Gaps to all-data files")
print("="*80)

# Load all-data.parquet
print("\n1. Loading all-data.parquet...")
df = pd.read_parquet('data/all-data.parquet')
print(f"   Loaded {len(df)} rows")
print(f"   TEGs: {sorted(df['TEGNum'].unique())}")

# Apply the function
print("\n2. Adding rankings and gaps...")
df_updated = add_rankings_and_gaps(df)

# Verify new columns were added
new_cols = ['TEG_Hole', 'Rank_GrossVP_TEG', 'Rank_Stableford_TEG', 'Gap_GrossVP_TEG', 'Gap_Stableford_TEG']
print("\n3. Verifying new columns:")
for col in new_cols:
    if col in df_updated.columns:
        print(f"   [OK] {col}")
    else:
        print(f"   [ERROR] {col} - MISSING!")
        sys.exit(1)

# Save updated parquet
print("\n4. Saving all-data.parquet...")
df_updated.to_parquet('data/all-data.parquet', index=False)
print("   [OK] Saved")

# Save updated CSV (if possible)
print("\n5. Saving all-data.csv...")
try:
    df_updated.to_csv('data/all-data.csv', index=False)
    print("   [OK] Saved")
    csv_updated = True
except PermissionError:
    print("   [SKIPPED] File is open - will be updated by data update process")
    csv_updated = False

print("\n" + "="*80)
print("UPDATE COMPLETE")
print("="*80)
print(f"\nTotal rows processed: {len(df_updated)}")
print(f"New columns added: {len(new_cols)}")
print("\nFiles updated:")
print("  - data/all-data.parquet")
if csv_updated:
    print("  - data/all-data.csv")
else:
    print("  - data/all-data.csv (skipped - file is open)")