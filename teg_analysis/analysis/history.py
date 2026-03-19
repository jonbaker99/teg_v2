"""TEG history, winners, and completeness checking.

Functions for calculating TEG winners, preparing history tables,
finding notable achievements (eagles, holes-in-one), and managing
cached winner data.
"""

import logging
import re
import pandas as pd

from teg_analysis.constants import TEG_OVERRIDES

logger = logging.getLogger(__name__)


# === WINNER CALCULATIONS ===

def get_teg_winners(df: pd.DataFrame) -> pd.DataFrame:
    """Generate TEG winners — Trophy, Green Jacket, Wooden Spoon — by TEG.

    Args:
        df: DataFrame containing hole-level golf data.

    Returns:
        DataFrame with columns: TEG, Year, TEG Trophy, Green Jacket, HMM Wooden Spoon.
    """
    from .scoring import get_net_competition_measure

    grouped = df.groupby(['TEGNum', 'Player']).agg({
        'GrossVP': 'sum', 'NetVP': 'sum', 'Stableford': 'sum'
    }).reset_index()

    results = []
    for teg_num in df['TEGNum'].unique():
        teg_data = grouped[grouped['TEGNum'] == teg_num]
        net_measure = get_net_competition_measure(teg_num)

        best_gross_player = teg_data.loc[teg_data['GrossVP'].idxmin(), 'Player']

        if net_measure == 'NetVP':
            best_net_player = teg_data.loc[teg_data['NetVP'].idxmin(), 'Player']
            worst_net_player = teg_data.loc[teg_data['NetVP'].idxmax(), 'Player']
        else:
            best_net_player = teg_data.loc[teg_data['Stableford'].idxmax(), 'Player']
            worst_net_player = teg_data.loc[teg_data['Stableford'].idxmin(), 'Player']

        # Apply manual overrides
        teg_label = f"TEG {teg_num}"
        overrides = TEG_OVERRIDES.get(teg_label, {})
        best_gross_player = overrides.get('Best Gross', best_gross_player)
        best_net_player = overrides.get('Best Net', best_net_player)
        worst_net_player = overrides.get('Worst Net', worst_net_player)

        results.append({
            'TEGNum': teg_num, 'TEG': teg_label,
            'Best Gross': best_gross_player, 'Best Net': best_net_player,
            'Worst Net': worst_net_player,
        })

    result_df = pd.DataFrame(results).sort_values(by='TEGNum')
    teg_years = df[['TEGNum', 'Year']].drop_duplicates()
    result_df = result_df.merge(teg_years, on='TEGNum', how='left')
    result_df.rename(columns={
        'Best Net': 'TEG Trophy', 'Best Gross': 'Green Jacket',
        'Worst Net': 'HMM Wooden Spoon',
    }, inplace=True)
    return result_df[['TEG', 'Year', 'TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon']]


# === CHART / DISPLAY HELPERS ===

def process_winners_for_charts(winners_df: pd.DataFrame) -> dict:
    """Transform winners data into sorted datasets for bar charts."""
    clean_winners = winners_df.replace(r'\*', '', regex=True)
    melted = pd.melt(
        clean_winners, id_vars=['TEG'],
        value_vars=['TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon'],
        var_name='Competition', value_name='Player',
    )
    wins = melted.groupby(['Player', 'Competition']).size().unstack(fill_value=0)
    wins = wins[['TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon']]
    wins.columns = ['Trophy', 'Jacket', 'Spoon']

    trophy_sorted = wins.sort_values('Trophy', ascending=False).reset_index()
    jacket_sorted = wins.sort_values('Jacket', ascending=False).reset_index()
    spoon_sorted = wins.sort_values('Spoon', ascending=False).reset_index()

    return {
        'trophy_sorted': trophy_sorted,
        'jacket_sorted': jacket_sorted,
        'spoon_sorted': spoon_sorted,
        'max_wins': max(trophy_sorted['Trophy'].max(),
                        jacket_sorted['Jacket'].max(),
                        spoon_sorted['Spoon'].max()),
    }


