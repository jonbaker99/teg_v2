"""
Tournament Commentary Generator V2 - Multi-Pass Story Generation

This module implements the complete two-level multi-pass pipeline:
- Level 1: Process all data types (6 Python passes)
- Level 2: Generate round stories + tournament synthesis (4-5 LLM passes)

Output: story_notes.md files ready for final report generation
"""

import sys
import os
import json
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pattern_analysis import process_all_data_types
from data_loader import load_round_data, get_round_ending_context
from prompts import ROUND_STORY_PROMPT, TOURNAMENT_SYNTHESIS_PROMPT
from utils import get_teg_rounds
import anthropic

# Try to import streamlit for secrets, fall back to environment variables
try:
    import streamlit as st
    def get_api_key():
        """Get API key from Streamlit secrets or environment variable."""
        if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
            return st.secrets['ANTHROPIC_API_KEY']
        return os.getenv('ANTHROPIC_API_KEY')
except ImportError:
    def get_api_key():
        """Get API key from environment variable (when streamlit not available)."""
        return os.getenv('ANTHROPIC_API_KEY')


def generate_round_story(teg_num, round_num, round_data, previous_context):
    """
    Generate story notes for a single round using all 6 data types.

    Args:
        teg_num: Tournament number
        round_num: Round number
        round_data: Output from load_round_data()
        previous_context: Context from previous round (or None for Round 1)

    Returns:
        Tuple of (round_story, ending_context)
    """
    print(f"\n  Generating Round {round_num} story...")

    # Get API key
    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in Streamlit secrets or environment variables")

    client = anthropic.Anthropic(api_key=api_key)

    # Format data for prompt
    round_data_json = json.dumps(round_data, indent=2, default=str)
    previous_context_json = json.dumps(previous_context, indent=2, default=str) if previous_context else "First round of the tournament"

    # Build prompt
    prompt = ROUND_STORY_PROMPT.format(
        round_num=round_num,
        round_data=round_data_json,
        previous_context=previous_context_json
    )

    # LLM call
    print(f"    Calling LLM for Round {round_num}...")
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    round_story = message.content[0].text

    # Extract ending context for next round
    ending_context = get_round_ending_context(round_data)

    print(f"    > Round {round_num} story complete ({len(round_story)} chars)")

    return round_story, ending_context


def generate_tournament_synthesis(round_stories, teg_num):
    """
    Generate tournament-level sections using all round stories.

    Args:
        round_stories: List of round story strings
        teg_num: Tournament number

    Returns:
        Tournament synthesis text (3 sections)
    """
    print(f"\n  Generating tournament synthesis...")

    # Get API key
    api_key = get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in Streamlit secrets or environment variables")

    client = anthropic.Anthropic(api_key=api_key)

    # Load tournament-level data
    tournament_summary = pd.read_parquet('data/commentary_tournament_summary.parquet')
    tournament_summary = tournament_summary[tournament_summary['TEGNum'] == teg_num]

    # Format for prompt
    round_summaries_text = "\n\n".join([
        f"## Round {i+1}\n{story}"
        for i, story in enumerate(round_stories)
    ])

    tournament_data_json = json.dumps(
        tournament_summary.to_dict('records'),
        indent=2,
        default=str
    )

    # Build prompt
    prompt = TOURNAMENT_SYNTHESIS_PROMPT.format(
        round_summaries=round_summaries_text,
        tournament_data=tournament_data_json,
        historical_context="[Historical context placeholder - will be enhanced in future version]"
    )

    # LLM call
    print(f"    Calling LLM for tournament synthesis...")
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )

    synthesis = message.content[0].text

    print(f"    > Tournament synthesis complete ({len(synthesis)} chars)")

    return synthesis


def build_story_notes_file(teg_num, round_stories, synthesis):
    """
    Build the complete story_notes.md content in structured format.

    Args:
        teg_num: Tournament number
        round_stories: List of round notes strings (structured bullets)
        synthesis: Tournament synthesis notes (structured bullets)

    Returns:
        Complete markdown content matching existing story_notes.md format
    """
    content = f"# TEG {teg_num} Story Notes\n\n"

    # Add tournament-level synthesis sections first
    content += synthesis + "\n\n"

    # Add round-by-round notes
    for i, round_notes in enumerate(round_stories, 1):
        content += round_notes + "\n\n"

    return content


