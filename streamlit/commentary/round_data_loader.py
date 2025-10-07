"""
Round Report Data Loader

This module loads and prepares all data needed for round-level reports.
Designed for live tournament analysis with forward-looking projections.

Key functions:
- load_round_report_data(): Main data assembly
- calculate_hole_by_hole_positions(): Position changes through the round
- calculate_tournament_projections(): Forward-looking "what's at stake" math
- calculate_hole_difficulty(): Average scoring on each hole
"""

import pandas as pd
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils import get_teg_rounds


def calculate_six_hole_splits(round_data_df):
    """
    Calculate scoring for 1st, 2nd, and 3rd six-hole segments.

    Args:
        round_data_df: DataFrame with hole-by-hole data for a round

    Returns:
        Dict with player -> {first_six, second_six, third_six} Stableford scores
    """
    splits = {}

    for player in round_data_df['Player'].unique():
        player_data = round_data_df[round_data_df['Player'] == player].sort_values('Hole')

        first_six = player_data[player_data['Hole'].between(1, 6)]['Stableford'].sum()
        second_six = player_data[player_data['Hole'].between(7, 12)]['Stableford'].sum()
        third_six = player_data[player_data['Hole'].between(13, 18)]['Stableford'].sum()

        splits[player] = {
            'first_six': int(first_six),
            'second_six': int(second_six),
            'third_six': int(third_six)
        }

    return splits


def calculate_hole_difficulty(round_data_df):
    """
    Calculate average score on each hole (all players).

    Args:
        round_data_df: DataFrame with hole-by-hole data for a round

    Returns:
        List of dicts with hole stats: hole, par, avg_score, avg_vs_par, avg_stableford
    """
    hole_stats = []

    for hole in range(1, 19):
        hole_data = round_data_df[round_data_df['Hole'] == hole]

        if len(hole_data) > 0:
            par = hole_data['PAR'].iloc[0]
            avg_score = hole_data['Sc'].mean()
            avg_vs_par = hole_data['GrossVP'].mean()
            avg_stableford = hole_data['Stableford'].mean()

            hole_stats.append({
                'hole': hole,
                'par': int(par),
                'avg_score': round(avg_score, 2),
                'avg_vs_par': round(avg_vs_par, 2),
                'avg_stableford': round(avg_stableford, 2),
                'hardest': avg_vs_par == round_data_df.groupby('Hole')['GrossVP'].mean().max(),
                'easiest': avg_vs_par == round_data_df.groupby('Hole')['GrossVP'].mean().min()
            })

    return sorted(hole_stats, key=lambda x: x['hole'])


def get_previous_round_scores(teg_num, round_num):
    """
    Get scores from the previous round (Round N-1) for comparison.

    Args:
        teg_num: Tournament number
        round_num: Current round number

    Returns:
        Dict with player -> {prev_stableford, prev_gross, prev_rank} or None if Round 1
    """
    if round_num == 1:
        return None

    # Load round summary data
    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')

    # Filter to previous round
    prev_round_data = round_summary[
        (round_summary['TEGNum'] == teg_num) &
        (round_summary['Round'] == round_num - 1)
    ]

    if len(prev_round_data) == 0:
        return None

    prev_scores = {}
    for _, row in prev_round_data.iterrows():
        prev_scores[row['Player']] = {
            'prev_round_stableford': int(row['Round_Score_Stableford']),
            'prev_round_gross': int(row['Round_Score_Gross']),
            'prev_round_rank_stableford': int(row['Player_Round_Rank_Stableford']),
            'prev_round_rank_gross': int(row['Player_Round_Rank_Gross'])
        }

    return prev_scores


