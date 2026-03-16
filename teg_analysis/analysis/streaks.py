"""Streak analysis for TEG golf data.

Calculates consecutive scoring achievements (birdies, pars, etc.),
tracks running streaks across player careers, and summarizes max streaks.
"""

import logging

import pandas as pd


# --- Configuration -----------------------------------------------------------

BOOL_COLS = ["eagle", "birdie", "par_better", "double_bogey", "TBP"]

STREAK_CONFIGS = {
    'good': {
        'column_mapping': {
            'Birdies': 'birdie_true_streak',
            'Pars': 'par_better_true_streak',
            'No +2s': 'double_bogey_false_streak',
            'No TBPs': 'TBP_false_streak',
        },
        'sort_col': 'Pars',
        'streak_types': ['Eagles', 'Birdies', 'Pars or Better', 'No +2s', 'No TBPs'],
    },
    'bad': {
        'column_mapping': {
            'No Eagles': 'eagle_false_streak',
            'No Birdies': 'birdie_false_streak',
            'Over par': 'par_better_false_streak',
            '+2s': 'double_bogey_true_streak',
            'TBPs': 'TBP_true_streak',
        },
        'sort_col': 'Over par',
        'streak_types': ['No Eagles', 'No Birdies', 'Over Par', '+2s or Worse', 'TBPs'],
    },
}


# --- Core streak building ----------------------------------------------------

def build_streaks(all_data: pd.DataFrame, assume_sorted: bool = False) -> pd.DataFrame:
    """Create streaks data (boolean flags + streak counters) from all_data.

    Requires columns: 'Pl', 'HoleID', 'Sc', 'Career Count', 'GrossVP', 'Hole Order Ever'

    Adds boolean flags (eagle, birdie, par_better, double_bogey, TBP) and for
    each flag adds <name>_true_streak and <name>_false_streak counters.
    """
    needed = ['Pl', 'HoleID', 'Sc', 'Career Count', 'GrossVP', 'Hole Order Ever']
    missing = [c for c in needed if c not in all_data.columns]
    if missing:
        raise KeyError(f"build_streaks: missing columns in all_data: {missing}")

    df = all_data[needed].copy()

    df['eagle']        = df['GrossVP'] <= -2
    df['birdie']       = df['GrossVP'] <= -1
    df['par_better']   = df['GrossVP'] <= 0
    df['double_bogey'] = df['GrossVP'] > 1
    df['TBP']          = df['GrossVP'] > 2

    if not assume_sorted:
        df = df.sort_values(['Pl', 'Career Count'], kind='mergesort').reset_index(drop=True)

    for col in BOOL_COLS:
        s = df[col].fillna(False).astype(bool)
        reset = df['Pl'].ne(df['Pl'].shift()) | s.ne(s.shift())
        seg_id = reset.cumsum()
        pos = df.groupby(seg_id).cumcount() + 1
        df[f"{col}_true_streak"]  = pos.where(s, 0)
        df[f"{col}_false_streak"] = pos.where(~s, 0)

    return df


# --- Streak accessors --------------------------------------------------------

def get_max_streaks(streaks_df):
    """Return max streaks for each player in wide form."""
    scols = [c for c in streaks_df.columns if c.endswith("_streak")]
    return streaks_df.groupby("Pl", as_index=False)[scols].max()


def get_current_streaks(streaks_df):
    """Return current (latest) streaks for each player in wide form."""
    scols = [c for c in streaks_df.columns if c.endswith("_streak")]
    latest_idx = streaks_df.groupby("Pl")["Career Count"].idxmax()
    return streaks_df.loc[latest_idx, ["Pl"] + scols].reset_index(drop=True)


def get_player_mapping(all_data):
    """Get mapping from Pl to Player names."""
    return all_data[['Pl', 'Player']].drop_duplicates().set_index('Pl')['Player'].to_dict()


def get_current_equals_max_streaks(max_streaks_df, current_streaks_df):
    """Boolean mask: which current streaks equal historical maximums."""
    streak_cols = [c for c in max_streaks_df.columns if c.endswith('_streak')]

    comparison = max_streaks_df[['Pl'] + streak_cols].merge(
        current_streaks_df[['Pl'] + streak_cols],
        on='Pl', suffixes=('_max', '_current')
    )

    equals_max = pd.DataFrame({'Pl': comparison['Pl']})
    for col in streak_cols:
        equals_max[col] = comparison[f'{col}_max'] == comparison[f'{col}_current']

    return equals_max


# --- Display transforms (direction-parameterised) ----------------------------

