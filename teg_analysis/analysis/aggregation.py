"""Core aggregation engine and data accessors.

This module provides:
- TEG round lookup functions
- The general-purpose aggregation engine (aggregate_data)
- Cached data accessors (get_complete_teg_data, get_round_data, etc.)
- TEG status functions (get_last_completed_teg_fast, etc.)
- Round/TEG selection helpers and context display
- Comeback and collapse analysis
- Scorecard selection helpers
"""


import logging
import pandas as pd
from typing import List

from teg_analysis.constants import TEG_ROUNDS, TEGNUM_ROUNDS

logger = logging.getLogger(__name__)


# === LOOKUP FUNCTIONS ===

def get_teg_rounds(TEG: str) -> int:
    """Return the number of rounds for a given TEG.

    If the TEG is not found in the dictionary, return 4 as the default value.

    Parameters:
        TEG (str): The TEG identifier (e.g., 'TEG 1', 'TEG 2', etc.)

    Returns:
        int: The total number of rounds for the given TEG, defaulting to 4 if not found.
    """
    return TEG_ROUNDS.get(TEG, 4)


def get_tegnum_rounds(TEGNum: int) -> int:
    """Return the number of rounds for a given TEG by number.

    If the TEG is not found in the dictionary, return 4 as the default value.

    Parameters:
        TEGNum (int): The TEG number (e.g., 1, 2, 3, etc.)

    Returns:
        int: The total number of rounds for the given TEG, defaulting to 4 if not found.
    """
    return TEGNUM_ROUNDS.get(TEGNum, 4)


# === AGGREGATION ENGINE ===

def list_fields_by_aggregation_level(df):
    """Determine which fields are unique at each aggregation level.

    Args:
        df (pd.DataFrame): DataFrame to analyze.

    Returns:
        dict: Dictionary mapping aggregation levels to unique fields.
    """
    # Define the levels of aggregation
    aggregation_levels = {
        'Player': ['Player'],
        'TEG': ['Player', 'TEG'],
        'Round': ['Player', 'TEG', 'Round'],
        'FrontBack': ['Player', 'TEG', 'Round', 'FrontBack'],
    }

    # Dictionary to hold fields unique at each level
    fields_by_level = {level: [] for level in aggregation_levels}

    # For each field in the dataframe, determine its uniqueness level
    for col in df.columns:
        for level, group_fields in aggregation_levels.items():
            # Check if the field is unique at this level
            if df.groupby(group_fields)[col].nunique().max() == 1:
                fields_by_level[level].append(col)
                break  # Stop after finding the lowest level of uniqueness

    return fields_by_level


def aggregate_data(data: pd.DataFrame, aggregation_level: str, measures: List[str] = None, additional_group_fields: List[str] = None) -> pd.DataFrame:
    """Generalized aggregation function with dynamic level of aggregation and additional group fields.

    Parameters:
        data (pd.DataFrame): The DataFrame to aggregate.
        aggregation_level (str): The level of aggregation ('Player', 'TEG', 'Round', 'FrontBack', 'Hole'). Use 'Player' for career/all-time totals.
        measures (List[str], optional): List of measure columns to aggregate. Defaults to standard measures.
        additional_group_fields (List[str], optional): Additional fields to include in the grouping. Defaults to None.

    Returns:
        pd.DataFrame: Aggregated DataFrame.
    """
    # Set default measures if none provided
    if measures is None:
        measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']

    # Get the fields related to each aggregation level
    fields_by_level = list_fields_by_aggregation_level(data)

    # Define the hierarchy of aggregation levels
    aggregation_hierarchy = ['Player', 'TEG', 'Round', 'FrontBack', 'Hole']

    if aggregation_level not in aggregation_hierarchy:
        raise ValueError(f"Invalid aggregation level: '{aggregation_level}'. Choose from: {aggregation_hierarchy}")

    # Determine which fields to include based on the selected aggregation level
    idx = aggregation_hierarchy.index(aggregation_level)
    group_columns = []

    # Add all fields from the selected aggregation level and higher levels
    for level in aggregation_hierarchy[:idx + 1]:
        group_columns.extend(fields_by_level[level])

    # Add additional group fields if provided
    if additional_group_fields:
        if isinstance(additional_group_fields, str):
            additional_group_fields = [additional_group_fields]  # Wrap in a list if it's a string
        group_columns.extend(additional_group_fields)

    # Ensure group columns are unique
    group_columns = list(set(group_columns))

    # Check if all group_columns are present in the DataFrame
    missing_columns = [col for col in group_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"Missing columns in the DataFrame: {missing_columns}")

    # Perform aggregation
    aggregated_df = data.groupby(group_columns, as_index=False)[measures].sum()
    aggregated_df = aggregated_df.sort_values(by=group_columns)

    return aggregated_df


