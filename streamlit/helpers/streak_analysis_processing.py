"""
Data processing functions for streak analysis and consecutive scoring achievements.

This module contains functions for:
- Calculating consecutive scoring achievements (birdies, pars, etc.)
- Tracking running streaks across player careers
- Summarizing maximum streaks by player and score type
"""

import pandas as pd
import numpy as np


def get_score_type_definitions():
    """
    Define score type conditions for streak analysis.

    Returns:
        dict: Score type definitions with lambda functions for conditions

    Purpose:
        Centralizes score type definitions for consistent streak calculations
        Each condition returns True when the streak should continue
    """
    score_types = {
        'Pars_or_Better': lambda x: x <= 0,    # At or under par
        'Birdies': lambda x: x == -1,           # Exactly one under par
        'TBPs': lambda x: x > 2,                # Triple bogey or worse (3+ over par)
        'Bogey or better': lambda x: x < 2,     # Better than double bogey
        'Double Bogey or worse': lambda x: x >= 2  # Double bogey or worse (2+ over par)
    }

    return score_types


def get_inverse_score_type_definitions():
    """
    Define inverse score type conditions for streak analysis (consecutive holes WITHOUT each score type).

    Returns:
        dict: Inverse score type definitions with lambda functions for conditions

    Purpose:
        Centralizes inverse score type definitions for consistent streak calculations
        Each condition returns True when the streak should continue (i.e., when NOT achieving the score type)
    """
    inverse_score_types = {
        'Eagles': lambda x: x >= -1,            # NOT eagles (birdie or worse)
        'Birdies': lambda x: x >= 0,            # NOT birdies (par or worse)
        'Pars_or_Better': lambda x: x > 0,      # NOT pars or better (bogey or worse)
        'TBPs': lambda x: x <= 2                # NOT triple bogey+ (double bogey or better)
    }

    return inverse_score_types


def calculate_multi_score_running_sum(df):
    """
    Calculate running streak counts for multiple score types across all players.
    
    Args:
        df (pd.DataFrame): Tournament data with GrossVP and Career Count columns
        
    Returns:
        pd.DataFrame: Original data with added RunningSum columns for each score type
        
    Purpose:
        Tracks consecutive achievements (consecutive pars, consecutive birdies, etc.)
        Uses Career Count to maintain chronological order across all tournaments
        Resets streak count when condition fails, continues when condition met
    """
    # Sort by player and chronological order (Career Count)
    df_sorted = df.sort_values(['Player', 'Career Count'])
    
    # Get score type definitions
    score_types = get_score_type_definitions()
    
    # Initialize running sum columns
    for score_type in score_types:
        df_sorted[f'RunningSum_{score_type}'] = 0
    
    def calculate_player_streaks(group):
        """Calculate running streaks for a single player."""
        for score_type, condition in score_types.items():
            running_sum = 0
            for i, row in group.iterrows():
                if condition(row['GrossVP']):
                    running_sum += 1  # Continue streak
                else:
                    running_sum = 0   # Reset streak
                group.at[i, f'RunningSum_{score_type}'] = running_sum
        return group

    # Apply streak calculation to each player
    df_sorted = df_sorted.groupby('Player', group_keys=False).apply(calculate_player_streaks)
    
    # Merge calculated streaks back to original dataframe
    merge_columns = ['Player', 'Career Count'] + [f'RunningSum_{score_type}' for score_type in score_types]
    df_with_streaks = df.merge(df_sorted[merge_columns], on=['Player', 'Career Count'], how='left')
    
    return df_with_streaks


def calculate_inverse_multi_score_running_sum(df):
    """
    Calculate running streak counts for multiple inverse score types across all players.

    Args:
        df (pd.DataFrame): Tournament data with GrossVP and Career Count columns

    Returns:
        pd.DataFrame: Original data with added InverseRunningSum columns for each score type

    Purpose:
        Tracks consecutive holes WITHOUT achievements (consecutive holes without birdies, etc.)
        Uses Career Count to maintain chronological order across all tournaments
        Resets streak count when condition fails, continues when condition met
    """
    # Sort by player and chronological order (Career Count)
    df_sorted = df.sort_values(['Player', 'Career Count'])

    # Get inverse score type definitions
    inverse_score_types = get_inverse_score_type_definitions()

    # Initialize running sum columns
    for score_type in inverse_score_types:
        df_sorted[f'InverseRunningSum_{score_type}'] = 0

    def calculate_player_inverse_streaks(group):
        """Calculate running inverse streaks for a single player."""
        for score_type, condition in inverse_score_types.items():
            running_sum = 0
            for i, row in group.iterrows():
                if condition(row['GrossVP']):
                    running_sum += 1  # Continue streak
                else:
                    running_sum = 0   # Reset streak
                group.at[i, f'InverseRunningSum_{score_type}'] = running_sum
        return group

    # Apply streak calculation to each player
    df_sorted = df_sorted.groupby('Player', group_keys=False).apply(calculate_player_inverse_streaks)

    # Merge calculated streaks back to original dataframe
    merge_columns = ['Player', 'Career Count'] + [f'InverseRunningSum_{score_type}' for score_type in inverse_score_types]
    df_with_inverse_streaks = df.merge(df_sorted[merge_columns], on=['Player', 'Career Count'], how='left')

    return df_with_inverse_streaks


