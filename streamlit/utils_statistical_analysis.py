"""
Statistical analysis utilities for TEG data analysis.

Functions for performance analysis, ranking, and statistical calculations.
These functions provide the core statistical analysis functionality used throughout the application.
"""

import pandas as pd
import numpy as np
import logging

# Import dependencies from other modules  
from utils_display_formatting import ordinal

# Configure logging
logger = logging.getLogger(__name__)

def add_ranks(df, fields_to_rank=None, rank_ascending=None):
    """
    Adds ranking columns to the DataFrame for optionally specified fields or all scoring fields, both within each player's rounds 
    and across all rounds. The ranking can be done in ascending or descending order.
    Ranking will be applied at lowest level of aggregation present in the data.

    Parameters:
    -----------
    df : pandas.DataFrame
        The input DataFrame containing the data. 
        It must include at least a 'Player' column and 
        the fields to be ranked (e.g., 'Sc', 'GrossVP', 'NetVP', 'Stableford').

    fields_to_rank : list or str, optional
        The fields to rank. This can be a list of field names (e.g., ['Sc', 'GrossVP']) or a single 
        field name as a string (e.g., 'Sc'). If not provided, the default is ['Sc', 'GrossVP', 'NetVP', 
        'Stableford'].

    rank_ascending : bool, optional
        The order of ranking. If not provided, the function defaults to:
        - True for all fields except 'Stableford', where it defaults to False.
        If provided, this will apply the same order for all fields.

    Returns:
    --------
    pandas.DataFrame
        A DataFrame with additional columns for the ranking of each specified field:
        - 'Rank_within_player_<field>': The rank of the field within each player's rounds.
        - 'Rank_within_all_<field>': The rank of the field across all rounds.
        
    Purpose:
        Core ranking functionality used by analysis pages to identify best/worst performances.
        Used by get_ranked_*_data functions and performance analysis throughout the application.
    """
    input_rank_ascending = rank_ascending

    # If fields_to_rank is not provided, use default list of fields
    if fields_to_rank is None:
        fields_to_rank = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    
    # Check if fields_to_rank is a string, convert to list if necessary
    if isinstance(fields_to_rank, str):
        fields_to_rank = [fields_to_rank]
    
    for field in fields_to_rank:
        # Determine default value for rank_ascending for each field
        if input_rank_ascending is None:
            rank_ascending = False if 'Stableford' in field else True
        
        # Check if the field exists in the dataframe
        if field not in df.columns:
            print(f"Warning: Field '{field}' not found in DataFrame. Available columns: {list(df.columns)}")
            continue
        
        # Rank within each player's rounds
        df[f'Rank_within_player_{field}'] = df.groupby('Player')[field].rank(ascending=rank_ascending, method='min')
        
        # Rank across all rounds
        df[f'Rank_within_all_{field}'] = df[field].rank(ascending=rank_ascending, method='min')
    
    return df

def get_best(df, measure_to_use, player_level=False, top_n=1):
    """
    Get the best performances based on a specified measure.
    
    Parameters:
        df (pd.DataFrame): DataFrame with ranking columns
        measure_to_use (str): The measure to use ('Sc', 'GrossVP', 'NetVP', 'Stableford')
        player_level (bool): If True, rank within player; if False, rank across all players
        top_n (int): Number of top performances to return
        
    Returns:
        pd.DataFrame: DataFrame containing the best performances
        
    Purpose:
        Identifies best performances for analysis and record pages.
        Used by TEG Records, Best Performance pages, and statistical displays.
    """
    valid_measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    if measure_to_use not in valid_measures:
        error_message = f"Invalid measure: '{measure_to_use}'. Valid options are: {', '.join(valid_measures)}"
        raise ValueError(error_message)

    if player_level is None:
        player_level = False

    if top_n is None:
        top_n = 1
    
    measure_fn = 'Rank_within_' + ('player' if player_level else 'all') + f'_{measure_to_use}' 

    # Check if ranking column exists
    if measure_fn not in df.columns:
        raise KeyError(f"Ranking column '{measure_fn}' not found. Ensure add_ranks() has been called first.")
    
    return df[df[measure_fn] <= top_n]

