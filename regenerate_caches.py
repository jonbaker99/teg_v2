"""One-off script to regenerate commentary and streaks cache files.

This script updates the commentary cache files (round_summary, events, streaks)
and the streaks.parquet file to include all current data from all-scores.parquet.

Run this after adding new round data to ensure cache files are up-to-date.

Usage:
    python regenerate_caches.py
"""

import sys
import os

# Add streamlit directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'streamlit'))

from utils import update_commentary_caches, update_streaks_cache, clear_all_caches
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Regenerate all cache files."""
    print("=" * 60)
    print("REGENERATING CACHE FILES")
    print("=" * 60)
    print()

    try:
        # Step 1: Regenerate streaks cache
        print("Step 1/3: Regenerating streaks cache...")
        print("-" * 60)
        result = update_streaks_cache(defer_github=False)
        if result is None:
            print("[OK] Streaks cache regenerated successfully")
        else:
            print("[WARN] Streaks cache update returned unexpected result")
        print()

        # Step 2: Regenerate commentary caches
        print("Step 2/3: Regenerating commentary caches...")
        print("-" * 60)
        result = update_commentary_caches(defer_github=False)
        if result is None:
            print("[OK] Commentary caches regenerated successfully")
        else:
            print("[WARN] Commentary cache update returned unexpected result")
        print()

        # Step 3: Clear Streamlit caches
        print("Step 3/3: Clearing Streamlit caches...")
        print("-" * 60)
        clear_all_caches()
        print("[OK] Streamlit caches cleared")
        print()

        # Success message
        print("=" * 60)
        print("[SUCCESS] ALL CACHE FILES REGENERATED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print("Files updated:")
        print("  - data/streaks.parquet")
        print("  - data/commentary_round_summary.parquet")
        print("  - data/commentary_round_events.parquet")
        print("  - data/commentary_round_streaks.parquet")
        print("  - data/commentary_tournament_summary.parquet")
        print("  - data/commentary_tournament_streaks.parquet")
        print()
        print("Next steps:")
        print("  1. Commit and push these files to GitHub")
        print("  2. Retry report generation: python streamlit/commentary/generate_round_report.py 18 2")
        print()

    except Exception as e:
        print()
        print("=" * 60)
        print("[ERROR] CACHE REGENERATION FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        logger.error("Cache regeneration failed", exc_info=True)
        print()
        print("Please check the error message above and try again.")
        return 1

    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
