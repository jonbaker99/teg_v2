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

# Fallback TEG number when no in-progress or completed TEG can be determined
# (e.g. an empty/corrupt round_data). Kept as a named constant rather than a
# bare literal since it's just "the latest TEG at time of writing", not a
# rule with any domain meaning.
FALLBACK_TEG_NUM = 18

# Route modules can hold their own lru_cache'd data accessors (e.g.
# player.py's winners cache). deps must not import routes (that would be a
# circular import), so instead a route registers its cache_clear callable
# here at import time and clear_all_data_caches() fans out to all of them.
_extra_cache_clearers: list = []


def register_cache_clearer(clear_fn) -> None:
    """Register a callable to be invoked by clear_all_data_caches().

    Idempotent per callable, so re-importing a module doesn't stack duplicate
    clearers.
    """
    if clear_fn not in _extra_cache_clearers:
        _extra_cache_clearers.append(clear_fn)


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


@lru_cache(maxsize=1)
def cached_winners():
    """TEG winners table (Trophy / Green Jacket / Wooden Spoon per TEG).

    Recomputed once per process from cached_load_all_data() rather than per
    request -- used by /honours, /player (trophy cabinet) and the latest-teg
    result tabs, which previously each sourced this independently.
    """
    from teg_analysis.analysis.history import get_teg_winners
    return get_teg_winners(cached_load_all_data())


@lru_cache(maxsize=1)
def cached_streaks_data():
    """The maintained streaks cache (data/streaks.parquet), read once per process."""
    from teg_analysis.constants import STREAKS_PARQUET
    from teg_analysis.io.file_operations import read_file
    return read_file(STREAKS_PARQUET)


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

    Call after a data update so the site re-reads the freshly written files.
    These wrappers plus teg_analysis's one internal cache (the players.csv
    code->name dict in ``core.players``) are the complete set.
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
        cached_winners,
        cached_streaks_data,
    ):
        fn.cache_clear()

    from teg_analysis.core.players import clear_player_cache
    clear_player_cache()

    # Route-level caches that registered themselves (see register_cache_clearer).
    for clear_fn in _extra_cache_clearers:
        clear_fn()


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

def parse_teg_label(label) -> int:
    """Parse a 'TEG N' label (or a bare number) into its integer N."""
    if isinstance(label, int):
        return label
    text = str(label).strip()
    return int(text.replace('TEG', '').strip()) if text.upper().startswith('TEG') else int(text)


def get_default_teg_num() -> int:
    """Get the TEG number to show by default (in-progress or last completed)."""
    in_progress_num, _ = get_current_in_progress_teg_fast()
    if in_progress_num:
        return in_progress_num
    completed_num, _ = get_last_completed_teg_fast()
    return completed_num or FALLBACK_TEG_NUM


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


# --- Contents / tournament-state helpers (I5) --------------------------------

def _format_date_dmy(date_str) -> str:
    """Parse DD/MM/YYYY and return '17 March 2026' style. Mirrors
    webapp/routes/scorecard.py's `_format_date`; kept local rather than
    imported since deps.py must not depend on route modules."""
    from datetime import datetime
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
        return dt.strftime("%-d %B %Y")
    except (ValueError, TypeError):
        return str(date_str)


def _leader_rows(teg_rd: pd.DataFrame, value_col: str, ascending: bool) -> dict:
    """Rank one competition and return every player tied for first and every
    player tied for last -- TEG has no countback, so a tie is never collapsed
    to one name ([[feedback_no_countback]])."""
    lb = create_leaderboard(teg_rd, value_col, ascending=ascending)
    if lb.empty:
        return {"leaders": [], "leader_total": "", "last": [], "last_total": ""}
    leader_total = lb.iloc[0]['Total']
    last_total = lb.iloc[-1]['Total']
    return {
        "leaders": lb.loc[lb['Total'] == leader_total, PLAYER_COLUMN].tolist(),
        "leader_total": format_value(leader_total, value_col),
        "last": lb.loc[lb['Total'] == last_total, PLAYER_COLUMN].tolist(),
        "last_total": format_value(last_total, value_col),
    }


