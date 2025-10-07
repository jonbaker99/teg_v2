"""
Golf Tournament Commentary Generator

Generates entertaining newspaper-style reports from tournament data using a
3-stage pipeline: Data Synthesis → Story Architecture → Journalism
"""

import pandas as pd
import json
from typing import Dict, Any, Optional, List
import anthropic
import os
from prompts import (
    STORY_ARCHITECT_PROMPT,
    GOLF_JOURNALIST_PROMPT,
    BRIEF_SUMMARY_PROMPT,
    PLAYER_PROFILES_PROMPT
)

# Import player dictionary if available
try:
    from player_dictionary import PLAYER_DICTIONARY
except ImportError:
    PLAYER_DICTIONARY = {}


def load_tournament_data(
    teg_num: int,
    tournament_summary_path: str,
    round_summary_path: str,
    events_path: Optional[str] = None,
    tournament_streaks_path: Optional[str] = None,
    round_streaks_path: Optional[str] = None,
    all_data_path: Optional[str] = None,
    winners_csv_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Load and filter tournament data from parquet/CSV files.
    Only extracts essential fields to minimize token usage.

    Args:
        teg_num: Tournament number (e.g., 17 for TEG 17)
        tournament_summary_path: Path to tournament summary parquet/CSV
        round_summary_path: Path to round summary parquet/CSV
        events_path: Optional path to events parquet/CSV
        tournament_streaks_path: Optional path to tournament streaks parquet/CSV
        round_streaks_path: Optional path to round streaks parquet/CSV
        all_data_path: Optional path to all-data.parquet for hole-by-hole data
        winners_csv_path: Optional path to teg_winners.csv for historical win counts

    Returns:
        Dictionary containing filtered tournament data
    """
    # Helper to read either parquet or CSV
    def read_file(path: str) -> pd.DataFrame:
        if path.endswith('.parquet'):
            return pd.read_parquet(path)
        else:
            return pd.read_csv(path)

    # Load and filter tournament summary - only essential fields
    tourney_df = read_file(tournament_summary_path)
    tourney_df = tourney_df[tourney_df['TEGNum'] == teg_num]

    # Select only key tournament fields
    tourney_cols = [
        'TEG', 'Player', 'Year',
        # Stableford (primary)
        'Tournament_Score_Stableford', 'Final_Rank_Stableford', 'Final_Gap_Stableford',
        'Won_Stableford', 'Margin_Stableford', 'Wooden_Spoon',
        # Gross (important)
        'Tournament_Score_Gross', 'Final_Rank_Gross', 'Final_Gap_Gross',
        'Won_Gross', 'Margin_Gross',
        # Scoring events
        'Total_Eagles', 'Total_Birdies', 'Total_Bogeys', 'Total_Double_Bogeys',
        # Leadership
        'Total_Holes_In_Lead_Stableford', 'Rounds_Leading_After_Stableford',
        'Total_Holes_In_Lead_Gross', 'Rounds_Leading_After_Gross',
        # Historical context (if exceptional)
        'Rank_Among_Player_TEGs_Stableford', 'Rank_Among_All_TEGs_To_Date_Stableford'
    ]
    tourney_cols = [c for c in tourney_cols if c in tourney_df.columns]
    tourney_data = tourney_df[tourney_cols].to_dict('records')

    # Load and filter round summaries - only essential fields
    rounds_df = read_file(round_summary_path)
    rounds_df = rounds_df[rounds_df['TEGNum'] == teg_num]

    round_cols = [
        'TEG', 'Player', 'Round', 'Date', 'Course',
        # Stableford scoring
        'Round_Score_Stableford', 'Player_Round_Rank_Stableford',
        'Cumulative_Tournament_Rank_Stableford', 'Gap_To_Leader_After_Round_Stableford',
        'Lead_Gained_Count_Stableford', 'Lead_Lost_Count_Stableford',
        # Gross scoring
        'Round_Score_Gross', 'Player_Round_Rank_Gross',
        'Cumulative_Tournament_Rank_Gross', 'Gap_To_Leader_After_Round_Gross',
        # Nine splits
        'Front_9_Score_Stableford', 'Back_9_Score_Stableford',
        # Scoring events
        'Eagles_Count', 'Birdies_Count', 'Triple_Bogeys_Or_Worse_Count'
    ]
    round_cols = [c for c in round_cols if c in rounds_df.columns]
    rounds_data = rounds_df[round_cols].to_dict('records')

    # Load events - filter to only dramatic ones
    events_data = []
    if events_path and os.path.exists(events_path):
        events_df = read_file(events_path)
        events_df = events_df[events_df['TEGNum'] == teg_num]

        # Only include dramatic events
        dramatic_events = events_df[
            (events_df['Event'] == 'Eagle') |
            (events_df['Event'].str.contains('Lead_Change', na=False)) |
            (events_df['Event'].str.contains('Collapse', na=False)) |
            (events_df['Final_Hole_Flag'] == True)
        ]

        event_cols = ['Player', 'Round', 'Hole', 'Event', 'Par', 'GrossVP', 'Stableford']
        event_cols = [c for c in event_cols if c in dramatic_events.columns]
        events_data = dramatic_events[event_cols].to_dict('records')

    # Load streaks - only notable ones (3+ holes)
    tourney_streaks = []
    if tournament_streaks_path and os.path.exists(tournament_streaks_path):
        streaks_df = read_file(tournament_streaks_path)
        streaks_df = streaks_df[
            (streaks_df['TEGNum'] == teg_num) &
            (streaks_df['Max_Streak'] >= 3)
        ]
        streak_cols = ['Player', 'Streak_Type', 'Max_Streak', 'Location']
        streak_cols = [c for c in streak_cols if c in streaks_df.columns]
        tourney_streaks = streaks_df[streak_cols].to_dict('records')

    round_streaks = []
    if round_streaks_path and os.path.exists(round_streaks_path):
        streaks_df = read_file(round_streaks_path)
        streaks_df = streaks_df[
            (streaks_df['TEGNum'] == teg_num) &
            (streaks_df['Max_Streak'] >= 3)
        ]
        streak_cols = ['Player', 'Round', 'Streak_Type', 'Max_Streak', 'Location']
        streak_cols = [c for c in streak_cols if c in streaks_df.columns]
        round_streaks = streaks_df[streak_cols].to_dict('records')

    # Load hole-by-hole data (all-data.parquet)
    hole_by_hole_data = []
    if all_data_path and os.path.exists(all_data_path):
        all_df = read_file(all_data_path)
        all_df = all_df[all_df['TEGNum'] == teg_num]

        # Select only essential hole-by-hole fields
        hole_cols = [
            'Player', 'Round', 'Hole', 'Par',
            'Sc', 'GrossVP', 'Stableford',
            'Rank_Gross', 'Rank_Stableford'
        ]
        hole_cols = [c for c in hole_cols if c in all_df.columns]
        hole_by_hole_data = all_df[hole_cols].to_dict('records')

    # Add player info for players in this tournament
    # IMPORTANT: Calculate wins BEFORE this tournament using teg_winners.csv
    players_in_tournament = set([p['Player'] for p in tourney_data])
    player_info = {}

    # Load winners history if path provided
    wins_before = {}
    if winners_csv_path and os.path.exists(winners_csv_path):
        winners_df = pd.read_csv(winners_csv_path)
        # Extract TEG number from "TEG X" format
        winners_df['TEGNum'] = winners_df['TEG'].str.extract('(\d+)').astype(int)

        # Filter to tournaments BEFORE this one
        historical_winners = winners_df[winners_df['TEGNum'] < teg_num]

        # Count wins for each player in each competition
        for player in players_in_tournament:
            wins_before[player] = {
                'teg_trophy_wins_before': (historical_winners['TEG Trophy'] == player).sum(),
                'green_jacket_wins_before': (historical_winners['Green Jacket'] == player).sum(),
                'wooden_spoons_before': (historical_winners['HMM Wooden Spoon'] == player).sum()
            }

    for player in players_in_tournament:
        base_info = PLAYER_DICTIONARY.get(player, {}).copy()

        # Add historical wins from teg_winners.csv (the source of truth)
        if player in wins_before:
            base_info.update(wins_before[player])
        else:
            # Fallback if no winners CSV
            base_info['teg_trophy_wins_before'] = 0
            base_info['green_jacket_wins_before'] = 0
            base_info['wooden_spoons_before'] = 0

        player_info[player] = base_info

    return {
        'teg_num': teg_num,
        'tournament_summary': tourney_data,
        'round_summaries': rounds_data,
        'events': events_data,
        'tournament_streaks': tourney_streaks,
        'round_streaks': round_streaks,
        'hole_by_hole': hole_by_hole_data,
        'player_info': player_info
    }


def create_story_blueprint(tournament_data: Dict[str, Any], api_key: str) -> str:
    """
    Stage 2: Analyze data and create story blueprint.
    Uses prompt caching to reduce costs for repeated prompts.

    Args:
        tournament_data: Structured tournament data from Stage 1
        api_key: Anthropic API key

    Returns:
        Story blueprint as text
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Format data for LLM
    data_summary = json.dumps(tournament_data, indent=2, default=str)

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        system=[
            {
                "type": "text",
                "text": STORY_ARCHITECT_PROMPT,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"**TOURNAMENT DATA:**\n{data_summary}"
            }
        ]
    )

    return message.content[0].text


