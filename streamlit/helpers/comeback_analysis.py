"""Helper functions for analyzing final round comebacks and collapses in TEG tournaments.

This module provides functions to identify and analyze dramatic final round performances:
- Biggest final round score differentials
- Biggest leads lost by penultimate round leaders
- Biggest leads lost during the final round
- Biggest comebacks in the final round regardless of winning
"""

import pandas as pd
import numpy as np
from typing import Tuple


def calculate_final_round_differentials(
    all_scores_df: pd.DataFrame,
    round_info_df: pd.DataFrame,
    measure: str = 'GrossVP'
) -> pd.DataFrame:
    """Calculate the biggest final round score differentials.

    Finds the best and worst final round performances for each player in each TEG,
    showing who had the biggest positive or negative scoring swings.

    Args:
        all_scores_df: DataFrame with hole-by-hole scores
        round_info_df: DataFrame with TEG round information
        measure: Scoring measure ('GrossVP' or 'Stableford')

    Returns:
        DataFrame with columns: TEG, Player, FinalRound, FinalRoundScore, TotalScore, Rank
    """
    # Exclude TEG 2 (only 3 rounds)
    valid_tegs = round_info_df[round_info_df['Round'] == 4]['TEGNum'].unique()
    df = all_scores_df[all_scores_df['TEGNum'].isin(valid_tegs)].copy()

    # For Stableford, only include TEG 6+
    if measure == 'Stableford':
        df = df[df['TEGNum'] >= 6]

    # Get final round number for each TEG
    final_rounds = round_info_df.groupby('TEGNum')['Round'].max().to_dict()

    # Calculate round totals
    round_totals = df.groupby(['TEG', 'TEGNum', 'Player', 'Round'])[measure].sum().reset_index()
    round_totals.columns = ['TEG', 'TEGNum', 'Player', 'Round', 'RoundScore']

    # Filter for final rounds only
    round_totals['FinalRound'] = round_totals['TEGNum'].map(final_rounds)
    final_round_scores = round_totals[round_totals['Round'] == round_totals['FinalRound']].copy()

    # Calculate tournament totals
    teg_totals = round_totals.groupby(['TEG', 'TEGNum', 'Player'])['RoundScore'].sum().reset_index()
    teg_totals.columns = ['TEG', 'TEGNum', 'Player', 'TotalScore']

    # Calculate scores through penultimate round for "Rank After R3"
    penultimate_data = round_totals[round_totals['Round'] < round_totals['FinalRound']]
    penultimate_totals = penultimate_data.groupby(['TEG', 'TEGNum', 'Player'])['RoundScore'].sum().reset_index()
    penultimate_totals.columns = ['TEG', 'TEGNum', 'Player', 'ScoreAfterR3']

    # Add rankings (ascending for Gross, descending for Stableford)
    ascending = True if measure == 'GrossVP' else False
    penultimate_totals['RankAfterR3'] = penultimate_totals.groupby('TEG')['ScoreAfterR3'].rank(method='min', ascending=ascending)

    # Merge final round with totals and penultimate rank
    result = final_round_scores.merge(teg_totals, on=['TEG', 'TEGNum', 'Player'])
    result = result.merge(penultimate_totals[['TEG', 'Player', 'RankAfterR3']], on=['TEG', 'Player'])

    # Add final rankings
    result['FinalRank'] = result.groupby('TEG')['TotalScore'].rank(method='min', ascending=ascending)

    # Sort by final round score (best performances first based on measure)
    result = result.sort_values('RoundScore', ascending=ascending)

    # Select and rename columns
    result = result[['TEG', 'Player', 'FinalRound', 'RoundScore', 'RankAfterR3', 'TotalScore', 'FinalRank']]
    result.columns = ['TEG', 'Player', 'Final Round', 'Final Round Score', 'Rank After R3', 'Total Score', 'Final Rank']

    return result


