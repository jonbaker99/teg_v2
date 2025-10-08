"""
Round Report Generator

Generates narrative round reports for live tournament analysis.
Follows the proven two-pass LLM architecture:
1. Story Notes Generation (identify storylines from data)
2. Report Generation (transform notes into narrative with forward-looking analysis)

Usage:
    # Single report
    python generate_round_report.py --teg 17 --round 2

    # Range of rounds in a single TEG
    python generate_round_report.py --teg 17 --round 1-4

    # Range of TEGs and rounds (batch processing with prompt caching optimization)
    python generate_round_report.py --teg 15-17 --round 1-4

    # Only generate story notes (Phase 1)
    python generate_round_report.py --teg 17 --round 1-4 --story-notes-only

    # Only generate reports from existing story notes (Phase 2)
    python generate_round_report.py --teg 17 --round 1-4 --reports-only

    # Dry run (test without LLM calls)
    python generate_round_report.py --teg 17 --round 2 --dry-run

    # Backwards compatible
    python generate_round_report.py 17 2
"""

import sys
import os
import json
import argparse
import time
import math
from pathlib import Path
from collections import deque

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from round_data_loader import load_round_report_data
from round_pattern_analysis import get_round_storylines
from prompts import ROUND_STORY_NOTES_PROMPT, ROUND_REPORT_PROMPT
from utils import get_teg_rounds, write_text_file
from batch_api import (
    create_batch_request, save_batch_requests, submit_batch,
    poll_until_complete, get_batch_results, save_batch_info,
    find_batch_info_file, load_batch_info, check_batch_status, list_recent_batches
)

# LLM setup (reusing tournament report patterns)
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: anthropic package not available. Running in dry-run mode only.")

# Configuration
DRY_RUN = False  # Set to True to test without LLM calls
DEBUG = True

# Token budget configuration (from Anthropic rate limits)
RATE_BUDGET_INPUT_TOKENS_PER_MIN = 30000
RATE_SAFETY = 0.90  # Use 90% of budget to stay safe


# ========================
# Token Limiter + Safe API Wrapper
# ========================

class TokenMinuteLimiter:
    """
    Rolling 60s token limiter with simulation during DRY_RUN.
    Stores (timestamp, tokens) and plans waits so sum(tokens) <= budget within last 60s.
    """
    def __init__(self, budget_per_min: int, safety: float, dry_run: bool, debug: bool):
        self.budget = int(budget_per_min * safety)
        self.events = deque()  # (ts, tokens)
        self.dry_run = dry_run
        self.debug = debug

    def _now(self):
        return time.monotonic()

    def _prune(self, now=None):
        now = now or self._now()
        while self.events and now - self.events[0][0] > 60:
            self.events.popleft()

    def used_last_min(self):
        now = self._now()
        self._prune(now)
        return sum(t for _, t in self.events)

    def plan_wait(self, tokens: int) -> int:
        now = self._now()
        self._prune(now)
        used = self.used_last_min()
        if used + tokens <= self.budget:
            return 0
        # Find when enough oldest tokens age out
        temp = list(self.events)
        total = used
        wait = 0
        for ts, t in temp:
            total -= t
            expire_in = (ts + 60) - now
            if total + tokens <= self.budget:
                wait = max(0, math.ceil(expire_in))
                break
        else:
            wait = 60
        return wait

    def acquire(self, tokens: int, label: str = ""):
        """Plan wait; in DRY_RUN simulate consumption; in live, sleep then record."""
        wait = self.plan_wait(tokens)
        used = self.used_last_min()
        if self.debug:
            print(f"  - Rate limit: used {used:,} / budget {self.budget:,} tokens, next '{label}' ~{tokens:,} tokens, wait {wait}s")
        now = self._now()
        if self.dry_run:
            self.events.append((now, tokens))  # simulate consumption
        else:
            if wait > 0:
                time.sleep(wait)
            self.events.append((self._now(), tokens))


# Global limiter instance
TOKEN_LIMITER = TokenMinuteLimiter(RATE_BUDGET_INPUT_TOKENS_PER_MIN, RATE_SAFETY, DRY_RUN, DEBUG)


def safe_create_message(client, max_retries=8, **kwargs):
    """
    Wrapper around client.messages.create with retry logic for rate limits and overload errors.
    - Handles 429 (rate limit) with Retry-After headers
    - Handles 500 (internal server error) with exponential backoff
    - Handles 529 (overloaded) with exponential backoff
    - Exponential backoff otherwise (cap 60s)

    Args:
        client: Anthropic client instance
        max_retries: Maximum number of retry attempts (default 8)
        **kwargs: Arguments to pass to client.messages.create()
    """
    backoff = 2.0
    attempt = 0
    while True:
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            attempt += 1
            if attempt > max_retries:
                raise
            resp = getattr(e, "response", None)
            headers = getattr(resp, "headers", {}) if resp is not None else {}
            retry_after = headers.get("retry-after")
            reset_secs = headers.get("anthropic-ratelimit-tokens-reset")
            sleep_for = None
            if retry_after:
                try:
                    sleep_for = float(retry_after)
                except Exception:
                    pass
            if sleep_for is None and reset_secs:
                try:
                    sleep_for = float(reset_secs)
                except Exception:
                    pass
            if sleep_for is None:
                sleep_for = backoff
                backoff = min(backoff * 2, 60.0)
            print(f"  · Rate limit (429). Backing off {sleep_for:.1f}s (attempt {attempt}/{max_retries})")
            time.sleep(sleep_for)
        except anthropic.APIStatusError as e:
            # Handle 500, 529, and other transient errors
            attempt += 1
            if attempt > max_retries:
                raise
            status_code = getattr(e, 'status_code', None)
            if status_code == 500:
                print(f"  · Internal server error (500). Backing off {backoff:.1f}s (attempt {attempt}/{max_retries})")
            elif status_code == 529:
                print(f"  · Server overloaded (529). Backing off {backoff:.1f}s (attempt {attempt}/{max_retries})")
            else:
                print(f"  · Transient API error ({status_code}). Backing off {backoff:.1f}s (attempt {attempt}/{max_retries})")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)


