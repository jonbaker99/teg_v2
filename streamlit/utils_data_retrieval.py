"""
Data retrieval utilities for TEG golf data analysis.

Core data loading functions with Streamlit caching for optimal performance.
These functions form the foundation of the entire application's data access layer.
"""

import pandas as pd
import logging
import streamlit as st

# Import dependencies from other modules
from utils_core_io import read_file
from utils_data_processing import aggregate_data
from utils_statistical_analysis import add_ranks
from utils_data_management import exclude_incomplete_tegs_function

# Configure logging
logger = logging.getLogger(__name__)

# Constants for data retrieval
ALL_DATA_PARQUET = "data/all-data.parquet"
ROUND_INFO_CSV = "data/round_info.csv"


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_all_data(exclude_teg_50: bool = True, exclude_incomplete_tegs: bool = False) -> pd.DataFrame:
    """
    Load the main golf dataset with optional filtering.
    
    Parameters:
        exclude_teg_50 (bool): Whether to exclude TEG 50 (special case tournament)
        exclude_incomplete_tegs (bool): Whether to exclude tournaments with missing rounds
        
    Returns:
        pd.DataFrame: The main golf dataset
        
    Purpose:
        THE most critical function in the entire application.
        Loads the core dataset that all analysis depends on.
        Cached for performance with TTL to balance freshness and speed.
    """
    try:
        df = read_file(ALL_DATA_PARQUET)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()
    
    # Ensure 'Year' is of integer type
    df['Year'] = df['Year'].astype('Int64')
    
    # Exclude TEG 50 if the flag is set
    if exclude_teg_50:
        df = df[df['TEGNum'] != 50]
    
    # Exclude incomplete TEGs if the flag is set
    if exclude_incomplete_tegs:
        df = exclude_incomplete_tegs_function(df)
    
    return df


@st.cache_data
def get_complete_teg_data():
    """
    Get complete tournament-level data (excludes TEG 50 and incomplete tournaments).
    
    Returns:
        pd.DataFrame: TEG-level aggregated data for complete tournaments only
        
    Purpose:
        Core dataset for TEG-level analysis and records.
        Used by TEG Records, TEG History, and performance analysis pages.
    """
    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=True)
    aggregated_data = aggregate_data(all_data, 'TEG')
    return aggregated_data


@st.cache_data
def get_teg_data_inc_in_progress():
    """
    Get tournament-level data including in-progress tournaments.
    
    Returns:
        pd.DataFrame: TEG-level aggregated data including incomplete tournaments
        
    Purpose:
        Used for current tournament analysis and leaderboards.
        Includes incomplete tournaments to show current status.
    """
    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'TEG')
    return aggregated_data


def get_round_data(ex_50=True, ex_incomplete=False):
    """
    Get round-level aggregated data.
    
    Parameters:
        ex_50 (bool): Whether to exclude TEG 50
        ex_incomplete (bool): Whether to exclude incomplete tournaments
        
    Returns:
        pd.DataFrame: Round-level aggregated data
        
    Purpose:
        Core dataset for round-level analysis.
        Used by round records, scoring analysis, and performance tracking.
    """
    all_data = load_all_data(exclude_teg_50=ex_50, exclude_incomplete_tegs=ex_incomplete)
    aggregated_data = aggregate_data(all_data, 'Round')
    return aggregated_data


@st.cache_data
def get_9_data():
    """
    Get 9-hole (front/back) aggregated data.
    
    Returns:
        pd.DataFrame: Front/back 9-hole aggregated data
        
    Purpose:
        Dataset for 9-hole analysis and records.
        Used for front 9 vs back 9 performance comparisons.
    """
    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'FrontBack')
    return aggregated_data    


@st.cache_data
def get_Pl_data():
    """
    Get player-level aggregated data.
    
    Returns:
        pd.DataFrame: Player-level aggregated career data
        
    Purpose:
        Dataset for player career statistics and analysis.
        Used for player profiles and career performance tracking.
    """
    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    aggregated_data = aggregate_data(all_data, 'Player')
    return aggregated_data


