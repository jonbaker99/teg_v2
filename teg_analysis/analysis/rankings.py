"""Ranking calculations and utilities.

This module provides ranking-related functions for the TEG analysis system,
including rank calculations, best/worst performance identification, and
ordinal number formatting.
"""


import logging
import pandas as pd

logger = logging.getLogger(__name__)


def add_ranks(df, fields_to_rank=None, rank_ascending=None):
    """Adds ranking columns to the DataFrame for optionally specified fields or all scoring fields.

    Adds rankings both within each player's rounds and across all rounds.
    The ranking can be done in ascending or descending order.
    Ranking will be applied at lowest level of aggregation present in the data.

    Parameters:
    -----------
    df : pandas.DataFrame
        The input DataFrame containing the data.
        It must include at least a 'Player' column and
        the fields to be ranked (e.g., 'Sc', 'GrossVP', 'NetVP', 'Stableford').

    fields_to_rank : list or str, optional
        The fields to rank. This can be a list of field names (e.g., ['Sc', 'GrossVP']) or a single
        field name as a string (e.g., 'Sc'). If not provided, the default is ['Sc', 'GrossVP', 'NetVP',
        'Stableford'].

    rank_ascending : bool, optional
        The order of ranking. If not provided, the function defaults to:
        - True for all fields except 'Stableford', where it defaults to False.
        If provided, this will apply the same order for all fields.

    Returns:
    --------
    pandas.DataFrame
        A DataFrame with additional columns for the ranking of each specified field:
        - 'Rank_within_player_<field>': The rank of the field within each player's rounds.
        - 'Rank_within_all_<field>': The rank of the field across all rounds.

    Example:
    --------
    >>> add_ranks(df, fields_to_rank=['Sc', 'Stableford'], rank_ascending=True)
    This will add rank columns for 'Sc' and 'Stableford', ranked in ascending order.

    >>> add_ranks(df)
    This will add rank columns for the default fields ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    with default ascending/descending order.
    """

    input_rank_ascending = rank_ascending

    # If fields_to_rank is not provided, use default list of fields
    if fields_to_rank is None:
        fields_to_rank = ['Sc', 'GrossVP', 'NetVP', 'Stableford']

    # Check if fields_to_rank is a string, convert to list if necessary
    if isinstance(fields_to_rank, str):
        fields_to_rank = [fields_to_rank]

    for field in fields_to_rank:
        # Determine default value for rank_ascending for each field
        if input_rank_ascending is None:
            rank_ascending = False if 'Stableford' in field else True

        # Rank within each Player's scores
        df[f'Rank_within_player_{field}'] = df.groupby('Player')[field].rank(method='min', ascending=rank_ascending)

        # Rank across all Players
        df[f'Rank_within_all_{field}'] = df[field].rank(method='min', ascending=rank_ascending)

    return df


def get_ranked_teg_data():
    """Gets complete TEG-level data with rankings added.

    Returns:
        pd.DataFrame: TEG-level aggregated data with ranking columns.
    """
    # Import here to avoid circular dependency
    from .aggregation import get_complete_teg_data

    df = get_complete_teg_data()
    ranked_data = add_ranks(df)
    return ranked_data


def get_ranked_round_data():
    """Gets round-level data with rankings added.

    Returns:
        pd.DataFrame: Round-level aggregated data with ranking columns.
    """
    # Import here to avoid circular dependency
    from .aggregation import get_round_data

    df = get_round_data()
    ranked_data = add_ranks(df)
    return ranked_data


def get_ranked_frontback_data():
    """Gets front/back 9 data with rankings added.

    Returns:
        pd.DataFrame: 9-hole aggregated data with ranking columns.
    """
    # Import here to avoid circular dependency
    from .aggregation import get_9_data

    df = get_9_data()
    ranked_data = add_ranks(df)
    return ranked_data


