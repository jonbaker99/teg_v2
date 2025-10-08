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
from utils import get_teg_rounds, write_text_file

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

    # Step 4: Save to file using Railway-aware function
    output_path = f"data/commentary/round_reports/teg_{teg_num}_round_{round_num}_report.md"

    write_text_file(
        output_path,
        complete_report,
        commit_message=f"Generate round report for TEG {teg_num}, Round {round_num}"
    )

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
