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
    Prepare good streaks data combining selected columns from both regular and inverse streaks.

    Args:
        all_data (pd.DataFrame): Raw tournament data

    Returns:
        pd.DataFrame: Table with good streak columns: Birdies [or better], Pars [or better], No +2s, No TBPs

    Purpose:
        Creates a focused table showing positive streaks for competitive display
    """
    # Get regular streaks (for Birdies, Pars or Better, Bogey or better)
    data_with_streaks = calculate_multi_score_running_sum(all_data)
    regular_summary = summarize_multi_score_running_sum(data_with_streaks)

    # Get inverse streaks (for No TBPs)
    data_with_inverse_streaks = calculate_inverse_multi_score_running_sum(all_data)
    inverse_summary = summarize_inverse_multi_score_running_sum(data_with_inverse_streaks)

    # Combine the relevant columns
    good_streaks = pd.DataFrame()
    good_streaks['Player'] = regular_summary['Player']
    good_streaks['Birdies*'] = regular_summary['Birdies']
    good_streaks['Pars*'] = regular_summary['Pars_or_Better']
    good_streaks['No +2s**'] = regular_summary['Bogey or better']
    good_streaks['No TBPs'] = inverse_summary['TBPs']

    # Sort by Pars* for consistent ordering
    good_streaks = good_streaks.sort_values('Pars*', ascending=False)

    return good_streaks


def prepare_bad_streaks_data(all_data):
    """
    Prepare bad streaks data combining selected columns from both regular and inverse streaks.

    Args:
        all_data (pd.DataFrame): Raw tournament data

    Returns:
        pd.DataFrame: Table with bad streak columns: No eagles, No birdies, Bogey or worse, Double Bogey or worse, TBP

    Purpose:
        Creates a focused table showing negative streaks for competitive display
    """
    # Get regular streaks (for TBP, Double Bogey or worse)
    data_with_streaks = calculate_multi_score_running_sum(all_data)
    regular_summary = summarize_multi_score_running_sum(data_with_streaks)

    # Get inverse streaks (for No eagles, No birdies, Bogey or worse)
    data_with_inverse_streaks = calculate_inverse_multi_score_running_sum(all_data)
    inverse_summary = summarize_inverse_multi_score_running_sum(data_with_inverse_streaks)

    # Combine the relevant columns
    bad_streaks = pd.DataFrame()
    bad_streaks['Player'] = inverse_summary['Player']
    bad_streaks['No Eagles'] = inverse_summary['Eagles']
    bad_streaks['No Birdies*'] = inverse_summary['Birdies']
    bad_streaks['Over par'] = inverse_summary['Pars_or_Better']
    bad_streaks['+2s**'] = regular_summary['Double Bogey or worse']
    bad_streaks['TBPs'] = regular_summary['TBPs']

    # Sort by Over par for consistent ordering
    bad_streaks = bad_streaks.sort_values('Over par', ascending=False)

    return bad_streaks