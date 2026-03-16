"""Aggregation and data grouping functions.

This module provides data aggregation functions for the TEG analysis system,
including TEG-level, round-level, and 9-hole aggregation, plus winner calculations.
"""


import logging
import pandas as pd
from typing import List

from teg_analysis.constants import TEG_ROUNDS, TEGNUM_ROUNDS, TEG_OVERRIDES

logger = logging.getLogger(__name__)


# === LOOKUP FUNCTIONS ===

def get_teg_rounds(TEG: str) -> int:
    """Return the number of rounds for a given TEG.

    If the TEG is not found in the dictionary, return 4 as the default value.

    Parameters:
        TEG (str): The TEG identifier (e.g., 'TEG 1', 'TEG 2', etc.)

    Returns:
        int: The total number of rounds for the given TEG, defaulting to 4 if not found.
    """
    return TEG_ROUNDS.get(TEG, 4)


def get_tegnum_rounds(TEGNum: int) -> int:
    """Return the number of rounds for a given TEG by number.

    If the TEG is not found in the dictionary, return 4 as the default value.

    Parameters:
        TEGNum (int): The TEG number (e.g., 1, 2, 3, etc.)

    Returns:
        int: The total number of rounds for the given TEG, defaulting to 4 if not found.
    """
    return TEGNUM_ROUNDS.get(TEGNum, 4)


# === WINNER CALCULATIONS ===

def get_teg_winners(df: pd.DataFrame) -> pd.DataFrame:
    """Generate TEG winners, best net, gross, and worst net by TEG.

    Parameters:
        df (pd.DataFrame): DataFrame containing the golf data.

    Returns:
        pd.DataFrame: DataFrame summarizing TEG winners.
    """
    # Import scoring function here to avoid circular dependency
    from .scoring import get_net_competition_measure

    logger.info("Calculating TEG winners.")

    # Group by 'TEGNum' and 'Player', and calculate the sum for each player in each TEG
    grouped = df.groupby(['TEGNum', 'Player']).agg({
        'GrossVP': 'sum',
        'NetVP': 'sum',
        'Stableford': 'sum'
    }).reset_index()

    results = []

    # Get unique TEG numbers
    for teg_num in df['TEGNum'].unique():
        # Filter data for the current TEG
        teg_data = grouped[grouped['TEGNum'] == teg_num]

        # Determine which measure to use for net competition based on TEG number
        net_measure = get_net_competition_measure(teg_num)

        # Identify the best gross, best net, and worst net players
        best_gross_player = teg_data.loc[teg_data['GrossVP'].idxmin(), 'Player']

        if net_measure == 'NetVP':
            # For TEG 1-5: Lower NetVP is better (closer to or under par)
            best_net_player = teg_data.loc[teg_data['NetVP'].idxmin(), 'Player']
            worst_net_player = teg_data.loc[teg_data['NetVP'].idxmax(), 'Player']
        else:
            # For TEG 6+: Higher Stableford is better
            best_net_player = teg_data.loc[teg_data['Stableford'].idxmax(), 'Player']
            worst_net_player = teg_data.loc[teg_data['Stableford'].idxmin(), 'Player']

        # Apply manual overrides if any
        teg_label = f"TEG {teg_num}"
        overrides = TEG_OVERRIDES.get(teg_label, {})
        best_gross_player = overrides.get('Best Gross', best_gross_player)
        best_net_player = overrides.get('Best Net', best_net_player)
        worst_net_player = overrides.get('Worst Net', worst_net_player)

        # Append the results
        results.append({
            'TEGNum': teg_num,
            'TEG': teg_label,
            'Best Gross': best_gross_player,
            'Best Net': best_net_player,
            'Worst Net': worst_net_player
        })

    # Convert results to a DataFrame
    result_df = pd.DataFrame(results).sort_values(by='TEGNum')

    # Merge with year data from df
    teg_years = df[['TEGNum', 'Year']].drop_duplicates()
    result_df = result_df.merge(teg_years, on='TEGNum', how='left')

    # Rename columns
    result_df.rename(columns={
        'Best Net': 'TEG Trophy',
        'Best Gross': 'Green Jacket',
        'Worst Net': 'HMM Wooden Spoon',
        'Year': 'Year'
    }, inplace=True)

    # Select and order columns
    result_df = result_df[['TEG', 'Year', 'TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon']]

    logger.info("TEG winners calculated.")
    return result_df


# === AGGREGATION ENGINE ===

def list_fields_by_aggregation_level(df):
    """Determine which fields are unique at each aggregation level.

    Args:
        df (pd.DataFrame): DataFrame to analyze.

    Returns:
        dict: Dictionary mapping aggregation levels to unique fields.
    """
    # Define the levels of aggregation
    aggregation_levels = {
        'Player': ['Player'],
        'TEG': ['Player', 'TEG'],
        'Round': ['Player', 'TEG', 'Round'],
        'FrontBack': ['Player', 'TEG', 'Round', 'FrontBack'],
    }

    # Dictionary to hold fields unique at each level
    fields_by_level = {level: [] for level in aggregation_levels}

    # For each field in the dataframe, determine its uniqueness level
    for col in df.columns:
        for level, group_fields in aggregation_levels.items():
            # Check if the field is unique at this level
            if df.groupby(group_fields)[col].nunique().max() == 1:
                fields_by_level[level].append(col)
                break  # Stop after finding the lowest level of uniqueness

    return fields_by_level


def aggregate_data(data: pd.DataFrame, aggregation_level: str, measures: List[str] = None, additional_group_fields: List[str] = None) -> pd.DataFrame:
    """Generalized aggregation function with dynamic level of aggregation and additional group fields.

    Parameters:
        data (pd.DataFrame): The DataFrame to aggregate.
        aggregation_level (str): The level of aggregation ('Player', 'TEG', 'Round', 'FrontBack', 'Hole').
        measures (List[str], optional): List of measure columns to aggregate. Defaults to standard measures.
        additional_group_fields (List[str], optional): Additional fields to include in the grouping. Defaults to None.

    Returns:
        pd.DataFrame: Aggregated DataFrame.
    """
    # Set default measures if none provided
    if measures is None:
        measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']

    # Get the fields related to each aggregation level
    fields_by_level = list_fields_by_aggregation_level(data)

    # Define the hierarchy of aggregation levels
    aggregation_hierarchy = ['Player', 'TEG', 'Round', 'FrontBack', 'Hole']

    if aggregation_level not in aggregation_hierarchy:
        raise ValueError(f"Invalid aggregation level: '{aggregation_level}'. Choose from: {aggregation_hierarchy}")

    # Determine which fields to include based on the selected aggregation level
    idx = aggregation_hierarchy.index(aggregation_level)
    group_columns = []

    # Add all fields from the selected aggregation level and higher levels
    for level in aggregation_hierarchy[:idx + 1]:
        group_columns.extend(fields_by_level[level])

    # Add additional group fields if provided
    if additional_group_fields:
        if isinstance(additional_group_fields, str):
            additional_group_fields = [additional_group_fields]  # Wrap in a list if it's a string
        group_columns.extend(additional_group_fields)

    # Ensure group columns are unique
    group_columns = list(set(group_columns))

    # Check if all group_columns are present in the DataFrame
    missing_columns = [col for col in group_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"Missing columns in the DataFrame: {missing_columns}")

    # Perform aggregation
    aggregated_df = data.groupby(group_columns, as_index=False)[measures].sum()
    aggregated_df = aggregated_df.sort_values(by=group_columns)

    return aggregated_df


# === CACHED AGGREGATION FUNCTIONS ===

def get_complete_teg_data():
    """Get complete TEG-level data (excluding TEG 50 and incomplete TEGs).

    Returns:
        pd.DataFrame: TEG-level aggregated data.
    """
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=True)
    aggregated_data = aggregate_data(all_data, 'TEG')
    return aggregated_data


def get_teg_data_inc_in_progress():
    """Get TEG-level data including in-progress TEGs.

    Returns:
        pd.DataFrame: TEG-level aggregated data including incomplete TEGs.
    """
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'TEG')
    return aggregated_data


def get_round_data(ex_50=True, ex_incomplete=False):
    """Get round-level aggregated data.

    Args:
        ex_50 (bool): Exclude TEG 50 if True.
        ex_incomplete (bool): Exclude incomplete TEGs if True.

    Returns:
        pd.DataFrame: Round-level aggregated data.
    """
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=ex_50, exclude_incomplete_tegs=ex_incomplete)
    aggregated_data = aggregate_data(all_data, 'Round')
    return aggregated_data


def get_9_data():
    """Get 9-hole (front/back) aggregated data.

    Returns:
        pd.DataFrame: 9-hole aggregated data.
    """
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'FrontBack')
    return aggregated_data


def get_Pl_data():
    """Get player-level aggregated data.

    Returns:
        pd.DataFrame: Player-level aggregated data.
    """
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'Player')
    return aggregated_data


# === HISTORY DATA PROCESSING (from helpers/history_data_processing.py) ===

def process_winners_for_charts(winners_df: pd.DataFrame) -> dict:
    """Processes winners data to create datasets for charts.

    This function transforms the winners' data into a format suitable for bar
    charts and tables, counting the wins per player for each competition.

    Args:
        winners_df (pd.DataFrame): A DataFrame with raw winners data.

    Returns:
        dict: A dictionary containing sorted DataFrames for each competition
        and the maximum number of wins.
    """
    # Clean asterisks from winner names (used for footnotes)
    clean_winners = winners_df.replace(r'\*', '', regex=True)

    # Melt the DataFrame to long format for easier grouping
    melted_winners = pd.melt(
        clean_winners,
        id_vars=['TEG'],
        value_vars=['TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon'],
        var_name='Competition',
        value_name='Player'
    )

    # Count wins per player per competition
    player_wins = melted_winners.groupby(['Player', 'Competition']).size().unstack(fill_value=0)
    player_wins = player_wins[['TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon']]
    player_wins.columns = ['Trophy', 'Jacket', 'Spoon']

    # Create sorted dataframes for each competition
    trophy_sorted = player_wins.sort_values(by='Trophy', ascending=False).reset_index()
    jacket_sorted = player_wins.sort_values(by='Jacket', ascending=False).reset_index()
    spoon_sorted = player_wins.sort_values(by='Spoon', ascending=False).reset_index()

    # Find maximum wins for chart scaling
    max_wins = max(
        trophy_sorted['Trophy'].max(),
        jacket_sorted['Jacket'].max(),
        spoon_sorted['Spoon'].max()
    )

    return {
        'trophy_sorted': trophy_sorted,
        'jacket_sorted': jacket_sorted,
        'spoon_sorted': spoon_sorted,
        'max_wins': max_wins
    }


def calculate_trophy_jacket_doubles(winners_df: pd.DataFrame) -> tuple:
    """Calculates players who won both the Trophy and Green Jacket in the same TEG.

    This function identifies the rare achievement of winning both main
    competitions in a single TEG.

    Args:
        winners_df (pd.DataFrame): A DataFrame with winners data.

    Returns:
        tuple: A tuple containing:
            - doubles_df (pd.DataFrame): A DataFrame showing player doubles.
            - count (int): The total number of doubles.
    """
    # Clean asterisks from winner names
    clean_winners = winners_df.replace(r'\*', '', regex=True)

    # Find TEGs where same player won both Trophy and Green Jacket
    same_player_both = clean_winners[clean_winners['TEG Trophy'] == clean_winners['Green Jacket']]

    # Count doubles per player
    player_doubles = same_player_both['TEG Trophy'].value_counts().reset_index()
    player_doubles.columns = ['Player', 'Doubles']
    player_doubles = player_doubles.sort_values(by='Doubles', ascending=False)

    return player_doubles, same_player_both.shape[0]


def prepare_history_table_display(winners_df: pd.DataFrame) -> pd.DataFrame:
    """Prepares winners data for the historical display table.

    This function creates a compact historical view by combining the TEG name
    and year, and adding the area for each TEG.

    Args:
        winners_df (pd.DataFrame): A DataFrame with raw winners data.

    Returns:
        pd.DataFrame: A formatted DataFrame with a combined TEG(Year) column
        and an Area column.
    """
    from teg_analysis.io.file_operations import read_file

    # Get constants to access ROUND_INFO_CSV
    from utils import ROUND_INFO_CSV

    # Create a copy to avoid modifying original
    display_winners = winners_df.copy()

    # Get unique TEG-Area combinations from round_info
    round_info = read_file(ROUND_INFO_CSV)
    teg_areas = round_info[['TEG', 'Area']].drop_duplicates()

    # Join area data to winners table
    display_winners = display_winners.merge(teg_areas, on='TEG', how='left')

    # Combine TEG and Year into single display column
    display_winners["TEG"] = (
        display_winners['TEG'].astype(str) + " (" +
        display_winners['Year'].astype(str) + ")"
    )

    # Remove separate Year column and reorder columns
    display_winners = display_winners.drop(columns=['Year'])

    # Reorder columns: TEG, Area, then competition winners
    competition_cols = [col for col in display_winners.columns if col not in ['TEG', 'Area']]
    column_order = ['TEG', 'Area'] + competition_cols
    display_winners = display_winners[column_order]

    return display_winners