def calculate_hole_by_hole_positions(teg_num, round_num):
    """
    Calculate tournament position after each hole in the round.
    Uses cumulative Stableford scores through the round.

    Args:
        teg_num: Tournament number
        round_num: Current round number

    Returns:
        DataFrame with columns: Player, Hole, Cumulative_Stableford, Position, Position_Change
    """
    # Load hole-by-hole data
    all_data = pd.read_parquet('data/all-scores.parquet')
    round_data = all_data[
        (all_data['TEGNum'] == teg_num) &
        (all_data['Round'] == round_num)
    ].copy()

    # Load round summary for tournament standings before this round
    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')
    before_round = round_summary[
        (round_summary['TEGNum'] == teg_num) &
        (round_summary['Round'] == round_num)
    ][['Player', 'Cumulative_Tournament_Rank_Before_Round_Stableford']].copy()

    # Calculate cumulative Stableford through the round
    round_data = round_data.sort_values(['Player', 'Hole'])
    round_data['Round_Cumulative_Stableford'] = round_data.groupby('Player')['Stableford'].cumsum()

    # For each hole, get tournament cumulative (previous rounds + this round so far)
    # Get starting totals (before this round)
    if round_num > 1:
        prev_totals = round_summary[
            (round_summary['TEGNum'] == teg_num) &
            (round_summary['Round'] == round_num)
        ][['Player', 'Cumulative_Tournament_Score_Stableford', 'Round_Score_Stableford']].copy()

        # Starting total = cumulative - this round's final score
        prev_totals['Starting_Total'] = prev_totals['Cumulative_Tournament_Score_Stableford'] - prev_totals['Round_Score_Stableford']
        starting_totals = dict(zip(prev_totals['Player'], prev_totals['Starting_Total']))
    else:
        # Round 1: starting total is 0
        starting_totals = {player: 0 for player in round_data['Player'].unique()}

    # Add starting total + round cumulative
    round_data['Tournament_Cumulative_Stableford'] = round_data.apply(
        lambda row: starting_totals.get(row['Player'], 0) + row['Round_Cumulative_Stableford'],
        axis=1
    )

    # Calculate position after each hole
    position_data = []

    for hole in range(1, 19):
        hole_data = round_data[round_data['Hole'] == hole].copy()

        # Rank by tournament cumulative (descending)
        hole_data = hole_data.sort_values('Tournament_Cumulative_Stableford', ascending=False)
        hole_data['Position'] = range(1, len(hole_data) + 1)

        for _, row in hole_data.iterrows():
            position_data.append({
                'Player': row['Player'],
                'Hole': hole,
                'Round_Cumulative_Stableford': int(row['Round_Cumulative_Stableford']),
                'Tournament_Cumulative_Stableford': int(row['Tournament_Cumulative_Stableford']),
                'Position': int(row['Position'])
            })

    positions_df = pd.DataFrame(position_data)

    # Calculate position changes from start of round
    starting_positions = dict(zip(before_round['Player'], before_round['Cumulative_Tournament_Rank_Before_Round_Stableford']))
    positions_df['Starting_Position'] = positions_df['Player'].map(starting_positions)
    positions_df['Position_Change'] = positions_df['Starting_Position'] - positions_df['Position']  # Positive = moved up

    return positions_df


def calculate_tournament_projections(teg_num, round_num):
    """
    Calculate forward-looking projections for "What's At Stake" analysis.

    Args:
        teg_num: Tournament number
        round_num: Round number just completed

    Returns:
        Dict with projection data:
        - rounds_remaining
        - max_possible_points_remaining (per player)
        - gaps_analysis (catchable vs insurmountable)
        - what_each_player_needs
    """
    # Get total rounds for this TEG
    total_rounds = get_teg_rounds(teg_num)
    rounds_remaining = total_rounds - round_num

    # Load current standings after this round
    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')
    current_standings = round_summary[
        (round_summary['TEGNum'] == teg_num) &
        (round_summary['Round'] == round_num)
    ].sort_values('Cumulative_Tournament_Rank_Stableford')

    if len(current_standings) == 0:
        return None

    # Maximum possible points per round = 108 (18 holes × 6 points)
    max_points_per_round = 108
    max_possible_total = rounds_remaining * max_points_per_round

    # Get leader's current total
    leader = current_standings.iloc[0]
    leader_total = leader['Cumulative_Tournament_Score_Stableford']
    leader_name = leader['Player']

    # Analysis for each player
    player_projections = []

    for _, row in current_standings.iterrows():
        player_total = row['Cumulative_Tournament_Score_Stableford']
        gap_to_leader = row['Gap_To_Leader_After_Round_Stableford']

        # Can this player catch the leader?
        max_possible_final = player_total + max_possible_total
        leader_current = leader_total

        # Assume leader averages 60 points/round (reasonable target)
        leader_projected_total = leader_current + (rounds_remaining * 60)

        # What average does this player need per round to catch leader?
        if rounds_remaining > 0:
            points_needed_to_tie = gap_to_leader + 1  # Need to beat, not tie
            avg_per_round_needed = points_needed_to_tie / rounds_remaining
        else:
            avg_per_round_needed = None

        # Is it mathematically possible?
        mathematically_possible = max_possible_final > leader_projected_total

        # Is it realistically catchable? (need <50 points/round average)
        realistically_catchable = avg_per_round_needed is not None and avg_per_round_needed < 50

        player_projections.append({
            'player': row['Player'],
            'current_position': int(row['Cumulative_Tournament_Rank_Stableford']),
            'current_total': int(player_total),
            'gap_to_leader': int(gap_to_leader) if gap_to_leader > 0 else 0,
            'max_possible_total': int(max_possible_final),
            'points_per_round_needed': round(avg_per_round_needed, 1) if avg_per_round_needed else None,
            'mathematically_possible': mathematically_possible,
            'realistically_catchable': realistically_catchable
        })

    return {
        'rounds_remaining': rounds_remaining,
        'max_points_per_round': max_points_per_round,
        'total_rounds': total_rounds,
        'round_just_completed': round_num,
        'leader': leader_name,
        'leader_total': int(leader_total),
        'player_projections': player_projections
    }