def summarize_multi_score_running_sum(df):
    """
    Summarize maximum streak lengths for each player and score type.
    
    Args:
        df (pd.DataFrame): Data with RunningSum columns from calculate_multi_score_running_sum()
        
    Returns:
        pd.DataFrame: Summary table with maximum streaks by player and score type
        
    Purpose:
        Creates final summary showing each player's longest streak for each achievement type
        Sorted by best "Pars or Better" streak for competitive comparison
    """
    # Define score types in display order
    score_types = ['Birdies', 'Pars_or_Better', 'TBPs', 'Bogey or better', 'Double Bogey or worse']
    
    # Validate that required columns exist
    for score_type in score_types:
        if f'RunningSum_{score_type}' not in df.columns:
            raise ValueError(f"RunningSum_{score_type} column not found. Please calculate running sums first.")

    # Group by player and find maximum streak for each score type
    summary = df.groupby('Player').agg({
        f'RunningSum_{score_type}': 'max' for score_type in score_types
    }).reset_index()
    
    # Rename columns for clean display
    summary.columns = ['Player'] + score_types
    
    # Sort by 'Pars_or_Better' streak length (descending)
    summary = summary.sort_values('Pars_or_Better', ascending=False)
    
    return summary


def summarize_inverse_multi_score_running_sum(df):
    """
    Summarize maximum inverse streak lengths for each player and score type.

    Args:
        df (pd.DataFrame): Data with InverseRunningSum columns from calculate_inverse_multi_score_running_sum()

    Returns:
        pd.DataFrame: Summary table with maximum inverse streaks by player and score type

    Purpose:
        Creates final summary showing each player's longest streak WITHOUT each achievement type
        Sorted by best "WITHOUT Pars or Better" streak for competitive comparison
    """
    # Define inverse score types in display order
    inverse_score_types = ['Eagles', 'Birdies', 'Pars_or_Better', 'TBPs']

    # Validate that required columns exist
    for score_type in inverse_score_types:
        if f'InverseRunningSum_{score_type}' not in df.columns:
            raise ValueError(f"InverseRunningSum_{score_type} column not found. Please calculate inverse running sums first.")

    # Group by player and find maximum streak for each score type
    summary = df.groupby('Player').agg({
        f'InverseRunningSum_{score_type}': 'max' for score_type in inverse_score_types
    }).reset_index()

    # Rename columns for clean display
    summary.columns = ['Player'] + inverse_score_types

    # Sort by 'Pars_or_Better' inverse streak length (descending)
    summary = summary.sort_values('Pars_or_Better', ascending=False)

    return summary


def prepare_streak_data_for_display(all_data):
    """
    Complete workflow to prepare streak data for display.
    
    Args:
        all_data (pd.DataFrame): Raw tournament data
        
    Returns:
        pd.DataFrame: Final streak summary table ready for display
        
    Purpose:
        Combines the full streak calculation workflow into a single function
        Handles the complete process from raw data to display-ready summary
    """
    # Calculate running streaks for all score types
    data_with_streaks = calculate_multi_score_running_sum(all_data)
    
    # Summarize maximum streaks by player
    streak_summary = summarize_multi_score_running_sum(data_with_streaks)

    return streak_summary


def prepare_inverse_streak_data_for_display(all_data):
    """
    Complete workflow to prepare inverse streak data for display.

    Args:
        all_data (pd.DataFrame): Raw tournament data

    Returns:
        pd.DataFrame: Final inverse streak summary table ready for display

    Purpose:
        Combines the full inverse streak calculation workflow into a single function
        Handles the complete process from raw data to display-ready inverse summary
    """
    # Calculate running inverse streaks for all score types
    data_with_inverse_streaks = calculate_inverse_multi_score_running_sum(all_data)

    # Summarize maximum inverse streaks by player
    inverse_streak_summary = summarize_inverse_multi_score_running_sum(data_with_inverse_streaks)

    return inverse_streak_summary


