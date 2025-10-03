"""Data processing functions for bestball and worstball team format analysis.

This module contains functions for calculating bestball (best score per hole)
and worstball (worst score per hole) team scores, as well as formatting and
preparing data for team format displays.
"""

import pandas as pd
import streamlit as st


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
