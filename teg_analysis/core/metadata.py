"""Metadata and reference data functions.

This module provides functions for loading and accessing TEG metadata,
course information, and scorecard data.
"""

import pandas as pd
from typing import Optional, Dict
from ..io.file_operations import read_file

# File path constants
ROUND_INFO_CSV = 'data/round_info.csv'


def get_teg_metadata(teg_num: int, round_num: Optional[int] = None) -> Dict:
    """Get TEG metadata from round_info.csv.

    Args:
        teg_num: TEG number
        round_num: Optional round number for round-specific data

    Returns:
        dict: Metadata including area, course, date, year

    Raises:
        FileNotFoundError: If round_info.csv not found

    Examples:
        >>> meta = get_teg_metadata(18)
        >>> meta = get_teg_metadata(18, 2)  # Specific round
    """
    try:
        round_info = read_file(ROUND_INFO_CSV)

        if round_num:
            # Get specific round data
            round_data = round_info[(round_info['TEGNum'] == teg_num) &
                                  (round_info['Round'] == round_num)]
            if round_data.empty:
                return {}
            return round_data.iloc[0].to_dict()
        else:
            # Get TEG-level data (from first round)
            teg_data = round_info[round_info['TEGNum'] == teg_num]
            if teg_data.empty:
                return {}
            return teg_data.iloc[0].to_dict()
    except FileNotFoundError:
        raise
    except Exception as e:
        # Log warning but return empty dict for graceful degradation
        import logging
        logging.warning(f"Error loading TEG metadata for TEG {teg_num}: {e}")
        return {}


def load_course_info() -> pd.DataFrame:
    """Load unique course/area combinations from round_info.csv.

    Returns:
        pd.DataFrame: Course information with columns ['Course', 'Area']

    Raises:
        FileNotFoundError: If round_info.csv not found

    Examples:
        >>> courses = load_course_info()
        >>> print(courses[['Course', 'Area']])
    """
    round_info = read_file(ROUND_INFO_CSV)
    course_info = round_info[['Course', 'Area']].drop_duplicates()
    return course_info


def get_scorecard_data(
    teg_num: Optional[int] = None,
    round_num: Optional[int] = None,
    player_code: Optional[str] = None
) -> pd.DataFrame:
    """Get golf data for scorecard generation with optional filtering.

    This function provides flexible filtering for scorecard data, allowing
    you to get data for a specific player, round, tournament, or any combination.

    Args:
        teg_num: Optional TEG number filter
        round_num: Optional round number filter
        player_code: Optional player code filter (e.g., 'JB')

    Returns:
        pd.DataFrame: Filtered and sorted data

    Examples:
        >>> # One player's round
        >>> data = get_scorecard_data(18, 2, 'JB')

        >>> # All players in round 2 of TEG 18
        >>> data = get_scorecard_data(18, 2)

        >>> # One player's tournament
        >>> data = get_scorecard_data(18, player_code='JB')

        >>> # All data for TEG 18
        >>> data = get_scorecard_data(18)
    """
    # Import here to avoid circular dependency
    from .data_loader import load_all_data

    all_data = load_all_data(exclude_incomplete=False)

    # Apply filters if provided
    if teg_num is not None:
        all_data = all_data[all_data['TEGNum'] == teg_num]

    if round_num is not None:
        all_data = all_data[all_data['Round'] == round_num]

    if player_code is not None:
        all_data = all_data[all_data['Pl'] == player_code]

    # Sort appropriately based on what filters were applied
    if player_code is not None and round_num is not None:
        # Single player, single round - sort by hole
        sort_cols = ['Hole']
    elif round_num is not None:
        # Single round, multiple players - sort by player then hole
        sort_cols = ['Pl', 'Hole']
    else:
        # Multiple rounds - sort by round then hole
        sort_cols = ['Round', 'Hole']
        if player_code is None:
            # Multiple players too - add player to sort
            sort_cols = ['Pl'] + sort_cols

    return all_data.sort_values(sort_cols)
