"""
Pattern Analysis Module for Tournament Story Generation

This module provides functions to analyze golf tournament data and identify
narrative-worthy patterns across multiple data dimensions.

Functions process data in passes, creating structured outputs for story generation.
"""

import pandas as pd
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils import get_teg_rounds


def load_all_data_for_teg(teg_num):
    """
    Load all scoring data for a specific TEG.

    Args:
        teg_num: Tournament number

    Returns:
        DataFrame with all hole-by-hole scoring data for the tournament
    """
    # Load the main scoring data
    df = pd.read_parquet('data/all-scores.parquet')

    # Filter to this TEG
    df = df[df['TEGNum'] == teg_num].copy()

    return df


def analyze_momentum_windows(teg_num, window_sizes=[3, 6]):
    """
    Calculate rolling performance windows for hot/cold spell detection.

    Analyzes player performance over rolling windows of holes to identify
    momentum shifts and sustained periods of strong/weak play.

    Detects patterns in both:
    - Stableford scoring (net competition)
    - Gross scoring vs par (gross competition)

    Args:
        teg_num: Tournament number
        window_sizes: List of window sizes to analyze (default: [3, 6] holes)

    Returns:
        List of dicts with momentum patterns:
        - player: Player name
        - round: Round number
        - holes: Hole range (e.g., "5-7")
        - window_size: Number of holes in window
        - points: Stableford points in window (for net patterns)
        - avg_gross_vs_par: Average gross vs par (for gross patterns)
        - type: 'hot' or 'cold'
        - scoring_type: 'net' or 'gross'
    """
    df = load_all_data_for_teg(teg_num)

    momentum_patterns = []

    for player in df['Player'].unique():
        player_df = df[df['Player'] == player]

        for round_num in player_df['Round'].unique():
            round_df = player_df[player_df['Round'] == round_num].sort_values('Hole')

            # Calculate rolling windows for both scoring types
            for window_size in window_sizes:
                # Stableford (net) rolling windows
                round_df[f'rolling_stableford_{window_size}'] = (
                    round_df['Stableford'].rolling(window_size).sum()
                )

                # Gross vs par rolling windows (average)
                round_df[f'rolling_gross_{window_size}'] = (
                    round_df['GrossVP'].rolling(window_size).mean()
                )

                # Stableford thresholds
                # Hot: Averaging >3.3 points/hole for 3-hole, >3.0 for 6-hole
                stableford_hot_threshold = 11 if window_size == 3 else 18
                # Cold: Averaging <1.0 point/hole for 3-hole, <1.3 for 6-hole
                stableford_cold_threshold = 1 if window_size == 3 else 6

                # Gross thresholds
                # Good: Average <0.2 vs par (under par or just over)
                gross_good_threshold = 0.2
                # Bad: Average >2.2 vs par (well over par)
                gross_bad_threshold = 2.2

                for idx in round_df.index:
                    end_hole = round_df.loc[idx, 'Hole']
                    start_hole = end_hole - window_size + 1

                    # Check Stableford patterns
                    if pd.notna(round_df.loc[idx, f'rolling_stableford_{window_size}']):
                        points = round_df.loc[idx, f'rolling_stableford_{window_size}']

                        if points >= stableford_hot_threshold:
                            momentum_patterns.append({
                                'player': player,
                                'round': round_num,
                                'holes': f"{start_hole}-{end_hole}",
                                'window_size': window_size,
                                'points': int(points),
                                'avg_gross_vs_par': None,
                                'type': 'hot',
                                'scoring_type': 'net'
                            })
                        elif points <= stableford_cold_threshold:
                            momentum_patterns.append({
                                'player': player,
                                'round': round_num,
                                'holes': f"{start_hole}-{end_hole}",
                                'window_size': window_size,
                                'points': int(points),
                                'avg_gross_vs_par': None,
                                'type': 'cold',
                                'scoring_type': 'net'
                            })

                    # Check Gross patterns
                    if pd.notna(round_df.loc[idx, f'rolling_gross_{window_size}']):
                        avg_gross = round_df.loc[idx, f'rolling_gross_{window_size}']

                        if avg_gross <= gross_good_threshold:
                            momentum_patterns.append({
                                'player': player,
                                'round': round_num,
                                'holes': f"{start_hole}-{end_hole}",
                                'window_size': window_size,
                                'points': None,
                                'avg_gross_vs_par': round(avg_gross, 2),
                                'type': 'hot',
                                'scoring_type': 'gross'
                            })
                        elif avg_gross >= gross_bad_threshold:
                            momentum_patterns.append({
                                'player': player,
                                'round': round_num,
                                'holes': f"{start_hole}-{end_hole}",
                                'window_size': window_size,
                                'points': None,
                                'avg_gross_vs_par': round(avg_gross, 2),
                                'type': 'cold',
                                'scoring_type': 'gross'
                            })

    return momentum_patterns