def calculate_biggest_leads_lost_after_r3(
    all_scores_df: pd.DataFrame,
    round_info_df: pd.DataFrame,
    measure: str = 'GrossVP'
) -> pd.DataFrame:
    """Find biggest leads going into the final round where the leader didn't win.

    Calculates the standings after the penultimate round and identifies cases where
    the leader(s) after that round did not go on to win the tournament.

    Args:
        all_scores_df: DataFrame with hole-by-hole scores
        round_info_df: DataFrame with TEG round information
        measure: Scoring measure ('GrossVP' or 'Stableford')

    Returns:
        DataFrame with: TEG, LeaderAfterR3, GapToSecond, Winner, LeaderFinalPosition
    """
    # Exclude TEG 2 (only 3 rounds)
    valid_tegs = round_info_df[round_info_df['Round'] == 4]['TEGNum'].unique()
    df = all_scores_df[all_scores_df['TEGNum'].isin(valid_tegs)].copy()

    # For Stableford, only include TEG 6+
    if measure == 'Stableford':
        df = df[df['TEGNum'] >= 6]

    # Get penultimate round number for each TEG
    final_rounds = round_info_df.groupby('TEGNum')['Round'].max().to_dict()

    # Calculate round totals
    round_totals = df.groupby(['TEG', 'TEGNum', 'Player', 'Round'])[measure].sum().reset_index()

    results = []

    for teg_num, teg_name in df[['TEGNum', 'TEG']].drop_duplicates().values:
        final_round = final_rounds.get(teg_num, 4)
        penultimate_round = final_round - 1

        teg_data = round_totals[round_totals['TEGNum'] == teg_num]

        # Calculate cumulative scores through penultimate round
        penultimate_data = teg_data[teg_data['Round'] <= penultimate_round]
        penultimate_totals = penultimate_data.groupby('Player')[measure].sum().reset_index()
        penultimate_totals.columns = ['Player', 'ScoreAfterR3']

        # Calculate final totals
        final_totals = teg_data.groupby('Player')[measure].sum().reset_index()
        final_totals.columns = ['Player', 'FinalScore']

        # Determine ascending based on measure
        ascending = True if measure == 'GrossVP' else False

        # Find leader(s) after penultimate round
        if ascending:
            leader_score = penultimate_totals['ScoreAfterR3'].min()
        else:
            leader_score = penultimate_totals['ScoreAfterR3'].max()

        leaders = penultimate_totals[penultimate_totals['ScoreAfterR3'] == leader_score]['Player'].tolist()

        # Find winner(s)
        if ascending:
            winner_score = final_totals['FinalScore'].min()
        else:
            winner_score = final_totals['FinalScore'].max()

        winners = final_totals[final_totals['FinalScore'] == winner_score]['Player'].tolist()

        # Check if leader didn't win
        if not any(leader in winners for leader in leaders):
            # Calculate gap to second place
            if ascending:
                second_score = penultimate_totals[
                    penultimate_totals['ScoreAfterR3'] > leader_score
                ]['ScoreAfterR3'].min()
                gap = second_score - leader_score
            else:
                second_score = penultimate_totals[
                    penultimate_totals['ScoreAfterR3'] < leader_score
                ]['ScoreAfterR3'].max()
                gap = leader_score - second_score

            # Get leader's final position
            final_totals['Rank'] = final_totals['FinalScore'].rank(method='min', ascending=ascending)

            for leader in leaders:
                leader_final_rank = final_totals[final_totals['Player'] == leader]['Rank'].iloc[0]

                results.append({
                    'TEG': teg_name,
                    'Leader After R3': leader,
                    'Gap to 2nd': gap,
                    'Winner': ', '.join(winners),
                    'Leader Final Position': int(leader_final_rank)
                })

    result_df = pd.DataFrame(results)

    if not result_df.empty:
        # Sort by gap (biggest leads lost first)
        result_df = result_df.sort_values('Gap to 2nd', ascending=False)

    return result_df


