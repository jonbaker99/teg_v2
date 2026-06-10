"""Value formatting and display utilities.

This module provides formatting functions for display in the TEG analysis system,
including value formatters, date formatters, and data preparation for display tables.
"""

import logging
import pandas as pd
from typing import Tuple

logger = logging.getLogger(__name__)


# === CONSTANTS ===
MEASURE_TITLES = {
    'Sc': "Best Score",
    'GrossVP': "Best Gross",
    'NetVP': "Best Net",
    'Stableford': "Best Stableford"
}

WORST_MEASURE_TITLES = {
    'Sc': "Worst Score",
    'GrossVP': "Worst Gross",
    'NetVP': "Worst Net",
    'Stableford': "Worst Stableford"
}


# === CORE FORMATTING FUNCTIONS ===

def format_vs_par(value: float) -> str:
    """Formats a value as a vs-par score (e.g., '-5', 'E', '+3').

    Args:
        value: The numerical value to format.

    Returns:
        str: The formatted vs-par score.
    """
    if value is None or (isinstance(value, float) and value != value):  # Check for NaN
        return 'N/A'

    value = int(value)

    if value > 0:
        return f'+{value}'
    elif value == 0:
        return 'E'
    else:
        return str(value)


def format_date_for_scorecard(date_str, input_format=None, output_format='%d/%m/%y'):
    """Formats a date string for scorecard display.

    Args:
        date_str: The date string to format.
        input_format: The input format (optional, will attempt to infer).
        output_format: The desired output format (default: '%d/%m/%y').

    Returns:
        str: The formatted date string.
    """
    if pd.isna(date_str):
        return ''

    try:
        if input_format:
            date_obj = pd.to_datetime(date_str, format=input_format)
        else:
            date_obj = pd.to_datetime(date_str, dayfirst=True)  # FIXED: added dayfirst=True
        return date_obj.strftime(output_format)
    except:
        return str(date_str)


# === RECORD VALUE FORMATTING ===

def format_record_value(value: float, measure: str) -> str:
    """Formats a record value for display based on the measure type.

    Args:
        value (float): The numeric value to format.
        measure (str): The measure type ('GrossVP', 'NetVP', 'Sc',
            'Stableford').

    Returns:
        str: The formatted value as a string (e.g., "+3", "-2", "85").
    """
    if measure in ['GrossVP', 'NetVP']:
        return f"{int(value):+}"  # Shows +3 or -2
    else:
        return str(int(value))    # Shows 85


# === RECORDS DISPLAY PREPARATION ===

def prepare_records_display(best_records: pd.DataFrame, record_type: str) -> pd.DataFrame:
    """Prepares record data for display.

    This function formats columns and selects relevant fields based on the
    record type.

    Args:
        best_records (pd.DataFrame): The raw record data.
        record_type (str): The type of record ('teg', 'round', or
            'frontback').

    Returns:
        pd.DataFrame: The formatted data ready for display.
    """
    df = best_records.copy()
    df['Year'] = df['Year'].astype(str)

    if record_type in ['round', 'frontback']:
        # Add "R" prefix to round numbers (R1, R2, etc.)
        df['Round'] = 'R' + df['Round'].astype(str)
        # Combine TEG and Round for display (e.g., "TEG 15, R2")
        df['TEG_Round'] = df['TEG'] + ', ' + df['Round']

        if record_type == 'frontback':
            # Add front/back designation for 9-hole records
            df['TEG_Round'] += ' ' + df['FrontBack'] + ' 9'

        # Select columns for round/9-hole display
        df = df[['Player', 'Course', 'TEG_Round', 'Year']]
    else:
        # TEG-level records only need these columns
        df = df[['Player', 'TEG', 'Year']]

    return df