def calculate_trophy_jacket_doubles(winners_df: pd.DataFrame) -> tuple:
    """Find players who won both Trophy and Green Jacket in the same TEG."""
    clean = winners_df.replace(r'\*', '', regex=True)
    same = clean[clean['TEG Trophy'] == clean['Green Jacket']]
    doubles = same['TEG Trophy'].value_counts().reset_index()
    doubles.columns = ['Player', 'Doubles']
    return doubles.sort_values('Doubles', ascending=False), same.shape[0]


def prepare_history_table_display(winners_df: pd.DataFrame) -> pd.DataFrame:
    """Format winners for history table with TEG(Year) and Area columns."""
    from teg_analysis.io.file_operations import read_file
    from teg_analysis.constants import ROUND_INFO_CSV

    display = winners_df.copy()
    round_info = read_file(ROUND_INFO_CSV)
    teg_areas = round_info[['TEG', 'Area']].drop_duplicates()
    display = display.merge(teg_areas, on='TEG', how='left')
    display['TEG'] = display['TEG'].astype(str) + " (" + display['Year'].astype(str) + ")"
    display = display.drop(columns=['Year'])
    other_cols = [c for c in display.columns if c not in ['TEG', 'Area']]
    return display[['TEG', 'Area'] + other_cols]


# === NOTABLE ACHIEVEMENTS ===

def get_eagles_data(all_data: pd.DataFrame) -> pd.DataFrame:
    """Find all Eagles (-2 gross vs par) in TEG history."""
    eagles = all_data[all_data['GrossVP'] == -2.0].copy()
    if eagles.empty:
        return pd.DataFrame(columns=['Player', 'Date', 'Course', 'Hole'])
    eagles['Hole'] = eagles['TEG'].astype(str) + ' | Rd ' + eagles['Round'].astype(str) + ' | Hole ' + eagles['Hole'].astype(str)
    result = eagles[['Player', 'Date', 'Course', 'Hole', 'TEGNum']].copy()
    return result.sort_values(['TEGNum', 'Date'])[['Player', 'Date', 'Course', 'Hole']]


def get_holes_in_one_data(all_data: pd.DataFrame) -> pd.DataFrame:
    """Find all Holes in One (score == 1) in TEG history."""
    hio = all_data[all_data['Sc'] == 1.0].copy()
    if hio.empty:
        return pd.DataFrame(columns=['Player', 'Date', 'Course', 'Hole'])
    hio['Hole'] = hio['TEG'].astype(str) + ' | Rd ' + hio['Round'].astype(str) + ' | Hole ' + hio['Hole'].astype(str)
    result = hio[['Player', 'Date', 'Course', 'Hole', 'TEGNum']].copy()
    return result.sort_values(['TEGNum', 'Date'])[['Player', 'Date', 'Course', 'Hole']]


# === INCOMPLETE / FUTURE TEGS ===

def get_incomplete_tegs() -> pd.DataFrame:
    """Find TEGs that have started but not completed."""
    from teg_analysis.core.data_loader import load_all_data, exclude_incomplete_tegs_function
    from teg_analysis.io import read_file
    from teg_analysis.constants import ROUND_INFO_CSV

    all_with = load_all_data(exclude_incomplete_tegs=False)
    complete = load_all_data(exclude_incomplete_tegs=True)
    incomplete_nums = set(all_with['TEGNum'].unique()) - set(complete['TEGNum'].unique())

    if not incomplete_nums:
        return pd.DataFrame(columns=['TEG', 'Year', 'Area'])

    round_info = read_file(ROUND_INFO_CSV)
    inc = round_info[round_info['TEGNum'].isin(incomplete_nums)]
    summary = inc[['TEGNum', 'TEG', 'Year', 'Area']].drop_duplicates()
    return summary.sort_values('TEGNum')[['TEG', 'Year', 'Area']]


