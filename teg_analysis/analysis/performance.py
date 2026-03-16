"""Performance table generation — best/worst TEGs, rounds, personal records."""

import pandas as pd


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


# === ROUND DATA HELPER ===

def prepare_round_data_with_identifiers(rd_data_ranked: pd.DataFrame) -> pd.DataFrame:
    """Add combined 'TEG X|R1' identifier to the Round column."""
    df = rd_data_ranked.copy()
    df['Round'] = df['TEG'] + '|R' + df['Round'].astype(str)
    return df


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
