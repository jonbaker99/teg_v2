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


CONTRIBUTION_COLS = [
    'Pl', 'Player',
    'bb_holes', 'bb_solo', 'bb_impact',
    'wb_holes', 'wb_solo', 'wb_impact',
]


def calculate_player_contributions(round_data: pd.DataFrame) -> pd.DataFrame:
    """Per-player contribution to a single round's bestball and worstball totals.

    For each player, for each of bestball (field-lowest GrossVP per hole) and
    worstball (field-highest), computes:
      - holes:  number of holes where the player matched the field best/worst
                (the cells highlighted on the field scorecard); ties count for
                every matching player.
      - solo:   of those, the holes where the player was the *only* contributor.
      - impact: the player's signed contribution to the bestball/worstball
                total — recomputed as the team total *with* the player minus the
                total *without* them (the per-hole min/max recomputed without
                their round). Bestball impact is <= 0 (the player lowers/helps
                the team's best score); worstball impact is >= 0 (the player
                raises/worsens it). The total only moves on the player's solo
                holes.

    Args:
        round_data: all players in one round, with Pl, Player, Hole, GrossVP.

    Returns:
        DataFrame with one row per player and columns ``CONTRIBUTION_COLS``.
        Row order follows the input's player order (callers may re-sort).
    """
    if round_data is None or round_data.empty:
        return pd.DataFrame(columns=CONTRIBUTION_COLS)

    df = round_data[['Pl', 'Player', 'Hole', 'GrossVP']].copy()
    df['GrossVP'] = df['GrossVP'].astype(int)

    holes = sorted(df['Hole'].unique())
    by_hole = {h: df[df['Hole'] == h] for h in holes}

    rows = []
    for pl in df['Pl'].drop_duplicates():
        pdf = df[df['Pl'] == pl]
        name = pdf['Player'].iloc[0]
        pmap = dict(zip(pdf['Hole'], pdf['GrossVP']))
        bb_holes = bb_solo = wb_holes = wb_solo = 0
        bb_impact = wb_impact = 0
        for h in holes:
            if h not in pmap:
                continue
            vals = by_hole[h]['GrossVP'].values
            pv = pmap[h]
            hmin, hmax = int(vals.min()), int(vals.max())
            others = by_hole[h].loc[by_hole[h]['Pl'] != pl, 'GrossVP'].values
            if pv == hmin:
                bb_holes += 1
                if (vals == hmin).sum() == 1:
                    bb_solo += 1
            if pv == hmax:
                wb_holes += 1
                if (vals == hmax).sum() == 1:
                    wb_solo += 1
            # Signed contribution = (total with player) - (total without). On
            # tied or non-contributing holes the min/max is unchanged, so this
            # sums only the player's solo holes.
            if len(others) > 0:
                bb_impact += hmin - int(others.min())   # <= 0 (player helps bestball)
                wb_impact += hmax - int(others.max())   # >= 0 (player worsens worstball)
        rows.append({
            'Pl': pl, 'Player': name,
            'bb_holes': bb_holes, 'bb_solo': bb_solo, 'bb_impact': bb_impact,
            'wb_holes': wb_holes, 'wb_solo': wb_solo, 'wb_impact': wb_impact,
        })

    return pd.DataFrame(rows, columns=CONTRIBUTION_COLS)
