"""
Data processing functions for best TEGs and rounds analysis.

This module contains functions for:
- Processing ranked TEG and round data
- Creating performance tables with proper formatting
- Handling measure name mappings for user interface
"""

import pandas as pd


def get_measure_name_mappings():
    """
    Get mapping between user-friendly names and internal measure names.
    
    Returns:
        tuple: (name_mapping, inverted_mapping) for display and processing
        
    Purpose:
        Provides consistent naming between user interface and data processing
        Allows easy conversion between display names and database column names
    """
    name_mapping = {
        'Gross vs Par': 'GrossVP',
        'Score': 'Sc',
        'Net vs Par': 'NetVP',
        'Stableford': 'Stableford'
    }
    inverted_mapping = {v: k for k, v in name_mapping.items()}
    
    return name_mapping, inverted_mapping


def prepare_best_teg_table(teg_data_ranked, selected_measure, selected_friendly_name, n_keep):
    """
    Create formatted table of best TEG performances.
    
    Args:
        teg_data_ranked (pd.DataFrame): Ranked TEG performance data
        selected_measure (str): Internal measure name (e.g., 'GrossVP')
        selected_friendly_name (str): Display name (e.g., 'Gross vs Par')
        n_keep (int): Number of top performances to show
        
    Returns:
        pd.DataFrame: Formatted table ready for display
        
    Purpose:
        Creates clean, ranked table showing top TEG performances
        Handles column renaming and data type formatting for display
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Calculate ranking column name
    rank_measure = f'Rank_within_all_{selected_measure}'
    
    # Get best performances from utils function
    from utils import get_best
    
    best_tegs = (get_best(teg_data_ranked, selected_measure, player_level=False, top_n=n_keep)
                 .sort_values(by=rank_measure, ascending=True)
                 .rename(columns={rank_measure: '#'})
                 .rename(columns=inverted_name_mapping))
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'TEG', 'Year']
    best_tegs = best_tegs[display_columns]
    
    # Convert numeric columns to integers for clean display
    numeric_columns = best_tegs.select_dtypes(include=['float64', 'int64']).columns
    best_tegs[numeric_columns] = best_tegs[numeric_columns].astype(int)
    
    return best_tegs


def prepare_best_round_table(rd_data_ranked, selected_measure, selected_friendly_name, n_keep):
    """
    Create formatted table of best round performances.
    
    Args:
        rd_data_ranked (pd.DataFrame): Ranked round performance data
        selected_measure (str): Internal measure name (e.g., 'GrossVP')
        selected_friendly_name (str): Display name (e.g., 'Gross vs Par')
        n_keep (int): Number of top performances to show
        
    Returns:
        pd.DataFrame: Formatted table ready for display
        
    Purpose:
        Creates clean, ranked table showing top individual round performances
        Formats round identifiers and handles data type conversions
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Calculate ranking column name
    rank_measure = f'Rank_within_all_{selected_measure}'
    
    # Get best performances from utils function
    from utils import get_best
    
    best_rounds = (get_best(rd_data_ranked, selected_measure, player_level=False, top_n=n_keep)
                   .sort_values(by=rank_measure, ascending=True)
                   .rename(columns={rank_measure: '#'})
                   .rename(columns=inverted_name_mapping))
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'Round', 'Course', 'Year']
    best_rounds = best_rounds[display_columns]
    
    # Convert numeric columns to integers for clean display
    numeric_columns = best_rounds.select_dtypes(include=['float64', 'int64']).columns
    best_rounds[numeric_columns] = best_rounds[numeric_columns].astype(int)
    
    return best_rounds


def prepare_round_data_with_identifiers(rd_data_ranked):
    """
    Prepare round data with combined TEG|Round identifiers.
    
    Args:
        rd_data_ranked (pd.DataFrame): Raw ranked round data
        
    Returns:
        pd.DataFrame: Round data with formatted round identifiers
        
    Purpose:
        Creates readable round identifiers combining TEG and round number
        Format: "TEG 15|R1" for TEG 15, Round 1
    """
    rd_data_formatted = rd_data_ranked.copy()
    rd_data_formatted['Round'] = rd_data_formatted['TEG'] + '|R' + rd_data_formatted['Round'].astype(str)
    
    return rd_data_formatted


def prepare_personal_best_teg_table(teg_data_ranked, selected_measure, selected_friendly_name):
    """
    Create formatted table of personal best TEG performances for each player.
    
    Args:
        teg_data_ranked (pd.DataFrame): Ranked TEG performance data
        selected_measure (str): Internal measure name (e.g., 'GrossVP')
        selected_friendly_name (str): Display name (e.g., 'Gross vs Par')
        
    Returns:
        pd.DataFrame: Formatted table with each player's best TEG performance
        
    Purpose:
        Shows each player's personal best TEG performance in the selected measure
        Includes overall ranking to show how personal bests compare across all players
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Use player-level ranking to get 1 best performance per player
    rank_all_time = f'Rank_within_all_{selected_measure}'
    
    # Get best performances from utils function (player_level=True gets 1 per player)
    from utils import get_best
    
    personal_best_tegs = (get_best(teg_data_ranked, selected_measure, player_level=True, top_n=1)
                         .sort_values(by=rank_all_time, ascending=True)
                         .rename(columns={rank_all_time: '#'})
                         .rename(columns=inverted_name_mapping))
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'TEG', 'Year']
    personal_best_tegs = personal_best_tegs[display_columns]
    
    # Convert numeric columns to integers for clean display
    numeric_columns = personal_best_tegs.select_dtypes(include=['float64', 'int64']).columns
    personal_best_tegs[numeric_columns] = personal_best_tegs[numeric_columns].astype(int)
    
    return personal_best_tegs


def prepare_personal_best_round_table(rd_data_ranked, selected_measure, selected_friendly_name):
    """
    Create formatted table of personal best round performances for each player.
    
    Args:
        rd_data_ranked (pd.DataFrame): Ranked round performance data
        selected_measure (str): Internal measure name (e.g., 'GrossVP')
        selected_friendly_name (str): Display name (e.g., 'Gross vs Par')
        
    Returns:
        pd.DataFrame: Formatted table with each player's best round performance
        
    Purpose:
        Shows each player's personal best individual round performance
        Includes overall ranking to show how personal bests compare across all players
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Use player-level ranking to get 1 best performance per player
    rank_all_time = f'Rank_within_all_{selected_measure}'
    
    # Get best performances from utils function (player_level=True gets 1 per player)
    from utils import get_best
    
    personal_best_rounds = (get_best(rd_data_ranked, selected_measure, player_level=True, top_n=1)
                           .sort_values(by=rank_all_time, ascending=True)
                           .rename(columns={rank_all_time: '#'})
                           .rename(columns=inverted_name_mapping))
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'Round', 'Course', 'Year']
    personal_best_rounds = personal_best_rounds[display_columns]
    
    # Convert numeric columns to integers for clean display
    numeric_columns = personal_best_rounds.select_dtypes(include=['float64', 'int64']).columns
    personal_best_rounds[numeric_columns] = personal_best_rounds[numeric_columns].astype(int)
    
    return personal_best_rounds