def get_eagles_data(all_data: pd.DataFrame) -> pd.DataFrame:
    """Finds all Eagles (-2 gross vs par) scored in TEG history.

    Args:
        all_data (pd.DataFrame): The complete scoring data.

    Returns:
        pd.DataFrame: A DataFrame of Eagles data with Player, Date, Course,
        and Hole columns.
    """
    # Find all Eagles: Gross score is 2 under par
    eagles = all_data[all_data['GrossVP'] == -2.0].copy()

    if eagles.empty:
        return pd.DataFrame(columns=['Player', 'Date', 'Course', 'Hole'])

    # Create formatted hole information as "TEG X | Rd X | Hole X"
    eagles['Hole'] = eagles['TEG'].astype(str) + ' | Rd ' + eagles['Round'].astype(str) + ' | Hole ' + eagles['Hole'].astype(str)

    # Select and order columns for display
    eagles_display = eagles[['Player', 'Date', 'Course', 'Hole', 'TEGNum']].copy()

    # Sort by TEG, Round, Hole (using original numeric values)
    eagles_display = eagles_display.sort_values(['TEGNum', 'Date'])

    # Remove TEGNum from final display
    eagles_display = eagles_display[['Player', 'Date', 'Course', 'Hole']]

    return eagles_display


def get_holes_in_one_data(all_data: pd.DataFrame) -> pd.DataFrame:
    """Finds all Holes in One scored in TEG history.

    Args:
        all_data (pd.DataFrame): The complete scoring data.

    Returns:
        pd.DataFrame: A DataFrame of Holes in One data with Player, Date,
        Course, and Hole columns.
    """
    # Find all Holes in One: Gross score is 1
    holes_in_one = all_data[all_data['Sc'] == 1.0].copy()

    if holes_in_one.empty:
        return pd.DataFrame(columns=['Player', 'Date', 'Course', 'Hole'])

    # Create formatted hole information as "TEG X | Rd X | Hole X"
    holes_in_one['Hole'] = holes_in_one['TEG'].astype(str) + ' | Rd ' + holes_in_one['Round'].astype(str) + ' | Hole ' + holes_in_one['Hole'].astype(str)

    # Select and order columns for display
    holes_in_one_display = holes_in_one[['Player', 'Date', 'Course', 'Hole', 'TEGNum']].copy()

    # Sort by TEG, Round, Hole (using original numeric values)
    holes_in_one_display = holes_in_one_display.sort_values(['TEGNum', 'Date'])

    # Remove TEGNum from final display
    holes_in_one_display = holes_in_one_display[['Player', 'Date', 'Course', 'Hole']]

    return holes_in_one_display

def get_incomplete_tegs() -> pd.DataFrame:
    """Finds TEGs that are in progress.

    This function identifies TEGs that have started but have not yet been
    completed, for display in the history table.

    Returns:
        pd.DataFrame: A DataFrame of incomplete TEG data with TEG, Year, and
        Area columns.
    """
    from utils import load_all_data, read_file, ROUND_INFO_CSV, exclude_incomplete_tegs_function
    
    # Load all data including incomplete TEGs
    all_data_with_incomplete = load_all_data(exclude_incomplete_tegs=False)
    
    # Load only complete data 
    complete_data = load_all_data(exclude_incomplete_tegs=True)
    
    # Find TEGs that exist in all data but not in complete data
    all_tegs = set(all_data_with_incomplete['TEGNum'].unique())
    complete_tegs = set(complete_data['TEGNum'].unique())
    incomplete_teg_nums = all_tegs - complete_tegs
    
    if not incomplete_teg_nums:
        return pd.DataFrame(columns=['TEG', 'Year', 'Area'])
    
    # Get metadata for incomplete TEGs from round_info
    round_info = read_file(ROUND_INFO_CSV)
    incomplete_tegs = round_info[round_info['TEGNum'].isin(incomplete_teg_nums)]
    
    # Get unique TEG entries (one row per TEG) - keep TEGNum for sorting
    incomplete_summary = incomplete_tegs[['TEGNum', 'TEG', 'Year', 'Area']].drop_duplicates()
    
    # Sort by TEGNum then drop it since we only need TEG, Year, Area for output
    incomplete_summary = incomplete_summary.sort_values('TEGNum')[['TEG', 'Year', 'Area']]
    
    return incomplete_summary


def get_future_tegs() -> pd.DataFrame:
    """Loads planned future TEGs that have not yet started.

    Returns:
        pd.DataFrame: A DataFrame of future TEG data with TEG, Year, and Area
        columns.
    """
    from utils import read_file
    
    try:
        # Try to load future TEGs from a dedicated file
        future_tegs = read_file('data/future_tegs.csv')
        # Convert Year column to integers to avoid decimal display
        future_tegs['Year'] = future_tegs['Year'].astype(int)
        return future_tegs[['TEG', 'Year', 'Area']].sort_values('Year')
    except Exception:
        # If no future TEGs file exists, return empty DataFrame
        return pd.DataFrame(columns=['TEG', 'Year', 'Area'])


def prepare_complete_history_table(winners_df: pd.DataFrame) -> pd.DataFrame:
    """Prepares a complete history table.

    This function includes completed, incomplete, and future TEGs in a single
    table for a comprehensive historical view.

    Args:
        winners_df (pd.DataFrame): A DataFrame of winners data from completed
            TEGs.

    Returns:
        pd.DataFrame: A complete history table with "TBC" entries for
        incomplete or future TEGs.
    """
    # Start with completed TEGs history
    completed_history = prepare_history_table_display(winners_df)
    
    # Get incomplete TEGs
    incomplete_tegs = get_incomplete_tegs()
    
    # Get future TEGs  
    future_tegs = get_future_tegs()
    
    # Get all TEG names that already exist in completed or incomplete data
    existing_tegs = set()
    
    # Add completed TEG names (extract from "TEG X (YYYY)" format)
    import re
    for teg_str in completed_history['TEG']:
        match = re.search(r'(TEG \d+)', teg_str)
        if match:
            existing_tegs.add(match.group(1))
    
    # Add incomplete TEG names
    if not incomplete_tegs.empty:
        existing_tegs.update(incomplete_tegs['TEG'].tolist())
    
    # Filter out future TEGs that already exist in the data
    if not future_tegs.empty:
        future_tegs = future_tegs[~future_tegs['TEG'].isin(existing_tegs)]
    
    # Combine incomplete and future TEGs (after filtering duplicates)
    pending_tegs = pd.concat([incomplete_tegs, future_tegs], ignore_index=True)
    
    if pending_tegs.empty:
        return completed_history
    
    # Create TBC entries for pending TEGs
    tbc_entries = []
    for _, row in pending_tegs.iterrows():
        tbc_entry = {
            'TEG': f"{row['TEG']} ({row['Year']})",
            'Area': row['Area'],
            'TEG Trophy': 'TBC',
            'Green Jacket': 'TBC', 
            'HMM Wooden Spoon': 'TBC'
        }
        tbc_entries.append(tbc_entry)
    
    # Convert to DataFrame
    tbc_df = pd.DataFrame(tbc_entries)
    
    # Combine completed and TBC entries
    complete_history = pd.concat([completed_history, tbc_df], ignore_index=True)
    
    # Sort by TEG number (extract from TEG name)
    def extract_teg_num(teg_str):
        try:
            # Extract number from "TEG X (YYYY)" format
            import re
            match = re.search(r'TEG (\d+)', teg_str)
            return int(match.group(1)) if match else 999
        except:
            return 999
    
    complete_history['_sort_order'] = complete_history['TEG'].apply(extract_teg_num)
    complete_history = complete_history.sort_values('_sort_order').drop('_sort_order', axis=1)

    return complete_history


# ============================================
#  TEG COMPLETENESS CHECKING FUNCTIONS
# ============================================

def check_winner_completeness() -> set:
    """Checks if the cached winners match the completed TEGs status.

    Returns:
        set: A set of TEG numbers that are completed but missing from the
        winners cache.
    """
    from utils import read_file

    try:
        # Load status files
        completed_tegs = read_file('data/completed_tegs.csv')
        cached_winners = read_file('data/teg_winners.csv')

        # Extract TEG numbers from both sources
        completed_teg_nums = set(completed_tegs['TEGNum']) if not completed_tegs.empty else set()

        # Extract TEG numbers from cached winners (from TEG column like "TEG 18")
        cached_teg_nums = set()
        if not cached_winners.empty:
            import re
            for teg_str in cached_winners['TEG']:
                match = re.search(r'TEG (\d+)', str(teg_str))
                if match:
                    cached_teg_nums.add(int(match.group(1)))

        # Identify missing winners
        missing_winners = completed_teg_nums - cached_teg_nums

        return missing_winners

    except Exception as e:
        print(f"Error checking winner completeness: {e}")
        return set()


# display_completeness_status() - MOVED TO streamlit/utils.py as UI wrapper
# Use check_winner_completeness() for the calculation logic


def calculate_and_save_missing_winners(missing_teg_nums: set) -> dict:
    """Calculates and saves the winners for a specific set of missing TEGs.

    Pure calculation function - returns results instead of showing UI.

    Args:
        missing_teg_nums (set): A set of TEG numbers to calculate winners for.

    Returns:
        dict: Results with keys:
            - 'new_winners': list of new winner dicts added
            - 'errors': list of error dicts {'teg': int, 'error': str}
            - 'warnings': list of warning messages
            - 'cache_clear_needed': bool

    Raises:
        ValueError: If no data available
    """
    import pandas as pd
    # Import from teg_analysis instead of utils to avoid circular dependency
    from ..io.file_operations import read_file, write_file
    from ..core.data_loader import load_all_data

    # Load all data (expensive operation)
    all_data = load_all_data()

    if all_data.empty:
        raise ValueError("No data available to calculate winners")

    # Load existing cached winners
    try:
        cached_winners = read_file('data/teg_winners.csv')
    except Exception:
        # Create empty DataFrame with correct structure
        cached_winners = pd.DataFrame(columns=['TEG', 'Year', 'Area', 'TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon'])

    # Calculate winners only for missing TEGs
    new_winners = []
    errors = []
    warnings = []

    for teg_num in missing_teg_nums:
        try:
            # Get TEG data
            teg_data = all_data[all_data['TEGNum'] == teg_num]
            if teg_data.empty:
                warnings.append(f"No data found for TEG {teg_num}")
                continue

            # Get TEG info from data
            teg_info = teg_data.iloc[0]
            teg_name = teg_info['TEG']
            year = teg_info['Year']
            area = teg_info['Area'] if 'Area' in teg_info else "Unknown"

            # Calculate winners using existing logic in this module
            winners_df = get_teg_winners(teg_data)

            if not winners_df.empty:
                # Get the row for this specific TEG
                teg_winners = winners_df[winners_df['TEG'] == teg_name]
                if not teg_winners.empty:
                    winner_row = teg_winners.iloc[0]
                    new_winner_row = {
                        'TEG': teg_name,
                        'Year': year,
                        'Area': area,
                        'TEG Trophy': winner_row.get('TEG Trophy', 'Unknown'),
                        'Green Jacket': winner_row.get('Green Jacket', 'Unknown'),
                        'HMM Wooden Spoon': winner_row.get('HMM Wooden Spoon', 'Unknown')
                    }
                    new_winners.append(new_winner_row)

        except Exception as e:
            errors.append({'teg': teg_num, 'error': str(e)})

    if new_winners:
        # Add new winners to cached data
        new_winners_df = pd.DataFrame(new_winners)
        updated_winners = pd.concat([cached_winners, new_winners_df], ignore_index=True)

        # Sort by Year to maintain order
        updated_winners = updated_winners.sort_values('Year')

        # Save updated winners
        write_file('data/teg_winners.csv', updated_winners)

        return {
            'new_winners': new_winners,
            'errors': errors,
            'warnings': warnings,
            'cache_clear_needed': True
        }
    else:
        warnings.append("No winners could be calculated for the missing TEGs")
        return {
            'new_winners': [],
            'errors': errors,
            'warnings': warnings,
            'cache_clear_needed': False
        }