try:
    import streamlit as st
    def get_api_key():
        """Get Anthropic API key from Streamlit secrets or environment variables."""
        try:
            if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
                return st.secrets['ANTHROPIC_API_KEY']
        except Exception:
            # If secrets.toml doesn't exist or can't be read, fall through to env var
            pass
        return os.getenv('ANTHROPIC_API_KEY')
except ImportError:
    def get_api_key():
        """Get Anthropic API key from environment variables."""
        return os.getenv('ANTHROPIC_API_KEY')


def format_round_data_for_prompt(round_data, storylines):
    """
    Format round data into a compact JSON structure for LLM consumption.

    Args:
        round_data: Output from load_round_report_data()
        storylines: Output from get_round_storylines()

    Returns:
        String with formatted data ready for LLM prompt
    """
    import numpy as np
    import pandas as pd

    print("DEBUG: Starting format_round_data_for_prompt")

    def clean_value(val):
        """Convert NaN/None to None for JSON serialization."""
        if pd.isna(val) or val is None:
            return None
        if isinstance(val, (np.integer, np.floating)):
            if np.isnan(val):
                return None
            return int(val) if isinstance(val, np.integer) else float(val)
        return val

    print("DEBUG: Building prompt_data structure")
    # Build compact data structure
    try:
        prompt_data = {
            'round_info': {
                'teg_num': round_data['teg_num'],
                'round_num': round_data['round_num'],
                'course': round_data['metadata']['course'],
                'date': round_data['metadata']['date'],
                'par': round_data['metadata']['par']
            },
            'round_summary': [],
            'six_hole_splits': {},
            'hole_difficulty': [],
            'previous_round_scores': None,
            'key_events': [],
            'streaks': [],
            'storylines': {},
            'projections': {}
        }

        print(f"DEBUG: Processing {len(round_data['round_summary'])} players in round_summary")
        for i, r in enumerate(round_data['round_summary']):
            print(f"DEBUG: Processing player {i+1}: {r.get('Player')}")
            try:
                player_summary = {
                    'player': r['Player'],
                    'round_stableford': clean_value(r.get('Round_Score_Stableford')),
                    'round_gross': clean_value(r.get('Round_Score_Gross')),
                    'cumulative_stableford': clean_value(r.get('Cumulative_Tournament_Score_Stableford')),
                    'position_before': clean_value(r.get('Cumulative_Tournament_Rank_Before_Round_Stableford')),
                    'position_after': clean_value(r.get('Cumulative_Tournament_Rank_Stableford')),
                    'gap_to_leader': clean_value(r.get('Gap_To_Leader_After_Round_Stableford')),
                    'front_9': clean_value(r.get('Front_9_Score_Stableford')),
                    'back_9': clean_value(r.get('Back_9_Score_Stableford'))
                }
                prompt_data['round_summary'].append(player_summary)
            except Exception as e:
                print(f"ERROR processing player {r.get('Player')}: {e}")
                print(f"DEBUG: Player data: {r}")
                raise

        print("DEBUG: Setting six_hole_splits")
        prompt_data['six_hole_splits'] = round_data['six_hole_splits']

        print("DEBUG: Setting hole_difficulty")
        prompt_data['hole_difficulty'] = round_data['hole_difficulty']

        print("DEBUG: Setting previous_round_scores")
        prompt_data['previous_round_scores'] = round_data['previous_round_scores']

        print(f"DEBUG: Processing {len(round_data['events'])} events")
        for e in round_data['events']:
            if e.get('Event') in ['Eagle', 'Zero_Stableford_Points', 'Lead_Change_Stableford']:
                try:
                    event_data = {
                        'hole': clean_value(e.get('Hole')),
                        'player': e.get('Player'),
                        'event': e.get('Event'),
                        'par': clean_value(e.get('Par')),
                        'score': clean_value(e.get('Sc')),
                        'gross_vp': clean_value(e.get('GrossVP')),
                        'stableford': clean_value(e.get('Stableford'))
                    }
                    prompt_data['key_events'].append(event_data)
                except Exception as ex:
                    print(f"ERROR processing event: {ex}")
                    print(f"DEBUG: Event data: {e}")
                    raise

        print(f"DEBUG: Processing {len(round_data['streaks'])} streaks")
        for s in round_data['streaks']:
            if s.get('StreakLength', 0) >= 3:
                try:
                    streak_data = {
                        'player': s.get('Player'),
                        'type': s.get('StreakType'),
                        'length': clean_value(s.get('StreakLength')),
                        'start_hole': clean_value(s.get('StartHole')),
                        'end_hole': clean_value(s.get('EndHole'))
                    }
                    prompt_data['streaks'].append(streak_data)
                except Exception as ex:
                    print(f"ERROR processing streak: {ex}")
                    print(f"DEBUG: Streak data: {s}")
                    raise

        print("DEBUG: Setting storylines")
        prompt_data['storylines'] = storylines

        print("DEBUG: Setting projections")
        prompt_data['projections'] = round_data['projections']

    except Exception as e:
        print(f"ERROR in format_round_data_for_prompt: {e}")
        import traceback
        traceback.print_exc()
        raise

    print("DEBUG: Converting to JSON")
    try:
        result = json.dumps(prompt_data, indent=2, default=str)
        print(f"DEBUG: JSON conversion successful, length: {len(result)}")
        return result
    except Exception as e:
        print(f"ERROR in json.dumps: {e}")
        import traceback
        traceback.print_exc()
        raise