def calculate_biggest_leads_lost_in_r4(
    all_scores_df: pd.DataFrame,
    round_info_df: pd.DataFrame,
    measure: str = 'GrossVP'
) -> pd.DataFrame:
    """Find biggest leads lost during the final round.

    Tracks cumulative scores hole-by-hole during the final round to find cases
    where a player held a significant lead at some point but didn't win.

    Args:
        all_scores_df: DataFrame with hole-by-hole scores
        round_info_df: DataFrame with TEG round information
        measure: Scoring measure ('GrossVP' or 'Stableford')

    Returns:
        DataFrame with: TEG, Player, MaxLeadInR4, HoleOfMaxLead, Winner, FinalGap
    """
    # Exclude TEG 2 (only 3 rounds)
    valid_tegs = round_info_df[round_info_df['Round'] == 4]['TEGNum'].unique()
    df = all_scores_df[all_scores_df['TEGNum'].isin(valid_tegs)].copy()

    # For Stableford, only include TEG 6+
    if measure == 'Stableford':
        df = df[df['TEGNum'] >= 6]

    # Get final round number for each TEG
    final_rounds = round_info_df.groupby('TEGNum')['Round'].max().to_dict()

    temp_results = []  # Temporary tracking of leads at each hole
    final_results = []  # Final summary results
    ascending = True if measure == 'GrossVP' else False

    for teg_num, teg_name in df[['TEGNum', 'TEG']].drop_duplicates().values:
        final_round = final_rounds.get(teg_num, 4)

        # Get scores through penultimate round
        pre_final_data = df[(df['TEGNum'] == teg_num) & (df['Round'] < final_round)]
        pre_final_totals = pre_final_data.groupby('Player')[measure].sum().reset_index()
        pre_final_totals.columns = ['Player', 'PreFinalScore']

        # Get final round data
        final_round_data = df[(df['TEGNum'] == teg_num) & (df['Round'] == final_round)]

        # For each hole in final round, calculate cumulative standings
        for hole in sorted(final_round_data['Hole'].unique()):
            # Get scores through this hole in final round
            through_hole = final_round_data[final_round_data['Hole'] <= hole]
            final_round_cum = through_hole.groupby('Player')[measure].sum().reset_index()
            final_round_cum.columns = ['Player', 'FinalRoundScore']

            # Merge with pre-final scores
            standings = pre_final_totals.merge(final_round_cum, on='Player', how='left')
            standings['FinalRoundScore'] = standings['FinalRoundScore'].fillna(0)
            standings['TotalScore'] = standings['PreFinalScore'] + standings['FinalRoundScore']

            # Calculate ranks and gaps
            standings['Rank'] = standings['TotalScore'].rank(method='min', ascending=ascending)

            # Find leader(s) at this hole
            leaders = standings[standings['Rank'] == 1]

            # Calculate gap to second for each leader
            if len(standings) > 1:
                for _, leader_row in leaders.iterrows():
                    leader_score = leader_row['TotalScore']
                    non_leaders = standings[standings['Player'] != leader_row['Player']]

                    if len(non_leaders) > 0:
                        if ascending:
                            second_score = non_leaders['TotalScore'].min()
                            gap = second_score - leader_score
                        else:
                            second_score = non_leaders['TotalScore'].max()
                            gap = leader_score - second_score

                        # Store this as a potential max lead
                        temp_results.append({
                            'TEGNum': teg_num,
                            'TEG': teg_name,
                            'Player': leader_row['Player'],
                            'Hole': hole,
                            'Lead': gap,
                            'TotalScore': leader_score
                        })

        # Get final results for this TEG
        final_data = df[df['TEGNum'] == teg_num]
        final_totals = final_data.groupby('Player')[measure].sum().reset_index()
        final_totals.columns = ['Player', 'FinalScore']

        if ascending:
            winner_score = final_totals['FinalScore'].min()
        else:
            winner_score = final_totals['FinalScore'].max()

        winners = final_totals[final_totals['FinalScore'] == winner_score]['Player'].tolist()

        # For each TEG, find the maximum lead held by non-winners
        teg_temp_results = [r for r in temp_results if r['TEGNum'] == teg_num]
        for player in set([r['Player'] for r in teg_temp_results]):
            if player not in winners:
                player_leads = [r for r in teg_temp_results if r['Player'] == player]
                if player_leads:
                    max_lead_record = max(player_leads, key=lambda x: x['Lead'])

                    # Calculate final gap
                    player_final = final_totals[final_totals['Player'] == player]['FinalScore'].iloc[0]
                    if ascending:
                        final_gap = player_final - winner_score
                    else:
                        final_gap = winner_score - player_final

                    final_results.append({
                        'TEG': teg_name,
                        'Player': player,
                        'Max Lead in R4': max_lead_record['Lead'],
                        'Hole of Max Lead': int(max_lead_record['Hole']),
                        'Winner': ', '.join(winners),
                        'Final Gap': final_gap,
                        '_sort_key': max_lead_record['Lead']
                    })

    # Create DataFrame from final results
    result_df = pd.DataFrame(final_results)

    if not result_df.empty:
        # Sort by max lead (biggest leads first)
        result_df = result_df.sort_values('_sort_key', ascending=False)
        result_df = result_df[['TEG', 'Player', 'Max Lead in R4', 'Hole of Max Lead', 'Winner', 'Final Gap']]

    return result_df


