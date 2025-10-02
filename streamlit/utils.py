import pandas as pd
import os
import numpy as np
import logging
from math import floor
from google.oauth2.service_account import Credentials
import gspread
from typing import Dict, Any, List
import streamlit as st
from pathlib import Path
from typing import Optional
import base64
from github import Github
from io import BytesIO, StringIO
import subprocess
from datetime import datetime

#print("utils module is being imported")

# Configure Logging
#logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def clear_all_caches():
    """Clears all Streamlit data caches"""
    st.cache_data.clear()


def get_base_directory():
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

# ============================================
#  CONSTANTS AND CONFIGURATIONS
# ============================================

# --- GitHub Repository ---
GITHUB_REPO = "jonbaker99/teg_v2"

# --- Base Directory ---
# Determines the root directory of the project, whether running locally or on Streamlit/Railway.
BASE_DIR = Path.cwd().parent if Path.cwd().name == "streamlit" else Path.cwd()

# --- Data File Paths ---
# Defines the paths for all data files, used for both local and GitHub access.
# Using Parquet for primary data files for performance.
ALL_DATA_PARQUET = "data/all-data.parquet"
ALL_SCORES_PARQUET = "data/all-scores.parquet" # Changed from .csv to .parquet
STREAKS_PARQUET = "data/streaks.parquet"
BESTBALL_PARQUET = "data/bestball.parquet"
HANDICAPS_CSV = "data/handicaps.csv"
ROUND_INFO_CSV = "data/round_info.csv"

# Commentary/analysis cache files (regenerated when data changes)
COMMENTARY_ROUND_EVENTS_PARQUET = "data/commentary_round_events.parquet"
COMMENTARY_ROUND_SUMMARY_PARQUET = "data/commentary_round_summary.parquet"
COMMENTARY_TOURNAMENT_SUMMARY_PARQUET = "data/commentary_tournament_summary.parquet"
COMMENTARY_ROUND_STREAKS_PARQUET = "data/commentary_round_streaks.parquet"
COMMENTARY_TOURNAMENT_STREAKS_PARQUET = "data/commentary_tournament_streaks.parquet"

# This is a mirrored version of the main data file, useful for ad-hoc analysis.
ALL_DATA_CSV_MIRROR = "data/all-data.csv"

def get_current_branch():
    """
    Gets the current git branch.
    - On Railway, it uses the built-in 'RAILWAY_GIT_BRANCH' environment variable.
    - Locally, it attempts to get the branch using a git command.
    - Defaults to 'main' if the branch cannot be determined.
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

GITHUB_BRANCH = get_current_branch()

def read_from_github(file_path):
    """Simple GitHub file reading with proper base64 decoding"""
    from github import Github
    from io import BytesIO, StringIO
    import base64
    
    token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN')
    g = Github(token)
    repo = g.get_repo(GITHUB_REPO)
    content = repo.get_contents(file_path, ref=get_current_branch())
    
    if file_path.endswith('.csv'):
        # Decode the base64 content first
        decoded_content = base64.b64decode(content.content).decode('utf-8')
        return pd.read_csv(StringIO(decoded_content))
    elif file_path.endswith('.parquet'):
        # For parquet files, decode to bytes
        decoded_bytes = base64.b64decode(content.content)
        return pd.read_parquet(BytesIO(decoded_bytes))
    else:
        # For other files, return decoded string
        return base64.b64decode(content.content).decode('utf-8')

def write_to_github(file_path, data, commit_message="Update data"):
    from github import Github
    from io import BytesIO

    token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN')
    g = Github(token)
    repo = g.get_repo(GITHUB_REPO)

    branch = get_current_branch()

    # Prepare content
    if isinstance(data, pd.DataFrame):
        if file_path.endswith('.csv'):
            content = data.to_csv(index=False)
        elif file_path.endswith('.parquet'):
            buffer = BytesIO()
            data.to_parquet(buffer, index=False)
            content = buffer.getvalue()
    else:
        content = data

    # Try update, fallback to create
    try:
        file = repo.get_contents(file_path, ref=branch)
        repo.update_file(file_path, commit_message, content, file.sha, branch=get_current_branch())
    except:
        repo.create_file(file_path, commit_message, content, branch=get_current_branch())

    st.cache_data.clear()

# Enhanced read_file and write_file functions for utils.py
# Replace your existing functions with these

def read_file(file_path: str) -> pd.DataFrame:
    """
    Read from volume if exists, otherwise cache from GitHub.
    No timestamp checking - simple cache with manual invalidation.
    """
    if os.getenv('RAILWAY_ENVIRONMENT'):
        volume_path = f"/mnt/data_repo/{file_path}"
        
        # Simple check: does file exist in volume?
        if os.path.exists(volume_path):
            # Fast path: read from volume (NO API calls)
            try:
                if file_path.endswith('.csv'):
                    return pd.read_csv(volume_path)
                elif file_path.endswith('.parquet'):
                    return pd.read_parquet(volume_path)
                else:
                    raise ValueError(f"Unsupported file type: {file_path}")
            except Exception as e:
                logger.warning(f"Error reading from volume {volume_path}: {e}")
                # If volume read fails, fall back to GitHub
                pass
        
        # File not cached or volume read failed: download and cache
        try:
            data = read_from_github(file_path)
            
            # Cache to volume for next time
            os.makedirs(os.path.dirname(volume_path), exist_ok=True)
            
            if file_path.endswith('.csv'):
                data.to_csv(volume_path, index=False)
            elif file_path.endswith('.parquet'):
                data.to_parquet(volume_path, index=False)
            
            logger.info(f"Cached {file_path} to volume for future reads")
            return data
            
        except Exception as e:
            logger.error(f"Error reading {file_path} from GitHub: {e}")
            raise
    else:
        # Local development unchanged
        local_path = BASE_DIR / file_path
        if file_path.endswith('.csv'):
            return pd.read_csv(local_path)
        elif file_path.endswith('.parquet'):
            return pd.read_parquet(local_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")


def write_file(file_path: str, data: pd.DataFrame, commit_message: str = "Update data"):
    """
    Write to both volume (fast) and GitHub (sync) simultaneously.
    """
    if os.getenv('RAILWAY_ENVIRONMENT'):
        # Write to volume first (fast local write)
        volume_path = f"/mnt/data_repo/{file_path}"
        
        try:
            os.makedirs(os.path.dirname(volume_path), exist_ok=True)
            
            if file_path.endswith('.csv'):
                data.to_csv(volume_path, index=False)
            elif file_path.endswith('.parquet'):
                data.to_parquet(volume_path, index=False)
            else:
                raise ValueError(f"Unsupported file type: {file_path}")
                
            logger.info(f"Successfully wrote {file_path} to volume")
            
        except Exception as e:
            logger.error(f"Error writing to volume {volume_path}: {e}")
            # Continue to GitHub write even if volume fails
        
        # Write to GitHub (for cross-environment sync)
        try:
            write_to_github(file_path, data, commit_message)
            logger.info(f"Successfully wrote {file_path} to GitHub")
        except Exception as e:
            logger.error(f"Error writing to GitHub: {e}")
            raise  # Re-raise GitHub errors as they're critical
            
    else:
        # Local development unchanged
        local_path = BASE_DIR / file_path
        if file_path.endswith('.csv'):
            data.to_csv(local_path, index=False)
        elif file_path.endswith('.parquet'):
            data.to_parquet(local_path, index=False)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")
    
    # Clear caches after successful write
    st.cache_data.clear()


# Optional: Add this utility function for manual cache management
def clear_volume_cache(file_path: str = None):
    """
    Clear volume cache for a specific file or all files.
    Useful for forcing refresh from GitHub.
    """
    if not os.getenv('RAILWAY_ENVIRONMENT'):
        return "Not running on Railway - no volume to clear"
    
    try:
        if file_path:
            # Clear specific file
            volume_path = f"/mnt/data_repo/{file_path}"
            if os.path.exists(volume_path):
                os.remove(volume_path)
                return f"Cleared volume cache for {file_path}"
            else:
                return f"File {file_path} not found in volume cache"
        else:
            # Clear entire volume
            import shutil
            volume_base = "/mnt/data_repo"
            if os.path.exists(volume_base):
                shutil.rmtree(volume_base)
                return "Cleared entire volume cache"
            else:
                return "Volume cache already empty"
                
    except Exception as e:
        return f"Error clearing volume cache: {e}"



def backup_file(source_path, backup_path):
    """Create a backup of a file"""
    if os.getenv('RAILWAY_ENVIRONMENT'):
        # Read and write with new name (to backups branch)
        data = read_from_github(source_path)
        write_to_github(backup_path, data, f"Backup of {source_path}")
    else:
        import shutil
        backup_full_path = BASE_DIR / backup_path
        backup_full_path.parent.mkdir(parents=True, exist_ok=True)  # 👈 create folders if needed
        shutil.copy(BASE_DIR / source_path, backup_full_path)

## Temporary compatibility wrappers (remove after migration)
##  THESE CAN BE DELETED IF EVERYTHING IS RUNNING OK


# def read_file_from_storage(file_path, file_type='csv'):
#     """Compatibility wrapper - will be removed after migration"""
#     return read_file(file_path, file_type)

# def write_file_to_storage(file_path, data, file_type='csv', commit_message="Update data"):
#     """Compatibility wrapper - will be removed after migration"""
#     write_file(file_path, data, commit_message)

# def backup_file_on_storage(source_path, backup_path):
#     """Compatibility wrapper - will be removed after migration"""
#     backup_file(source_path, backup_path)

### END OF TEMPORARY COMPATIBILITY WRAPPERS




# FILE_PATH_ALL_DATA = os.path.join(BASE_DIR, "../data/all-data.parquet")  # Dynamically construct the path
FILE_PATH_ALL_DATA = ALL_DATA_PARQUET

TOTAL_HOLES = 18

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

TEG_ROUNDS = {
    'TEG 1': 1,
    'TEG 2': 3,
    # Add more TEGs if necessary
}

# Auto-generated from TEG_ROUNDS
TEGNUM_ROUNDS = {
    int(teg.split()[1]): rounds 
    for teg, rounds in TEG_ROUNDS.items()
}

TEG_OVERRIDES = {
    'TEG 5': {
        'Best Net': 'Gregg WILLIAMS',
        'Best Gross': 'Stuart NEUMANN*'
    }
}

@st.cache_data  
def load_all_data(exclude_teg_50: bool = True, exclude_incomplete_tegs: bool = False) -> pd.DataFrame:
    try:
        df = read_file(ALL_DATA_PARQUET)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()
    
    # Load round info data to get Area information
    try:
        round_info = read_file(ROUND_INFO_CSV)
        # Join to get Area information (select only columns we need to avoid duplicates)
        round_info_subset = round_info[['TEGNum', 'Round', 'Area']].copy()
        df = df.merge(round_info_subset, on=['TEGNum', 'Round'], how='left')
    except Exception as e:
        st.warning(f"Could not load round info for Area data: {e}")
    
    # Ensure 'Year' is of integer type
    df['Year'] = df['Year'].astype('Int64')
    
    # Exclude TEG 50 if the flag is set
    if exclude_teg_50:
        df = df[df['TEGNum'] != 50]
    
    # Exclude incomplete TEGs if the flag is set
    if exclude_incomplete_tegs:
        df = exclude_incomplete_tegs_function(df)
    
    return df

def get_number_of_completed_rounds_by_teg(df: pd.DataFrame) -> pd.DataFrame:
    num_rounds = (
        df.groupby(['TEGNum', 'TEG'])['Round']
          .nunique()
          .reset_index(name="num_rounds")
    )
    return num_rounds

def get_incomplete_tegs(df: pd.DataFrame) -> pd.DataFrame:

    # Compute the number of unique COMPLETED rounds per TEGNum
    all_rounds = df.groupby('TEGNum')['Round'].nunique()
    
    # Create a DataFrame with TEGNum and observed rounds
    teg_rounds = all_rounds.reset_index(name='AllRounds')
    
    # Apply get_teg_rounds to get the expected number of rounds per TEGNum
    teg_rounds['ExpectedRounds'] = teg_rounds['TEGNum'].apply(get_tegnum_rounds)
    
    # Identify incomplete TEGs where observed rounds do not match expected rounds
    incomplete_tegs = teg_rounds[teg_rounds['AllRounds'] != teg_rounds['ExpectedRounds']]['TEGNum'] 

    return incomplete_tegs


def exclude_incomplete_tegs_function(df: pd.DataFrame) -> pd.DataFrame:
    """
    Exclude TEGs with incomplete rounds based on the number of unique rounds in the data.
    
    Parameters:
        df (pd.DataFrame): The dataset to filter.
    
    Returns:
        pd.DataFrame: The dataset with incomplete TEGs excluded.
    """
    # Compute the number of unique COMPLETED rounds per TEGNum
    observed_rounds = df.groupby('TEGNum')['Round'].nunique()
    
    # Create a DataFrame with TEGNum and observed rounds
    teg_rounds = observed_rounds.reset_index(name='ObservedRounds')
    
    # Apply get_teg_rounds to get the expected number of rounds per TEGNum
    teg_rounds['ExpectedRounds'] = teg_rounds['TEGNum'].apply(get_tegnum_rounds)
    
    # Identify incomplete TEGs where observed rounds do not match expected rounds
    incomplete_tegs = teg_rounds[teg_rounds['ObservedRounds'] != teg_rounds['ExpectedRounds']]['TEGNum']
    
    # Exclude the incomplete TEGs from the dataset
    df_filtered = df[~df['TEGNum'].isin(incomplete_tegs)]
    
    return df_filtered

def get_player_name(initials: str) -> str:
    """
    Retrieve the player's full name based on their initials.

    Parameters:
        initials (str): The initials of the player.

    Returns:
        str: Full name of the player or 'Unknown Player' if not found.
    """
    return PLAYER_DICT.get(initials.upper(), 'Unknown Player')


def process_round_for_all_scores(long_df: pd.DataFrame, hc_long: pd.DataFrame) -> pd.DataFrame:
    """
    Process round data for all scores by computing various metrics.

    Parameters:
        long_df (pd.DataFrame): DataFrame containing round data.
        hc_long (pd.DataFrame): DataFrame containing handicap data.

    Returns:
        pd.DataFrame: Processed DataFrame with additional computed columns.
    """
    logger.info("Processing rounds for all scores.")

    # Rename columns if they exist
    long_df.rename(columns={'Score': 'Sc', 'Par': 'PAR'}, inplace=True)
    for col in ['Sc', 'PAR']:
        if col not in long_df.columns:
            logger.warning(f"Column '{col}' not found.")

    # Create 'TEG' column
    long_df['TEG'] = 'TEG ' + long_df['TEGNum'].astype(str)

    # Merge handicap data
    long_df = long_df.merge(hc_long, on=['TEG', 'Pl'], how='left')
    long_df['HC'] = long_df['HC'].fillna(0)
    logger.debug("Handicap data merged.")

    # Create 'HoleID' using vectorized operations
    long_df['HoleID'] = (
        "T" + long_df['TEGNum'].astype(int).astype(str).str.zfill(2) +
        "|R" + long_df['Round'].astype(int).astype(str).str.zfill(2) +
        "|H" + long_df['Hole'].astype(int).astype(str).str.zfill(2)
    )

    # Determine 'FrontBack' using vectorized operations
    long_df['FrontBack'] = np.where(long_df['Hole'] < 10, 'Front', 'Back')

    # Map player names using the more efficient .map() method
    long_df['Player'] = long_df['Pl'].map(PLAYER_DICT).fillna('Unknown Player')

    # Calculate 'HCStrokes' using vectorized operations
    long_df['HCStrokes'] = (long_df['HC'] // 18) + ((long_df['HC'] % 18 >= long_df['SI']).astype(int))

    # Calculate scoring metrics
    long_df['GrossVP'] = long_df['Sc'] - long_df['PAR']
    long_df['Net'] = long_df['Sc'] - long_df['HCStrokes']
    long_df['NetVP'] = long_df['Net'] - long_df['PAR']
    long_df['Stableford'] = (2 - long_df['NetVP']).clip(lower=0)

    logger.info("Round processing completed.")
    return long_df


def check_hc_strokes_combinations(transformed_df: pd.DataFrame) -> pd.DataFrame:
    """
    Check unique combinations of HC, SI, and HCStrokes.

    Parameters:
        transformed_df (pd.DataFrame): DataFrame containing the transformed golf data.

    Returns:
        pd.DataFrame: DataFrame with unique combinations of HC, SI, and HCStrokes.
    """
    hc_si_strokes_df = transformed_df[['HC', 'SI', 'HCStrokes']].drop_duplicates()
    logger.info("Unique combinations of HC, SI, and HCStrokes obtained.")
    return hc_si_strokes_df


def add_cumulative_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add cumulative scores and averages for specified measures across rounds, TEGs, and career.

    Parameters:
        df (pd.DataFrame): DataFrame containing the golf data.

    Returns:
        pd.DataFrame: DataFrame with cumulative and average scores added.
    """
    logger.info("Adding cumulative scores and averages.")

    # Sort data
    df.sort_values(by=['Pl', 'TEGNum', 'Round', 'Hole'], inplace=True)

    # Create 'Hole Order Ever'
    df['Hole Order Ever'] = df.groupby(['Pl']).cumcount() + 1

    measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    groupings = {
        'Round': ['Pl', 'TEGNum', 'Round'],
        'TEG': ['Pl', 'TEGNum'],
        'Career': ['Pl']
    }

    for measure in measures:
        for period, group_cols in groupings.items():
            cum_col = f'{measure} Cum {period}'
            df[cum_col] = df.groupby(group_cols)[measure].cumsum()

    # Add counts
    df['TEG Count'] = df.groupby(['Pl', 'TEGNum']).cumcount() + 1
    df['Career Count'] = df.groupby('Pl').cumcount() + 1

    # Add averages
    for measure in measures:
        df[f'{measure} Round Avg'] = df[f'{measure} Cum Round'] / df['Hole']
        df[f'{measure} TEG Avg'] = df[f'{measure} Cum TEG'] / df['TEG Count']
        df[f'{measure} Career Avg'] = df[f'{measure} Cum Career'] / df['Career Count']

    logger.info("Cumulative scores and averages added.")
    return df