@st.cache_data
def get_ranked_teg_data():
    """
    Get ranked tournament-level data with performance rankings.
    
    Returns:
        pd.DataFrame: TEG-level data with ranking columns added
        
    Purpose:
        Core dataset for TEG performance analysis with rankings.
        Used by TEG Records and best performance identification.
    """
    df = get_complete_teg_data()
    ranked_data = add_ranks(df)
    return ranked_data


@st.cache_data
def get_ranked_round_data():
    """
    Get ranked round-level data with performance rankings.
    
    Returns:
        pd.DataFrame: Round-level data with ranking columns added
        
    Purpose:
        Core dataset for round performance analysis with rankings.
        Used by round records and best performance identification.
    """
    df = get_round_data()
    ranked_data = add_ranks(df)
    return ranked_data


@st.cache_data
def get_ranked_frontback_data():
    """
    Get ranked 9-hole data with performance rankings.
    
    Returns:
        pd.DataFrame: Front/back 9-hole data with ranking columns added
        
    Purpose:
        Dataset for 9-hole performance analysis with rankings.
        Used by 9-hole records and best performance identification.
    """
    df = get_9_data()
    ranked_data = add_ranks(df)
    return ranked_data


def get_teg_metadata(teg_num, round_num=None):
    """
    Get TEG metadata from round_info.csv.
    
    Args:
        teg_num: TEG number
        round_num: Optional round number for round-specific data
    
    Returns:
        dict: Metadata including area, course, date, year
        
    Purpose:
        Retrieves tournament context information for display.
        Used by scorecard generation and tournament information display.
    """
    try:
        round_info = read_file(ROUND_INFO_CSV)
        
        if round_num:
            # Get specific round data
            round_data = round_info[(round_info['TEGNum'] == teg_num) & 
                                  (round_info['Round'] == round_num)]
            if round_data.empty:
                return {}
            return round_data.iloc[0].to_dict()
        else:
            # Get TEG-level data (from first round)
            teg_data = round_info[round_info['TEGNum'] == teg_num]
            if teg_data.empty:
                return {}
            return teg_data.iloc[0].to_dict()
    except Exception:
        return {}


def get_scorecard_data(teg_num=None, round_num=None, player_code=None):
    """
    Get golf data for scorecard generation with optional filtering by TEG, Round, and/or Player.
    
    Args:
        teg_num: Optional TEG number filter
        round_num: Optional round number filter  
        player_code: Optional player code filter (e.g., 'JB')
    
    Returns:
        pd.DataFrame: Filtered and sorted data
        
    Examples:
        get_scorecard_data(18, 2, 'JB')     # One player's round
        get_scorecard_data(18, 2)           # All players in round 2 of TEG 18
        get_scorecard_data(18, player_code='JB')  # One player's tournament
        get_scorecard_data(18)              # All data for TEG 18
        
    Purpose:
        Flexible data retrieval for scorecard display and detailed round analysis.
        Supports various filtering combinations for different scorecard views.
    """
    all_data = load_all_data(exclude_incomplete_tegs=False)
    
    # Apply filters if provided
    if teg_num is not None:
        all_data = all_data[all_data['TEGNum'] == teg_num]
    
    if round_num is not None:
        all_data = all_data[all_data['Round'] == round_num]
    
    if player_code is not None:
        all_data = all_data[all_data['Pl'] == player_code]
    
    # Sort appropriately based on what filters were applied
    if player_code is not None and round_num is not None:
        # Single player, single round - sort by hole
        all_data = all_data.sort_values(['Hole'])
    elif player_code is not None:
        # Single player, multiple rounds - sort by round, then hole
        all_data = all_data.sort_values(['Round', 'Hole'])
    elif round_num is not None:
        # Single round, multiple players - sort by player, then hole
        all_data = all_data.sort_values(['Pl', 'Hole'])
    else:
        # Multiple rounds and players - sort by round, player, hole
        all_data = all_data.sort_values(['Round', 'Pl', 'Hole'])
    
    return all_data


@st.cache_data
def load_course_info():
    """
    Load unique course/area combinations from round_info.csv.
    
    Returns:
        pd.DataFrame: Unique combinations of Course and Area
        
    Purpose:
        Reference data for course selection and filtering.
        Used by course-specific analysis pages and filters.
    """
    round_info = read_file(ROUND_INFO_CSV)
    course_info = round_info[['Course', 'Area']].drop_duplicates()
    return course_info