def calculate_biggest_comebacks(
    all_scores_df: pd.DataFrame,
    round_info_df: pd.DataFrame,
    measure: str = 'GrossVP'
) -> pd.DataFrame:
    """Find biggest score comebacks in the final round, regardless of winning.

    Identifies the biggest score differentials between any player and the leader
    going into the final round, showing who made the biggest improvement.

    Args:
        all_scores_df: DataFrame with hole-by-hole scores
        round_info_df: DataFrame with TEG round information
        measure: Scoring measure ('GrossVP' or 'Stableford')

    Returns:
        DataFrame with: TEG, Player, GapAfterR3, FinalRoundScore, GapClosed,
                        FinalPosition, Winner
    """
    # Exclude TEG 2 (only 3 rounds)
    valid_tegs = round_info_df[round_info_df['Round'] == 4]['TEGNum'].unique()
    df = all_scores_df[all_scores_df['TEGNum'].isin(valid_tegs)].copy()

    # For Stableford, only include TEG 6+
    if measure == 'Stableford':
        df = df[df['TEGNum'] >= 6]

    # Get round information
    final_rounds = round_info_df.groupby('TEGNum')['Round'].max().to_dict()

    # Calculate round totals
    round_totals = df.groupby(['TEG', 'TEGNum', 'Player', 'Round'])[measure].sum().reset_index()

    results = []
    ascending = True if measure == 'GrossVP' else False

    for teg_num, teg_name in df[['TEGNum', 'TEG']].drop_duplicates().values:
        final_round = final_rounds.get(teg_num, 4)
        penultimate_round = final_round - 1

        teg_data = round_totals[round_totals['TEGNum'] == teg_num]

        # Calculate scores after penultimate round
        penultimate_data = teg_data[teg_data['Round'] <= penultimate_round]
        penultimate_totals = penultimate_data.groupby('Player')[measure].sum().reset_index()
        penultimate_totals.columns = ['Player', 'ScoreAfterR3']

        # Get final round scores
        final_round_data = teg_data[teg_data['Round'] == final_round]
        final_round_scores = final_round_data.groupby('Player')[measure].sum().reset_index()
        final_round_scores.columns = ['Player', 'FinalRoundScore']

        # Calculate final totals
        final_totals = teg_data.groupby('Player')[measure].sum().reset_index()
        final_totals.columns = ['Player', 'FinalScore']

        # Find leader after R3
        if ascending:
            leader_r3_score = penultimate_totals['ScoreAfterR3'].min()
        else:
            leader_r3_score = penultimate_totals['ScoreAfterR3'].max()

        # Find winner
        if ascending:
            winner_score = final_totals['FinalScore'].min()
        else:
            winner_score = final_totals['FinalScore'].max()

        winners = final_totals[final_totals['FinalScore'] == winner_score]['Player'].tolist()

        # Merge all data
        merged = penultimate_totals.merge(final_round_scores, on='Player')
        merged = merged.merge(final_totals, on='Player')

        # Calculate gaps
        if ascending:
            merged['GapAfterR3'] = merged['ScoreAfterR3'] - leader_r3_score
            merged['GapAfterR4'] = merged['FinalScore'] - winner_score
        else:
            merged['GapAfterR3'] = leader_r3_score - merged['ScoreAfterR3']
            merged['GapAfterR4'] = winner_score - merged['FinalScore']

        # Calculate gap closed (positive means improved position)
        merged['GapClosed'] = merged['GapAfterR3'] - merged['GapAfterR4']

        # Calculate final rank
        merged['FinalRank'] = merged['FinalScore'].rank(method='min', ascending=ascending)

        # Get leader's final round score
        leader_final_round_score = None
        for winner in winners:
            winner_r4_score = final_round_scores[final_round_scores['Player'] == winner]['FinalRoundScore'].values
            if len(winner_r4_score) > 0:
                leader_final_round_score = winner_r4_score[0]
                break

        # Add to results
        for _, row in merged.iterrows():
            results.append({
                'TEG': teg_name,
                'Player': row['Player'],
                'Gap After R3': row['GapAfterR3'],
                'Player R4 Score': row['FinalRoundScore'],
                'Leader R4 Score': leader_final_round_score,
                'Gap Closed': row['GapClosed'],
                'Final Position': int(row['FinalRank']),
                'Winner': ', '.join(winners)
            })

    result_df = pd.DataFrame(results)

    if not result_df.empty:
        # Sort by gap closed (biggest comebacks first)
        result_df = result_df.sort_values('Gap Closed', ascending=False)

    return result_df
