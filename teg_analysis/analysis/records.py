"""Records and Personal Bests identification functions.

This module contains functions for identifying all-time records, personal
bests, and personal worsts from ranked data, as well as displaying them in a
clean summary format.
"""


import pandas as pd
import logging

logger = logging.getLogger(__name__)


def get_friendly_metric_name(metric: str) -> str:
    """Converts an internal metric name to a user-friendly display name.

    Args:
        metric (str): The internal metric name (e.g., 'Sc', 'GrossVP').

    Returns:
        str: The user-friendly metric name.
    """
    name_mapping = {
        'Sc': 'Score',
        'GrossVP': 'Gross vs Par',
        'NetVP': 'Net vs Par',
        'Stableford': 'Stableford'
    }
    return name_mapping.get(metric, metric)



def identify_aggregate_records_and_pbs(df_teg_or_round: pd.DataFrame, selected_teg: str, selected_round: int = None) -> dict:
    """Identifies records and personal bests from aggregate score metrics.

    This function scans ranked data for all-time records, personal bests, and
    personal worsts using pre-calculated ranking columns.

    Args:
        df_teg_or_round (pd.DataFrame): The ranked TEG or round data.
        selected_teg (str): The selected TEG (e.g., "TEG 17").
        selected_round (int, optional): The selected round number. Defaults
            to None.

    Returns:
        dict: A dictionary containing lists of records, personal bests, and
        personal worsts.
    """
    # Filter to selected TEG/round
    if selected_round is not None:
        filtered = df_teg_or_round[(df_teg_or_round['TEG'] == selected_teg) &
                                    (df_teg_or_round['Round'] == selected_round)]
    else:
        filtered = df_teg_or_round[df_teg_or_round['TEG'] == selected_teg]

    if filtered.empty:
        return {
            'records': [],
            'personal_bests': [],
            'personal_worsts': []
        }

    metrics = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    records = []
    personal_bests = []
    personal_worsts = []

    for metric in metrics:
        rank_all_col = f'Rank_within_all_{metric}'
        rank_player_col = f'Rank_within_player_{metric}'

        # Skip if columns don't exist
        if rank_all_col not in filtered.columns or rank_player_col not in filtered.columns:
            continue

        # Check each player's performance
        for _, row in filtered.iterrows():
            player = row['Player']
            value = row[metric]

            # All-time record (rank 1 across all players/TEGs)
            if row[rank_all_col] == 1:
                records.append({
                    'player': player,
                    'metric': metric,
                    'value': value,
                    'friendly_name': get_friendly_metric_name(metric)
                })

            # Personal best (rank 1 within player's history)
            if row[rank_player_col] == 1:
                personal_bests.append({
                    'player': player,
                    'metric': metric,
                    'value': value,
                    'friendly_name': get_friendly_metric_name(metric)
                })

            # Personal worst (highest rank within player's history)
            # Only include if they have more than 1 performance (rank > 1 exists)
            player_data = df_teg_or_round[df_teg_or_round['Player'] == player]
            max_rank = player_data[rank_player_col].max()
            if row[rank_player_col] == max_rank and max_rank > 1:
                personal_worsts.append({
                    'player': player,
                    'metric': metric,
                    'value': value,
                    'friendly_name': get_friendly_metric_name(metric)
                })

    return {
        'records': records,
        'personal_bests': personal_bests,
        'personal_worsts': personal_worsts
    }


def identify_9hole_records_and_pbs(selected_teg: str, selected_round: int, df_9hole: pd.DataFrame = None) -> dict:
    """Identifies 9-hole records and personal bests for the selected round.

    This function checks if the front 9 or back 9 of the selected round set
    any records or personal bests.

    Args:
        selected_teg (str): The selected TEG (e.g., "TEG 17").
        selected_round (int): The selected round number.
        df_9hole (pd.DataFrame, optional): Pre-ranked 9-hole data. If None,
            will attempt to generate from loaded data.

    Returns:
        dict: A dictionary containing lists of records and personal bests for
        9-hole segments.
    """
    if df_9hole is None:
        logger.warning("No 9-hole data provided to identify_9hole_records_and_pbs")
        return {'records': [], 'personal_bests': []}

    # Parse TEG number
    teg_num = int(selected_teg.split()[1])

    # Filter to selected TEG and round
    filtered = df_9hole[(df_9hole['TEGNum'] == teg_num) &
                        (df_9hole['Round'] == selected_round)]

    if filtered.empty:
        return {
            'records': [],
            'personal_bests': []
        }

    metrics = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    records = []
    personal_bests = []

    for metric in metrics:
        rank_all_col = f'Rank_within_all_{metric}'
        rank_player_col = f'Rank_within_player_{metric}'

        # Skip if columns don't exist
        if rank_all_col not in filtered.columns or rank_player_col not in filtered.columns:
            continue

        # Check each 9-hole segment
        for _, row in filtered.iterrows():
            player = row['Player']
            value = row[metric]
            segment = row['FrontBack']  # 'Front' or 'Back'

            # All-time record
            if row[rank_all_col] == 1:
                records.append({
                    'player': player,
                    'metric': metric,
                    'value': value,
                    'friendly_name': get_friendly_metric_name(metric),
                    'segment': segment
                })

            # Personal best
            if row[rank_player_col] == 1:
                personal_bests.append({
                    'player': player,
                    'metric': metric,
                    'value': value,
                    'friendly_name': get_friendly_metric_name(metric),
                    'segment': segment
                })

    return {
        'records': records,
        'personal_bests': personal_bests
    }


