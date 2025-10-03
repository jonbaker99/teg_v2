"""Data processing functions for latest round analysis and context display.

This module contains functions for managing round selection session state,
processing round ranking data for display, and creating metric-specific context
tables and charts.
"""

import streamlit as st
import pandas as pd
from utils import get_current_in_progress_teg_fast, get_last_completed_teg_fast


def get_round_metric_mappings() -> tuple[dict, dict]:
    """Gets mappings between user-friendly and internal metric names for rounds.

    Returns:
        tuple: A tuple containing two dictionaries:
            - name_mapping (dict): Maps user-friendly names to internal names.
            - inverted_mapping (dict): Maps internal names to user-friendly
              names.
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
    """Initializes session state variables for round selection.

    This function sets up a persistent state for TEG and round selection to
    prevent UI resets and maintain the user's current selection.
    """
    if 'teg_r' not in st.session_state:
        st.session_state.teg_r = None
    if 'rd_r' not in st.session_state:
        st.session_state.rd_r = None


def get_latest_round_defaults(df_round: pd.DataFrame) -> tuple[str, int]:
    """Gets the default TEG and round values (the latest available).

    This function determines the most recent round for default selection,
    which is used for the "Latest Round" button functionality.

    Args:
        df_round (pd.DataFrame): A DataFrame of round ranking data, used as a
            fallback.

    Returns:
        tuple: A tuple containing the max TEG and max round in that TEG.
    """
    try:
        # Try fast method first: check if there's a TEG in progress
        in_progress_teg, rounds_played = get_current_in_progress_teg_fast()
        if in_progress_teg:
            return f"TEG {in_progress_teg}", rounds_played

        # If no TEG in progress, get last completed TEG
        last_teg, rounds = get_last_completed_teg_fast()
        if last_teg:
            return f"TEG {last_teg}", rounds

        # Fallback to original method if status files unavailable
        df_sorted = df_round.sort_values(by=['TEGNum', 'Round'])
        max_teg = df_sorted.loc[df_sorted['TEGNum'].idxmax(), 'TEG']
        max_round_in_max_teg = df_sorted[df_sorted['TEG'] == max_teg]['Round'].max()
        return max_teg, max_round_in_max_teg

    except Exception:
        # Fallback to original method on any error
        df_sorted = df_round.sort_values(by=['TEGNum', 'Round'])
        max_teg = df_sorted.loc[df_sorted['TEGNum'].idxmax(), 'TEG']
        max_round_in_max_teg = df_sorted[df_sorted['TEG'] == max_teg]['Round'].max()
        return max_teg, max_round_in_max_teg


def update_session_state_defaults(df_round: pd.DataFrame):
    """Sets the session state to the latest round if not already initialized.

    This function ensures that the session state has valid default values on
    the first load, using the latest available round as a sensible default.

    Args:
        df_round (pd.DataFrame): The round ranking data.
    """
    max_teg, max_round_in_max_teg = get_latest_round_defaults(df_round)
    
    if st.session_state.teg_r is None:
        st.session_state.teg_r = max_teg
    if st.session_state.rd_r is None:
        st.session_state.rd_r = max_round_in_max_teg


def create_round_selection_reset_function(df_round: pd.DataFrame) -> callable:
    """Creates a callback function for the "Latest Round" button.

    This function provides a one-click reset to the most recent round by
    updating the session state when the button is clicked.

    Args:
        df_round (pd.DataFrame): The round ranking data.

    Returns:
        callable: A callback function that resets the selection to the
        latest round.
    """
    max_teg, max_round_in_max_teg = get_latest_round_defaults(df_round)
    
    def reset_to_latest():
        st.session_state.teg_r = max_teg
        st.session_state.rd_r = max_round_in_max_teg
    
    return reset_to_latest


def get_teg_and_round_options(df_round: pd.DataFrame, selected_teg: str) -> tuple[list, list]:
    """Gets available TEG and round options for selection dropdowns.

    This function provides filtered options for dynamic dropdown menus, where
    the round options update based on the selected TEG.

    Args:
        df_round (pd.DataFrame): The round ranking data.
        selected_teg (str): The currently selected TEG.

    Returns:
        tuple: A tuple containing:
            - teg_options (list): A list of TEG options.
            - round_options (list): A list of round options for the
              selected TEG.
    """
    teg_options = list(df_round['TEG'].unique())
    round_options = sorted(df_round[df_round['TEG'] == selected_teg]['Round'].unique())
    
    return teg_options, round_options


def create_metric_tabs_data(metrics: list) -> tuple[list, list]:
    """Prepares metric data for tabbed display.

    This function creates user-friendly tab labels from internal metric names
    and maintains a mapping for data processing within each tab.

    Args:
        metrics (list): A list of internal metric names.

    Returns:
        tuple: A tuple containing:
            - metrics (list): The original list of internal metric names.
            - friendly_metrics (list): A list of user-friendly metric names.
    """
    name_mapping, inverted_name_mapping = get_round_metric_mappings()
    friendly_metrics = [inverted_name_mapping[metric] for metric in metrics]
    
    return metrics, friendly_metrics


def prepare_round_context_display(df_round: pd.DataFrame, teg_r: str, rd_r: int, metric: str, friendly_metric: str) -> pd.DataFrame:
    """Prepares round context data for display in a specific metric tab.

    This function creates a context table showing how the selected round
    compares to other rounds.

    Args:
        df_round (pd.DataFrame): The round ranking data.
        teg_r (str): The selected TEG.
        rd_r (int): The selected round.
        metric (str): The internal metric name.
        friendly_metric (str): The user-friendly metric name.

    Returns:
        pd.DataFrame: A context table with renamed columns for display.
    """
    from utils import chosen_rd_context
    
    # Get context data from utils function
    context_data = chosen_rd_context(df_round, teg_r, rd_r, metric)
    
    # Rename metric column to friendly name for display
    display_data = context_data.rename(columns={metric: friendly_metric})
    
    return display_data


# === TEG CONTEXT FUNCTIONS ===

def initialize_teg_selection_state():
    """Initializes session state variables for TEG selection.

    This function sets up a persistent state for TEG selection to prevent UI
    resets and maintain the user's current selection.
    """
    if 'teg_t' not in st.session_state:
        st.session_state.teg_t = None


def get_latest_teg_default(df_teg: pd.DataFrame) -> str:
    """Gets the default TEG value (the latest available).

    This function determines the most recent TEG for default selection, which
    is used for the "Latest TEG" button functionality.

    Args:
        df_teg (pd.DataFrame): A DataFrame of TEG ranking data, used as a
            fallback.

    Returns:
        str: The latest available TEG for default selection.
    """
    try:
        # Try fast method first: check if there's a TEG in progress
        in_progress_teg, rounds_played = get_current_in_progress_teg_fast()
        if in_progress_teg:
            return f"TEG {in_progress_teg}"

        # If no TEG in progress, get last completed TEG
        last_teg, rounds = get_last_completed_teg_fast()
        if last_teg:
            return f"TEG {last_teg}"

        # Fallback to original method if status files unavailable
        df_sorted = df_teg.sort_values(by='TEGNum')
        max_teg = df_sorted.loc[df_sorted['TEGNum'].idxmax(), 'TEG']
        return max_teg

    except Exception:
        # Fallback to original method on any error
        df_sorted = df_teg.sort_values(by='TEGNum')
        max_teg = df_sorted.loc[df_sorted['TEGNum'].idxmax(), 'TEG']
        return max_teg


def update_teg_session_state_defaults(df_teg: pd.DataFrame):
    """Sets the session state to the latest TEG if not already initialized.

    This function ensures that the session state has a valid default value on
    the first load, using the latest available TEG as a sensible default.

    Args:
        df_teg (pd.DataFrame): The TEG ranking data.
    """
    max_teg = get_latest_teg_default(df_teg)
    
    if st.session_state.teg_t is None:
        st.session_state.teg_t = max_teg


def create_teg_selection_reset_function(df_teg: pd.DataFrame) -> callable:
    """Creates a callback function for the "Latest TEG" button.

    This function provides a one-click reset to the most recent TEG by
    updating the session state when the button is clicked.

    Args:
        df_teg (pd.DataFrame): The TEG ranking data.

    Returns:
        callable: A callback function that resets the selection to the
        latest TEG.
    """
    max_teg = get_latest_teg_default(df_teg)
    
    def reset_to_latest_teg():
        st.session_state.teg_t = max_teg
    
    return reset_to_latest_teg


def get_teg_options(df_teg: pd.DataFrame) -> list:
    """Gets available TEG options for the selection dropdown.

    Args:
        df_teg (pd.DataFrame): The TEG ranking data.

    Returns:
        list: A list of TEG options for the dropdown menu.
    """
    return list(df_teg['TEG'].unique())


def prepare_teg_context_display(df_teg: pd.DataFrame, teg_t: str, metric: str, friendly_metric: str) -> pd.DataFrame:
    """Prepares TEG context data for display in a specific metric tab.

    This function creates a context table showing how the selected TEG
    compares to other TEGs.

    Args:
        df_teg (pd.DataFrame): The TEG ranking data.
        teg_t (str): The selected TEG.
        metric (str): The internal metric name.
        friendly_metric (str): The user-friendly metric name.

    Returns:
        pd.DataFrame: A context table with renamed columns for display.
    """
    from utils import chosen_teg_context
    
    # Get context data from utils function
    context_data = chosen_teg_context(df_teg, teg_t, metric)
    
    # Rename metric column to friendly name for display
    display_data = context_data.rename(columns={metric: friendly_metric})
    
    return display_data