def get_future_tegs() -> pd.DataFrame:
    """Load planned future TEGs from data/future_tegs.csv."""
    from teg_analysis.io import read_file
    try:
        future = read_file('data/future_tegs.csv')
        future['Year'] = future['Year'].astype(int)
        return future[['TEG', 'Year', 'Area']].sort_values('Year')
    except Exception:
        return pd.DataFrame(columns=['TEG', 'Year', 'Area'])


# === HISTORY TABLE ASSEMBLY ===

def _extract_teg_num(teg_str: str) -> int:
    """Extract numeric TEG number from 'TEG X (YYYY)' format."""
    match = re.search(r'TEG (\d+)', str(teg_str))
    return int(match.group(1)) if match else 999


def _sort_history_by_teg(df: pd.DataFrame) -> pd.DataFrame:
    """Sort a history DataFrame by TEG number extracted from TEG column."""
    df = df.copy()
    df['_sort'] = df['TEG'].apply(_extract_teg_num)
    return df.sort_values('_sort').drop('_sort', axis=1)


def _make_tbc_entries(pending_tegs: pd.DataFrame) -> pd.DataFrame:
    """Create TBC rows for incomplete/future TEGs."""
    entries = []
    for _, row in pending_tegs.iterrows():
        entries.append({
            'TEG': f"{row['TEG']} ({row['Year']})",
            'Area': row['Area'],
            'TEG Trophy': 'TBC', 'Green Jacket': 'TBC', 'HMM Wooden Spoon': 'TBC',
        })
    return pd.DataFrame(entries)


def prepare_complete_history_table(winners_df: pd.DataFrame) -> pd.DataFrame:
    """Complete history table: completed + incomplete + future TEGs."""
    completed = prepare_history_table_display(winners_df)
    incomplete = get_incomplete_tegs()
    future = get_future_tegs()

    existing = {m.group(1) for t in completed['TEG']
                if (m := re.search(r'(TEG \d+)', t))}
    if not incomplete.empty:
        existing.update(incomplete['TEG'].tolist())
    if not future.empty:
        future = future[~future['TEG'].isin(existing)]

    pending = pd.concat([incomplete, future], ignore_index=True)
    if pending.empty:
        return completed

    tbc = _make_tbc_entries(pending)
    return _sort_history_by_teg(pd.concat([completed, tbc], ignore_index=True))


# === WINNER CACHING ===

def check_winner_completeness() -> set:
    """Return set of TEG numbers completed but missing from winners cache."""
    from teg_analysis.io import read_file
    try:
        completed = read_file('data/completed_tegs.csv')
        cached = read_file('data/teg_winners.csv')
        completed_nums = set(completed['TEGNum']) if not completed.empty else set()
        cached_nums = set()
        if not cached.empty:
            for t in cached['TEG']:
                m = re.search(r'TEG (\d+)', str(t))
                if m:
                    cached_nums.add(int(m.group(1)))
        return completed_nums - cached_nums
    except Exception as e:
        print(f"Error checking winner completeness: {e}")
        return set()