def prepare_good_streaks_data(all_data):
    """
    Prepare good streaks data using cached streak calculations with asterisk marking.

    Args:
        all_data (pd.DataFrame): Raw tournament data (used for player mapping only)

    Returns:
        pd.DataFrame: Table with good streak columns: Birdies, Pars, No +2s, No TBPs
                     Values marked with '*' when that max streak is currently active

    Purpose:
        Creates a focused table showing positive streaks using fast cached data
    """
    try:
        from utils import read_file, STREAKS_PARQUET

        # Read cached streak data
        streaks_df = read_file(STREAKS_PARQUET)

        # Get player mapping from all_data
        player_mapping = get_player_mapping(all_data)

        # Get both max and current streaks for comparison
        max_streaks = get_max_streaks(streaks_df)
        current_streaks = get_current_streaks(streaks_df)

        # Identify where current equals max
        equals_max = get_current_equals_max_streaks(max_streaks, current_streaks)

        # Transform to display format with asterisk marking
        good_streaks = transform_cached_good_streaks(max_streaks, player_mapping, equals_max)

        return good_streaks

    except Exception as e:
        # Fallback to original calculation if cache not available
        import logging
        logging.warning(f"Could not read streaks cache, falling back to calculation: {e}")

        # Original calculation code as fallback
        data_with_streaks = calculate_multi_score_running_sum(all_data)
        regular_summary = summarize_multi_score_running_sum(data_with_streaks)

        data_with_inverse_streaks = calculate_inverse_multi_score_running_sum(all_data)
        inverse_summary = summarize_inverse_multi_score_running_sum(data_with_inverse_streaks)

        good_streaks = pd.DataFrame()
        good_streaks['Player'] = regular_summary['Player']
        good_streaks['Birdies'] = regular_summary['Birdies']
        good_streaks['Pars'] = regular_summary['Pars_or_Better']
        good_streaks['No +2s'] = regular_summary['Bogey or better']
        good_streaks['No TBPs'] = inverse_summary['TBPs']

        good_streaks = good_streaks.sort_values('Pars', ascending=False)
        return good_streaks


def prepare_bad_streaks_data(all_data):
    """
    Prepare bad streaks data using cached streak calculations with asterisk marking.

    Args:
        all_data (pd.DataFrame): Raw tournament data (used for player mapping only)

    Returns:
        pd.DataFrame: Table with bad streak columns: No eagles, No birdies, Over par, +2s, TBPs
                     Values marked with '*' when that max streak is currently active

    Purpose:
        Creates a focused table showing negative streaks using fast cached data
    """
    try:
        from utils import read_file, STREAKS_PARQUET

        # Read cached streak data
        streaks_df = read_file(STREAKS_PARQUET)

        # Get player mapping from all_data
        player_mapping = get_player_mapping(all_data)

        # Get both max and current streaks for comparison
        max_streaks = get_max_streaks(streaks_df)
        current_streaks = get_current_streaks(streaks_df)

        # Identify where current equals max
        equals_max = get_current_equals_max_streaks(max_streaks, current_streaks)

        # Transform to display format with asterisk marking
        bad_streaks = transform_cached_bad_streaks(max_streaks, player_mapping, equals_max)

        return bad_streaks

    except Exception as e:
        # Fallback to original calculation if cache not available
        import logging
        logging.warning(f"Could not read streaks cache, falling back to calculation: {e}")

        # Original calculation code as fallback
        data_with_streaks = calculate_multi_score_running_sum(all_data)
        regular_summary = summarize_multi_score_running_sum(data_with_streaks)

        data_with_inverse_streaks = calculate_inverse_multi_score_running_sum(all_data)
        inverse_summary = summarize_inverse_multi_score_running_sum(data_with_inverse_streaks)

        bad_streaks = pd.DataFrame()
        bad_streaks['Player'] = inverse_summary['Player']
        bad_streaks['No Eagles'] = inverse_summary['Eagles']
        bad_streaks['No Birdies'] = inverse_summary['Birdies']
        bad_streaks['Over par'] = inverse_summary['Pars_or_Better']
        bad_streaks['+2s'] = regular_summary['Double Bogey or worse']
        bad_streaks['TBPs'] = regular_summary['TBPs']

        bad_streaks = bad_streaks.sort_values('Over par', ascending=False)
        return bad_streaks


def get_current_streaks_data(all_data):
    """
    Calculate current (ongoing) streaks for all players and score types.

    Args:
        all_data (pd.DataFrame): Raw tournament data with Career Count column

    Returns:
        pd.DataFrame: Current streak values for each player and score type

    Purpose:
        Shows what streak each player is currently on (not their historical maximum)
        Uses the most recently played hole for each player to determine current status
    """
    # Calculate all running streaks
    df_with_streaks = calculate_multi_score_running_sum(all_data)
    df_with_all_streaks = calculate_inverse_multi_score_running_sum(df_with_streaks)

    # Find each player's most recent hole (maximum Career Count)
    max_career_counts = df_with_all_streaks.groupby('Player')['Career Count'].max().reset_index()
    max_career_counts.columns = ['Player', 'Max_Career_Count']

    # Get current streak values at most recent hole for each player
    current_streaks = df_with_all_streaks.merge(max_career_counts, on='Player')
    current_streaks = current_streaks[current_streaks['Career Count'] == current_streaks['Max_Career_Count']]

    # Select relevant columns for current streaks
    score_types = list(get_score_type_definitions().keys())
    inverse_score_types = list(get_inverse_score_type_definitions().keys())

    streak_columns = ['Player'] + [f'RunningSum_{score_type}' for score_type in score_types]
    inverse_streak_columns = [f'InverseRunningSum_{score_type}' for score_type in inverse_score_types]

    all_columns = streak_columns + inverse_streak_columns + ['Career Count']
    current_streaks = current_streaks[all_columns].copy()

    return current_streaks