def prepare_records_table(data_source: pd.DataFrame, record_type: str) -> pd.DataFrame:
    """Prepares a consolidated records table.

    This function creates a unified table showing the best records across all
    measures for a given record type.

    Args:
        data_source (pd.DataFrame): The ranked data (teg, round, or
            frontback).
        record_type (str): The type of record ('teg', 'round', or
            'frontback').

    Returns:
        pd.DataFrame: A table with a custom header based on the record type.
    """
    from teg_analysis.analysis.rankings import get_best

    if record_type == 'teg':
        table_title = 'Best TEGs:'
        measures = ['GrossVP', 'NetVP', 'Stableford']
    elif record_type == 'round':
        table_title = 'Best Rounds:'
        measures = ['GrossVP', 'Sc', 'NetVP', 'Stableford']
    else:  # frontback
        table_title = 'Best 9s:'
        measures = ['GrossVP', 'Sc', 'NetVP', 'Stableford']

    records_data = []

    for measure in measures:
        rank_column = f'Rank_within_all_{measure}'

        if rank_column in data_source.columns:
            tied_records = data_source[data_source[rank_column] == 1]
        else:
            tied_records = get_best(data_source, measure_to_use=measure, top_n=1)

        if not tied_records.empty:
            for idx, record_row in tied_records.iterrows():
                if record_type == 'teg':
                    when = f"{record_row['TEG']} ({record_row['Area']}, {record_row['Year']})"
                else:
                    if 'Date' in record_row and pd.notna(record_row['Date']):
                        # FIXED: Removed the secondary .strftime() call that would cause a crash
                        month_year = format_date_for_scorecard(record_row['Date'], output_format='%b %Y')
                    else:
                        month_year = str(record_row['Year'])
                    
                    if record_type == 'round':
                        when = f"{record_row['TEG']} Rd {record_row['Round']} ({record_row['Course']}, {month_year})"
                    else:  # frontback
                        when = f"{record_row['TEG']} Rd {record_row['Round']} {record_row['FrontBack']} ({record_row['Course']}, {month_year})"

                records_data.append({
                    table_title: MEASURE_TITLES[measure],
                    '': format_record_value(record_row[measure], measure),
                    ' ': record_row['Player'],
                    '  ': when
                })

    return pd.DataFrame(records_data)


def prepare_worst_records_table(data_source: pd.DataFrame, record_type: str) -> pd.DataFrame:
    """Prepares a consolidated worst records table.

    This function creates a unified table showing the worst records across all
    measures for a given record type.

    Args:
        data_source (pd.DataFrame): The data source (teg, round, or
            frontback).
        record_type (str): The type of record ('teg', 'round', or
            'frontback').

    Returns:
        pd.DataFrame: A table with a custom header based on the record type.
    """
    if record_type == 'teg':
        table_title = 'Worst TEGs:'
        measures = ['GrossVP', 'NetVP', 'Stableford']
    elif record_type == 'round':
        table_title = 'Worst Rounds:'
        measures = ['GrossVP', 'Sc', 'NetVP', 'Stableford']
    else:  # frontback
        table_title = 'Worst 9s:'
        measures = ['GrossVP', 'Sc', 'NetVP', 'Stableford']

    records_data = []

    for measure in measures:
        if measure == 'Stableford':
            tied_worst_records = data_source.nsmallest(1, measure, keep='all')
        else:
            tied_worst_records = data_source.nlargest(1, measure, keep='all')

        if not tied_worst_records.empty:
            for idx, record_row in tied_worst_records.iterrows():
                if record_type == 'teg':
                    when = f"{record_row['TEG']} ({record_row['Area']}, {record_row['Year']})"
                else:
                    if 'Date' in record_row and pd.notna(record_row['Date']):
                        # FIXED: Removed the secondary .strftime() call that would cause a crash
                        month_year = format_date_for_scorecard(record_row['Date'], output_format='%b %Y')
                    else:
                        month_year = str(record_row['Year'])
                    
                    if record_type == 'round':
                        when = f"{record_row['TEG']} Rd {record_row['Round']} ({record_row['Course']}, {month_year})"
                    else:  # frontback
                        when = f"{record_row['TEG']} Rd {record_row['Round']} {record_row['FrontBack']} ({record_row['Course']}, {month_year})"

                records_data.append({
                    table_title: WORST_MEASURE_TITLES[measure],
                    '': format_record_value(record_row[measure], measure),
                    ' ': record_row['Player'],
                    '  ': when
                })

    return pd.DataFrame(records_data)


def prepare_streak_records_table(streak_data: pd.DataFrame, table_title: str) -> pd.DataFrame:
    """Prepares a streak records table with a title in the header row."""
    from teg_analysis.constants import PLAYER_DICT

    name_to_initials = {name: initials for initials, name in PLAYER_DICT.items()}
    records_data = []
    grouped = streak_data.groupby(['Streak Type', 'Record'])

    for (streak_type, record_value), group in grouped:
        num_holders = len(group)

        if num_holders >= 3:
            player_initials = []
            seen = set()
            for player_name in group['Player']:
                initials = name_to_initials.get(player_name, player_name)
                if initials not in seen:
                    player_initials.append(initials)
                    seen.add(initials)
            initials_str = ' / '.join(player_initials)

            records_data.append({
                table_title: streak_type,
                '': record_value,
                ' ': f'({num_holders} times)',
                '  ': initials_str
            })
        else:
            for _, row in group.iterrows():
                records_data.append({
                    table_title: streak_type,
                    '': row['Record'],
                    ' ': row['Player'],
                    '  ': row['When']
                })

    return pd.DataFrame(records_data)