def generate_round_story_notes(teg_num, round_num, dry_run=False):
    """
    Generate structured story notes for a round using LLM.

    Args:
        teg_num: Tournament number
        round_num: Round number
        dry_run: If True, skip LLM call and return placeholder

    Returns:
        String with structured story notes (markdown bullets)
    """
    print(f"\nGenerating story notes for TEG {teg_num}, Round {round_num}...")

    # Load data
    round_data = load_round_report_data(teg_num, round_num)
    storylines = get_round_storylines(round_data)

    # Format data for prompt
    data_json = format_round_data_for_prompt(round_data, storylines)

    # Build prompt
    system_prompt = ROUND_STORY_NOTES_PROMPT
    user_message = f"""Round Data:

{data_json}

Create structured story notes for this round following the specified format."""

    if DEBUG:
        print(f"  Data size: {len(data_json):,} characters")
        print(f"  Prompt size: {len(system_prompt + user_message):,} characters")

    # DRY RUN gate
    if dry_run or DRY_RUN:
        print("  DRY RUN: Skipping LLM call")
        return "DRY_RUN_STORY_NOTES"

    # Real LLM call
    if not ANTHROPIC_AVAILABLE:
        raise ValueError("Anthropic package not available. Install with: pip install anthropic")

    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables or Streamlit secrets")

    client = anthropic.Anthropic(api_key=api_key)

    # Estimate input tokens (rough: 4 chars per token)
    estimated_input_tokens = (len(system_prompt) + len(user_message)) // 4

    # Acquire tokens from rate limiter
    TOKEN_LIMITER.acquire(estimated_input_tokens, label=f"TEG{teg_num}_R{round_num}_story_notes")

    message = safe_create_message(
        client,
        model="claude-sonnet-4-5",
        max_tokens=3000,
        system=[{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"}
        }],
        messages=[{
            "role": "user",
            "content": user_message
        }]
    )

    story_notes = message.content[0].text
    print(f"  > Story notes complete ({len(story_notes)} characters)")

    return story_notes


def generate_round_narrative_report(teg_num, round_num, story_notes, dry_run=False):
    """
    Generate full narrative report from story notes using LLM.

    Args:
        teg_num: Tournament number
        round_num: Round number
        story_notes: Structured story notes (from generate_round_story_notes)
        dry_run: If True, skip LLM call and return placeholder

    Returns:
        String with full markdown report
    """
    print(f"\nGenerating narrative report for TEG {teg_num}, Round {round_num}...")

    # Load data for metadata
    round_data = load_round_report_data(teg_num, round_num)

    # Build prompt
    system_prompt = ROUND_REPORT_PROMPT
    user_message = f"""Story Notes:

{story_notes}

Tournament Context:
- TEG Number: {teg_num}
- Round Number: {round_num}
- Course: {round_data['metadata']['course']}
- Date: {round_data['metadata']['date']}
- Rounds Remaining: {round_data['projections']['rounds_remaining']}

Generate a complete round report following the specified format."""

    if DEBUG:
        print(f"  Story notes size: {len(story_notes):,} characters")
        print(f"  Prompt size: {len(system_prompt + user_message):,} characters")

    # DRY RUN gate
    if dry_run or DRY_RUN:
        print("  DRY RUN: Skipping LLM call")
        return "DRY_RUN_NARRATIVE_REPORT"

    # Real LLM call
    if not ANTHROPIC_AVAILABLE:
        raise ValueError("Anthropic package not available")

    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found")

    client = anthropic.Anthropic(api_key=api_key)

    # Estimate input tokens (rough: 4 chars per token)
    estimated_input_tokens = (len(system_prompt) + len(user_message)) // 4

    # Acquire tokens from rate limiter
    TOKEN_LIMITER.acquire(estimated_input_tokens, label=f"TEG{teg_num}_R{round_num}_narrative")

    message = safe_create_message(
        client,
        model="claude-sonnet-4-5",
        max_tokens=4000,
        system=[{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"}
        }],
        messages=[{
            "role": "user",
            "content": user_message
        }]
    )

    narrative_report = message.content[0].text
    print(f"  > Narrative report complete ({len(narrative_report)} characters)")

    return narrative_report


def build_round_report_file(teg_num, round_num, story_notes, narrative_report):
    """
    Build complete round report file with story notes + narrative.

    Args:
        teg_num: Tournament number
        round_num: Round number
        story_notes: Structured story notes
        narrative_report: Full narrative report

    Returns:
        Complete markdown content
    """
    content = f"""# TEG {teg_num} - Round {round_num} Report

---

## Story Notes

{story_notes}

---

## Round Report

{narrative_report}

"""

    return content


