"""
Unified Round Data Loader

This module provides a comprehensive data loading system that merges tournament
and round report data needs into a single source. It includes all granular
detail, pattern analysis, and contextual information needed for both:
- Tournament retrospective reports (arc across all rounds)
- Live round reports (hole-by-hole coverage with forward projections)

Key functions:
- load_unified_round_data(): Main data assembly function
- build_course_context(): Course history, records, and descriptions
- build_location_context(): Venue and area return information
- calculate_hole_by_hole_positions_dual(): Position tracking for both competitions

This replaces the separate systems in:
- round_data_loader.py (round reports)
- data_loader.py (tournament reports)
"""

import pandas as pd
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils import get_teg_rounds, read_file
import numpy as np


def safe_int(value, default=0):
    """Safely convert value to int, handling NaN and None."""
    if pd.isna(value) or value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    """Safely convert value to float, handling NaN and None."""
    if pd.isna(value) or value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ========================
# Course Context Functions
# ========================

def build_course_records(course, teg_num, round_num):
    """
    Build comprehensive course records showing before/after status for this round.

    Tracks three types of records:
    1. Gross Score (actual strokes, e.g., 83)
    2. Gross vs Par (e.g., +10)
    3. Stableford Points

    For each metric, shows:
    - Record BEFORE this round (and who held it)
    - Record AFTER this round (and who holds it)
    - Whether a new record was set THIS round

    Args:
        course: Course name
        teg_num: Current tournament number
        round_num: Current round number

    Returns:
        Dict with comprehensive course records or None if course played <=2 times
    """
    # Load round summary data
    round_summary = read_file('data/commentary_round_summary.parquet')

    # Get all rounds played on this course
    course_data = round_summary[round_summary['Course'] == course].copy()

    # Count unique TEG+Round combinations
    times_played = course_data[['TEGNum', 'Round']].drop_duplicates().shape[0]

    # Only track records for courses played >2 times
    if times_played <= 2:
        return None

    # Get par for this course (from all-scores.parquet - PAR is hole-level data, sum all 18 holes)
    # Note: TEGNum + Round uniquely identifies the course, no need to filter by course name
    all_scores = read_file('data/all-scores.parquet')
    course_par_data = all_scores[
        (all_scores['TEGNum'] == teg_num) &
        (all_scores['Round'] == round_num)
    ]

    # Calculate course par by summing all 18 holes
    if len(course_par_data) > 0:
        par = int(course_par_data.groupby('Hole')['PAR'].first().sum())
    else:
        par = 72  # Default fallback

    # Split data: before this round vs all data (including this round)
    before_this_round = course_data[
        (course_data['TEGNum'] < teg_num) |
        ((course_data['TEGNum'] == teg_num) & (course_data['Round'] < round_num))
    ].copy()

    this_round_only = course_data[
        (course_data['TEGNum'] == teg_num) &
        (course_data['Round'] == round_num)
    ].copy()

    after_this_round = pd.concat([before_this_round, this_round_only])

    records = {
        'course': course,
        'par': par,
        'times_played': times_played
    }

    # Track each type of record
    for metric_name, column, ascending in [
        ('score', 'Round_Score_Sc', True),  # Lowest actual score
        ('vs_par', 'Round_Score_Gross', True),  # Lowest vs par
        ('stableford', 'Round_Score_Stableford', False)  # Highest Stableford
    ]:
        # BEFORE this round
        if len(before_this_round) > 0:
            if ascending:
                best_before = before_this_round[column].min()
            else:
                best_before = before_this_round[column].max()

            holders_before = before_this_round[before_this_round[column] == best_before]
            holders_before_list = holders_before[['Player', 'TEGNum', 'Round']].to_dict('records')

            records[f'record_{metric_name}_before_round'] = safe_int(best_before) if metric_name != 'vs_par' else safe_float(best_before)
            records[f'record_{metric_name}_holders_before'] = holders_before_list
        else:
            records[f'record_{metric_name}_before_round'] = None
            records[f'record_{metric_name}_holders_before'] = []

        # AFTER this round (including this round)
        if ascending:
            best_after = after_this_round[column].min()
        else:
            best_after = after_this_round[column].max()

        holders_after = after_this_round[after_this_round[column] == best_after]
        holders_after_list = holders_after[['Player', 'TEGNum', 'Round']].to_dict('records')

        records[f'record_{metric_name}_after_round'] = safe_int(best_after) if metric_name != 'vs_par' else safe_float(best_after)
        records[f'record_{metric_name}_holders_after'] = holders_after_list

        # Was a new record set THIS round?
        this_round_record_holders = holders_after[
            (holders_after['TEGNum'] == teg_num) &
            (holders_after['Round'] == round_num)
        ]

        new_record = len(this_round_record_holders) > 0
        records[f'new_record_{metric_name}_this_round'] = new_record
        records[f'record_{metric_name}_players_this_round'] = this_round_record_holders['Player'].tolist()

    return records