def write_tournament_article(story_blueprint: str, tournament_data: Dict[str, Any], api_key: str) -> str:
    """
    Stage 3: Write entertaining tournament article.
    Uses prompt caching to reduce costs for repeated prompts.

    Args:
        story_blueprint: Story architecture from Stage 2
        tournament_data: Original tournament data for reference
        api_key: Anthropic API key

    Returns:
        Final article text
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Include both blueprint and raw data for journalist
    data_summary = json.dumps(tournament_data, indent=2, default=str)

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        system=[
            {
                "type": "text",
                "text": GOLF_JOURNALIST_PROMPT,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"""**STORY BLUEPRINT:**
{story_blueprint}

**TOURNAMENT DATA (for fact-checking):**
{data_summary}

Write the tournament article now."""
            }
        ]
    )

    return message.content[0].text


def generate_brief_summary(tournament_data: Dict[str, Any], api_key: str) -> str:
    """
    Generate a brief 2-3 paragraph tournament summary.
    Uses prompt caching to reduce costs.

    Args:
        tournament_data: Structured tournament data
        api_key: Anthropic API key

    Returns:
        Brief summary as text
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Format data for LLM
    data_summary = json.dumps(tournament_data, indent=2, default=str)

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system=[
            {
                "type": "text",
                "text": BRIEF_SUMMARY_PROMPT,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"**TOURNAMENT DATA:**\n{data_summary}\n\nWrite a brief summary now."
            }
        ]
    )

    return message.content[0].text