def identify_streak_records(all_data: pd.DataFrame, streaks_df: pd.DataFrame, selected_teg: str, selected_round: int = None) -> dict:
    """Identifies streak records for the selected TEG or round.

    This function compares the displayed streak values against all-time streak
    records to identify when a player's streak matches a record.

    Args:
        all_data (pd.DataFrame): The complete tournament data.
        streaks_df (pd.DataFrame): The streak data.
        selected_teg (str): The selected TEG (e.g., "TEG 17").
        selected_round (int, optional): The selected round number. Defaults
            to None.

    Returns:
        dict: A dictionary containing a list of streak records.
    """
    from teg_analysis.analysis.streaks import (
        prepare_record_streaks_data,
        get_player_window_streaks
    )

    try:
        # Get record streaks
        best_streak_records = prepare_record_streaks_data(all_data, 'good')
        worst_streak_records = prepare_record_streaks_data(all_data, 'bad')

        # Combine into single lookup dataframe
        all_streak_records = pd.concat([best_streak_records, worst_streak_records], ignore_index=True)

        # Get streaks for this TEG/round
        if selected_round is not None:
            teg_streaks = get_player_window_streaks(
                all_data,
                streaks_df,
                teg=selected_teg,
                round_num=selected_round
            )
        else:
            # For TEG, get through last round
            teg_num = int(selected_teg.split()[1])
            teg_data = all_data[all_data['TEGNum'] == teg_num]
            if teg_data.empty:
                return {'records': []}
            last_round = teg_data['Round'].max()
            teg_streaks = get_player_window_streaks(
                all_data,
                streaks_df,
                teg=selected_teg,
                round_num=last_round
            )

        if teg_streaks.empty:
            return {'records': []}

        records = []

        # Compare each player's streak to records
        for _, row in teg_streaks.iterrows():
            streak_type = row['Streak Type']
            player = row['Player']
            max_streak = row['Max Streak']

            # Check if this matches a record
            matching_records = all_streak_records[
                all_streak_records['Streak Type'] == streak_type
            ]

            if not matching_records.empty:
                # Get the record value (should be same across all matching rows)
                record_value = int(matching_records.iloc[0]['Record'])

                # If player's streak matches record, add it
                if max_streak == record_value:
                    records.append({
                        'player': player,
                        'streak_type': streak_type,
                        'value': max_streak
                    })

        return {'records': records}

    except Exception as e:
        # If any error occurs in streak processing, return empty
        return {'records': []}


def identify_all_time_worsts(df_teg_or_round: pd.DataFrame, selected_teg: str, selected_round: int = None) -> list:
    """Identifies all-time worst performances from aggregate score metrics.

    This function identifies if the selected TEG or round contains any
    all-time worst performances by checking for the maximum rank.

    Args:
        df_teg_or_round (pd.DataFrame): The ranked TEG or round data.
        selected_teg (str): The selected TEG (e.g., "TEG 17").
        selected_round (int, optional): The selected round number. Defaults
            to None.

    Returns:
        list: A list of dictionaries containing information about the worst
        performances.
    """
    # Filter to selected TEG/round
    if selected_round is not None:
        filtered = df_teg_or_round[(df_teg_or_round['TEG'] == selected_teg) &
                                    (df_teg_or_round['Round'] == selected_round)]
    else:
        filtered = df_teg_or_round[df_teg_or_round['TEG'] == selected_teg]

    if filtered.empty:
        return []

    metrics = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    all_time_worsts = []

    for metric in metrics:
        rank_all_col = f'Rank_within_all_{metric}'

        # Skip if column doesn't exist
        if rank_all_col not in filtered.columns:
            continue

        # Find the worst rank across all data for this metric
        max_rank_all_time = df_teg_or_round[rank_all_col].max()

        # Check each player's performance in selected TEG/round
        for _, row in filtered.iterrows():
            player = row['Player']
            value = row[metric]

            # If this matches the all-time worst rank
            if row[rank_all_col] == max_rank_all_time:
                all_time_worsts.append({
                    'player': player,
                    'metric': metric,
                    'value': value,
                    'friendly_name': get_friendly_metric_name(metric)
                })

    return all_time_worsts