def transform_cached_streaks(streaks_df, player_mapping, direction='good', equals_max_df=None):
    """Transform cached streak data into display format.

    Args:
        streaks_df: Output from get_max_streaks() or get_current_streaks()
        player_mapping: Mapping from Pl to Player names
        direction: 'good' or 'bad'
        equals_max_df: Boolean mask from get_current_equals_max_streaks()

    Returns:
        DataFrame with Player column and display-named streak columns.
        Values marked with '*' when current equals max.
    """
    config = STREAK_CONFIGS[direction]
    column_mapping = config['column_mapping']
    sort_col = config['sort_col']

    result = pd.DataFrame()
    result['Player'] = streaks_df['Pl'].map(player_mapping)

    for display_col, streak_col in column_mapping.items():
        values = streaks_df[streak_col].astype(str)

        if equals_max_df is not None:
            merged = streaks_df[['Pl', streak_col]].merge(
                equals_max_df[['Pl', streak_col]], on='Pl', suffixes=('', '_equals_max')
            )
            mask = merged[f'{streak_col}_equals_max']
            values = merged[streak_col].astype(str)
            values.loc[mask] = values.loc[mask] + '*'

        result[display_col] = values

    result['_sort'] = result[sort_col].str.replace('*', '', regex=False).astype(int)
    result = result.sort_values('_sort', ascending=False).drop('_sort', axis=1)

    return result


def _load_and_transform(all_data, direction, use_current=False):
    """Shared logic for prepare_streaks_data / prepare_current_streaks_data.

    Loads cached streaks, computes equals-max mask, and transforms to display format.
    Falls back to computing streaks from all_data if cache unavailable.
    """
    try:
        from teg_analysis.io import read_file
        from teg_analysis.constants import STREAKS_PARQUET

        streaks_df = read_file(STREAKS_PARQUET)
    except Exception as e:
        logging.warning(f"Could not read streaks cache, falling back to calculation: {e}")
        streaks_df = build_streaks(all_data)

    player_mapping = get_player_mapping(all_data)
    max_streaks = get_max_streaks(streaks_df)
    current_streaks = get_current_streaks(streaks_df)
    equals_max = get_current_equals_max_streaks(max_streaks, current_streaks)

    source = current_streaks if use_current else max_streaks
    return transform_cached_streaks(source, player_mapping, direction, equals_max)


def prepare_streaks_data(all_data, direction='good'):
    """Prepare max streaks data for display. direction='good' or 'bad'."""
    return _load_and_transform(all_data, direction, use_current=False)


def prepare_current_streaks_data(all_data, direction='good'):
    """Prepare current (ongoing) streaks data for display. direction='good' or 'bad'."""
    return _load_and_transform(all_data, direction, use_current=True)


# Backward-compatible aliases
def prepare_good_streaks_data(all_data):
    return prepare_streaks_data(all_data, 'good')

def prepare_bad_streaks_data(all_data):
    return prepare_streaks_data(all_data, 'bad')

def prepare_current_good_streaks_data(all_data):
    return prepare_current_streaks_data(all_data, 'good')

def prepare_current_bad_streaks_data(all_data):
    return prepare_current_streaks_data(all_data, 'bad')


# --- Window streak functions (TEG/Round level) --------------------------------

def adjust_opening_streak(series):
    """Adjust streak values to be relative to the start of a window.

    When analyzing streaks within a TEG or Round, adjusts for any pre-existing
    streak carried over from before the window.
    """
    if len(series) == 0:
        return series

    opening_val = series.iloc[0]
    if opening_val == 0:
        return series

    has_reset = (series == 0).any()
    if has_reset:
        reset_idx = (series == 0).idxmax()
        result = series.copy()
        mask = series.index < reset_idx
        result.loc[mask] = result.loc[mask] - opening_val + 1
        return result
    else:
        return series - opening_val + 1


def find_streak_location(window_data, streak_col, max_value):
    """Find where the maximum streak occurred (start and end holes).

    Returns (from_holeid, to_holeid) or (None, None) if not found.
    """
    if max_value == 0:
        return None, None

    max_locations = window_data[window_data[streak_col] == max_value]
    if len(max_locations) == 0:
        return None, None

    end_idx = max_locations.index[-1]
    end_hole = window_data.loc[end_idx, 'HoleID']

    start_idx = end_idx - max_value + 1
    if start_idx < window_data.index[0]:
        start_idx = window_data.index[0]
    start_hole = window_data.loc[start_idx, 'HoleID']

    return start_hole, end_hole


def format_hole_location(hole_id):
    """Convert HoleID format (T10|R01|H01) to display format (T10 R1 H1)."""
    if pd.isna(hole_id) or hole_id is None:
        return ""

    parts = str(hole_id).split('|')
    if len(parts) != 3:
        return hole_id

    teg = parts[0]
    round_num = int(parts[1].replace('R', ''))
    hole_num = int(parts[2].replace('H', ''))

    return f"{teg} R{round_num} H{hole_num}"


