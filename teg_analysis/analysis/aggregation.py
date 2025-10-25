"""Aggregation and data grouping functions.

This module provides data aggregation functions for the TEG analysis system,
including TEG-level, round-level, and 9-hole aggregation, plus winner calculations.
"""

import logging
import pandas as pd
from typing import List

logger = logging.getLogger(__name__)


def _get_constants():
    """Get constants from utils.py to avoid circular imports."""
    from streamlit.utils import TEG_ROUNDS, TEGNUM_ROUNDS, TEG_OVERRIDES
    return {
        'TEG_ROUNDS': TEG_ROUNDS,
        'TEGNUM_ROUNDS': TEGNUM_ROUNDS,
        'TEG_OVERRIDES': TEG_OVERRIDES,
    }


# === LOOKUP FUNCTIONS ===

def get_teg_rounds(TEG: str) -> int:
    """Return the number of rounds for a given TEG.

    If the TEG is not found in the dictionary, return 4 as the default value.

    Parameters:
        TEG (str): The TEG identifier (e.g., 'TEG 1', 'TEG 2', etc.)

    Returns:
        int: The total number of rounds for the given TEG, defaulting to 4 if not found.
    """
    consts = _get_constants()
    return consts['TEG_ROUNDS'].get(TEG, 4)


def get_tegnum_rounds(TEGNum: int) -> int:
    """Return the number of rounds for a given TEG by number.

    If the TEG is not found in the dictionary, return 4 as the default value.

    Parameters:
        TEGNum (int): The TEG number (e.g., 1, 2, 3, etc.)

    Returns:
        int: The total number of rounds for the given TEG, defaulting to 4 if not found.
    """
    consts = _get_constants()
    return consts['TEGNUM_ROUNDS'].get(TEGNum, 4)


# === WINNER CALCULATIONS ===

def get_teg_winners(df: pd.DataFrame) -> pd.DataFrame:
    """Generate TEG winners, best net, gross, and worst net by TEG.

    Parameters:
        df (pd.DataFrame): DataFrame containing the golf data.

    Returns:
        pd.DataFrame: DataFrame summarizing TEG winners.
    """
    # Import scoring function here to avoid circular dependency
    from .scoring import get_net_competition_measure

    consts = _get_constants()
    TEG_OVERRIDES = consts['TEG_OVERRIDES']

    logger.info("Calculating TEG winners.")

    # Group by 'TEGNum' and 'Player', and calculate the sum for each player in each TEG
    grouped = df.groupby(['TEGNum', 'Player']).agg({
        'GrossVP': 'sum',
        'NetVP': 'sum',
        'Stableford': 'sum'
    }).reset_index()

    results = []

    # Get unique TEG numbers
    for teg_num in df['TEGNum'].unique():
        # Filter data for the current TEG
        teg_data = grouped[grouped['TEGNum'] == teg_num]

        # Determine which measure to use for net competition based on TEG number
        net_measure = get_net_competition_measure(teg_num)

        # Identify the best gross, best net, and worst net players
        best_gross_player = teg_data.loc[teg_data['GrossVP'].idxmin(), 'Player']

        if net_measure == 'NetVP':
            # For TEG 1-5: Lower NetVP is better (closer to or under par)
            best_net_player = teg_data.loc[teg_data['NetVP'].idxmin(), 'Player']
            worst_net_player = teg_data.loc[teg_data['NetVP'].idxmax(), 'Player']
        else:
            # For TEG 6+: Higher Stableford is better
            best_net_player = teg_data.loc[teg_data['Stableford'].idxmax(), 'Player']
            worst_net_player = teg_data.loc[teg_data['Stableford'].idxmin(), 'Player']

        # Apply manual overrides if any
        teg_label = f"TEG {teg_num}"
        overrides = TEG_OVERRIDES.get(teg_label, {})
        best_gross_player = overrides.get('Best Gross', best_gross_player)
        best_net_player = overrides.get('Best Net', best_net_player)
        worst_net_player = overrides.get('Worst Net', worst_net_player)

        # Append the results
        results.append({
            'TEGNum': teg_num,
            'TEG': teg_label,
            'Best Gross': best_gross_player,
            'Best Net': best_net_player,
            'Worst Net': worst_net_player
        })

    # Convert results to a DataFrame
    result_df = pd.DataFrame(results).sort_values(by='TEGNum')

    # Merge with year data from df
    teg_years = df[['TEGNum', 'Year']].drop_duplicates()
    result_df = result_df.merge(teg_years, on='TEGNum', how='left')

    # Rename columns
    result_df.rename(columns={
        'Best Net': 'TEG Trophy',
        'Best Gross': 'Green Jacket',
        'Worst Net': 'HMM Wooden Spoon',
        'Year': 'Year'
    }, inplace=True)

    # Select and order columns
    result_df = result_df[['TEG', 'Year', 'TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon']]

    logger.info("TEG winners calculated.")
    return result_df


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
        aggregation_level (str): The level of aggregation ('Player', 'TEG', 'Round', 'FrontBack', 'Hole').
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