def add_rankings_and_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add TEG-level rankings and gaps to leader for cumulative scores.

    This function adds four columns:
    - Rank_GrossVP_TEG: Player's rank based on cumulative GrossVP at each hole in the TEG
    - Rank_Stableford_TEG: Player's rank based on cumulative Stableford at each hole in the TEG
    - Gap_GrossVP_TEG: Difference from leader's cumulative GrossVP
    - Gap_Stableford_TEG: Difference from leader's cumulative Stableford

    Parameters:
        df (pd.DataFrame): DataFrame with cumulative scores already calculated

    Returns:
        pd.DataFrame: DataFrame with ranking and gap columns added
    """
    logger.info("Adding TEG rankings and gaps to leader.")

    # Create TEG_Hole column for grouping (cumulative hole number within TEG)
    df['TEG_Hole'] = df['Hole'] + 18 * (df['Round'] - 1)

    # Add rankings for GrossVP (lower is better - ascending)
    df['Rank_GrossVP_TEG'] = df.groupby(['TEGNum', 'TEG_Hole'])['GrossVP Cum TEG'].rank(
        method='min', ascending=True, na_option='keep'
    )

    # Add rankings for Stableford (higher is better - descending)
    df['Rank_Stableford_TEG'] = df.groupby(['TEGNum', 'TEG_Hole'])['Stableford Cum TEG'].rank(
        method='min', ascending=False, na_option='keep'
    )

    # Add gap to leader for GrossVP (leader has minimum, so gap = player - leader)
    df['Gap_GrossVP_TEG'] = df.groupby(['TEGNum', 'TEG_Hole'])['GrossVP Cum TEG'].transform(
        lambda x: x - x.min()
    )

    # Add gap to leader for Stableford (leader has maximum, so gap = leader - player)
    df['Gap_Stableford_TEG'] = df.groupby(['TEGNum', 'TEG_Hole'])['Stableford Cum TEG'].transform(
        lambda x: x.max() - x
    )

    logger.info("TEG rankings and gaps to leader added.")
    return df


def save_to_parquet(df: pd.DataFrame, output_file: str) -> None:
    """
    Save DataFrame to a Parquet file.

    Parameters:
        df (pd.DataFrame): DataFrame containing the updated golf data.
        output_file (str): Path to save the Parquet file.
    """
    write_file(output_file, df, "Save to parquet")
    logger.info(f"Data successfully saved to {output_file}")


def update_streaks_cache():
    """
    Update the streaks cache file with current streak calculations.

    This function:
    1. Loads all data (including incomplete TEGs)
    2. Calls build_streaks() to calculate streak data
    3. Saves result to streaks.parquet
    4. Clears streamlit cache

    Called whenever source data changes (data updates, deletions).
    """
    try:
        # Import build_streaks function
        from helpers.streak_analysis_processing import build_streaks

        # Load all data including incomplete TEGs for streak calculations
        all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

        if all_data.empty:
            logger.warning("No data available for streak calculation")
            return

        # Calculate streaks using the build_streaks function
        streaks_df = build_streaks(all_data)

        # Save to streaks parquet file
        write_file(STREAKS_PARQUET, streaks_df, "Update streaks cache")
        logger.info(f"Streaks cache updated successfully: {STREAKS_PARQUET}")

        # Clear streamlit cache to ensure fresh data on next load
        clear_all_caches()

    except Exception as e:
        logger.error(f"Error updating streaks cache: {e}")
        st.error(f"Failed to update streaks cache: {e}")


def update_bestball_cache():
    """
    Update the bestball/worstball cache file.

    This function:
    1. Loads all data (including incomplete TEGs)
    2. Calculates bestball scores
    3. Calculates worstball scores
    4. Combines them and saves to bestball.parquet
    """
    try:
        # Load all data including incomplete TEGs for up-to-date analysis
        all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

        if all_data.empty:
            logger.warning("No data available for bestball calculation")
            return

        # Import processing functions
        from helpers.bestball_processing import prepare_bestball_data, calculate_bestball_scores, calculate_worstball_scores

        # Prepare data
        prepared_data = prepare_bestball_data(all_data)

        # Calculate scores
        bestball_data = calculate_bestball_scores(prepared_data)
        worstball_data = calculate_worstball_scores(prepared_data)

        # Add a 'Format' column to distinguish them
        bestball_data['Format'] = 'Bestball'
        worstball_data['Format'] = 'Worstball'

        # Combine into a single DataFrame
        combined_df = pd.concat([bestball_data, worstball_data], ignore_index=True)

        # Save to parquet file
        write_file(BESTBALL_PARQUET, combined_df, "Update bestball/worstball cache")
        logger.info(f"Bestball/worstball cache updated successfully: {BESTBALL_PARQUET}")

    except Exception as e:
        logger.error(f"Error updating bestball cache: {e}")
        st.error(f"Failed to update bestball cache: {e}")

def update_commentary_caches():
    """
    Update the commentary cache files with current event and summary data.

    This function:
    1. Loads all data (including incomplete TEGs)
    2. Calls create_round_events() to generate event log
    3. Calls create_round_summary() to generate round summaries
    4. Calls create_tournament_summary() to generate tournament summaries
    5. Calls create_round_streaks_summary() to generate round streaks
    6. Calls create_tournament_streaks_summary() to generate tournament streaks
    7. Saves results to commentary parquet files
    8. Clears streamlit cache

    Called whenever source data changes (data updates, deletions).
    """
    try:
        logger.info("Updating commentary cache files")

        # Load all data including incomplete TEGs for commentary
        all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

        if all_data.empty:
            logger.warning("No data available for commentary generation")
            return

        # Load round info and streaks data
        round_info = read_file(ROUND_INFO_CSV)
        streaks_df = read_file(STREAKS_PARQUET)

        # Generate round events
        logger.info("Generating round events...")
        events_df = create_round_events(all_data_df=all_data)
        write_file(COMMENTARY_ROUND_EVENTS_PARQUET, events_df, "Update commentary round events cache")
        logger.info(f"Round events cache updated: {COMMENTARY_ROUND_EVENTS_PARQUET}")

        # Generate round summary
        logger.info("Generating round summary...")
        round_summary_df = create_round_summary(all_data_df=all_data, round_info_df=round_info)
        write_file(COMMENTARY_ROUND_SUMMARY_PARQUET, round_summary_df, "Update commentary round summary cache")
        logger.info(f"Round summary cache updated: {COMMENTARY_ROUND_SUMMARY_PARQUET}")

        # Generate tournament summary
        logger.info("Generating tournament summary...")
        tournament_summary_df = create_tournament_summary(all_data_df=all_data, round_info_df=round_info)
        write_file(COMMENTARY_TOURNAMENT_SUMMARY_PARQUET, tournament_summary_df, "Update commentary tournament summary cache")
        logger.info(f"Tournament summary cache updated: {COMMENTARY_TOURNAMENT_SUMMARY_PARQUET}")

        # Generate round streaks summary
        logger.info("Generating round streaks summary...")
        round_streaks_df = create_round_streaks_summary(all_data_df=all_data, streaks_df=streaks_df)
        write_file(COMMENTARY_ROUND_STREAKS_PARQUET, round_streaks_df, "Update commentary round streaks cache")
        logger.info(f"Round streaks cache updated: {COMMENTARY_ROUND_STREAKS_PARQUET}")

        # Generate tournament streaks summary
        logger.info("Generating tournament streaks summary...")
        tournament_streaks_df = create_tournament_streaks_summary(all_data_df=all_data, streaks_df=streaks_df)
        write_file(COMMENTARY_TOURNAMENT_STREAKS_PARQUET, tournament_streaks_df, "Update commentary tournament streaks cache")
        logger.info(f"Tournament streaks cache updated: {COMMENTARY_TOURNAMENT_STREAKS_PARQUET}")

        # Clear streamlit cache to ensure fresh data on next load
        clear_all_caches()

        logger.info("Commentary cache files updated successfully")

    except Exception as e:
        logger.error(f"Error updating commentary caches: {e}")
        st.error(f"Failed to update commentary caches: {e}")


def get_google_sheet(sheet_name: str, worksheet_name: str) -> pd.DataFrame:
    """
    Load data from a specified Google Sheet and worksheet using credentials from 
    Railway environment variables or Streamlit secrets.
    """
    logger.info(f"Fetching data from Google Sheet: {sheet_name}, Worksheet: {worksheet_name}")
    
    SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    try:
        # Try Railway environment variables first, fallback to st.secrets for local development
        if os.getenv('GOOGLE_TYPE'):
            # Railway environment variables
            service_account_info = {
                "type": os.getenv('GOOGLE_TYPE'),
                "project_id": os.getenv('GOOGLE_PROJECT_ID'),
                "private_key_id": os.getenv('GOOGLE_PRIVATE_KEY_ID'),
                "private_key": os.getenv('GOOGLE_PRIVATE_KEY').replace('\\n', '\n') if os.getenv('GOOGLE_PRIVATE_KEY') else None,
                "client_email": os.getenv('GOOGLE_CLIENT_EMAIL'),
                "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                "auth_uri": os.getenv('GOOGLE_AUTH_URI'),
                "token_uri": os.getenv('GOOGLE_TOKEN_URI'),
                "auth_provider_x509_cert_url": os.getenv('GOOGLE_AUTH_PROVIDER_X509_CERT_URL'),
                "client_x509_cert_url": os.getenv('GOOGLE_CLIENT_X509_CERT_URL'),
                "universe_domain": os.getenv('GOOGLE_UNIVERSE_DOMAIN'),
            }
            logger.info("Using Railway environment variables for Google credentials")
        else:
            # Fallback for local development
            service_account_info = st.secrets["google"]
            logger.info("Using Streamlit secrets for Google credentials")
        
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
        
        # Rest of your existing code...
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).worksheet(worksheet_name)
        
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        logger.info("Data fetched successfully from Google Sheets.")
        return df
    except Exception as e:
        logger.error(f"Error fetching data from Google Sheets: {e}")
        st.error(f"Error fetching data: {e}")
        raise


def reshape_round_data(df: pd.DataFrame, id_vars: List[str]) -> pd.DataFrame:
    """
    Reshape round data from wide to long format.

    Parameters:
        df (pd.DataFrame): Original wide-format DataFrame.
        id_vars (List[str]): List of identifier variables.

    Returns:
        pd.DataFrame: Reshaped long-format DataFrame.
    """
    logger.info("Reshaping round data to long format.")

    # Identify player columns by excluding id_vars
    player_columns = [col for col in df.columns if col not in id_vars]

    long_df = df.melt(id_vars=id_vars, value_vars=player_columns, var_name='Pl', value_name='Score')
    long_df['Score'] = pd.to_numeric(long_df['Score'], errors='coerce')
    reshaped_df = long_df.dropna(subset=['Score'])
    reshaped_df = reshaped_df[reshaped_df['Score'] != 0]
    logger.info("Round data reshaped successfully.")
    return reshaped_df


@st.cache_data
def load_and_prepare_handicap_data(file_path: str) -> pd.DataFrame:
    """
    Load and prepare handicap data from a CSV file.

    Parameters:
        file_path (str): Path to the handicap CSV file.

    Returns:
        pd.DataFrame: Melted and cleaned handicap DataFrame.
    """
    logger.info(f"Loading handicap data from {file_path}")
    try:
        hc_lookup = read_file(file_path)
    except Exception as e:
        logger.error(f"File not found: {file_path}")
        raise
    hc_long = hc_lookup.melt(id_vars='TEG', var_name='Pl', value_name='HC')
    hc_long = hc_long.dropna(subset=['HC'])
    hc_long = hc_long[hc_long['HC'] != 0]
    logger.info("Handicap data loaded and prepared.")
    return hc_long


def summarise_existing_rd_data(existing_rows: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize existing round data.

    Parameters:
        existing_rows (pd.DataFrame): DataFrame containing existing rows.

    Returns:
        pd.DataFrame: Pivoted summary DataFrame.
    """
    logger.info("Summarizing existing round data.")
    existing_summary_df = existing_rows.groupby(['TEGNum', 'Round', 'Pl'])['Sc'].sum().reset_index()
    existing_summary_pivot = existing_summary_df.pivot(index='Pl', columns=['Round', 'TEGNum'], values='Sc')
    summary = existing_summary_pivot.fillna('-').astype(str).replace(r'\.0$', '', regex=True)
    logger.info("Existing round data summarized.")
    return summary


def add_round_info(all_data: pd.DataFrame) -> pd.DataFrame:
    """
    Add round information to the DataFrame.

    Parameters:
        all_data (pd.DataFrame): The main DataFrame containing golf data.

    Returns:
        pd.DataFrame: DataFrame with round information added.
    """
    logger.info("Adding round information to the data.")

    # Read the round info CSV file
    round_info = read_file(ROUND_INFO_CSV)

    # Merge the round info with all_data based on TEGNum and Round
    merged_data = pd.merge(
        all_data,
        round_info[['TEGNum', 'Round', 'Date', 'Course']],
        on=['TEGNum', 'Round'],
        how='left'
    )

    return merged_data


def update_all_data(csv_file: str, parquet_file: str, csv_output_file: str) -> None:
    """
    Load data from a CSV file, apply cumulative scores and averages, and save it as both a Parquet file and a CSV file.

    Parameters:
        csv_file (str): Path to the input CSV file.
        parquet_file (str): Path to the output Parquet file.
        csv_output_file (str): Path to the output CSV file for review.
    """
    logger.info(f"Updating all data from {csv_file} to {parquet_file} and {csv_output_file}")

    # Load the CSV file
    try:
        df = read_file(csv_file)
        logger.debug("CSV data loaded.")
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_file}")
        raise

    # Add round info
    df = add_round_info(df)
    df['TEG-Round'] = df['TEG'] +'|R' + df['Round'].astype('str')
    logger.debug("Round info added.")

    # Apply cumulative score and average calculations
    df_transformed = add_cumulative_scores(df)
    logger.debug("Cumulative scores and averages applied.")

    # Add rankings and gaps to leader
    df_transformed = add_rankings_and_gaps(df_transformed)
    logger.debug("Rankings and gaps to leader added.")

    # Add 'Year' column and convert to pandas nullable integer type
    df_transformed['Year'] = pd.to_datetime(
        df_transformed['Date'], dayfirst=True, errors='coerce'
    ).dt.year.astype('Int64')

    # Save the transformed dataframe to a Parquet file
    save_to_parquet(df_transformed, parquet_file)

    # Save the transformed dataframe to a CSV file for manual review
    write_file(csv_output_file, df_transformed, "Update all-data CSV")
    logger.info(f"Transformed data saved to {csv_output_file}")

    st.cache_data.clear()
    st.success("✅ Cache cleared")


