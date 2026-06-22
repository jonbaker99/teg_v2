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


@lru_cache(maxsize=1)
def cached_bestball_data():
    """Round-level bestball/worstball totals (data/bestball.parquet).

    Maintained by pipeline.update_bestball_cache on every add/delete, so the
    site can rank a round's totals without recomputing the full-history
    groupby('TRH').apply(...) on every page load.
    """
    from teg_analysis.constants import BESTBALL_PARQUET
    from teg_analysis.io.file_operations import read_file
    return read_file(BESTBALL_PARQUET)


def bestball_worstball_totals(all_data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (bestball_totals, worstball_totals): per-round team-format scores.

    Sourced from the maintained bestball cache (data/bestball.parquet,
    regenerated on every add/delete) to avoid recomputing the full-history
    groupby('TRH').apply(...) on every page load. Falls back to live
    computation if the cache is missing, empty, or malformed, so pages never
    break. A round's bestball/worstball total is independent of which other
    TEGs are present, so callers can safely filter the result by TEGNum.
    """
    from teg_analysis.analysis.bestball import (
        prepare_bestball_data,
        calculate_bestball_scores,
        calculate_worstball_scores,
    )
    try:
        cache = cached_bestball_data()
        if cache is not None and not cache.empty and 'Format' in cache.columns:
            bb = cache[cache['Format'] == 'Bestball']
            wb = cache[cache['Format'] == 'Worstball']
            if not bb.empty and not wb.empty:
                return bb, wb
        logger.warning("Bestball cache present but unusable; recomputing live")
    except Exception:
        logger.warning("Bestball cache unavailable; recomputing live", exc_info=True)

    prepared = prepare_bestball_data(all_data)
    return calculate_bestball_scores(prepared), calculate_worstball_scores(prepared)


def clear_all_data_caches() -> None:
    """Clear every in-process data cache.

    Call after a data update so the site re-reads the freshly written files
    (teg_analysis has no internal caching, so these wrappers are the only ones).
    """
    for fn in (
        cached_load_all_data,
        cached_round_data,
        cached_complete_teg_data,
        cached_9_data,
        cached_ranked_teg_data,
        cached_ranked_round_data,
        cached_ranked_frontback_data,
        cached_bestball_data,
    ):
        fn.cache_clear()


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