def identify_score_count_records(all_data: pd.DataFrame, selected_teg: str, selected_round: int = None) -> dict:
    """Identifies score count records for the selected TEG or round.

    This function identifies records for specific score types, such as most
    Eagles, Birdies, Pars, or TBPs.

    Args:
        all_data (pd.DataFrame): The complete tournament data.
        selected_teg (str): The selected TEG (e.g., "TEG 17").
        selected_round (int, optional): The selected round number. Defaults
            to None.

    Returns:
        dict: A dictionary containing lists of the best and worst score count
        records.
    """
    from teg_analysis.analysis.scoring import count_scores_by_player

    try:
        # Filter to selected TEG/round
        teg_num = int(selected_teg.split()[1])
        if selected_round is not None:
            filtered_data = all_data[(all_data['TEGNum'] == teg_num) &
                                      (all_data['Round'] == selected_round)]
        else:
            filtered_data = all_data[all_data['TEGNum'] == teg_num]

        if filtered_data.empty:
            return {'best_score_counts': [], 'worst_score_counts': []}

        # Get score counts for this TEG/round
        score_counts = count_scores_by_player(filtered_data, field='GrossVP')

        # Get player columns
        player_cols = [col for col in score_counts.columns]

        best_records = []
        worst_records = []

        # Define score categories to check
        score_categories = {
            'Eagles': -2,  # Exactly -2
            'Birdies (or better)': [-2, -1],  # -2 or -1
            'Pars (or better)': [-2, -1, 0],  # -2, -1, or 0
            'TBPs': [3, 4, 5, 6, 7, 8, 9, 10]  # +3 or worse
        }

        # Calculate counts for each category
        for category, scores in score_categories.items():
            if not isinstance(scores, list):
                scores = [scores]

            # Sum counts for each player across the score range
            player_counts = {}
            for player in player_cols:
                total = 0
                for score in scores:
                    if score in score_counts.index:
                        total += score_counts.loc[score, player]
                player_counts[player] = total

            # Find max count for this category
            max_count = max(player_counts.values()) if player_counts else 0

            if max_count == 0:
                continue  # Skip if no one has this score

            # Get all-time record for this category by checking all data
            all_time_max = get_all_time_score_count_record(all_data, category, scores, selected_round is not None)

            # Check if this matches the all-time record
            for player, count in player_counts.items():
                if count == all_time_max and count > 0:
                    record_data = {
                        'player': player,
                        'score_type': category,
                        'count': count
                    }

                    # Categorize as best or worst
                    if category == 'TBPs':
                        worst_records.append(record_data)
                    else:
                        best_records.append(record_data)

        return {
            'best_score_counts': best_records,
            'worst_score_counts': worst_records
        }

    except Exception as e:
        return {'best_score_counts': [], 'worst_score_counts': []}


def get_all_time_score_count_record(all_data: pd.DataFrame, category: str, scores: list, is_round_level: bool = True) -> int:
    """Gets the all-time record for a specific score count category.

    Args:
        all_data (pd.DataFrame): The complete tournament data.
        category (str): The name of the score category.
        scores (list): A list of score values to include in the count.
        is_round_level (bool, optional): True for round-level records, False
            for TEG-level records. Defaults to True.

    Returns:
        int: The maximum count for the category across all history.
    """
    from teg_analysis.analysis.scoring import count_scores_by_player

    try:
        max_count = 0

        if is_round_level:
            # Check each round separately
            for (teg_num, round_num), group in all_data.groupby(['TEGNum', 'Round']):
                score_counts = count_scores_by_player(group, field='GrossVP')
                player_cols = [col for col in score_counts.columns]

                for player in player_cols:
                    total = 0
                    for score in scores:
                        if score in score_counts.index:
                            total += score_counts.loc[score, player]
                    max_count = max(max_count, total)
        else:
            # Check each TEG separately
            for teg_num, group in all_data.groupby('TEGNum'):
                score_counts = count_scores_by_player(group, field='GrossVP')
                player_cols = [col for col in score_counts.columns]

                for player in player_cols:
                    total = 0
                    for score in scores:
                        if score in score_counts.index:
                            total += score_counts.loc[score, player]
                    max_count = max(max_count, total)

        return max_count

    except Exception:
        return 0