def analyze_lead_progression(teg_num):
    """
    Analyze lead progression across all rounds.

    Tracks who held the lead after each round, identifying lead changes
    and margin evolution. Uses round summary data for cumulative standings.

    Note: This provides end-of-round lead progression, not hole-by-hole.
    For hole-by-hole drama, use momentum windows and drill-down patterns.

    Args:
        teg_num: Tournament number

    Returns:
        Dict with:
        - lead_timeline: List of leader after each round with margins
        - lead_changes: List of lead change events
    """
    # Load round summary data which has cumulative standings
    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')
    round_summary = round_summary[round_summary['TEGNum'] == teg_num]

    # Get number of rounds
    num_rounds = get_teg_rounds(teg_num)

    lead_timeline = []
    for round_num in range(1, num_rounds + 1):
        round_data = round_summary[round_summary['Round'] == round_num]

        # Leader has rank 1 after this round
        leader_data = round_data[
            round_data['Cumulative_Tournament_Rank_Stableford'] == 1
        ].iloc[0]

        # Find 2nd place
        second_data = round_data[
            round_data['Cumulative_Tournament_Rank_Stableford'] == 2
        ]

        if len(second_data) > 0:
            margin = second_data.iloc[0]['Gap_To_Leader_After_Round_Stableford']
        else:
            margin = 0

        lead_timeline.append({
            'round': round_num,
            'leader': leader_data['Player'],
            'margin_to_2nd': int(abs(margin)),
            'tight_battle': abs(margin) <= 2,
            'breakaway': abs(margin) >= 10
        })

    # Identify lead changes between rounds
    lead_changes = []
    for i in range(1, len(lead_timeline)):
        if lead_timeline[i]['leader'] != lead_timeline[i-1]['leader']:
            lead_changes.append({
                'round': lead_timeline[i]['round'],
                'from': lead_timeline[i-1]['leader'],
                'to': lead_timeline[i]['leader'],
                'new_margin': lead_timeline[i]['margin_to_2nd']
            })

    return {
        'lead_timeline': lead_timeline,
        'lead_changes': lead_changes
    }


def analyze_front_back_nine(teg_num):
    """
    Identify significant front 9 vs back 9 differences.
    Uses existing commentary_round_summary data.

    Args:
        teg_num: Tournament number

    Returns:
        List of dicts with notable nine-hole performances
    """
    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')
    round_summary = round_summary[round_summary['TEGNum'] == teg_num]

    nine_patterns = []

    # Threshold for "significant" difference (to test/refine)
    threshold = 5

    for idx, row in round_summary.iterrows():
        diff = row['Front_9_vs_Back_9_Stableford']

        if abs(diff) >= threshold:
            nine_patterns.append({
                'player': row['Player'],
                'round': row['Round'],
                'front_9': int(row['Front_9_Score_Stableford']),
                'back_9': int(row['Back_9_Score_Stableford']),
                'difference': int(diff),
                'pattern': 'strong_starter' if diff > 0 else 'strong_finisher'
            })

    return nine_patterns


