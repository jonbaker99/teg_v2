"""
Data processing functions for latest round analysis and context display.

This module contains functions for:
- Managing round selection session state
- Processing round ranking data for display
- Creating metric-specific context tables and charts
"""

import streamlit as st
import pandas as pd


def get_round_metric_mappings():
    """
    Get mapping between user-friendly names and internal metric names for rounds.
    
    Returns:
        tuple: (name_mapping, inverted_mapping) for display and processing
        
    Purpose:
        Provides consistent naming between user interface and data processing
        Same mapping pattern as other performance analysis pages
    """
    name_mapping = {
        'Gross vs Par': 'GrossVP',
        'Score': 'Sc',
        'Net vs Par': 'NetVP',
        'Stableford': 'Stableford'
    }
    inverted_mapping = {v: k for k, v in name_mapping.items()}
    
    return name_mapping, inverted_mapping


def initialize_round_selection_state():
    """
    Initialize session state variables for round selection.
    
    Purpose:
        Sets up persistent state for TEG and round selection
        Prevents UI reset issues during navigation
        Maintains user's current selection across interactions
    """
    if 'teg_r' not in st.session_state:
        st.session_state.teg_r = None
    if 'rd_r' not in st.session_state:
        st.session_state.rd_r = None


def get_latest_round_defaults(df_round):
    """
    Get default TEG and round values (latest available).
    
    Args:
        df_round (pd.DataFrame): Round ranking data
        
    Returns:
        tuple: (max_teg, max_round_in_teg) representing latest available round
        
    Purpose:
        Determines the most recent round for default selection
        Provides "Latest Round" button functionality
    """
    df_sorted = df_round.sort_values(by=['TEGNum', 'Round'])
    max_teg = df_sorted.loc[df_sorted['TEGNum'].idxmax(), 'TEG']
    max_round_in_max_teg = df_sorted[df_sorted['TEG'] == max_teg]['Round'].max()
    
    return max_teg, max_round_in_max_teg


def update_session_state_defaults(df_round):
    """
    Set session state to latest round if not already initialized.
    
    Args:
        df_round (pd.DataFrame): Round ranking data
        
    Purpose:
        Ensures session state has valid default values on first load
        Uses latest available round as sensible default
    """
    max_teg, max_round_in_max_teg = get_latest_round_defaults(df_round)
    
    if st.session_state.teg_r is None:
        st.session_state.teg_r = max_teg
    if st.session_state.rd_r is None:
        st.session_state.rd_r = max_round_in_max_teg


def create_round_selection_reset_function(df_round):
    """
    Create callback function for "Latest Round" button.
    
    Args:
        df_round (pd.DataFrame): Round ranking data
        
    Returns:
        function: Callback function that resets selection to latest round
        
    Purpose:
        Provides one-click reset to most recent round
        Updates session state when button is clicked
    """
    max_teg, max_round_in_max_teg = get_latest_round_defaults(df_round)
    
    def reset_to_latest():
        st.session_state.teg_r = max_teg
        st.session_state.rd_r = max_round_in_max_teg
    
    return reset_to_latest


def get_teg_and_round_options(df_round, selected_teg):
    """
    Get available TEG and round options for selection dropdowns.
    
    Args:
        df_round (pd.DataFrame): Round ranking data
        selected_teg (str): Currently selected TEG
        
    Returns:
        tuple: (teg_options, round_options) for dropdown menus
        
    Purpose:
        Provides filtered options for dynamic dropdown menus
        Round options update based on selected TEG
    """
    teg_options = list(df_round['TEG'].unique())
    round_options = sorted(df_round[df_round['TEG'] == selected_teg]['Round'].unique())
    
    return teg_options, round_options


def create_metric_tabs_data(metrics):
    """
    Prepare metric data for tabbed display.
    
    Args:
        metrics (list): List of internal metric names
        
    Returns:
        tuple: (metrics, friendly_metrics) for tab creation and processing
        
    Purpose:
        Creates user-friendly tab labels from internal metric names
        Maintains mapping for data processing within each tab
    """
    name_mapping, inverted_name_mapping = get_round_metric_mappings()
    friendly_metrics = [inverted_name_mapping[metric] for metric in metrics]
    
    return metrics, friendly_metrics