def generate_player_profiles(tournament_data: Dict[str, Any], api_key: str) -> str:
    """
    Generate individual player summaries for the tournament.
    Uses prompt caching to reduce costs.

    Args:
        tournament_data: Structured tournament data
        api_key: Anthropic API key

    Returns:
        Player profiles as text (markdown formatted)
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Format data for LLM
    data_summary = json.dumps(tournament_data, indent=2, default=str)

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        system=[
            {
                "type": "text",
                "text": PLAYER_PROFILES_PROMPT,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"**TOURNAMENT DATA:**\n{data_summary}\n\nWrite player profiles now."
            }
        ]
    )

    return message.content[0].text


def generate_tournament_commentary(
    teg_num: int,
    tournament_summary_path: str,
    round_summary_path: str,
    api_key: str,
    events_path: Optional[str] = None,
    tournament_streaks_path: Optional[str] = None,
    round_streaks_path: Optional[str] = None,
    all_data_path: Optional[str] = None,
    winners_csv_path: Optional[str] = None,
    output_path: Optional[str] = None
) -> Dict[str, str]:
    """
    Complete pipeline: Generate tournament commentary from data files.

    Args:
        teg_num: Tournament number
        tournament_summary_path: Path to tournament summary CSV/parquet
        round_summary_path: Path to round summary CSV/parquet
        api_key: Anthropic API key
        events_path: Optional path to events CSV/parquet
        tournament_streaks_path: Optional path to tournament streaks CSV/parquet
        round_streaks_path: Optional path to round streaks CSV/parquet
        all_data_path: Optional path to all-data.parquet for hole-by-hole data
        winners_csv_path: Optional path to teg_winners.csv for historical win counts
        output_path: Optional path to save article markdown file

    Returns:
        Dictionary with 'blueprint' and 'article' keys
    """
    print(f"Generating commentary for TEG {teg_num}...")

    # Stage 1: Load and synthesize data (Python)
    print("Stage 1: Loading tournament data...")
    tournament_data = load_tournament_data(
        teg_num=teg_num,
        tournament_summary_path=tournament_summary_path,
        round_summary_path=round_summary_path,
        events_path=events_path,
        tournament_streaks_path=tournament_streaks_path,
        round_streaks_path=round_streaks_path,
        all_data_path=all_data_path,
        winners_csv_path=winners_csv_path
    )

    # Stage 2: Create story blueprint (LLM)
    print("Stage 2: Creating story blueprint...")
    blueprint = create_story_blueprint(tournament_data, api_key)

    # Stage 3: Write article (LLM)
    print("Stage 3: Writing tournament article...")
    article = write_tournament_article(blueprint, tournament_data, api_key)

    # Save if output path provided
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# TEG {teg_num} Tournament Report\n\n")
            f.write(article)
        print(f"Article saved to: {output_path}")

    return {
        'blueprint': blueprint,
        'article': article
    }


# Example usage
if __name__ == "__main__":
    # This is a template - user will provide actual paths
    result = generate_tournament_commentary(
        teg_num=17,
        tournament_summary_path="path/to/tournament_summary.csv",
        round_summary_path="path/to/round_summary.csv",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        events_path="path/to/events.csv",
        output_path="data/commentary/drafts/teg_17.md"
    )

    print("\n" + "="*80)
    print("ARTICLE:")
    print("="*80)
    print(result['article'])