def prepare_current_good_streaks_data(all_data):
    """
    Prepare current good streaks data using cached streak calculations with asterisk marking.

    Args:
        all_data (pd.DataFrame): Raw tournament data (used for player mapping only)

    Returns:
        pd.DataFrame: Table with current good streak values: Birdies, Pars, No +2s, No TBPs
                     Values marked with '*' when current equals historical maximum

    Purpose:
        Shows current positive streaks using fast cached data
    """
    try:
        from utils import read_file, STREAKS_PARQUET

        # Read cached streak data
        streaks_df = read_file(STREAKS_PARQUET)

        # Get player mapping from all_data
        player_mapping = get_player_mapping(all_data)

        # Get both max and current streaks for comparison
        max_streaks = get_max_streaks(streaks_df)
        current_streaks = get_current_streaks(streaks_df)

        # Identify where current equals max
        equals_max = get_current_equals_max_streaks(max_streaks, current_streaks)

        # Transform to display format with asterisk marking
        good_streaks = transform_cached_good_streaks(current_streaks, player_mapping, equals_max)

        return good_streaks

    except Exception as e:
        # Fallback to original calculation if cache not available
        import logging
        logging.warning(f"Could not read streaks cache, falling back to calculation: {e}")

        # Original calculation code as fallback
        current_streaks = get_current_streaks_data(all_data)

        good_streaks = pd.DataFrame()
        good_streaks['Player'] = current_streaks['Player']
        good_streaks['Birdies'] = current_streaks['RunningSum_Birdies']
        good_streaks['Pars'] = current_streaks['RunningSum_Pars_or_Better']
        good_streaks['No +2s'] = current_streaks['RunningSum_Bogey or better']
        good_streaks['No TBPs'] = current_streaks['InverseRunningSum_TBPs']

        good_streaks = good_streaks.sort_values('Pars', ascending=False)
        return good_streaks


def prepare_current_bad_streaks_data(all_data):
    """
    Prepare current bad streaks data using cached streak calculations with asterisk marking.

    Args:
        all_data (pd.DataFrame): Raw tournament data (used for player mapping only)

    Returns:
        pd.DataFrame: Table with current bad streak values: No eagles, No birdies, Over par, +2s, TBPs
                     Values marked with '*' when current equals historical maximum

    Purpose:
        Shows current negative streaks using fast cached data
    """
    try:
        from utils import read_file, STREAKS_PARQUET

        # Read cached streak data
        streaks_df = read_file(STREAKS_PARQUET)

        # Get player mapping from all_data
        player_mapping = get_player_mapping(all_data)

        # Get both max and current streaks for comparison
        max_streaks = get_max_streaks(streaks_df)
        current_streaks = get_current_streaks(streaks_df)

        # Identify where current equals max
        equals_max = get_current_equals_max_streaks(max_streaks, current_streaks)

        # Transform to display format with asterisk marking
        bad_streaks = transform_cached_bad_streaks(current_streaks, player_mapping, equals_max)

        return bad_streaks

    except Exception as e:
        # Fallback to original calculation if cache not available
        import logging
        logging.warning(f"Could not read streaks cache, falling back to calculation: {e}")

        # Original calculation code as fallback
        current_streaks = get_current_streaks_data(all_data)

        bad_streaks = pd.DataFrame()
        bad_streaks['Player'] = current_streaks['Player']
        bad_streaks['No Eagles'] = current_streaks['InverseRunningSum_Eagles']
        bad_streaks['No Birdies'] = current_streaks['InverseRunningSum_Birdies']
        bad_streaks['Over par'] = current_streaks['InverseRunningSum_Pars_or_Better']
        bad_streaks['+2s'] = current_streaks['RunningSum_Double Bogey or worse']
        bad_streaks['TBPs'] = current_streaks['RunningSum_TBPs']

        bad_streaks = bad_streaks.sort_values('Over par', ascending=False)
        return bad_streaks


import pandas as pd

BOOL_COLS = ["eagle", "birdie", "par_better", "double_bogey", "TBP"]