def build_course_context(teg_num, round_num):
    """
    Build comprehensive course context for this round.

    Includes:
    - Course name, area, par, type, designer, description
    - Course history (previous TEGs that played this course)
    - Course records (before/after for score, vs par, Stableford)

    Args:
        teg_num: Tournament number
        round_num: Round number

    Returns:
        Dict with complete course context
    """
    # Load round info
    round_info = read_file('data/round_info.csv')

    # Get this round's course
    this_round_info = round_info[
        (round_info['TEGNum'] == teg_num) &
        (round_info['Round'] == round_num)
    ]

    if len(this_round_info) == 0:
        return None

    course_name = this_round_info['Course'].iloc[0]
    area = this_round_info['Area'].iloc[0] if 'Area' in this_round_info.columns else 'Unknown'

    # Get par from all-scores.parquet (sum of all 18 holes)
    all_scores = read_file('data/all-scores.parquet')
    course_par_data = all_scores[
        (all_scores['TEGNum'] == teg_num) &
        (all_scores['Round'] == round_num)
    ]
    if len(course_par_data) > 0:
        par = int(course_par_data.groupby('Hole')['PAR'].first().sum())
    else:
        par = 72

    # Get course history (all previous times this course was played)
    course_history = round_info[round_info['Course'] == course_name].copy()
    course_history = course_history[
        (course_history['TEGNum'] < teg_num) |
        ((course_history['TEGNum'] == teg_num) & (course_history['Round'] < round_num))
    ]

    history_list = []
    for _, row in course_history.iterrows():
        history_list.append({
            'teg_num': safe_int(row['TEGNum']),
            'round_num': safe_int(row['Round']),
            'year': row['Year'] if 'Year' in row.index else None
        })

    # Build course records
    course_records = build_course_records(course_name, teg_num, round_num)

    return {
        'course_name': course_name,
        'course_area': area,
        'course_par': par,
        'course_type': None,  # Could be added if we have a course details database
        'course_designer': None,  # Could be added if we have a course details database
        'course_description': None,  # Could be added if we have a course details database
        'course_history_tegs': history_list,
        'course_records': course_records
    }


