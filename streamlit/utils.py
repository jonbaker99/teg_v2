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
from utils_statistical_analysis import add_ranks
from utils_data_processing import add_cumulative_scores, aggregate_data, read_file
from utils_data_management import exclude_incomplete_tegs_function
from utils_helper_utilities import get_current_branch
from utils_data_retrieval import load_all_data

#print("utils module is being imported")

# Configure Logging
#logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)




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
HANDICAPS_CSV = "data/handicaps.csv"
ROUND_INFO_CSV = "data/round_info.csv"

# This is a mirrored version of the main data file, useful for ad-hoc analysis.
ALL_DATA_CSV_MIRROR = "data/all-data.csv"


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


TEG_ROUNDS = {
    'TEG 1': 1,
    'TEG 2': 3,
    # Add more TEGs if necessary
}

TEGNUM_ROUNDS = {
    1: 1,
    2: 3,
    # Add more TEGs if necessary
}















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














from typing import List
import pandas as pd










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
    chosen_teg_context[measure] = chosen_teg_context[measure].astype(int)
    return chosen_teg_context




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
        df = load_all_data(exclude_teg_50=True)

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




### CONVERT TROPHY NAMES BETWEEN SHORT VERSIONS AND FULL NAMES

# short -> long
TROPHY_NAME_LOOKUPS_SHORTLONG = {
    "trophy": "TEG Trophy",
    "jacket": "Green Jacket",
    "spoon": "HMM Wooden Spoon",
}

# long -> short (keys normalised to lowercase for case-insensitive input)
TROPHY_NAME_LOOKUPS_LONGSHORT = {v.lower(): k for k, v in TROPHY_NAME_LOOKUPS_SHORTLONG.items()}