def drill_down_patterns(momentum_patterns, nine_patterns, teg_num):
    """
    For each identified pattern, drill down to specific holes.

    Takes momentum and nine-hole patterns and adds hole-by-hole detail
    to identify the specific culprit holes that created each pattern.

    Args:
        momentum_patterns: Output from analyze_momentum_windows()
        nine_patterns: Output from analyze_front_back_nine()
        teg_num: Tournament number

    Returns:
        List of pattern dicts enriched with hole-level details
    """
    df = load_all_data_for_teg(teg_num)
    pattern_details = []

    # Drill down momentum patterns
    for pattern in momentum_patterns:
        player = pattern['player']
        round_num = pattern['round']
        holes_str = pattern['holes']

        # Parse hole range
        start, end = map(int, holes_str.split('-'))

        # Get hole-by-hole data for this window
        window_df = df[
            (df['Player'] == player) &
            (df['Round'] == round_num) &
            (df['Hole'] >= start) &
            (df['Hole'] <= end)
        ].sort_values('Hole')

        # Find notable holes in window
        # IMPORTANT: Only count GROSS birdies (GrossVP=-1), not just 4-point Stableford scores
        birdies = window_df[window_df['GrossVP'] == -1]['Hole'].tolist()
        # Track 4-point holes separately (these may be pars with good handicap)
        four_point_holes = window_df[window_df['Stableford'] >= 4]['Hole'].tolist()
        blow_ups = window_df[window_df['Stableford'] == 0]['Hole'].tolist()

        pattern_details.append({
            **pattern,  # Include original pattern
            'birdies_in_window': birdies,
            'four_point_holes_in_window': four_point_holes,
            'blow_ups_in_window': blow_ups,
            'hole_scores': window_df[['Hole', 'PAR', 'Sc', 'Stableford', 'GrossVP']].to_dict('records')
        })

    # Drill down front/back 9 patterns
    for pattern in nine_patterns:
        player = pattern['player']
        round_num = pattern['round']
        is_front = pattern['pattern'] == 'strong_starter'

        # Get the nine in question
        nine_df = df[
            (df['Player'] == player) &
            (df['Round'] == round_num) &
            (df['FrontBack'] == ('F' if is_front else 'B'))
        ].sort_values('Hole')

        # Find what made it strong
        # IMPORTANT: Only count GROSS birdies (GrossVP=-1), not just 4-point Stableford scores
        birdies = nine_df[nine_df['GrossVP'] == -1]['Hole'].tolist()
        four_point_holes = nine_df[nine_df['Stableford'] >= 4]['Hole'].tolist()
        blow_ups = nine_df[nine_df['Stableford'] == 0]['Hole'].tolist()

        pattern_details.append({
            **pattern,
            'birdies': birdies,
            'four_point_holes': four_point_holes,
            'blow-ups': blow_ups,
            'hole_scores': nine_df[['Hole', 'PAR', 'Sc', 'Stableford', 'GrossVP']].to_dict('records')
        })

    return pattern_details


def identify_round_records_and_pbs(teg_num, round_num):
    """
    Identify all records and personal bests for a specific round.

    Uses pre-calculated ranking data to identify:
    - All-time TEG records (bests and worsts)
    - Personal bests
    - Personal worsts

    Args:
        teg_num: Tournament number
        round_num: Round number

    Returns:
        Dict with categorized records and PBs:
        - all_time_records: List of all-time best records
        - all_time_worsts: List of all-time worst records
        - personal_bests: List of personal bests
        - personal_worsts: List of personal worsts
    """
    # Load round summary data which has pre-calculated rankings
    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')

    # Filter to this specific round
    round_data = round_summary[
        (round_summary['TEGNum'] == teg_num) &
        (round_summary['Round'] == round_num)
    ]

    if round_data.empty:
        return {
            'all_time_records': [],
            'all_time_worsts': [],
            'personal_bests': [],
            'personal_worsts': []
        }

    all_time_records = []
    all_time_worsts = []
    personal_bests = []
    personal_worsts = []

    # Metrics to check: Gross and Stableford (focus on main competitions)
    metrics = [
        ('Gross', 'Round_Score_Gross', 'Round_Rank_In_All_History_Gross', 'Round_Rank_In_Player_History_Gross'),
        ('Stableford', 'Round_Score_Stableford', 'Round_Rank_In_All_History_Stableford', 'Round_Rank_In_Player_History_Stableford')
    ]

    for metric_name, value_col, all_rank_col, player_rank_col in metrics:
        for _, row in round_data.iterrows():
            player = row['Player']
            value = row[value_col]

            # Parse rank strings like "3 of 61" or "1 of 325"
            all_rank_str = str(row[all_rank_col])
            player_rank_str = str(row[player_rank_col])

            if ' of ' in all_rank_str:
                all_rank = int(all_rank_str.split(' of ')[0])
                all_total = int(all_rank_str.split(' of ')[1])
            else:
                continue

            if ' of ' in player_rank_str:
                player_rank = int(player_rank_str.split(' of ')[0])
                player_total = int(player_rank_str.split(' of ')[1])
            else:
                continue

            # All-time record (rank 1 of all)
            if all_rank == 1:
                all_time_records.append({
                    'player': player,
                    'metric': metric_name,
                    'value': value,
                    'rank': all_rank_str
                })

            # All-time worst (highest rank of all)
            if all_rank == all_total and all_total > 1:
                all_time_worsts.append({
                    'player': player,
                    'metric': metric_name,
                    'value': value,
                    'rank': all_rank_str
                })

            # Personal best (rank 1 for player)
            if player_rank == 1:
                personal_bests.append({
                    'player': player,
                    'metric': metric_name,
                    'value': value,
                    'rank': player_rank_str
                })

            # Personal worst (highest rank for player)
            if player_rank == player_total and player_total > 1:
                personal_worsts.append({
                    'player': player,
                    'metric': metric_name,
                    'value': value,
                    'rank': player_rank_str
                })

    return {
        'all_time_records': all_time_records,
        'all_time_worsts': all_time_worsts,
        'personal_bests': personal_bests,
        'personal_worsts': personal_worsts
    }


