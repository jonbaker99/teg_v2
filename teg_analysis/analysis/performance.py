"""Performance table generation — best/worst TEGs, rounds, personal records.

Replaces 11 near-identical functions with a single parameterised
`prepare_performance_table()` plus a `prepare_pb_summary_table()`.
"""

import pandas as pd
from teg_analysis.analysis.scoring import format_vs_par


# === MEASURE MAPPINGS ===

MEASURE_NAMES = {
    'Gross': 'GrossVP',
    'Score': 'Sc',
    'Net': 'NetVP',
    'Stableford': 'Stableford',
}
MEASURE_NAMES_INV = {v: k for k, v in MEASURE_NAMES.items()}


def get_measure_name_mappings() -> tuple[dict, dict]:
    """Return (friendly→internal, internal→friendly) measure name dicts."""
    return MEASURE_NAMES.copy(), MEASURE_NAMES_INV.copy()


# === CORE PERFORMANCE TABLE ===

def prepare_performance_table(
    data: pd.DataFrame,
    measure: str,
    friendly_name: str,
    *,
    level: str = 'teg',
    direction: str = 'best',
    personal: bool = False,
    n: int = 10,
) -> pd.DataFrame:
    """One function to replace prepare_{best,worst}_{teg,round}_table and personal variants.

    Args:
        data: Ranked DataFrame (TEG-level or round-level).
        measure: Internal measure name (e.g. 'GrossVP').
        friendly_name: Display name (e.g. 'Gross').
        level: 'teg' or 'round'.
        direction: 'best' or 'worst'.
        personal: If True, return one row per player (their best/worst).
        n: Number of rows to return (ignored when personal=True).

    Returns:
        Formatted DataFrame ready for display.
    """
    higher_is_better = (measure == 'Stableford')
    want_best = (direction == 'best')

    # For TEG level, filter out TEG 2 (only 3 rounds)
    df = data.copy()
    if level == 'teg':
        df = df[df['TEGNum'] != 2]

    if personal:
        df = _select_personal(df, measure, want_best, higher_is_better, level)
    else:
        df = _select_top_n(df, measure, want_best, higher_is_better, n, level)

    # Sort
    if want_best:
        sort_asc = not higher_is_better
    else:
        sort_asc = higher_is_better
    df = df.sort_values(measure, ascending=sort_asc)

    # Rank
    df = df.copy()
    df['#'] = range(1, len(df) + 1)

    # Rename measures for display
    df = df.rename(columns=MEASURE_NAMES_INV)

    # Pick display columns
    if level == 'teg':
        cols = ['#', 'Player', friendly_name, 'TEG', 'Area', 'Year']
    else:
        cols = ['#', 'Player', friendly_name, 'Round', 'Course', 'Year']
    df = df[cols]

    # Format
    _format_display(df, friendly_name)
    return df


def _select_personal(df, measure, want_best, higher_is_better, level):
    """Select each player's best or worst row."""
    if level == 'round':
        from teg_analysis.analysis.rankings import get_best, get_worst
        fn = get_best if want_best else get_worst
        return fn(df, measure, player_level=True, top_n=1)

    # TEG level — use idxmin/idxmax directly
    if want_best == (not higher_is_better):
        # best + lower-is-better, or worst + higher-is-better → idxmin
        idx = df.groupby('Player')[measure].idxmin()
    else:
        idx = df.groupby('Player')[measure].idxmax()
    return df.loc[idx]


def _select_top_n(df, measure, want_best, higher_is_better, n, level):
    """Select top-N best or worst rows overall."""
    if level == 'round':
        from teg_analysis.analysis.rankings import get_best, get_worst
        fn = get_best if want_best else get_worst
        return fn(df, measure, player_level=False, top_n=n)

    # TEG level — use nsmallest/nlargest
    if want_best == (not higher_is_better):
        return df.nsmallest(n, measure)
    else:
        return df.nlargest(n, measure)


def _format_display(df, friendly_name):
    """In-place formatting: vs-par notation or integer conversion."""
    if friendly_name in ['Gross', 'Net']:
        df[friendly_name] = df[friendly_name].apply(format_vs_par)
        for col in df.select_dtypes(include=['float64', 'int64']).columns:
            if col != friendly_name:
                df[col] = df[col].astype(int)
    else:
        num_cols = df.select_dtypes(include=['float64', 'int64']).columns
        df[num_cols] = df[num_cols].astype(int)


# === ROUND DATA HELPER ===

def prepare_round_data_with_identifiers(rd_data_ranked: pd.DataFrame) -> pd.DataFrame:
    """Add combined 'TEG X|R1' identifier to the Round column."""
    df = rd_data_ranked.copy()
    df['Round'] = df['TEG'] + '|R' + df['Round'].astype(str)
    return df