def generate_complete_round_report(teg_num, round_num, dry_run=False):
    """
    Main function: Generate complete round report (story notes + narrative).

    Args:
        teg_num: Tournament number
        round_num: Round number
        dry_run: If True, skip LLM calls

    Returns:
        Tuple of (story_notes_path, report_path)
    """
    print("\n" + "="*60)
    print(f"GENERATING ROUND REPORT: TEG {teg_num}, Round {round_num}")
    print("="*60)

    # Step 1: Generate story notes
    story_notes = generate_round_story_notes(teg_num, round_num, dry_run)

    # Step 2: Generate narrative report
    narrative_report = generate_round_narrative_report(teg_num, round_num, story_notes, dry_run)

    # Step 3: Save story notes to separate file
    story_notes_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_story_notes.md"
    story_notes_content = f"""# TEG {teg_num} - Round {round_num} Story Notes

{story_notes}

"""

    write_text_file(
        story_notes_path,
        story_notes_content,
        commit_message=f"Generate story notes for TEG {teg_num}, Round {round_num}"
    )

    # Step 4: Save narrative report to separate file
    report_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_report.md"
    report_content = f"""# TEG {teg_num} - Round {round_num} Report

{narrative_report}


"""

    write_text_file(
        report_path,
        report_content,
        commit_message=f"Generate round report for TEG {teg_num}, Round {round_num}"
    )

    # Step 5: Also save combined file for backwards compatibility
    complete_report = build_round_report_file(teg_num, round_num, story_notes, narrative_report)
    combined_path = f"data/commentary/round_reports/teg_{teg_num}_round_{round_num}_report.md"

    write_text_file(
        combined_path,
        complete_report,
        commit_message=f"Generate combined round report for TEG {teg_num}, Round {round_num}"
    )

    print("\n" + "="*60)
    print("ROUND REPORT COMPLETE")
    print("="*60)
    print(f"Story notes saved to: {story_notes_path}")
    print(f"Report saved to: {report_path}")
    print(f"Combined saved to: {combined_path}")
    print(f"Story notes length: {len(story_notes):,} characters")
    print(f"Report length: {len(narrative_report):,} characters")
    print("="*60 + "\n")

    return (story_notes_path, report_path)


def parse_range(range_str):
    """
    Parse a range string like '1-4' or a single number '3'.

    Args:
        range_str: String like '1-4' or '3'

    Returns:
        List of integers
    """
    if '-' in range_str:
        start, end = range_str.split('-')
        return list(range(int(start), int(end) + 1))
    else:
        return [int(range_str)]


