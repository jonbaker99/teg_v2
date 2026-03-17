"""Data loading and leaderboard logic for the webapp."""

import logging
from functools import lru_cache
from typing import Any

import pandas as pd

from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import (
    get_round_data,
    get_complete_teg_data,
    get_9_data,
    get_last_completed_teg_fast,
    get_current_in_progress_teg_fast,
)
from teg_analysis.analysis.scoring import get_net_competition_measure
from teg_analysis.analysis.rankings import (
    get_ranked_teg_data,
    get_ranked_round_data,
    get_ranked_frontback_data,
)

logger = logging.getLogger(__name__)

PLAYER_COLUMN = 'Player'


# --- Cached data accessors ---------------------------------------------------

@lru_cache(maxsize=1)
def cached_load_all_data():
    return load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)


@lru_cache(maxsize=1)
def cached_round_data():
    return get_round_data(ex_50=True, ex_incomplete=False)


@lru_cache(maxsize=1)
def cached_complete_teg_data():
    return get_complete_teg_data()


@lru_cache(maxsize=1)
def cached_9_data():
    return get_9_data()


@lru_cache(maxsize=1)
def cached_ranked_teg_data():
    return get_ranked_teg_data()


@lru_cache(maxsize=1)
def cached_ranked_round_data():
    return get_ranked_round_data()


@lru_cache(maxsize=1)
def cached_ranked_frontback_data():
    return get_ranked_frontback_data()


# --- Leaderboard logic (from streamlit/leaderboard_utils.py) ------------------

def create_leaderboard(leaderboard_df: pd.DataFrame, value_column: str, ascending: bool = True) -> pd.DataFrame:
    """Creates a leaderboard from the given DataFrame."""
    pivot_df = leaderboard_df.pivot_table(
        index=PLAYER_COLUMN,
        columns='Round',
        values=value_column,
        aggfunc='sum',
        fill_value=0
    ).assign(Total=lambda x: x.sum(axis=1)).sort_values('Total', ascending=ascending)

    pivot_df.columns = [f'R{col}' if isinstance(col, int) else col for col in pivot_df.columns]
    pivot_df = pivot_df.reset_index()
    pivot_df['Rank'] = pivot_df['Total'].rank(method='min', ascending=ascending).astype(int)

    # Convert Rank to string, then add '=' suffix for ties
    pivot_df['Rank'] = pivot_df['Rank'].astype(str)
    duplicated_scores = pivot_df['Total'].duplicated(keep=False)
    if duplicated_scores.any():
        pivot_df.loc[duplicated_scores, 'Rank'] = pivot_df.loc[duplicated_scores, 'Rank'] + '='

    columns = ['Rank', PLAYER_COLUMN] + [col for col in pivot_df.columns if col not in ['Rank', PLAYER_COLUMN]]
    return pivot_df[columns]


def format_value(value: Any, value_type: str) -> str:
    """Formats values based on their type."""
    try:
        num = float(value)
        if value_type in ['GrossVP', 'NetVP']:
            if num > 0:
                return f"+{int(num)}" if num.is_integer() else f"+{num}"
            elif num < 0:
                return f"{int(num)}" if num.is_integer() else f"{num}"
            else:
                return "="
        elif value_type == 'Stableford':
            return f"{int(round(num))}"
        else:
            return str(value)
    except (ValueError, TypeError):
        return str(value)


# --- TEG helpers --------------------------------------------------------------

def get_default_teg_num() -> int:
    """Get the TEG number to show by default (in-progress or last completed)."""
    in_progress_num, _ = get_current_in_progress_teg_fast()
    if in_progress_num:
        return in_progress_num
    completed_num, _ = get_last_completed_teg_fast()
    return completed_num or 18  # fallback


def get_available_teg_numbers() -> list[int]:
    """Get sorted list of available TEG numbers from round data."""
    df = cached_round_data()
    return sorted(df['TEGNum'].unique().tolist())


def get_rounds_for_teg(teg_num: int) -> list[int]:
    """Get sorted list of round numbers for a given TEG."""
    df = cached_round_data()
    teg_df = df[df['TEGNum'] == teg_num]
    return sorted(teg_df['Round'].unique().tolist())


def get_filtered_teg_data():
    """Get complete TEG data excluding TEG 2 (only 3 rounds)."""
    df = cached_complete_teg_data()
    return df[df['TEGNum'] != 2]
