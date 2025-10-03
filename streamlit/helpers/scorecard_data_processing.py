"""Data processing functions for scorecard display and user interface.

This module contains functions for processing scorecard selection options,
validating scorecard data, and preparing data for different scorecard types.
"""

import pandas as pd
import streamlit as st


def prepare_scorecard_selection_options(all_data: pd.DataFrame) -> dict:
    """Prepares dropdown options for the scorecard selection interface.

    This function creates consistent, sorted options for all scorecard
    selection dropdowns, ensuring the user interface has complete and current
    data options.

    Args:
        all_data (pd.DataFrame): The complete dataset with all hole-by-hole
            data.

    Returns:
        dict: A dictionary containing sorted lists for player, TEG, and round
        options.
    """
    return {
        'players': sorted(all_data['Pl'].unique()),
        'tournaments': sorted(all_data['TEGNum'].unique()),
        'all_data': all_data  # Keep reference for dynamic round filtering
    }


def get_round_options_for_tournament(all_data: pd.DataFrame, selected_tegnum: int) -> list:
    """Gets the available rounds for a specific tournament.

    This function dynamically updates the round options based on the selected
    tournament, ensuring that users only see valid round choices.

    Args:
        all_data (pd.DataFrame): The complete dataset.
        selected_tegnum (int): The selected tournament number.

    Returns:
        list: A sorted list of available rounds for the tournament.
    """
    return sorted(all_data[all_data['TEGNum'] == selected_tegnum]['Round'].unique())


def validate_and_prepare_single_round_data(rd_data: pd.DataFrame) -> tuple[bool, pd.DataFrame, str]:
    """Validates and prepares data for a single round scorecard display.

    This function ensures that the scorecard data is complete (18 holes) and
    properly formatted, providing clear error messages for any data issues.

    Args:
        rd_data (pd.DataFrame): The raw round data.

    Returns:
        tuple: A tuple containing:
            - is_valid (bool): True if the data is valid, False otherwise.
            - prepared_data (pd.DataFrame or None): The prepared data, or
              None if invalid.
            - error_message (str or None): An error message, or None if
              valid.
    """
    if len(rd_data) == 0:
        return False, None, "No data found for the selected round"
    
    # Define columns needed for scorecard display
    output_cols = ['Hole', 'PAR', 'SI', 'HCStrokes', 'Sc', 'GrossVP', 'NetVP', 'Stableford']
    output_data = rd_data[output_cols].copy()
    
    # Convert numeric data to integers, handling NaN values
    def to_int_or_zero(x):
        if pd.isna(x):
            return 0
        return int(x)
    
    # Apply conversion to all numeric columns
    numeric_columns = output_data.select_dtypes(include=['float64', 'int64']).columns
    for col in numeric_columns:
        output_data[col] = output_data[col].map(to_int_or_zero)
    
    # Validate that we have complete 18-hole data
    if len(output_data) != 18:
        return False, None, f"Expected 18 holes, found {len(output_data)} holes for this round."
    
    return True, output_data, None


def get_scorecard_type_mapping() -> tuple[list, list]:
    """Defines the mapping between internal tab names and user-friendly display names.

    This function separates internal logic names from user-facing descriptions,
    making it easy to update display text without changing the logic.

    Returns:
        tuple: A tuple containing:
            - tab_names (list): A list of internal tab names.
            - display_names (list): A list of user-friendly display names.
    """
    tab_names = ["1 Round / All Players", "1 Player / All Rounds", "1 Round / 1 Player"]
    display_names = ["Round Comparison (all players)", "Tournament view (one player)", "Single Player Round"]
    
    return tab_names, display_names


def determine_control_states(selected_tab: str) -> dict:
    """Determines which UI controls should be enabled or disabled.

    This function provides clear logic for which controls are relevant for
    each scorecard type, preventing user confusion by disabling irrelevant
    options.

    Args:
        selected_tab (str): The currently selected scorecard type.

    Returns:
        dict: A dictionary of control states for player and round selection.
    """
    return {
        'player_disabled': (selected_tab == "1 Round / All Players"),
        'round_disabled': (selected_tab == "1 Player / All Rounds")
    }


def prepare_tournament_display_data(tournament_data: pd.DataFrame) -> dict or None:
    """Prepares data for the tournament view display.

    This function extracts the necessary display information for tournament
    scorecard headers, ensuring a consistent naming format.

    Args:
        tournament_data (pd.DataFrame): The raw tournament data.

    Returns:
        dict or None: The prepared data with the player name and tournament
        name, or None if the input data is empty.
    """
    if len(tournament_data) == 0:
        return None
        
    return {
        'player_name': tournament_data['Player'].iloc[0],
        'teg_name': f"TEG {tournament_data['TEGNum'].iloc[0]}"
    }


def initialize_scorecard_session_state():
    """Initializes session state variables for scorecard functionality.

    This function sets up a persistent state for tab selection and user
    preferences to prevent UI reset issues during scorecard navigation.
    """
    if 'active_scorecard_tab' not in st.session_state:
        st.session_state.active_scorecard_tab = 0