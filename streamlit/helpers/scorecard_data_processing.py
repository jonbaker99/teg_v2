"""
Data processing functions for scorecard display and user interface.

This module contains functions for:
- Processing scorecard selection options
- Validating scorecard data
- Preparing data for different scorecard types
"""

import pandas as pd
import streamlit as st


def prepare_scorecard_selection_options(all_data):
    """
    Prepare dropdown options for scorecard selection interface.
    
    Args:
        all_data (pd.DataFrame): Complete dataset with all hole-by-hole data
        
    Returns:
        dict: Contains sorted lists for player, TEG, and round options
        
    Purpose:
        Creates consistent, sorted options for all scorecard selection dropdowns
        Ensures user interface has complete and current data options
    """
    return {
        'players': sorted(all_data['Pl'].unique()),
        'tournaments': sorted(all_data['TEGNum'].unique()),
        'all_data': all_data  # Keep reference for dynamic round filtering
    }


def get_round_options_for_tournament(all_data, selected_tegnum):
    """
    Get available rounds for a specific tournament.
    
    Args:
        all_data (pd.DataFrame): Complete dataset
        selected_tegnum: Selected tournament number
        
    Returns:
        list: Sorted list of available rounds for the tournament
        
    Purpose:
        Dynamically updates round options based on tournament selection
        Ensures users only see valid round choices for selected tournament
    """
    return sorted(all_data[all_data['TEGNum'] == selected_tegnum]['Round'].unique())


def validate_and_prepare_single_round_data(rd_data):
    """
    Validate and prepare data for single round scorecard display.
    
    Args:
        rd_data (pd.DataFrame): Raw round data from get_scorecard_data()
        
    Returns:
        tuple: (is_valid, prepared_data, error_message)
        
    Purpose:
        Ensures scorecard data is complete (18 holes) and properly formatted
        Converts numeric data to integers for clean display
        Provides clear error messages for data issues
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


def get_scorecard_type_mapping():
    """
    Define mapping between internal tab names and user-friendly display names.
    
    Returns:
        tuple: (tab_names, display_names) for scorecard type selection
        
    Purpose:
        Separates internal logic names from user-facing descriptions
        Makes it easy to update display text without changing logic
    """
    tab_names = ["1 Round / All Players", "1 Player / All Rounds", "1 Round / 1 Player"]
    display_names = ["Round Comparison (all players)", "Tournament view (one player)", "Single Player Round"]
    
    return tab_names, display_names


def determine_control_states(selected_tab):
    """
    Determine which UI controls should be enabled/disabled based on scorecard type.
    
    Args:
        selected_tab (str): Currently selected scorecard type
        
    Returns:
        dict: Control states for player and round selection
        
    Purpose:
        Provides clear logic for which controls are relevant for each scorecard type
        Prevents user confusion by disabling irrelevant options
    """
    return {
        'player_disabled': (selected_tab == "1 Round / All Players"),
        'round_disabled': (selected_tab == "1 Player / All Rounds")
    }


def prepare_tournament_display_data(tournament_data):
    """
    Prepare data for tournament view display.
    
    Args:
        tournament_data (pd.DataFrame): Raw tournament data
        
    Returns:
        dict: Prepared data with player name and tournament name
        
    Purpose:
        Extracts display information needed for tournament scorecard headers
        Ensures consistent naming format across tournament displays
    """
    if len(tournament_data) == 0:
        return None
        
    return {
        'player_name': tournament_data['Player'].iloc[0],
        'teg_name': f"TEG {tournament_data['TEGNum'].iloc[0]}"
    }


def initialize_scorecard_session_state():
    """
    Initialize session state variables for scorecard functionality.
    
    Purpose:
        Sets up persistent state for tab selection and user preferences
        Prevents UI reset issues during scorecard navigation
    """
    if 'active_scorecard_tab' not in st.session_state:
        st.session_state.active_scorecard_tab = 0