def build_streaks(all_data: pd.DataFrame, assume_sorted: bool = False) -> pd.DataFrame:
    """
    Create streaks data (flags + true/false streak counters) from all_data.

    Requires columns:
      'Pl', 'HoleID', 'Sc', 'Career Count', 'GrossVP', 'Hole Order Ever'

    Adds boolean flags:
      - eagle         : GrossVP <= -2
      - birdie        : GrossVP <= -1
      - par_better    : GrossVP <= 0
      - double_bogey  : GrossVP > 1
      - TBP           : GrossVP > 2

    Then, for each of the above, adds:
      - <name>_true_streak   : consecutive Trues per player over Career Count
      - <name>_false_streak  : consecutive Falses per player over Career Count

    Parameters
    ----------
    all_data : pd.DataFrame
        Source dataframe with at least the required columns.
    assume_sorted : bool, default False
        If True, assumes rows are already sorted by ['Pl', 'Career Count'].

    Returns
    -------
    pd.DataFrame
        A new dataframe containing the selected base columns, the boolean flags,
        and the per-hole streak counters.
    """
    needed = ['Pl', 'HoleID', 'Sc', 'Career Count', 'GrossVP', 'Hole Order Ever']
    missing = [c for c in needed if c not in all_data.columns]
    if missing:
        raise KeyError(f"build_streaks: missing columns in all_data: {missing}")

    # Base subset
    df = all_data[needed].copy()

    # Boolean flags from GrossVP
    df['eagle']        = df['GrossVP'] <= -2
    df['birdie']       = df['GrossVP'] <= -1
    df['par_better']   = df['GrossVP'] <= 0
    df['double_bogey'] = df['GrossVP'] > 1
    df['TBP']          = df['GrossVP'] > 2

    # Sort once (stable) to ensure streak correctness
    if not assume_sorted:
        df = df.sort_values(['Pl', 'Career Count'], kind='mergesort').reset_index(drop=True)

    # Add streak counters for each boolean column
    for col in BOOL_COLS:
        s = df[col].fillna(False).astype(bool)

        # New streak segment when player changes OR value flips
        reset = df['Pl'].ne(df['Pl'].shift()) | s.ne(s.shift())
        seg_id = reset.cumsum()

        # Position within each segment
        pos = df.groupby(seg_id).cumcount() + 1

        # True/False streaks (0 when condition not met)
        df[f"{col}_true_streak"]  = pos.where(s, 0)
        df[f"{col}_false_streak"] = pos.where(~s, 0)

    return df

def get_max_streaks(streaks_df):
    """Return max streaks for each player in wide form."""
    scols = [c for c in streaks_df.columns if c.endswith("_streak")]
    return (
        streaks_df
        .groupby("Pl", as_index=False)[scols]
        .max()
    )

def get_current_streaks(streaks_df):
    """Return current (latest) streaks for each player in wide form."""
    scols = [c for c in streaks_df.columns if c.endswith("_streak")]
    latest_idx = streaks_df.groupby("Pl")["Career Count"].idxmax()
    return streaks_df.loc[latest_idx, ["Pl"] + scols].reset_index(drop=True)


def get_player_mapping(all_data):
    """Get mapping from Pl to Player names using existing data."""
    return all_data[['Pl', 'Player']].drop_duplicates().set_index('Pl')['Player'].to_dict()


def transform_cached_good_streaks(streaks_df, player_mapping, equals_max_df=None):
    """
    Transform cached streak data into good streaks display format.

    Args:
        streaks_df (pd.DataFrame): Output from get_max_streaks() or get_current_streaks()
        player_mapping (dict): Mapping from Pl to Player names
        equals_max_df (pd.DataFrame, optional): Boolean mask from get_current_equals_max_streaks()

    Returns:
        pd.DataFrame: Table with columns ['Player', 'Birdies', 'Pars', 'No +2s', 'No TBPs']
                     Values marked with '*' when current equals max
    """
    # Create good streaks table with clean column names
    good_streaks = pd.DataFrame()
    good_streaks['Player'] = streaks_df['Pl'].map(player_mapping)

    # Column mapping for good streaks
    column_mapping = {
        'Birdies': 'birdie_true_streak',
        'Pars': 'par_better_true_streak',
        'No +2s': 'double_bogey_false_streak',
        'No TBPs': 'TBP_false_streak'
    }

    # Add each column with optional asterisk marking
    for display_col, streak_col in column_mapping.items():
        values = streaks_df[streak_col].astype(str)

        # Add asterisks where current equals max
        if equals_max_df is not None:
            # Merge to align players
            streak_with_equals = streaks_df[['Pl', streak_col]].merge(
                equals_max_df[['Pl', streak_col]], on='Pl', suffixes=('', '_equals_max')
            )

            # Add asterisk where equals max is True
            mask = streak_with_equals[f'{streak_col}_equals_max']
            values = streak_with_equals[streak_col].astype(str)
            values.loc[mask] = values.loc[mask] + '*'

        good_streaks[display_col] = values

    # Sort by Pars for consistent ordering (extract numeric value for sorting)
    good_streaks['_pars_numeric'] = good_streaks['Pars'].str.replace('*', '').astype(int)
    good_streaks = good_streaks.sort_values('_pars_numeric', ascending=False)
    good_streaks = good_streaks.drop('_pars_numeric', axis=1)

    return good_streaks


