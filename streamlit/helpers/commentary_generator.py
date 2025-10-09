"""Commentary Generator Module

Automatically generates round and tournament commentary reports for changed data.
This module orchestrates the existing commentary generation scripts without modifying them.

Usage:
    from helpers.commentary_generator import generate_reports_for_changes

    changed_rounds = {17: [1, 2], 18: [1]}  # TEG 17 rounds 1&2, TEG 18 round 1
    results = generate_reports_for_changes(changed_rounds)
"""

import logging
from typing import Dict, List, Tuple
from pathlib import Path
import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)


def generate_reports_for_changes(changed_rounds: Dict[int, List[int]]) -> Dict:
    """Generate round and tournament reports for changed data.

    This function orchestrates report generation for changed rounds and tournaments,
    calling existing generator functions without modifying them.

    Args:
        changed_rounds: Dictionary mapping TEG numbers to lists of changed rounds.
                       Example: {17: [1, 2], 18: [1]} means TEG 17 rounds 1&2, TEG 18 round 1

    Returns:
        Dict with generation results:
        {
            'round_reports': [(teg_num, round_num), ...],
            'tournament_reports': [teg_num, ...],
            'errors': ['error message', ...]
        }
    """
    results = {
        'round_reports': [],
        'tournament_reports': [],
        'errors': []
    }

    if not changed_rounds:
        logger.info("No changed rounds to process")
        return results

    logger.info(f"Starting report generation for {len(changed_rounds)} TEGs")

    for teg_num in sorted(changed_rounds.keys()):
        rounds = sorted(changed_rounds[teg_num])
        logger.info(f"Processing TEG {teg_num}, rounds {rounds}")

        # 1. Generate round reports for each changed round
        for round_num in rounds:
            try:
                logger.info(f"Generating round report for TEG {teg_num}, Round {round_num}")
                _generate_round_report(teg_num, round_num)
                results['round_reports'].append((teg_num, round_num))
                logger.info(f"Successfully generated round report for TEG {teg_num}, Round {round_num}")
            except Exception as e:
                error_msg = f"Round TEG {teg_num} Round {round_num}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)

        # 2. Check if tournament is complete and generate tournament report
        try:
            if is_tournament_complete(teg_num):
                logger.info(f"TEG {teg_num} is complete, generating tournament reports")
                _generate_tournament_reports(teg_num)
                results['tournament_reports'].append(teg_num)
                logger.info(f"Successfully generated tournament reports for TEG {teg_num}")
        except Exception as e:
            error_msg = f"Tournament TEG {teg_num}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)

    logger.info(f"Report generation complete. Generated {len(results['round_reports'])} round reports, "
                f"{len(results['tournament_reports'])} tournament reports, "
                f"{len(results['errors'])} errors")

    return results


def _generate_round_report(teg_num: int, round_num: int):
    """Generate a single round report using existing generator.

    This function is a wrapper that calls the existing generate_complete_round_report
    function without modifying it.

    Args:
        teg_num: Tournament number
        round_num: Round number
    """
    # Import here to avoid circular dependencies
    import sys
    import os

    # Add commentary directory to path if needed
    commentary_dir = Path(__file__).parent.parent / "commentary"
    if str(commentary_dir) not in sys.path:
        sys.path.insert(0, str(commentary_dir))

    from commentary.generate_round_report import generate_complete_round_report

    # Call existing generator function (no modifications)
    generate_complete_round_report(teg_num, round_num, dry_run=False)


def _generate_tournament_reports(teg_num: int):
    """Generate tournament reports (story notes and main report) and move to production.

    This function orchestrates the tournament report generation using existing
    generator functions, then moves the completed reports from drafts to production.

    Args:
        teg_num: Tournament number
    """
    # Import here to avoid circular dependencies
    import sys
    from pathlib import Path

    # Add commentary directory to path if needed
    commentary_dir = Path(__file__).parent.parent / "commentary"
    if str(commentary_dir) not in sys.path:
        sys.path.insert(0, str(commentary_dir))

    from commentary.generate_tournament_commentary_v2 import (
        generate_complete_story_notes,
        generate_main_report
    )

    # Generate story notes (writes to drafts/)
    logger.info(f"Generating story notes for TEG {teg_num}")
    generate_complete_story_notes(teg_num)

    # Generate main report (writes to drafts/)
    logger.info(f"Generating main report for TEG {teg_num}")
    generate_main_report(teg_num)

    # Move reports from drafts to production
    logger.info(f"Moving tournament reports to production for TEG {teg_num}")
    move_tournament_report_to_production(teg_num)


def is_tournament_complete(teg_num: int) -> bool:
    """Check if a tournament is marked as complete.

    Checks the completed_tegs.csv file to determine if a tournament
    has all rounds completed.

    Args:
        teg_num: Tournament number

    Returns:
        bool: True if tournament is complete, False otherwise
    """
    try:
        from utils import read_file

        # Read completed TEGs file
        completed = read_file('data/completed_tegs.csv')

        # Check if this TEG is in the completed list
        is_complete = teg_num in completed['TEGNum'].values

        logger.info(f"TEG {teg_num} completion status: {is_complete}")
        return is_complete

    except Exception as e:
        logger.error(f"Error checking completion status for TEG {teg_num}: {e}")
        # If we can't determine, assume not complete (safer)
        return False


def move_tournament_report_to_production(teg_num: int):
    """Move tournament reports from drafts folder to production commentary folder.

    Reads files from data/commentary/drafts/ and writes them to data/commentary/
    using the existing write_text_file function which handles Railway volume + GitHub.

    Args:
        teg_num: Tournament number
    """
    from utils import write_text_file
    from pathlib import Path

    # Define files to move
    files_to_move = [
        f"teg_{teg_num}_story_notes.md",
        f"teg_{teg_num}_main_report.md",
        f"teg_{teg_num}_brief_summary.md"
    ]

    moved_count = 0
    for filename in files_to_move:
        try:
            # Construct source path (in drafts folder)
            source_path = Path("data/commentary/drafts") / filename

            # Check if source file exists
            if not source_path.exists():
                logger.warning(f"Source file not found: {source_path}")
                continue

            # Read content from draft
            content = source_path.read_text(encoding='utf-8')

            # Write to production location using existing utility
            # This handles both Railway volume and GitHub commit
            dest_path = f"data/commentary/{filename}"
            write_text_file(
                dest_path,
                content,
                commit_message=f"Publish TEG {teg_num} {filename.replace('_', ' ').replace('.md', '')}"
            )

            logger.info(f"Moved {filename} to production")
            moved_count += 1

        except Exception as e:
            logger.error(f"Error moving {filename}: {e}", exc_info=True)
            # Continue with other files even if one fails
            continue

    logger.info(f"Moved {moved_count}/{len(files_to_move)} files to production for TEG {teg_num}")

    if moved_count == 0:
        raise Exception(f"Failed to move any tournament report files for TEG {teg_num}")