def identify_course_records(teg_num, round_num):
    """
    Identify course records for the round (gross score only).

    Only includes courses that have been played >2 times (>2 unique TEG+Round combinations).

    Args:
        teg_num: Tournament number
        round_num: Round number

    Returns:
        List of course record dicts, one per course in the round:
        - course: Course name
        - times_played: Number of unique TEG+Round combinations
        - record_score: Best gross score on course (e.g., 83)
        - record_vs_par: Best gross vs par on course (e.g., +10)
        - record_holders: List of players who hold the record
        - is_record_this_round: True if record was set/tied this round
        - record_players_this_round: Players who set/tied record this round
    """
    # Load round summary data
    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')

    # Get course for this round
    this_round_data = round_summary[
        (round_summary['TEGNum'] == teg_num) &
        (round_summary['Round'] == round_num)
    ]

    if this_round_data.empty:
        return []

    course = this_round_data['Course'].iloc[0]

    # Get all rounds played on this course
    course_data = round_summary[round_summary['Course'] == course].copy()

    # Count unique TEG+Round combinations
    times_played = course_data[['TEGNum', 'Round']].drop_duplicates().shape[0]

    # Only include courses with >2 rounds
    if times_played <= 2:
        return []

    # Find best gross score on this course
    best_gross = course_data['Round_Score_Gross'].min()

    # Find all players who achieved this score
    record_holders_data = course_data[course_data['Round_Score_Gross'] == best_gross]
    record_holders = record_holders_data[['Player', 'TEGNum', 'Round']].to_dict('records')

    # Check if record was set/tied this round
    this_round_records = record_holders_data[
        (record_holders_data['TEGNum'] == teg_num) &
        (record_holders_data['Round'] == round_num)
    ]

    is_record_this_round = len(this_round_records) > 0
    record_players_this_round = this_round_records['Player'].tolist() if is_record_this_round else []

    # Get the score and vs par from one of the record holders
    record_score = int(record_holders_data['Round_Score_Sc'].iloc[0])
    record_vs_par = int(best_gross)

    return [{
        'course': course,
        'times_played': times_played,
        'record_score': record_score,
        'record_vs_par': record_vs_par,
        'record_holders': record_holders,
        'is_record_this_round': is_record_this_round,
        'record_players_this_round': record_players_this_round
    }]