def calculate_window_streaks(window_data):
    """Calculate adjusted streaks for a selected window with location info.

    Args:
        window_data: Filtered DataFrame for the window (must include
                    'Player', 'HoleID', and all streak columns)

    Returns:
        DataFrame with columns: ['Streak Type', 'Player', 'Max Streak', 'Location']
    """
    if len(window_data) == 0:
        return pd.DataFrame()

    streak_cols = [c for c in window_data.columns if c.endswith('_streak')]

    streak_names = {
        'eagle_true_streak': 'Eagles',
        'eagle_false_streak': 'No Eagles',
        'birdie_true_streak': 'Birdies',
        'birdie_false_streak': 'No Birdies',
        'par_better_true_streak': 'Pars or Better',
        'par_better_false_streak': 'Over Par',
        'double_bogey_true_streak': '+2s or Worse',
        'double_bogey_false_streak': 'No +2s',
        'TBP_true_streak': 'TBPs',
        'TBP_false_streak': 'No TBPs'
    }

    results = []

    for player in window_data['Player'].unique():
        player_data = window_data[window_data['Player'] == player].copy()

        for streak_col in streak_cols:
            adj_col = f'{streak_col}_adj'
            player_data[adj_col] = adjust_opening_streak(player_data[streak_col])
            max_streak = player_data[adj_col].max()

            from_hole, to_hole = find_streak_location(player_data, adj_col, max_streak)
            if from_hole and to_hole:
                location = f"{format_hole_location(from_hole)} to {format_hole_location(to_hole)}"
            else:
                location = "-"

            results.append({
                'Streak Type': streak_names.get(streak_col, streak_col),
                'Player': player,
                'Max Streak': int(max_streak),
                'Location': location
            })

    results_df = pd.DataFrame(results)

    good_order = ['Eagles', 'Birdies', 'Pars or Better', 'No +2s', 'No TBPs']
    bad_order = ['No Eagles', 'No Birdies', 'Over Par', '+2s or Worse', 'TBPs']
    streak_order = good_order + bad_order

    results_df['_order'] = results_df['Streak Type'].map({s: i for i, s in enumerate(streak_order)})
    results_df = results_df.sort_values(['_order', 'Player']).drop('_order', axis=1)

    return results_df


def get_player_window_streaks(all_data, streaks_df, player=None, teg=None, round_num=None):
    """Get streak stats for a TEG/Round window.

    Args:
        all_data: Main DataFrame with all golf data
        streaks_df: Streaks DataFrame from read_file(STREAKS_PARQUET)
        player: Player code (e.g., 'JB') - optional
        teg: TEG name (e.g., 'TEG 10') - optional
        round_num: Round number (e.g., 1) - optional
    """
    df = streaks_df.merge(
        all_data[['HoleID', 'TEG', 'TEGNum', 'Round', 'Pl', 'Player']],
        on=['HoleID', 'Pl']
    )

    filtered = df.copy()
    if player:
        filtered = filtered[filtered['Pl'] == player]
    if teg:
        filtered = filtered[filtered['TEG'] == teg]
    if round_num is not None:
        filtered = filtered[filtered['Round'] == round_num]

    if len(filtered) == 0:
        return pd.DataFrame()

    filtered = filtered.sort_values(['Pl', 'TEGNum', 'Round', 'Career Count'])
    return calculate_window_streaks(filtered)


# --- Record streaks (direction-parameterised) ---------------------------------

def prepare_record_streaks_data(all_data, direction='good'):
    """Prepare record streaks data showing all-time record holders.

    Args:
        all_data: Raw tournament data
        direction: 'good' for best streaks, 'bad' for worst streaks

    Returns:
        DataFrame with columns ['Streak Type', 'Record', 'Player', 'When'].
        Only includes streaks > 1. Marks current streaks with '*'.
    """
    from teg_analysis.io import read_file
    from teg_analysis.constants import STREAKS_PARQUET

    streaks_df = read_file(STREAKS_PARQUET)

    df = streaks_df.merge(
        all_data[['HoleID', 'TEG', 'TEGNum', 'Round', 'Pl', 'Player']],
        on=['HoleID', 'Pl']
    )

    last_hole = df.sort_values('Hole Order Ever').iloc[-1]['HoleID']

    df = df.sort_values(['Pl', 'TEGNum', 'Round', 'Career Count'])
    all_streaks = calculate_window_streaks(df)

    streak_types = STREAK_CONFIGS[direction]['streak_types']
    filtered = all_streaks[all_streaks['Streak Type'].isin(streak_types)]

    records = []
    for streak_type in streak_types:
        type_data = filtered[filtered['Streak Type'] == streak_type]
        if len(type_data) == 0:
            continue

        max_streak = type_data['Max Streak'].max()
        if max_streak <= 1:
            continue

        for _, row in type_data[type_data['Max Streak'] == max_streak].iterrows():
            location = row['Location']
            is_current = location.endswith(format_hole_location(last_hole))
            record_display = f"{row['Max Streak']}*" if is_current else str(row['Max Streak'])

            records.append({
                'Streak Type': streak_type,
                'Record': record_display,
                'Player': row['Player'],
                'When': location
            })

    return pd.DataFrame(records)


# Backward-compatible aliases
def prepare_record_best_streaks_data(all_data):
    return prepare_record_streaks_data(all_data, 'good')

def prepare_record_worst_streaks_data(all_data):
    return prepare_record_streaks_data(all_data, 'bad')
