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


class ProgressTracker:
    """Tracks and reports generation progress with detailed sub-step updates.

    This class provides multi-level progress tracking:
    - Level 1: Overall progress (e.g., "Report 3 of 7")
    - Level 2: Current report being generated
    - Level 3: Sub-step within report (e.g., "Loading data", "LLM call 1/2")

    Usage:
        tracker = ProgressTracker(st.status_container)
        tracker.set_total(7)
        tracker.next_item()
        tracker.update("Generating TEG 18 Round 1", "Loading data...")
    """

    def __init__(self, status_container=None):
        """Initialize progress tracker.

        Args:
            status_container: Streamlit status container (st.status object) for UI updates.
                            If None, progress is only logged.
        """
        self.status = status_container
        self.current_item = 0
        self.total_items = 0
        self.current_report = ""
        self.current_step = ""

    def set_total(self, total: int):
        """Set the total number of items to process."""
        self.total_items = total
        logger.info(f"Progress tracker initialized: {total} total items")

    def next_item(self):
        """Move to the next item in the sequence."""
        self.current_item += 1
        logger.debug(f"Progress: {self.current_item}/{self.total_items}")

    def update(self, report: str, step: str = None):
        """Update progress with current report and optional sub-step.

        Args:
            report: Current report being generated (e.g., "Generating TEG 18 Round 1")
            step: Optional sub-step detail (e.g., "Loading data", "LLM call 1/2")
        """
        self.current_report = report
        self.current_step = step if step else ""

        # Format message: [3/7] Generating TEG 18 Round 1: Loading data...
        if self.total_items > 0:
            message = f"[{self.current_item}/{self.total_items}] {report}"
        else:
            message = report

        if step:
            message += f": {step}"

        # Update UI if status container provided
        if self.status:
            self.status.write(message)

        # Always log
        logger.info(message)

    def complete(self, message: str = "All reports generated successfully"):
        """Mark progress as complete with final message."""
        if self.status:
            self.status.write(f"✅ {message}")
        logger.info(message)