def prepare_score_count_records_table(all_data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Prepares score count records tables."""
    from teg_analysis.analysis.scoring import count_scores_by_player

    score_categories = {
        'Eagles': [-2],
        'Birdies': [-2, -1],
        'Pars': [-2, -1, 0],
        'TBPs': [3, 4, 5, 6, 7, 8, 9, 10]
    }

    best_records_data = []
    worst_records_data = []

    for category, scores in score_categories.items():
        teg_record_count = 0
        teg_record_holders = []

        for teg_num, group in all_data.groupby('TEGNum'):
            score_counts = count_scores_by_player(group, field='GrossVP')
            player_cols = [col for col in score_counts.columns]

            for player in player_cols:
                total = 0
                for score in scores:
                    if score in score_counts.index:
                        total += score_counts.loc[score, player]

                if total > teg_record_count:
                    teg_record_count = total
                    teg_record_holders = [(player, teg_num, group)]
                elif total == teg_record_count and total > 0:
                    teg_record_holders.append((player, teg_num, group))

        if teg_record_count > 0:
            if len(teg_record_holders) >= 3:
                player_initials = []
                seen = set()
                for p in teg_record_holders:
                    if p[0] not in seen:
                        player_initials.append(p[0])
                        seen.add(p[0])
                initials_str = ' / '.join(player_initials)

                record_data = {
                    'Best Score Counts:' if category != 'TBPs' else 'Worst Score Counts:': f"Most {category} in a TEG",
                    '': str(teg_record_count),
                    ' ': '→',
                    '  ': initials_str
                }
                if category == 'TBPs':
                    worst_records_data.append(record_data)
                else:
                    best_records_data.append(record_data)
            else:
                for player, teg_num, group in teg_record_holders:
                    teg_name = f"TEG {teg_num}"
                    area = group['Area'].iloc[0] if 'Area' in group.columns else ''
                    year = group['Year'].iloc[0] if 'Year' in group.columns else ''
                    when = f"{teg_name} ({area}, {year})"

                    record_data = {
                        'Best Score Counts:' if category != 'TBPs' else 'Worst Score Counts:': f"Most {category} in a TEG",
                        '': str(teg_record_count),
                        ' ': player,
                        '  ': when
                    }
                    if category == 'TBPs':
                        worst_records_data.append(record_data)
                    else:
                        best_records_data.append(record_data)

        round_record_count = 0
        round_record_holders = []

        for (teg_num, round_num), group in all_data.groupby(['TEGNum', 'Round']):
            score_counts = count_scores_by_player(group, field='GrossVP')
            player_cols = [col for col in score_counts.columns]

            for player in player_cols:
                total = 0
                for score in scores:
                    if score in score_counts.index:
                        total += score_counts.loc[score, player]

                if total > round_record_count:
                    round_record_count = total
                    round_record_holders = [(player, teg_num, round_num, group)]
                elif total == round_record_count and total > 0:
                    round_record_holders.append((player, teg_num, round_num, group))

        if round_record_count > 0:
            if len(round_record_holders) >= 3:
                player_initials = []
                seen = set()
                for p in round_record_holders:
                    if p[0] not in seen:
                        player_initials.append(p[0])
                        seen.add(p[0])
                initials_str = ' / '.join(player_initials)

                record_data = {
                    'Best Score Counts:' if category != 'TBPs' else 'Worst Score Counts:': f"Most {category} in a Round",
                    '': str(round_record_count),
                    ' ': '→',
                    '  ': initials_str
                }
                if category == 'TBPs':
                    worst_records_data.append(record_data)
                else:
                    best_records_data.append(record_data)
            else:
                for player, teg_num, round_num, group in round_record_holders:
                    teg_name = f"TEG {teg_num}"
                    course = group['Course'].iloc[0] if 'Course' in group.columns else ''

                    if 'Date' in group.columns and pd.notna(group['Date'].iloc[0]):
                        # FIXED: Swapped raw pd.to_datetime logic out for the clean format helper
                        month_year = format_date_for_scorecard(group['Date'].iloc[0], output_format='%b %Y')
                    else:
                        month_year = str(group['Year'].iloc[0]) if 'Year' in group.columns else ''

                    when = f"{teg_name} Rd {round_num} ({course}, {month_year})"

                    record_data = {
                        'Best Score Counts:' if category != 'TBPs' else 'Worst Score Counts:': f"Most {category} in a Round",
                        '': str(round_record_count),
                        ' ': player,
                        '  ': when
                    }
                    if category == 'TBPs':
                        worst_records_data.append(record_data)
                    else:
                        best_records_data.append(record_data)

    best_df = pd.DataFrame(best_records_data) if best_records_data else pd.DataFrame()
    worst_df = pd.DataFrame(worst_records_data) if worst_records_data else pd.DataFrame()

    return best_df, worst_df