def get_current_equals_max_streaks(max_streaks_df, current_streaks_df):
    """
    Identify which current streaks equal maximum streaks for each player.

    Args:
        max_streaks_df (pd.DataFrame): Output from get_max_streaks()
        current_streaks_df (pd.DataFrame): Output from get_current_streaks()

    Returns:
        pd.DataFrame: Boolean mask showing where current equals max for each streak column
    """
    # Get streak columns only
    streak_cols = [col for col in max_streaks_df.columns if col.endswith('_streak')]

    # Merge dataframes on player ID for comparison
    comparison = max_streaks_df[['Pl'] + streak_cols].merge(
        current_streaks_df[['Pl'] + streak_cols],
        on='Pl',
        suffixes=('_max', '_current')
    )

    # Create boolean mask for each streak type
    equals_max = pd.DataFrame()
    equals_max['Pl'] = comparison['Pl']

    for streak_type in streak_cols:
        max_col = f'{streak_type}_max'
        current_col = f'{streak_type}_current'
        equals_max[streak_type] = comparison[max_col] == comparison[current_col]

    return equals_max


def transform_cached_bad_streaks(streaks_df, player_mapping, equals_max_df=None):
    """
    Transform cached streak data into bad streaks display format.

    Args:
        streaks_df (pd.DataFrame): Output from get_max_streaks() or get_current_streaks()
        player_mapping (dict): Mapping from Pl to Player names
        equals_max_df (pd.DataFrame, optional): Boolean mask from get_current_equals_max_streaks()

    Returns:
        pd.DataFrame: Table with columns ['Player', 'No Eagles', 'No Birdies', 'Over par', '+2s', 'TBPs']
                     Values marked with '*' when current equals max
    """
    # Create bad streaks table with clean column names
    bad_streaks = pd.DataFrame()
    bad_streaks['Player'] = streaks_df['Pl'].map(player_mapping)

    # Column mapping for bad streaks
    column_mapping = {
        'No Eagles': 'eagle_false_streak',
        'No Birdies': 'birdie_false_streak',
        'Over par': 'par_better_false_streak',
        '+2s': 'double_bogey_true_streak',
        'TBPs': 'TBP_true_streak'
    }

    # Add each column with optional asterisk marking
    for display_col, streak_col in column_mapping.items():
        values = streaks_df[streak_col].astype(str)

        # Add asterisks where current equals max
        if equals_max_df is not None:
            # Merge to align players
            streak_with_equals = streaks_df[['Pl', streak_col]].merge(
                equals_max_df[['Pl', streak_col]], on='Pl', suffixes=('', '_equals_max')
            )

            # Add asterisk where equals max is True
            mask = streak_with_equals[f'{streak_col}_equals_max']
            values = streak_with_equals[streak_col].astype(str)
            values.loc[mask] = values.loc[mask] + '*'

        bad_streaks[display_col] = values

    # Sort by Over par for consistent ordering (extract numeric value for sorting)
    bad_streaks['_over_par_numeric'] = bad_streaks['Over par'].str.replace('*', '').astype(int)
    bad_streaks = bad_streaks.sort_values('_over_par_numeric', ascending=False)
    bad_streaks = bad_streaks.drop('_over_par_numeric', axis=1)

    return bad_streaks


# === TEG/ROUND WINDOW STREAK FUNCTIONS ===

def adjust_opening_streak(series):
    """
    Adjust streak values to be relative to the start of the selected window.

    Args:
        series: pandas Series of streak values

    Returns:
        pandas Series with adjusted values

    Purpose:
        When analyzing streaks within a specific window (TEG or Round),
        we need to adjust for any pre-existing streak. For example, if a player
        enters a TEG with a 4-hole par streak and pars the first 3 holes,
        their career streak shows 5,6,7 but the TEG-level streak should be 1,2,3.
    """
    if len(series) == 0:
        return series

    opening_val = series.iloc[0]

    # No adjustment needed if starting at 0
    if opening_val == 0:
        return series

    # Check if streak resets to 0 within the window
    has_reset = (series == 0).any()

    if has_reset:
        # Find first reset point
        reset_idx = (series == 0).idxmax()
        result = series.copy()

        # Adjust values before reset (these carry over from before the window)
        mask = series.index < reset_idx
        result.loc[mask] = result.loc[mask] - opening_val + 1

        # Values after reset are already relative to the window
        return result
    else:
        # No reset in window, adjust all values
        return series - opening_val + 1


def find_streak_location(window_data, streak_col, max_value):
    """
    Find where the maximum streak occurred (start and end holes).

    Args:
        window_data: DataFrame with streak data for the window
        streak_col: Name of the adjusted streak column
        max_value: The maximum streak value to locate

    Returns:
        tuple: (from_holeid, to_holeid) or (None, None) if not found

    Purpose:
        Identifies the exact holes where a max streak occurred to provide
        detailed location information (e.g., "T10 R1 H3 to T10 R1 H8").
    """
    if max_value == 0:
        return None, None

    # Find where this max value occurs
    max_locations = window_data[window_data[streak_col] == max_value]

    if len(max_locations) == 0:
        return None, None

    # Take the last occurrence (end of the streak)
    end_idx = max_locations.index[-1]
    end_hole = window_data.loc[end_idx, 'HoleID']

    # Work backwards to find the start
    start_idx = end_idx - max_value + 1
    if start_idx < window_data.index[0]:
        start_idx = window_data.index[0]

    start_hole = window_data.loc[start_idx, 'HoleID']

    return start_hole, end_hole