def create_round_summary(all_data_df=None, round_info_df=None):
    """
    Create a comprehensive summary table for each round (unique TEG + Round + Player combination).

    This function calculates and captures the following metrics for each round:
    - Basic round information (TEG, Round, Date, Course, Area, Player)
    - Round scores (Sc, Gross, and Stableford) for full round, front 9, and back 9
    - Cumulative tournament scores
    - Rankings (round-level and cumulative tournament)
    - Gap to leader (before and after round)
    - Lead tracking (holes in lead, leading at start/end, lead gained/lost counts)
    - Historical rankings (rank among player's rounds and all rounds to date)
    - Score type counts (eagles, birdies, pars, etc.)

    Parameters:
        all_data_df (pd.DataFrame, optional): DataFrame from all-data.parquet. If None, will load from file.
        round_info_df (pd.DataFrame, optional): DataFrame from round_info.csv. If None, will load from file.

    Returns:
        pd.DataFrame: Summary table with one row per player per round, containing all calculated metrics.
    """
    logger.info("Creating round summary table.")

    # ========================================
    # 1. LOAD DATA
    # ========================================
    if all_data_df is None:
        logger.info("Loading all-data.parquet")
        # Must use parquet file as it contains ranking and gap columns
        all_data_df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    if round_info_df is None:
        logger.info("Loading round_info.csv")
        round_info_df = read_file(ROUND_INFO_CSV)

    # Ensure data is sorted chronologically
    round_info_df = round_info_df.sort_values(['TEGNum', 'Round'])
    all_data_df = all_data_df.sort_values(['TEGNum', 'Round', 'Hole', 'Pl'])

    # ========================================
    # 2. CALCULATE ROUND-LEVEL SCORES
    # ========================================
    logger.info("Calculating round-level scores")

    # Filter for front 9 and back 9
    front_9 = all_data_df[all_data_df['Hole'] <= 9].copy()
    back_9 = all_data_df[all_data_df['Hole'] > 9].copy()

    # Aggregate scores by player and round
    round_scores = all_data_df.groupby(['TEGNum', 'Round', 'Pl', 'Player']).agg({
        'Sc': 'sum',
        'GrossVP': 'sum',
        'Stableford': 'sum'
    }).reset_index()
    round_scores.columns = ['TEGNum', 'Round', 'Pl', 'Player', 'Round_Score_Sc', 'Round_Score_Gross', 'Round_Score_Stableford']

    # Front 9 scores
    front_9_scores = front_9.groupby(['TEGNum', 'Round', 'Pl']).agg({
        'Sc': 'sum',
        'GrossVP': 'sum',
        'Stableford': 'sum'
    }).reset_index()
    front_9_scores.columns = ['TEGNum', 'Round', 'Pl', 'Front_9_Score_Sc', 'Front_9_Score_Gross', 'Front_9_Score_Stableford']

    # Back 9 scores
    back_9_scores = back_9.groupby(['TEGNum', 'Round', 'Pl']).agg({
        'Sc': 'sum',
        'GrossVP': 'sum',
        'Stableford': 'sum'
    }).reset_index()
    back_9_scores.columns = ['TEGNum', 'Round', 'Pl', 'Back_9_Score_Sc', 'Back_9_Score_Gross', 'Back_9_Score_Stableford']

    # Merge all score components
    summary = round_scores.merge(front_9_scores, on=['TEGNum', 'Round', 'Pl'], how='left')
    summary = summary.merge(back_9_scores, on=['TEGNum', 'Round', 'Pl'], how='left')

    # Calculate Front 9 vs Back 9 difference
    summary['Front_9_vs_Back_9_Sc'] = summary['Front_9_Score_Sc'] - summary['Back_9_Score_Sc']
    summary['Front_9_vs_Back_9_Gross'] = summary['Front_9_Score_Gross'] - summary['Back_9_Score_Gross']
    summary['Front_9_vs_Back_9_Stableford'] = summary['Front_9_Score_Stableford'] - summary['Back_9_Score_Stableford']

    # ========================================
    # 3. GET CUMULATIVE SCORES (from hole 18 of each round)
    # ========================================
    logger.info("Extracting cumulative tournament scores")

    # Get the data at hole 18 of each round (end of round snapshot)
    end_of_round = all_data_df[all_data_df['Hole'] == 18].copy()

    cumulative_scores = end_of_round[['TEGNum', 'Round', 'Pl', 'GrossVP Cum TEG', 'Stableford Cum TEG',
                                       'Rank_GrossVP_TEG', 'Rank_Stableford_TEG',
                                       'Gap_GrossVP_TEG', 'Gap_Stableford_TEG']].copy()
    cumulative_scores.columns = ['TEGNum', 'Round', 'Pl',
                                   'Cumulative_Tournament_Score_Gross', 'Cumulative_Tournament_Score_Stableford',
                                   'Cumulative_Tournament_Rank_Gross', 'Cumulative_Tournament_Rank_Stableford',
                                   'Gap_To_Leader_After_Round_Gross', 'Gap_To_Leader_After_Round_Stableford']

    summary = summary.merge(cumulative_scores, on=['TEGNum', 'Round', 'Pl'], how='left')

    # ========================================
    # 4. CALCULATE RANKINGS
    # ========================================
    logger.info("Calculating round rankings")

    # Round-level rankings (based on this round's score only)
    summary['Player_Round_Rank_Gross'] = summary.groupby(['TEGNum', 'Round'])['Round_Score_Gross'].rank(method='min', ascending=True)
    summary['Player_Round_Rank_Stableford'] = summary.groupby(['TEGNum', 'Round'])['Round_Score_Stableford'].rank(method='min', ascending=False)

    # Cumulative tournament rank BEFORE round (from previous round's hole 18)
    # Shift rankings forward by one round within each TEG and player
    summary = summary.sort_values(['TEGNum', 'Pl', 'Round'])
    summary['Cumulative_Tournament_Rank_Before_Round_Gross'] = summary.groupby(['TEGNum', 'Pl'])['Cumulative_Tournament_Rank_Gross'].shift(1)
    summary['Cumulative_Tournament_Rank_Before_Round_Stableford'] = summary.groupby(['TEGNum', 'Pl'])['Cumulative_Tournament_Rank_Stableford'].shift(1)

    # Gap to leader BEFORE round (from previous round's hole 18)
    summary['Gap_To_Leader_Before_Round_Gross'] = summary.groupby(['TEGNum', 'Pl'])['Gap_To_Leader_After_Round_Gross'].shift(1)
    summary['Gap_To_Leader_Before_Round_Stableford'] = summary.groupby(['TEGNum', 'Pl'])['Gap_To_Leader_After_Round_Stableford'].shift(1)

    # ========================================
    # 5. CALCULATE LEAD TRACKING
    # ========================================
    logger.info("Calculating lead tracking metrics")

    # Count holes where player was in lead (rank = 1) during the round
    holes_in_lead = all_data_df.groupby(['TEGNum', 'Round', 'Pl'], as_index=False).apply(
        lambda x: pd.Series({
            'Holes_In_Lead_Gross': (x['Rank_GrossVP_TEG'] == 1).sum(),
            'Holes_In_Lead_Stableford': (x['Rank_Stableford_TEG'] == 1).sum()
        }), include_groups=False
    ).reset_index()

    summary = summary.merge(holes_in_lead, on=['TEGNum', 'Round', 'Pl'], how='left')

    # Leading at start/end of round flags
    summary['Leading_At_Start_Of_Round_Gross'] = (summary['Cumulative_Tournament_Rank_Before_Round_Gross'] == 1).astype(int)
    summary['Leading_At_Start_Of_Round_Stableford'] = (summary['Cumulative_Tournament_Rank_Before_Round_Stableford'] == 1).astype(int)
    summary['Leading_At_End_Of_Round_Gross'] = (summary['Cumulative_Tournament_Rank_Gross'] == 1).astype(int)
    summary['Leading_At_End_Of_Round_Stableford'] = (summary['Cumulative_Tournament_Rank_Stableford'] == 1).astype(int)

    # ========================================
    # 6. CALCULATE HISTORICAL RANKINGS (CHRONOLOGICAL)
    # ========================================
    logger.info("Calculating historical rankings")

    # Merge with round_info to get dates for chronological ordering
    summary = summary.merge(round_info_df[['TEGNum', 'Round', 'Date']], on=['TEGNum', 'Round'], how='left')

    # Convert date to datetime for proper sorting
    summary['Date'] = pd.to_datetime(summary['Date'], format='%d/%m/%Y', errors='coerce')
    summary = summary.sort_values(['Date', 'TEGNum', 'Round', 'Pl'])

    # For each round, rank it among all player's rounds TO DATE (excluding future rounds)
    summary['Round_Rank_In_Player_History_Gross'] = None
    summary['Round_Rank_In_Player_History_Stableford'] = None
    summary['Total_Player_Rounds_To_Date'] = None

    summary['Round_Rank_In_All_History_Gross'] = None
    summary['Round_Rank_In_All_History_Stableford'] = None
    summary['Total_Rounds_To_Date'] = None

    # Calculate historical rankings row by row
    for idx, row in summary.iterrows():
        current_date = row['Date']
        current_player = row['Pl']
        current_gross = row['Round_Score_Gross']
        current_stableford = row['Round_Score_Stableford']

        # Filter for rounds up to current date
        historical_data = summary[summary['Date'] <= current_date].copy()

        # Player-specific historical data
        player_historical = historical_data[historical_data['Pl'] == current_player].copy()

        # Rank this round among player's rounds to date
        player_historical['rank_gross'] = player_historical['Round_Score_Gross'].rank(method='min', ascending=True)
        player_historical['rank_stableford'] = player_historical['Round_Score_Stableford'].rank(method='min', ascending=False)

        player_total_rounds = len(player_historical)
        player_rank_gross = player_historical[player_historical.index == idx]['rank_gross'].values[0] if idx in player_historical.index else None
        player_rank_stableford = player_historical[player_historical.index == idx]['rank_stableford'].values[0] if idx in player_historical.index else None

        summary.at[idx, 'Round_Rank_In_Player_History_Gross'] = f"{int(player_rank_gross)} of {player_total_rounds}" if player_rank_gross else None
        summary.at[idx, 'Round_Rank_In_Player_History_Stableford'] = f"{int(player_rank_stableford)} of {player_total_rounds}" if player_rank_stableford else None
        summary.at[idx, 'Total_Player_Rounds_To_Date'] = player_total_rounds

        # All players historical data
        historical_data['rank_gross'] = historical_data['Round_Score_Gross'].rank(method='min', ascending=True)
        historical_data['rank_stableford'] = historical_data['Round_Score_Stableford'].rank(method='min', ascending=False)

        total_rounds = len(historical_data)
        all_rank_gross = historical_data[historical_data.index == idx]['rank_gross'].values[0] if idx in historical_data.index else None
        all_rank_stableford = historical_data[historical_data.index == idx]['rank_stableford'].values[0] if idx in historical_data.index else None

        summary.at[idx, 'Round_Rank_In_All_History_Gross'] = f"{int(all_rank_gross)} of {total_rounds}" if all_rank_gross else None
        summary.at[idx, 'Round_Rank_In_All_History_Stableford'] = f"{int(all_rank_stableford)} of {total_rounds}" if all_rank_stableford else None
        summary.at[idx, 'Total_Rounds_To_Date'] = total_rounds

    # ========================================
    # 7. CALCULATE SCORE TYPE COUNTS
    # ========================================
    logger.info("Calculating score type counts")

    # Count various score types by round
    score_counts = all_data_df.groupby(['TEGNum', 'Round', 'Pl']).agg({
        'GrossVP': [
            ('Eagles_Count', lambda x: (x == -2).sum()),
            ('Birdies_Count', lambda x: (x == -1).sum()),
            ('Pars_Or_Better_Count', lambda x: (x <= 0).sum()),
            ('Triple_Bogeys_Or_Worse_Count', lambda x: (x >= 3).sum())
        ],
        'Stableford': [
            ('Zero_Stableford_Points_Count', lambda x: (x == 0).sum()),
            ('Four_Plus_Stableford_Points_Count', lambda x: (x >= 4).sum()),
            ('Five_Plus_Stableford_Points_Count', lambda x: (x >= 5).sum())
        ]
    }).reset_index()

    # Flatten multi-level columns
    score_counts.columns = ['TEGNum', 'Round', 'Pl', 'Eagles_Count', 'Birdies_Count',
                            'Pars_Or_Better_Count', 'Triple_Bogeys_Or_Worse_Count',
                            'Zero_Stableford_Points_Count', 'Four_Plus_Stableford_Points_Count',
                            'Five_Plus_Stableford_Points_Count']

    summary = summary.merge(score_counts, on=['TEGNum', 'Round', 'Pl'], how='left')

    # ========================================
    # 8. CALCULATE LEAD GAINED/LOST COUNTS FROM EVENTS
    # ========================================
    logger.info("Calculating lead gained/lost counts from events")

    # Generate events data
    events_df = create_round_events(all_data_df=all_data_df)

    # Count how many times each player took/lost lead in each round
    # Filter for lead change events only (exclude hole 1 where taking lead is just starting)
    lead_changes = events_df[events_df['Hole'] > 1].copy()

    # Count lead gains and losses by round for Gross
    lead_gained_gross = lead_changes[lead_changes['Event'] == 'Took Lead (Gross)'].groupby(
        ['TEGNum', 'Round', 'Pl']
    ).size().reset_index(name='Lead_Gained_Count_Gross')

    lead_lost_gross = lead_changes[lead_changes['Event'] == 'Lost Lead (Gross)'].groupby(
        ['TEGNum', 'Round', 'Pl']
    ).size().reset_index(name='Lead_Lost_Count_Gross')

    # Count lead gains and losses by round for Stableford
    lead_gained_stableford = lead_changes[lead_changes['Event'] == 'Took Lead (Stableford)'].groupby(
        ['TEGNum', 'Round', 'Pl']
    ).size().reset_index(name='Lead_Gained_Count_Stableford')

    lead_lost_stableford = lead_changes[lead_changes['Event'] == 'Lost Lead (Stableford)'].groupby(
        ['TEGNum', 'Round', 'Pl']
    ).size().reset_index(name='Lead_Lost_Count_Stableford')

    # Merge lead change counts into summary
    summary = summary.merge(lead_gained_gross, on=['TEGNum', 'Round', 'Pl'], how='left')
    summary = summary.merge(lead_lost_gross, on=['TEGNum', 'Round', 'Pl'], how='left')
    summary = summary.merge(lead_gained_stableford, on=['TEGNum', 'Round', 'Pl'], how='left')
    summary = summary.merge(lead_lost_stableford, on=['TEGNum', 'Round', 'Pl'], how='left')

    # Fill NaN with 0 (no lead changes)
    summary['Lead_Gained_Count_Gross'] = summary['Lead_Gained_Count_Gross'].fillna(0).astype(int)
    summary['Lead_Lost_Count_Gross'] = summary['Lead_Lost_Count_Gross'].fillna(0).astype(int)
    summary['Lead_Gained_Count_Stableford'] = summary['Lead_Gained_Count_Stableford'].fillna(0).astype(int)
    summary['Lead_Lost_Count_Stableford'] = summary['Lead_Lost_Count_Stableford'].fillna(0).astype(int)

    # ========================================
    # 9. ADD ROUND METADATA
    # ========================================
    logger.info("Adding round metadata from round_info")

    # Merge with round_info for Course, Area, and Year (Date already merged)
    summary = summary.merge(round_info_df[['TEGNum', 'Round', 'Course', 'Area', 'TEG', 'Year']],
                           on=['TEGNum', 'Round'], how='left')

    # ========================================
    # 9. REORDER COLUMNS FOR CLARITY
    # ========================================
    logger.info("Reordering columns")

    # Define column order
    column_order = [
        'TEG', 'TEGNum', 'Round', 'Date', 'Course', 'Area', 'Year', 'Player',
        # Round Scores - Actual Score
        'Round_Score_Sc', 'Front_9_Score_Sc', 'Back_9_Score_Sc', 'Front_9_vs_Back_9_Sc',
        # Round Scores - Gross
        'Round_Score_Gross', 'Front_9_Score_Gross', 'Back_9_Score_Gross', 'Front_9_vs_Back_9_Gross',
        # Round Scores - Stableford
        'Round_Score_Stableford', 'Front_9_Score_Stableford', 'Back_9_Score_Stableford', 'Front_9_vs_Back_9_Stableford',
        # Cumulative Scores
        'Cumulative_Tournament_Score_Gross', 'Cumulative_Tournament_Score_Stableford',
        # Rankings - Gross
        'Player_Round_Rank_Gross', 'Cumulative_Tournament_Rank_Before_Round_Gross', 'Cumulative_Tournament_Rank_Gross',
        # Rankings - Stableford
        'Player_Round_Rank_Stableford', 'Cumulative_Tournament_Rank_Before_Round_Stableford', 'Cumulative_Tournament_Rank_Stableford',
        # Gaps - Gross
        'Gap_To_Leader_Before_Round_Gross', 'Gap_To_Leader_After_Round_Gross',
        # Gaps - Stableford
        'Gap_To_Leader_Before_Round_Stableford', 'Gap_To_Leader_After_Round_Stableford',
        # Lead Tracking - Gross
        'Holes_In_Lead_Gross', 'Leading_At_Start_Of_Round_Gross', 'Leading_At_End_Of_Round_Gross',
        'Lead_Gained_Count_Gross', 'Lead_Lost_Count_Gross',
        # Lead Tracking - Stableford
        'Holes_In_Lead_Stableford', 'Leading_At_Start_Of_Round_Stableford', 'Leading_At_End_Of_Round_Stableford',
        'Lead_Gained_Count_Stableford', 'Lead_Lost_Count_Stableford',
        # Historical Rankings
        'Round_Rank_In_Player_History_Gross', 'Round_Rank_In_Player_History_Stableford',
        'Round_Rank_In_All_History_Gross', 'Round_Rank_In_All_History_Stableford',
        # Score Type Counts
        'Eagles_Count', 'Birdies_Count', 'Pars_Or_Better_Count', 'Triple_Bogeys_Or_Worse_Count',
        'Zero_Stableford_Points_Count', 'Four_Plus_Stableford_Points_Count', 'Five_Plus_Stableford_Points_Count',
        # Support fields
        'Pl', 'Total_Player_Rounds_To_Date', 'Total_Rounds_To_Date'
    ]

    # Reorder columns (keep any extra columns at the end)
    existing_columns = [col for col in column_order if col in summary.columns]
    other_columns = [col for col in summary.columns if col not in column_order]
    summary = summary[existing_columns + other_columns]

    logger.info(f"Round summary table created with {len(summary)} rows and {len(summary.columns)} columns.")

    return summary