def prepare_round_context_display(df_round, teg_r, rd_r, metric, friendly_metric):
    """
    Prepare round context data for display in a specific metric tab.
    
    Args:
        df_round (pd.DataFrame): Round ranking data
        teg_r (str): Selected TEG
        rd_r (str): Selected round
        metric (str): Internal metric name
        friendly_metric (str): User-friendly metric name
        
    Returns:
        pd.DataFrame: Context table with renamed columns for display
        
    Purpose:
        Creates context table showing how selected round compares to other rounds
        Uses chosen_rd_context from utils for core logic, adds display formatting
    """
    from utils import chosen_rd_context
    
    # Get context data from utils function
    context_data = chosen_rd_context(df_round, teg_r, rd_r, metric)
    
    # Rename metric column to friendly name for display
    display_data = context_data.rename(columns={metric: friendly_metric})
    
    return display_data


# === TEG CONTEXT FUNCTIONS ===

def initialize_teg_selection_state():
    """
    Initialize session state variables for TEG selection.
    
    Purpose:
        Sets up persistent state for TEG selection
        Prevents UI reset issues during navigation
        Maintains user's current selection across interactions
    """
    if 'teg_t' not in st.session_state:
        st.session_state.teg_t = None


def get_latest_teg_default(df_teg):
    """
    Get default TEG value (latest available).
    
    Args:
        df_teg (pd.DataFrame): TEG ranking data
        
    Returns:
        str: Latest available TEG for default selection
        
    Purpose:
        Determines the most recent TEG for default selection
        Provides "Latest TEG" button functionality
    """
    df_sorted = df_teg.sort_values(by='TEGNum')
    max_teg = df_sorted.loc[df_sorted['TEGNum'].idxmax(), 'TEG']
    
    return max_teg


def update_teg_session_state_defaults(df_teg):
    """
    Set session state to latest TEG if not already initialized.
    
    Args:
        df_teg (pd.DataFrame): TEG ranking data
        
    Purpose:
        Ensures session state has valid default value on first load
        Uses latest available TEG as sensible default
    """
    max_teg = get_latest_teg_default(df_teg)
    
    if st.session_state.teg_t is None:
        st.session_state.teg_t = max_teg


def create_teg_selection_reset_function(df_teg):
    """
    Create callback function for "Latest TEG" button.
    
    Args:
        df_teg (pd.DataFrame): TEG ranking data
        
    Returns:
        function: Callback function that resets selection to latest TEG
        
    Purpose:
        Provides one-click reset to most recent TEG
        Updates session state when button is clicked
    """
    max_teg = get_latest_teg_default(df_teg)
    
    def reset_to_latest_teg():
        st.session_state.teg_t = max_teg
    
    return reset_to_latest_teg


def get_teg_options(df_teg):
    """
    Get available TEG options for selection dropdown.
    
    Args:
        df_teg (pd.DataFrame): TEG ranking data
        
    Returns:
        list: TEG options for dropdown menu
        
    Purpose:
        Provides all available TEG options for selection
        Maintains chronological order for user convenience
    """
    return list(df_teg['TEG'].unique())


def prepare_teg_context_display(df_teg, teg_t, metric, friendly_metric):
    """
    Prepare TEG context data for display in a specific metric tab.
    
    Args:
        df_teg (pd.DataFrame): TEG ranking data
        teg_t (str): Selected TEG
        metric (str): Internal metric name
        friendly_metric (str): User-friendly metric name
        
    Returns:
        pd.DataFrame: Context table with renamed columns for display
        
    Purpose:
        Creates context table showing how selected TEG compares to other TEGs
        Uses chosen_teg_context from utils for core logic, adds display formatting
    """
    from utils import chosen_teg_context
    
    # Get context data from utils function
    context_data = chosen_teg_context(df_teg, teg_t, metric)
    
    # Rename metric column to friendly name for display
    display_data = context_data.rename(columns={metric: friendly_metric})
    
    return display_data