def format_hole_location(hole_id):
    """
    Convert HoleID format (T10|R01|H01) to display format (T10 R1 H1).

    Args:
        hole_id: String in format "T{teg}|R{round}|H{hole}"

    Returns:
        String in format "T{teg} R{round} H{hole}" with leading zeros removed
    """
    if pd.isna(hole_id) or hole_id is None:
        return ""

    parts = str(hole_id).split('|')
    if len(parts) != 3:
        return hole_id

    teg = parts[0]  # T10
    round_num = int(parts[1].replace('R', ''))  # R01 -> 1
    hole_num = int(parts[2].replace('H', ''))  # H01 -> 1

    return f"{teg} R{round_num} H{hole_num}"


def calculate_window_streaks(window_data):
    """
    Calculate adjusted streaks for a selected window and return detailed results.

    Args:
        window_data: Filtered DataFrame for the selected window (must include
                    'Player', 'HoleID', and all streak columns)

    Returns:
        DataFrame with columns: ['Streak Type', 'Player', 'Max Streak', 'Location']

    Purpose:
        Main function for calculating TEG/Round-level streaks. Takes a filtered
        window of data and calculates max streaks adjusted for any pre-existing
        streaks at the start of the window. Also identifies where each max streak
        occurred within the window.
    """
    if len(window_data) == 0:
        return pd.DataFrame()

    # Get all streak columns
    streak_cols = [c for c in window_data.columns if c.endswith('_streak')]

    # Define friendly names for streak types
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

    # Process each player in the window
    for player in window_data['Player'].unique():
        player_data = window_data[window_data['Player'] == player].copy()

        # Calculate adjusted streaks for each type
        for streak_col in streak_cols:
            adj_col = f'{streak_col}_adj'
            player_data[adj_col] = adjust_opening_streak(player_data[streak_col])

            # Get max value
            max_streak = player_data[adj_col].max()

            # Find location
            from_hole, to_hole = find_streak_location(player_data, adj_col, max_streak)

            # Format location
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

    # Sort by streak type (good streaks first, then bad streaks)
    good_streaks_order = ['Eagles', 'Birdies', 'Pars or Better', 'No +2s', 'No TBPs']
    bad_streaks_order = ['No Eagles', 'No Birdies', 'Over Par', '+2s or Worse', 'TBPs']
    streak_order = good_streaks_order + bad_streaks_order

    results_df['_order'] = results_df['Streak Type'].map({s: i for i, s in enumerate(streak_order)})
    results_df = results_df.sort_values(['_order', 'Player']).drop('_order', axis=1)

    return results_df


def get_player_window_streaks(all_data, streaks_df, player=None, teg=None, round_num=None):
    """
    Quick lookup function to get streak stats for a TEG/Round window.

    Args:
        all_data: Main DataFrame with all golf data
        streaks_df: Streaks DataFrame from read_file(STREAKS_PARQUET)
        player: Player code (e.g., 'JB', 'DM') - optional, if None returns all players
        teg: TEG name (e.g., 'TEG 10') - optional
        round_num: Round number (e.g., 1, 2, 3, 4) - optional

    Returns:
        DataFrame with streak results for the specified window
        Columns: ['Streak Type', 'Player', 'Max Streak', 'Location']

    Example:
        # Get all players' streaks for TEG 10
        result = get_player_window_streaks(all_data, streaks_df, teg='TEG 10')

        # Get JB's streaks for TEG 10
        result = get_player_window_streaks(all_data, streaks_df, player='JB', teg='TEG 10')

        # Get all players' streaks for Round 1 of TEG 10
        result = get_player_window_streaks(all_data, streaks_df, teg='TEG 10', round_num=1)

        # Get JB's streaks for Round 1 of TEG 10
        result = get_player_window_streaks(all_data, streaks_df, player='JB', teg='TEG 10', round_num=1)
    """
    # Merge TEG/Round info
    df = streaks_df.merge(
        all_data[['HoleID', 'TEG', 'TEGNum', 'Round', 'Pl', 'Player']],
        on=['HoleID', 'Pl']
    )

    # Apply filters
    filtered = df.copy()

    if player:
        filtered = filtered[filtered['Pl'] == player]

    if teg:
        filtered = filtered[filtered['TEG'] == teg]

    if round_num is not None:
        filtered = filtered[filtered['Round'] == round_num]

    if len(filtered) == 0:
        return pd.DataFrame()

    # Sort and calculate
    filtered = filtered.sort_values(['Pl', 'TEGNum', 'Round', 'Career Count'])

    # Calculate window streaks
    return calculate_window_streaks(filtered)