def get_best(df, measure_to_use, player_level=False, top_n=1):
    """Gets the best performances based on the specified measure.

    Args:
        df (pd.DataFrame): DataFrame with performance data.
        measure_to_use (str): Measure to evaluate ('Sc', 'GrossVP', 'NetVP', 'Stableford').
        player_level (bool): If True, get best per player. If False, get best overall.
        top_n (int): Number of top performances to return.

    Returns:
        pd.DataFrame: Filtered DataFrame with top performances.
    """
    valid_measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    if measure_to_use not in valid_measures:
        error_message = f"Invalid measure: '{measure_to_use}'. Valid options are: {', '.join(valid_measures)}"
        raise ValueError(error_message)

    if player_level is None:
        player_level = False

    if top_n is None:
        top_n = 1

    measure_fn = 'Rank_within_' + ('player' if player_level else 'all') + f'_{measure_to_use}'

    return df[df[measure_fn] <= top_n]


def get_worst(df, measure_to_use, player_level=False, top_n=1):
    """Gets the worst performances based on the specified measure.

    Args:
        df (pd.DataFrame): DataFrame with performance data.
        measure_to_use (str): Measure to evaluate ('Sc', 'GrossVP', 'NetVP', 'Stableford').
        player_level (bool): If True, get worst per player. If False, get worst overall.
        top_n (int): Number of worst performances to return.

    Returns:
        pd.DataFrame: Filtered DataFrame with worst performances.
    """
    valid_measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    if measure_to_use not in valid_measures:
        error_message = f"Invalid measure: '{measure_to_use}'. Valid options are: {', '.join(valid_measures)}"
        raise ValueError(error_message)

    if player_level is None:
        player_level = False

    if top_n is None:
        top_n = 1

    if player_level == False:
        if measure_to_use == 'Stableford':
            df = df.nsmallest(top_n, measure_to_use)
        else:
            df = df.nlargest(top_n, measure_to_use)
    else:
        if measure_to_use == 'Stableford':
            df = df.groupby('Player', group_keys=False).apply(lambda x: x.nsmallest(top_n, measure_to_use))
        else:
            df = df.groupby('Player', group_keys=False).apply(lambda x: x.nlargest(top_n, measure_to_use))

    return df


def ordinal(n):
    """Converts a number to its ordinal representation.

    Args:
        n (int): The number to convert.

    Returns:
        str: The ordinal representation (e.g., 1st, 2nd, 3rd, 4th, etc.).
    """
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix


def safe_ordinal(n):
    """Safely converts a number to its ordinal representation, handling NaN and invalid values.

    Args:
        n: The number to convert (can be NaN or invalid).

    Returns:
        str or NaN: The ordinal representation, or NaN/string for invalid inputs.
    """
    if pd.isna(n):
        return n  # or return a specific string like 'N/A'
    try:
        return ordinal(int(n))
    except ValueError:
        return str(n)  # or return a specific string for invalid inputs


