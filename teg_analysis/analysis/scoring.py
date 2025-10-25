"""Scoring calculations and utilities.

This module provides scoring-related functions for the TEG analysis system,
including scoring calculations and various scoring utilities.
"""

import logging

logger = logging.getLogger(__name__)


def format_vs_par(value) -> str:
    """Formats a value as a vs-par score (e.g., '-5', 'E', '+3').

    Args:
        value: The numerical value to format.

    Returns:
        str: The formatted vs-par score.
    """
    if value is None or (isinstance(value, float) and value != value):  # Check for NaN
        return 'N/A'

    value = int(value)

    if value > 0:
        return f'+{value}'
    elif value == 0:
        return 'E'
    else:
        return str(value)


def get_net_competition_measure(teg_num: int) -> str:
    """Gets the net competition measure for a specific TEG.

    For TEGs 1-5, net competition is based on total net vs par.
    For TEG 6 onwards, net competition is based on stableford points.

    Args:
        teg_num (int): The TEG number.

    Returns:
        str: Either 'NetVP' (for TEGs 1-5) or 'Stableford' (for TEG 6+).
    """
    if teg_num <= 5:
        return 'NetVP'
    else:
        return 'Stableford'


# Additional scoring functions would be migrated from helpers/scoring_data_processing.py
# and added here in subsequent phases