# === CACHED AGGREGATION FUNCTIONS ===

def get_complete_teg_data():
    """Get complete TEG-level data (excluding TEG 50 and incomplete TEGs).

    Returns:
        pd.DataFrame: TEG-level aggregated data.
    """
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=True)
    aggregated_data = aggregate_data(all_data, 'TEG')
    return aggregated_data


def get_teg_data_inc_in_progress():
    """Get TEG-level data including in-progress TEGs.

    Returns:
        pd.DataFrame: TEG-level aggregated data including incomplete TEGs.
    """
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'TEG')
    return aggregated_data


def get_round_data(ex_50=True, ex_incomplete=False):
    """Get round-level aggregated data.

    Args:
        ex_50 (bool): Exclude TEG 50 if True.
        ex_incomplete (bool): Exclude incomplete TEGs if True.

    Returns:
        pd.DataFrame: Round-level aggregated data.
    """
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=ex_50, exclude_incomplete_tegs=ex_incomplete)
    aggregated_data = aggregate_data(all_data, 'Round')
    return aggregated_data


def get_9_data():
    """Get 9-hole (front/back) aggregated data.

    Returns:
        pd.DataFrame: 9-hole aggregated data.
    """
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'FrontBack')
    return aggregated_data


def get_Pl_data():
    """Get player-level aggregated data.

    Returns:
        pd.DataFrame: Player-level aggregated data.
    """
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'Player')
    return aggregated_data


# === ROUND/TEG SELECTION HELPERS ===

def get_round_metric_mappings() -> tuple[dict, dict]:
    """Gets mappings between user-friendly and internal metric names for rounds.

    Returns:
        tuple: A tuple containing two dictionaries:
            - name_mapping (dict): Maps user-friendly names to internal names.
            - inverted_mapping (dict): Maps internal names to user-friendly
              names.
    """
    name_mapping = {
        'Gross vs Par': 'GrossVP',
        'Score': 'Sc',
        'Net vs Par': 'NetVP',
        'Stableford': 'Stableford'
    }
    inverted_mapping = {v: k for k, v in name_mapping.items()}

    return name_mapping, inverted_mapping


def get_latest_round_defaults(df_round: pd.DataFrame) -> tuple[str, int]:
    """Gets the default TEG and round values (the latest available).

    Pure calculation function - determines the most recent round.

    Args:
        df_round (pd.DataFrame): A DataFrame of round ranking data, used as a
            fallback.

    Returns:
        tuple: A tuple containing the max TEG and max round in that TEG.

    Raises:
        ValueError: If df_round is empty or invalid
    """
    if df_round.empty:
        raise ValueError("Cannot determine latest round from empty DataFrame")

    try:
        # Fallback to DataFrame method
        df_sorted = df_round.sort_values(by=['TEGNum', 'Round'])
        max_teg = df_sorted.loc[df_sorted['TEGNum'].idxmax(), 'TEG']
        max_round_in_max_teg = df_sorted[df_sorted['TEG'] == max_teg]['Round'].max()
        return max_teg, max_round_in_max_teg

    except Exception as e:
        raise ValueError(f"Error determining latest round: {e}")


def get_teg_and_round_options(df_round: pd.DataFrame, selected_teg: str) -> tuple[list, list]:
    """Gets available TEG and round options for selection dropdowns.

    Args:
        df_round (pd.DataFrame): The round ranking data.
        selected_teg (str): The currently selected TEG.

    Returns:
        tuple: A tuple containing:
            - teg_options (list): A list of TEG options.
            - round_options (list): A list of round options for the
              selected TEG.
    """
    teg_options = list(df_round['TEG'].unique())
    round_options = sorted(df_round[df_round['TEG'] == selected_teg]['Round'].unique())

    return teg_options, round_options


def create_metric_tabs_data(metrics: list) -> tuple[list, list]:
    """Prepares metric data for tabbed display.

    Args:
        metrics (list): A list of internal metric names.

    Returns:
        tuple: A tuple containing:
            - metrics (list): The original list of internal metric names.
            - friendly_metrics (list): A list of user-friendly metric names.
    """
    name_mapping, inverted_name_mapping = get_round_metric_mappings()
    friendly_metrics = [inverted_name_mapping[metric] for metric in metrics]

    return metrics, friendly_metrics


