"""Bestball and worstball team format analysis."""

import pandas as pd
from teg_analysis.analysis.scoring import format_vs_par

BESTBALL_COLS = ['TEG', 'TEGNum', 'Round', 'Course', 'Year']
VALUE_COLS = ['GrossVP', 'Sc']


def get_bestball_columns() -> tuple[list, list]:
    """Return (grouping_cols, value_cols) for bestball analysis."""
    return BESTBALL_COLS.copy(), VALUE_COLS.copy()


def prepare_bestball_data(all_data: pd.DataFrame) -> pd.DataFrame:
    """Add TRH (TEG|Round|Hole) identifier for team format grouping."""
    df = all_data.copy()
    df['TRH'] = df[['TEGNum', 'Round', 'Hole']].astype(str).agg('|'.join, axis=1)
    return df


def calculate_bestball_scores(filtered_data: pd.DataFrame) -> pd.DataFrame:
    """Best score per hole, summed to round totals."""
    bestball_holes = filtered_data.groupby('TRH').apply(
        lambda x: x.nsmallest(1, 'Sc'), include_groups=False
    ).reset_index(drop=True)
    result = bestball_holes.groupby(BESTBALL_COLS)[VALUE_COLS].sum().reset_index()
    result['Sc'] = result['Sc'].astype(int)
    return result


def calculate_worstball_scores(filtered_data: pd.DataFrame) -> pd.DataFrame:
    """Worst score per hole, summed to round totals."""
    worstball_holes = filtered_data.groupby('TRH').apply(
        lambda x: x.nlargest(1, 'Sc'), include_groups=False
    ).reset_index(drop=True)
    result = worstball_holes.groupby(BESTBALL_COLS)[VALUE_COLS].sum().reset_index()
    result['Sc'] = result['Sc'].astype(int)
    return result


def format_team_scores_for_display(team_data: pd.DataFrame, sort_by_best: bool = True) -> pd.DataFrame:
    """Format team scores with vs-par notation, sorted by performance."""
    df = team_data[BESTBALL_COLS + VALUE_COLS].sort_values(
        'GrossVP', ascending=sort_by_best
    ).copy()
    df['GrossVP'] = df['GrossVP'].apply(format_vs_par)
    return df