def get_worst(df, measure_to_use, player_level=False, top_n=1):
    """
    Get the worst performances based on a specified measure.
    
    Parameters:
        df (pd.DataFrame): DataFrame with ranking columns
        measure_to_use (str): The measure to use ('Sc', 'GrossVP', 'NetVP', 'Stableford')
        player_level (bool): If True, rank within player; if False, rank across all players
        top_n (int): Number of worst performances to return
        
    Returns:
        pd.DataFrame: DataFrame containing the worst performances
        
    Purpose:
        Identifies worst performances for analysis and TEG Worsts pages.
        Used for performance analysis and statistical displays.
    """
    valid_measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    if measure_to_use not in valid_measures:
        error_message = f"Invalid measure: '{measure_to_use}'. Valid options are: {', '.join(valid_measures)}"
        raise ValueError(error_message)

    if player_level is None:
        player_level = False

    if top_n is None:
        top_n = 1
    
    if player_level == False:
        # For worst across all players, we want the highest ranks (worst performances)
        measure_fn = f'Rank_within_all_{measure_to_use}'
        if measure_fn not in df.columns:
            raise KeyError(f"Ranking column '{measure_fn}' not found. Ensure add_ranks() has been called first.")
        
        # Get the maximum rank values (worst performances) 
        max_rank = df[measure_fn].max()
        return df[df[measure_fn] >= (max_rank - top_n + 1)]
    else:
        # For worst within each player
        measure_fn = f'Rank_within_player_{measure_to_use}'
        if measure_fn not in df.columns:
            raise KeyError(f"Ranking column '{measure_fn}' not found. Ensure add_ranks() has been called first.")
            
        # Group by player and get worst performances
        df = df.groupby('Player', group_keys=False).apply(lambda x: x.nlargest(top_n, measure_fn))
        return df

def get_teg_winners(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate TEG winners, best net, gross, and worst net by TEG.

    Parameters:
        df (pd.DataFrame): DataFrame containing the golf data.

    Returns:
        pd.DataFrame: DataFrame summarizing TEG winners.
        
    Purpose:
        Identifies tournament winners for TEG History page and trophy calculations.
        Used by history analysis and winner tracking functionality.
    """
    logger.info("Calculating TEG winners.")
    
    # Group by TEG and Player, then sum the relevant columns
    grouped = df.groupby(['TEG', 'Player']).agg({
        'Stableford': 'sum',
        'GrossVP': 'sum',
        'NetVP': 'sum'
    }).reset_index()
    
    # Find the winner for each category by TEG
    winners = []
    
    for teg in grouped['TEG'].unique():
        teg_data = grouped[grouped['TEG'] == teg]
        
        # TEG Winner (highest Stableford)
        teg_winner = teg_data.loc[teg_data['Stableford'].idxmax()]
        winners.append({
            'TEG': teg,
            'Category': 'TEG Winner', 
            'Player': teg_winner['Player'],
            'Score': teg_winner['Stableford'],
            'Measure': 'Stableford'
        })
        
        # Best Gross (highest GrossVP)
        best_gross = teg_data.loc[teg_data['GrossVP'].idxmax()]
        winners.append({
            'TEG': teg,
            'Category': 'Best Gross',
            'Player': best_gross['Player'], 
            'Score': best_gross['GrossVP'],
            'Measure': 'GrossVP'
        })
        
        # Best Net (highest NetVP)
        best_net = teg_data.loc[teg_data['NetVP'].idxmax()]
        winners.append({
            'TEG': teg,
            'Category': 'Best Net',
            'Player': best_net['Player'],
            'Score': best_net['NetVP'], 
            'Measure': 'NetVP'
        })
        
        # Worst Net (lowest NetVP)
        worst_net = teg_data.loc[teg_data['NetVP'].idxmin()]
        winners.append({
            'TEG': teg,
            'Category': 'Worst Net',
            'Player': worst_net['Player'],
            'Score': worst_net['NetVP'],
            'Measure': 'NetVP'
        })
    
    winners_df = pd.DataFrame(winners)
    logger.info(f"TEG winners calculated for {len(grouped['TEG'].unique())} TEGs")
    return winners_df