def build_location_context(teg_num):
    """
    Build location/venue context for this tournament.

    Includes:
    - Tournament area and year
    - Area return status (first time, consecutive, gap since last visit)
    - Previous TEGs in this area
    - Country return info (if first time in area but country visited before)

    Args:
        teg_num: Tournament number

    Returns:
        Dict with location context
    """
    # Load round info
    round_info = read_file('data/round_info.csv')

    # Get this TEG's information
    current_teg = round_info[round_info['TEGNum'] == teg_num]
    if len(current_teg) == 0:
        return None

    area = current_teg['Area'].iloc[0]
    year = current_teg['Year'].iloc[0] if 'Year' in current_teg.columns else None

    # Check for area returns
    all_teg_areas = round_info[['TEGNum', 'Area', 'Year']].drop_duplicates().sort_values('TEGNum')
    same_area_tegs = all_teg_areas[all_teg_areas['Area'] == area]
    previous_in_area = same_area_tegs[same_area_tegs['TEGNum'] < teg_num]

    area_return_status = None
    previous_area_tegs = []
    country_return_info = None

    if len(previous_in_area) > 0:
        # Have been to this area before
        last_teg_in_area = previous_in_area.iloc[-1]['TEGNum']
        gap = teg_num - last_teg_in_area

        if gap == 1:
            area_return_status = f"Area Return: Consecutive TEG (following TEG {safe_int(last_teg_in_area)})"
        else:
            area_return_status = f"Area Return: {safe_int(gap)}-TEG gap since TEG {safe_int(last_teg_in_area)}"

        previous_area_tegs = previous_in_area[['TEGNum', 'Year']].to_dict('records')
    else:
        # First time in this area
        area_return_status = f"First time in {area}"

        # Check for broader geographic returns (e.g., different England areas)
        area_country = area.split(',')[-1].strip() if ',' in area else area
        country_tegs = all_teg_areas[all_teg_areas['Area'].str.contains(area_country, na=False, regex=False)]
        previous_in_country = country_tegs[country_tegs['TEGNum'] < teg_num]

        if len(previous_in_country) > 0:
            last_teg_in_country = previous_in_country.iloc[-1]['TEGNum']
            last_area = previous_in_country.iloc[-1]['Area']
            gap = teg_num - last_teg_in_country

            country_return_info = {
                'last_teg': safe_int(last_teg_in_country),
                'last_area': last_area,
                'gap': safe_int(gap),
                'country': area_country
            }
        else:
            # Brand new destination
            area_return_status = f"NEW DESTINATION: First TEG in {area}"

    return {
        'area': area,
        'year': year,
        'area_return_status': area_return_status,
        'previous_area_tegs': previous_area_tegs,
        'country_return_info': country_return_info
    }


# ========================
# Position Tracking (Dual Competition)
# ========================