def get_contents_state1_leaders(teg_num: int) -> dict:
    """State 1 (in-progress) leader rows: current Trophy (net) / Jacket
    (gross) leaders and the net wooden spoon, from live round data.

    The only Contents state-1 helper that reads `cached_round_data()` --
    callers should check cache warmth first (see `get_tournament_state`'s
    cold-load fallback, I4 R10) rather than call this unconditionally.
    """
    rd = cached_round_data()
    teg_rd = rd[rd['TEGNum'] == teg_num]
    net_measure = get_net_competition_measure(teg_num)
    net = _leader_rows(teg_rd, net_measure, ascending=(net_measure == 'NetVP'))
    gross = _leader_rows(teg_rd, 'GrossVP', ascending=True)
    return {
        "net_leaders": net["leaders"], "net_leader_total": net["leader_total"],
        "net_last": net["last"], "net_last_total": net["last_total"],
        "gross_leaders": gross["leaders"], "gross_leader_total": gross["leader_total"],
        "net_unit": "pts" if net_measure == "Stableford" else "vs par",
    }


def get_tournament_state() -> dict:
    """Single source of truth for Contents' three states (in progress /
    latest complete / no usable data), chosen from the two small status
    CSVs -- never from `get_default_teg_num()`, which silently falls back
    to `FALLBACK_TEG_NUM` on unreadable data and would misreport State 3
    as a real TEG.
    """
    from teg_analysis.io.file_operations import read_file
    from teg_analysis.core.metadata import get_teg_metadata
    from teg_analysis.core.data_loader import get_tegnum_rounds
    from teg_analysis.analysis.history import get_future_tegs
    from teg_analysis.reporting.newspaper_edition import has_edition

    in_teg, rounds_played = get_current_in_progress_teg_fast()
    if in_teg:
        meta = get_teg_metadata(in_teg)
        round_meta = get_teg_metadata(in_teg, rounds_played) if rounds_played else {}
        year = meta.get('Year')
        state = {
            "state": "in_progress",
            "teg_num": in_teg,
            "teg_label": f"TEG {in_teg}",
            "area": meta.get('Area', ''),
            "year": str(int(year)) if year and str(year).strip() else '',
            "rounds_played": rounds_played,
            "rounds_expected": get_tegnum_rounds(in_teg),
            "last_round_date": _format_date_dmy(round_meta.get('Date', '')),
        }
        # Cold-load budget (I4 R10): State 1 is the only state that pays for
        # cached_round_data(). If this request would be the first (cold)
        # miss, render the headline/context/actions immediately and defer
        # leader rows to an HTMX partial (GET /contents/leaders) reusing
        # I2's standard loading/error pattern, rather than blocking the page
        # on a cold parquet load.
        cold = cached_round_data.cache_info().currsize == 0
        state["leaders_deferred"] = cold
        if not cold:
            state.update(get_contents_state1_leaders(in_teg))
        return state

    last_teg, _rounds = get_last_completed_teg_fast()
    if last_teg:
        meta = get_teg_metadata(last_teg)
        rounds_expected = get_tegnum_rounds(last_teg)
        round_meta = get_teg_metadata(last_teg, rounds_expected)
        year = meta.get('Year')

        winners = {}
        try:
            winners_df = read_file('data/teg_winners.csv')
            row = winners_df[winners_df['TEG'] == f"TEG {last_teg}"]
            if not row.empty:
                winners = row.iloc[0].to_dict()
        except Exception:
            winners = {}

        next_teg = None
        try:
            future = get_future_tegs()
            if not future.empty:
                next_row = future.iloc[0]
                next_teg = {
                    "label": next_row['TEG'],
                    "year": int(next_row['Year']),
                    "area": next_row['Area'],
                }
        except Exception:
            next_teg = None

        return {
            "state": "complete",
            "teg_num": last_teg,
            "teg_label": f"TEG {last_teg}",
            "area": meta.get('Area', ''),
            "year": str(int(year)) if year and str(year).strip() else '',
            "last_round_date": _format_date_dmy(round_meta.get('Date', '')),
            "net_measure": get_net_competition_measure(last_teg),
            "trophy": winners.get('TEG Trophy', ''),
            "jacket": winners.get('Green Jacket', ''),
            "spoon": winners.get('HMM Wooden Spoon', ''),
            "has_report": has_edition(last_teg),
            "next_teg": next_teg,
        }

    return {"state": "no_data"}