def load_round_report_data(teg_num, round_num):
    """
    Main data assembly function for round reports.
    Loads all necessary data for round narrative generation.

    Args:
        teg_num: Tournament number
        round_num: Round number

    Returns:
        Dict with complete round data:
        - round_summary: Round scores, standings, gaps
        - hole_by_hole: All hole-by-hole scoring
        - events: Eagles, disasters, key moments
        - streaks: Birdie runs, bogey-free, disasters
        - six_hole_splits: Scores for holes 1-6, 7-12, 13-18
        - hole_difficulty: Average scoring on each hole
        - previous_round_scores: Scores from Round N-1
        - positions_through_round: Position after each hole
        - projections: Forward-looking "what's at stake" data
        - metadata: Course, date, rounds remaining
    """
    print(f"Loading round report data for TEG {teg_num}, Round {round_num}...")

    # 1. Load round summary data
    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')
    round_summary_data = round_summary[
        (round_summary['TEGNum'] == teg_num) &
        (round_summary['Round'] == round_num)
    ]

    if len(round_summary_data) == 0:
        raise ValueError(f"No data found for TEG {teg_num}, Round {round_num}")

    # 2. Load hole-by-hole data
    all_scores = pd.read_parquet('data/all-scores.parquet')
    round_holes = all_scores[
        (all_scores['TEGNum'] == teg_num) &
        (all_scores['Round'] == round_num)
    ]

    # 3. Load events data
    events = pd.read_parquet('data/commentary_round_events.parquet')
    round_events = events[
        (events['TEGNum'] == teg_num) &
        (events['Round'] == round_num)
    ]

    # 4. Load streaks (round-level)
    round_streaks = pd.read_parquet('data/commentary_round_streaks.parquet')
    streaks_data = round_streaks[
        (round_streaks['TEGNum'] == teg_num) &
        (round_streaks['Round'] == round_num)
    ]

    # 5. Calculate six-hole splits
    six_hole_splits = calculate_six_hole_splits(round_holes)

    # 6. Calculate hole difficulty
    hole_difficulty = calculate_hole_difficulty(round_holes)

    # 7. Get previous round scores
    prev_round_scores = get_previous_round_scores(teg_num, round_num)

    # 8. Calculate hole-by-hole positions
    positions_through_round = calculate_hole_by_hole_positions(teg_num, round_num)

    # 9. Calculate tournament projections
    projections = calculate_tournament_projections(teg_num, round_num)

    # 10. Get metadata
    round_info = pd.read_csv('data/round_info.csv')
    metadata = round_info[
        (round_info['TEGNum'] == teg_num) &
        (round_info['Round'] == round_num)
    ]

    if len(metadata) > 0:
        metadata_dict = {
            'course': metadata['Course'].iloc[0],
            'date': metadata['Date'].iloc[0],
            'area': metadata['Area'].iloc[0],
            'par': metadata['PAR'].iloc[0] if 'PAR' in metadata.columns else 72
        }
    else:
        metadata_dict = {'course': 'Unknown', 'date': 'Unknown', 'area': 'Unknown', 'par': 72}

    print(f"  > Loaded round summary ({len(round_summary_data)} players)")
    print(f"  > Loaded hole-by-hole data ({len(round_holes)} holes)")
    print(f"  > Loaded events ({len(round_events)} events)")
    print(f"  > Loaded streaks ({len(streaks_data)} streaks)")
    print(f"  > Calculated six-hole splits")
    print(f"  > Calculated hole difficulty")
    print(f"  > Calculated positions through round")
    print(f"  > Calculated tournament projections ({projections['rounds_remaining']} rounds remaining)")

    return {
        'teg_num': teg_num,
        'round_num': round_num,
        'round_summary': round_summary_data.to_dict('records'),
        'hole_by_hole': round_holes.to_dict('records'),
        'events': round_events.to_dict('records'),
        'streaks': streaks_data.to_dict('records'),
        'six_hole_splits': six_hole_splits,
        'hole_difficulty': hole_difficulty,
        'previous_round_scores': prev_round_scores,
        'positions_through_round': positions_through_round.to_dict('records'),
        'projections': projections,
        'metadata': metadata_dict
    }