def load_cached_winners() -> tuple[pd.DataFrame, set] or tuple[None, set]:
    """Loads cached winners and calculates any missing ones.

    Returns:
        tuple: A tuple containing:
            - winners_data (pd.DataFrame or None): The winners data, or None
              if the cached file does not exist.
            - missing_teg_nums (set): A set of TEG numbers for which winners
              were missing.
    """
    import pandas as pd
    from ..io.file_operations import read_file
    from ..core.data_loader import load_all_data

    try:
        # Try to load cached winners
        cached_winners = read_file('data/teg_winners.csv')

        # Check for missing winners using existing function
        missing = check_winner_completeness()

        # If no missing winners, return cached data as before
        if not missing:
            cached_winners["TEG"] = (
                cached_winners['TEG'].astype(str) + " (" +
                cached_winners['Year'].astype(str) + ")"
            )
            cached_winners = cached_winners.drop(columns=['Year'])
            return cached_winners, set()

        # Calculate missing winners and append to display
        all_data = load_all_data()
        for teg_num in missing:
            try:
                teg_data = all_data[all_data['TEGNum'] == teg_num]
                if not teg_data.empty:
                    winners_df = get_teg_winners(teg_data)
                    if not winners_df.empty:
                        # Get winner info for this TEG
                        teg_info = teg_data.iloc[0]
                        winner_row = winners_df.iloc[0]
                        new_row = {
                            'TEG': teg_info['TEG'],
                            'Year': teg_info['Year'],
                            'Area': teg_info['Area'],
                            'TEG Trophy': winner_row.get('TEG Trophy', 'Unknown'),
                            'Green Jacket': winner_row.get('Green Jacket', 'Unknown'),
                            'HMM Wooden Spoon': winner_row.get('HMM Wooden Spoon', 'Unknown')
                        }
                        cached_winners = pd.concat([cached_winners, pd.DataFrame([new_row])], ignore_index=True)
            except Exception as e:
                print(f"Error calculating winners for TEG {teg_num}: {e}")

        # Format for display consistency
        cached_winners["TEG"] = (
            cached_winners['TEG'].astype(str) + " (" +
            cached_winners['Year'].astype(str) + ")"
        )
        cached_winners = cached_winners.drop(columns=['Year'])

        return cached_winners, missing

    except Exception as e:
        # If cached file doesn't exist or has issues, return None
        print(f"Could not load cached winners: {e}")
        return None, set()


def prepare_complete_history_table_fast(cached_winners_df: pd.DataFrame = None) -> pd.DataFrame:
    """Prepares a complete history table using cached winners data.

    This is a faster version of `prepare_complete_history_table` that uses
    cached data when available.

    Args:
        cached_winners_df (pd.DataFrame, optional): Pre-loaded cached winners
            data. Defaults to None.

    Returns:
        pd.DataFrame: A complete history table with "TBC" entries for
        incomplete or future TEGs.
    """

    # Try to use provided cached data, or load it
    if cached_winners_df is None:
        cached_winners_df = load_cached_winners()

    # If no cached data available, fall back to calculation
    if cached_winners_df is None:
        print("No cached winners data available, falling back to calculation...")
        from utils import load_all_data, get_teg_winners
        all_data = load_all_data(exclude_incomplete_tegs=True, exclude_teg_50=True)
        winners_with_year = get_teg_winners(all_data)
        completed_history = prepare_history_table_display(winners_with_year)
    else:
        completed_history = cached_winners_df.copy()

    # Get future TEGs
    future_tegs = get_future_tegs()

    # Get all TEG names that already exist in completed data
    existing_tegs = set()

    # Add completed TEG names (extract from "TEG X (YYYY)" format)
    import re
    for teg_str in completed_history['TEG']:
        match = re.search(r'(TEG \d+)', teg_str)
        if match:
            existing_tegs.add(match.group(1))

    # Filter out future TEGs that already exist in the data
    if not future_tegs.empty:
        future_tegs = future_tegs[~future_tegs['TEG'].isin(existing_tegs)]

    if future_tegs.empty:
        return completed_history

    # Create TBC entries for future TEGs
    tbc_entries = []
    for _, row in future_tegs.iterrows():
        tbc_entry = {
            'TEG': f"{row['TEG']} ({row['Year']})",
            'Area': row['Area'],
            'TEG Trophy': 'TBC',
            'Green Jacket': 'TBC',
            'HMM Wooden Spoon': 'TBC'
        }
        tbc_entries.append(tbc_entry)

    # Convert to DataFrame
    tbc_df = pd.DataFrame(tbc_entries)

    # Combine completed and TBC entries
    complete_history = pd.concat([completed_history, tbc_df], ignore_index=True)

    # Sort by TEG number (extract from TEG name)
    def extract_teg_num(teg_str):
        try:
            # Extract number from "TEG X (YYYY)" format
            import re
            match = re.search(r'TEG (\d+)', teg_str)
            return int(match.group(1)) if match else 999
        except:
            return 999

    complete_history['_sort_order'] = complete_history['TEG'].apply(extract_teg_num)
    complete_history = complete_history.sort_values('_sort_order').drop('_sort_order', axis=1)

    return complete_history


# ============================================
#  TEG COMPLETENESS CHECKING FUNCTIONS
# ============================================

def check_winner_completeness():
    """
    Check if cached winners match completed TEGs status.

    Returns:
        set: Set of TEG numbers that are completed but missing from winners cache
    """
    from utils import read_file

    try:
        # Load status files
        completed_tegs = read_file('data/completed_tegs.csv')
        cached_winners = read_file('data/teg_winners.csv')

        # Extract TEG numbers from both sources
        completed_teg_nums = set(completed_tegs['TEGNum']) if not completed_tegs.empty else set()

        # Extract TEG numbers from cached winners (from TEG column like "TEG 18")
        cached_teg_nums = set()
        if not cached_winners.empty:
            import re
            for teg_str in cached_winners['TEG']:
                match = re.search(r'TEG (\d+)', str(teg_str))
                if match:
                    cached_teg_nums.add(int(match.group(1)))

        # Identify missing winners
        missing_winners = completed_teg_nums - cached_teg_nums

        return missing_winners

    except Exception as e:
        print(f"Error checking winner completeness: {e}")
        return set()


# DUPLICATE FUNCTIONS REMOVED - see lines 672-776 for kept versions
# display_completeness_status() - UI wrapper moved to streamlit/utils.py
# calculate_and_save_missing_winners() - Pure version above (line 676)


# === MIGRATED SECTION ===

"""Data processing functions for best TEGs and rounds analysis.

This module contains functions for processing ranked TEG and round data,
creating performance tables with proper formatting, and handling measure name
mappings for the user interface.
"""


import pandas as pd


def get_measure_name_mappings() -> tuple[dict, dict]:
    """Gets mappings between user-friendly and internal measure names.

    This function provides a consistent way to map between the display names
    used in the user interface (e.g., 'Gross') and the internal column names
    used in the data (e.g., 'GrossVP').

    Returns:
        tuple: A tuple containing two dictionaries:
            - name_mapping (dict): Maps user-friendly names to internal names.
            - inverted_mapping (dict): Maps internal names to user-friendly
              names.
    """
    name_mapping = {
        'Gross': 'GrossVP',
        'Score': 'Sc',
        'Net': 'NetVP',
        'Stableford': 'Stableford'
    }
    inverted_mapping = {v: k for k, v in name_mapping.items()}
    
    return name_mapping, inverted_mapping