def prepare_round_context_display(df_round: pd.DataFrame, teg_r: str, rd_r: int, metric: str, friendly_metric: str) -> pd.DataFrame:
    """Prepares round context data for display in a specific metric tab.

    Args:
        df_round (pd.DataFrame): The round ranking data.
        teg_r (str): The selected TEG.
        rd_r (int): The selected round.
        metric (str): The internal metric name.
        friendly_metric (str): The user-friendly metric name.

    Returns:
        pd.DataFrame: A context table with renamed columns for display.
    """
    df = df_round.copy()
    all_cnt = len(df)
    df['Pl_count'] = df.groupby('Pl')['Pl'].transform('count')
    chosen_rd = df[(df['TEG'] == teg_r) & (df['Round'] == rd_r)]

    sort_ascending = metric != 'Stableford'
    chosen_rd = chosen_rd.sort_values(metric, ascending=sort_ascending)
    chosen_rd['Pl rank'] = (chosen_rd[f'Rank_within_player_{metric}'].astype(int).astype(str) +
                            ' / ' + chosen_rd['Pl_count'].astype(str))
    chosen_rd['All time rank'] = (chosen_rd[f'Rank_within_all_{metric}'].astype(int).astype(str) +
                                  ' / ' + str(all_cnt))
    context_data = chosen_rd[['Player', metric, 'Pl rank', 'All time rank']]

    # Rename metric column to friendly name for display
    display_data = context_data.rename(columns={metric: friendly_metric})

    return display_data


# === TEG CONTEXT FUNCTIONS ===

def get_latest_teg_default(df_teg: pd.DataFrame) -> str:
    """Gets the default TEG value (the latest available).

    Pure calculation function - determines the most recent TEG.

    Args:
        df_teg (pd.DataFrame): A DataFrame of TEG ranking data.

    Returns:
        str: The latest available TEG for default selection.

    Raises:
        ValueError: If df_teg is empty or invalid
    """
    if df_teg.empty:
        raise ValueError("Cannot determine latest TEG from empty DataFrame")

    try:
        # Fallback to DataFrame method
        df_sorted = df_teg.sort_values(by='TEGNum')
        max_teg = df_sorted.loc[df_sorted['TEGNum'].idxmax(), 'TEG']
        return max_teg

    except Exception as e:
        raise ValueError(f"Error determining latest TEG: {e}")


def get_teg_options(df_teg: pd.DataFrame) -> list:
    """Gets available TEG options for the selection dropdown.

    Args:
        df_teg (pd.DataFrame): The TEG ranking data.

    Returns:
        list: A list of TEG options for the dropdown menu.
    """
    return list(df_teg['TEG'].unique())


def prepare_teg_context_display(df_teg: pd.DataFrame, teg_t: str, metric: str, friendly_metric: str) -> pd.DataFrame:
    """Prepares TEG context data for display in a specific metric tab.

    Args:
        df_teg (pd.DataFrame): The TEG ranking data.
        teg_t (str): The selected TEG.
        metric (str): The internal metric name.
        friendly_metric (str): The user-friendly metric name.

    Returns:
        pd.DataFrame: A context table with renamed columns for display.
    """
    df = df_teg.copy()
    all_cnt = len(df)
    df['Pl_count'] = df.groupby('Pl')['Pl'].transform('count')
    chosen_teg = df[df['TEG'] == teg_t]

    sort_ascending = metric != 'Stableford'
    chosen_teg = chosen_teg.sort_values(metric, ascending=sort_ascending)
    chosen_teg['Pl rank'] = (chosen_teg[f'Rank_within_player_{metric}'].astype(int).astype(str) +
                             ' / ' + chosen_teg['Pl_count'].astype(str))
    chosen_teg['All time rank'] = (chosen_teg[f'Rank_within_all_{metric}'].astype(int).astype(str) +
                                   ' / ' + str(all_cnt))
    context_data = chosen_teg[['Player', metric, 'Pl rank', 'All time rank']]

    # Rename metric column to friendly name for display
    display_data = context_data.rename(columns={metric: friendly_metric})

    return display_data


# === COMEBACK AND COLLAPSE ANALYSIS ===

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


# === SCORECARD SELECTION HELPERS ===

def prepare_scorecard_selection_options(all_data: pd.DataFrame) -> dict:
    """Prepares dropdown options for the scorecard selection interface.

    Args:
        all_data (pd.DataFrame): The complete dataset with all hole-by-hole data.

    Returns:
        dict: A dictionary containing sorted lists for player, TEG, and round options.
    """
    return {
        'players': sorted(all_data['Pl'].unique()),
        'tournaments': sorted(all_data['TEGNum'].unique()),
        'all_data': all_data  # Keep reference for dynamic round filtering
    }


def get_round_options_for_tournament(all_data: pd.DataFrame, selected_tegnum: int) -> list:
    """Gets the available rounds for a specific tournament.

    Args:
        all_data (pd.DataFrame): The complete dataset.
        selected_tegnum (int): The selected tournament number.

    Returns:
        list: A sorted list of available rounds for the tournament.
    """
    return sorted(all_data[all_data['TEGNum'] == selected_tegnum]['Round'].unique())


