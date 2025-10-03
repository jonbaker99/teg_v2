"""Data processing functions for scoring achievements analysis.

This module contains functions for processing career scoring achievements
statistics, formatting the data for display, and creating tabbed displays for
different score types.
"""

import pandas as pd
import numpy as np


def get_scoring_achievement_fields() -> list[list[str]]:
    """Defines the score achievement fields for the tabbed display.

    This function centralizes the definition of score achievement categories,
    where each pair contains the achievement count and the holes per
    achievement metric.

    Returns:
        list: A list of field pairs for achievements and frequency metrics.
    """
    chart_fields = [
        ['Eagles', 'Holes_per_Eagle'],
        ['Birdies', 'Holes_per_Birdie'],
        ['Pars_or_Better', 'Holes_per_Par_or_Better'],
        ['TBPs', 'Holes_per_TBP']
    ]
    
    return chart_fields


def create_achievement_tab_labels(chart_fields_all: list[list[str]]) -> list[str]:
    """Creates user-friendly tab labels from achievement field names.

    This function converts internal field names to display-ready tab labels by
    replacing underscores with spaces for a cleaner UI presentation.

    Args:
        chart_fields_all (list): A list of all achievement field pairs.

    Returns:
        list: A list of tab labels.
    """
    tab_labels = [chart_fields[0].replace("_", " ") for chart_fields in chart_fields_all]
    return tab_labels


def format_achievement_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Formats the achievement DataFrame columns for display.

    This function formats achievement counts as integers and frequency ratios
    as decimals, handling infinite values and cleaning up column names.

    Args:
        df (pd.DataFrame): The raw achievement data with counts and ratios.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for HTML display.
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


def prepare_achievement_table_data(scoring_stats: pd.DataFrame, chart_fields: list) -> pd.DataFrame:
    """Prepares achievement table data for a specific score type.

    This function extracts the relevant columns for a specific achievement
    type, sorts the data, and applies formatting for a clean display.

    Args:
        scoring_stats (pd.DataFrame): The complete scoring statistics data.
        chart_fields (list): A field pair for a specific achievement type.

    Returns:
        pd.DataFrame: A formatted table ready for display.
    """
    # Select relevant columns for this achievement type
    table_columns = ['Player'] + chart_fields
    table_df = scoring_stats[table_columns].copy()
    
    # Sort by achievement count (desc) then frequency (asc - lower is better)
    table_df = table_df.sort_values(by=chart_fields, ascending=[False, True])
    
    # Apply formatting for display
    formatted_table = format_achievement_dataframe_columns(table_df)
    
    return formatted_table


def create_section_title(chart_fields: list) -> str:
    """Creates a section title from achievement field names.

    This function converts an internal field name to a user-friendly section
    title by removing underscores and adding proper context.

    Args:
        chart_fields (list): A field pair for an achievement type.

    Returns:
        str: A cleaned section title for display.
    """
    section_title = chart_fields[0].replace("_", " ")
    return section_title