def prepare_best_teg_table(teg_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str, n_keep: int) -> pd.DataFrame:
    """Creates a formatted table of the best TEG performances.

    This function filters and formats the TEG data to create a clean, ranked
    table of the top TEG performances for a selected measure.

    Args:
        teg_data_ranked (pd.DataFrame): DataFrame containing ranked TEG
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').
        n_keep (int): The number of top performances to show.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for display.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Filter out TEG 2 for all measures BEFORE getting best performances
    # (TEG 2 only had 3 rounds, so not comparable to 4-round TEGs)
    filtered_data = teg_data_ranked[teg_data_ranked['TEGNum'] != 2].copy()
    
    # For filtered data, we can't use the pre-calculated rankings (they include TEG 2)
    # So we'll get the best scores directly using nsmallest/nlargest
    if selected_measure == 'Stableford':
        # For Stableford, higher is better
        best_tegs = filtered_data.nlargest(n_keep, selected_measure)
    else:
        # For other measures, lower is better
        best_tegs = filtered_data.nsmallest(n_keep, selected_measure)
    
    # Add ranking column manually
    best_tegs = best_tegs.copy()
    best_tegs['#'] = range(1, len(best_tegs) + 1)
    
    # Rename columns for display
    best_tegs = best_tegs.rename(columns=inverted_name_mapping)
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'TEG', 'Area', 'Year']
    best_tegs = best_tegs[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation
        best_tegs[selected_friendly_name] = best_tegs[selected_friendly_name].apply(format_vs_par)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = best_tegs.select_dtypes(include=['float64', 'int64']).columns
        best_tegs[numeric_columns] = best_tegs[numeric_columns].astype(int)
    
    return best_tegs


def prepare_best_round_table(rd_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str, n_keep: int) -> pd.DataFrame:
    """Creates a formatted table of the best round performances.

    This function filters and formats the round data to create a clean, ranked
    table of the top individual round performances for a selected measure.

    Args:
        rd_data_ranked (pd.DataFrame): DataFrame containing ranked round
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').
        n_keep (int): The number of top performances to show.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for display.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Calculate ranking column name
    rank_measure = f'Rank_within_all_{selected_measure}'
    
    # Get best performances from utils function
    from utils import get_best
    
    best_rounds = (get_best(rd_data_ranked, selected_measure, player_level=False, top_n=n_keep)
                   .sort_values(by=rank_measure, ascending=True)
                   .rename(columns={rank_measure: '#'})
                   .rename(columns=inverted_name_mapping))
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'Round', 'Course', 'Year']
    best_rounds = best_rounds[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation
        best_rounds[selected_friendly_name] = best_rounds[selected_friendly_name].apply(format_vs_par)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = best_rounds.select_dtypes(include=['float64', 'int64']).columns
        best_rounds[numeric_columns] = best_rounds[numeric_columns].astype(int)
    
    return best_rounds


def prepare_round_data_with_identifiers(rd_data_ranked: pd.DataFrame) -> pd.DataFrame:
    """Prepares round data with combined TEG and round identifiers.

    This function creates a readable round identifier by combining the TEG and
    round number (e.g., "TEG 15|R1").

    Args:
        rd_data_ranked (pd.DataFrame): DataFrame containing raw ranked round
            data.

    Returns:
        pd.DataFrame: The round data with a formatted 'Round' column.
    """
    rd_data_formatted = rd_data_ranked.copy()
    rd_data_formatted['Round'] = rd_data_formatted['TEG'] + '|R' + rd_data_formatted['Round'].astype(str)
    
    return rd_data_formatted


def prepare_personal_best_teg_table(teg_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str) -> pd.DataFrame:
    """Creates a formatted table of personal best TEG performances for each player.

    This function identifies and formats each player's best TEG performance for
    a selected measure, including their overall ranking.

    Args:
        teg_data_ranked (pd.DataFrame): DataFrame containing ranked TEG
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').

    Returns:
        pd.DataFrame: A formatted DataFrame with each player's best TEG
        performance.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Filter out TEG 2 for all measures (3 rounds vs standard 4)
    filtered_data = teg_data_ranked[teg_data_ranked['TEGNum'] != 2].copy()
    
    # Get each player's best performance from the filtered data using direct sorting
    if selected_measure == 'Stableford':
        # For Stableford, higher is better - get max per player
        personal_best_tegs = filtered_data.loc[filtered_data.groupby('Player')[selected_measure].idxmax()]
    else:
        # For other measures, lower is better - get min per player
        personal_best_tegs = filtered_data.loc[filtered_data.groupby('Player')[selected_measure].idxmin()]
    
    # Sort by the measure (best first)
    sort_ascending = selected_measure != 'Stableford'
    personal_best_tegs = personal_best_tegs.sort_values(by=selected_measure, ascending=sort_ascending)
    
    # Add ranking column manually
    personal_best_tegs = personal_best_tegs.copy()
    personal_best_tegs['#'] = range(1, len(personal_best_tegs) + 1)
    
    # Rename columns for display
    personal_best_tegs = personal_best_tegs.rename(columns=inverted_name_mapping)
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'TEG', 'Area', 'Year']
    personal_best_tegs = personal_best_tegs[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation (but not the # column)
        personal_best_tegs[selected_friendly_name] = personal_best_tegs[selected_friendly_name].apply(format_vs_par)
        # Convert other numeric columns (like #, Year) to integers
        numeric_columns = personal_best_tegs.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_columns:
            if col != selected_friendly_name:  # Don't convert the formatted vs par column
                personal_best_tegs[col] = personal_best_tegs[col].astype(int)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = personal_best_tegs.select_dtypes(include=['float64', 'int64']).columns
        personal_best_tegs[numeric_columns] = personal_best_tegs[numeric_columns].astype(int)
    
    return personal_best_tegs


def prepare_personal_best_round_table(rd_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str) -> pd.DataFrame:
    """Creates a formatted table of personal best round performances for each player.

    This function identifies and formats each player's best individual round
    performance for a selected measure, including their overall ranking.

    Args:
        rd_data_ranked (pd.DataFrame): DataFrame containing ranked round
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').

    Returns:
        pd.DataFrame: A formatted DataFrame with each player's best round
        performance.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Use player-level ranking to get 1 best performance per player
    rank_all_time = f'Rank_within_all_{selected_measure}'
    
    # Get best performances from utils function (player_level=True gets 1 per player)
    from utils import get_best
    
    personal_best_rounds = (get_best(rd_data_ranked, selected_measure, player_level=True, top_n=1)
                           .sort_values(by=rank_all_time, ascending=True)
                           .rename(columns={rank_all_time: '#'})
                           .rename(columns=inverted_name_mapping))
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'Round', 'Course', 'Year']
    personal_best_rounds = personal_best_rounds[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation (but not the # column)
        personal_best_rounds[selected_friendly_name] = personal_best_rounds[selected_friendly_name].apply(format_vs_par)
        # Convert other numeric columns (like #, Year) to integers
        numeric_columns = personal_best_rounds.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_columns:
            if col != selected_friendly_name:  # Don't convert the formatted vs par column
                personal_best_rounds[col] = personal_best_rounds[col].astype(int)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = personal_best_rounds.select_dtypes(include=['float64', 'int64']).columns
        personal_best_rounds[numeric_columns] = personal_best_rounds[numeric_columns].astype(int)
    
    return personal_best_rounds


def prepare_worst_teg_table(teg_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str, n_keep: int) -> pd.DataFrame:
    """Creates a formatted table of the worst TEG performances.

    This function filters and formats the TEG data to create a clean, ranked
    table of the worst TEG performances for a selected measure.

    Args:
        teg_data_ranked (pd.DataFrame): DataFrame containing ranked TEG
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').
        n_keep (int): The number of worst performances to show.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for display.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Filter out TEG 2 for all measures BEFORE getting worst performances
    # (TEG 2 only had 3 rounds, so not comparable to 4-round TEGs)
    filtered_data = teg_data_ranked[teg_data_ranked['TEGNum'] != 2].copy()
    
    # For filtered data, we can't use get_worst with pre-calculated rankings
    # So we'll get the worst scores directly using nsmallest/nlargest
    if selected_measure == 'Stableford':
        # For Stableford, lower is worse
        worst_tegs = filtered_data.nsmallest(n_keep, selected_measure)
    else:
        # For other measures, higher is worse
        worst_tegs = filtered_data.nlargest(n_keep, selected_measure)
    
    # Add ranking column manually
    worst_tegs = worst_tegs.copy()
    worst_tegs['#'] = range(1, len(worst_tegs) + 1)
    
    # Rename columns for display
    worst_tegs = worst_tegs.rename(columns=inverted_name_mapping)
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'TEG', 'Area', 'Year']
    worst_tegs = worst_tegs[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation
        worst_tegs[selected_friendly_name] = worst_tegs[selected_friendly_name].apply(format_vs_par)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = worst_tegs.select_dtypes(include=['float64', 'int64']).columns
        worst_tegs[numeric_columns] = worst_tegs[numeric_columns].astype(int)
    
    return worst_tegs


def prepare_worst_round_table(rd_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str, n_keep: int) -> pd.DataFrame:
    """Creates a formatted table of the worst round performances.

    This function filters and formats the round data to create a clean, ranked
    table of the worst individual round performances for a selected measure.

    Args:
        rd_data_ranked (pd.DataFrame): DataFrame containing ranked round
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').
        n_keep (int): The number of worst performances to show.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for display.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Get worst performances from utils function
    from utils import get_worst
    
    worst_rounds = (get_worst(rd_data_ranked, selected_measure, player_level=False, top_n=n_keep)
                    .rename(columns=inverted_name_mapping))
    
    # Sort by measure in descending order (worst first)
    sort_ascending = selected_measure == 'Stableford'  # Stableford: lower is worse
    worst_rounds = worst_rounds.sort_values(by=selected_friendly_name, ascending=sort_ascending)
    
    # Add ranking column
    worst_rounds['#'] = range(1, len(worst_rounds) + 1)
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'Round', 'Course', 'Year']
    worst_rounds = worst_rounds[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation
        worst_rounds[selected_friendly_name] = worst_rounds[selected_friendly_name].apply(format_vs_par)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = worst_rounds.select_dtypes(include=['float64', 'int64']).columns
        worst_rounds[numeric_columns] = worst_rounds[numeric_columns].astype(int)
    
    return worst_rounds


def prepare_personal_worst_teg_table(teg_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str) -> pd.DataFrame:
    """Creates a formatted table of personal worst TEG performances for each player.

    This function identifies and formats each player's worst TEG performance
    for a selected measure, including their overall ranking.

    Args:
        teg_data_ranked (pd.DataFrame): DataFrame containing ranked TEG
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').

    Returns:
        pd.DataFrame: A formatted DataFrame with each player's worst TEG
        performance.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Filter out TEG 2 for all measures (3 rounds vs standard 4)
    filtered_data = teg_data_ranked[teg_data_ranked['TEGNum'] != 2].copy()
    
    # Get worst performances per player using get_worst function 
    from utils import get_worst
    
    personal_worst_tegs = (get_worst(filtered_data, selected_measure, player_level=True, top_n=1)
                          .rename(columns=inverted_name_mapping))
    
    # Sort by measure (worst first)
    sort_ascending = selected_measure == 'Stableford'  # Stableford: lower is worse
    personal_worst_tegs = personal_worst_tegs.sort_values(by=selected_friendly_name, ascending=sort_ascending)
    
    # Add ranking column
    personal_worst_tegs['#'] = range(1, len(personal_worst_tegs) + 1)
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'TEG', 'Area', 'Year']
    personal_worst_tegs = personal_worst_tegs[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation (but not the # column)
        personal_worst_tegs[selected_friendly_name] = personal_worst_tegs[selected_friendly_name].apply(format_vs_par)
        # Convert other numeric columns (like #, Year) to integers
        numeric_columns = personal_worst_tegs.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_columns:
            if col != selected_friendly_name:  # Don't convert the formatted vs par column
                personal_worst_tegs[col] = personal_worst_tegs[col].astype(int)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = personal_worst_tegs.select_dtypes(include=['float64', 'int64']).columns
        personal_worst_tegs[numeric_columns] = personal_worst_tegs[numeric_columns].astype(int)
    
    return personal_worst_tegs


def prepare_personal_worst_round_table(rd_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str) -> pd.DataFrame:
    """Creates a formatted table of personal worst round performances for each player.

    This function identifies and formats each player's worst individual round
    performance for a selected measure, including their overall ranking.

    Args:
        rd_data_ranked (pd.DataFrame): DataFrame containing ranked round
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').

    Returns:
        pd.DataFrame: A formatted DataFrame with each player's worst round
        performance.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Get worst performances per player using get_worst function
    from utils import get_worst
    
    personal_worst_rounds = (get_worst(rd_data_ranked, selected_measure, player_level=True, top_n=1)
                            .rename(columns=inverted_name_mapping))
    
    # Sort by measure (worst first)
    sort_ascending = selected_measure == 'Stableford'  # Stableford: lower is worse
    personal_worst_rounds = personal_worst_rounds.sort_values(by=selected_friendly_name, ascending=sort_ascending)
    
    # Add ranking column
    personal_worst_rounds['#'] = range(1, len(personal_worst_rounds) + 1)
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'Round', 'Course', 'Year']
    personal_worst_rounds = personal_worst_rounds[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation (but not the # column)
        personal_worst_rounds[selected_friendly_name] = personal_worst_rounds[selected_friendly_name].apply(format_vs_par)
        # Convert other numeric columns (like #, Year) to integers
        numeric_columns = personal_worst_rounds.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_columns:
            if col != selected_friendly_name:  # Don't convert the formatted vs par column
                personal_worst_rounds[col] = personal_worst_rounds[col].astype(int)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = personal_worst_rounds.select_dtypes(include=['float64', 'int64']).columns
        personal_worst_rounds[numeric_columns] = personal_worst_rounds[numeric_columns].astype(int)
    
    return personal_worst_rounds


def prepare_pb_teg_summary_table(teg_data_ranked: pd.DataFrame) -> pd.DataFrame:
    """Creates a summary table of each player's personal best TEG.

    This function generates a summary table showing each player's personal best
    TEG performance across all scoring measures.

    Args:
        teg_data_ranked (pd.DataFrame): DataFrame containing ranked TEG
            performance data.

    Returns:
        pd.DataFrame: A summary DataFrame with columns for Score, Gross v Par,
        Net v Par, and Stableford.
    """
    from utils import format_vs_par
    
    # Filter out TEG 2 (3 rounds vs standard 4)
    filtered_data = teg_data_ranked[teg_data_ranked['TEGNum'] != 2].copy()
    
    # Get unique players
    players = sorted(filtered_data['Player'].unique())
    
    summary_data = []
    
    for player in players:
        player_data = filtered_data[filtered_data['Player'] == player]
        row = {'Player': player.replace(' ', '<br>')}
        
        # Score (lowest is best)
        best_score = player_data.loc[player_data['Sc'].idxmin()]
        row['Score'] = f"<span class='pb-score'>{int(best_score['Sc'])}</span><br><span class='pb-when'>{best_score['TEG']}</span>"
        
        # Gross vs Par (lowest is best)
        best_gross = player_data.loc[player_data['GrossVP'].idxmin()]
        row['Gross'] = f"<span class='pb-score'>{format_vs_par(best_gross['GrossVP'])}</span><br><span class='pb-when'>{best_gross['TEG']}</span>"
        
        # Net vs Par (lowest is best)
        best_net = player_data.loc[player_data['NetVP'].idxmin()]
        row['Net'] = f"<span class='pb-score'>{format_vs_par(best_net['NetVP'])}</span><br><span class='pb-when'>{best_net['TEG']}</span>"
        
        # Stableford (highest is best)
        best_stableford = player_data.loc[player_data['Stableford'].idxmax()]
        row['Stfd'] = f"<span class='pb-score'>{int(best_stableford['Stableford'])}</span><br><span class='pb-when'>{best_stableford['TEG']}</span>"
        
        summary_data.append(row)
    
    return pd.DataFrame(summary_data)


def prepare_pb_round_summary_table(rd_data_ranked: pd.DataFrame) -> pd.DataFrame:
    """Creates a summary table of each player's personal best round.

    This function generates a summary table showing each player's personal best
    individual round performance across all scoring measures.

    Args:
        rd_data_ranked (pd.DataFrame): DataFrame containing ranked round
            performance data.

    Returns:
        pd.DataFrame: A summary DataFrame with columns for Score, Gross v Par,
        Net v Par, and Stableford.
    """
    from utils import format_vs_par

    # Get unique players
    players = sorted(rd_data_ranked['Player'].unique())

    summary_data = []

    for player in players:
        player_data = rd_data_ranked[rd_data_ranked['Player'] == player]
        row = {'Player': player.replace(' ', '<br>')}

        # Score (lowest is best)
        best_score = player_data.loc[player_data['Sc'].idxmin()]
        row['Score'] = f"<span class='pb-score'>{int(best_score['Sc'])}</span><br><span class='pb-when'>{best_score['TEG']}|R{best_score['Round']}</span>"

        # Gross vs Par (lowest is best)
        best_gross = player_data.loc[player_data['GrossVP'].idxmin()]
        row['Gross'] = f"<span class='pb-score'>{format_vs_par(best_gross['GrossVP'])}</span><br><span class='pb-when'>{best_gross['TEG']}|R{best_gross['Round']}</span>"

        # Net vs Par (lowest is best)
        best_net = player_data.loc[player_data['NetVP'].idxmin()]
        row['Net'] = f"<span class='pb-score'>{format_vs_par(best_net['NetVP'])}</span><br><span class='pb-when'>{best_net['TEG']}|R{best_net['Round']}</span>"

        # Stableford (highest is best)
        best_stableford = player_data.loc[player_data['Stableford'].idxmax()]
        row['Stfd'] = f"<span class='pb-score'>{int(best_stableford['Stableford'])}</span><br><span class='pb-when'>{best_stableford['TEG']}|R{best_stableford['Round']}</span>"

        summary_data.append(row)

    return pd.DataFrame(summary_data)


def prepare_pb_nine_summary_table(nine_data_ranked: pd.DataFrame) -> pd.DataFrame:
    """Creates a summary table of each player's personal best 9 holes.

    This function generates a summary table showing each player's personal best
    9-hole performance (Front 9 or Back 9) across all scoring measures.

    Args:
        nine_data_ranked (pd.DataFrame): DataFrame containing ranked 9-hole
            (FrontBack) performance data.

    Returns:
        pd.DataFrame: A summary DataFrame with columns for Score, Gross v Par,
        Net v Par, and Stableford.
    """
    from utils import format_vs_par

    # Get unique players
    players = sorted(nine_data_ranked['Player'].unique())

    summary_data = []

    for player in players:
        player_data = nine_data_ranked[nine_data_ranked['Player'] == player]
        row = {'Player': player.replace(' ', '<br>')}

        # Score (lowest is best)
        best_score = player_data.loc[player_data['Sc'].idxmin()]
        row['Score'] = f"<span class='pb-score'>{int(best_score['Sc'])}</span><br><span class='pb-when'>{best_score['TEG']}|R{best_score['Round']} {best_score['FrontBack']}</span>"

        # Gross vs Par (lowest is best)
        best_gross = player_data.loc[player_data['GrossVP'].idxmin()]
        row['Gross'] = f"<span class='pb-score'>{format_vs_par(best_gross['GrossVP'])}</span><br><span class='pb-when'>{best_gross['TEG']}|R{best_gross['Round']} {best_gross['FrontBack']}</span>"

        # Net vs Par (lowest is best)
        best_net = player_data.loc[player_data['NetVP'].idxmin()]
        row['Net'] = f"<span class='pb-score'>{format_vs_par(best_net['NetVP'])}</span><br><span class='pb-when'>{best_net['TEG']}|R{best_net['Round']} {best_net['FrontBack']}</span>"

        # Stableford (highest is best)
        best_stableford = player_data.loc[player_data['Stableford'].idxmax()]
        row['Stfd'] = f"<span class='pb-score'>{int(best_stableford['Stableford'])}</span><br><span class='pb-when'>{best_stableford['TEG']}|R{best_stableford['Round']} {best_stableford['FrontBack']}</span>"

        summary_data.append(row)

    return pd.DataFrame(summary_data)


# === SECTION DIVIDER ===

"""Data processing functions for worst performance analysis.

This module contains functions for processing worst performance records,
formatting the data for display, and creating performance stat sections with
proper formatting.
"""


import pandas as pd


def get_performance_measure_titles() -> dict:
    """Defines measure titles for worst performance displays.

    This function provides consistent titles for worst performance statistics
    by separating internal field names from user-facing descriptions.

    Returns:
        dict: A mapping of internal measure names to display titles.
    """
    measure_titles = {
        'Sc': "Worst Score",
        'GrossVP': "Worst Gross",
        'NetVP': "Worst Net",
        'Stableford': "Worst Stableford"
    }
    
    return measure_titles


def format_performance_value(value: float, measure: str) -> str:
    """Formats performance values for display with appropriate notation.

    This function applies consistent formatting for worst performance values,
    using +/- notation for vs-par measures and plain integers for others.

    Args:
        value (float): The performance value to format.
        measure (str): The performance measure type.

    Returns:
        str: The formatted value with +/- notation for vs-par measures.
    """
    if measure in ['GrossVP', 'NetVP']:
        return f"{int(value):+}"  # Shows +5 or -2
    else:
        return str(int(value))    # Shows 85


def prepare_worst_performance_dataframe(worst_records: pd.DataFrame, record_type: str) -> pd.DataFrame:
    """Prepares the worst performance DataFrame for stat section display.

    This function formats worst performance data for a clean stat section
    display, handling different record types with appropriate column selection
    and creating combined identifiers for rounds and 9-hole segments.

    Args:
        worst_records (pd.DataFrame): The raw worst performance records.
        record_type (str): The type of record ('teg', 'round', or
            'frontback').

    Returns:
        pd.DataFrame: A formatted DataFrame ready for stat section display.
    """
    df = worst_records.copy()
    df['Year'] = df['Year'].astype(str)
    
    if record_type in ['round', 'frontback']:
        # Format round identifier
        df['Round'] = 'R' + df['Round'].astype(str)
        df['TEG_Round'] = df['TEG'] + ', ' + df['Round']
        
        # Add front/back identifier for 9-hole records
        if record_type == 'frontback':
            df['TEG_Round'] += ' ' + df['FrontBack'] + ' 9'
        
        # Select columns for round/9-hole display
        df = df[['Player', 'Course', 'TEG_Round', 'Year']]
    else:  # TEG record type
        # Select columns for TEG display
        df = df[['Player', 'TEG', 'Year']]
    
    return df


def load_worst_performance_custom_css() -> str:
    """Loads custom CSS styling for the worst performance page.

    This function provides specialized styling for worst performance displays,
    creating a consistent visual layout for stat sections and defining
    typography and color schemes.

    Returns:
        str: A string of CSS styling for stat sections and layout.
    """
    css_styles = """
    <style>
    div[data-testid="column"] {
        background-color: #f0f0f0;
        border-radius: 10px;
        padding: 20px;
        height: 100%;
    }
    .stat-section {
        margin-bottom: 20px;
        background-color: rgb(240, 242, 246);
        padding: 20px;
        margin: 5px;
    }
    .stat-section h2 {
        margin-bottom: 5px;
        font-size: 22px;
        line-height: 1.0;
        color: #333;
        padding: 0;
    }
    .stat-section h2 .title {
        font-weight: normal;
    }
    .stat-section h2 .value {
        font-weight: bold;
    }
    .stat-details {
        font-size: 16px;
        color: #999;
        line-height: 1.4;
    }
    .stat-details .Player {
        color: #666;
    }
    </style>
    """
    
    return css_styles


def create_worst_performance_section(worst_records: pd.DataFrame, measure: str, record_type: str, measure_titles: dict) -> str:
    """Creates a complete worst performance stat section.

    This function generates a complete stat section for the worst performance
    display, combining the title, value, and details into formatted HTML.

    Args:
        worst_records (pd.DataFrame): The worst performance records.
        measure (str): The performance measure.
        record_type (str): The type of record ('teg', 'round', or
            'frontback').
        measure_titles (dict): A dictionary of measure title mappings.

    Returns:
        str: The HTML for the stat section display.
    """
    from utils import create_stat_section
    
    title = measure_titles[measure]
    value = format_performance_value(worst_records[measure].iloc[0], measure)
    df = prepare_worst_performance_dataframe(worst_records, record_type)
    
    return create_stat_section(title, value, df, "| ")


def get_filtered_teg_data() -> pd.DataFrame:
    """Gets TEG data with TEG 2 excluded for worst performance analysis.

    This function excludes TEG 2 from the worst performance analysis as it is
    considered anomalous, providing a clean dataset for meaningful
    comparisons.

    Returns:
        pd.DataFrame: The TEG data with TEG 2 excluded.
    """
    from utils import get_complete_teg_data
    
    teg_data = get_complete_teg_data()
    filtered_teg_data = teg_data[teg_data['TEGNum'] != 2]
    
    return filtered_teg_data


# === SECTION DIVIDER ===

"""Data processing functions for latest round analysis and context display.

This module contains functions for managing round selection session state,
processing round ranking data for display, and creating metric-specific context
tables and charts.
"""


import pandas as pd
# get_current_in_progress_teg_fast and get_last_completed_teg_fast
# are now defined at the end of this module (lines ~2800+)


def get_round_metric_mappings() -> tuple[dict, dict]:
    """Gets mappings between user-friendly and internal metric names for rounds.

    Returns:
        tuple: A tuple containing two dictionaries:
            - name_mapping (dict): Maps user-friendly names to internal names.
            - inverted_mapping (dict): Maps internal names to user-friendly
              names.
    """
    name_mapping = {
        'Gross vs Par': 'GrossVP',
        'Score': 'Sc',
        'Net vs Par': 'NetVP',
        'Stableford': 'Stableford'
    }
    inverted_mapping = {v: k for k, v in name_mapping.items()}
    
    return name_mapping, inverted_mapping


# initialize_round_selection_state() - MOVED TO streamlit/utils.py
# This function uses st.session_state which is Streamlit-specific


def get_latest_round_defaults(df_round: pd.DataFrame) -> tuple[str, int]:
    """Gets the default TEG and round values (the latest available).

    Pure calculation function - determines the most recent round.

    Args:
        df_round (pd.DataFrame): A DataFrame of round ranking data, used as a
            fallback.

    Returns:
        tuple: A tuple containing the max TEG and max round in that TEG.

    Raises:
        ValueError: If df_round is empty or invalid
    """
    if df_round.empty:
        raise ValueError("Cannot determine latest round from empty DataFrame")

    try:
        # Try fast method first: check if there's a TEG in progress
        # Note: These functions need to be migrated to this module
        # For now, fall back to DataFrame method
        # in_progress_teg, rounds_played = get_current_in_progress_teg_fast()
        # if in_progress_teg:
        #     return f"TEG {in_progress_teg}", rounds_played

        # Fallback to DataFrame method
        df_sorted = df_round.sort_values(by=['TEGNum', 'Round'])
        max_teg = df_sorted.loc[df_sorted['TEGNum'].idxmax(), 'TEG']
        max_round_in_max_teg = df_sorted[df_sorted['TEG'] == max_teg]['Round'].max()
        return max_teg, max_round_in_max_teg

    except Exception as e:
        raise ValueError(f"Error determining latest round: {e}")


# update_session_state_defaults() - MOVED TO streamlit/utils.py
# This function uses st.session_state which is Streamlit-specific


# create_round_selection_reset_function() - MOVED TO streamlit/utils.py
# This function uses st.session_state which is Streamlit-specific


def get_teg_and_round_options(df_round: pd.DataFrame, selected_teg: str) -> tuple[list, list]:
    """Gets available TEG and round options for selection dropdowns.

    This function provides filtered options for dynamic dropdown menus, where
    the round options update based on the selected TEG.

    Args:
        df_round (pd.DataFrame): The round ranking data.
        selected_teg (str): The currently selected TEG.

    Returns:
        tuple: A tuple containing:
            - teg_options (list): A list of TEG options.
            - round_options (list): A list of round options for the
              selected TEG.
    """
    teg_options = list(df_round['TEG'].unique())
    round_options = sorted(df_round[df_round['TEG'] == selected_teg]['Round'].unique())
    
    return teg_options, round_options


def create_metric_tabs_data(metrics: list) -> tuple[list, list]:
    """Prepares metric data for tabbed display.

    This function creates user-friendly tab labels from internal metric names
    and maintains a mapping for data processing within each tab.

    Args:
        metrics (list): A list of internal metric names.

    Returns:
        tuple: A tuple containing:
            - metrics (list): The original list of internal metric names.
            - friendly_metrics (list): A list of user-friendly metric names.
    """
    name_mapping, inverted_name_mapping = get_round_metric_mappings()
    friendly_metrics = [inverted_name_mapping[metric] for metric in metrics]
    
    return metrics, friendly_metrics


def prepare_round_context_display(df_round: pd.DataFrame, teg_r: str, rd_r: int, metric: str, friendly_metric: str) -> pd.DataFrame:
    """Prepares round context data for display in a specific metric tab.

    This function creates a context table showing how the selected round
    compares to other rounds.

    Args:
        df_round (pd.DataFrame): The round ranking data.
        teg_r (str): The selected TEG.
        rd_r (int): The selected round.
        metric (str): The internal metric name.
        friendly_metric (str): The user-friendly metric name.

    Returns:
        pd.DataFrame: A context table with renamed columns for display.
    """
    from utils import chosen_rd_context
    
    # Get context data from utils function
    context_data = chosen_rd_context(df_round, teg_r, rd_r, metric)
    
    # Rename metric column to friendly name for display
    display_data = context_data.rename(columns={metric: friendly_metric})
    
    return display_data


# === TEG CONTEXT FUNCTIONS ===

# initialize_teg_selection_state() - MOVED TO streamlit/utils.py
# This function uses st.session_state which is Streamlit-specific


def get_latest_teg_default(df_teg: pd.DataFrame) -> str:
    """Gets the default TEG value (the latest available).

    Pure calculation function - determines the most recent TEG.

    Args:
        df_teg (pd.DataFrame): A DataFrame of TEG ranking data.

    Returns:
        str: The latest available TEG for default selection.

    Raises:
        ValueError: If df_teg is empty or invalid
    """
    if df_teg.empty:
        raise ValueError("Cannot determine latest TEG from empty DataFrame")

    try:
        # Try fast method first (when functions are migrated)
        # Note: These functions need to be migrated to this module
        # For now, fall back to DataFrame method
        # in_progress_teg, rounds_played = get_current_in_progress_teg_fast()
        # if in_progress_teg:
        #     return f"TEG {in_progress_teg}"

        # Fallback to DataFrame method
        df_sorted = df_teg.sort_values(by='TEGNum')
        max_teg = df_sorted.loc[df_sorted['TEGNum'].idxmax(), 'TEG']
        return max_teg

    except Exception as e:
        raise ValueError(f"Error determining latest TEG: {e}")


# update_teg_session_state_defaults() - MOVED TO streamlit/utils.py
# This function uses st.session_state which is Streamlit-specific


# create_teg_selection_reset_function() - MOVED TO streamlit/utils.py
# This function uses st.session_state which is Streamlit-specific


def get_teg_options(df_teg: pd.DataFrame) -> list:
    """Gets available TEG options for the selection dropdown.

    Args:
        df_teg (pd.DataFrame): The TEG ranking data.

    Returns:
        list: A list of TEG options for the dropdown menu.
    """
    return list(df_teg['TEG'].unique())


def prepare_teg_context_display(df_teg: pd.DataFrame, teg_t: str, metric: str, friendly_metric: str) -> pd.DataFrame:
    """Prepares TEG context data for display in a specific metric tab.

    This function creates a context table showing how the selected TEG
    compares to other TEGs.

    Args:
        df_teg (pd.DataFrame): The TEG ranking data.
        teg_t (str): The selected TEG.
        metric (str): The internal metric name.
        friendly_metric (str): The user-friendly metric name.

    Returns:
        pd.DataFrame: A context table with renamed columns for display.
    """
    from utils import chosen_teg_context
    
    # Get context data from utils function
    context_data = chosen_teg_context(df_teg, teg_t, metric)
    
    # Rename metric column to friendly name for display
    display_data = context_data.rename(columns={metric: friendly_metric})
    
    return display_data


# === SECTION DIVIDER ===

"""Helper functions for analyzing final round comebacks and collapses in TEG tournaments.

This module provides functions to identify and analyze dramatic final round performances:
- Biggest final round score differentials
- Biggest leads lost by penultimate round leaders
- Biggest leads lost during the final round
- Biggest comebacks in the final round regardless of winning
"""


import pandas as pd
import numpy as np
from typing import Tuple


def calculate_final_round_differentials(
    all_scores_df: pd.DataFrame,
    round_info_df: pd.DataFrame,
    measure: str = 'GrossVP'
) -> pd.DataFrame:
    """Calculate the biggest final round score differentials.

    Finds the best and worst final round performances for each player in each TEG,
    showing who had the biggest positive or negative scoring swings.

    Args:
        all_scores_df: DataFrame with hole-by-hole scores
        round_info_df: DataFrame with TEG round information
        measure: Scoring measure ('GrossVP' or 'Stableford')

    Returns:
        DataFrame with columns: TEG, Player, FinalRound, FinalRoundScore, TotalScore, Rank
    """
    # Exclude TEG 2 (only 3 rounds)
    valid_tegs = round_info_df[round_info_df['Round'] == 4]['TEGNum'].unique()
    df = all_scores_df[all_scores_df['TEGNum'].isin(valid_tegs)].copy()

    # For Stableford, only include TEG 6+
    if measure == 'Stableford':
        df = df[df['TEGNum'] >= 6]

    # Get final round number for each TEG
    final_rounds = round_info_df.groupby('TEGNum')['Round'].max().to_dict()

    # Calculate round totals
    round_totals = df.groupby(['TEG', 'TEGNum', 'Player', 'Round'])[measure].sum().reset_index()
    round_totals.columns = ['TEG', 'TEGNum', 'Player', 'Round', 'RoundScore']

    # Filter for final rounds only
    round_totals['FinalRound'] = round_totals['TEGNum'].map(final_rounds)
    final_round_scores = round_totals[round_totals['Round'] == round_totals['FinalRound']].copy()

    # Calculate tournament totals
    teg_totals = round_totals.groupby(['TEG', 'TEGNum', 'Player'])['RoundScore'].sum().reset_index()
    teg_totals.columns = ['TEG', 'TEGNum', 'Player', 'TotalScore']

    # Calculate scores through penultimate round for "Rank After R3"
    penultimate_data = round_totals[round_totals['Round'] < round_totals['FinalRound']]
    penultimate_totals = penultimate_data.groupby(['TEG', 'TEGNum', 'Player'])['RoundScore'].sum().reset_index()
    penultimate_totals.columns = ['TEG', 'TEGNum', 'Player', 'ScoreAfterR3']

    # Add rankings (ascending for Gross, descending for Stableford)
    ascending = True if measure == 'GrossVP' else False
    penultimate_totals['RankAfterR3'] = penultimate_totals.groupby('TEG')['ScoreAfterR3'].rank(method='min', ascending=ascending)

    # Merge final round with totals and penultimate rank
    result = final_round_scores.merge(teg_totals, on=['TEG', 'TEGNum', 'Player'])
    result = result.merge(penultimate_totals[['TEG', 'Player', 'RankAfterR3']], on=['TEG', 'Player'])

    # Add final rankings
    result['FinalRank'] = result.groupby('TEG')['TotalScore'].rank(method='min', ascending=ascending)

    # Sort by final round score (best performances first based on measure)
    result = result.sort_values('RoundScore', ascending=ascending)

    # Select and rename columns
    result = result[['TEG', 'Player', 'FinalRound', 'RoundScore', 'RankAfterR3', 'TotalScore', 'FinalRank']]
    result.columns = ['TEG', 'Player', 'Final Round', 'Final Round Score', 'Rank After R3', 'Total Score', 'Final Rank']

    return result


def calculate_biggest_leads_lost_after_r3(
    all_scores_df: pd.DataFrame,
    round_info_df: pd.DataFrame,
    measure: str = 'GrossVP'
) -> pd.DataFrame:
    """Find biggest leads going into the final round where the leader didn't win.

    Calculates the standings after the penultimate round and identifies cases where
    the leader(s) after that round did not go on to win the tournament.

    Args:
        all_scores_df: DataFrame with hole-by-hole scores
        round_info_df: DataFrame with TEG round information
        measure: Scoring measure ('GrossVP' or 'Stableford')

    Returns:
        DataFrame with: TEG, LeaderAfterR3, GapToSecond, Winner, LeaderFinalPosition
    """
    # Exclude TEG 2 (only 3 rounds)
    valid_tegs = round_info_df[round_info_df['Round'] == 4]['TEGNum'].unique()
    df = all_scores_df[all_scores_df['TEGNum'].isin(valid_tegs)].copy()

    # For Stableford, only include TEG 6+
    if measure == 'Stableford':
        df = df[df['TEGNum'] >= 6]

    # Get penultimate round number for each TEG
    final_rounds = round_info_df.groupby('TEGNum')['Round'].max().to_dict()

    # Calculate round totals
    round_totals = df.groupby(['TEG', 'TEGNum', 'Player', 'Round'])[measure].sum().reset_index()

    results = []

    for teg_num, teg_name in df[['TEGNum', 'TEG']].drop_duplicates().values:
        final_round = final_rounds.get(teg_num, 4)
        penultimate_round = final_round - 1

        teg_data = round_totals[round_totals['TEGNum'] == teg_num]

        # Calculate cumulative scores through penultimate round
        penultimate_data = teg_data[teg_data['Round'] <= penultimate_round]
        penultimate_totals = penultimate_data.groupby('Player')[measure].sum().reset_index()
        penultimate_totals.columns = ['Player', 'ScoreAfterR3']

        # Calculate final totals
        final_totals = teg_data.groupby('Player')[measure].sum().reset_index()
        final_totals.columns = ['Player', 'FinalScore']

        # Determine ascending based on measure
        ascending = True if measure == 'GrossVP' else False

        # Find leader(s) after penultimate round
        if ascending:
            leader_score = penultimate_totals['ScoreAfterR3'].min()
        else:
            leader_score = penultimate_totals['ScoreAfterR3'].max()

        leaders = penultimate_totals[penultimate_totals['ScoreAfterR3'] == leader_score]['Player'].tolist()

        # Find winner(s)
        if ascending:
            winner_score = final_totals['FinalScore'].min()
        else:
            winner_score = final_totals['FinalScore'].max()

        winners = final_totals[final_totals['FinalScore'] == winner_score]['Player'].tolist()

        # Check if leader didn't win
        if not any(leader in winners for leader in leaders):
            # Calculate gap to second place
            if ascending:
                second_score = penultimate_totals[
                    penultimate_totals['ScoreAfterR3'] > leader_score
                ]['ScoreAfterR3'].min()
                gap = second_score - leader_score
            else:
                second_score = penultimate_totals[
                    penultimate_totals['ScoreAfterR3'] < leader_score
                ]['ScoreAfterR3'].max()
                gap = leader_score - second_score

            # Get leader's final position
            final_totals['Rank'] = final_totals['FinalScore'].rank(method='min', ascending=ascending)

            for leader in leaders:
                leader_final_rank = final_totals[final_totals['Player'] == leader]['Rank'].iloc[0]

                results.append({
                    'TEG': teg_name,
                    'Leader After R3': leader,
                    'Gap to 2nd': gap,
                    'Winner': ', '.join(winners),
                    'Leader Final Position': int(leader_final_rank)
                })

    result_df = pd.DataFrame(results)

    if not result_df.empty:
        # Sort by gap (biggest leads lost first)
        result_df = result_df.sort_values('Gap to 2nd', ascending=False)

    return result_df


def calculate_biggest_leads_lost_in_r4(
    all_scores_df: pd.DataFrame,
    round_info_df: pd.DataFrame,
    measure: str = 'GrossVP'
) -> pd.DataFrame:
    """Find biggest leads lost during the final round.

    Tracks cumulative scores hole-by-hole during the final round to find cases
    where a player held a significant lead at some point but didn't win.

    Args:
        all_scores_df: DataFrame with hole-by-hole scores
        round_info_df: DataFrame with TEG round information
        measure: Scoring measure ('GrossVP' or 'Stableford')

    Returns:
        DataFrame with: TEG, Player, MaxLeadInR4, HoleOfMaxLead, Winner, FinalGap
    """
    # Exclude TEG 2 (only 3 rounds)
    valid_tegs = round_info_df[round_info_df['Round'] == 4]['TEGNum'].unique()
    df = all_scores_df[all_scores_df['TEGNum'].isin(valid_tegs)].copy()

    # For Stableford, only include TEG 6+
    if measure == 'Stableford':
        df = df[df['TEGNum'] >= 6]

    # Get final round number for each TEG
    final_rounds = round_info_df.groupby('TEGNum')['Round'].max().to_dict()

    temp_results = []  # Temporary tracking of leads at each hole
    final_results = []  # Final summary results
    ascending = True if measure == 'GrossVP' else False

    for teg_num, teg_name in df[['TEGNum', 'TEG']].drop_duplicates().values:
        final_round = final_rounds.get(teg_num, 4)

        # Get scores through penultimate round
        pre_final_data = df[(df['TEGNum'] == teg_num) & (df['Round'] < final_round)]
        pre_final_totals = pre_final_data.groupby('Player')[measure].sum().reset_index()
        pre_final_totals.columns = ['Player', 'PreFinalScore']

        # Get final round data
        final_round_data = df[(df['TEGNum'] == teg_num) & (df['Round'] == final_round)]

        # For each hole in final round, calculate cumulative standings
        for hole in sorted(final_round_data['Hole'].unique()):
            # Get scores through this hole in final round
            through_hole = final_round_data[final_round_data['Hole'] <= hole]
            final_round_cum = through_hole.groupby('Player')[measure].sum().reset_index()
            final_round_cum.columns = ['Player', 'FinalRoundScore']

            # Merge with pre-final scores
            standings = pre_final_totals.merge(final_round_cum, on='Player', how='left')
            standings['FinalRoundScore'] = standings['FinalRoundScore'].fillna(0)
            standings['TotalScore'] = standings['PreFinalScore'] + standings['FinalRoundScore']

            # Calculate ranks and gaps
            standings['Rank'] = standings['TotalScore'].rank(method='min', ascending=ascending)

            # Find leader(s) at this hole
            leaders = standings[standings['Rank'] == 1]

            # Calculate gap to second for each leader
            if len(standings) > 1:
                for _, leader_row in leaders.iterrows():
                    leader_score = leader_row['TotalScore']
                    non_leaders = standings[standings['Player'] != leader_row['Player']]

                    if len(non_leaders) > 0:
                        if ascending:
                            second_score = non_leaders['TotalScore'].min()
                            gap = second_score - leader_score
                        else:
                            second_score = non_leaders['TotalScore'].max()
                            gap = leader_score - second_score

                        # Store this as a potential max lead
                        temp_results.append({
                            'TEGNum': teg_num,
                            'TEG': teg_name,
                            'Player': leader_row['Player'],
                            'Hole': hole,
                            'Lead': gap,
                            'TotalScore': leader_score
                        })

        # Get final results for this TEG
        final_data = df[df['TEGNum'] == teg_num]
        final_totals = final_data.groupby('Player')[measure].sum().reset_index()
        final_totals.columns = ['Player', 'FinalScore']

        if ascending:
            winner_score = final_totals['FinalScore'].min()
        else:
            winner_score = final_totals['FinalScore'].max()

        winners = final_totals[final_totals['FinalScore'] == winner_score]['Player'].tolist()

        # For each TEG, find the maximum lead held by non-winners
        teg_temp_results = [r for r in temp_results if r['TEGNum'] == teg_num]
        for player in set([r['Player'] for r in teg_temp_results]):
            if player not in winners:
                player_leads = [r for r in teg_temp_results if r['Player'] == player]
                if player_leads:
                    max_lead_record = max(player_leads, key=lambda x: x['Lead'])

                    # Calculate final gap
                    player_final = final_totals[final_totals['Player'] == player]['FinalScore'].iloc[0]
                    if ascending:
                        final_gap = player_final - winner_score
                    else:
                        final_gap = winner_score - player_final

                    final_results.append({
                        'TEG': teg_name,
                        'Player': player,
                        'Max Lead in R4': max_lead_record['Lead'],
                        'Hole of Max Lead': int(max_lead_record['Hole']),
                        'Winner': ', '.join(winners),
                        'Final Gap': final_gap,
                        '_sort_key': max_lead_record['Lead']
                    })

    # Create DataFrame from final results
    result_df = pd.DataFrame(final_results)

    if not result_df.empty:
        # Sort by max lead (biggest leads first)
        result_df = result_df.sort_values('_sort_key', ascending=False)
        result_df = result_df[['TEG', 'Player', 'Max Lead in R4', 'Hole of Max Lead', 'Winner', 'Final Gap']]

    return result_df


def calculate_biggest_comebacks(
    all_scores_df: pd.DataFrame,
    round_info_df: pd.DataFrame,
    measure: str = 'GrossVP'
) -> pd.DataFrame:
    """Find biggest score comebacks in the final round, regardless of winning.

    Identifies the biggest score differentials between any player and the leader
    going into the final round, showing who made the biggest improvement.

    Args:
        all_scores_df: DataFrame with hole-by-hole scores
        round_info_df: DataFrame with TEG round information
        measure: Scoring measure ('GrossVP' or 'Stableford')

    Returns:
        DataFrame with: TEG, Player, GapAfterR3, FinalRoundScore, GapClosed,
                        FinalPosition, Winner
    """
    # Exclude TEG 2 (only 3 rounds)
    valid_tegs = round_info_df[round_info_df['Round'] == 4]['TEGNum'].unique()
    df = all_scores_df[all_scores_df['TEGNum'].isin(valid_tegs)].copy()

    # For Stableford, only include TEG 6+
    if measure == 'Stableford':
        df = df[df['TEGNum'] >= 6]

    # Get round information
    final_rounds = round_info_df.groupby('TEGNum')['Round'].max().to_dict()

    # Calculate round totals
    round_totals = df.groupby(['TEG', 'TEGNum', 'Player', 'Round'])[measure].sum().reset_index()

    results = []
    ascending = True if measure == 'GrossVP' else False

    for teg_num, teg_name in df[['TEGNum', 'TEG']].drop_duplicates().values:
        final_round = final_rounds.get(teg_num, 4)
        penultimate_round = final_round - 1

        teg_data = round_totals[round_totals['TEGNum'] == teg_num]

        # Calculate scores after penultimate round
        penultimate_data = teg_data[teg_data['Round'] <= penultimate_round]
        penultimate_totals = penultimate_data.groupby('Player')[measure].sum().reset_index()
        penultimate_totals.columns = ['Player', 'ScoreAfterR3']

        # Get final round scores
        final_round_data = teg_data[teg_data['Round'] == final_round]
        final_round_scores = final_round_data.groupby('Player')[measure].sum().reset_index()
        final_round_scores.columns = ['Player', 'FinalRoundScore']

        # Calculate final totals
        final_totals = teg_data.groupby('Player')[measure].sum().reset_index()
        final_totals.columns = ['Player', 'FinalScore']

        # Find leader after R3
        if ascending:
            leader_r3_score = penultimate_totals['ScoreAfterR3'].min()
        else:
            leader_r3_score = penultimate_totals['ScoreAfterR3'].max()

        # Find winner
        if ascending:
            winner_score = final_totals['FinalScore'].min()
        else:
            winner_score = final_totals['FinalScore'].max()

        winners = final_totals[final_totals['FinalScore'] == winner_score]['Player'].tolist()

        # Merge all data
        merged = penultimate_totals.merge(final_round_scores, on='Player')
        merged = merged.merge(final_totals, on='Player')

        # Calculate gaps
        if ascending:
            merged['GapAfterR3'] = merged['ScoreAfterR3'] - leader_r3_score
            merged['GapAfterR4'] = merged['FinalScore'] - winner_score
        else:
            merged['GapAfterR3'] = leader_r3_score - merged['ScoreAfterR3']
            merged['GapAfterR4'] = winner_score - merged['FinalScore']

        # Calculate gap closed (positive means improved position)
        merged['GapClosed'] = merged['GapAfterR3'] - merged['GapAfterR4']

        # Calculate final rank
        merged['FinalRank'] = merged['FinalScore'].rank(method='min', ascending=ascending)

        # Get leader's final round score
        leader_final_round_score = None
        for winner in winners:
            winner_r4_score = final_round_scores[final_round_scores['Player'] == winner]['FinalRoundScore'].values
            if len(winner_r4_score) > 0:
                leader_final_round_score = winner_r4_score[0]
                break

        # Add to results
        for _, row in merged.iterrows():
            results.append({
                'TEG': teg_name,
                'Player': row['Player'],
                'Gap After R3': row['GapAfterR3'],
                'Player R4 Score': row['FinalRoundScore'],
                'Leader R4 Score': leader_final_round_score,
                'Gap Closed': row['GapClosed'],
                'Final Position': int(row['FinalRank']),
                'Winner': ', '.join(winners)
            })

    result_df = pd.DataFrame(results)

    if not result_df.empty:
        # Sort by gap closed (biggest comebacks first)
        result_df = result_df.sort_values('Gap Closed', ascending=False)

    return result_df
"""Data processing functions for bestball and worstball team format analysis.

This module contains functions for calculating bestball (best score per hole)
and worstball (worst score per hole) team scores, as well as formatting and
preparing data for team format displays.
"""


import pandas as pd


def prepare_bestball_data(all_data: pd.DataFrame) -> pd.DataFrame:
    """Prepares data for bestball analysis by adding team round hole identifiers.

    This function creates a unique identifier for each hole in each round,
    which is essential for grouping and team format calculations.

    Args:
        all_data (pd.DataFrame): The complete tournament data.

    Returns:
        pd.DataFrame: The data with a 'TRH' (TEG|Round|Hole) identifier
        column.
    """
    prepared_data = all_data.copy()
    
    # Create TEG|Round|Hole identifier for grouping by specific holes
    prepared_data['TRH'] = prepared_data[['TEGNum', 'Round', 'Hole']].astype(str).agg('|'.join, axis=1)
    
    return prepared_data


def get_bestball_columns() -> tuple[list, list]:
    """Defines the column sets for bestball analysis.

    This function centralizes the column definitions to ensure consistent
    processing by separating grouping fields from value fields.

    Returns:
        tuple: A tuple containing two lists:
            - bestball_cols (list): The columns to use for grouping.
            - value_cols (list): The columns containing the values to be
              aggregated.
    """
    bestball_cols = ['TEG', 'TEGNum', 'Round', 'Course', 'Year']
    value_cols = ['GrossVP', 'Sc']
    
    return bestball_cols, value_cols


def calculate_bestball_scores(filtered_data: pd.DataFrame) -> pd.DataFrame:
    """Calculates bestball team scores (best score per hole).

    This function creates a team format where the best player's score counts
    for each hole. It groups by hole and takes the lowest score, then
    aggregates the scores to create round totals.

    Args:
        filtered_data (pd.DataFrame): The filtered tournament data.

    Returns:
        pd.DataFrame: A DataFrame of bestball team scores by round.
    """
    bestball_cols, value_cols = get_bestball_columns()
    
    # For each hole, take the best (lowest) score
    bestball_holes = filtered_data.groupby('TRH').apply(
        lambda x: x.nsmallest(1, 'Sc')
    ).reset_index(drop=True)
    
    # Sum hole scores to get round totals
    bestball_rounds = bestball_holes.groupby(bestball_cols)[value_cols].sum().reset_index()
    bestball_rounds['Sc'] = bestball_rounds['Sc'].astype(int)
    
    return bestball_rounds


def calculate_worstball_scores(filtered_data: pd.DataFrame) -> pd.DataFrame:
    """Calculates worstball team scores (worst score per hole).

    This function creates a team format where the worst player's score counts
    for each hole. It groups by hole and takes the highest score, then
    aggregates the scores to create round totals.

    Args:
        filtered_data (pd.DataFrame): The filtered tournament data.

    Returns:
        pd.DataFrame: A DataFrame of worstball team scores by round.
    """
    bestball_cols, value_cols = get_bestball_columns()
    
    # For each hole, take the worst (highest) score
    worstball_holes = filtered_data.groupby('TRH').apply(
        lambda x: x.nlargest(1, 'Sc')
    ).reset_index(drop=True)
    
    # Sum hole scores to get round totals
    worstball_rounds = worstball_holes.groupby(bestball_cols)[value_cols].sum().reset_index()
    worstball_rounds['Sc'] = worstball_rounds['Sc'].astype(int)
    
    return worstball_rounds


def format_team_scores_for_display(team_data: pd.DataFrame, sort_by_best: bool = True) -> pd.DataFrame:
    """Formats team scores for display.

    This function applies consistent formatting for team format displays,
    including sorting by performance and formatting vs-par values.

    Args:
        team_data (pd.DataFrame): The raw team scores data.
        sort_by_best (bool, optional): Whether to sort by best performance
            (True) or worst (False). Defaults to True.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for display.
    """
    from utils import format_vs_par
    
    bestball_cols, value_cols = get_bestball_columns()
    
    # Sort by GrossVP performance
    formatted_data = team_data[bestball_cols + value_cols].sort_values(
        by='GrossVP', 
        ascending=sort_by_best
    ).copy()
    
    # Format GrossVP values with vs-par notation
    formatted_data['GrossVP'] = formatted_data['GrossVP'].apply(format_vs_par)
    
    return formatted_data
"""Data processing functions for scorecard display and user interface.

This module contains functions for processing scorecard selection options,
validating scorecard data, and preparing data for different scorecard types.
"""


import pandas as pd


def prepare_scorecard_selection_options(all_data: pd.DataFrame) -> dict:
    """Prepares dropdown options for the scorecard selection interface.

    This function creates consistent, sorted options for all scorecard
    selection dropdowns, ensuring the user interface has complete and current
    data options.

    Args:
        all_data (pd.DataFrame): The complete dataset with all hole-by-hole
            data.

    Returns:
        dict: A dictionary containing sorted lists for player, TEG, and round
        options.
    """
    return {
        'players': sorted(all_data['Pl'].unique()),
        'tournaments': sorted(all_data['TEGNum'].unique()),
        'all_data': all_data  # Keep reference for dynamic round filtering
    }


def get_round_options_for_tournament(all_data: pd.DataFrame, selected_tegnum: int) -> list:
    """Gets the available rounds for a specific tournament.

    This function dynamically updates the round options based on the selected
    tournament, ensuring that users only see valid round choices.

    Args:
        all_data (pd.DataFrame): The complete dataset.
        selected_tegnum (int): The selected tournament number.

    Returns:
        list: A sorted list of available rounds for the tournament.
    """
    return sorted(all_data[all_data['TEGNum'] == selected_tegnum]['Round'].unique())


def validate_and_prepare_single_round_data(rd_data: pd.DataFrame) -> tuple[bool, pd.DataFrame, str]:
    """Validates and prepares data for a single round scorecard display.

    This function ensures that the scorecard data is complete (18 holes) and
    properly formatted, providing clear error messages for any data issues.

    Args:
        rd_data (pd.DataFrame): The raw round data.

    Returns:
        tuple: A tuple containing:
            - is_valid (bool): True if the data is valid, False otherwise.
            - prepared_data (pd.DataFrame or None): The prepared data, or
              None if invalid.
            - error_message (str or None): An error message, or None if
              valid.
    """
    if len(rd_data) == 0:
        return False, None, "No data found for the selected round"
    
    # Define columns needed for scorecard display
    output_cols = ['Hole', 'PAR', 'SI', 'HCStrokes', 'Sc', 'GrossVP', 'NetVP', 'Stableford']
    output_data = rd_data[output_cols].copy()
    
    # Convert numeric data to integers, handling NaN values
    def to_int_or_zero(x):
        if pd.isna(x):
            return 0
        return int(x)
    
    # Apply conversion to all numeric columns
    numeric_columns = output_data.select_dtypes(include=['float64', 'int64']).columns
    for col in numeric_columns:
        output_data[col] = output_data[col].map(to_int_or_zero)
    
    # Validate that we have complete 18-hole data
    if len(output_data) != 18:
        return False, None, f"Expected 18 holes, found {len(output_data)} holes for this round."
    
    return True, output_data, None


def get_scorecard_type_mapping() -> tuple[list, list]:
    """Defines the mapping between internal tab names and user-friendly display names.

    This function separates internal logic names from user-facing descriptions,
    making it easy to update display text without changing the logic.

    Returns:
        tuple: A tuple containing:
            - tab_names (list): A list of internal tab names.
            - display_names (list): A list of user-friendly display names.
    """
    tab_names = ["1 Round / All Players", "1 Player / All Rounds", "1 Round / 1 Player"]
    display_names = ["Round Comparison (all players)", "Tournament view (one player)", "Single Player Round"]
    
    return tab_names, display_names


def determine_control_states(selected_tab: str) -> dict:
    """Determines which UI controls should be enabled or disabled.

    This function provides clear logic for which controls are relevant for
    each scorecard type, preventing user confusion by disabling irrelevant
    options.

    Args:
        selected_tab (str): The currently selected scorecard type.

    Returns:
        dict: A dictionary of control states for player and round selection.
    """
    return {
        'player_disabled': (selected_tab == "1 Round / All Players"),
        'round_disabled': (selected_tab == "1 Player / All Rounds")
    }


def prepare_tournament_display_data(tournament_data: pd.DataFrame) -> dict or None:
    """Prepares data for the tournament view display.

    This function extracts the necessary display information for tournament
    scorecard headers, ensuring a consistent naming format.

    Args:
        tournament_data (pd.DataFrame): The raw tournament data.

    Returns:
        dict or None: The prepared data with the player name and tournament
        name, or None if the input data is empty.
    """
    if len(tournament_data) == 0:
        return None
        
    return {
        'player_name': tournament_data['Player'].iloc[0],
        'teg_name': f"TEG {tournament_data['TEGNum'].iloc[0]}"
    }


# initialize_scorecard_session_state() - MOVED TO streamlit/utils.py
# This function uses st.session_state which is Streamlit-specific


# === TEG STATUS FUNCTIONS (Fast Checks) ===

def get_last_completed_teg_fast() -> tuple:
    """Get the highest TEG number from completed_tegs.csv with round count.

    Uses status file for fast lookup without loading full dataset.

    Returns:
        tuple: (teg_num, rounds) or (None, 0) if no completed TEGs

    Examples:
        >>> teg_num, rounds = get_last_completed_teg_fast()
        >>> if teg_num:
        ...     print(f"Last completed: TEG {teg_num} with {rounds} rounds")
    """
    from ..io.file_operations import read_file

    try:
        completed_tegs = read_file('data/completed_tegs.csv')
        if completed_tegs.empty:
            return None, 0

        max_row = completed_tegs.loc[completed_tegs['TEGNum'].idxmax()]
        return int(max_row['TEGNum']), int(max_row['Rounds'])

    except Exception as e:
        logger.warning(f"Error reading completed TEGs status file: {e}")
        return None, 0


def get_current_in_progress_teg_fast() -> tuple:
    """Get the current in-progress TEG with round count.

    Uses status file for fast lookup without loading full dataset.

    Returns:
        tuple: (teg_num, rounds) or (None, 0) if no TEGs in progress

    Examples:
        >>> teg_num, rounds = get_current_in_progress_teg_fast()
        >>> if teg_num:
        ...     print(f"In progress: TEG {teg_num}, {rounds} rounds played")
    """
    from ..io.file_operations import read_file

    try:
        in_progress_tegs = read_file('data/in_progress_tegs.csv')
        if in_progress_tegs.empty:
            return None, 0

        # Should typically be only one in-progress TEG, get the first one
        current_row = in_progress_tegs.iloc[0]
        return int(current_row['TEGNum']), int(current_row['Rounds'])

    except Exception as e:
        logger.warning(f"Error reading in-progress TEGs status file: {e}")
        return None, 0


def has_incomplete_teg_fast() -> bool:
    """Fast check if there are any incomplete TEGs using status files.

    Returns:
        bool: True if there are TEGs in progress, False otherwise

    Examples:
        >>> if has_incomplete_teg_fast():
        ...     print("There's a TEG in progress!")
    """
    from ..io.file_operations import read_file

    try:
        in_progress_tegs = read_file('data/in_progress_tegs.csv')
        return not in_progress_tegs.empty

    except Exception as e:
        logger.warning(f"Error checking for incomplete TEGs: {e}")
        return False


def filter_data_by_teg(all_data: pd.DataFrame, selected_tegnum) -> pd.DataFrame:
    """Filter data by selected TEG tournament.

    Args:
        all_data: Complete tournament data
        selected_tegnum: Selected TEG number or "All TEGs"

    Returns:
        pd.DataFrame: Filtered data for selected tournament or complete data

    Purpose:
        Applies consistent TEG filtering logic across different analysis pages.
        Returns complete dataset when "All TEGs" is selected.

    Examples:
        >>> filtered = filter_data_by_teg(all_data, 18)
        >>> filtered = filter_data_by_teg(all_data, "All TEGs")  # Returns all
    """
    if selected_tegnum != 'All TEGs':
        selected_tegnum_int = int(selected_tegnum)
        return all_data[all_data['TEGNum'] == selected_tegnum_int]
    else:
        return all_data


def get_teg_leaderboard(df: pd.DataFrame, measure: str, teg_num: int = None) -> pd.DataFrame:
    """Generate a tournament leaderboard table with round-by-round scores and totals.

    Args:
        df (pd.DataFrame): Tournament data (either full dataset or pre-filtered to a TEG)
        measure (str): Score column to rank by - 'Stableford', 'GrossVP', 'NetVP', or 'Sc'
        teg_num (int, optional): TEG number to filter. If None, assumes df is already filtered
            or contains data for all rounds you want in the leaderboard.

    Returns:
        pd.DataFrame: Leaderboard with columns: Rank, Player, R1, R2, R3, R4, Total
                     Players sorted by measure (Stableford descending, others ascending)

    Purpose:
        Transforms aggregated round-level data into a display-ready leaderboard
        suitable for any UI framework (Streamlit, NiceGUI, etc).

    Examples:
        >>> # Method 1: Filter first, then leaderboard
        >>> teg_18 = filter_data_by_teg(all_data, 18)
        >>> aggregated = aggregate_data(teg_18, 'Round')
        >>> leaderboard = get_teg_leaderboard(aggregated, 'Stableford')

        >>> # Method 2: Pass teg_num to function
        >>> aggregated = aggregate_data(all_data, 'Round')
        >>> leaderboard = get_teg_leaderboard(aggregated, 'Stableford', teg_num=18)
    """
    # Filter by TEG if specified
    data = df.copy()
    if teg_num is not None:
        data = data[data['TEGNum'] == teg_num]

    if data.empty:
        return pd.DataFrame()

    # Pivot to Player rows × Round columns
    pivoted = data.pivot_table(
        index='Player',
        columns='Round',
        values=measure,
        aggfunc='first'
    )

    # Add total column
    pivoted['Total'] = pivoted.sum(axis=1)

    # Determine sort order based on measure type
    # Stableford: higher is better (descending)
    # GrossVP, NetVP, Sc: lower is better (ascending)
    ascending = measure != 'Stableford'

    # Sort by Total
    pivoted = pivoted.sort_values('Total', ascending=ascending)

    # Reset index to make Player a column
    pivoted = pivoted.reset_index()

    # Rename columns to R1, R2, R3, R4 format
    pivoted.columns = [
        f'R{int(col)}' if isinstance(col, (int, float)) else col
        for col in pivoted.columns
    ]

    # Add Rank column
    pivoted['Rank'] = pivoted['Total'].rank(method='min', ascending=ascending).astype(int)

    # Handle tied ranks (show "1=" for ties)
    duplicated_scores = pivoted['Total'].duplicated(keep=False)
    pivoted.loc[duplicated_scores, 'Rank'] = pivoted.loc[duplicated_scores, 'Rank'].astype(str) + '='

    # Reorder columns: Rank, Player, R1, R2, ..., Total
    round_cols = [col for col in pivoted.columns if col.startswith('R') and col != 'Rank']
    columns = ['Rank', 'Player'] + round_cols + ['Total']
    leaderboard = pivoted[columns]

    logger.info(f"Leaderboard created for {measure} (teg_num={teg_num}).")
    return leaderboard


def get_round_leaderboard(df: pd.DataFrame, measure: str, teg_num: int = None, round_num: int = None) -> pd.DataFrame:
    """Generate a single-round leaderboard table.

    Args:
        df (pd.DataFrame): Tournament data
        measure (str): Score column to rank by - 'Stableford', 'GrossVP', 'NetVP', or 'Sc'
        teg_num (int, optional): TEG number to filter
        round_num (int, optional): Round number to filter

    Returns:
        pd.DataFrame: Leaderboard with columns: Rank, Player, Measure
                     Players sorted by measure

    Purpose:
        Creates a simplified leaderboard for a single round, useful for
        round-by-round analysis or comparing round results across tournaments.

    Examples:
        >>> leaderboard = get_round_leaderboard(all_data, 'Stableford', teg_num=18, round_num=1)
    """
    # Filter data
    data = df.copy()
    if teg_num is not None:
        data = data[data['TEGNum'] == teg_num]
    if round_num is not None:
        data = data[data['Round'] == round_num]

    if data.empty:
        return pd.DataFrame()

    # Aggregate by player (sum the measure for the round)
    aggregated = data.groupby('Player', as_index=False)[measure].sum()

    # Determine sort order based on measure type
    ascending = measure != 'Stableford'

    # Sort by measure
    aggregated = aggregated.sort_values(measure, ascending=ascending)

    # Add Rank column
    aggregated['Rank'] = aggregated[measure].rank(method='min', ascending=ascending).astype(int)

    # Handle tied ranks
    duplicated_scores = aggregated[measure].duplicated(keep=False)
    aggregated.loc[duplicated_scores, 'Rank'] = aggregated.loc[duplicated_scores, 'Rank'].astype(str) + '='

    # Reorder columns
    leaderboard = aggregated[['Rank', 'Player', measure]]

    logger.info(f"Round leaderboard created for {measure} (teg_num={teg_num}, round_num={round_num}).")
    return leaderboard