def generate_complete_story_notes(teg_num):
    """
    Complete pipeline: Process all data types → Generate round stories → Synthesize.

    Handles variable round counts (TEG 2 = 3 rounds, most = 4 rounds).

    Args:
        teg_num: Tournament number

    Returns:
        Complete story notes content
    """
    print(f"\n{'='*60}")
    print(f"GENERATING STORY NOTES FOR TEG {teg_num}")
    print(f"{'='*60}\n")

    # LEVEL 1: Process all 6 data types (Python - multi-pass)
    print("LEVEL 1: Data Type Processing (6 passes)")
    print("-" * 60)
    all_data = process_all_data_types(teg_num)
    print("> All data types processed")

    # LEVEL 2: Generate round stories (LLM - multi-pass by round)
    print(f"\nLEVEL 2: Round Story Generation")
    print("-" * 60)
    num_rounds = get_teg_rounds(teg_num)
    print(f"Tournament has {num_rounds} rounds")

    round_stories = []
    previous_context = None

    for round_num in range(1, num_rounds + 1):
        # Load data for this round from all 6 sources
        round_data = load_round_data(teg_num, round_num, all_data)

        # Generate round story
        round_story, round_context = generate_round_story(
            teg_num, round_num, round_data, previous_context
        )

        round_stories.append(round_story)
        previous_context = round_context

    print(f"\n> All {num_rounds} round stories complete")

    # LEVEL 2 (continued): Tournament synthesis
    print(f"\nLEVEL 2: Tournament Synthesis")
    print("-" * 60)
    synthesis = generate_tournament_synthesis(round_stories, teg_num)
    print("> Tournament synthesis complete")

    # Build complete story notes file
    story_notes = build_story_notes_file(
        teg_num, round_stories, synthesis
    )

    # Save
    output_path = f"streamlit/commentary/outputs/teg_{teg_num}_story_notes.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(story_notes)

    print(f"\n{'='*60}")
    print(f"STORY NOTES COMPLETE")
    print(f"{'='*60}")
    print(f"\nSaved to: {output_path}")
    print(f"Total rounds: {num_rounds}")
    print(f"Total LLM calls: {num_rounds + 1} ({num_rounds} rounds + 1 synthesis)")
    print(f"Total characters: {len(story_notes):,}")
    print(f"\n{'='*60}\n")

    return story_notes


def generate_story_notes_up_to_round(teg_num, completed_rounds):
    """
    Generate story notes for in-progress tournament.
    Only processes completed rounds.

    Args:
        teg_num: Tournament number
        completed_rounds: Number of completed rounds

    Returns:
        Partial story notes content
    """
    print(f"\n{'='*60}")
    print(f"GENERATING STORY NOTES FOR TEG {teg_num}")
    print(f"(IN PROGRESS - {completed_rounds} rounds completed)")
    print(f"{'='*60}\n")

    # Same process but limit to completed rounds
    print("LEVEL 1: Data Type Processing (6 passes)")
    print("-" * 60)
    all_data = process_all_data_types(teg_num)
    print("> All data types processed")

    print(f"\nLEVEL 2: Round Story Generation ({completed_rounds} rounds)")
    print("-" * 60)

    round_stories = []
    previous_context = None

    for round_num in range(1, completed_rounds + 1):
        round_data = load_round_data(teg_num, round_num, all_data)
        round_story, round_context = generate_round_story(
            teg_num, round_num, round_data, previous_context
        )
        round_stories.append(round_story)
        previous_context = round_context

    print(f"\n> All {completed_rounds} round stories complete")

    # Don't synthesize until tournament complete
    # Just save round notes
    content = f"# TEG {teg_num} Story Notes (In Progress - {completed_rounds} rounds)\n\n"
    content += "**Note:** Tournament synthesis will be added when all rounds are complete.\n\n"

    for i, round_notes in enumerate(round_stories, 1):
        content += round_notes + "\n\n"

    output_path = f"streamlit/commentary/outputs/teg_{teg_num}_story_notes_partial.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n{'='*60}")
    print(f"PARTIAL STORY NOTES COMPLETE")
    print(f"{'='*60}")
    print(f"\nSaved to: {output_path}")
    print(f"Completed rounds: {completed_rounds}")
    print(f"Total LLM calls: {completed_rounds}")
    print(f"Total characters: {len(content):,}")
    print(f"\n{'='*60}\n")

    return content


if __name__ == "__main__":
    # Test with TEG 17
    import argparse

    parser = argparse.ArgumentParser(description='Generate tournament story notes')
    parser.add_argument('teg_num', type=int, help='Tournament number')
    parser.add_argument('--partial', type=int, help='Number of completed rounds (for in-progress tournaments)')

    args = parser.parse_args()

    if args.partial:
        generate_story_notes_up_to_round(args.teg_num, args.partial)
    else:
        generate_complete_story_notes(args.teg_num)
