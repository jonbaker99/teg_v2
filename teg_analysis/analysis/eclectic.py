"""Eclectic score calculations — best score per hole across rounds.

Ported from streamlit/eclectic_utils.py (no Streamlit dependencies).
"""

import pandas as pd
import numpy as np


def calculate_eclectic_by_dimension(data: pd.DataFrame, dimension: str) -> tuple[pd.DataFrame, str]:
    """Calculates eclectic scores grouped by a specified dimension.

    Args:
        data: The input DataFrame with hole-by-hole scores.
        dimension: The dimension to group by ('Player', 'TEGNum', 'Course',
            'Teams', or 'Combined').

    Returns:
        A tuple of (eclectic DataFrame, display dimension name).
    """
    if data.empty:
        return pd.DataFrame(), dimension

    if dimension == 'Teams':
        return calculate_team_eclectics(data)
    elif dimension == 'Combined':
        return calculate_combined_eclectic(data)

    group_cols = [dimension, 'Hole']
    eclectic_holes = data.groupby(group_cols)['GrossVP'].min().reset_index()

    # Count rounds contributing to each dimension's eclectic
    if dimension == 'TEGNum':
        rounds_count = data.groupby(dimension)['Round'].nunique().reset_index()
        rounds_count.rename(columns={'Round': 'Rounds'}, inplace=True)
    else:
        rounds_count = data.groupby(dimension).agg({
            'Round': 'nunique',
            'TEGNum': 'nunique'
        }).reset_index()

    if dimension == 'Player':
        rounds_count['Rounds'] = data.groupby(dimension).apply(
            lambda x: len(x[['TEGNum', 'Round']].drop_duplicates())
        ).values
    elif dimension == 'Course':
        rounds_count['Rounds'] = data.groupby(dimension).apply(
            lambda x: len(x[['TEGNum', 'Round']].drop_duplicates())
        ).values

    display_dimension = dimension
    if dimension == 'TEGNum':
        eclectic_holes['TEG'] = 'TEG ' + eclectic_holes['TEGNum'].astype(str)
        rounds_count['TEG'] = 'TEG ' + rounds_count['TEGNum'].astype(str)
        display_dimension = 'TEG'

    eclectic_pivot = eclectic_holes.pivot(index=display_dimension, columns='Hole', values='GrossVP')
    eclectic_pivot.columns.name = None

    for hole in range(1, 19):
        if hole not in eclectic_pivot.columns:
            eclectic_pivot[hole] = np.nan

    hole_cols = sorted([col for col in eclectic_pivot.columns if isinstance(col, int)])
    eclectic_pivot = eclectic_pivot[hole_cols]
    eclectic_pivot['Total'] = eclectic_pivot.sum(axis=1, skipna=True)
    eclectic_pivot = eclectic_pivot.reset_index()
    eclectic_pivot = eclectic_pivot.merge(rounds_count[[display_dimension, 'Rounds']], on=display_dimension, how='left')
    eclectic_pivot = eclectic_pivot.sort_values('Total').reset_index(drop=True)

    return eclectic_pivot, display_dimension