def prepare_record_best_streaks_data(all_data):
    """
    Prepare record best (good) streaks data from all career streaks.

    Args:
        all_data (pd.DataFrame): Raw tournament data

    Returns:
        pd.DataFrame: Table with columns ['Streak Type', 'Record', 'Player', 'When']
                     showing the maximum streak for each good streak type
                     Returns all players who share the record (multiple rows per streak type)
                     Marks current streaks with asterisk (*)

    Purpose:
        Identifies all-time record holders for each positive streak type
        Only includes streaks > 1
    """
    from utils import read_file, STREAKS_PARQUET

    # Load streak data
    streaks_df = read_file(STREAKS_PARQUET)

    # Merge with tournament data to get TEG/Round/Player info
    df = streaks_df.merge(
        all_data[['HoleID', 'TEG', 'TEGNum', 'Round', 'Pl', 'Player']],
        on=['HoleID', 'Pl']
    )

    # Find the last hole played overall (maximum HoleID by sorting)
    last_hole = df.sort_values('Hole Order Ever').iloc[-1]['HoleID']

    # Calculate window streaks for all data (no filters)
    df = df.sort_values(['Pl', 'TEGNum', 'Round', 'Career Count'])
    all_streaks = calculate_window_streaks(df)

    # Define good streak types
    good_streak_types = ['Eagles', 'Birdies', 'Pars or Better', 'No +2s', 'No TBPs']

    # Filter for good streaks only
    good_streaks = all_streaks[all_streaks['Streak Type'].isin(good_streak_types)]

    # Find the maximum streak for each streak type and return all matching records
    records = []
    for streak_type in good_streak_types:
        type_data = good_streaks[good_streaks['Streak Type'] == streak_type]
        if len(type_data) > 0:
            max_streak = type_data['Max Streak'].max()

            # Only include if streak is > 1
            if max_streak > 1:
                # Get all rows that match the maximum
                max_rows = type_data[type_data['Max Streak'] == max_streak]

                for _, row in max_rows.iterrows():
                    # Check if this streak ends at the last hole (i.e., it's current)
                    location = row['Location']
                    is_current = location.endswith(format_hole_location(last_hole))

                    # Add asterisk if current
                    record_display = f"{row['Max Streak']}*" if is_current else str(row['Max Streak'])

                    records.append({
                        'Streak Type': streak_type,
                        'Record': record_display,
                        'Player': row['Player'],
                        'When': location
                    })

    records_df = pd.DataFrame(records)
    return records_df


def prepare_record_worst_streaks_data(all_data):
    """
    Prepare record worst (bad) streaks data from all career streaks.

    Args:
        all_data (pd.DataFrame): Raw tournament data

    Returns:
        pd.DataFrame: Table with columns ['Streak Type', 'Record', 'Player', 'When']
                     showing the maximum streak for each bad streak type
                     Returns all players who share the record (multiple rows per streak type)
                     Marks current streaks with asterisk (*)

    Purpose:
        Identifies all-time record holders for each negative streak type
        Only includes streaks > 1
    """
    from utils import read_file, STREAKS_PARQUET

    # Load streak data
    streaks_df = read_file(STREAKS_PARQUET)

    # Merge with tournament data to get TEG/Round/Player info
    df = streaks_df.merge(
        all_data[['HoleID', 'TEG', 'TEGNum', 'Round', 'Pl', 'Player']],
        on=['HoleID', 'Pl']
    )

    # Find the last hole played overall (maximum HoleID by sorting)
    last_hole = df.sort_values('Hole Order Ever').iloc[-1]['HoleID']

    # Calculate window streaks for all data (no filters)
    df = df.sort_values(['Pl', 'TEGNum', 'Round', 'Career Count'])
    all_streaks = calculate_window_streaks(df)

    # Define bad streak types
    bad_streak_types = ['No Eagles', 'No Birdies', 'Over Par', '+2s or Worse', 'TBPs']

    # Filter for bad streaks only
    bad_streaks = all_streaks[all_streaks['Streak Type'].isin(bad_streak_types)]

    # Find the maximum streak for each streak type and return all matching records
    records = []
    for streak_type in bad_streak_types:
        type_data = bad_streaks[bad_streaks['Streak Type'] == streak_type]
        if len(type_data) > 0:
            max_streak = type_data['Max Streak'].max()

            # Only include if streak is > 1
            if max_streak > 1:
                # Get all rows that match the maximum
                max_rows = type_data[type_data['Max Streak'] == max_streak]

                for _, row in max_rows.iterrows():
                    # Check if this streak ends at the last hole (i.e., it's current)
                    location = row['Location']
                    is_current = location.endswith(format_hole_location(last_hole))

                    # Add asterisk if current
                    record_display = f"{row['Max Streak']}*" if is_current else str(row['Max Streak'])

                    records.append({
                        'Streak Type': streak_type,
                        'Record': record_display,
                        'Player': row['Player'],
                        'When': location
                    })

    records_df = pd.DataFrame(records)
    return records_df
