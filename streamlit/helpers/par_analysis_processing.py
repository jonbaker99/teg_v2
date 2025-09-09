"""
Data processing functions for par-based scoring analysis.

This module contains functions for:
- Processing scores by par value (Par 3, Par 4, Par 5)
- Creating player performance matrices by par
- Formatting vs-par values for display
"""

import pandas as pd
import numpy as np




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
        if pd.isna(value):
            return ""
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