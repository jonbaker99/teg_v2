"""
Display helper functions for Records pages.

This module contains reusable functions for:
- Value formatting (scores, vs-par displays)
- Data preparation for display
- Constants and mappings for consistent labeling
"""

import pandas as pd


# === CONSTANTS ===
MEASURE_TITLES = {
    'Sc': "Best Score",
    'GrossVP': "Best Gross", 
    'NetVP': "Best Net",
    'Stableford': "Best Stableford"
}


# === FORMATTING FUNCTIONS ===

def format_record_value(value, measure):
    """
    Format a record value for display based on measure type.
    
    Args:
        value: The numeric value to format
        measure: The measure type ('GrossVP', 'NetVP', 'Sc', 'Stableford')
    
    Returns:
        str: Formatted value (e.g., "+3", "-2", "85")
        
    Example:
        format_record_value(3, 'GrossVP') -> "+3"
        format_record_value(-2, 'NetVP') -> "-2" 
        format_record_value(85, 'Sc') -> "85"
    """
    if measure in ['GrossVP', 'NetVP']:
        return f"{int(value):+}"  # Shows +3 or -2
    else:
        return str(int(value))    # Shows 85


def prepare_records_display(best_records, record_type):
    """
    Prepare record data for display by formatting columns and selecting relevant fields.

    Args:
        best_records (pd.DataFrame): Raw record data from database
        record_type (str): Type of record - 'teg', 'round', or 'frontback'

    Returns:
        pd.DataFrame: Formatted data ready for display

    Purpose:
        Different record types need different column combinations:
        - TEG records: Player, TEG, Year
        - Round records: Player, Course, TEG+Round, Year
        - 9-hole records: Player, Course, TEG+Round+FrontBack, Year
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


def prepare_records_table(data_source, record_type):
    """
    Prepare a consolidated records table showing all measures for a given record type.

    Args:
        data_source (pd.DataFrame): Ranked data (teg, round, or frontback)
        record_type (str): Type of record - 'teg', 'round', or 'frontback'

    Returns:
        pd.DataFrame: Table with custom header based on record type

    Purpose:
        Creates a unified table showing best records across all measures for easy comparison.
        Replaces individual stat cards with a consolidated tabular view.
    """
    from utils import get_best

    # Define table title based on record type
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
        # Get all records tied for best (rank 1) for this measure
        rank_column = f'Rank_within_all_{measure}'

        if rank_column in data_source.columns:
            # Get all records with rank 1 (includes ties)
            tied_records = data_source[data_source[rank_column] == 1]
        else:
            # Fallback to old method if ranking column doesn't exist
            tied_records = get_best(data_source, measure_to_use=measure, top_n=1)

        if not tied_records.empty:
            # Handle multiple tied records
            for idx, record_row in tied_records.iterrows():
                # Format the "When" column based on record type
                if record_type == 'teg':
                    when = f"{record_row['TEG']} ({record_row['Area']}, {record_row['Year']})"
                elif record_type == 'round':
                    # Format date to get month/year
                    if 'Date' in record_row and pd.notna(record_row['Date']):
                        try:
                            date_obj = pd.to_datetime(record_row['Date'])
                            month_year = date_obj.strftime('%b %Y')
                        except:
                            month_year = str(record_row['Year'])
                    else:
                        month_year = str(record_row['Year'])
                    when = f"{record_row['TEG']} Rd {record_row['Round']} ({record_row['Course']}, {month_year})"
                else:  # frontback
                    # Format date to get month/year
                    if 'Date' in record_row and pd.notna(record_row['Date']):
                        try:
                            date_obj = pd.to_datetime(record_row['Date'])
                            month_year = date_obj.strftime('%b %Y')
                        except:
                            month_year = str(record_row['Year'])
                    else:
                        month_year = str(record_row['Year'])
                    when = f"{record_row['TEG']} Rd {record_row['Round']} {record_row['FrontBack']} ({record_row['Course']}, {month_year})"

                records_data.append({
                    table_title: MEASURE_TITLES[measure],
                    '': format_record_value(record_row[measure], measure),
                    ' ': record_row['Player'],
                    '  ': when
                })

    return pd.DataFrame(records_data)


def prepare_streak_records_table(streak_data, table_title):
    """
    Prepare a streak records table with title in header row.
    Consolidates records with 3+ holders into a single row.

    Args:
        streak_data (pd.DataFrame): Streak data with columns ['Streak Type', 'Record', 'Player', 'When']
        table_title (str): Title for the table (e.g., 'Best Streaks:', 'Worst Streaks:')

    Returns:
        pd.DataFrame: Table formatted for records page display with title in header

    Purpose:
        Formats streak records to match the style of other records tables on the page.
        When 3+ players share the same record, consolidates them into one row showing player initials.
    """
    from utils import PLAYER_DICT

    # Create reverse lookup: full name to initials
    name_to_initials = {name: initials for initials, name in PLAYER_DICT.items()}

    records_data = []

    # Group by Streak Type and Record to find shared records
    grouped = streak_data.groupby(['Streak Type', 'Record'])

    for (streak_type, record_value), group in grouped:
        num_holders = len(group)

        if num_holders >= 3:
            # Consolidate into one row with player initials (deduplicated, maintaining order)
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
            # Show each record separately (1-2 holders)
            for _, row in group.iterrows():
                records_data.append({
                    table_title: streak_type,
                    '': row['Record'],
                    ' ': row['Player'],
                    '  ': row['When']
                })

    return pd.DataFrame(records_data)


def prepare_score_count_records_table(all_data):
    """
    Prepare score count records tables for best (Eagles, Birdies, Pars) and worst (TBPs).

    Args:
        all_data (pd.DataFrame): All tournament data

    Returns:
        tuple: (best_records_df, worst_records_df) formatted for records page display

    Purpose:
        Finds all-time records for score counts:
        - Best: Most Eagles, Birdies (or better), Pars (or better) in TEG/Round
        - Worst: Most TBPs in TEG/Round
    """
    from helpers.score_count_processing import count_scores_by_player

    # Define score categories
    score_categories = {
        'Eagles': [-2],
        'Birdies': [-2, -1],
        'Pars': [-2, -1, 0],
        'TBPs': [3, 4, 5, 6, 7, 8, 9, 10]
    }

    best_records_data = []
    worst_records_data = []

    # Process each category
    for category, scores in score_categories.items():
        # Find records at TEG level
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

        # Add TEG records
        if teg_record_count > 0:
            # If 3+ holders, consolidate into one row
            if len(teg_record_holders) >= 3:
                # Get player initials (deduplicated, maintaining order)
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
                # Show each record separately (1-2 holders)
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

        # Find records at Round level
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

        # Add Round records
        if round_record_count > 0:
            # If 3+ holders, consolidate into one row
            if len(round_record_holders) >= 3:
                # Get player initials (deduplicated, maintaining order)
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
                # Show each record separately (1-2 holders)
                for player, teg_num, round_num, group in round_record_holders:
                    teg_name = f"TEG {teg_num}"
                    course = group['Course'].iloc[0] if 'Course' in group.columns else ''

                    # Format date
                    if 'Date' in group.columns and pd.notna(group['Date'].iloc[0]):
                        try:
                            date_obj = pd.to_datetime(group['Date'].iloc[0])
                            month_year = date_obj.strftime('%b %Y')
                        except:
                            month_year = str(group['Year'].iloc[0]) if 'Year' in group.columns else ''
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


def prepare_worst_records_table(data_source, record_type):
    """
    Prepare a consolidated worst records table showing all measures for a given record type.

    Args:
        data_source (pd.DataFrame): Data source (teg, round, or frontback data)
        record_type (str): Type of record - 'teg', 'round', or 'frontback'

    Returns:
        pd.DataFrame: Table with custom header based on record type

    Purpose:
        Creates a unified table showing worst records across all measures for easy comparison.
        Replaces individual stat cards with a consolidated tabular view (worst performance version).
    """
    from utils import get_worst

    # Define worst measure titles
    WORST_MEASURE_TITLES = {
        'Sc': "Worst Score",
        'GrossVP': "Worst Gross",
        'NetVP': "Worst Net",
        'Stableford': "Worst Stableford"
    }

    # Define table title based on record type
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
        # Get all records tied for worst for this measure
        if measure == 'Stableford':
            # For Stableford, lower is worse
            tied_worst_records = data_source.nsmallest(1, measure, keep='all')
        else:
            # For other measures, higher is worse
            tied_worst_records = data_source.nlargest(1, measure, keep='all')

        if not tied_worst_records.empty:
            # Handle multiple tied records
            for idx, record_row in tied_worst_records.iterrows():
                # Format the "When" column based on record type
                if record_type == 'teg':
                    when = f"{record_row['TEG']} ({record_row['Area']}, {record_row['Year']})"
                elif record_type == 'round':
                    # Format date to get month/year
                    if 'Date' in record_row and pd.notna(record_row['Date']):
                        try:
                            date_obj = pd.to_datetime(record_row['Date'])
                            month_year = date_obj.strftime('%b %Y')
                        except:
                            month_year = str(record_row['Year'])
                    else:
                        month_year = str(record_row['Year'])
                    when = f"{record_row['TEG']} Rd {record_row['Round']} ({record_row['Course']}, {month_year})"
                else:  # frontback
                    # Format date to get month/year
                    if 'Date' in record_row and pd.notna(record_row['Date']):
                        try:
                            date_obj = pd.to_datetime(record_row['Date'])
                            month_year = date_obj.strftime('%b %Y')
                        except:
                            month_year = str(record_row['Year'])
                    else:
                        month_year = str(record_row['Year'])
                    when = f"{record_row['TEG']} Rd {record_row['Round']} {record_row['FrontBack']} ({record_row['Course']}, {month_year})"

                records_data.append({
                    table_title: WORST_MEASURE_TITLES[measure],
                    '': format_record_value(record_row[measure], measure),
                    ' ': record_row['Player'],
                    '  ': when
                })

    return pd.DataFrame(records_data)