# === PB SUMMARY TABLES (all measures, HTML output) ===

_SUMMARY_MEASURES = [
    ('Sc', 'Score', 'min'),
    ('GrossVP', 'Gross', 'min'),
    ('NetVP', 'Net', 'min'),
    ('Stableford', 'Stfd', 'max'),
]


def prepare_pb_summary_table(
    data: pd.DataFrame,
    level: str = 'teg',
) -> pd.DataFrame:
    """Personal-best summary table across all measures.

    Args:
        data: Ranked data at the appropriate level.
        level: 'teg', 'round', or 'nine'.

    Returns:
        DataFrame with HTML-formatted cells showing score + when.
    """
    df = data.copy()
    if level == 'teg':
        df = df[df['TEGNum'] != 2]

    players = sorted(df['Player'].unique())
    rows = []

    for player in players:
        pdata = df[df['Player'] == player]
        row = {'Player': player.replace(' ', '<br>')}

        for measure, col_name, agg in _SUMMARY_MEASURES:
            if agg == 'min':
                best = pdata.loc[pdata[measure].idxmin()]
            else:
                best = pdata.loc[pdata[measure].idxmax()]

            val = format_vs_par(best[measure]) if measure in ('GrossVP', 'NetVP') else str(int(best[measure]))
            when = _format_when(best, level)
            row[col_name] = f"<span class='pb-score'>{val}</span><br><span class='pb-when'>{when}</span>"

        rows.append(row)

    return pd.DataFrame(rows)


def _format_when(row, level):
    """Format the 'when' label for a PB summary cell."""
    teg = row['TEG']
    if level == 'teg':
        return teg
    rnd = f"|R{row['Round']}"
    if level == 'nine':
        return f"{teg}{rnd} {row['FrontBack']}"
    return f"{teg}{rnd}"


# === WORST PERFORMANCE DISPLAY HELPERS ===

def get_performance_measure_titles() -> dict:
    """Measure titles for worst-performance displays."""
    return {'Sc': "Worst Score", 'GrossVP': "Worst Gross",
            'NetVP': "Worst Net", 'Stableford': "Worst Stableford"}


def format_performance_value(value: float, measure: str) -> str:
    """Format a performance value with +/- for vs-par measures."""
    if measure in ['GrossVP', 'NetVP']:
        return f"{int(value):+}"
    return str(int(value))


def prepare_worst_performance_dataframe(worst_records: pd.DataFrame, record_type: str) -> pd.DataFrame:
    """Format worst-performance records for stat-section display."""
    df = worst_records.copy()
    df['Year'] = df['Year'].astype(str)
    if record_type in ['round', 'frontback']:
        df['Round'] = 'R' + df['Round'].astype(str)
        df['TEG_Round'] = df['TEG'] + ', ' + df['Round']
        if record_type == 'frontback':
            df['TEG_Round'] += ' ' + df['FrontBack'] + ' 9'
        return df[['Player', 'Course', 'TEG_Round', 'Year']]
    return df[['Player', 'TEG', 'Year']]


def load_worst_performance_custom_css() -> str:
    """CSS for worst-performance stat sections."""
    return """
    <style>
    div[data-testid="column"] {
        background-color: #f0f0f0; border-radius: 10px; padding: 20px; height: 100%;
    }
    .stat-section { margin-bottom: 20px; background-color: rgb(240, 242, 246); padding: 20px; margin: 5px; }
    .stat-section h2 { margin-bottom: 5px; font-size: 22px; line-height: 1.0; color: #333; padding: 0; }
    .stat-section h2 .title { font-weight: normal; }
    .stat-section h2 .value { font-weight: bold; }
    .stat-details { font-size: 16px; color: #999; line-height: 1.4; }
    .stat-details .Player { color: #666; }
    </style>
    """


def create_worst_performance_section(worst_records: pd.DataFrame, measure: str,
                                     record_type: str, measure_titles: dict) -> str:
    """Create complete HTML worst-performance stat section."""
    from teg_analysis.display.tables import create_stat_section
    title = measure_titles[measure]
    value = format_performance_value(worst_records[measure].iloc[0], measure)
    df = prepare_worst_performance_dataframe(worst_records, record_type)
    return create_stat_section(title, value, df, "| ")


def get_filtered_teg_data() -> pd.DataFrame:
    """TEG data with TEG 2 excluded (for worst-performance analysis)."""
    from teg_analysis.analysis.aggregation import get_complete_teg_data
    teg_data = get_complete_teg_data()
    return teg_data[teg_data['TEGNum'] != 2]