def calculate_team_eclectics(data: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Calculates eclectic scores for the Heroes vs. Wildcats teams."""
    heroes = ['Jon BAKER', 'David MULLIN', 'Stuart NEUMANN']
    wildcats = ['Alex BAKER', 'Gregg WILLIAMS', 'John PATTERSON']

    heroes_data = data[data['Player'].isin(heroes)]
    wildcats_data = data[data['Player'].isin(wildcats)]

    team_results = []

    for team_name, team_data in [('Heroes', heroes_data), ('Wildcats', wildcats_data)]:
        if team_data.empty:
            continue

        team_eclectic = team_data.groupby('Hole')['GrossVP'].min().reset_index()
        team_eclectic['Team'] = team_name
        total_rounds = len(team_data.groupby(['Player', 'TEGNum', 'Round']))
        team_eclectic['Rounds'] = total_rounds
        team_results.append(team_eclectic)

    if not team_results:
        return pd.DataFrame(), 'Team'

    all_teams = pd.concat(team_results, ignore_index=True)
    team_pivot = all_teams.pivot(index='Team', columns='Hole', values='GrossVP')
    team_pivot.columns.name = None

    for hole in range(1, 19):
        if hole not in team_pivot.columns:
            team_pivot[hole] = np.nan

    hole_cols = sorted([col for col in team_pivot.columns if isinstance(col, int)])
    team_pivot = team_pivot[hole_cols]
    team_pivot['Total'] = team_pivot.sum(axis=1, skipna=True)
    team_pivot = team_pivot.reset_index()

    rounds_data = []
    for team_name, team_data in [('Heroes', heroes_data), ('Wildcats', wildcats_data)]:
        if not team_data.empty:
            rounds_data.append({
                'Team': team_name,
                'Rounds': len(team_data.groupby(['Player', 'TEGNum', 'Round']))
            })

    rounds_df = pd.DataFrame(rounds_data)
    team_pivot = team_pivot.merge(rounds_df, on='Team', how='left')
    team_pivot = team_pivot.sort_values('Total').reset_index(drop=True)

    return team_pivot, 'Team'


def calculate_combined_eclectic(data: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Calculates a single combined eclectic score from all data."""
    if data.empty:
        return pd.DataFrame(), 'Combined'

    combined_eclectic = data.groupby('Hole')['GrossVP'].min()
    total_rounds = len(data.groupby(['Player', 'TEGNum', 'Round']))

    row_data = {'Combined': 'All Data'}
    for hole in range(1, 19):
        row_data[hole] = combined_eclectic[hole] if hole in combined_eclectic.index else np.nan

    hole_scores = [row_data[hole] for hole in range(1, 19) if not pd.isna(row_data[hole])]
    row_data['Total'] = sum(hole_scores)
    row_data['Rounds'] = total_rounds

    result_df = pd.DataFrame([row_data])
    hole_cols = list(range(1, 19))
    ordered_cols = ['Combined', 'Total', 'Rounds'] + hole_cols
    result_df = result_df[ordered_cols]

    return result_df, 'Combined'


def get_overall_top_eclectics(data: pd.DataFrame, dimension: str, top_n: int = 3) -> pd.DataFrame:
    """Gets the overall top N eclectics across all players, including ties.

    For each player, computes their per-dimension eclectics (e.g. one row per
    TEG or per Course), then returns the best ``top_n`` rows across all
    players. Ties for the Nth-best score are all included.

    Args:
        data: Hole-by-hole score data.
        dimension: Dimension to group eclectics by ('TEGNum' or 'Course').
        top_n: Number of top records to return (ties included). Defaults to 3.

    Returns:
        DataFrame of the top eclectic scores with a 'Player' column added.
    """
    all_results = []
    players = sorted(data['Player'].unique())

    for player in players:
        player_data = data[data['Player'] == player]
        if player_data.empty:
            continue

        eclectics, _actual_dimension = calculate_eclectic_by_dimension(player_data, dimension)
        if eclectics.empty:
            continue

        eclectics['Player'] = player
        all_results.append(eclectics)

    if not all_results:
        return pd.DataFrame()

    combined_results = pd.concat(all_results, ignore_index=True)
    combined_results = combined_results.sort_values('Total')

    # Include all rows tied with the Nth-best score
    if len(combined_results) >= top_n:
        nth_score = combined_results.iloc[top_n - 1]['Total']
        return combined_results[combined_results['Total'] <= nth_score]
    return combined_results


def get_personal_best_eclectics(data: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Gets each player's best eclectic score(s) for a dimension, including ties.

    Args:
        data: Hole-by-hole score data.
        dimension: Dimension to group eclectics by ('TEGNum' or 'Course').

    Returns:
        DataFrame of each player's best eclectic(s) with a 'Player' column,
        sorted by Total then Player.
    """
    all_results = []
    players = sorted(data['Player'].unique())

    for player in players:
        player_data = data[data['Player'] == player]
        if player_data.empty:
            continue

        eclectics, _actual_dimension = calculate_eclectic_by_dimension(player_data, dimension)
        if eclectics.empty:
            continue

        best_score = eclectics['Total'].min()
        best_eclectics = eclectics[eclectics['Total'] == best_score].copy()
        best_eclectics['Player'] = player
        all_results.append(best_eclectics)

    if not all_results:
        return pd.DataFrame()

    return pd.concat(all_results, ignore_index=True).sort_values(['Total', 'Player'])


def format_eclectic_records_table(df: pd.DataFrame) -> pd.DataFrame:
    """Formats an eclectic-records table for display (summary columns only).

    Keeps Player, the dimension column (TEG/Course), Total and Rounds — no
    hole-by-hole detail — and coerces Total/Rounds to ints.

    Args:
        df: Eclectic scores DataFrame (output of the records helpers above).

    Returns:
        A formatted DataFrame ready for display.
    """
    if df.empty:
        return pd.DataFrame()

    # The dimension column is the only non-int column that isn't Player/Total/Rounds
    dimension_col = [
        col for col in df.columns
        if col not in ['Player', 'Total', 'Rounds'] and not isinstance(col, int)
    ][0]

    display_cols = ['Player', dimension_col, 'Total', 'Rounds']
    formatted_df = df[display_cols].copy()

    for col in ['Total', 'Rounds']:
        if col in formatted_df.columns:
            formatted_df[col] = formatted_df[col].apply(lambda x: int(x) if pd.notna(x) else '-')

    return formatted_df


def format_eclectic_table(eclectic_df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Formats the eclectic table for display.

    Converts hole scores to integers, ensures proper column ordering.
    """
    if eclectic_df.empty:
        return pd.DataFrame()

    display_df = eclectic_df.copy()

    hole_cols = [col for col in display_df.columns if isinstance(col, int)]
    for col in hole_cols + ['Total']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: int(x) if pd.notna(x) else '-')

    if 'Rounds' in display_df.columns:
        display_df['Rounds'] = display_df['Rounds'].astype(int)

    ordered_cols = [dimension] + ['Total'] + ['Rounds'] + hole_cols
    display_df = display_df[[c for c in ordered_cols if c in display_df.columns]]

    return display_df
