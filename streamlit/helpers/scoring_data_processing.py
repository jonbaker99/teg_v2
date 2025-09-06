"""
Data processing functions for scoring analysis pages.

This module contains functions for:
- Score formatting and aggregation
- Streak calculations and analysis
- Score type statistics processing
"""

import pandas as pd
import numpy as np


# === SCORE FORMATTING ===

def format_vs_par_value(value):
    """
    Format vs-par values for display (e.g., +1.5, -0.5, =).
    
    Args:
        value (float): The vs-par value to format
        
    Returns:
        str: Formatted string (e.g., "+1.50", "-0.50", "=")
        
    Purpose:
        Consistent formatting for vs-par scores across all scoring displays
    """
    if value > 0:
        return f"+{value:.2f}"
    elif value < 0:
        return f"{value:.2f}"
    else:
        return "="


def prepare_average_scores_by_par(all_data):
    """
    Calculate and format average scores by par value for each player.
    
    Args:
        all_data (pd.DataFrame): Complete hole-by-hole scoring data
        
    Returns:
        pd.DataFrame: Formatted table with average scores by par, ready for display
        
    Purpose:
        Shows how each player performs on different par values (Par 3, 4, 5)
        Helps identify strengths and weaknesses by hole difficulty
    """
    # Calculate average GrossVP by player and par value
    avg_grossvp = all_data.groupby(['Player', 'PAR'])['GrossVP'].mean().unstack(fill_value=0)
    
    # Add overall average column
    avg_grossvp['Total'] = all_data.groupby('Player')['GrossVP'].mean()
    
    # Sort by overall performance (best to worst)
    avg_grossvp = avg_grossvp.sort_values('Total', ascending=True)
    avg_grossvp = avg_grossvp.round(2)

    # Format all values using consistent vs-par formatting
    for column in avg_grossvp.columns:
        avg_grossvp[column] = avg_grossvp[column].apply(format_vs_par_value)

    # Prepare for display
    avg_grossvp.reset_index(inplace=True)
    avg_grossvp.columns.name = None
    avg_grossvp.columns = ['Player'] + [f'Par {col}' if col != 'Total' else col for col in avg_grossvp.columns[1:]]
    
    return avg_grossvp


def format_scoring_stats_columns(df):
    """
    Format columns in scoring statistics dataframe for display.
    
    Args:
        df (pd.DataFrame): Raw scoring statistics data
        
    Returns:
        pd.DataFrame: Formatted dataframe ready for display
        
    Purpose:
        Standardizes number formatting and column names for scoring tables
        Handles infinite values (when player has 0 of a score type)
    """
    # Create a copy to avoid modifying the original
    formatted_df = df.copy()
    
    # Format count column as integer
    formatted_df.iloc[:, 1] = formatted_df.iloc[:, 1].astype(int)
    
    # Format frequency column, handling infinite values
    formatted_df.iloc[:, 2] = formatted_df.iloc[:, 2].apply(
        lambda x: 'n/a' if np.isinf(x) else f"{x:,.1f}"
    )
    
    # Clean up column names (replace underscores with spaces)
    formatted_df.columns = [col.replace('_', ' ') for col in formatted_df.columns]
    
    return formatted_df


# === STREAK CALCULATIONS ===

def calculate_multi_score_running_sum(df):
    """
    Calculate running streaks for different score types (birdies, pars, etc.).
    
    Args:
        df (pd.DataFrame): Hole-by-hole data with Career Count ordering
        
    Returns:
        pd.DataFrame: Original data with added RunningSum columns for each score type
        
    Purpose:
        Tracks consecutive achievements (e.g., consecutive birdies, pars or better)
        Used to find longest streaks for each player
    """
    # Sort by player and chronological order
    df_sorted = df.sort_values(['Player', 'Career Count'])
    
    # Define score type conditions based on GrossVP values
    score_types = {
        'Pars_or_Better': lambda x: x <= 0,  # Par or better (birdie, eagle)
        'Birdies': lambda x: x == -1,        # Exactly birdie
        'TBPs': lambda x: x > 2              # Triple bogey or worse
    }
    
    # Initialize running sum columns
    for score_type in score_types:
        df_sorted[f'RunningSum_{score_type}'] = 0
    
    # Calculate running sums for each player
    def calc_running_sums(group):
        """Calculate consecutive streaks within a single player's data."""
        for score_type, condition in score_types.items():
            running_sum = 0
            for i, row in group.iterrows():
                if condition(row['GrossVP']):
                    running_sum += 1
                else:
                    running_sum = 0  # Reset streak
                group.at[i, f'RunningSum_{score_type}'] = running_sum
        return group

    # Apply calculation to each player's data
    df_sorted = df_sorted.groupby('Player', group_keys=False).apply(calc_running_sums)
    
    # Merge calculated columns back to original dataframe
    merge_columns = ['Player', 'Career Count'] + [f'RunningSum_{score_type}' for score_type in score_types]
    df = df.merge(df_sorted[merge_columns], on=['Player', 'Career Count'], how='left')
    
    return df


def summarize_multi_score_running_sum(df):
    """
    Summarize maximum streak lengths for each player and score type.
    
    Args:
        df (pd.DataFrame): Data with RunningSum columns from calculate_multi_score_running_sum()
        
    Returns:
        pd.DataFrame: Summary showing longest streak for each player/score type
        
    Purpose:
        Creates the final "Longest Streaks" table showing each player's best streaks
    """
    score_types = ['Birdies', 'Pars_or_Better', 'TBPs']
    
    # Verify required columns exist
    for score_type in score_types:
        if f'RunningSum_{score_type}' not in df.columns:
            raise ValueError(f"RunningSum_{score_type} column not found. Please calculate running sums first.")

    # Get maximum streak length for each player/score type
    summary = df.groupby('Player').agg({
        f'RunningSum_{score_type}': 'max' for score_type in score_types
    }).reset_index()
    
    # Clean up column names
    summary.columns = ['Player'] + score_types
    
    # Sort by best "Pars or Better" streak
    summary = summary.sort_values('Pars_or_Better', ascending=False)
    
    return summary