def generate_batch_reports(teg_nums, round_nums, dry_run=False, story_notes_only=False, reports_only=False, use_batch_api=False, submit_only=False):
    """
    Generate reports for multiple TEGs and rounds in batch mode.
    Optimized for prompt caching by processing all story notes first, then all reports.

    Args:
        teg_nums: List of TEG numbers to process
        round_nums: List of round numbers to process (applied to each TEG)
        dry_run: If True, skip LLM calls
        story_notes_only: If True, only generate story notes (skip reports)
        reports_only: If True, only generate reports (requires existing story notes)
        use_batch_api: If True, use Anthropic Batch API (50% cheaper, up to 24hr processing)
        submit_only: If True, submit batch and exit (only with use_batch_api=True)

    Returns:
        List of tuples (teg_num, round_num, story_notes_path, report_path)
    """
    # Build list of (teg_num, round_num) tuples to process
    work_items = []
    for teg_num in teg_nums:
        total_rounds = get_teg_rounds(teg_num)
        for round_num in round_nums:
            if round_num < 1 or round_num > total_rounds:
                print(f"Warning: Skipping TEG {teg_num} Round {round_num} (TEG has {total_rounds} rounds)")
                continue
            work_items.append((teg_num, round_num))

    if not work_items:
        print("Error: No valid TEG/round combinations to process")
        return []

    mode_desc = "story notes only" if story_notes_only else "reports only" if reports_only else "full reports"
    batch_desc = " (using Batch API - 50% cheaper, up to 24hr processing)" if use_batch_api else ""
    print("\n" + "="*60)
    print(f"BATCH MODE: Processing {len(work_items)} {mode_desc}{batch_desc}")
    print("="*60)
    for teg_num, round_num in work_items:
        print(f"  - TEG {teg_num}, Round {round_num}")
    print("="*60 + "\n")

    # If using Batch API, delegate to batch processor
    if use_batch_api:
        return generate_batch_reports_via_api(work_items, story_notes_only, reports_only, submit_only)


    # PHASE 1: Generate all story notes (maximizes prompt cache hits)
    story_notes_cache = {}

    if not reports_only:
        print("\n" + "="*60)
        print("PHASE 1: Generating all story notes")
        print("="*60)
        for i, (teg_num, round_num) in enumerate(work_items, 1):
            print(f"\n[{i}/{len(work_items)}] Processing TEG {teg_num}, Round {round_num}")
            try:
                story_notes = generate_round_story_notes(teg_num, round_num, dry_run)
                story_notes_cache[(teg_num, round_num)] = story_notes

                # Save story notes immediately
                story_notes_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_story_notes.md"
                story_notes_content = f"""# TEG {teg_num} - Round {round_num} Story Notes

{story_notes}


"""
                write_text_file(
                    story_notes_path,
                    story_notes_content,
                    commit_message=f"Generate story notes for TEG {teg_num}, Round {round_num}"
                )
                print(f"  > Story notes saved to: {story_notes_path}")
            except Exception as e:
                print(f"  > ERROR: Failed to generate story notes: {e}")
                if DEBUG:
                    import traceback
                    traceback.print_exc()

    # If story-notes-only mode, we're done
    if story_notes_only:
        print("\n" + "="*60)
        print("STORY NOTES GENERATION COMPLETE")
        print("="*60)
        print(f"Successfully processed: {len(story_notes_cache)}/{len(work_items)} story notes")
        for teg_num, round_num in story_notes_cache.keys():
            print(f"  ✓ TEG {teg_num}, Round {round_num}")
        print("="*60 + "\n")
        return [(teg_num, round_num, f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_story_notes.md", None)
                for teg_num, round_num in story_notes_cache.keys()]

    # PHASE 2: Generate all narrative reports (maximizes prompt cache hits)
    # If reports_only mode, load existing story notes
    if reports_only:
        print("\n" + "="*60)
        print("Loading existing story notes")
        print("="*60)
        for i, (teg_num, round_num) in enumerate(work_items, 1):
            story_notes_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_story_notes.md"
            try:
                with open(story_notes_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract just the story notes content (skip header and footer)
                    lines = content.split('\n')
                    # Skip first line (header) and last two lines (footer)
                    story_notes = '\n'.join(lines[2:-3]).strip()
                    story_notes_cache[(teg_num, round_num)] = story_notes
                    print(f"[{i}/{len(work_items)}] Loaded story notes for TEG {teg_num}, Round {round_num}")
            except FileNotFoundError:
                print(f"[{i}/{len(work_items)}] ERROR: Story notes not found for TEG {teg_num}, Round {round_num}")
                print(f"  Expected: {story_notes_path}")
            except Exception as e:
                print(f"[{i}/{len(work_items)}] ERROR loading story notes: {e}")
                if DEBUG:
                    import traceback
                    traceback.print_exc()

    print("\n" + "="*60)
    print("PHASE 2: Generating all narrative reports")
    print("="*60)
    results = []
    for i, (teg_num, round_num) in enumerate(work_items, 1):
        if (teg_num, round_num) not in story_notes_cache:
            print(f"\n[{i}/{len(work_items)}] Skipping TEG {teg_num}, Round {round_num} (story notes failed)")
            continue

        print(f"\n[{i}/{len(work_items)}] Processing TEG {teg_num}, Round {round_num}")
        try:
            story_notes = story_notes_cache[(teg_num, round_num)]

            # Generate narrative report
            narrative_report = generate_round_narrative_report(teg_num, round_num, story_notes, dry_run)

            # Load round data for metadata
            round_data = load_round_report_data(teg_num, round_num)

            # Save narrative report
            report_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_report.md"
            report_content = f"""# TEG {teg_num} - Round {round_num} Report

{narrative_report}


"""
            write_text_file(
                report_path,
                report_content,
                commit_message=f"Generate round report for TEG {teg_num}, Round {round_num}"
            )
            print(f"  > Report saved to: {report_path}")

            # Save combined file for backwards compatibility
            complete_report = build_round_report_file(teg_num, round_num, story_notes, narrative_report)
            combined_path = f"data/commentary/round_reports/teg_{teg_num}_round_{round_num}_report.md"
            write_text_file(
                combined_path,
                complete_report,
                commit_message=f"Generate combined round report for TEG {teg_num}, Round {round_num}"
            )

            story_notes_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_story_notes.md"
            results.append((teg_num, round_num, story_notes_path, report_path))

        except Exception as e:
            print(f"  > ERROR: Failed to generate report: {e}")
            if DEBUG:
                import traceback
                traceback.print_exc()

    # Summary
    print("\n" + "="*60)
    print("BATCH PROCESSING COMPLETE")
    print("="*60)
    print(f"Successfully processed: {len(results)}/{len(work_items)} reports")
    for teg_num, round_num, story_path, report_path in results:
        print(f"  ✓ TEG {teg_num}, Round {round_num}")
    print("="*60 + "\n")

    return results


def generate_batch_reports_via_api(work_items, story_notes_only=False, reports_only=False, submit_only=False):
    """
    Generate reports using Anthropic Batch API (50% cost reduction).

    Args:
        work_items: List of (teg_num, round_num) tuples
        story_notes_only: If True, only generate story notes
        reports_only: If True, only generate reports from existing story notes
        submit_only: If True, submit batch and exit (don't wait for results)

    Returns:
        List of tuples (teg_num, round_num, story_notes_path, report_path)
        OR List of batch_ids if submit_only=True
    """
    print("\n" + "="*60)
    print("BATCH API MODE (50% cost reduction)")
    if submit_only:
        print("SUBMIT ONLY - Will exit after submission")
    print("="*60)

    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables or Streamlit secrets")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    batch_dir = f"streamlit/commentary/batch_requests"
    results_dir = f"streamlit/commentary/batch_results"
    os.makedirs(batch_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    # PHASE 1: Story Notes (if not reports-only)
    story_notes_batch_id = None
    if not reports_only:
        print("\nPHASE 1: Building story notes batch requests...")
        story_notes_requests = []

        for teg_num, round_num in work_items:
            print(f"  Preparing TEG {teg_num}, Round {round_num}...")

            # Load data
            round_data = load_round_report_data(teg_num, round_num)
            storylines = get_round_storylines(round_data)
            data_json = format_round_data_for_prompt(round_data, storylines)

            # Build request
            user_message = f"""Round Data:

{data_json}

Create structured story notes for this round following the specified format."""

            request = create_batch_request(
                custom_id=f"TEG{teg_num}_R{round_num}_story_notes",
                model="claude-sonnet-4-5",
                max_tokens=3000,
                system_prompt=ROUND_STORY_NOTES_PROMPT,
                user_message=user_message,
                use_cache=True
            )
            story_notes_requests.append(request)

        # Save and submit story notes batch
        batch_file = f"{batch_dir}/story_notes_{timestamp}.jsonl"
        save_batch_requests(story_notes_requests, batch_file)

        print("\nSubmitting story notes batch to Anthropic...")
        batch_info = submit_batch(batch_file, api_key)
        story_notes_batch_id = batch_info['batch_id']
        save_batch_info(batch_info, results_dir, batch_type="round_story_notes")

        if submit_only:
            print("\n" + "="*60)
            print("BATCH SUBMITTED - YOU CAN NOW CLOSE THIS WINDOW")
            print("="*60)
            print(f"Story notes batch ID: {story_notes_batch_id}")
            print(f"\nTo retrieve results later, run:")
            print(f"  python generate_round_report.py --retrieve-batch {story_notes_batch_id}")
            print("\nBatch info saved to:")
            print(f"  {results_dir}/batch_{story_notes_batch_id}_info.json")
            print("="*60)
            return [story_notes_batch_id]

        print("\nPolling for story notes completion...")
        poll_until_complete(story_notes_batch_id, api_key, check_interval=60)

        print("\nRetrieving story notes results...")
        story_notes_results = get_batch_results(story_notes_batch_id, api_key, results_dir)

        # Save story notes to files
        print("\nSaving story notes to files...")
        for teg_num, round_num in work_items:
            custom_id = f"TEG{teg_num}_R{round_num}_story_notes"
            if custom_id in story_notes_results and story_notes_results[custom_id]:
                story_notes = story_notes_results[custom_id]
                story_notes_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_story_notes.md"
                story_notes_content = f"""# TEG {teg_num} - Round {round_num} Story Notes

{story_notes}


"""
                write_text_file(
                    story_notes_path,
                    story_notes_content,
                    commit_message=f"Generate story notes for TEG {teg_num}, Round {round_num} (Batch API)"
                )
                print(f"  ✓ Saved: {story_notes_path}")

    # If story-notes-only, we're done
    if story_notes_only:
        print("\n" + "="*60)
        print("STORY NOTES COMPLETE (via Batch API)")
        print("="*60)
        return [(teg, rnd, f"data/commentary/round_reports/TEG{teg}_R{rnd}_story_notes.md", None)
                for teg, rnd in work_items]

    # PHASE 2: Narrative Reports (if not story-notes-only)
    print("\nPHASE 2: Building narrative report batch requests...")
    report_requests = []

    for teg_num, round_num in work_items:
        # Load existing story notes
        story_notes_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_story_notes.md"
        try:
            with open(story_notes_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract just the story notes content (skip header)
                lines = content.split('\n')
                story_notes = '\n'.join(lines[2:-3]).strip()

            # Load round data for metadata
            round_data = load_round_report_data(teg_num, round_num)

            user_message = f"""Story Notes:

{story_notes}

Tournament Context:
- TEG Number: {teg_num}
- Round Number: {round_num}
- Course: {round_data['metadata']['course']}
- Date: {round_data['metadata']['date']}
- Rounds Remaining: {round_data['projections']['rounds_remaining']}

Generate a complete round report following the specified format."""

            request = create_batch_request(
                custom_id=f"TEG{teg_num}_R{round_num}_narrative",
                model="claude-sonnet-4-5",
                max_tokens=4000,
                system_prompt=ROUND_REPORT_PROMPT,
                user_message=user_message,
                use_cache=True
            )
            report_requests.append(request)
            print(f"  Prepared TEG {teg_num}, Round {round_num}")

        except FileNotFoundError:
            print(f"  ✗ Story notes not found for TEG {teg_num}, Round {round_num}")

    # Save and submit narrative reports batch
    batch_file = f"{batch_dir}/narrative_reports_{timestamp}.jsonl"
    save_batch_requests(report_requests, batch_file)

    print("\nSubmitting narrative reports batch to Anthropic...")
    batch_info = submit_batch(batch_file, api_key)
    reports_batch_id = batch_info['batch_id']
    save_batch_info(batch_info, results_dir, batch_type="round_narrative_reports")

    if submit_only:
        print("\n" + "="*60)
        print("BATCH SUBMITTED - YOU CAN NOW CLOSE THIS WINDOW")
        print("="*60)
        print(f"Narrative reports batch ID: {reports_batch_id}")
        if story_notes_batch_id:
            print(f"Story notes batch ID: {story_notes_batch_id}")
        print(f"\nTo retrieve results later, run:")
        print(f"  python generate_round_report.py --retrieve-batch {reports_batch_id}")
        if story_notes_batch_id:
            print(f"  python generate_round_report.py --retrieve-batch {story_notes_batch_id}")
        print("\nBatch info saved to:")
        print(f"  {results_dir}/batch_{reports_batch_id}_info.json")
        print("="*60)
        return [story_notes_batch_id, reports_batch_id] if story_notes_batch_id else [reports_batch_id]

    print("\nPolling for narrative reports completion...")
    poll_until_complete(reports_batch_id, api_key, check_interval=60)

    print("\nRetrieving narrative report results...")
    report_results = get_batch_results(reports_batch_id, api_key, results_dir)

    # Save reports to files
    print("\nSaving narrative reports to files...")
    results = []
    for teg_num, round_num in work_items:
        custom_id = f"TEG{teg_num}_R{round_num}_narrative"
        if custom_id in report_results and report_results[custom_id]:
            narrative_report = report_results[custom_id]

            # Save narrative report
            report_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_report.md"
            report_content = f"""# TEG {teg_num} - Round {round_num} Report

{narrative_report}


"""
            write_text_file(
                report_path,
                report_content,
                commit_message=f"Generate round report for TEG {teg_num}, Round {round_num} (Batch API)"
            )

            # Also save combined file for backwards compatibility
            story_notes_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_story_notes.md"
            with open(story_notes_path, 'r', encoding='utf-8') as f:
                story_notes_content = f.read()
                story_notes = '\n'.join(story_notes_content.split('\n')[2:-3]).strip()

            complete_report = build_round_report_file(teg_num, round_num, story_notes, narrative_report)
            combined_path = f"data/commentary/round_reports/teg_{teg_num}_round_{round_num}_report.md"
            write_text_file(
                combined_path,
                complete_report,
                commit_message=f"Generate combined round report for TEG {teg_num}, Round {round_num} (Batch API)"
            )

            results.append((teg_num, round_num, story_notes_path, report_path))
            print(f"  ✓ Saved: {report_path}")

    # Summary
    print("\n" + "="*60)
    print("BATCH API PROCESSING COMPLETE")
    print("="*60)
    print(f"Successfully processed: {len(results)}/{len(work_items)} reports")
    print(f"Cost savings: ~50% compared to standard API")
    if story_notes_batch_id:
        print(f"Story notes batch ID: {story_notes_batch_id}")
    print(f"Reports batch ID: {reports_batch_id}")
    print("="*60 + "\n")

    return results


def retrieve_batch_results_round_reports(batch_id):
    """
    Retrieve results from a previously submitted batch.

    Args:
        batch_id: Batch ID to retrieve

    Returns:
        Results dict or None if batch not complete
    """
    print("\n" + "="*60)
    print(f"RETRIEVING BATCH RESULTS: {batch_id}")
    print("="*60)

    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found")

    results_dir = "streamlit/commentary/batch_results"

    # Check status first
    print("\nChecking batch status...")
    status = check_batch_status(batch_id, api_key)
    print(f"  Status: {status['status']}")
    print(f"  Request counts: {status['request_counts']}")

    if status['status'] != 'ended':
        print(f"\n⚠️  Batch not complete yet. Current status: {status['status']}")
        print(f"Check again later or run:")
        print(f"  python generate_round_report.py --retrieve-batch {batch_id}")
        return None

    # Load batch info to determine type
    batch_info_file = find_batch_info_file(batch_id, results_dir)
    if not batch_info_file:
        print(f"\n⚠️  Warning: Batch info file not found for {batch_id}")
        print("Proceeding with retrieval anyway...")
        batch_type = "unknown"
    else:
        batch_info = load_batch_info(batch_info_file)
        batch_type = batch_info.get('batch_type', 'unknown')
        print(f"  Batch type: {batch_type}")

    # Retrieve results
    print("\nRetrieving results...")
    results = get_batch_results(batch_id, api_key, results_dir)

    # Save results to appropriate files based on batch type
    print("\nSaving results to files...")

    if batch_type == "round_story_notes":
        # Parse custom_ids and save story notes
        for custom_id, content in results.items():
            if content is None:
                continue
            # Parse TEG{num}_R{num}_story_notes
            parts = custom_id.split('_')
            if len(parts) >= 3:
                teg_num = int(parts[0].replace('TEG', ''))
                round_num = int(parts[1].replace('R', ''))

                story_notes_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_story_notes.md"
                story_notes_content = f"""# TEG {teg_num} - Round {round_num} Story Notes

{content}


"""
                write_text_file(
                    story_notes_path,
                    story_notes_content,
                    commit_message=f"Generate story notes for TEG {teg_num}, Round {round_num} (Batch API)"
                )
                print(f"  ✓ Saved: {story_notes_path}")

    elif batch_type == "round_narrative_reports":
        # Parse custom_ids and save narrative reports
        for custom_id, content in results.items():
            if content is None:
                continue
            # Parse TEG{num}_R{num}_narrative
            parts = custom_id.split('_')
            if len(parts) >= 3:
                teg_num = int(parts[0].replace('TEG', ''))
                round_num = int(parts[1].replace('R', ''))

                # Save narrative report
                report_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_report.md"
                report_content = f"""# TEG {teg_num} - Round {round_num} Report

{content}


"""
                write_text_file(
                    report_path,
                    report_content,
                    commit_message=f"Generate round report for TEG {teg_num}, Round {round_num} (Batch API)"
                )

                # Also save combined file
                story_notes_path = f"data/commentary/round_reports/TEG{teg_num}_R{round_num}_story_notes.md"
                if os.path.exists(story_notes_path):
                    with open(story_notes_path, 'r', encoding='utf-8') as f:
                        story_notes_content = f.read()
                        story_notes = '\n'.join(story_notes_content.split('\n')[2:-3]).strip()

                    complete_report = build_round_report_file(teg_num, round_num, story_notes, content)
                    combined_path = f"data/commentary/round_reports/teg_{teg_num}_round_{round_num}_report.md"
                    write_text_file(
                        combined_path,
                        complete_report,
                        commit_message=f"Generate combined round report for TEG {teg_num}, Round {round_num} (Batch API)"
                    )

                print(f"  ✓ Saved: {report_path}")

    else:
        print(f"  ⚠️  Unknown batch type '{batch_type}' - results saved to {results_dir} but not processed")

    print("\n" + "="*60)
    print("BATCH RETRIEVAL COMPLETE")
    print("="*60)
    print(f"Retrieved: {len([r for r in results.values() if r is not None])}/{len(results)} successful")
    print("="*60)

    return results


def list_pending_batches():
    """
    List all recent batch submissions and their status.
    """
    print("\n" + "="*60)
    print("RECENT BATCH SUBMISSIONS")
    print("="*60)

    batches = list_recent_batches()

    if not batches:
        print("No batch submissions found.")
        return

    api_key = get_api_key()
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not found - showing cached info only")

    for i, batch in enumerate(batches, 1):
        print(f"\n{i}. Batch ID: {batch['batch_id']}")
        print(f"   Type: {batch.get('batch_type', 'unknown')}")
        print(f"   Created: {batch.get('created_at', 'unknown')}")

        # Try to get current status if API key available
        if api_key:
            try:
                status = check_batch_status(batch['batch_id'], api_key)
                print(f"   Status: {status['status']}")
                print(f"   Progress: {status['request_counts']}")
            except Exception as e:
                print(f"   Status: Error checking status - {e}")
        else:
            print(f"   Status: {batch.get('status', 'unknown')} (cached)")

        print(f"   To retrieve: python generate_round_report.py --retrieve-batch {batch['batch_id']}")

    print("\n" + "="*60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Generate round reports for live tournament analysis',
        epilog='''
Examples:
  # Generate report for single TEG and round
  python %(prog)s --teg 17 --round 2

  # Generate reports for range of rounds in a single TEG
  python %(prog)s --teg 17 --round 1-4

  # Generate reports for range of TEGs and rounds
  python %(prog)s --teg 15-17 --round 1-4

  # Only generate story notes (first phase)
  python %(prog)s --teg 17 --round 1-4 --story-notes-only

  # Only generate reports from existing story notes (second phase)
  python %(prog)s --teg 17 --round 1-4 --reports-only

  # Test without LLM calls
  python %(prog)s --teg 17 --round 2 --dry-run

  # Backwards compatible: single arguments (deprecated)
  python %(prog)s 17 2
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # New flag-based arguments (recommended)
    parser.add_argument('--teg', type=str, help='TEG number or range (e.g., "17" or "15-17")')
    parser.add_argument('--round', type=str, help='Round number or range (e.g., "2" or "1-4")')
    parser.add_argument('--dry-run', action='store_true', help='Test without LLM calls')
    parser.add_argument('--story-notes-only', action='store_true', help='Only generate story notes (skip reports)')
    parser.add_argument('--reports-only', action='store_true', help='Only generate reports (requires existing story notes)')
    parser.add_argument('--use-batch', action='store_true', help='Use Anthropic Batch API (50%% cheaper, up to 24hr processing)')
    parser.add_argument('--submit-only', action='store_true', help='Submit batch and exit (retrieve results later with --retrieve-batch)')
    parser.add_argument('--retrieve-batch', type=str, metavar='BATCH_ID', help='Retrieve results from previously submitted batch')
    parser.add_argument('--list-batches', action='store_true', help='List recent batch submissions and their status')

    # Backwards compatible positional arguments
    parser.add_argument('teg_num', type=int, nargs='?', help='Tournament number (deprecated: use --teg)')
    parser.add_argument('round_num', type=int, nargs='?', help='Round number (deprecated: use --round)')

    args = parser.parse_args()

    # Handle list-batches command
    if args.list_batches:
        list_pending_batches()
        sys.exit(0)

    # Handle retrieve-batch command
    if args.retrieve_batch:
        retrieve_batch_results_round_reports(args.retrieve_batch)
        sys.exit(0)

    # Validate mutually exclusive flags
    if args.story_notes_only and args.reports_only:
        print("Error: --story-notes-only and --reports-only cannot be used together")
        sys.exit(1)

    # Handle backwards compatibility
    if args.teg_num is not None and args.round_num is not None:
        # Old style: positional arguments
        teg_nums = [args.teg_num]
        round_nums = [args.round_num]
    elif args.teg and args.round:
        # New style: flag-based with ranges
        teg_nums = parse_range(args.teg)
        round_nums = parse_range(args.round)
    else:
        parser.print_help()
        print("\nError: Must provide either --teg and --round, or positional teg_num and round_num")
        sys.exit(1)

    # Batch mode if multiple items, otherwise single mode
    if len(teg_nums) == 1 and len(round_nums) == 1:
        # Single report mode
        teg_num = teg_nums[0]
        round_num = round_nums[0]

        # Validate round number
        total_rounds = get_teg_rounds(teg_num)
        if round_num < 1 or round_num > total_rounds:
            print(f"Error: TEG {teg_num} has {total_rounds} rounds. Round {round_num} is invalid.")
            sys.exit(1)

        # Generate report
        try:
            output_path = generate_complete_round_report(teg_num, round_num, dry_run=args.dry_run)
            print(f"\nSuccess! Report saved to: {output_path}")
        except Exception as e:
            print(f"\nError generating report: {e}")
            if DEBUG:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    else:
        # Batch mode
        try:
            results = generate_batch_reports(
                teg_nums,
                round_nums,
                dry_run=args.dry_run,
                story_notes_only=args.story_notes_only,
                reports_only=args.reports_only,
                use_batch_api=args.use_batch,
                submit_only=args.submit_only
            )
            if not results:
                sys.exit(1)
        except Exception as e:
            print(f"\nError in batch processing: {e}")
            if DEBUG:
                import traceback
                traceback.print_exc()
            sys.exit(1)
