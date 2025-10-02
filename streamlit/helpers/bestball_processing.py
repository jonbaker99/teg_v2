"""
Data processing functions for bestball and worstball team format analysis.

This module contains functions for:
- Calculating bestball (best score per hole) team scores
- Calculating worstball (worst score per hole) team scores
- Formatting and preparing data for team format displays
"""

import pandas as pd
import streamlit as st


def prepare_bestball_data(all_data):
    """
    Prepare data for bestball analysis by adding team round hole identifiers.
    
    Args:
        all_data (pd.DataFrame): Complete tournament data
        
    Returns:
        pd.DataFrame: Data with TRH (TEG|Round|Hole) identifiers for grouping
        
    Purpose:
        Creates unique identifiers for each hole in each round
        Enables grouping by hole to find best/worst scores per hole
        Essential for team format calculations
    """
    prepared_data = all_data.copy()
    
    # Create TEG|Round|Hole identifier for grouping by specific holes
    prepared_data['TRH'] = prepared_data[['TEGNum', 'Round', 'Hole']].astype(str).agg('|'.join, axis=1)
    
    return prepared_data


def get_bestball_columns():
    """
    Define column sets for bestball analysis.
    
    Returns:
        tuple: (grouping_columns, value_columns) for data processing
        
    Purpose:
        Centralizes column definitions for consistent processing
        Separates grouping fields from value fields for aggregation
    """
    bestball_cols = ['TEG', 'TEGNum', 'Round', 'Course', 'Year']
    value_cols = ['GrossVP', 'Sc']
    
    return bestball_cols, value_cols


def calculate_bestball_scores(filtered_data):
    """
    Calculate bestball team scores (best score per hole).
    
    Args:
        filtered_data (pd.DataFrame): Filtered tournament data
        
    Returns:
        pd.DataFrame: Bestball team scores by round with total scores
        
    Purpose:
        Creates team format where best player score counts for each hole
        Groups by TRH (TEG|Round|Hole) and takes lowest score per hole
        Aggregates hole scores to create round totals
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


def calculate_worstball_scores(filtered_data):
    """
    Calculate worstball team scores (worst score per hole).
    
    Args:
        filtered_data (pd.DataFrame): Filtered tournament data
        
    Returns:
        pd.DataFrame: Worstball team scores by round with total scores
        
    Purpose:
        Creates team format where worst player score counts for each hole
        Groups by TRH (TEG|Round|Hole) and takes highest score per hole
        Aggregates hole scores to create round totals
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


def format_team_scores_for_display(team_data, sort_by_best=True):
    """
    Format team scores for display with proper sorting and vs-par formatting.
    
    Args:
        team_data (pd.DataFrame): Raw team scores data
        sort_by_best (bool): True for best-first, False for worst-first
        
    Returns:
        pd.DataFrame: Formatted team scores ready for display
        
    Purpose:
        Applies consistent formatting for team format displays
        Sorts by GrossVP performance and formats vs-par values
        Creates display-ready data for HTML tables
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
