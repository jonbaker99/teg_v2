"""
Data processing functions for scoring achievements analysis (eagles, birdies, etc.).

This module contains functions for:
- Processing career scoring achievements statistics
- Formatting achievement data for display
- Creating tabbed displays for different score types
"""

import pandas as pd
import numpy as np


def get_scoring_achievement_fields():
    """
    Define score achievement fields for tabbed display.
    
    Returns:
        list: Field pairs for achievements and frequency metrics
        
    Purpose:
        Centralizes definition of score achievement categories
        Each pair contains [achievement_count, holes_per_achievement]
        Used for both data processing and UI tab creation
    """
    chart_fields = [
        ['Eagles', 'Holes_per_Eagle'],
        ['Birdies', 'Holes_per_Birdie'],
        ['Pars_or_Better', 'Holes_per_Par_or_Better'],
        ['TBPs', 'Holes_per_TBP']
    ]
    
    return chart_fields


def create_achievement_tab_labels(chart_fields_all):
    """
    Create user-friendly tab labels from achievement field names.
    
    Args:
        chart_fields_all (list): All achievement field pairs
        
    Returns:
        list: Tab labels with underscores replaced by spaces
        
    Purpose:
        Converts internal field names to display-ready tab labels
        Removes underscores for cleaner UI presentation
    """
    tab_labels = [chart_fields[0].replace("_", " ") for chart_fields in chart_fields_all]
    return tab_labels


def format_achievement_dataframe_columns(df):
    """
    Format achievement dataframe columns for display.
    
    Args:
        df (pd.DataFrame): Raw achievement data with counts and ratios
        
    Returns:
        pd.DataFrame: Formatted dataframe ready for HTML display
        
    Purpose:
        Formats achievement counts as integers and frequency ratios as decimals
        Handles infinite values (when no achievements) with "n/a"
        Cleans column names by removing underscores
    """
    # Create copy to avoid modifying original dataframe
    formatted_df = df.copy()
    
    # Format achievement count as integer (column 1)
    formatted_df.iloc[:, 1] = formatted_df.iloc[:, 1].astype(int)
    
    # Format frequency ratio (column 2) - handle infinity for zero achievements
    formatted_df.iloc[:, 2] = formatted_df.iloc[:, 2].apply(
        lambda x: 'n/a' if np.isinf(x) else f"{x:,.1f}"
    )
    
    # Clean column names by removing underscores
    formatted_df.columns = [col.replace('_', ' ') for col in formatted_df.columns]
    
    return formatted_df


def prepare_achievement_table_data(scoring_stats, chart_fields):
    """
    Prepare achievement table data for a specific score type.
    
    Args:
        scoring_stats (pd.DataFrame): Complete scoring statistics data
        chart_fields (list): Field pair for specific achievement type
        
    Returns:
        pd.DataFrame: Formatted table ready for display
        
    Purpose:
        Extracts relevant columns for specific achievement type
        Sorts by achievement count (descending) and frequency (ascending)
        Applies formatting for clean display
    """
    # Select relevant columns for this achievement type
    table_columns = ['Player'] + chart_fields
    table_df = scoring_stats[table_columns].copy()
    
    # Sort by achievement count (desc) then frequency (asc - lower is better)
    table_df = table_df.sort_values(by=chart_fields, ascending=[False, True])
    
    # Apply formatting for display
    formatted_table = format_achievement_dataframe_columns(table_df)
    
    return formatted_table


def create_section_title(chart_fields):
    """
    Create section title from achievement field names.
    
    Args:
        chart_fields (list): Field pair for achievement type
        
    Returns:
        str: Cleaned section title for display
        
    Purpose:
        Converts field name to user-friendly section title
        Removes underscores and adds proper context
    """
    section_title = chart_fields[0].replace("_", " ")
    return section_title