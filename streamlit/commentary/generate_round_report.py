"""
Round Report Generator

Generates narrative round reports for live tournament analysis.
Follows the proven two-pass LLM architecture:
1. Story Notes Generation (identify storylines from data)
2. Report Generation (transform notes into narrative with forward-looking analysis)

Usage:
    python generate_round_report.py 17 2          # Generate report for TEG 17, Round 2
    python generate_round_report.py 17 2 --dry-run  # Test without LLM calls
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from round_data_loader import load_round_report_data
from round_pattern_analysis import get_round_storylines
from prompts import ROUND_STORY_NOTES_PROMPT, ROUND_REPORT_PROMPT
from utils import get_teg_rounds

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


def get_api_key():
    """Get Anthropic API key from environment or Streamlit secrets."""
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
            return st.secrets['ANTHROPIC_API_KEY']
    except ImportError:
        pass
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
    # Build compact data structure
    prompt_data = {
        'round_info': {
            'teg_num': round_data['teg_num'],
            'round_num': round_data['round_num'],
            'course': round_data['metadata']['course'],
            'date': round_data['metadata']['date'],
            'par': round_data['metadata']['par']
        },
        'round_summary': [
            {
                'player': r['Player'],
                'round_stableford': r['Round_Score_Stableford'],
                'round_gross': r['Round_Score_Gross'],
                'cumulative_stableford': r['Cumulative_Tournament_Score_Stableford'],
                'position_before': r['Cumulative_Tournament_Rank_Before_Round_Stableford'],
                'position_after': r['Cumulative_Tournament_Rank_Stableford'],
                'gap_to_leader': r['Gap_To_Leader_After_Round_Stableford'],
                'front_9': r['Front_9_Score_Stableford'],
                'back_9': r['Back_9_Score_Stableford']
            }
            for r in round_data['round_summary']
        ],
        'six_hole_splits': round_data['six_hole_splits'],
        'hole_difficulty': round_data['hole_difficulty'],
        'previous_round_scores': round_data['previous_round_scores'],
        'key_events': [
            {
                'hole': e.get('Hole'),
                'player': e.get('Player'),
                'event': e.get('Event'),
                'par': e.get('Par'),
                'score': e.get('Sc'),
                'gross_vp': e.get('GrossVP'),
                'stableford': e.get('Stableford')
            }
            for e in round_data['events']
            if e.get('Event') in ['Eagle', 'Zero_Stableford_Points', 'Lead_Change_Stableford']
        ],
        'streaks': [
            {
                'player': s.get('Player'),
                'type': s.get('StreakType'),
                'length': s.get('StreakLength'),
                'start_hole': s.get('StartHole'),
                'end_hole': s.get('EndHole')
            }
            for s in round_data['streaks']
            if s.get('StreakLength', 0) >= 3  # Only significant streaks
        ],
        'storylines': storylines,
        'projections': round_data['projections']
    }

    return json.dumps(prompt_data, indent=2, default=str)


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

    message = client.messages.create(
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

    message = client.messages.create(
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

---

*Generated by Round Report System*
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
        Path to saved report file
    """
    print("\n" + "="*60)
    print(f"GENERATING ROUND REPORT: TEG {teg_num}, Round {round_num}")
    print("="*60)

    # Step 1: Generate story notes
    story_notes = generate_round_story_notes(teg_num, round_num, dry_run)

    # Step 2: Generate narrative report
    narrative_report = generate_round_narrative_report(teg_num, round_num, story_notes, dry_run)

    # Step 3: Build complete file
    complete_report = build_round_report_file(teg_num, round_num, story_notes, narrative_report)

    # Step 4: Save to file
    output_dir = Path("data/commentary/round_reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"teg_{teg_num}_round_{round_num}_report.md"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(complete_report)

    print("\n" + "="*60)
    print("ROUND REPORT COMPLETE")
    print("="*60)
    print(f"Saved to: {output_path}")
    print(f"Total length: {len(complete_report):,} characters")
    print("="*60 + "\n")

    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Generate round reports for live tournament analysis',
        epilog='''
Examples:
  # Generate report for TEG 17, Round 2
  python %(prog)s 17 2

  # Test without LLM calls
  python %(prog)s 17 2 --dry-run

  # Generate reports for multiple rounds
  python %(prog)s 17 1
  python %(prog)s 17 2
  python %(prog)s 17 3
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('teg_num', type=int, help='Tournament number')
    parser.add_argument('round_num', type=int, help='Round number')
    parser.add_argument('--dry-run', action='store_true', help='Test without LLM calls')

    args = parser.parse_args()

    # Validate round number
    total_rounds = get_teg_rounds(args.teg_num)
    if args.round_num < 1 or args.round_num > total_rounds:
        print(f"Error: TEG {args.teg_num} has {total_rounds} rounds. Round {args.round_num} is invalid.")
        sys.exit(1)

    # Generate report
    try:
        output_path = generate_complete_round_report(args.teg_num, args.round_num, dry_run=args.dry_run)
        print(f"\nSuccess! Report saved to: {output_path}")
    except Exception as e:
        print(f"\nError generating report: {e}")
        if DEBUG:
            import traceback
            traceback.print_exc()
        sys.exit(1)
