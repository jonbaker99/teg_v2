"""Data processing functions for par-based scoring analysis.

This module contains functions for processing scores by par value (Par 3, Par 4,
Par 5), creating player performance matrices by par, and formatting vs-par
values for display.
"""

import pandas as pd
import numpy as np


def calculate_par_performance_matrix(filtered_data: pd.DataFrame) -> pd.DataFrame:
    """Calculates the average GrossVP performance by player and par value.

    This function creates a comprehensive view of how each player performs on
    different par holes, including an overall average for comparison.

    Args:
        filtered_data (pd.DataFrame): The tournament data for analysis.

    Returns:
        pd.DataFrame: A player-by-par performance matrix with totals, sorted
        by total performance.
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


def format_par_performance_table(avg_grossvp: pd.DataFrame) -> pd.DataFrame:
    """Formats the par performance table for display.

    This function applies consistent formatting for vs-par values, using +/-
    notation and renaming columns for a user-friendly display.

    Args:
        avg_grossvp (pd.DataFrame): The raw performance matrix.

    Returns:
        pd.DataFrame: A formatted table ready for HTML display.
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