def create_round_events(all_data_df=None):
    """
    Create a comprehensive event log capturing key moments during each hole of every round.

    This function tracks two categories of events:

    1. **Position Events** - Changes in tournament standings:
       - Took Lead (Gross/Stableford): Player moved to 1st place
       - Lost Lead (Gross/Stableford): Player dropped from 1st place
       - Hit Bottom (Spoon): Player moved to last place (Stableford-based wooden spoon)
       - Left Bottom (Spoon): Player moved up from last place

    2. **Hole Outcome Events** - Notable scoring achievements:
       - Hole in One, Eagle, Birdie
       - Triple Bogey or Worse, Quintuple Bogey or Worse
       - Zero Points, 4+ Points, 5+ Points (Stableford)

    Parameters:
        all_data_df (pd.DataFrame, optional): DataFrame from all-data.parquet with hole-by-hole rankings.
                                               If None, will load from file.

    Returns:
        pd.DataFrame: Tidy event log with one row per event occurrence.
                     Columns include:
                     - TEG, TEGNum, Round, Hole, Player, Pl
                     - Par, Sc, GrossVP, Stableford
                     - Final_Hole_Flag (boolean)
                     - Event (human-readable description)
                     - Metric (relevant score for the event)
                     - Rank_Gross_Before, Rank_Gross_After
                     - Rank_Stableford_Before, Rank_Stableford_After

    Example:
        >>> events_df = create_round_events()
        >>> events_df[events_df['Event'] == 'Took Lead (Stableford)'].head()
    """
    logger.info("Creating round events log.")

    # ========================================
    # 1. LOAD AND VALIDATE DATA
    # ========================================
    REQUIRED_COLS = [
        'TEGNum', 'TEG', 'Round', 'Hole', 'Pl', 'Player',
        'Sc', 'PAR', 'GrossVP', 'Stableford',
        'Rank_Stableford_TEG', 'Rank_GrossVP_TEG'
    ]

    if all_data_df is None:
        logger.info("Loading all-data.parquet")
        all_data_df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    # Validate required columns
    missing = [c for c in REQUIRED_COLS if c not in all_data_df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = all_data_df.copy()

    # ========================================
    # 2. CALCULATE DERIVED FIELDS
    # ========================================
    logger.info("Calculating derived fields")

    # Count players per round (needed for bottom detection)
    n_players = df.groupby(['TEGNum', 'Round'])['Pl'].nunique().rename('NPlayers')
    df = df.merge(n_players, on=['TEGNum', 'Round'], how='left')

    # Create TEG-wide hole index (bridges rounds: R1H18 → R2H1, etc.)
    # Assumes 18 holes per round
    df['TEG_Hole'] = (df['Round'] - 1) * 18 + df['Hole']

    # Derive Wooden Spoon rank (inverse of Stableford rank within each hole)
    # Last place in Stableford = 1st place in Spoon competition
    df = df.sort_values(['TEGNum', 'Round', 'Hole'])
    df['MaxRank_ThisHole'] = df.groupby(['TEGNum', 'Round', 'Hole'])['Rank_Stableford_TEG'].transform('max')
    df['Rank_Spoon_TEG'] = df['MaxRank_ThisHole'] + 1 - df['Rank_Stableford_TEG']

    # ========================================
    # 3. CALCULATE RANK "BEFORE" FIELDS
    # ========================================
    logger.info("Calculating rank before/after fields")

    # Sort by TEG-wide hole order for proper chronological shifting
    df = df.sort_values(['TEGNum', 'Pl', 'TEG_Hole'])

    # Shift rankings by 1 hole to get "before" state (per player, per TEG)
    df['Rank_Gross_After'] = df['Rank_GrossVP_TEG']
    df['Rank_Gross_Before'] = df.groupby(['TEGNum', 'Pl'])['Rank_GrossVP_TEG'].shift(1)

    df['Rank_Stableford_After'] = df['Rank_Stableford_TEG']
    df['Rank_Stableford_Before'] = df.groupby(['TEGNum', 'Pl'])['Rank_Stableford_TEG'].shift(1)

    df['Rank_Spoon_After'] = df['Rank_Spoon_TEG']
    df['Rank_Spoon_Before'] = df.groupby(['TEGNum', 'Pl'])['Rank_Spoon_TEG'].shift(1)

    # ========================================
    # 4. DETECT POSITION EVENTS (VECTORIZED)
    # ========================================
    logger.info("Detecting position change events")

    position_events_frames = []

    # Define position events for each competition
    position_event_specs = {
        # Gross competition (Green Jacket)
        'Took Lead (Gross)': (
            (df['Rank_Gross_After'] == 1) &
            ((df['Rank_Gross_Before'] > 1) | df['Rank_Gross_Before'].isna())
        ),
        'Lost Lead (Gross)': (
            (df['Rank_Gross_Before'] == 1) &
            (df['Rank_Gross_After'] > 1)
        ),

        # Stableford competition (Trophy)
        'Took Lead (Stableford)': (
            (df['Rank_Stableford_After'] == 1) &
            ((df['Rank_Stableford_Before'] > 1) | df['Rank_Stableford_Before'].isna())
        ),
        'Lost Lead (Stableford)': (
            (df['Rank_Stableford_Before'] == 1) &
            (df['Rank_Stableford_After'] > 1)
        ),

        # Wooden Spoon competition (Stableford-based, last place)
        'Hit Bottom (Spoon)': (
            (df['Rank_Stableford_After'] == df['NPlayers']) &
            ((df['Rank_Stableford_Before'] < df['NPlayers']) | df['Rank_Stableford_Before'].isna())
        ),
        'Left Bottom (Spoon)': (
            (df['Rank_Stableford_Before'] == df['NPlayers']) &
            (df['Rank_Stableford_After'] < df['NPlayers'])
        ),
    }

    # Create wide DataFrame with all position event flags
    position_flags = pd.DataFrame(position_event_specs)

    # Base columns to include in output
    base_cols = ['TEGNum', 'TEG', 'Round', 'Hole', 'Pl', 'Player', 'Sc', 'PAR', 'GrossVP', 'Stableford',
                 'Rank_Gross_Before', 'Rank_Gross_After', 'Rank_Stableford_Before', 'Rank_Stableford_After', 'NPlayers']

    # Reshape to tidy format: one row per event occurrence
    position_events = (
        pd.concat([df[base_cols].reset_index(drop=True), position_flags.reset_index(drop=True)], axis=1)
        .melt(id_vars=base_cols, var_name='Event', value_name='Flag')
        .query('Flag == True')
        .drop(columns='Flag')
    )

    # ========================================
    # 5. DETECT HOLE OUTCOME EVENTS (VECTORIZED)
    # ========================================
    logger.info("Detecting hole outcome events")

    # Sort for consistent ordering with position events
    df_outcomes = df.sort_values(['TEGNum', 'Round', 'Pl', 'TEG_Hole'])

    # Define hole outcome event criteria
    outcome_event_specs = {
        'Hole in One': df_outcomes['Sc'].eq(1),
        'Eagle': df_outcomes['GrossVP'].eq(-2),
        'Birdie': df_outcomes['GrossVP'].eq(-1),
        'Triple Bogey or Worse': df_outcomes['GrossVP'].ge(3),
        'Quintuple Bogey or Worse': df_outcomes['GrossVP'].ge(5),
        'Zero Points': df_outcomes['Stableford'].eq(0),
        '4+ Points': df_outcomes['Stableford'].ge(4),
        '5+ Points': df_outcomes['Stableford'].ge(5),
    }

    # Create wide DataFrame with all outcome event flags
    outcome_flags = pd.DataFrame(outcome_event_specs)

    # Reshape to tidy format
    outcome_events = (
        pd.concat([
            df_outcomes[['TEGNum', 'TEG', 'Round', 'Hole', 'Pl', 'Player', 'Sc', 'PAR', 'GrossVP', 'Stableford',
                        'Rank_Gross_Before', 'Rank_Gross_After', 'Rank_Stableford_Before', 'Rank_Stableford_After',
                        'NPlayers']].reset_index(drop=True),
            outcome_flags.reset_index(drop=True)
        ], axis=1)
        .melt(
            id_vars=['TEGNum', 'TEG', 'Round', 'Hole', 'Pl', 'Player', 'Sc', 'PAR', 'GrossVP', 'Stableford',
                    'Rank_Gross_Before', 'Rank_Gross_After', 'Rank_Stableford_Before', 'Rank_Stableford_After', 'NPlayers'],
            var_name='Event', value_name='Flag'
        )
        .query('Flag == True')
        .drop(columns='Flag')
    )

    # ========================================
    # 6. ADD METRIC COLUMN
    # ========================================
    logger.info("Adding metric column")

    # Map each event type to its relevant metric
    metric_map = {
        'Hole in One': 'Sc',
        'Eagle': 'GrossVP',
        'Birdie': 'GrossVP',
        'Triple Bogey or Worse': 'GrossVP',
        'Quintuple Bogey or Worse': 'GrossVP',
        'Zero Points': 'Stableford',
        '4+ Points': 'Stableford',
        '5+ Points': 'Stableford',
        # Position events don't have a specific metric
        'Took Lead (Gross)': None,
        'Lost Lead (Gross)': None,
        'Took Lead (Stableford)': None,
        'Lost Lead (Stableford)': None,
        'Hit Bottom (Spoon)': None,
        'Left Bottom (Spoon)': None,
    }

    # Combine position and outcome events
    all_events = pd.concat([position_events, outcome_events], ignore_index=True)

    # Add Metric column based on event type
    all_events['Metric'] = all_events.apply(
        lambda row: row[metric_map[row['Event']]] if metric_map.get(row['Event']) else pd.NA,
        axis=1
    )

    # ========================================
    # 7. ADD FINAL HOLE FLAG
    # ========================================
    logger.info("Adding final hole flag")

    all_events['Final_Hole_Flag'] = (all_events['Hole'] == 18)

    # ========================================
    # 8. FORMAT AND RETURN
    # ========================================
    logger.info("Formatting output")

    # Define final column order
    output_cols = [
        'TEG', 'TEGNum', 'Round', 'Hole', 'Player', 'Pl',
        'Par', 'Sc', 'GrossVP', 'Stableford',
        'Final_Hole_Flag', 'Event', 'Metric',
        'Rank_Gross_Before', 'Rank_Gross_After',
        'Rank_Stableford_Before', 'Rank_Stableford_After'
    ]

    # Rename PAR to Par for consistency
    all_events = all_events.rename(columns={'PAR': 'Par'})

    # Select and reorder columns
    events_output = all_events[output_cols].copy()

    # Sort by TEG, Round, Hole, Event, Player for logical ordering
    events_output = events_output.sort_values(
        ['TEGNum', 'Round', 'Hole', 'Event', 'Pl']
    ).reset_index(drop=True)

    logger.info(f"Round events log created with {len(events_output)} event occurrences.")

    return events_output


def create_tournament_summary(all_data_df=None, round_info_df=None):
    """
    Create a comprehensive summary table for each tournament (unique TEG + Player combination).

    This function aggregates round-level data to provide tournament-wide metrics including:
    - Final scores and rankings
    - Performance consistency metrics
    - Lead tracking across all rounds
    - Scoring achievement counts
    - Historical context

    Args:
        all_data_df (pd.DataFrame, optional): DataFrame with hole-by-hole data including rankings.
            If None, loads from all-data.parquet.
        round_info_df (pd.DataFrame, optional): DataFrame with round metadata.
            If None, loads from round_info.csv.

    Returns:
        pd.DataFrame: Summary table with one row per player per TEG, containing all calculated metrics.
    """

    logger.info("Creating tournament summary")

    # ========================================
    # 1. LOAD DATA
    # ========================================
    if all_data_df is None:
        all_data_df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    if round_info_df is None:
        round_info_df = read_file(ROUND_INFO_CSV)

    # Get round summary data for aggregation
    round_summary_df = create_round_summary(all_data_df=all_data_df, round_info_df=round_info_df)

    # ========================================
    # 2. BASIC INFO
    # ========================================
    logger.info("Calculating basic tournament info")

    # Get unique TEG info per player
    basic_info = round_summary_df.groupby(['TEGNum', 'Pl']).agg({
        'Player': 'first',
        'TEG': 'first',
        'Year': 'first'
    }).reset_index()

    # ========================================
    # 3. TOURNAMENT SCORES & RANKINGS
    # ========================================
    logger.info("Calculating tournament scores and rankings")

    # Sum scores across all rounds
    tournament_scores = round_summary_df.groupby(['TEGNum', 'Pl']).agg({
        'Round_Score_Sc': 'sum',
        'Round_Score_Gross': 'sum',
        'Round_Score_Stableford': 'sum'
    }).reset_index()

    tournament_scores.rename(columns={
        'Round_Score_Sc': 'Tournament_Score_Sc',
        'Round_Score_Gross': 'Tournament_Score_Gross',
        'Round_Score_Stableford': 'Tournament_Score_Stableford'
    }, inplace=True)

    # Calculate final rankings within each TEG
    tournament_scores['Final_Rank_Gross'] = tournament_scores.groupby('TEGNum')['Tournament_Score_Gross'].rank(method='min').astype(int)
    tournament_scores['Final_Rank_Stableford'] = tournament_scores.groupby('TEGNum')['Tournament_Score_Stableford'].rank(method='min', ascending=False).astype(int)

    # Calculate gaps to winner
    tournament_scores['Winner_Score_Gross'] = tournament_scores.groupby('TEGNum')['Tournament_Score_Gross'].transform('min')
    tournament_scores['Winner_Score_Stableford'] = tournament_scores.groupby('TEGNum')['Tournament_Score_Stableford'].transform('max')
    tournament_scores['Final_Gap_Gross'] = tournament_scores['Tournament_Score_Gross'] - tournament_scores['Winner_Score_Gross']
    tournament_scores['Final_Gap_Stableford'] = tournament_scores['Winner_Score_Stableford'] - tournament_scores['Tournament_Score_Stableford']

    # Tournament outcome flags
    tournament_scores['Won_Gross'] = tournament_scores['Final_Rank_Gross'] == 1
    tournament_scores['Won_Stableford'] = tournament_scores['Final_Rank_Stableford'] == 1

    # Wooden Spoon: last place in Stableford
    tournament_scores['Max_Rank_Stableford'] = tournament_scores.groupby('TEGNum')['Final_Rank_Stableford'].transform('max')
    tournament_scores['Wooden_Spoon'] = tournament_scores['Final_Rank_Stableford'] == tournament_scores['Max_Rank_Stableford']

    # Margin of victory/defeat (positive if won, negative if lost)
    tournament_scores['Margin_Gross'] = -tournament_scores['Final_Gap_Gross']  # Invert so winner has positive margin
    tournament_scores['Margin_Stableford'] = tournament_scores['Final_Gap_Stableford']  # Already correct direction

    # Drop intermediate columns
    tournament_scores.drop(columns=['Winner_Score_Gross', 'Winner_Score_Stableford', 'Max_Rank_Stableford'], inplace=True)

    # ========================================
    # 4. PERFORMANCE CONSISTENCY
    # ========================================
    logger.info("Calculating performance consistency metrics")

    # Best/worst rounds
    consistency = round_summary_df.groupby(['TEGNum', 'Pl']).agg({
        'Round_Score_Gross': ['min', 'max'],
        'Round_Score_Stableford': ['min', 'max']
    }).reset_index()

    consistency.columns = ['TEGNum', 'Pl',
                          'Best_Round_Gross', 'Worst_Round_Gross',
                          'Worst_Round_Stableford', 'Best_Round_Stableford']

    # Range (best - worst)
    consistency['Range_Round_Gross'] = consistency['Worst_Round_Gross'] - consistency['Best_Round_Gross']
    consistency['Range_Round_Stableford'] = consistency['Best_Round_Stableford'] - consistency['Worst_Round_Stableford']

    # Calculate standard deviation by round and by hole across tournament
    round_std = round_summary_df.groupby(['TEGNum', 'Pl']).agg({
        'Round_Score_Gross': 'std',
        'Round_Score_Stableford': 'std'
    }).reset_index()

    round_std.rename(columns={
        'Round_Score_Gross': 'StdDev_Round_Gross',
        'Round_Score_Stableford': 'StdDev_Round_Stableford'
    }, inplace=True)

    hole_std = all_data_df.groupby(['TEGNum', 'Pl']).agg({
        'GrossVP': 'std',
        'Stableford': 'std'
    }).reset_index()

    hole_std.rename(columns={
        'GrossVP': 'StdDev_Hole_Gross',
        'Stableford': 'StdDev_Hole_Stableford'
    }, inplace=True)

    consistency = consistency.merge(round_std, on=['TEGNum', 'Pl'], how='left')
    consistency = consistency.merge(hole_std, on=['TEGNum', 'Pl'], how='left')

    # ========================================
    # 5. LEAD TRACKING ACROSS TOURNAMENT
    # ========================================
    logger.info("Calculating lead tracking metrics")

    # Total holes in lead
    lead_tracking = round_summary_df.groupby(['TEGNum', 'Pl']).agg({
        'Holes_In_Lead_Gross': 'sum',
        'Holes_In_Lead_Stableford': 'sum',
        'Leading_At_End_Of_Round_Gross': 'sum',
        'Leading_At_End_Of_Round_Stableford': 'sum',
        'Lead_Gained_Count_Gross': 'sum',
        'Lead_Lost_Count_Gross': 'sum',
        'Lead_Gained_Count_Stableford': 'sum',
        'Lead_Lost_Count_Stableford': 'sum'
    }).reset_index()

    lead_tracking.rename(columns={
        'Holes_In_Lead_Gross': 'Total_Holes_In_Lead_Gross',
        'Holes_In_Lead_Stableford': 'Total_Holes_In_Lead_Stableford',
        'Leading_At_End_Of_Round_Gross': 'Rounds_Leading_After_Gross',
        'Leading_At_End_Of_Round_Stableford': 'Rounds_Leading_After_Stableford',
        'Lead_Gained_Count_Gross': 'Total_Lead_Gained_Gross',
        'Lead_Lost_Count_Gross': 'Total_Lead_Lost_Gross',
        'Lead_Gained_Count_Stableford': 'Total_Lead_Gained_Stableford',
        'Lead_Lost_Count_Stableford': 'Total_Lead_Lost_Stableford'
    }, inplace=True)

    # ========================================
    # 6. SCORING ACHIEVEMENTS
    # ========================================
    logger.info("Calculating scoring achievements")

    # Count hole outcomes
    scoring = all_data_df.groupby(['TEGNum', 'Pl']).apply(lambda x: pd.Series({
        'Total_Eagles': (x['GrossVP'] == -2).sum(),
        'Total_Birdies': (x['GrossVP'] == -1).sum(),
        'Total_Pars': (x['GrossVP'] == 0).sum(),
        'Total_Bogeys': (x['GrossVP'] == 1).sum(),
        'Total_Double_Bogeys': (x['GrossVP'] == 2).sum(),
        'Total_Worse_Than_Double': (x['GrossVP'] > 2).sum(),
        'Holes_In_One': (x['Sc'] == 1).sum(),
        'Total_Stableford_5s': (x['Stableford'] >= 5).sum(),
        'Total_Stableford_0s': (x['Stableford'] == 0).sum()
    }), include_groups=False).reset_index()

    # ========================================
    # 7. HISTORICAL CONTEXT
    # ========================================
    logger.info("Calculating historical rankings")

    # For historical rankings, we need to rank this TEG against all previous TEGs for the player
    # First get the earliest date for each TEG
    teg_dates = round_info_df.groupby('TEGNum')['Date'].min().reset_index()
    teg_dates.columns = ['TEGNum', 'TEG_Date']

    # Merge dates into tournament scores
    tournament_with_dates = tournament_scores.merge(teg_dates, on='TEGNum', how='left')

    # Calculate historical rankings
    historical_rankings = []

    for _, row in tournament_with_dates.iterrows():
        player = row['Pl']
        teg_num = row['TEGNum']
        teg_date = row['TEG_Date']
        gross_score = row['Tournament_Score_Gross']
        stableford_score = row['Tournament_Score_Stableford']

        # Get all TEGs for this player up to and including this date
        player_history = tournament_with_dates[
            (tournament_with_dates['Pl'] == player) &
            (tournament_with_dates['TEG_Date'] <= teg_date)
        ].copy()

        # Rank among player's TEGs
        rank_player_gross = (player_history['Tournament_Score_Gross'] < gross_score).sum() + 1
        rank_player_stableford = (player_history['Tournament_Score_Stableford'] > stableford_score).sum() + 1

        # Get all TEGs up to this date
        all_history = tournament_with_dates[tournament_with_dates['TEG_Date'] <= teg_date].copy()

        # Rank among all TEGs to date
        rank_all_gross = (all_history['Tournament_Score_Gross'] < gross_score).sum() + 1
        rank_all_stableford = (all_history['Tournament_Score_Stableford'] > stableford_score).sum() + 1

        historical_rankings.append({
            'TEGNum': teg_num,
            'Pl': player,
            'Rank_Among_Player_TEGs_Gross': rank_player_gross,
            'Rank_Among_Player_TEGs_Stableford': rank_player_stableford,
            'Rank_Among_All_TEGs_To_Date_Gross': rank_all_gross,
            'Rank_Among_All_TEGs_To_Date_Stableford': rank_all_stableford
        })

    historical_df = pd.DataFrame(historical_rankings)

    # ========================================
    # 8. MERGE ALL SECTIONS
    # ========================================
    logger.info("Merging all sections")

    summary = basic_info
    summary = summary.merge(tournament_scores, on=['TEGNum', 'Pl'], how='left')
    summary = summary.merge(consistency, on=['TEGNum', 'Pl'], how='left')
    summary = summary.merge(lead_tracking, on=['TEGNum', 'Pl'], how='left')
    summary = summary.merge(scoring, on=['TEGNum', 'Pl'], how='left')
    summary = summary.merge(historical_df, on=['TEGNum', 'Pl'], how='left')

    # ========================================
    # 9. COLUMN ORDERING
    # ========================================
    logger.info("Ordering columns")

    column_order = [
        # Basic Info
        'TEGNum', 'Player', 'Pl', 'TEG', 'Year',

        # Tournament Scores & Rankings
        'Tournament_Score_Sc', 'Tournament_Score_Gross', 'Tournament_Score_Stableford',
        'Final_Rank_Gross', 'Final_Rank_Stableford',
        'Final_Gap_Gross', 'Final_Gap_Stableford',
        'Won_Gross', 'Won_Stableford', 'Wooden_Spoon',
        'Margin_Gross', 'Margin_Stableford',

        # Performance Consistency
        'Best_Round_Gross', 'Worst_Round_Gross', 'Range_Round_Gross', 'StdDev_Round_Gross',
        'Best_Round_Stableford', 'Worst_Round_Stableford', 'Range_Round_Stableford', 'StdDev_Round_Stableford',
        'StdDev_Hole_Gross', 'StdDev_Hole_Stableford',

        # Lead Tracking
        'Total_Holes_In_Lead_Gross', 'Total_Holes_In_Lead_Stableford',
        'Rounds_Leading_After_Gross', 'Rounds_Leading_After_Stableford',
        'Total_Lead_Gained_Gross', 'Total_Lead_Lost_Gross',
        'Total_Lead_Gained_Stableford', 'Total_Lead_Lost_Stableford',

        # Scoring Achievements
        'Total_Eagles', 'Total_Birdies', 'Total_Pars', 'Total_Bogeys',
        'Total_Double_Bogeys', 'Total_Worse_Than_Double',
        'Holes_In_One', 'Total_Stableford_5s', 'Total_Stableford_0s',

        # Historical Context
        'Rank_Among_Player_TEGs_Gross', 'Rank_Among_Player_TEGs_Stableford',
        'Rank_Among_All_TEGs_To_Date_Gross', 'Rank_Among_All_TEGs_To_Date_Stableford'
    ]

    summary = summary[column_order]

    logger.info(f"Tournament summary created: {len(summary)} rows, {len(summary.columns)} columns")

    return summary


def create_round_streaks_summary(all_data_df=None, streaks_df=None):
    """
    Create a comprehensive streaks summary for each round (unique TEG + Round + Player combination).

    This function calculates adjusted streaks for each round, showing:
    - Maximum streak lengths for each streak type within the round
    - Location information (from which hole to which hole)
    - All 10 streak types (Eagles, Birdies, Pars or Better, No +2s, No TBPs,
      No Eagles, No Birdies, Over Par, +2s or Worse, TBPs)

    Args:
        all_data_df (pd.DataFrame, optional): DataFrame with hole-by-hole data.
            If None, loads from all-data.parquet.
        streaks_df (pd.DataFrame, optional): DataFrame with streak data.
            If None, loads from streaks.parquet.

    Returns:
        pd.DataFrame: Summary table with columns:
            ['TEG', 'TEGNum', 'Round', 'Player', 'Pl', 'Streak_Type', 'Max_Streak', 'Location']
    """

    logger.info("Creating round streaks summary")

    # Import the helper function from streak_analysis_processing
    from helpers.streak_analysis_processing import calculate_window_streaks

    # ========================================
    # 1. LOAD DATA
    # ========================================
    if all_data_df is None:
        all_data_df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    if streaks_df is None:
        streaks_df = read_file(STREAKS_PARQUET)

    # ========================================
    # 2. MERGE STREAKS WITH ROUND INFO
    # ========================================
    logger.info("Merging streaks with round information")

    # Merge to get TEG, Round, Player info
    df = streaks_df.merge(
        all_data_df[['HoleID', 'TEG', 'TEGNum', 'Round', 'Pl', 'Player']],
        on=['HoleID', 'Pl'],
        how='left'
    )

    # ========================================
    # 3. CALCULATE STREAKS FOR EACH ROUND
    # ========================================
    logger.info("Calculating streaks for each round")

    all_results = []

    # Get unique TEG + Round combinations
    rounds = df[['TEGNum', 'Round']].drop_duplicates().sort_values(['TEGNum', 'Round'])

    for _, row in rounds.iterrows():
        teg_num = row['TEGNum']
        round_num = row['Round']

        # Filter to this round
        round_data = df[(df['TEGNum'] == teg_num) & (df['Round'] == round_num)].copy()

        if len(round_data) == 0:
            continue

        # Sort by Career Count for correct streak calculation
        round_data = round_data.sort_values(['Pl', 'Career Count'])

        # Keep player mapping for later
        player_mapping = round_data[['Player', 'Pl']].drop_duplicates()

        # Calculate window streaks for this round
        round_streaks = calculate_window_streaks(round_data)

        # Merge player codes back
        round_streaks = round_streaks.merge(player_mapping, on='Player', how='left')

        # Add TEG and Round info
        round_streaks['TEGNum'] = teg_num
        round_streaks['Round'] = round_num

        all_results.append(round_streaks)

    # ========================================
    # 4. COMBINE AND FORMAT
    # ========================================
    if len(all_results) == 0:
        logger.warning("No round streaks calculated")
        return pd.DataFrame()

    final_df = pd.concat(all_results, ignore_index=True)

    # Add TEG name
    teg_mapping = all_data_df[['TEGNum', 'TEG']].drop_duplicates().set_index('TEGNum')['TEG'].to_dict()
    final_df['TEG'] = final_df['TEGNum'].map(teg_mapping)

    # Rename columns with underscores for consistency
    final_df = final_df.rename(columns={
        'Streak Type': 'Streak_Type',
        'Max Streak': 'Max_Streak'
    })

    # Reorder columns
    final_df = final_df[['TEG', 'TEGNum', 'Round', 'Player', 'Pl', 'Streak_Type', 'Max_Streak', 'Location']]

    # Sort by TEG, Round, Player, Streak Type
    final_df = final_df.sort_values(['TEGNum', 'Round', 'Player', 'Streak_Type']).reset_index(drop=True)

    logger.info(f"Round streaks summary created: {len(final_df)} rows")

    return final_df


def create_tournament_streaks_summary(all_data_df=None, streaks_df=None):
    """
    Create a comprehensive streaks summary for each tournament (unique TEG + Player combination).

    This function calculates adjusted streaks for each tournament, showing:
    - Maximum streak lengths for each streak type within the tournament
    - Location information (from which hole to which hole)
    - All 10 streak types (Eagles, Birdies, Pars or Better, No +2s, No TBPs,
      No Eagles, No Birdies, Over Par, +2s or Worse, TBPs)

    Args:
        all_data_df (pd.DataFrame, optional): DataFrame with hole-by-hole data.
            If None, loads from all-data.parquet.
        streaks_df (pd.DataFrame, optional): DataFrame with streak data.
            If None, loads from streaks.parquet.

    Returns:
        pd.DataFrame: Summary table with columns:
            ['TEG', 'TEGNum', 'Player', 'Pl', 'Streak_Type', 'Max_Streak', 'Location']
    """

    logger.info("Creating tournament streaks summary")

    # Import the helper function from streak_analysis_processing
    from helpers.streak_analysis_processing import calculate_window_streaks

    # ========================================
    # 1. LOAD DATA
    # ========================================
    if all_data_df is None:
        all_data_df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    if streaks_df is None:
        streaks_df = read_file(STREAKS_PARQUET)

    # ========================================
    # 2. MERGE STREAKS WITH TEG INFO
    # ========================================
    logger.info("Merging streaks with TEG information")

    # Merge to get TEG, Player info
    df = streaks_df.merge(
        all_data_df[['HoleID', 'TEG', 'TEGNum', 'Round', 'Pl', 'Player']],
        on=['HoleID', 'Pl'],
        how='left'
    )

    # ========================================
    # 3. CALCULATE STREAKS FOR EACH TEG
    # ========================================
    logger.info("Calculating streaks for each tournament")

    all_results = []

    # Get unique TEGs
    tegs = df['TEGNum'].unique()

    for teg_num in sorted(tegs):
        # Filter to this TEG
        teg_data = df[df['TEGNum'] == teg_num].copy()

        if len(teg_data) == 0:
            continue

        # Sort by Career Count for correct streak calculation
        teg_data = teg_data.sort_values(['Pl', 'Career Count'])

        # Keep player mapping for later
        player_mapping = teg_data[['Player', 'Pl']].drop_duplicates()

        # Calculate window streaks for this TEG
        teg_streaks = calculate_window_streaks(teg_data)

        # Merge player codes back
        teg_streaks = teg_streaks.merge(player_mapping, on='Player', how='left')

        # Add TEG info
        teg_streaks['TEGNum'] = teg_num

        all_results.append(teg_streaks)

    # ========================================
    # 4. COMBINE AND FORMAT
    # ========================================
    if len(all_results) == 0:
        logger.warning("No tournament streaks calculated")
        return pd.DataFrame()

    final_df = pd.concat(all_results, ignore_index=True)

    # Add TEG name
    teg_mapping = all_data_df[['TEGNum', 'TEG']].drop_duplicates().set_index('TEGNum')['TEG'].to_dict()
    final_df['TEG'] = final_df['TEGNum'].map(teg_mapping)

    # Rename columns with underscores for consistency
    final_df = final_df.rename(columns={
        'Streak Type': 'Streak_Type',
        'Max Streak': 'Max_Streak'
    })

    # Reorder columns
    final_df = final_df[['TEG', 'TEGNum', 'Player', 'Pl', 'Streak_Type', 'Max_Streak', 'Location']]

    # Sort by TEG, Player, Streak Type
    final_df = final_df.sort_values(['TEGNum', 'Player', 'Streak_Type']).reset_index(drop=True)

    logger.info(f"Tournament streaks summary created: {len(final_df)} rows")

    return final_df


def check_for_complete_and_duplicate_data(all_scores_path: str, all_data_path: str) -> Dict[str, pd.DataFrame]:
    """
    Check for complete and duplicate data in the all-scores (CSV) and all-data (Parquet) files.

    Parameters:
        all_scores_path (str): Path to the all-scores CSV file.
        all_data_path (str): Path to the all-data Parquet file.

    Returns:
        Dict[str, pd.DataFrame]: Summary of incomplete and duplicate data.
    """
    logger.info("Checking for complete and duplicate data.")

    # Load the all-scores CSV file and the all-data Parquet file
    all_scores_df = read_file(all_scores_path)
    all_data_df = read_file(all_data_path)
    logger.debug("All-scores and all-data files loaded.")

    # Group by TEG, Round, and Player and count the number of entries
    all_scores_count = all_scores_df.groupby(['TEGNum', 'Round', 'Pl']).size().reset_index(name='EntryCount')
    all_data_count = all_data_df.groupby(['TEGNum', 'Round', 'Pl']).size().reset_index(name='EntryCount')

    # Check for incomplete and duplicate data in all-scores.csv
    incomplete_scores = all_scores_count[all_scores_count['EntryCount'] < TOTAL_HOLES]
    duplicate_scores = all_scores_count[all_scores_count['EntryCount'] > TOTAL_HOLES]

    # Check for incomplete and duplicate data in all-data.parquet
    incomplete_data = all_data_count[all_data_count['EntryCount'] < TOTAL_HOLES]
    duplicate_data = all_data_count[all_data_count['EntryCount'] > TOTAL_HOLES]

    # Summarize the results
    summary: Dict[str, Any] = {
        'incomplete_scores': incomplete_scores,
        'duplicate_scores': duplicate_scores,
        'incomplete_data': incomplete_data,
        'duplicate_data': duplicate_data
    }

    # Log the summary
    if not incomplete_scores.empty:
        logger.warning("Incomplete data found in all-scores.csv.")
    else:
        logger.info("No incomplete data found in all-scores.csv.")

    if not duplicate_scores.empty:
        logger.warning("Duplicate data found in all-scores.csv.")
    else:
        logger.info("No duplicate data found in all-scores.csv.")

    if not incomplete_data.empty:
        logger.warning("Incomplete data found in all-data.parquet.")
    else:
        logger.info("No incomplete data found in all-data.parquet.")

    if not duplicate_data.empty:
        logger.warning("Duplicate data found in all-data.parquet.")
    else:
        logger.info("No duplicate data found in all-data.parquet.")

    return summary


def get_teg_rounds(TEG: str) -> int:
    """
    Return the number of rounds for a given TEG.
    If the TEG is not found in the dictionary, return 4 as the default value.

    Parameters:
        TEG (str): The TEG identifier (e.g., 'TEG 1', 'TEG 2', etc.)

    Returns:
        int: The total number of rounds for the given TEG, defaulting to 4 if not found.
    """
    return TEG_ROUNDS.get(TEG, 4)

def get_tegnum_rounds(TEGNum: int) -> int:
    """
    Return the number of rounds for a given TEG.
    If the TEG is not found in the dictionary, return 4 as the default value.

    Parameters:
        TEG (str): The TEG identifier (e.g., 'TEG 1', 'TEG 2', etc.)

    Returns:
        int: The total number of rounds for the given TEG, defaulting to 4 if not found.
    """
    return TEGNUM_ROUNDS.get(TEGNum, 4)

def format_vs_par(value: float) -> str:
    """
    Format the value against par.

    Parameters:
        value (float): The value to format.

    Returns:
        str: Formatted string.
    """
    if pd.isna(value):
        return ""
    value = int(value)
    if value > 0:
        return f"+{value}"
    elif value < 0:
        return f"{value}"
    else:
        return "="


def get_net_competition_measure(teg_num: int) -> str:
    """
    Return the scoring measure to use for the net competition based on TEG number.
    
    Up to TEG 7, the net competition was based on total net vs par (NetVP).
    From TEG 8 onwards, the net competition is based on total stableford points.
    
    Parameters:
        teg_num (int): The TEG number
        
    Returns:
        str: 'NetVP' for TEG 1-7, 'Stableford' for TEG 8+
        
    Examples:
        >>> get_net_competition_measure(3)
        'NetVP'
        >>> get_net_competition_measure(8)
        'Stableford'
    """
    if teg_num <= 7:
        return 'NetVP'
    else:
        return 'Stableford'


def get_teg_winners(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate TEG winners, best net, gross, and worst net by TEG.

    Parameters:
        df (pd.DataFrame): DataFrame containing the golf data.

    Returns:
        pd.DataFrame: DataFrame summarizing TEG winners.
    """
    logger.info("Calculating TEG winners.")

    # Group by 'TEGNum' and 'Player', and calculate the sum for each player in each TEG
    grouped = df.groupby(['TEGNum', 'Player']).agg({
        'GrossVP': 'sum',
        'NetVP': 'sum',
        'Stableford': 'sum'
    }).reset_index()

    results = []

    # Get unique TEG numbers
    for teg_num in df['TEGNum'].unique():
        # Filter data for the current TEG
        teg_data = grouped[grouped['TEGNum'] == teg_num]
        
        # Determine which measure to use for net competition based on TEG number
        net_measure = get_net_competition_measure(teg_num)

        # Identify the best gross, best net, and worst net players
        best_gross_player = teg_data.loc[teg_data['GrossVP'].idxmin(), 'Player']
        
        if net_measure == 'NetVP':
            # For TEG 1-5: Lower NetVP is better (closer to or under par)
            best_net_player = teg_data.loc[teg_data['NetVP'].idxmin(), 'Player']
            worst_net_player = teg_data.loc[teg_data['NetVP'].idxmax(), 'Player']
        else:
            # For TEG 6+: Higher Stableford is better
            best_net_player = teg_data.loc[teg_data['Stableford'].idxmax(), 'Player']
            worst_net_player = teg_data.loc[teg_data['Stableford'].idxmin(), 'Player']

        # Apply manual overrides if any
        teg_label = f"TEG {teg_num}"
        overrides = TEG_OVERRIDES.get(teg_label, {})
        best_gross_player = overrides.get('Best Gross', best_gross_player)
        best_net_player = overrides.get('Best Net', best_net_player)
        worst_net_player = overrides.get('Worst Net', worst_net_player)

        # Append the results
        results.append({
            'TEGNum': teg_num,
            'TEG': teg_label,
            'Best Gross': best_gross_player,
            'Best Net': best_net_player,
            'Worst Net': worst_net_player
        })

    # Convert results to a DataFrame
    result_df = pd.DataFrame(results).sort_values(by='TEGNum')

    # Merge with year data from df
    teg_years = df[['TEGNum', 'Year']].drop_duplicates()
    result_df = result_df.merge(teg_years, on='TEGNum', how='left')

    # Rename columns
    result_df.rename(columns={
        'Best Net': 'TEG Trophy',
        'Best Gross': 'Green Jacket',
        'Worst Net': 'HMM Wooden Spoon',
        'Year': 'Year'
    }, inplace=True)

    # Select and order columns
    result_df = result_df[['TEG', 'Year', 'TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon']]

    logger.info("TEG winners calculated.")
    return result_df

from typing import List
import pandas as pd

def aggregate_data(data: pd.DataFrame, aggregation_level: str, measures: List[str] = None, additional_group_fields: List[str] = None) -> pd.DataFrame:
    """
    Generalized aggregation function with dynamic level of aggregation and additional group fields.

    Parameters:
        data (pd.DataFrame): The DataFrame to aggregate.
        aggregation_level (str): The level of aggregation ('Player', 'TEG', 'Round', 'FrontBack', 'Hole').
        measures (List[str], optional): List of measure columns to aggregate. Defaults to standard measures.
        additional_group_fields (List[str], optional): Additional fields to include in the grouping. Defaults to None.

    Returns:
        pd.DataFrame: Aggregated DataFrame.
    """
    # Set default measures if none provided
    if measures is None:
        measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']

    # Get the fields related to each aggregation level
    fields_by_level = list_fields_by_aggregation_level(data)

    # Define the hierarchy of aggregation levels
    aggregation_hierarchy = ['Player', 'TEG', 'Round', 'FrontBack', 'Hole']

    if aggregation_level not in aggregation_hierarchy:
        raise ValueError(f"Invalid aggregation level: '{aggregation_level}'. Choose from: {aggregation_hierarchy}")

    # Determine which fields to include based on the selected aggregation level
    idx = aggregation_hierarchy.index(aggregation_level)
    group_columns = []

    # Add all fields from the selected aggregation level and higher levels
    for level in aggregation_hierarchy[:idx + 1]:
        group_columns.extend(fields_by_level[level])

    # Add additional group fields if provided
    if additional_group_fields:
        if isinstance(additional_group_fields, str):
            additional_group_fields = [additional_group_fields]  # Wrap in a list if it's a string
        group_columns.extend(additional_group_fields)

    # Ensure group columns are unique
    group_columns = list(set(group_columns))

    # Debug: Print group columns and check if they exist in the DataFrame
    #print(f"Group columns: {group_columns}")
    #print(f"DataFrame columns: {data.columns.tolist()}")

    # Check if all group_columns are present in the DataFrame
    missing_columns = [col for col in group_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"Missing columns in the DataFrame: {missing_columns}")

    # Perform aggregation
    aggregated_df = data.groupby(group_columns, as_index=False)[measures].sum()
    aggregated_df = aggregated_df.sort_values(by=group_columns)

    return aggregated_df

@st.cache_data
def get_complete_teg_data():
    all_data = load_all_data(exclude_teg_50 = True, exclude_incomplete_tegs= True)
    aggregated_data = aggregate_data(all_data,'TEG')
    return aggregated_data

@st.cache_data
def get_teg_data_inc_in_progress():
    all_data = load_all_data(exclude_teg_50 = True, exclude_incomplete_tegs= False)
    aggregated_data = aggregate_data(all_data,'TEG')
    return aggregated_data

@st.cache_data
def get_round_data(ex_50 = True, ex_incomplete= False):
    all_data = load_all_data(exclude_teg_50 = ex_50, exclude_incomplete_tegs = ex_incomplete)
    aggregated_data = aggregate_data(all_data,'Round')
    return aggregated_data

@st.cache_data
def get_9_data():
    all_data = load_all_data(exclude_teg_50 = True, exclude_incomplete_tegs= False)
    aggregated_data = aggregate_data(all_data,'FrontBack')
    return aggregated_data    

@st.cache_data
def get_Pl_data():
    all_data = load_all_data(exclude_teg_50 = True, exclude_incomplete_tegs= False)
    aggregated_data = aggregate_data(all_data,'Player')
    return aggregated_data

def list_fields_by_aggregation_level(df):
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

# Example usage
# fields_by_level = list_fields_by_aggregation_level(all_data)
# for level, fields in fields_by_level.items():
#     print(f"Fields unique at {level} level: {fields}")


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

    Example:
    --------
    >>> add_ranks_for_fields(df, fields_to_rank=['Sc', 'Stableford'], rank_ascending=True)
    This will add rank columns for 'Sc' and 'Stableford', ranked in ascending order.
    
    >>> add_ranks_for_fields(df)
    This will add rank columns for the default fields ['Sc', 'GrossVP', 'NetVP', 'Stableford'] 
    with default ascending/descending order.
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
        
        #print(f'===================\nField: {field}\ninput_rank_asc: {input_rank_ascending}\nRank ascending:{rank_ascending}')

        # Rank within each Player's scores
        df[f'Rank_within_player_{field}'] = df.groupby('Player')[field].rank(method='min', ascending=rank_ascending)
        
        # Rank across all Players
        df[f'Rank_within_all_{field}'] = df[field].rank(method='min', ascending=rank_ascending)
    
    return df

@st.cache_data
def get_ranked_teg_data():
    df = get_complete_teg_data()
    ranked_data = add_ranks(df)
    return ranked_data

@st.cache_data
def get_ranked_round_data():
    df = get_round_data()
    ranked_data = add_ranks(df)
    return ranked_data

@st.cache_data
def get_ranked_frontback_data():
    df = get_9_data()
    ranked_data = add_ranks(df)
    return ranked_data

def get_best(df, measure_to_use, player_level = False, top_n = 1):
    valid_measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    if measure_to_use not in valid_measures:
        error_message = f"Invalid measure: '{measure_to_use}'. Valid options are: {', '.join(valid_measures)}"

    if player_level is None:
        player_level = False

    if top_n is None:
        top_n = 1
    
    measure_fn = 'Rank_within_' + ('player' if player_level else 'all') + f'_{measure_to_use}' 

    #measure_fn
    return df[df[measure_fn] <= top_n]

def get_worst(df, measure_to_use, player_level = False, top_n = 1):
    valid_measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    if measure_to_use not in valid_measures:
        error_message = f"Invalid measure: '{measure_to_use}'. Valid options are: {', '.join(valid_measures)}"

    if player_level is None:
        player_level = False

    if top_n is None:
        top_n = 1
    
    #measure_fn = 'Rank_within_' + ('player' if player_level else 'all') + f'_{measure_to_use}' 

    if player_level == False:
        if measure_to_use == 'Stableford':
            df = df.nsmallest(top_n, measure_to_use)
        else:
            df = df.nlargest(top_n, measure_to_use)
    else:
        if measure_to_use == 'Stableford':
            df = df.groupby('Player', group_keys=False).apply(lambda x: x.nsmallest(top_n, measure_to_use))
        else:
            df = df.groupby('Player', group_keys=False).apply(lambda x: x.nlargest(top_n, measure_to_use))

    return df

def ordinal(n):
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix

def safe_ordinal(n):
    if pd.isna(n):
        return n  # or return a specific string like 'N/A'
    try:
        return ordinal(int(n))
    except ValueError:
        return str(n)  # or return a specific string for invalid inputs

def chosen_rd_context(ranked_rd_df, teg = 'TEG 16',rd = 4, measure = None):
    #@st.cache_data
    df = ranked_rd_df
    all_cnt = len(df)
    df['Pl_count'] = df.groupby('Pl')['Pl'].transform('count')
    chosen_rd = df[(df['TEG']==teg) & (df['Round'] == rd)]

    sort_ascending = measure != 'Stableford'
    chosen_rd = chosen_rd.sort_values(measure, ascending=sort_ascending)
    # chosen_rd['Pl rank'] = chosen_rd['Rank_within_player_' + measure].apply(safe_ordinal)
    # chosen_rd['All time rank'] = chosen_rd['Rank_within_all_' + measure].apply(safe_ordinal)
    #chosen_rd['Pl rank'] = f'{chosen_rd['Rank_within_player_' + measure].astype(int)} / {chosen_rd['Pl_count']}'
    chosen_rd['Pl rank'] = (chosen_rd['Rank_within_player_' + measure].astype(int).astype(str) + 
                        ' / ' + 
                        chosen_rd['Pl_count'].astype(str))
    chosen_rd['All time rank'] = (chosen_rd['Rank_within_all_' + measure].astype(int).astype(str) +
                              ' / ' +
                              str(all_cnt))
    chosen_rd_context = chosen_rd[['Player',measure,'Pl rank','All time rank']]

    # Format the measure column appropriately
    if measure in ['GrossVP', 'NetVP']:
        chosen_rd_context[measure] = chosen_rd_context[measure].apply(format_vs_par)
    else:
        chosen_rd_context[measure] = chosen_rd_context[measure].astype(int)

    return chosen_rd_context

def chosen_teg_context(ranked_teg_df, teg = 'TEG 15', measure = None):
    #@st.cache_data
    df = ranked_teg_df
    all_cnt = len(df)
    df['Pl_count'] = df.groupby('Pl')['Pl'].transform('count')
    chosen_teg = df[(df['TEG']==teg)]

    sort_ascending = measure != 'Stableford'
    chosen_teg = chosen_teg.sort_values(measure, ascending=sort_ascending)
    # chosen_rd['Pl rank'] = chosen_rd['Rank_within_player_' + measure].apply(safe_ordinal)
    # chosen_rd['All time rank'] = chosen_rd['Rank_within_all_' + measure].apply(safe_ordinal)
    #chosen_rd['Pl rank'] = f'{chosen_rd['Rank_within_player_' + measure].astype(int)} / {chosen_rd['Pl_count']}'
    chosen_teg['Pl rank'] = (chosen_teg['Rank_within_player_' + measure].astype(int).astype(str) + 
                        ' / ' + 
                        chosen_teg['Pl_count'].astype(str))
    chosen_teg['All time rank'] = (chosen_teg['Rank_within_all_' + measure].astype(int).astype(str) +
                              ' / ' +
                              str(all_cnt))
    chosen_teg_context = chosen_teg[['Player',measure,'Pl rank','All time rank']]

    # Format the measure column appropriately
    if measure in ['GrossVP', 'NetVP']:
        chosen_teg_context[measure] = chosen_teg_context[measure].apply(format_vs_par)
    else:
        chosen_teg_context[measure] = chosen_teg_context[measure].astype(int)

    return chosen_teg_context


def create_stat_section(title, value=None, df=None, divider=None):
    """
    Creates an HTML string representing a stat section with a title, optional value, and details from a DataFrame.

    This function generates a formatted HTML string for displaying statistical information. It includes
    a title, an optional value (typically a score or primary statistic), and detailed information
    from a provided DataFrame. Each row of the DataFrame is formatted into a single line of details.

    Parameters:
    -----------
    title : str
        The title of the stat section.
    value : str or None, optional
        An optional value to be displayed prominently alongside the title. If None, no value is displayed.
    df : pandas.DataFrame or None, optional
        A DataFrame containing the detailed information to be displayed. Each row represents a set of
        details, and each column will be formatted and displayed. If None, no details are displayed.
    divider : str or None, optional
        An optional value to split up the text on the second row

    Returns:
    --------
    str
        An HTML string representing the formatted stat section.

    Notes:
    ------
    - The function assumes that the necessary CSS classes (stat-section, title, value, stat-details)
    are defined in the Streamlit app's stylesheet.
    - Each column in the DataFrame will be wrapped in a <span> tag with a class name matching the column name.
    - All rows from the DataFrame are joined with '<br>' tags for line breaks.

    Example:
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({'name': ['John Doe'], 'score': ['95'], 'date': ['2023-05-01']})
    >>> html = create_stat_section("Top Score", "95", df)
    >>> print(html)
    <div class="stat-section">
        <h2><span class='title'>Top Score</span><span class='value'> 95</span></h2>
        <div class="stat-details">
            <strong><span class='name'>John Doe</span></strong> • <span class='score'>95</span> • <span class='date'>2023-05-01</span>
        </div>
    </div>
    """

    if divider is None:
        divider = ''

    # Create the title and value part
    title_html = f"<h2><span class='title'>{title}</span>"
    if value is not None:
        title_html += f"<span class='value'> {value}</span>"
    title_html += "</h2>"

    # Create the details part from the DataFrame
    details_html = ""
    if df is not None and not df.empty:
        rows = []
        for _, row in df.iterrows():
            # Make only the Player element strong
            player_html = f"<strong><span class='Player'>{row['Player']}</span></strong>"
            # Format other elements normally
            other_elements = [
                f"<span class='{col}'>{row[col]}</span>"
                for col in df.columns if col != 'Player'
            ]
            # Join all elements with the divider
            row_elements = [player_html] + other_elements
            row_str = f" {divider}".join(row_elements)
            rows.append(row_str)
        details_html = "<br>".join(rows)

    # Combine all parts
    return f"""
    <div class="stat-section">
        {title_html}
        <div class="stat-details">
            {details_html}
        </div>
    </div>
    """


# utils.py

import pandas as pd

def define_score_types(gross_vp):
    """
    Define score types based on the GrossVP values.
    
    Args:
    gross_vp (pd.Series): A pandas Series containing GrossVP values.
    
    Returns:
    dict: A dictionary with counts for each score type.
    """
    return {
        'Pars_or_Better': (gross_vp <= 0).sum(),
        'Birdies': (gross_vp == -1).sum(),
        'Eagles': (gross_vp == -2).sum(),
        'TBPs': (gross_vp > 2).sum()
    }

def apply_score_types(df, groupby_cols=['Player']):
    """
    Apply score type definitions to a DataFrame and return aggregated results.
    
    Args:
    df (pd.DataFrame): The input DataFrame with a 'GrossVP' column.
    groupby_cols (list): Columns to group by before applying score types.
    
    Returns:
    pd.DataFrame: Aggregated results with score type counts.
    """
    grouped = df.groupby(groupby_cols).agg({
        'GrossVP': define_score_types
    }).reset_index()
    
    # Expand the dictionary result into separate columns
    score_columns = ['Pars_or_Better', 'Birdies', 'Eagles', 'TBPs']
    for col in score_columns:
        grouped[col] = grouped['GrossVP'].apply(lambda x: x[col])
    
    # Drop the original 'GrossVP' column containing the dictionary
    grouped = grouped.drop(columns=['GrossVP'])
    
    return grouped

def score_type_stats(df=None):

    if df is None:
        df = load_all_data(exclude_teg_50=True)

    # Apply score types grouped by Player
    stats = apply_score_types(df, groupby_cols=['Player'])
    
    # Add Holes_Played column
    stats['Holes_Played'] = df.groupby('Player')['GrossVP'].count().values

    # Calculate ratios and their inverses
    stats['Birdie_Rate'] = stats['Birdies'] / stats['Holes_Played']
    stats['Holes_per_Birdie'] = stats['Holes_Played'] / stats['Birdies']
    
    stats['Eagle_Rate'] = stats['Eagles'] / stats['Holes_Played']
    stats['Holes_per_Eagle'] = stats['Holes_Played'] / stats['Eagles']
    
    stats['TBP_Rate'] = stats['TBPs'] / stats['Holes_Played']
    stats['Holes_per_TBP'] = stats['Holes_Played'] / stats['TBPs']
    
    stats['Pars_or_Better_Rate'] = stats['Pars_or_Better'] / stats['Holes_Played']
    stats['Holes_per_Par_or_Better'] = stats['Holes_Played'] / stats['Pars_or_Better']
    
    return stats

def max_scoretype_per_round(df = None):

    if df is None:
        df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    # Apply score types with grouping by Player, Round, and TEG
    scores = apply_score_types(df, groupby_cols=['Player', 'Round', 'TEG'])
    
    # Find the maximum scores across rounds and TEGs for each player
    max_scores = scores.groupby('Player').agg({
        'Pars_or_Better': 'max',
        'Birdies': 'max',
        'Eagles': 'max',
        'TBPs': 'max'
    }).reset_index()
    
    return max_scores


def max_scoretype_per_teg(df = None):

    if df is None:
        df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    # Apply score types with grouping by Player, Round, and TEG
    scores = apply_score_types(df, groupby_cols=['Player', 'TEG'])
    
    # Find the maximum scores across rounds and TEGs for each player
    max_scores = scores.groupby('Player').agg({
        'Pars_or_Better': 'max',
        'Birdies': 'max',
        'Eagles': 'max',
        'TBPs': 'max'
    }).reset_index()
    
    return max_scores

# Function to find the root directory (TEG folder) by looking for the 'TEG' folder name
# def find_project_root(current_path: Path, folder_name: str) -> Path:
#     while current_path.name != folder_name:
#         if current_path == current_path.parent:
#             raise RuntimeError(f"Folder '{folder_name}' not found in the directory tree")
#         current_path = current_path.parent
#     return current_path

# def get_base_directory():
#     # Check if running on Streamlit Cloud by checking if "/app/TEG" path exists
#     if Path("/app/TEG").exists():
#         BASE_DIR = Path("/app/TEG")  # Adjusted to match your folder structure
#     else:
#         # Running locally, use find_project_root to find the TEG directory
#         BASE_DIR = find_project_root(Path(__file__).resolve(), 'TEG')

#     return BASE_DIR

def load_css_file(css_file_path: str):
    """Load CSS from file and inject into Streamlit using proper path resolution"""
    base_dir = get_base_directory()
    
    # If running from streamlit folder, styles are in same folder
    if Path.cwd().name == "streamlit":
        full_path = Path.cwd() / css_file_path
    else:
        # Running from project root, styles are in streamlit subfolder
        full_path = base_dir / "streamlit" / css_file_path
    
    try:
        with open(full_path, 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found: {full_path}")
        st.write(f"Current working directory: {Path.cwd()}")
        st.write(f"Base directory: {base_dir}")

def load_datawrapper_css():
    """Load datawrapper table CSS from external file"""
    load_css_file('styles/datawrapper.css')

def datawrapper_table(df, left_align=None, css_classes=None, return_html=False):
    """
    Render a pandas DataFrame as HTML with datawrapper styling.
    
    Args:
        df: DataFrame to render
        left_align: If True, left-align all cells (backward compatibility)
        css_classes: Additional CSS classes as string (e.g., 'history-table narrow-first')
        return_html: If True, return HTML string instead of writing to Streamlit
    """
    
    # Start with base class
    classes = 'datawrapper-table'
    
    # Add left alignment if needed
    if left_align:
        classes += ' table-left-align'
    
    # Add any additional classes
    if css_classes:
        classes += f' {css_classes}'
    
    # Render table
    html = df.to_html(index=False, justify='left', classes=classes)
    
    if return_html:
        return html
    else:
        st.write(html, unsafe_allow_html=True)

service_account_info = {
    "type": os.getenv('GOOGLE_TYPE'),
    "project_id": os.getenv('GOOGLE_PROJECT_ID'),
    "private_key_id": os.getenv('GOOGLE_PRIVATE_KEY_ID'),
    "private_key": os.getenv('GOOGLE_PRIVATE_KEY').replace('\\n', '\n') if os.getenv('GOOGLE_PRIVATE_KEY') else None,
    "client_email": os.getenv('GOOGLE_CLIENT_EMAIL'),
    "client_id": os.getenv('GOOGLE_CLIENT_ID'),
    "auth_uri": os.getenv('GOOGLE_AUTH_URI'),
    "token_uri": os.getenv('GOOGLE_TOKEN_URI'),
    "auth_provider_x509_cert_url": os.getenv('GOOGLE_AUTH_PROVIDER_X509_CERT_URL'),
    "client_x509_cert_url": os.getenv('GOOGLE_CLIENT_X509_CERT_URL'),
    "universe_domain": os.getenv('GOOGLE_UNIVERSE_DOMAIN'),
}

def get_teg_metadata(teg_num, round_num=None):
    """
    Get TEG metadata from round_info.csv
    
    Args:
        teg_num: TEG number
        round_num: Optional round number for round-specific data
    
    Returns:
        dict: Metadata including area, course, date, year
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

def format_date_for_scorecard(date_str, input_format=None, output_format='%d/%m/%y'):
    """
    Format date string with flexible input and output formats (UK conventions)
    
    Args:
        date_str: Date string from CSV
        input_format: Optional specific format (e.g., '%d/%m/%Y'). If None, tries common UK formats
        output_format: Output format (default: '15/1/25' UK style without leading zeros)
    
    Returns:
        str: Formatted date or original string if parsing fails
    """
    if not date_str or pd.isna(date_str):
        return str(date_str) if date_str else None
    
    date_str = str(date_str).strip()
    
    try:
        if input_format:
            # Use specified format
            date_obj = datetime.strptime(date_str, input_format)
        else:
            # Try common UK date formats (day first, no leading zeros supported)
            uk_formats = [
                '%d/%m/%Y',    # 15/1/2025 or 1/12/2025
                '%d/%m/%y',    # 15/1/25 or 1/12/25
                '%d-%m-%Y',    # 15-1-2025 or 1-12-2025
                '%d-%m-%y',    # 15-1-25 or 1-12-25
                '%d %b %Y',    # 15 Jan 2025
                '%d %B %Y',    # 15 January 2025
                '%Y-%m-%d',    # 2025-01-15 (ISO format)
                '%d.%m.%Y',    # 15.1.2025
                '%d.%m.%y',    # 15.1.25
            ]
            
            date_obj = None
            for fmt in uk_formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if date_obj is None:
                return date_str
        
        # Custom formatting to avoid leading zeros in day/month
        if output_format == '%d/%m/%y':
            return f"{date_obj.day}/{date_obj.month}/{date_obj.strftime('%y')}"
        elif output_format == '%d/%m/%Y':
            return f"{date_obj.day}/{date_obj.month}/{date_obj.year}"
        elif output_format == '%d %B %Y':
            return f"{date_obj.day} {date_obj.strftime('%B')} {date_obj.year}"
        elif output_format == '%d %b %Y':
            return f"{date_obj.day} {date_obj.strftime('%b')} {date_obj.year}"
        elif output_format == '%d %b %y':
            return f"{date_obj.day} {date_obj.strftime('%b')} {date_obj.strftime('%y')}"
        else:
            # For any other format, use standard strftime
            return date_obj.strftime(output_format)
            
    except Exception:
        return date_str

def get_scorecard_data(teg_num=None, round_num=None, player_code=None):
    """
    Get golf data for scorecard generation with optional filtering by TEG, Round, and/or Player
    
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
        sort_cols = ['Hole']
    elif round_num is not None:
        # Single round, multiple players - sort by player then hole
        sort_cols = ['Pl', 'Hole']
    else:
        # Multiple rounds - sort by round then hole
        sort_cols = ['Round', 'Hole']
        if player_code is None:
            # Multiple players too - add player to sort
            sort_cols = ['Pl'] + sort_cols
    
    return all_data.sort_values(sort_cols)

### CONVERT TROPHY NAMES BETWEEN SHORT VERSIONS AND FULL NAMES

# short -> long
TROPHY_NAME_LOOKUPS_SHORTLONG = {
    "trophy": "TEG Trophy",
    "jacket": "Green Jacket",
    "spoon": "HMM Wooden Spoon",
}

# long -> short (keys normalised to lowercase for case-insensitive input)
TROPHY_NAME_LOOKUPS_LONGSHORT = {v.lower(): k for k, v in TROPHY_NAME_LOOKUPS_SHORTLONG.items()}

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
    """
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
    """
    key = trophy.strip()
    
    if key.lower() in TROPHY_NAME_LOOKUPS_LONGSHORT:  
        # it's already a long name → use as-is
        trophy_name = key
    else:
        # otherwise assume it's a short name → convert
        trophy_name = convert_trophy_name(key)

    return trophy_name

@st.cache_data
def load_course_info():
    """Load unique course/area combinations from round_info.csv"""
    round_info = read_file(ROUND_INFO_CSV)
    course_info = round_info[['Course', 'Area']].drop_duplicates()
    return course_info


def get_teg_filter_options(all_data):
    """
    Get TEG filtering options for dropdown selections.
    
    Args:
        all_data (pd.DataFrame): Complete tournament data
        
    Returns:
        list: TEG options including "All TEGs" and individual tournaments in reverse chronological order
        
    Purpose:
        Provides consistent TEG filtering options across different analysis pages
        Orders TEGs in reverse chronological order (most recent first)
    """
    tegnum_options = ['All TEGs'] + sorted(all_data['TEGNum'].unique().tolist(), reverse=True)
    return tegnum_options


def filter_data_by_teg(all_data, selected_tegnum):
    """
    Filter data by selected TEG tournament.
    
    Args:
        all_data (pd.DataFrame): Complete tournament data
        selected_tegnum: Selected TEG number or "All TEGs"
        
    Returns:
        pd.DataFrame: Filtered data for selected tournament or complete data
        
    Purpose:
        Applies consistent TEG filtering logic across different analysis pages
        Returns complete dataset when "All TEGs" is selected
    """
    if selected_tegnum != 'All TEGs':
        selected_tegnum_int = int(selected_tegnum)
        return all_data[all_data['TEGNum'] == selected_tegnum_int]
    else:
        return all_data


def get_hc(TEG_needed: int | None = None) -> pd.DataFrame:
    """
    Calculate handicaps for a given TEG.

    Parameters
    ----------
    TEG_needed : int, optional
        TEG number to calculate handicaps for.
        Defaults to the next TEG after the highest TEGNum in teg_data.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ['Pl', 'hc_raw', 'hc'].
    """

    # Load handicap reference
    hc = load_and_prepare_handicap_data(HANDICAPS_CSV)
    hc['TEGNum'] = hc["TEG"].str[-2:].str.strip().astype(int)

    # Load game data
    all_data = load_all_data(exclude_incomplete_tegs=False)
    teg_data = get_teg_data_inc_in_progress()
    num_rounds = get_number_of_completed_rounds_by_teg(all_data)

    # Default TEG_needed = next after highest available
    if TEG_needed is None:
        TEG_needed = teg_data["TEGNum"].max() + 1

    # Previous two TEGs
    TEG_1 = TEG_needed - 1
    TEG_2 = TEG_needed - 2
    tegnums = [TEG_1, TEG_2]

    # Handicap data for previous TEGs
    hc_x = hc[hc['TEGNum'].isin(tegnums)]

    # Stableford data for previous TEGs
    stab_x = teg_data.loc[teg_data['TEGNum'].isin(tegnums), ['Pl','Stableford','TEGNum']].copy()
    stab_x = stab_x.merge(num_rounds[['TEGNum','num_rounds']], on="TEGNum", how="left")
    stab_x['ave_stab'] = stab_x['Stableford'] / stab_x['num_rounds']

    # Merge HC and Stableford
    hc_merged = hc_x.merge(stab_x, on=['Pl','TEGNum'], how='left')
    hc_merged['ave_stab'] = pd.to_numeric(hc_merged['ave_stab'], errors="coerce").fillna(36)

    # Adjusted gross
    hc_merged['AdjGross'] = 36 - hc_merged['ave_stab'] + hc_merged['HC']

    # Pivot for weighted average
    pivoted = hc_merged.pivot(index="Pl", columns="TEGNum", values="AdjGross")

    # Weighted handicap calculation
    result = (
        0.75 * pivoted[TEG_1] +
        0.25 * pivoted[TEG_2]
    ).reset_index(name="hc_raw")

    # Add rounded version
    result['hc'] = result['hc_raw'].round(0).astype(int)
    return result

@st.cache_data
def get_next_teg_and_check_if_in_progress():
    """
    DEPRECATED: Use get_next_teg_and_check_if_in_progress_fast() instead.

    Get TEG completion status (cached for performance).
    This function is kept for backward compatibility but may be slow.
    """
    teg_data_inc_progress = get_teg_data_inc_in_progress()
    teg_data_completed = get_complete_teg_data()

    last_completed_teg = max(teg_data_completed['TEGNum'])
    next_teg = last_completed_teg + 1
    in_progress = (teg_data_inc_progress['TEGNum'] == next_teg).any()

    return last_completed_teg, next_teg, in_progress

def get_current_handicaps_formatted(last_completed_teg, next_teg):
    """Get handicaps in exact same format as hardcoded version"""
    # from utils import load_and_prepare_handicap_data, HANDICAPS_CSV, get_player_name

    hc_data = load_and_prepare_handicap_data(HANDICAPS_CSV)

    last_teg_str = f'TEG {last_completed_teg}'
    next_teg_str = f'TEG {next_teg}'

    # Get current and previous handicaps
    current_hc = hc_data[hc_data['TEG'] == next_teg_str]
    previous_hc = hc_data[hc_data['TEG'] == last_teg_str]

    # Track whether handicaps were calculated
    handicaps_were_calculated = current_hc.empty

    if current_hc.empty:
        # Calculate missing handicaps and supplement the data
        calculated_handicaps = get_hc(next_teg)

        # Transform calculated handicaps to match hc_data structure
        calculated_rows = []
        for _, row in calculated_handicaps.iterrows():
            calculated_rows.append({
                'TEG': next_teg_str,
                'Pl': row['Pl'],
                'HC': row['hc']
            })

        # Add calculated handicaps to hc_data
        calculated_df = pd.DataFrame(calculated_rows)
        hc_data = pd.concat([hc_data, calculated_df], ignore_index=True)

        # Now get the current handicaps (which will exist)
        current_hc = hc_data[hc_data['TEG'] == next_teg_str]
    
    # Merge and calculate change
    merged = current_hc.merge(previous_hc[['Pl', 'HC']], on='Pl', how='left', suffixes=('_current', '_previous'))
    merged['HC_previous'] = merged['HC_previous'].fillna(merged['HC_current'])
    merged['Change'] = merged['HC_current'] - merged['HC_previous']
    
    # Convert initials to full names using existing function
    merged['FullName'] = merged['Pl'].apply(get_player_name)
    
    # Create result in exact format expected by rest of code
    result = pd.DataFrame({
        'Handicap': merged['FullName'].tolist(),
        next_teg_str: merged['HC_current'].astype(int).tolist(),
        'Change': merged['Change'].astype(int).tolist()
    })

    return result, handicaps_were_calculated


# ============================================
#  TEG STATUS TRACKING FUNCTIONS
# ============================================

def analyze_teg_completion(all_data: pd.DataFrame) -> pd.DataFrame:
    """
    Determine completion status and round count for each TEG using existing get_incomplete_tegs() logic.

    Args:
        all_data: DataFrame with columns TEGNum, Round, Player, Hole

    Returns:
        DataFrame with columns: TEGNum, TEG, Year, Status, Rounds
    """
    # Get round info for TEG metadata
    round_info = read_file(ROUND_INFO_CSV)

    # Use existing get_incomplete_tegs() function to identify incomplete TEGs
    incomplete_teg_nums = set(get_incomplete_tegs(all_data))

    # Get all TEG numbers in the data
    all_teg_nums = set(all_data['TEGNum'].unique())

    # Build status analysis for each TEG
    teg_analysis = []

    for teg_num in all_teg_nums:
        teg_data = all_data[all_data['TEGNum'] == teg_num]

        # Determine status using get_incomplete_tegs() result
        is_complete = teg_num not in incomplete_teg_nums
        status = "complete" if is_complete else "in_progress"

        # Get actual round count for this TEG
        max_round = teg_data['Round'].max()

        # Get TEG metadata from round_info
        teg_info = round_info[round_info['TEGNum'] == teg_num].iloc[0]

        teg_analysis.append({
            'TEGNum': teg_num,
            'TEG': teg_info['TEG'],
            'Year': teg_info['Year'],
            'Status': status,
            'Rounds': max_round
        })

    return pd.DataFrame(teg_analysis)


def save_teg_status_file(status_data: pd.DataFrame, filename: str):
    """
    Save TEG status data to CSV file.

    Args:
        status_data: DataFrame with TEG status information
        filename: Name of the file (e.g., 'completed_tegs.csv')
    """
    # Sort by TEGNum for consistent ordering
    status_data_sorted = status_data.sort_values('TEGNum') if not status_data.empty else status_data

    # Use the relative path that write_file expects
    file_path = f'data/{filename}'

    # Write to file using existing write_file function
    write_file(file_path, status_data_sorted)


def update_teg_status_files():
    """
    Update TEG status files after data changes.
    This should be called after data updates or deletions.
    """
    # Clear cache first to ensure we work with fresh data after deletions/updates
    st.cache_data.clear()

    # Load all data to determine TEG completion status
    all_data = load_all_data(exclude_incomplete_tegs=False)

    if all_data.empty:
        logger.warning("No data available for TEG status analysis")
        return

    # Analyze completion by TEG
    teg_completion = analyze_teg_completion(all_data)

    # Split into completed and in-progress
    completed_tegs = teg_completion[teg_completion['Status'] == 'complete']
    in_progress_tegs = teg_completion[teg_completion['Status'] == 'in_progress']

    # Save status files (this automatically handles TEG transitions and deletions)
    save_teg_status_file(completed_tegs, 'completed_tegs.csv')
    save_teg_status_file(in_progress_tegs, 'in_progress_tegs.csv')

    logger.info(f"Updated TEG status files: {len(completed_tegs)} completed, {len(in_progress_tegs)} in progress")


def get_next_teg_and_check_if_in_progress_fast():
    """
    Fast TEG status check using status files instead of loading full data.

    Returns:
        tuple: (last_completed_teg, next_teg, in_progress)
    """
    try:
        completed_tegs = read_file('data/completed_tegs.csv')
        in_progress_tegs = read_file('data/in_progress_tegs.csv')

        last_completed_teg = completed_tegs['TEGNum'].max() if not completed_tegs.empty else 0
        next_teg = last_completed_teg + 1
        in_progress = (in_progress_tegs['TEGNum'] == next_teg).any() if not in_progress_tegs.empty else False

        return last_completed_teg, next_teg, in_progress

    except Exception as e:
        logger.warning(f"Status files not available, falling back to slow method: {e}")
        # Fallback to original method if status files don't exist
        return get_next_teg_and_check_if_in_progress()


def get_last_completed_teg_fast():
    """
    Get the highest TEG number from completed_tegs.csv with round count.

    Returns:
        tuple: (teg_num, rounds) or (None, 0) if no completed TEGs
    """
    try:
        completed_tegs = read_file('data/completed_tegs.csv')
        if completed_tegs.empty:
            return None, 0

        max_row = completed_tegs.loc[completed_tegs['TEGNum'].idxmax()]
        return max_row['TEGNum'], max_row['Rounds']

    except Exception as e:
        logger.warning(f"Error reading completed TEGs status file: {e}")
        return None, 0


def get_current_in_progress_teg_fast():
    """
    Get the current in-progress TEG with round count.

    Returns:
        tuple: (teg_num, rounds) or (None, 0) if no TEGs in progress
    """
    try:
        in_progress_tegs = read_file('data/in_progress_tegs.csv')
        if in_progress_tegs.empty:
            return None, 0

        # Should typically be only one in-progress TEG, get the first one
        current_row = in_progress_tegs.iloc[0]
        return current_row['TEGNum'], current_row['Rounds']

    except Exception as e:
        logger.warning(f"Error reading in-progress TEGs status file: {e}")
        return None, 0


def has_incomplete_teg_fast():
    """
    Fast check if there are any incomplete TEGs using status files.

    Returns:
        bool: True if there are TEGs in progress, False otherwise
    """
    try:
        in_progress_tegs = read_file('data/in_progress_tegs.csv')
        return not in_progress_tegs.empty

    except Exception as e:
        logger.warning(f"Error checking for incomplete TEGs: {e}")
        return False


# ============================================
#  CENTRALIZED NAVIGATION SYSTEM
# ============================================

def get_app_base_url():
    """
    Dynamically get the base URL for the current Streamlit app.

    Returns:
        str: Base URL for the app (e.g., 'http://localhost:8501' or 'https://app.railway.app')
    """
    if os.getenv('RAILWAY_ENVIRONMENT'):
        # Railway deployment - check for public domain
        railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')
        if railway_domain:
            return f"https://{railway_domain}"
        else:
            # Fallback - this should be updated with your actual Railway URL
            return "https://your-railway-app.railway.app"
    else:
        # Local development - use default Streamlit port
        return "http://localhost:8501"


def convert_filename_to_streamlit_url(page_file):
    """Convert a page filename to Streamlit's URL format.

    Streamlit strips leading numbers from filenames when creating URLs.
    The main page (first page in navigation) is accessible at root URL.

    Examples:
    - "101TEG History.py" → "" (main page, accessible at root)
    - "300TEG Records.py" → "TEG_Records"
    - "500Handicaps.py" → "Handicaps"
    - "leaderboard.py" → "leaderboard"
    """
    import re

    # Special case: main page (TEG History) should redirect to root
    if page_file == "101TEG History.py":
        return ""

    # Remove .py extension
    page_name = page_file.replace('.py', '')
    # Replace spaces with underscores
    page_name = page_name.replace(' ', '_')
    # Remove leading digits (Streamlit does this automatically)
    page_name = re.sub(r'^\d+', '', page_name)
    return page_name


# Import page configuration from dedicated config file
from page_config import PAGE_DEFINITIONS, SECTION_LAYOUTS, SECTION_CONFIG




# ============================================
#  CUSTOM NAVIGATION SYSTEM (Manual HTML)
# ============================================



def add_custom_navigation_links_DEPRECATED(input_value, css_class="custom-nav-link", layout="columns", separator=" | ", exclude_current=True):
    """Add custom HTML navigation links with full styling control

    Args:
        input_value: Page filename (e.g. "101TEG History.py") OR section name (e.g. "History")
        css_class: CSS class for the links (default: "custom-nav-link")
        layout: Layout style - "columns", "horizontal", or "vertical" (default: "columns")
        separator: Separator for horizontal layout (default: " | ")
        exclude_current: Whether to exclude current page from navigation (default: True)
    """
    # Smart detection: determine if input is page file or section name
    if input_value.endswith('.py'):
        # Input is a page filename
        # Handle both full path and just filename
        if os.path.sep in input_value:
            current_page_file = os.path.basename(input_value)
        else:
            current_page_file = input_value

        # Get current page info
        current_page_info = PAGE_DEFINITIONS.get(current_page_file)
        if not current_page_info:
            return  # No navigation for pages not in the system

        section = current_page_info["section"]

        # Get all pages in this section, optionally excluding current page
        if exclude_current:
            section_pages = [
                file for file, info in PAGE_DEFINITIONS.items()
                if info["section"] == section and file != current_page_file
            ]
        else:
            section_pages = [
                file for file, info in PAGE_DEFINITIONS.items()
                if info["section"] == section
            ]
    else:
        # Input is a section name
        section = input_value

        # Get all pages in this section
        section_pages = [
            file for file, info in PAGE_DEFINITIONS.items()
            if info["section"] == section
        ]

    if not section_pages:
        return  # No other pages in section

    # Create navigation UI
    # Auto-load CSS styles
    apply_custom_navigation_css()

    # Handle different layout types
    if layout == "columns":
        # Original column-based layout
        num_cols = SECTION_LAYOUTS.get(section, 3)
        cols = st.columns(num_cols)
        for i, page_file in enumerate(section_pages):
            col_index = i % num_cols
            create_custom_page_link(page_file, cols[col_index], css_class)

    elif layout == "horizontal":
        # Horizontal layout with custom separator
        links_html = []
        for page_file in section_pages:
            page_info = PAGE_DEFINITIONS.get(page_file, {})
            title = page_info.get("title", page_file)

            # Generate URL
            base_url = get_app_base_url()
            page_name = convert_filename_to_streamlit_url(page_file)
            full_url = f"{base_url}/{page_name}"

            # Create link HTML
            link_html = f'<a href="{full_url}" target="_self" class="{css_class}">{title}</a>'
            links_html.append(link_html)

        # Join with separator and display
        navigation_html = separator.join(links_html)
        st.markdown(navigation_html, unsafe_allow_html=True)

    elif layout == "vertical":
        # Vertical layout - each link on new line
        for page_file in section_pages:
            page_info = PAGE_DEFINITIONS.get(page_file, {})
            title = page_info.get("title", page_file)

            # Generate URL
            base_url = get_app_base_url()
            page_name = convert_filename_to_streamlit_url(page_file)
            full_url = f"{base_url}/{page_name}"

            # Create and display link
            link_html = f'<a href="{full_url}" target="_self" class="{css_class}">{title}</a>'
            st.markdown(link_html, unsafe_allow_html=True)



def add_custom_navigation_links(
    input_value,
    css_class="custom-nav-link",
    layout="columns",                 # "columns" | "horizontal" | "vertical"
    separator=" | ",
    exclude_current=True,
    render=True,                      # NEW: default True => fully backward-compatible
):
    """
    Add custom navigation links for a section or page.

    Args:
        input_value: Page filename (e.g. "101TEG History.py") OR section name (e.g. "History")
        css_class: CSS class for anchor elements
        layout: "columns" | "horizontal" | "vertical"
        separator: used for horizontal layout
        exclude_current: exclude current page when input_value is a page
        render: if True (default), writes to the Streamlit app (backward-compatible behaviour).
                if False, returns content:
                    - "horizontal"/"vertical": returns one HTML string
                    - "columns": returns List[List[str]] (each inner list = links for that column)
    Returns:
        None (when render=True)
        str (HTML) for horizontal/vertical when render=False
        List[List[str]] for columns when render=False
        "" if nothing to render
    """
    # --- Determine section & pages -------------------------------------------
    if isinstance(input_value, str) and input_value.endswith(".py"):
        current_page_file = os.path.basename(input_value)
        current_page_info = PAGE_DEFINITIONS.get(current_page_file)
        if not current_page_info:
            return "" if not render else None
        section = current_page_info["section"]

        if exclude_current:
            section_pages = [
                file for file, info in PAGE_DEFINITIONS.items()
                if info["section"] == section and file != current_page_file
            ]
        else:
            section_pages = [
                file for file, info in PAGE_DEFINITIONS.items()
                if info["section"] == section
            ]
    else:
        section = input_value
        section_pages = [
            file for file, info in PAGE_DEFINITIONS.items()
            if info["section"] == section
        ]

    if not section_pages:
        return "" if not render else None

    # --- Ensure CSS is present (safe to no-op if already applied) ------------
    apply_custom_navigation_css()

    # --- Helpers --------------------------------------------------------------
    def _link_html(page_file: str) -> str:
        page_info = PAGE_DEFINITIONS.get(page_file, {})
        title = page_info.get("title", page_file)
        base_url = get_app_base_url()
        page_name = convert_filename_to_streamlit_url(page_file)
        full_url = f"{base_url}/{page_name}"
        return f'<a href="{full_url}" target="_self" class="{css_class}">{title}</a>'

    # --- Layouts --------------------------------------------------------------
    if layout == "horizontal":
        links_html = [_link_html(pf) for pf in section_pages]
        navigation_html = separator.join(links_html)
        if render:
            st.markdown(navigation_html, unsafe_allow_html=True)
            return None
        else:
            return navigation_html

    elif layout == "vertical":
        links_html = [_link_html(pf) for pf in section_pages]
        navigation_html = "<br/>".join(links_html)
        if render:
            st.markdown(navigation_html, unsafe_allow_html=True)
            return None
        else:
            return navigation_html

    elif layout == "columns":
        num_cols = SECTION_LAYOUTS.get(section, 3)
        if render:
            cols = st.columns(num_cols)
            for i, page_file in enumerate(section_pages):
                col_index = i % num_cols
                # your original renderer
                create_custom_page_link(page_file, cols[col_index], css_class)
            return None
        else:
            # return data structure the caller can place as they wish
            cols_data = [[] for _ in range(num_cols)]
            for i, page_file in enumerate(section_pages):
                col_index = i % num_cols
                cols_data[col_index].append(_link_html(page_file))
            return cols_data

    else:
        raise ValueError(f"Unknown layout: {layout!r}")


def add_section_navigation_links(
    input_value=None,
    css_class="custom-nav-link",
    layout="columns",                 # "columns" | "horizontal" | "vertical"
    separator=" | ",
    exclude_current=True,
    exclude_data=True,
    render=True,
):
    """
    Add navigation links to sections (each link goes to the first page in that section).

    Args:
        input_value: Page filename (e.g. "__file__") to determine current page for exclusion
        css_class: CSS class for anchor elements
        layout: "columns" | "horizontal" | "vertical"
        separator: used for horizontal layout
        exclude_current: exclude current page's section from the links
        exclude_data: exclude "Data" section from the links (default True)
        render: if True (default), writes to the Streamlit app (backward-compatible behaviour).
                if False, returns content:
                    - "horizontal"/"vertical": returns one HTML string
                    - "columns": returns List[List[str]] (each inner list = links for that column)
    Returns:
        None (when render=True)
        str (HTML) for horizontal/vertical when render=False
        List[List[str]] for columns when render=False
        "" if nothing to render
    """
    # --- Get all sections and their first pages ---
    sections_data = {}
    # Preserve the order from PAGE_DEFINITIONS (don't sort alphabetically)
    for filename, page_info in PAGE_DEFINITIONS.items():
        section = page_info["section"]
        if section not in sections_data:
            sections_data[section] = []
        sections_data[section].append(filename)

    # Pages are already in definition order, so first page is sections_data[section][0]

    # --- Handle exclusions ---
    # Exclude Data section if requested
    if exclude_data and "Data" in sections_data:
        del sections_data["Data"]

    # Exclude current page's section if requested
    if exclude_current and input_value:
        try:
            # Extract just the filename from potentially full path
            current_page_file = os.path.basename(input_value)
            current_page_info = PAGE_DEFINITIONS.get(current_page_file)
            if current_page_info:
                current_section = current_page_info["section"]
                if current_section in sections_data:
                    del sections_data[current_section]
        except:
            # If we can't determine current page, continue without exclusion
            pass

    if not sections_data:
        return "" if not render else None

    # --- Create section links data ---
    section_links = []

    # Get sections in order using SECTION_CONFIG
    section_order = []
    for section in sections_data.keys():
        section_config = SECTION_CONFIG.get(section, {})
        order = section_config.get("order", 999)
        section_order.append((order, section))

    section_order.sort(key=lambda x: x[0])

    # Build links for each section
    for order, section in section_order:
        first_page = sections_data[section][0]  # First page in sorted order
        section_config = SECTION_CONFIG.get(section, {})
        display_name = section_config.get("display_name", section)

        section_links.append((first_page, display_name))

    if not section_links:
        return "" if not render else None

    # --- Ensure CSS is present ---
    apply_custom_navigation_css()

    # --- Helper function ---
    def _section_link_html(page_file: str, section_title: str) -> str:
        base_url = get_app_base_url()
        page_name = convert_filename_to_streamlit_url(page_file)
        full_url = f"{base_url}/{page_name}"
        return f'<a href="{full_url}" target="_self" class="{css_class}">{section_title}</a>'

    # --- Layouts ---
    if layout == "horizontal":
        links_html = [_section_link_html(pf, title) for pf, title in section_links]
        navigation_html = separator.join(links_html)
        if render:
            st.markdown(navigation_html, unsafe_allow_html=True)
            return None
        else:
            return navigation_html

    elif layout == "vertical":
        links_html = [_section_link_html(pf, title) for pf, title in section_links]
        navigation_html = "<br/>".join(links_html)
        if render:
            st.markdown(navigation_html, unsafe_allow_html=True)
            return None
        else:
            return navigation_html

    elif layout == "columns":
        # Use 3 columns as default for sections (fewer items than pages typically)
        num_cols = min(3, len(section_links))
        if render:
            cols = st.columns(num_cols)
            for i, (page_file, section_title) in enumerate(section_links):
                col_index = i % num_cols
                # Create the link directly in the column
                link_html = _section_link_html(page_file, section_title)
                cols[col_index].markdown(link_html, unsafe_allow_html=True)
            return None
        else:
            # return data structure the caller can place as they wish
            cols_data = [[] for _ in range(num_cols)]
            for i, (page_file, section_title) in enumerate(section_links):
                col_index = i % num_cols
                cols_data[col_index].append(_section_link_html(page_file, section_title))
            return cols_data

    else:
        raise ValueError(f"Unknown layout: {layout!r}")


def create_custom_navigation_section(section_name, pages, current_page, container_class="nav-section"):
    """Create a fully custom navigation section with advanced HTML structure"""
    base_url = get_app_base_url()

    # Filter out current page
    filtered_pages = [p for p in pages if p != current_page]
    if not filtered_pages:
        return ""

    # Create custom HTML structure
    nav_html = f'<div class="{container_class}" data-section="{section_name}">'
    nav_html += f'<h4 class="nav-section-title">{section_name}</h4>'
    nav_html += '<div class="nav-links">'

    for page_file in filtered_pages:
        page_info = PAGE_DEFINITIONS.get(page_file, {})
        title = page_info.get("title", page_file)
        icon = page_info.get("icon", "")
        label = f"{icon} {title}".strip() if icon else title

        # Convert filename to URL format (Streamlit strips leading numbers)
        page_name = convert_filename_to_streamlit_url(page_file)
        full_url = f"{base_url}/{page_name}"

        nav_html += f'''
        <a href="{full_url}"
           target="_self"
           class="nav-link"
           data-page="{page_file}"
           title="{title}">
           {label}
        </a>
        '''

    nav_html += '</div></div>'
    return nav_html


def apply_custom_navigation_css():
    """
    Load and apply CSS styles from the external navigation.css file.
    """
    import os
    from pathlib import Path

    # Get the path to the CSS file
    css_file_path = Path(__file__).parent / "styles" / "navigation.css"

    try:
        with open(css_file_path, 'r', encoding='utf-8') as f:
            css_content = f.read()

        # Apply the CSS
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
        return
    except FileNotFoundError:
        # Fallback: basic inline CSS if file doesn't exist
        pass

    # Fallback CSS if file doesn't exist
    fallback_css = """
    <style>
    .custom-nav-link {
        font-family: inherit;
        font-size: 1rem;
        color: #1e90ff;
        padding: 0.75rem 1.25rem;
        text-decoration: none !important;
        display: inline-block;
    }
    .custom-nav-link:hover {
        color: #0066cc;
        text-decoration: none !important;
    }
    </style>
    """
    st.markdown(fallback_css, unsafe_allow_html=True)