def process_all_data_types(teg_num):
    """
    Master function to run all 7 data type processing passes.

    Executes the complete Level 1 data processing pipeline,
    creating structured data ready for story generation.

    Args:
        teg_num: Tournament number

    Returns:
        Dict with all processed data ready for story generation:
        - lead_data
        - momentum_data
        - nine_data
        - pattern_details
        - round_events
        - round_summary
        - records_by_round: Dict mapping round_num -> records/PBs
        - course_records_by_round: Dict mapping round_num -> course records
    """
    print(f"Processing data for TEG {teg_num}...")

    # Pass 1: Lead progression
    print("Pass 1: Analyzing lead progression...")
    lead_data = analyze_lead_progression(teg_num)
    print(f"  > Found {len(lead_data['lead_changes'])} lead changes")

    # Pass 2: Momentum windows
    print("Pass 2: Analyzing momentum windows...")
    momentum_data = analyze_momentum_windows(teg_num)
    print(f"  > Found {len(momentum_data)} momentum patterns")

    # Pass 3: Front/back 9
    print("Pass 3: Analyzing front/back 9 patterns...")
    nine_data = analyze_front_back_nine(teg_num)
    print(f"  > Found {len(nine_data)} significant nine-hole performances")

    # Pass 4: Drill down
    print("Pass 4: Drilling down patterns...")
    pattern_details = drill_down_patterns(momentum_data, nine_data, teg_num)
    print(f"  > Enriched {len(pattern_details)} patterns with hole details")

    # Pass 5 & 6: Load existing commentary files
    print("Pass 5 & 6: Loading existing commentary data...")
    round_events = pd.read_parquet('data/commentary_round_events.parquet')
    round_events = round_events[round_events['TEGNum'] == teg_num]

    round_summary = pd.read_parquet('data/commentary_round_summary.parquet')
    round_summary = round_summary[round_summary['TEGNum'] == teg_num]

    print(f"  > Loaded {len(round_events)} round events")
    print(f"  > Loaded {len(round_summary)} round summaries")

    # Pass 7: Identify records and personal bests for each round
    print("Pass 7: Identifying records and personal bests...")
    num_rounds = get_teg_rounds(teg_num)
    records_by_round = {}
    course_records_by_round = {}

    total_records = 0
    total_course_records = 0

    for round_num in range(1, num_rounds + 1):
        # Get records/PBs for this round
        records_data = identify_round_records_and_pbs(teg_num, round_num)
        records_by_round[round_num] = records_data

        # Count items
        round_total = (
            len(records_data['all_time_records']) +
            len(records_data['all_time_worsts']) +
            len(records_data['personal_bests']) +
            len(records_data['personal_worsts'])
        )
        total_records += round_total

        # Get course records for this round
        course_records = identify_course_records(teg_num, round_num)
        course_records_by_round[round_num] = course_records
        total_course_records += len(course_records)

    print(f"  > Identified {total_records} records/PBs across {num_rounds} rounds")
    print(f"  > Identified {total_course_records} course record checks")

    print(f"\n> All data processing complete for TEG {teg_num}\n")

    return {
        'lead_data': lead_data,
        'momentum_data': momentum_data,
        'nine_data': nine_data,
        'pattern_details': pattern_details,
        'round_events': round_events.to_dict('records'),
        'round_summary': round_summary.to_dict('records'),
        'records_by_round': records_by_round,
        'course_records_by_round': course_records_by_round
    }


if __name__ == "__main__":
    # Test complete pipeline with TEG 17
    print("\n" + "=" * 60)
    print("TESTING COMPLETE PATTERN ANALYSIS PIPELINE - TEG 17")
    print("=" * 60 + "\n")

    # Run all 6 passes
    all_data = process_all_data_types(17)

    # Show summary of what was found
    print("=" * 60)
    print("SUMMARY BY ROUND")
    print("=" * 60)

    for round_num in range(1, 5):  # TEG 17 has 4 rounds
        print(f"\n--- Round {round_num} ---")

        # Lead after this round
        round_lead = all_data['lead_data']['lead_timeline'][round_num - 1]
        print(f"\nLeader after round: {round_lead['leader']}")
        print(f"  Margin to 2nd: {round_lead['margin_to_2nd']} points")
        if round_lead['tight_battle']:
            print(f"  Status: TIGHT BATTLE")
        elif round_lead['breakaway']:
            print(f"  Status: BREAKAWAY")

        # Check if lead changed this round
        round_lead_change = [lc for lc in all_data['lead_data']['lead_changes']
                            if lc['round'] == round_num]
        if round_lead_change:
            lc = round_lead_change[0]
            print(f"  ** LEAD CHANGE: {lc['from']} -> {lc['to']}")

        # Momentum patterns in this round
        round_momentum = [m for m in all_data['pattern_details']
                         if m['round'] == round_num and 'birdies_in_window' in m]

        # Show most notable patterns (with culprit holes)
        net_hot = [m for m in round_momentum
                  if m['type'] == 'hot' and m['scoring_type'] == 'net']
        if net_hot:
            top_net = sorted(net_hot, key=lambda x: x['points'], reverse=True)[0]
            print(f"\nTop Net Hot Spell: {top_net['player']} holes {top_net['holes']}")
            print(f"  {top_net['points']} points")
            if top_net['birdies_in_window']:
                print(f"  Birdies on holes: {top_net['birdies_in_window']}")

        gross_cold = [m for m in round_momentum
                     if m['type'] == 'cold' and m['scoring_type'] == 'gross']
        if gross_cold:
            worst_gross = sorted(gross_cold, key=lambda x: x['avg_gross_vs_par'],
                               reverse=True)[0]
            print(f"\nWorst Gross Spell: {worst_gross['player']} holes {worst_gross['holes']}")
            print(f"  Avg {worst_gross['avg_gross_vs_par']:+.2f} vs par")
            if worst_gross['blow_ups_in_window']:
                print(f"  Blow-ups on holes: {worst_gross['blow_ups_in_window']}")

    print("\n" + "=" * 60)
    print("> PIPELINE TEST COMPLETE")
    print("=" * 60)