def calculate_hole_by_hole_positions_dual(teg_num, round_num):
    """
    Calculate tournament position after each hole for BOTH competitions.

    Tracks:
    - Stableford (Trophy) competition
    - Gross (Green Jacket) competition

    For each, provides:
    - Round cumulative (through this round)
    - Tournament cumulative (total through this hole)
    - Position after hole
    - Starting position (at start of round)
    - Position change from start

    Args:
        teg_num: Tournament number
        round_num: Current round number

    Returns:
        DataFrame with dual competition position tracking
    """
    # Load hole-by-hole data
    all_data = read_file('data/all-scores.parquet')
    round_data = all_data[
        (all_data['TEGNum'] == teg_num) &
        (all_data['Round'] == round_num)
    ].copy()

    # Load round summary for tournament standings before this round
    round_summary = read_file('data/commentary_round_summary.parquet')
    before_round = round_summary[
        (round_summary['TEGNum'] == teg_num) &
        (round_summary['Round'] == round_num)
    ][[
        'Player',
        'Cumulative_Tournament_Rank_Before_Round_Stableford',
        'Cumulative_Tournament_Rank_Before_Round_Gross'
    ]].copy()

    # Sort and calculate cumulative scores
    round_data = round_data.sort_values(['Player', 'Hole'])
    round_data['Round_Cumulative_Stableford'] = round_data.groupby('Player')['Stableford'].cumsum()
    round_data['Round_Cumulative_Gross'] = round_data.groupby('Player')['GrossVP'].cumsum()

    # Get starting totals (before this round)
    if round_num > 1:
        prev_totals = round_summary[
            (round_summary['TEGNum'] == teg_num) &
            (round_summary['Round'] == round_num)
        ][[
            'Player',
            'Cumulative_Tournament_Score_Stableford',
            'Cumulative_Tournament_Score_Gross',
            'Round_Score_Stableford',
            'Round_Score_Gross'
        ]].copy()

        # Starting total = cumulative - this round's final score
        prev_totals['Starting_Total_Stableford'] = (
            prev_totals['Cumulative_Tournament_Score_Stableford'] -
            prev_totals['Round_Score_Stableford']
        )
        prev_totals['Starting_Total_Gross'] = (
            prev_totals['Cumulative_Tournament_Score_Gross'] -
            prev_totals['Round_Score_Gross']
        )

        starting_totals_stableford = dict(zip(prev_totals['Player'], prev_totals['Starting_Total_Stableford']))
        starting_totals_gross = dict(zip(prev_totals['Player'], prev_totals['Starting_Total_Gross']))
    else:
        # Round 1: starting total is 0
        starting_totals_stableford = {player: 0 for player in round_data['Player'].unique()}
        starting_totals_gross = {player: 0 for player in round_data['Player'].unique()}

    # Add starting total + round cumulative
    round_data['Tournament_Cumulative_Stableford'] = round_data.apply(
        lambda row: starting_totals_stableford.get(row['Player'], 0) + row['Round_Cumulative_Stableford'],
        axis=1
    )
    round_data['Tournament_Cumulative_Gross'] = round_data.apply(
        lambda row: starting_totals_gross.get(row['Player'], 0) + row['Round_Cumulative_Gross'],
        axis=1
    )

    # Calculate position after each hole for both competitions
    position_data = []

    for hole in range(1, 19):
        hole_data = round_data[round_data['Hole'] == hole].copy()

        # Stableford: Rank by tournament cumulative (descending - higher is better)
        hole_data_stableford = hole_data.sort_values('Tournament_Cumulative_Stableford', ascending=False)
        hole_data_stableford['Position_Stableford'] = range(1, len(hole_data_stableford) + 1)

        # Gross: Rank by tournament cumulative (ascending - lower is better)
        hole_data_gross = hole_data.sort_values('Tournament_Cumulative_Gross', ascending=True)
        hole_data_gross['Position_Gross'] = range(1, len(hole_data_gross) + 1)

        # Merge positions
        positions = pd.merge(
            hole_data_stableford[['Player', 'Position_Stableford']],
            hole_data_gross[['Player', 'Position_Gross']],
            on='Player'
        )

        # Add to result with all data
        for _, row in hole_data.iterrows():
            player = row['Player']
            pos_stableford = positions[positions['Player'] == player]['Position_Stableford'].iloc[0]
            pos_gross = positions[positions['Player'] == player]['Position_Gross'].iloc[0]

            position_data.append({
                'Player': player,
                'Hole': hole,
                'Round_Cumulative_Stableford': safe_int(row['Round_Cumulative_Stableford']),
                'Tournament_Cumulative_Stableford': safe_int(row['Tournament_Cumulative_Stableford']),
                'Position_Stableford': safe_int(pos_stableford),
                'Round_Cumulative_Gross': safe_int(row['Round_Cumulative_Gross']),
                'Tournament_Cumulative_Gross': safe_int(row['Tournament_Cumulative_Gross']),
                'Position_Gross': safe_int(pos_gross)
            })

    positions_df = pd.DataFrame(position_data)

    # Calculate position changes from start of round
    starting_positions_stableford = dict(zip(
        before_round['Player'],
        before_round['Cumulative_Tournament_Rank_Before_Round_Stableford']
    ))
    starting_positions_gross = dict(zip(
        before_round['Player'],
        before_round['Cumulative_Tournament_Rank_Before_Round_Gross']
    ))

    positions_df['Starting_Position_Stableford'] = positions_df['Player'].map(starting_positions_stableford)
    positions_df['Starting_Position_Gross'] = positions_df['Player'].map(starting_positions_gross)

    # Positive = moved up (from 5th to 2nd = +3)
    positions_df['Position_Change_Stableford'] = (
        positions_df['Starting_Position_Stableford'] - positions_df['Position_Stableford']
    )
    positions_df['Position_Change_Gross'] = (
        positions_df['Starting_Position_Gross'] - positions_df['Position_Gross']
    )

    return positions_df