def validate_and_prepare_single_round_data(rd_data: pd.DataFrame) -> tuple[bool, pd.DataFrame, str]:
    """Validates and prepares data for a single round scorecard display.

    Args:
        rd_data (pd.DataFrame): The raw round data.

    Returns:
        tuple: A tuple containing:
            - is_valid (bool): True if the data is valid, False otherwise.
            - prepared_data (pd.DataFrame or None): The prepared data, or None if invalid.
            - error_message (str or None): An error message, or None if valid.
    """
    if len(rd_data) == 0:
        return False, None, "No data found for the selected round"

    # Define columns needed for scorecard display
    output_cols = ['Hole', 'PAR', 'SI', 'HCStrokes', 'Sc', 'GrossVP', 'NetVP', 'Stableford']
    output_data = rd_data[output_cols].copy()

    # Convert numeric data to integers, handling NaN values
    def to_int_or_zero(x):
        if pd.isna(x):
            return 0
        return int(x)

    # Apply conversion to all numeric columns
    numeric_columns = output_data.select_dtypes(include=['float64', 'int64']).columns
    for col in numeric_columns:
        output_data[col] = output_data[col].map(to_int_or_zero)

    # Validate that we have complete 18-hole data
    if len(output_data) != 18:
        return False, None, f"Expected 18 holes, found {len(output_data)} holes for this round."

    return True, output_data, None


def get_scorecard_type_mapping() -> tuple[list, list]:
    """Defines the mapping between internal tab names and user-friendly display names.

    Returns:
        tuple: A tuple containing:
            - tab_names (list): A list of internal tab names.
            - display_names (list): A list of user-friendly display names.
    """
    tab_names = ["1 Round / All Players", "1 Player / All Rounds", "1 Round / 1 Player"]
    display_names = ["Round Comparison (all players)", "Tournament view (one player)", "Single Player Round"]

    return tab_names, display_names


def determine_control_states(selected_tab: str) -> dict:
    """Determines which UI controls should be enabled or disabled.

    Args:
        selected_tab (str): The currently selected scorecard type.

    Returns:
        dict: A dictionary of control states for player and round selection.
    """
    return {
        'player_disabled': (selected_tab == "1 Round / All Players"),
        'round_disabled': (selected_tab == "1 Player / All Rounds")
    }


def prepare_tournament_display_data(tournament_data: pd.DataFrame) -> dict or None:
    """Prepares data for the tournament view display.

    Args:
        tournament_data (pd.DataFrame): The raw tournament data.

    Returns:
        dict or None: The prepared data with the player name and tournament
        name, or None if the input data is empty.
    """
    if len(tournament_data) == 0:
        return None

    return {
        'player_name': tournament_data['Player'].iloc[0],
        'teg_name': f"TEG {tournament_data['TEGNum'].iloc[0]}"
    }


# === TEG STATUS FUNCTIONS (Fast Checks) ===

def get_last_completed_teg_fast() -> tuple:
    """Get the highest TEG number from completed_tegs.csv with round count.

    Uses status file for fast lookup without loading full dataset.

    Returns:
        tuple: (teg_num, rounds) or (None, 0) if no completed TEGs
    """
    from ..io.file_operations import read_file

    try:
        completed_tegs = read_file('data/completed_tegs.csv')
        if completed_tegs.empty:
            return None, 0

        max_row = completed_tegs.loc[completed_tegs['TEGNum'].idxmax()]
        return int(max_row['TEGNum']), int(max_row['Rounds'])

    except Exception as e:
        logger.warning(f"Error reading completed TEGs status file: {e}")
        return None, 0


def get_current_in_progress_teg_fast() -> tuple:
    """Get the current in-progress TEG with round count.

    Uses status file for fast lookup without loading full dataset.

    Returns:
        tuple: (teg_num, rounds) or (None, 0) if no TEGs in progress
    """
    from ..io.file_operations import read_file

    try:
        in_progress_tegs = read_file('data/in_progress_tegs.csv')
        if in_progress_tegs.empty:
            return None, 0

        # Should typically be only one in-progress TEG, get the first one
        current_row = in_progress_tegs.iloc[0]
        return int(current_row['TEGNum']), int(current_row['Rounds'])

    except Exception as e:
        logger.warning(f"Error reading in-progress TEGs status file: {e}")
        return None, 0


def has_incomplete_teg_fast() -> bool:
    """Fast check if there are any incomplete TEGs using status files.

    Returns:
        bool: True if there are TEGs in progress, False otherwise
    """
    from ..io.file_operations import read_file

    try:
        in_progress_tegs = read_file('data/in_progress_tegs.csv')
        return not in_progress_tegs.empty

    except Exception as e:
        logger.warning(f"Error checking for incomplete TEGs: {e}")
        return False
