"""
Data processing functions for par-based scoring analysis.

This module contains functions for:
- Processing scores by par value (Par 3, Par 4, Par 5)
- Creating player performance matrices by par
- Formatting vs-par values for display
"""

import pandas as pd
import numpy as np


def prepare_teg_filter_options(all_data):
    """
    Prepare TEG filtering options for par analysis.
    
    Args:
        all_data (pd.DataFrame): Complete tournament data
        
    Returns:
        list: TEG options including "All TEGs" and individual tournaments
        
    Purpose:
        Enables analysis of par performance for specific tournaments or all-time
        Orders TEGs in reverse chronological order (most recent first)
    """
    tegnum_options = ['All TEGs'] + sorted(all_data['TEGNum'].unique().tolist(), reverse=True)
    return tegnum_options


def filter_data_by_teg(all_data, selected_tegnum):
    """
    Filter data by selected TEG tournament.
    
    Args:
        all_data (pd.DataFrame): Complete tournament data
        selected_tegnum: Selected TEG number or "All TEGs"
        
    Returns:
        pd.DataFrame: Filtered data for selected tournament or complete data
        
    Purpose:
        Allows focused analysis of par performance for specific tournaments
        Returns complete dataset when "All TEGs" is selected
    """
    if selected_tegnum != 'All TEGs':
        selected_tegnum_int = int(selected_tegnum)
        return all_data[all_data['TEGNum'] == selected_tegnum_int]
    else:
        return all_data


def calculate_par_performance_matrix(filtered_data):
    """
    Calculate average GrossVP performance by player and par value.
    
    Args:
        filtered_data (pd.DataFrame): Tournament data for analysis
        
    Returns:
        pd.DataFrame: Player-by-par performance matrix with totals
        
    Purpose:
        Creates comprehensive view of how each player performs on different par holes
        Includes overall average for comparison across players
        Sorted by total performance (best to worst)
    """
    # Create pivot table of average GrossVP by player and par
    avg_grossvp = filtered_data.groupby(['Player', 'PAR'])['GrossVP'].mean().unstack(fill_value=0)
    
    # Add total column with overall average
    avg_grossvp['Total'] = filtered_data.groupby('Player')['GrossVP'].mean()
    
    # Sort by total performance (ascending = best first)
    avg_grossvp = avg_grossvp.sort_values('Total', ascending=True)
    
    # Round to 2 decimal places for clean display
    avg_grossvp = avg_grossvp.round(2)
    
    return avg_grossvp


def format_par_performance_table(avg_grossvp):
    """
    Format par performance table for display with proper vs-par notation.
    
    Args:
        avg_grossvp (pd.DataFrame): Raw performance matrix
        
    Returns:
        pd.DataFrame: Formatted table ready for HTML display
        
    Purpose:
        Applies consistent formatting for vs-par values
        Uses +/- notation and "=" for even par
        Renames columns for user-friendly display
    """
    def format_vs_par_value(value):
        """Format vs-par values with appropriate +/- symbols."""
        if value > 0:
            return f"+{value:.2f}"
        elif value < 0:
            return f"{value:.2f}"
        else:
            return "="
    
    # Apply formatting to all columns
    for column in avg_grossvp.columns:
        avg_grossvp[column] = avg_grossvp[column].apply(format_vs_par_value)
    
    # Reset index to make Player a regular column
    avg_grossvp.reset_index(inplace=True)
    avg_grossvp.columns.name = None
    
    # Rename columns for display
    avg_grossvp.columns = ['Player'] + [f'Par {col}' if col != 'Total' else col for col in avg_grossvp.columns[1:]]
    
    return avg_grossvp