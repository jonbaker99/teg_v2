"""Handicap calculation and TEG-status helpers.

Ported from streamlit/utils.py (no Streamlit dependencies). Provides the
weighted handicap calculation (``get_hc``), the current/draft handicap table
(``get_current_handicaps_formatted``) and the fast in-progress TEG status
check (``get_next_teg_and_check_if_in_progress_fast``).
"""

import logging

import pandas as pd

from teg_analysis.constants import HANDICAPS_CSV
from teg_analysis.io.file_operations import read_file
from teg_analysis.core.data_loader import (
    load_all_data,
    get_number_of_completed_rounds_by_teg,
    get_player_name,
)
from teg_analysis.analysis.aggregation import (
    get_teg_data_inc_in_progress,
    get_complete_teg_data,
)
from teg_analysis.analysis.pipeline import load_and_prepare_handicap_data

logger = logging.getLogger(__name__)


def get_hc(TEG_needed: int | None = None) -> pd.DataFrame:
    """Calculate weighted handicaps for a given TEG.

    Uses a 0.75/0.25 weighting of the adjusted gross from the previous two
    TEGs. Defaults to the next TEG after the highest available TEGNum.

    Returns:
        DataFrame with columns ['Pl', 'hc_raw', 'hc'].
    """
    hc = load_and_prepare_handicap_data(HANDICAPS_CSV)
    hc['TEGNum'] = hc["TEG"].str[-2:].str.strip().astype(int)

    all_data = load_all_data(exclude_incomplete_tegs=False)
    teg_data = get_teg_data_inc_in_progress()
    num_rounds = get_number_of_completed_rounds_by_teg(all_data)

    if TEG_needed is None:
        TEG_needed = teg_data["TEGNum"].max() + 1

    TEG_1 = TEG_needed - 1
    TEG_2 = TEG_needed - 2
    tegnums = [TEG_1, TEG_2]

    hc_x = hc[hc['TEGNum'].isin(tegnums)]

    stab_x = teg_data.loc[teg_data['TEGNum'].isin(tegnums), ['Pl', 'Stableford', 'TEGNum']].copy()
    stab_x = stab_x.merge(num_rounds[['TEGNum', 'num_rounds']], on="TEGNum", how="left")
    stab_x['ave_stab'] = stab_x['Stableford'] / stab_x['num_rounds']

    hc_merged = hc_x.merge(stab_x, on=['Pl', 'TEGNum'], how='left')
    hc_merged['ave_stab'] = pd.to_numeric(hc_merged['ave_stab'], errors="coerce").fillna(36)
    hc_merged['AdjGross'] = 36 - hc_merged['ave_stab'] + hc_merged['HC']

    pivoted = hc_merged.pivot(index="Pl", columns="TEGNum", values="AdjGross")
    result = (0.75 * pivoted[TEG_1] + 0.25 * pivoted[TEG_2]).reset_index(name="hc_raw")
    result['hc'] = result['hc_raw'].round(0).astype(int)
    return result


def get_current_handicaps_formatted(last_completed_teg: int, next_teg: int):
    """Build the current (or draft) handicap table for ``next_teg``.

    Returns:
        (DataFrame, bool): a table with columns ['Handicap', 'TEG {n}',
        'Change'] and a flag indicating whether the handicaps had to be
        calculated (i.e. they are a draft not yet saved to the CSV).
    """
    hc_data = load_and_prepare_handicap_data(HANDICAPS_CSV)

    last_teg_str = f'TEG {last_completed_teg}'
    next_teg_str = f'TEG {next_teg}'

    current_hc = hc_data[hc_data['TEG'] == next_teg_str]
    previous_hc = hc_data[hc_data['TEG'] == last_teg_str]

    handicaps_were_calculated = current_hc.empty

    if current_hc.empty:
        calculated_handicaps = get_hc(next_teg)
        calculated_rows = [
            {'TEG': next_teg_str, 'Pl': row['Pl'], 'HC': row['hc']}
            for _, row in calculated_handicaps.iterrows()
        ]
        hc_data = pd.concat([hc_data, pd.DataFrame(calculated_rows)], ignore_index=True)
        current_hc = hc_data[hc_data['TEG'] == next_teg_str]

    merged = current_hc.merge(previous_hc[['Pl', 'HC']], on='Pl', how='left', suffixes=('_current', '_previous'))
    merged['HC_previous'] = merged['HC_previous'].fillna(merged['HC_current'])
    merged['Change'] = merged['HC_current'] - merged['HC_previous']
    merged['FullName'] = merged['Pl'].apply(get_player_name)

    result = pd.DataFrame({
        'Handicap': merged['FullName'].tolist(),
        next_teg_str: merged['HC_current'].astype(int).tolist(),
        'Change': merged['Change'].astype(int).tolist(),
    })
    return result, handicaps_were_calculated


def get_next_teg_and_check_if_in_progress():
    """Slow TEG-status check from the full datasets.

    Returns:
        (last_completed_teg, next_teg, in_progress)
    """
    teg_data_inc_progress = get_teg_data_inc_in_progress()
    teg_data_completed = get_complete_teg_data()

    last_completed_teg = max(teg_data_completed['TEGNum'])
    next_teg = last_completed_teg + 1
    in_progress = (teg_data_inc_progress['TEGNum'] == next_teg).any()
    return last_completed_teg, next_teg, in_progress


def get_next_teg_and_check_if_in_progress_fast():
    """Fast TEG-status check using the completed/in-progress status files.

    Returns:
        (last_completed_teg, next_teg, in_progress)
    """
    try:
        completed_tegs = read_file('data/completed_tegs.csv')
        in_progress_tegs = read_file('data/in_progress_tegs.csv')

        last_completed_teg = completed_tegs['TEGNum'].max() if not completed_tegs.empty else 0
        next_teg = last_completed_teg + 1
        in_progress = (in_progress_tegs['TEGNum'] == next_teg).any() if not in_progress_tegs.empty else False
        return last_completed_teg, next_teg, in_progress
    except Exception as e:  # pragma: no cover - fallback path
        logger.warning(f"Status files not available, falling back to slow method: {e}")
        return get_next_teg_and_check_if_in_progress()
