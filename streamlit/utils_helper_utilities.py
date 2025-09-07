"""
Helper utilities for TEG data analysis.

Simple utility functions with minimal dependencies - LOWEST RISK module.
These functions provide basic helper functionality used throughout the codebase.
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Dict

# Configure logging
logger = logging.getLogger(__name__)

def get_base_directory():
    """
    Get the current working directory for the project.
    
    Returns:
        Path: Base directory path
        
    Purpose:
        Determines the root directory of the project, whether running locally or on Streamlit/Railway.
        Used by file operations and CSS loading functions.
    """
    # Get the current working directory
    current_dir = Path.cwd()
    
    # Check if we're in the Streamlit subfolder or not
    if current_dir.name == "streamlit":
        # If we're in the Streamlit folder, go up one level to TEG
        BASE_DIR = current_dir.parent
    else:
        # Assume we are already in the TEG directory
        BASE_DIR = current_dir
    
    return BASE_DIR

def get_current_branch():
    """
    Gets the current git branch.
    - On Railway, it uses the built-in 'RAILWAY_GIT_BRANCH' environment variable.
    - Locally, it attempts to get the branch using a git command.
    - Defaults to 'main' if the branch cannot be determined.
    
    Returns:
        str: Current git branch name
        
    Purpose:
        Used for GitHub API operations and deployment environment detection.
    """
    # Railway provides this variable automatically
    branch = os.getenv('RAILWAY_GIT_BRANCH')
    if branch:
        logger.info(f"Using branch from RAILWAY_GIT_BRANCH env var: {branch}")
        return branch

    # For local development, try to get the branch from the local git repo
    try:
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
        logger.info(f"Determined git branch locally: {branch}")
        return branch
    except Exception:
        # Fallback for local if git is not available or other issues
        logger.warning("Could not determine git branch locally. Defaulting to 'main'.")
        return 'main'

def get_player_name(initials: str) -> str:
    """
    Retrieve the player's full name based on their initials.

    Parameters:
        initials (str): The initials of the player.

    Returns:
        str: Full name of the player or 'Unknown Player' if not found.
        
    Purpose:
        Converts player codes to full names for display throughout the application.
    """
    PLAYER_DICT = {
        'AB': 'Alex BAKER',
        'JB': 'Jon BAKER',
        'DM': 'David MULLIN',
        'GW': 'Gregg WILLIAMS',
        'HM': 'Henry MELLER',
        'SN': 'Stuart NEUMANN',
        'JP': 'John PATTERSON',
        'GP': 'Graham PATTERSON',
        # Add more player initials and names as needed
    }
    return PLAYER_DICT.get(initials.upper(), 'Unknown Player')

def get_teg_rounds(TEG: str) -> int:
    """
    Return the number of rounds for a given TEG.
    If the TEG is not found in the dictionary, return 4 as the default value.

    Parameters:
        TEG (str): The TEG identifier (e.g., 'TEG 1', 'TEG 2', etc.)

    Returns:
        int: The total number of rounds for the given TEG, defaulting to 4 if not found.
        
    Purpose:
        Provides round count information for tournament structure calculations.
    """
    TEG_ROUNDS = {
        'TEG 1': 1,
        'TEG 2': 3,
        # Add more TEGs if necessary
    }
    return TEG_ROUNDS.get(TEG, 4)

def get_tegnum_rounds(TEGNum: int) -> int:
    """
    Return the number of rounds for a given TEG number.
    If the TEG is not found in the dictionary, return 4 as the default value.

    Parameters:
        TEGNum (int): The TEG number (e.g., 1, 2, etc.)

    Returns:
        int: The total number of rounds for the given TEG, defaulting to 4 if not found.
        
    Purpose:
        Provides round count information using numeric TEG identifiers.
    """
    TEGNUM_ROUNDS = {
        1: 1,
        2: 3,
        # Add more TEGs if necessary
    }
    return TEGNUM_ROUNDS.get(TEGNum, 4)

def convert_trophy_name(name: str) -> str:
    """
    Convert between short and long trophy names.

    Input is case-insensitive.
    Output always uses the canonical form from TROPHY_NAME_LOOKUPS.

    Examples:
        convert_trophy_name("trophy")       -> "TEG Trophy"
        convert_trophy_name("TEG Trophy")   -> "trophy"
        convert_trophy_name("jacket")       -> "Green Jacket"
        convert_trophy_name("green jacket") -> "jacket"
        
    Parameters:
        name (str): Trophy name to convert
        
    Returns:
        str: Converted trophy name
        
    Purpose:
        Provides consistent trophy name conversion for display and data processing.
    """
    # Trophy name lookups
    TROPHY_NAME_LOOKUPS_SHORTLONG = {
        "trophy": "TEG Trophy",
        "jacket": "Green Jacket",
        "spoon": "HMM Wooden Spoon",
    }
    TROPHY_NAME_LOOKUPS_LONGSHORT = {v.lower(): k for k, v in TROPHY_NAME_LOOKUPS_SHORTLONG.items()}
    
    key = name.strip().lower()

    # short -> long
    if key in TROPHY_NAME_LOOKUPS_SHORTLONG:
        return TROPHY_NAME_LOOKUPS_SHORTLONG[key]
    # long -> short
    if key in TROPHY_NAME_LOOKUPS_LONGSHORT:
        return TROPHY_NAME_LOOKUPS_LONGSHORT[key]

    raise ValueError(f"Unknown trophy name: {name!r}")

def get_trophy_full_name(trophy: str) -> str:
    """
    Get the full name of a trophy given its short name.

    Args:
        trophy (str): The short name of the trophy.

    Returns:
        str: The full name of the trophy.
        
    Purpose:
        Provides full trophy names for display in history and winner tables.
    """
    TROPHY_NAME_LOOKUPS_LONGSHORT = {
        "teg trophy": "trophy",
        "green jacket": "jacket", 
        "hmm wooden spoon": "spoon"
    }
    
    key = trophy.strip()
    
    if key.lower() in TROPHY_NAME_LOOKUPS_LONGSHORT:  
        # it's already a long name → use as-is
        trophy_name = key
    else:
        # otherwise assume it's a short name → convert
        trophy_name = convert_trophy_name(key)

    return trophy_name

def list_fields_by_aggregation_level(df):
    """
    List available fields by aggregation level for dynamic aggregation.
    
    Parameters:
        df: DataFrame to analyze
        
    Returns:
        dict: Fields available at each aggregation level
        
    Purpose:
        Supports the flexible aggregation system by determining which fields
        are unique at different levels of data aggregation.
    """
    # Define the levels of aggregation
    aggregation_levels = {
        'Player': ['Player'],
        'TEG': ['Player', 'TEG'],
        'Round': ['Player', 'TEG', 'Round'],
        'FrontBack': ['Player', 'TEG', 'Round', 'FrontBack'],
        #'Hole': ['Player', 'TEG', 'Round', 'FrontBack', 'Hole']
    }

    # Dictionary to hold fields unique at each level
    fields_by_level = {level: [] for level in aggregation_levels}

    # For each field in the dataframe, determine its uniqueness level
    for col in df.columns:
        for level, group_fields in aggregation_levels.items():
            # Check if the field is unique at this level
            if df.groupby(group_fields)[col].nunique().max() == 1:
                fields_by_level[level].append(col)
                break  # Stop after finding the lowest level of uniqueness

    return fields_by_level