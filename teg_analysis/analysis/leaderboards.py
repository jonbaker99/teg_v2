"""Leaderboard generation for TEG tournaments and individual rounds."""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def filter_data_by_teg(all_data: pd.DataFrame, selected_tegnum) -> pd.DataFrame:
    """Filter data by TEG number, or return all if 'All TEGs'."""
    if selected_tegnum != 'All TEGs':
        return all_data[all_data['TEGNum'] == int(selected_tegnum)]
    return all_data


def get_teg_leaderboard(df: pd.DataFrame, measure: str, teg_num: int = None) -> pd.DataFrame:
    """Tournament leaderboard with round-by-round scores and totals.

    Args:
        df: Round-level aggregated data.
        measure: 'Stableford', 'GrossVP', 'NetVP', or 'Sc'.
        teg_num: Optional TEG filter.

    Returns:
        DataFrame: Rank, Player, R1, R2, ..., Total.
    """
    data = df.copy()
    if teg_num is not None:
        data = data[data['TEGNum'] == teg_num]
    if data.empty:
        return pd.DataFrame()

    ascending = (measure != 'Stableford')

    pivoted = data.pivot_table(index='Player', columns='Round', values=measure, aggfunc='first')
    pivoted['Total'] = pivoted.sum(axis=1)
    pivoted = pivoted.sort_values('Total', ascending=ascending).reset_index()
    pivoted.columns = [f'R{int(c)}' if isinstance(c, (int, float)) else c for c in pivoted.columns]

    pivoted['Rank'] = pivoted['Total'].rank(method='min', ascending=ascending).astype(int)
    tied = pivoted['Total'].duplicated(keep=False)
    pivoted.loc[tied, 'Rank'] = pivoted.loc[tied, 'Rank'].astype(str) + '='

    round_cols = [c for c in pivoted.columns if c.startswith('R') and c != 'Rank']
    leaderboard = pivoted[['Rank', 'Player'] + round_cols + ['Total']]

    logger.info(f"Leaderboard created for {measure} (teg_num={teg_num}).")
    return leaderboard


def get_round_leaderboard(df: pd.DataFrame, measure: str,
                          teg_num: int = None, round_num: int = None) -> pd.DataFrame:
    """Single-round leaderboard.

    Args:
        df: Tournament data.
        measure: Score column to rank by.
        teg_num: Optional TEG filter.
        round_num: Optional round filter.

    Returns:
        DataFrame: Rank, Player, <measure>.
    """
    data = df.copy()
    if teg_num is not None:
        data = data[data['TEGNum'] == teg_num]
    if round_num is not None:
        data = data[data['Round'] == round_num]
    if data.empty:
        return pd.DataFrame()

    ascending = (measure != 'Stableford')
    agg = data.groupby('Player', as_index=False)[measure].sum()
    agg = agg.sort_values(measure, ascending=ascending)
    agg['Rank'] = agg[measure].rank(method='min', ascending=ascending).astype(int)
    tied = agg[measure].duplicated(keep=False)
    agg.loc[tied, 'Rank'] = agg.loc[tied, 'Rank'].astype(str) + '='

    logger.info(f"Round leaderboard created for {measure} (teg_num={teg_num}, round_num={round_num}).")
    return agg[['Rank', 'Player', measure]]