def convert_pivot_scores_to_ranks(pivot_df, measure):
    """Convert a pivot table of scores to tournament ranks for each column independently.

    Takes a pivot table with Players as rows, Events/TEGs as columns, and scores as values,
    and converts each column from scores to finishing positions (ranks).

    Args:
        pivot_df (pd.DataFrame): Pivot table with:
            - Index: Player names
            - Columns: Event identifiers (TEG numbers, TEG names, etc.)
            - Values: Scores (numeric)
        measure (str): Score type determining sort order:
            - 'Stableford': Higher score is better (ascending=False)
            - 'GrossVP', 'NetVP', 'Sc': Lower score is better (ascending=True)

    Returns:
        pd.DataFrame: Same structure as input but with ranks instead of scores
            - Ranks as strings: "1", "2", "3", etc.
            - Tied positions marked with "=": "1=", "2=", "3=", etc.
            - NaN preserved where player didn't participate

    Example:
        >>> # Create pivot: Players × TEGs with NetVP scores
        >>> pivot = agg_data.pivot_table(
        ...     index='Player',
        ...     columns='TEGNum',
        ...     values='NetVP',
        ...     aggfunc='min'
        ... )
        >>> # Convert to ranks
        >>> rankings = convert_pivot_scores_to_ranks(pivot, 'NetVP')
        >>> # Now shows "1", "2", "3=" instead of -15, -10, -5
    """
    ranked_df = pivot_df.copy()

    # Determine sort order based on measure
    # Stableford: higher is better (descending), others: lower is better (ascending)
    ascending = measure != 'Stableford'

    # Process each column (TEG/Event) independently
    for col in pivot_df.columns:
        col_data = pivot_df[col].dropna()

        if len(col_data) == 0:
            # No data in this column, skip
            continue

        # Rank the scores (method='min' for ties: same score gets same rank)
        ranks = col_data.rank(method='min', ascending=ascending)

        # Convert to integer then to string
        ranks = ranks.astype(int).astype(str)

        # Find tied values (same score)
        is_tie = col_data.duplicated(keep=False)

        # Mark ties with '=' suffix (e.g., "1=" instead of "1")
        if is_tie.any():
            ranks.loc[is_tie] = ranks.loc[is_tie] + '='

        # Write back to the ranked dataframe
        ranked_df.loc[ranks.index, col] = ranks

    return ranked_df


def calculate_average_rank_from_ranked_df(ranked_df: pd.DataFrame, player_col: str = None) -> pd.DataFrame:
    """Calculate average finishing position from a ranked DataFrame.

    Takes a ranking DataFrame (typically with players as rows and tournaments as columns,
    with rank values as cells like "1", "2=", "3", etc.) and calculates the average
    ranking for each player. Tied positions are converted to their numeric value by
    removing the "=" suffix. NaN values are ignored.

    Args:
        ranked_df: DataFrame with players as rows, tournaments as columns, ranks as values
        player_col: Name of the player column (used for detection). If not provided,
                   uses the index name or defaults to "Player".

    Returns:
        DataFrame with columns:
        - Player: Player name
        - TEGs Played: Number of tournaments played
        - Average Position: Average finishing position (sorted best to worst)
    """
    # Determine player column name
    if player_col is None:
        player_col = ranked_df.index.name if ranked_df.index.name else "Player"

    # Ensure index has the player column name for reset_index
    df_copy = ranked_df.copy()
    if player_col not in df_copy.columns:
        df_copy.index.name = player_col
        df_copy = df_copy.reset_index()

    # Get all rank columns (exclude player column)
    rank_columns = [col for col in df_copy.columns if col != player_col]

    summary_data = []

    for _, row in df_copy.iterrows():
        player_name = row[player_col]
        positions = row[rank_columns]

        # Get numeric positions (exclude NaN and remove '=' from ties)
        numeric_positions = []
        for pos in positions.dropna():
            clean_pos = str(pos).replace('=', '')
            if clean_pos.isdigit():
                numeric_positions.append(int(clean_pos))

        # Calculate average if player has played
        if numeric_positions:
            avg_position = sum(numeric_positions) / len(numeric_positions)
            tegs_played = len(numeric_positions)
        else:
            avg_position = None
            tegs_played = 0

        summary_data.append({
            'Player': player_name,
            'TEGs Played': tegs_played,
            'Average Position': avg_position
        })

    summary_df = pd.DataFrame(summary_data)

    # Sort by average position (best first), with non-players at bottom
    summary_df = summary_df.sort_values(
        ['TEGs Played', 'Average Position'],
        ascending=[False, True],
        na_position='last'
    )

    # Reset index to create a ranking column (1, 2, 3...)
    summary_df = summary_df.reset_index(drop=True)
    summary_df.insert(0, 'Rank', range(1, len(summary_df) + 1))

    # Format average position to 1 decimal place
    if 'Average Position' in summary_df.columns:
        summary_df['Average Position'] = summary_df['Average Position'].round(1)

    return summary_df