def generate_reports_for_changes(changed_rounds: Dict[int, List[int]], progress_tracker=None) -> Dict:
    """Generate round and tournament reports for changed data.

    This function orchestrates report generation for changed rounds and tournaments,
    calling existing generator functions without modifying them.

    Args:
        changed_rounds: Dictionary mapping TEG numbers to lists of changed rounds.
                       Example: {17: [1, 2], 18: [1]} means TEG 17 rounds 1&2, TEG 18 round 1
        progress_tracker: Optional ProgressTracker instance for UI updates

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
        'errors': [],
        'failed_items': []  # Track failed items for retry
    }

    if not changed_rounds:
        logger.info("No changed rounds to process")
        return results

    logger.info(f"Starting report generation for {len(changed_rounds)} TEGs")

    # Initialize progress tracker with total items
    if progress_tracker:
        # Calculate total: all rounds + completed TEGs
        total_rounds = sum(len(rounds) for rounds in changed_rounds.values())
        completed_tegs = [t for t in changed_rounds.keys() if is_tournament_complete(t)]
        total_items = total_rounds + len(completed_tegs)
        progress_tracker.set_total(total_items)

    # FIRST PASS: Generate all reports
    for teg_num in sorted(changed_rounds.keys()):
        rounds = sorted(changed_rounds[teg_num])
        logger.info(f"Processing TEG {teg_num}, rounds {rounds}")

        # 1. Generate round reports for each changed round
        for round_num in rounds:
            if progress_tracker:
                progress_tracker.next_item()
                progress_tracker.update(f"Round Report: TEG {teg_num} Round {round_num}")

            try:
                logger.info(f"Generating round report for TEG {teg_num}, Round {round_num}")
                _generate_round_report(teg_num, round_num, progress_tracker)
                results['round_reports'].append((teg_num, round_num))
                logger.info(f"Successfully generated round report for TEG {teg_num}, Round {round_num}")
            except Exception as e:
                error_msg = f"Round TEG {teg_num} Round {round_num}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)
                results['failed_items'].append(('round', teg_num, round_num))

        # 2. Check if tournament is complete and generate tournament report
        try:
            if is_tournament_complete(teg_num):
                if progress_tracker:
                    progress_tracker.next_item()
                    progress_tracker.update(f"Tournament Report: TEG {teg_num}")

                logger.info(f"TEG {teg_num} is complete, generating tournament reports")
                _generate_tournament_reports(teg_num, progress_tracker)
                results['tournament_reports'].append(teg_num)
                logger.info(f"Successfully generated tournament reports for TEG {teg_num}")
        except Exception as e:
            error_msg = f"Tournament TEG {teg_num}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)
            results['failed_items'].append(('tournament', teg_num, None))

    # RETRY LOGIC: Retry failed items once
    if results['failed_items']:
        if progress_tracker:
            progress_tracker.update("Retry", f"Retrying {len(results['failed_items'])} failed reports...")

        logger.info(f"Retrying {len(results['failed_items'])} failed reports")
        retry_failures = []

        for item_type, teg_num, round_num in results['failed_items']:
            try:
                if item_type == 'round':
                    if progress_tracker:
                        progress_tracker.update(f"RETRY: Round Report TEG {teg_num} Round {round_num}")

                    logger.info(f"RETRY: Generating round report for TEG {teg_num}, Round {round_num}")
                    _generate_round_report(teg_num, round_num, progress_tracker)
                    results['round_reports'].append((teg_num, round_num))

                    # Remove from errors list
                    error_to_remove = f"Round TEG {teg_num} Round {round_num}:"
                    results['errors'] = [e for e in results['errors'] if not e.startswith(error_to_remove)]

                    logger.info(f"RETRY SUCCEEDED: TEG {teg_num}, Round {round_num}")

                else:  # tournament
                    if progress_tracker:
                        progress_tracker.update(f"RETRY: Tournament Report TEG {teg_num}")

                    logger.info(f"RETRY: Generating tournament reports for TEG {teg_num}")
                    _generate_tournament_reports(teg_num, progress_tracker)
                    results['tournament_reports'].append(teg_num)

                    # Remove from errors list
                    error_to_remove = f"Tournament TEG {teg_num}:"
                    results['errors'] = [e for e in results['errors'] if not e.startswith(error_to_remove)]

                    logger.info(f"RETRY SUCCEEDED: TEG {teg_num}")

            except Exception as e:
                # Retry failed - keep in failures
                retry_failures.append((item_type, teg_num, round_num))
                logger.error(f"RETRY FAILED: {item_type} TEG {teg_num} {f'Round {round_num}' if round_num else ''}: {e}")

        # Update failed items with only those that failed retry
        results['failed_items'] = retry_failures

    logger.info(f"Report generation complete. Generated {len(results['round_reports'])} round reports, "
                f"{len(results['tournament_reports'])} tournament reports, "
                f"{len(results['errors'])} errors, "
                f"{len(results['failed_items'])} permanent failures")

    if progress_tracker:
        if results['failed_items']:
            progress_tracker.complete(f"Completed with {len(results['failed_items'])} permanent failure(s)")
        else:
            progress_tracker.complete("All reports generated successfully!")

    return results


def _generate_round_report(teg_num: int, round_num: int, progress_tracker=None):
    """Generate a single round report using existing generator.

    This function is a wrapper that calls the existing generate_complete_round_report
    function without modifying it.

    Args:
        teg_num: Tournament number
        round_num: Round number
        progress_tracker: Optional ProgressTracker for sub-step updates
    """
    # Import here to avoid circular dependencies
    import sys
    import os

    # Add commentary directory to path if needed
    commentary_dir = Path(__file__).parent.parent / "commentary"
    if str(commentary_dir) not in sys.path:
        sys.path.insert(0, str(commentary_dir))

    from commentary.generate_round_report import generate_complete_round_report

    # Show sub-steps if tracker provided
    if progress_tracker:
        progress_tracker.update(f"Round Report: TEG {teg_num} Round {round_num}", "Generating report (LLM)")

    # Call existing generator function (no modifications)
    generate_complete_round_report(teg_num, round_num, dry_run=False)

    if progress_tracker:
        progress_tracker.update(f"Round Report: TEG {teg_num} Round {round_num}", "✅ Complete")


def _generate_tournament_reports(teg_num: int, progress_tracker=None):
    """Generate tournament reports (story notes and main report) and move to production.

    This function orchestrates the tournament report generation using existing
    generator functions, then moves the completed reports from drafts to production.

    Args:
        teg_num: Tournament number
        progress_tracker: Optional ProgressTracker for sub-step updates

    Raises:
        Exception: If commentary cache files are missing
    """
    # Import here to avoid circular dependencies
    import sys
    from pathlib import Path

    # Add commentary directory to path if needed
    commentary_dir = Path(__file__).parent.parent / "commentary"
    if str(commentary_dir) not in sys.path:
        sys.path.insert(0, str(commentary_dir))

    # CRITICAL: Validate that commentary cache files exist before starting expensive generation
    # These files are created by update_commentary_caches() during data updates
    if progress_tracker:
        progress_tracker.update(f"Tournament Report: TEG {teg_num}", "Validating cache files")

    _validate_commentary_cache_files()

    from commentary.generate_tournament_commentary_v2 import (
        generate_complete_story_notes,
        generate_main_report
    )

    # Generate story notes (writes to drafts/)
    # This includes: data processing (6 passes) + round stories (4 LLM calls) + synthesis (1 LLM call)
    if progress_tracker:
        progress_tracker.update(f"Tournament Report: TEG {teg_num}", "Generating story notes (LLM calls)")

    logger.info(f"Generating story notes for TEG {teg_num}")
    generate_complete_story_notes(teg_num)

    # Generate main report (writes to drafts/)
    if progress_tracker:
        progress_tracker.update(f"Tournament Report: TEG {teg_num}", "Generating main report (LLM)")

    logger.info(f"Generating main report for TEG {teg_num}")
    generate_main_report(teg_num)

    # Move reports from drafts to production
    if progress_tracker:
        progress_tracker.update(f"Tournament Report: TEG {teg_num}", "Moving to production")

    logger.info(f"Moving tournament reports to production for TEG {teg_num}")
    move_tournament_report_to_production(teg_num)

    if progress_tracker:
        progress_tracker.update(f"Tournament Report: TEG {teg_num}", "✅ Complete")


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


def _validate_commentary_cache_files():
    """Validate that required commentary cache files exist before tournament report generation.

    Tournament report generation requires pre-computed cache files that are created during
    data updates. This function checks that all required files exist and are readable.

    Raises:
        Exception: If any required cache files are missing, with helpful error message
    """
    from utils import read_file

    required_files = [
        'data/commentary_tournament_summary.parquet',
        'data/commentary_round_summary.parquet',
        'data/commentary_round_events.parquet'
    ]

    missing_files = []

    for file_path in required_files:
        try:
            # Try to read the file using environment-aware utility
            _ = read_file(file_path)
            logger.debug(f"Cache file exists and is readable: {file_path}")
        except FileNotFoundError:
            missing_files.append(file_path)
            logger.error(f"Required cache file not found: {file_path}")
        except Exception as e:
            # File exists but can't be read
            logger.error(f"Error reading cache file {file_path}: {e}")
            missing_files.append(f"{file_path} (read error: {e})")

    if missing_files:
        error_msg = (
            f"❌ Commentary cache files are missing or unreadable:\n\n"
            f"Missing files:\n"
        )
        for file in missing_files:
            error_msg += f"  • {file}\n"

        error_msg += (
            f"\nThese files are generated during data updates by update_commentary_caches().\n\n"
            f"Please ensure:\n"
            f"1. Data was successfully updated using the Data Processing page\n"
            f"2. Commentary caches were regenerated (happens automatically during data update)\n"
            f"3. If on Railway, files were successfully written to volume and/or GitHub\n\n"
            f"If you just updated data, you may need to wait a few moments for cache generation to complete."
        )

        raise Exception(error_msg)