def calculate_and_save_missing_winners(missing_teg_nums: set) -> dict:
    """Calculate and cache winners for missing TEGs.

    Returns dict with keys: new_winners, errors, warnings, cache_clear_needed.
    """
    from ..io.file_operations import read_file, write_file
    from ..core.data_loader import load_all_data

    all_data = load_all_data()
    if all_data.empty:
        raise ValueError("No data available to calculate winners")

    try:
        cached = read_file('data/teg_winners.csv')
    except Exception:
        cached = pd.DataFrame(columns=['TEG', 'Year', 'Area', 'TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon'])

    new_winners, errors, warnings = [], [], []

    for teg_num in missing_teg_nums:
        try:
            teg_data = all_data[all_data['TEGNum'] == teg_num]
            if teg_data.empty:
                warnings.append(f"No data found for TEG {teg_num}")
                continue
            info = teg_data.iloc[0]
            winners_df = get_teg_winners(teg_data)
            if not winners_df.empty:
                teg_winners = winners_df[winners_df['TEG'] == info['TEG']]
                if not teg_winners.empty:
                    row = teg_winners.iloc[0]
                    new_winners.append({
                        'TEG': info['TEG'], 'Year': info['Year'],
                        'Area': info.get('Area', 'Unknown'),
                        'TEG Trophy': row.get('TEG Trophy', 'Unknown'),
                        'Green Jacket': row.get('Green Jacket', 'Unknown'),
                        'HMM Wooden Spoon': row.get('HMM Wooden Spoon', 'Unknown'),
                    })
        except Exception as e:
            errors.append({'teg': teg_num, 'error': str(e)})

    if new_winners:
        updated = pd.concat([cached, pd.DataFrame(new_winners)], ignore_index=True)
        updated = updated.sort_values('Year')
        write_file('data/teg_winners.csv', updated)
        return {'new_winners': new_winners, 'errors': errors, 'warnings': warnings, 'cache_clear_needed': True}

    warnings.append("No winners could be calculated for the missing TEGs")
    return {'new_winners': [], 'errors': errors, 'warnings': warnings, 'cache_clear_needed': False}


def load_cached_winners() -> tuple:
    """Load cached winners, calculating any missing ones.

    Returns (winners_df, missing_set) or (None, set()).
    """
    from ..io.file_operations import read_file
    from ..core.data_loader import load_all_data

    try:
        cached = read_file('data/teg_winners.csv')
        missing = check_winner_completeness()

        if not missing:
            cached['TEG'] = cached['TEG'].astype(str) + " (" + cached['Year'].astype(str) + ")"
            cached = cached.drop(columns=['Year'])
            return cached, set()

        all_data = load_all_data()
        for teg_num in missing:
            try:
                teg_data = all_data[all_data['TEGNum'] == teg_num]
                if not teg_data.empty:
                    w = get_teg_winners(teg_data)
                    if not w.empty:
                        info = teg_data.iloc[0]
                        row = w.iloc[0]
                        new_row = {
                            'TEG': info['TEG'], 'Year': info['Year'], 'Area': info['Area'],
                            'TEG Trophy': row.get('TEG Trophy', 'Unknown'),
                            'Green Jacket': row.get('Green Jacket', 'Unknown'),
                            'HMM Wooden Spoon': row.get('HMM Wooden Spoon', 'Unknown'),
                        }
                        cached = pd.concat([cached, pd.DataFrame([new_row])], ignore_index=True)
            except Exception as e:
                print(f"Error calculating winners for TEG {teg_num}: {e}")

        cached['TEG'] = cached['TEG'].astype(str) + " (" + cached['Year'].astype(str) + ")"
        cached = cached.drop(columns=['Year'])
        return cached, missing

    except Exception as e:
        print(f"Could not load cached winners: {e}")
        return None, set()


def prepare_complete_history_table_fast(cached_winners_df: pd.DataFrame = None) -> pd.DataFrame:
    """Fast history table using cached winners data."""
    if cached_winners_df is None:
        cached_winners_df, _ = load_cached_winners()

    if cached_winners_df is None:
        from teg_analysis.core.data_loader import load_all_data
        all_data = load_all_data(exclude_incomplete_tegs=True, exclude_teg_50=True)
        completed = prepare_history_table_display(get_teg_winners(all_data))
    else:
        completed = cached_winners_df.copy()

    future = get_future_tegs()
    existing = {m.group(1) for t in completed['TEG']
                if (m := re.search(r'(TEG \d+)', t))}

    if not future.empty:
        future = future[~future['TEG'].isin(existing)]
    if future.empty:
        return completed

    tbc = _make_tbc_entries(future)
    return _sort_history_by_teg(pd.concat([completed, tbc], ignore_index=True))