# ========================
# Hole Difficulty and Other Calculations
# ========================

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
                'par': safe_int(par),
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
        Dict with player -> {prev_stableford, prev_gross, prev_rank_*} or None if Round 1
    """
    if round_num == 1:
        return None

    # Load round summary data
    round_summary = read_file('data/commentary_round_summary.parquet')

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
            'prev_round_stableford': safe_int(row['Round_Score_Stableford']),
            'prev_round_gross': safe_int(row['Round_Score_Gross']),
            'prev_round_rank_stableford': safe_int(row['Player_Round_Rank_Stableford']),
            'prev_round_rank_gross': safe_int(row['Player_Round_Rank_Gross'])
        }

    return prev_scores


def calculate_tournament_projections(teg_num, round_num):
    """
    Calculate forward-looking projections for "What's At Stake" analysis.
    Provides projections for BOTH competitions (Stableford and Gross).

    Args:
        teg_num: Tournament number
        round_num: Round number just completed

    Returns:
        Dict with projection data for both competitions
    """
    # Get total rounds for this TEG
    total_rounds = get_teg_rounds(teg_num)
    rounds_remaining = total_rounds - round_num

    # Load current standings after this round
    round_summary = read_file('data/commentary_round_summary.parquet')
    current_standings = round_summary[
        (round_summary['TEGNum'] == teg_num) &
        (round_summary['Round'] == round_num)
    ]

    if len(current_standings) == 0:
        return None

    # Stableford leader
    stableford_standings = current_standings.sort_values('Cumulative_Tournament_Rank_Stableford')
    stableford_leader = stableford_standings.iloc[0]
    stableford_leader_total = stableford_leader['Cumulative_Tournament_Score_Stableford']
    stableford_leader_name = stableford_leader['Player']

    # Gross leader
    gross_standings = current_standings.sort_values('Cumulative_Tournament_Rank_Gross')
    gross_leader = gross_standings.iloc[0]
    gross_leader_total = gross_leader['Cumulative_Tournament_Score_Gross']
    gross_leader_name = gross_leader['Player']

    # Maximum possible points per round = 108 (18 holes × 6 points)
    max_points_per_round = 108
    max_possible_total = rounds_remaining * max_points_per_round

    # Stableford projections
    stableford_projections = []
    for _, row in stableford_standings.iterrows():
        player_total = row['Cumulative_Tournament_Score_Stableford']
        gap_to_leader = row['Gap_To_Leader_After_Round_Stableford']

        max_possible_final = player_total + max_possible_total
        leader_projected_total = stableford_leader_total + (rounds_remaining * 60)  # Assume 60 pts/round

        if rounds_remaining > 0:
            points_needed_to_tie = gap_to_leader + 1
            avg_per_round_needed = points_needed_to_tie / rounds_remaining
        else:
            avg_per_round_needed = None

        mathematically_possible = max_possible_final > leader_projected_total
        realistically_catchable = avg_per_round_needed is not None and avg_per_round_needed < 50

        stableford_projections.append({
            'player': row['Player'],
            'current_position': safe_int(row['Cumulative_Tournament_Rank_Stableford']),
            'current_total': safe_int(player_total),
            'gap_to_leader': safe_int(gap_to_leader) if gap_to_leader > 0 else 0,
            'max_possible_total': safe_int(max_possible_final),
            'points_per_round_needed': round(avg_per_round_needed, 1) if avg_per_round_needed else None,
            'mathematically_possible': mathematically_possible,
            'realistically_catchable': realistically_catchable
        })

    # Gross projections
    gross_projections = []
    for _, row in gross_standings.iterrows():
        player_total = row['Cumulative_Tournament_Score_Gross']
        gap_to_leader = row['Gap_To_Leader_After_Round_Gross']

        # For gross, lower is better (negative numbers beat positive)
        if rounds_remaining > 0:
            strokes_needed = gap_to_leader
            avg_per_round_needed = strokes_needed / rounds_remaining if strokes_needed > 0 else 0
        else:
            avg_per_round_needed = None

        # Mathematically possible if can shoot low enough
        mathematically_possible = rounds_remaining > 0 and gap_to_leader < (rounds_remaining * 18)

        gross_projections.append({
            'player': row['Player'],
            'current_position': safe_int(row['Cumulative_Tournament_Rank_Gross']),
            'current_total': safe_int(player_total),
            'gap_to_leader': safe_int(gap_to_leader) if gap_to_leader > 0 else 0,
            'strokes_per_round_needed': round(avg_per_round_needed, 1) if avg_per_round_needed else None,
            'mathematically_possible': mathematically_possible
        })

    return {
        'rounds_remaining': rounds_remaining,
        'max_points_per_round': max_points_per_round,
        'total_rounds': total_rounds,
        'round_just_completed': round_num,
        'stableford': {
            'leader': stableford_leader_name,
            'leader_total': safe_int(stableford_leader_total),
            'player_projections': stableford_projections
        },
        'gross': {
            'leader': gross_leader_name,
            'leader_total': safe_int(gross_leader_total),
            'player_projections': gross_projections
        }
    }


# ========================
# Main Unified Data Loader
# ========================

def load_unified_round_data(teg_num, round_num, all_processed_data):
    """
    Main data assembly function - loads ALL data for comprehensive story notes.

    This unified function merges data needs from both:
    - Tournament retrospective reports (arc, context, patterns)
    - Live round reports (hole-by-hole, projections, real-time)

    Args:
        teg_num: Tournament number
        round_num: Round number
        all_processed_data: Output from process_all_data_types() containing:
            - lead_data, momentum_data, nine_data, pattern_details
            - round_events, round_summary, records_by_round, course_records_by_round

    Returns:
        Dict with comprehensive unified data:
            - Metadata: teg_num, round_num, course, date, area, par, rounds_remaining
            - Round summary: per-player scores, positions, gaps (Stableford & Gross)
            - Hole-by-hole: complete scoring data for all players
            - Position tracking: dual competition tracking through the round
            - Events: eagles, disasters, lead changes (with before/after ranks)
            - Streaks: birdie runs, bogey-free, disasters
            - Momentum patterns: hot/cold spells (rolling windows)
            - Nine patterns: Front 9/Back 9 analysis (with gross differences)
            - Pattern details: enriched patterns with hole details
            - Lead timeline: leader after each round (both competitions)
            - Lead changes: all lead changes (both competitions)
            - Previous round: comparison to Round N-1
            - Hole difficulty: average scoring per hole
            - Projections: forward-looking "what's at stake" (both competitions)
            - Records & PBs: all-time records, personal bests/worsts
            - Course context: history, records (before/after), description
            - Location context: area, returns, venue significance
    """
    print(f"\nLoading unified round data for TEG {teg_num}, Round {round_num}...")

    # ========================
    # 1. METADATA
    # ========================
    total_rounds = get_teg_rounds(teg_num)
    rounds_remaining = total_rounds - round_num

    round_info = read_file('data/round_info.csv')
    metadata_row = round_info[
        (round_info['TEGNum'] == teg_num) &
        (round_info['Round'] == round_num)
    ]

    if len(metadata_row) > 0:
        # Get par from all-scores.parquet (sum of all 18 holes)
        all_scores = read_file('data/all-scores.parquet')
        par_data = all_scores[
            (all_scores['TEGNum'] == teg_num) &
            (all_scores['Round'] == round_num)
        ]
        if len(par_data) > 0:
            par = int(par_data.groupby('Hole')['PAR'].first().sum())
        else:
            par = 72

        metadata = {
            'teg_num': teg_num,
            'round_num': round_num,
            'course': metadata_row['Course'].iloc[0],
            'date': metadata_row['Date'].iloc[0],
            'area': metadata_row['Area'].iloc[0] if 'Area' in metadata_row.columns else 'Unknown',
            'par': par,
            'total_rounds': total_rounds,
            'rounds_remaining': rounds_remaining
        }
    else:
        metadata = {
            'teg_num': teg_num,
            'round_num': round_num,
            'course': 'Unknown',
            'date': 'Unknown',
            'area': 'Unknown',
            'par': 72,
            'total_rounds': total_rounds,
            'rounds_remaining': rounds_remaining
        }

    print(f"  > Metadata: {metadata['course']} ({metadata['date']})")

    # ========================
    # 2. ROUND SUMMARY (from all_processed_data)
    # ========================
    round_summary = [
        summary for summary in all_processed_data['round_summary']
        if summary['Round'] == round_num
    ]
    print(f"  > Round summary: {len(round_summary)} players")

    # ========================
    # 3. HOLE-BY-HOLE DATA
    # ========================
    all_scores = read_file('data/all-scores.parquet')
    hole_by_hole = all_scores[
        (all_scores['TEGNum'] == teg_num) &
        (all_scores['Round'] == round_num)
    ]
    print(f"  > Hole-by-hole: {len(hole_by_hole)} records")

    # ========================
    # 4. POSITION TRACKING (DUAL COMPETITION)
    # ========================
    positions_through_round = calculate_hole_by_hole_positions_dual(teg_num, round_num)
    print(f"  > Position tracking (dual): {len(positions_through_round)} records")

    # ========================
    # 5. EVENTS (from all_processed_data)
    # ========================
    round_events = [
        event for event in all_processed_data['round_events']
        if event['Round'] == round_num
    ]
    print(f"  > Events: {len(round_events)}")

    # ========================
    # 6. STREAKS (from commentary cache)
    # ========================
    round_streaks = read_file('data/commentary_round_streaks.parquet')
    streaks_data = round_streaks[
        (round_streaks['TEGNum'] == teg_num) &
        (round_streaks['Round'] == round_num)
    ]
    print(f"  > Streaks: {len(streaks_data)}")

    # ========================
    # 7. MOMENTUM PATTERNS (from all_processed_data)
    # ========================
    momentum_patterns = [
        pattern for pattern in all_processed_data['momentum_data']
        if pattern['round'] == round_num
    ]
    print(f"  > Momentum patterns: {len(momentum_patterns)}")

    # ========================
    # 8. FRONT 9/BACK 9 PATTERNS (from all_processed_data)
    # ========================
    nine_patterns = [
        pattern for pattern in all_processed_data['nine_data']
        if pattern['round'] == round_num
    ]
    print(f"  > Front 9/Back 9 patterns: {len(nine_patterns)}")

    # ========================
    # 9. PATTERN DETAILS (from all_processed_data)
    # ========================
    pattern_details = [
        detail for detail in all_processed_data['pattern_details']
        if detail['round'] == round_num
    ]
    print(f"  > Pattern details: {len(pattern_details)}")

    # ========================
    # 10. LEAD TIMELINE (from all_processed_data)
    # ========================
    lead_timeline = all_processed_data['lead_data']['lead_timeline']  # All rounds for context
    print(f"  > Lead timeline (all rounds): {len(lead_timeline)}")

    # ========================
    # 11. LEAD CHANGES (from all_processed_data)
    # ========================
    lead_changes = all_processed_data['lead_data']['lead_changes']  # All rounds for context
    print(f"  > Lead changes (all rounds): {len(lead_changes)}")

    # ========================
    # 12. PREVIOUS ROUND SCORES
    # ========================
    previous_round_scores = get_previous_round_scores(teg_num, round_num)
    print(f"  > Previous round scores: {'Yes' if previous_round_scores else 'N/A (Round 1)'}")

    # ========================
    # 13. HOLE DIFFICULTY
    # ========================
    hole_difficulty = calculate_hole_difficulty(hole_by_hole)
    print(f"  > Hole difficulty: {len(hole_difficulty)} holes")

    # ========================
    # 14. TOURNAMENT PROJECTIONS (DUAL)
    # ========================
    projections = calculate_tournament_projections(teg_num, round_num)
    print(f"  > Projections: {projections['rounds_remaining']} rounds remaining")

    # ========================
    # 15. RECORDS & PERSONAL BESTS (from all_processed_data)
    # ========================
    records_and_pbs = all_processed_data['records_by_round'].get(round_num, {
        'all_time_records': [],
        'all_time_worsts': [],
        'personal_bests': [],
        'personal_worsts': []
    })
    print(f"  > Records & PBs: {sum(len(v) for v in records_and_pbs.values())} total")

    # ========================
    # 16. COURSE CONTEXT (NEW)
    # ========================
    course_context = build_course_context(teg_num, round_num)
    print(f"  > Course context: {course_context['course_name'] if course_context else 'N/A'}")

    # ========================
    # 17. LOCATION CONTEXT (NEW)
    # ========================
    location_context = build_location_context(teg_num)
    print(f"  > Location context: {location_context['area'] if location_context else 'N/A'}")

    # ========================
    # ASSEMBLE FINAL DATA STRUCTURE
    # ========================
    unified_data = {
        # Core metadata
        'metadata': metadata,

        # Round data
        'round_summary': round_summary,
        'hole_by_hole': hole_by_hole.to_dict('records'),

        # Position tracking (both competitions)
        'positions_through_round': positions_through_round.to_dict('records'),

        # Events and moments
        'events': round_events,
        'streaks': streaks_data.to_dict('records'),

        # Pattern analysis
        'momentum_patterns': momentum_patterns,
        'nine_patterns': nine_patterns,
        'pattern_details': pattern_details,

        # Lead progression (all rounds for context)
        'lead_timeline': lead_timeline,
        'lead_changes': lead_changes,

        # Comparative and forward-looking
        'previous_round_scores': previous_round_scores,
        'hole_difficulty': hole_difficulty,
        'projections': projections,

        # Records and achievements
        'records_and_pbs': records_and_pbs,

        # Context (NEW)
        'course_context': course_context,
        'location_context': location_context
    }

    print(f"  > Unified data assembly complete!")
    return unified_data


# ========================
# Test/Debug Function
# ========================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING UNIFIED ROUND DATA LOADER")
    print("="*60 + "\n")

    # Test with TEG 17, Round 2
    # First need to process all data for the TEG
    from pattern_analysis import process_all_data_types

    print("Processing all TEG 17 data...")
    all_data = process_all_data_types(17)

    print("\n" + "="*60)
    print("Loading unified data for Round 2...")
    print("="*60)

    unified_data = load_unified_round_data(17, 2, all_data)

    print("\n" + "="*60)
    print("DATA SUMMARY")
    print("="*60)
    print(f"Metadata: {unified_data['metadata']}")
    print(f"\nRound summary players: {len(unified_data['round_summary'])}")
    print(f"Hole-by-hole records: {len(unified_data['hole_by_hole'])}")
    print(f"Position tracking records: {len(unified_data['positions_through_round'])}")
    print(f"Events: {len(unified_data['events'])}")
    print(f"Streaks: {len(unified_data['streaks'])}")
    print(f"Momentum patterns: {len(unified_data['momentum_patterns'])}")
    print(f"Nine patterns: {len(unified_data['nine_patterns'])}")
    print(f"Pattern details: {len(unified_data['pattern_details'])}")

    if unified_data['course_context']:
        print(f"\nCourse: {unified_data['course_context']['course_name']}")
        print(f"Course records: {unified_data['course_context']['course_records'] is not None}")

    if unified_data['location_context']:
        print(f"\nLocation: {unified_data['location_context']['area']}")
        print(f"Return status: {unified_data['location_context']['area_return_status']}")

    print("\n" + "="*60)
    print("UNIFIED DATA LOADER TEST COMPLETE")
    print("="*60)
