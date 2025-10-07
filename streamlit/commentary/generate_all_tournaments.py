"""
Batch Tournament Commentary Generator

Generates all three report types for multiple tournaments:
1. Main tournament report (detailed narrative)
2. Brief summary (2-3 paragraphs)
3. Player profiles (individual summaries)
"""

import os
from pathlib import Path
from generate_commentary import (
    load_tournament_data,
    create_story_blueprint,
    write_tournament_article,
    generate_brief_summary,
    generate_player_profiles
)

# Configuration
DATA_DIR = Path("data")
OUTPUT_DIR = Path("data/commentary/drafts")

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Get API key from environment
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY environment variable must be set")

# Define file paths
tournament_summary_path = DATA_DIR / "commentary_tournament_summary.parquet"
round_summary_path = DATA_DIR / "commentary_round_summary.parquet"
events_path = DATA_DIR / "commentary_round_events.parquet"
tournament_streaks_path = DATA_DIR / "commentary_tournament_streaks.parquet"
round_streaks_path = DATA_DIR / "commentary_round_streaks.parquet"
all_data_path = DATA_DIR / "all-data.parquet"
winners_csv_path = DATA_DIR / "teg_winners.csv"


def generate_all_reports_for_tournament(teg_num: int):
    """
    Generate all three report types for a single tournament.

    Args:
        teg_num: Tournament number
    """
    print(f"\n{'='*80}")
    print(f"GENERATING TEG {teg_num} COMMENTARY")
    print(f"{'='*80}\n")

    try:
        # Stage 1: Load tournament data (shared across all report types)
        print("Stage 1: Loading tournament data...")
        tournament_data = load_tournament_data(
            teg_num=teg_num,
            tournament_summary_path=str(tournament_summary_path),
            round_summary_path=str(round_summary_path),
            events_path=str(events_path),
            tournament_streaks_path=str(tournament_streaks_path),
            round_streaks_path=str(round_streaks_path),
            all_data_path=str(all_data_path),
            winners_csv_path=str(winners_csv_path)
        )

        # Stage 2: Create story blueprint (used for main report)
        print("Stage 2: Creating story blueprint...")
        blueprint = create_story_blueprint(tournament_data, api_key)

        # Stage 3a: Main tournament report
        print("Stage 3a: Writing main tournament article...")
        article = write_tournament_article(blueprint, tournament_data, api_key)

        main_report_path = OUTPUT_DIR / f"teg_{teg_num}_main_report.md"
        with open(main_report_path, 'w', encoding='utf-8') as f:
            f.write(f"# TEG {teg_num} Tournament Report\n\n")
            f.write(article)
        print(f"  ✓ Main report saved to: {main_report_path}")

        # Stage 3b: Brief summary
        print("Stage 3b: Writing brief summary...")
        brief_summary = generate_brief_summary(tournament_data, api_key)

        brief_summary_path = OUTPUT_DIR / f"teg_{teg_num}_brief_summary.md"
        with open(brief_summary_path, 'w', encoding='utf-8') as f:
            f.write(f"# TEG {teg_num} - Brief Summary\n\n")
            f.write(brief_summary)
        print(f"  ✓ Brief summary saved to: {brief_summary_path}")

        # Stage 3c: Player profiles
        print("Stage 3c: Writing player profiles...")
        player_profiles = generate_player_profiles(tournament_data, api_key)

        player_profiles_path = OUTPUT_DIR / f"teg_{teg_num}_player_profiles.md"
        with open(player_profiles_path, 'w', encoding='utf-8') as f:
            f.write(f"# TEG {teg_num} - Player Profiles\n\n")
            f.write(player_profiles)
        print(f"  ✓ Player profiles saved to: {player_profiles_path}")

        print(f"\n✓ TEG {teg_num} complete - all 3 reports generated successfully")

    except Exception as e:
        print(f"✗ ERROR generating TEG {teg_num}: {e}")
        raise


def generate_all_tournaments(start_teg: int = 1, end_teg: int = 17):
    """
    Generate all report types for a range of tournaments.

    Args:
        start_teg: First tournament number (default: 1)
        end_teg: Last tournament number (default: 17)
    """
    print(f"\n{'='*80}")
    print(f"BATCH GENERATION: TEG {start_teg} to TEG {end_teg}")
    print(f"{'='*80}\n")

    total_tournaments = end_teg - start_teg + 1
    successful = 0
    failed = []

    for teg_num in range(start_teg, end_teg + 1):
        try:
            generate_all_reports_for_tournament(teg_num)
            successful += 1
        except Exception as e:
            failed.append((teg_num, str(e)))
            print(f"\n✗ Skipping TEG {teg_num} due to error\n")
            continue

    # Summary
    print(f"\n{'='*80}")
    print(f"BATCH GENERATION COMPLETE")
    print(f"{'='*80}")
    print(f"Total tournaments: {total_tournaments}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(failed)}")

    if failed:
        print(f"\nFailed tournaments:")
        for teg_num, error in failed:
            print(f"  - TEG {teg_num}: {error}")


if __name__ == "__main__":
    # Generate all tournaments from TEG 1 to TEG 17
    # Adjust the range as needed
    generate_all_tournaments(start_teg=1, end_teg=17)