if __name__ == "__main__":
    # Test with TEG 17, Round 2
    print("\n" + "="*60)
    print("TESTING ROUND DATA LOADER - TEG 17, Round 2")
    print("="*60 + "\n")

    round_data = load_round_report_data(17, 2)

    print("\n" + "="*60)
    print("DATA SUMMARY")
    print("="*60)
    print(f"TEG: {round_data['teg_num']}")
    print(f"Round: {round_data['round_num']}")
    print(f"Course: {round_data['metadata']['course']}")
    print(f"Date: {round_data['metadata']['date']}")
    print(f"\nPlayers: {len(round_data['round_summary'])}")
    print(f"Events: {len(round_data['events'])}")
    print(f"Streaks: {len(round_data['streaks'])}")

    print("\n" + "="*60)
    print("SIX-HOLE SPLITS (Sample: First Player)")
    print("="*60)
    first_player = list(round_data['six_hole_splits'].keys())[0]
    splits = round_data['six_hole_splits'][first_player]
    print(f"{first_player}:")
    print(f"  Holes 1-6:   {splits['first_six']} pts")
    print(f"  Holes 7-12:  {splits['second_six']} pts")
    print(f"  Holes 13-18: {splits['third_six']} pts")

    print("\n" + "="*60)
    print("HOLE DIFFICULTY (Top 3 Hardest)")
    print("="*60)
    hardest = sorted(round_data['hole_difficulty'], key=lambda x: x['avg_vs_par'], reverse=True)[:3]
    for h in hardest:
        print(f"Hole {h['hole']} (Par {h['par']}): Avg {h['avg_score']:.1f} ({h['avg_vs_par']:+.2f} vs par)")

    print("\n" + "="*60)
    print("TOURNAMENT PROJECTIONS")
    print("="*60)
    proj = round_data['projections']
    print(f"Rounds remaining: {proj['rounds_remaining']}")
    print(f"Leader: {proj['leader']} ({proj['leader_total']} pts)")
    print(f"\nTop 3 Projections:")
    for p in proj['player_projections'][:3]:
        print(f"  {p['player']}: {p['current_total']} pts (gap: {p['gap_to_leader']})")
        if p['points_per_round_needed']:
            print(f"    Needs {p['points_per_round_needed']:.1f} pts/round to catch leader")
            print(f"    Catchable: {'Yes' if p['realistically_catchable'] else 'No'}")

    print("\n" + "="*60)
    print("POSITION CHANGES (After Hole 18)")
    print("="*60)
    final_positions = [p for p in round_data['positions_through_round'] if p['Hole'] == 18]
    final_positions = sorted(final_positions, key=lambda x: x['Position'])
    for p in final_positions:
        change_str = f"(+{p['Position_Change']})" if p['Position_Change'] > 0 else f"({p['Position_Change']})" if p['Position_Change'] < 0 else "(=)"
        print(f"  {p['Position']}. {p['Player']}: {p['Tournament_Cumulative_Stableford']} pts {change_str}")

    print("\n" + "="*60)
    print("> ROUND DATA LOADER TEST COMPLETE")
    print("="*60 + "\n")
