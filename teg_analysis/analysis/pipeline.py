"""Data processing pipeline and cache management functions.

This module provides the main data processing pipeline used for updates,
including cache generation for streaks, bestball, and commentary summaries.
"""


import logging
import pandas as pd
import os
from typing import List

try:
    import streamlit as st
    # _st_cache_data will be called as a function, not accessed as attribute
    if hasattr(st, 'cache_data'):
        _st_cache_data = st.cache_data
    else:
        # Fallback for older streamlit versions
        def _st_cache_data(func):
            return func
except ImportError:
    st = None
    # Define a no-op decorator if streamlit isn't available
    def _st_cache_data(func):
        return func

logger = logging.getLogger(__name__)


def _get_constants():
    """Get constants from utils.py to avoid circular imports."""
    from streamlit.utils import (STREAKS_PARQUET, BESTBALL_PARQUET,
        ROUND_INFO_CSV, COMMENTARY_ROUND_EVENTS_PARQUET,
        COMMENTARY_ROUND_SUMMARY_PARQUET, COMMENTARY_TOURNAMENT_SUMMARY_PARQUET,
        COMMENTARY_ROUND_STREAKS_PARQUET, COMMENTARY_TOURNAMENT_STREAKS_PARQUET)
    return locals()


def _get_deps():
    """Get function dependencies to avoid circular imports."""
    from teg_analysis.core.data_loader import load_all_data, read_file, write_file
    from teg_analysis.analysis.streaks import build_streaks
    from teg_analysis.analysis.commentary import (create_round_events, create_round_summary,
        create_tournament_summary, create_round_streaks_summary, create_tournament_streaks_summary)
    from streamlit.utils import clear_all_caches, add_cumulative_scores, add_rankings_and_gaps
    return locals()


def update_streaks_cache(defer_github: bool = False):
    """
    Update the streaks cache file with current streak calculations.

    Args:
        defer_github (bool): If True, defer GitHub push for batch commit

    Returns:
        dict: File info if defer_github=True, None otherwise

    This function:
    1. Loads all data (including incomplete TEGs)
    2. Calls build_streaks() to calculate streak data
    3. Saves result to streaks.parquet
    4. Clears streamlit cache

    Called whenever source data changes (data updates, deletions).
    """
    try:
        logger.info("Updating streaks cache file")

        # Get dependencies and constants
        deps = _get_deps()
        consts = _get_constants()
        load_all_data = deps['load_all_data']
        write_file = deps['write_file']
        clear_all_caches = deps['clear_all_caches']
        build_streaks = deps['build_streaks']
        STREAKS_PARQUET = consts['STREAKS_PARQUET']

        # Load all data including incomplete TEGs for streak calculations
        try:
            logger.info("Loading all data for streak calculation...")
            all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
            logger.info(f"Loaded {len(all_data)} rows of data")
        except Exception as e:
            raise Exception(f"Failed to load all data: {e}")

        if all_data.empty:
            logger.warning("No data available for streak calculation")
            return None

        # Calculate streaks using the build_streaks function
        try:
            logger.info("Calculating streaks...")
            streaks_df = build_streaks(all_data)
            logger.info(f"Calculated {len(streaks_df)} streak records")
        except Exception as e:
            raise Exception(f"Failed to calculate streaks: {e}")

        # Save to streaks parquet file
        try:
            file_info = write_file(STREAKS_PARQUET, streaks_df, "Update streaks cache", defer_github=defer_github)
            logger.info(f"Streaks cache updated successfully: {STREAKS_PARQUET}")
        except Exception as e:
            raise Exception(f"Failed to write streaks cache: {e}")

        # Clear streamlit cache to ensure fresh data on next load (only if not deferred)
        if not defer_github:
            clear_all_caches()

        logger.info("Streaks cache update completed successfully")
        return file_info

    except Exception as e:
        logger.error(f"Error updating streaks cache: {e}", exc_info=True)
        error_msg = f"Failed to update streaks cache: {e}"
        logger.error(error_msg)

        # Show error in UI
        try:
            st.error(error_msg)
        except:
            # If streamlit context not available (e.g. running from script)
            print(f"ERROR: {error_msg}")

        return None


def update_bestball_cache(defer_github: bool = False):
    """
    Update the bestball/worstball cache file.

    Args:
        defer_github (bool): If True, defer GitHub push for batch commit

    Returns:
        dict: File info if defer_github=True, None otherwise

    This function:
    1. Loads all data (including incomplete TEGs)
    2. Calculates bestball scores
    3. Calculates worstball scores
    4. Combines them and saves to bestball.parquet
    """
    try:
        # Get dependencies and constants
        deps = _get_deps()
        consts = _get_constants()
        load_all_data = deps['load_all_data']
        write_file = deps['write_file']
        BESTBALL_PARQUET = consts['BESTBALL_PARQUET']

        # Import bestball processing functions (keep from helpers for now)
        from helpers.bestball_processing import prepare_bestball_data, calculate_bestball_scores, calculate_worstball_scores

        # Load all data including incomplete TEGs for up-to-date analysis
        all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

        if all_data.empty:
            logger.warning("No data available for bestball calculation")
            return None

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
        file_info = write_file(BESTBALL_PARQUET, combined_df, "Update bestball/worstball cache", defer_github=defer_github)
        logger.info(f"Bestball/worstball cache updated successfully: {BESTBALL_PARQUET}")

        return file_info

    except Exception as e:
        logger.error(f"Error updating bestball cache: {e}")
        st.error(f"Failed to update bestball cache: {e}")
        return None

def update_commentary_caches(defer_github: bool = False):
    """
    Update the commentary cache files with current event and summary data.

    Args:
        defer_github (bool): If True, defer GitHub push for batch commit

    Returns:
        list: List of file infos if defer_github=True, None otherwise

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

        # Get dependencies and constants
        deps = _get_deps()
        consts = _get_constants()
        load_all_data = deps['load_all_data']
        read_file = deps['read_file']
        write_file = deps['write_file']
        clear_all_caches = deps['clear_all_caches']
        create_round_events = deps['create_round_events']
        create_round_summary = deps['create_round_summary']
        create_tournament_summary = deps['create_tournament_summary']
        create_round_streaks_summary = deps['create_round_streaks_summary']
        create_tournament_streaks_summary = deps['create_tournament_streaks_summary']
        ROUND_INFO_CSV = consts['ROUND_INFO_CSV']
        STREAKS_PARQUET = consts['STREAKS_PARQUET']
        COMMENTARY_ROUND_EVENTS_PARQUET = consts['COMMENTARY_ROUND_EVENTS_PARQUET']
        COMMENTARY_ROUND_SUMMARY_PARQUET = consts['COMMENTARY_ROUND_SUMMARY_PARQUET']
        COMMENTARY_TOURNAMENT_SUMMARY_PARQUET = consts['COMMENTARY_TOURNAMENT_SUMMARY_PARQUET']
        COMMENTARY_ROUND_STREAKS_PARQUET = consts['COMMENTARY_ROUND_STREAKS_PARQUET']
        COMMENTARY_TOURNAMENT_STREAKS_PARQUET = consts['COMMENTARY_TOURNAMENT_STREAKS_PARQUET']

        file_infos = []

        # Load all data including incomplete TEGs for commentary
        try:
            logger.info("Loading all data for commentary generation...")
            all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
            logger.info(f"Loaded {len(all_data)} rows of data")
        except Exception as e:
            raise Exception(f"Failed to load all data: {e}")

        if all_data.empty:
            logger.warning("No data available for commentary generation")
            return None

        # Load round info and streaks data
        try:
            logger.info("Loading round info and streaks data...")
            round_info = read_file(ROUND_INFO_CSV)
            streaks_df = read_file(STREAKS_PARQUET)
            logger.info(f"Loaded {len(round_info)} round info records and {len(streaks_df)} streak records")
        except Exception as e:
            raise Exception(f"Failed to load round info or streaks data: {e}")

        # Generate round events
        try:
            logger.info("Generating round events...")
            events_df = create_round_events(all_data_df=all_data)
            logger.info(f"Generated {len(events_df)} round events")
            file_info = write_file(COMMENTARY_ROUND_EVENTS_PARQUET, events_df, "Update commentary round events cache", defer_github=defer_github)
            if file_info:
                file_infos.append(file_info)
            logger.info(f"Round events cache updated: {COMMENTARY_ROUND_EVENTS_PARQUET}")
        except Exception as e:
            raise Exception(f"Failed to generate/write round events: {e}")

        # Generate round summary
        try:
            logger.info("Generating round summary...")
            round_summary_df = create_round_summary(all_data_df=all_data, round_info_df=round_info)
            logger.info(f"Generated {len(round_summary_df)} round summary records")
            file_info = write_file(COMMENTARY_ROUND_SUMMARY_PARQUET, round_summary_df, "Update commentary round summary cache", defer_github=defer_github)
            if file_info:
                file_infos.append(file_info)
            logger.info(f"Round summary cache updated: {COMMENTARY_ROUND_SUMMARY_PARQUET}")
        except Exception as e:
            raise Exception(f"Failed to generate/write round summary: {e}")

        # Generate tournament summary
        try:
            logger.info("Generating tournament summary...")
            tournament_summary_df = create_tournament_summary(all_data_df=all_data, round_info_df=round_info)
            logger.info(f"Generated {len(tournament_summary_df)} tournament summary records")
            file_info = write_file(COMMENTARY_TOURNAMENT_SUMMARY_PARQUET, tournament_summary_df, "Update commentary tournament summary cache", defer_github=defer_github)
            if file_info:
                file_infos.append(file_info)
            logger.info(f"Tournament summary cache updated: {COMMENTARY_TOURNAMENT_SUMMARY_PARQUET}")
        except Exception as e:
            raise Exception(f"Failed to generate/write tournament summary: {e}")

        # Generate round streaks summary
        try:
            logger.info("Generating round streaks summary...")
            round_streaks_df = create_round_streaks_summary(all_data_df=all_data, streaks_df=streaks_df)
            logger.info(f"Generated {len(round_streaks_df)} round streak records")
            file_info = write_file(COMMENTARY_ROUND_STREAKS_PARQUET, round_streaks_df, "Update commentary round streaks cache", defer_github=defer_github)
            if file_info:
                file_infos.append(file_info)
            logger.info(f"Round streaks cache updated: {COMMENTARY_ROUND_STREAKS_PARQUET}")
        except Exception as e:
            raise Exception(f"Failed to generate/write round streaks: {e}")

        # Generate tournament streaks summary
        try:
            logger.info("Generating tournament streaks summary...")
            tournament_streaks_df = create_tournament_streaks_summary(all_data_df=all_data, streaks_df=streaks_df)
            logger.info(f"Generated {len(tournament_streaks_df)} tournament streak records")
            file_info = write_file(COMMENTARY_TOURNAMENT_STREAKS_PARQUET, tournament_streaks_df, "Update commentary tournament streaks cache", defer_github=defer_github)
            if file_info:
                file_infos.append(file_info)
            logger.info(f"Tournament streaks cache updated: {COMMENTARY_TOURNAMENT_STREAKS_PARQUET}")
        except Exception as e:
            raise Exception(f"Failed to generate/write tournament streaks: {e}")

        # Clear streamlit cache to ensure fresh data on next load (only if not deferred)
        if not defer_github:
            clear_all_caches()

        logger.info("Commentary cache files updated successfully")

        return file_infos if defer_github else None

    except Exception as e:
        logger.error(f"Error updating commentary caches: {e}", exc_info=True)
        error_msg = f"Failed to update commentary caches: {e}"
        logger.error(error_msg)

        # Show error in UI
        try:
            st.error(error_msg)
        except:
            # If streamlit context not available (e.g. running from script)
            print(f"ERROR: {error_msg}")

        return None


def get_google_sheet(sheet_name: str, worksheet_name: str) -> pd.DataFrame:
    """
    Load data from a specified Google Sheet and worksheet using credentials from
    Railway environment variables or Streamlit secrets.
    """
    logger.info(f"Fetching data from Google Sheet: {sheet_name}, Worksheet: {worksheet_name}")

    # Import google dependencies
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as e:
        logger.error(f"Failed to import google dependencies: {e}")
        raise

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


@_st_cache_data
def load_and_prepare_handicap_data(file_path: str) -> pd.DataFrame:
    """
    Load and prepare handicap data from a CSV file.

    Parameters:
        file_path (str): Path to the handicap CSV file.

    Returns:
        pd.DataFrame: Melted and cleaned handicap DataFrame.
    """
    logger.info(f"Loading handicap data from {file_path}")
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import read_file
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

    # Import dependencies
    from teg_analysis.core.data_loader import read_file
    consts = _get_constants()
    ROUND_INFO_CSV = consts['ROUND_INFO_CSV']

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


def update_all_data(csv_file: str, parquet_file: str, csv_output_file: str, defer_github: bool = False):
    """
    Load data from a CSV file, apply cumulative scores and averages, and save it as both a Parquet file and a CSV file.

    Parameters:
        csv_file (str): Path to the input CSV file.
        parquet_file (str): Path to the output Parquet file.
        csv_output_file (str): Path to the output CSV file for review.
        defer_github (bool): If True, defer GitHub push for batch commit

    Returns:
        list: List of file infos if defer_github=True, None otherwise
    """
    logger.info(f"Updating all data from {csv_file} to {parquet_file} and {csv_output_file}")

    # Get dependencies
    deps = _get_deps()
    read_file = deps['read_file']
    write_file = deps['write_file']
    add_cumulative_scores = deps['add_cumulative_scores']
    add_rankings_and_gaps = deps['add_rankings_and_gaps']

    file_infos = []

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
    file_info = write_file(parquet_file, df_transformed, "Update all-data parquet", defer_github=defer_github)
    if file_info:
        file_infos.append(file_info)

    # Save the transformed dataframe to a CSV file for manual review
    file_info = write_file(csv_output_file, df_transformed, "Update all-data CSV", defer_github=defer_github)
    if file_info:
        file_infos.append(file_info)
    logger.info(f"Transformed data saved to {csv_output_file}")

    if not defer_github:
        st.cache_data.clear()
        st.success("✅ Cache cleared")

    return file_infos if defer_github else None

# ============================================================================
"""Data processing functions for TEG data update operations.

This module provides functions for processing and validating Google Sheets data,
checking for duplicate data, managing the data update workflow state, and
ensuring data integrity.
"""


import streamlit as st
import pandas as pd
import logging
from utils import (
    reshape_round_data,
    read_file,
    write_file,
    process_round_for_all_scores,
    load_and_prepare_handicap_data,
    update_all_data,
    update_streaks_cache,
    update_commentary_caches,
    update_bestball_cache,
    summarise_existing_rd_data,
    update_teg_status_files,
    clear_all_caches,
    clear_volume_cache,
    ALL_SCORES_PARQUET,
    HANDICAPS_CSV,
    ALL_DATA_PARQUET,
    ALL_DATA_CSV_MIRROR
)

# Configure logging
logger = logging.getLogger(__name__)

# State constants for the update workflow
STATE_INITIAL = "initial"
STATE_DATA_LOADED = "data_loaded" 
STATE_PROCESSING = "processing"
STATE_OVERWRITE_CONFIRM = "overwrite_confirm"


def initialize_update_state(force_reset: bool = False):
    """Initializes or resets the session state for the data update page.

    This function manages the multi-step data update workflow using Streamlit
    session state to ensure a clean state between different update operations.

    Args:
        force_reset (bool, optional): If True, forces a reset of all state
            variables. Defaults to False.
    """
    if force_reset or 'page_state' not in st.session_state:
        st.session_state.page_state = STATE_INITIAL
        st.session_state.new_data_df = None
        st.session_state.existing_data_df = None
        st.session_state.duplicates_df = None


def process_google_sheets_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Processes and validates data loaded from Google Sheets.

    This function transforms wide-format Google Sheets data into a long format,
    filters out incomplete rounds and invalid scores, and ensures data quality
    before further processing.

    Args:
        raw_df (pd.DataFrame): The raw data from Google Sheets.

    Returns:
        pd.DataFrame: The processed data containing only complete 18-hole
        rounds.
    """
    # reshape_round_data() - Converts wide format to long format by hole
    long_df = reshape_round_data(raw_df, ['TEGNum', 'Round', 'Hole', 'Par', 'SI'])
    
    # Remove invalid scores (NaN or 0)
    long_df = long_df.dropna(subset=['Score'])[long_df['Score'] != 0]
    
    # Filter to only include complete 18-hole rounds
    # Ensures data integrity by rejecting incomplete scorecards
    rounds_with_18_holes = long_df.groupby(['TEGNum', 'Round', 'Pl']).filter(lambda x: len(x) == 18)
    
    return rounds_with_18_holes


def check_for_duplicate_data() -> bool:
    """Checks for duplicate data at the hole level.

    This function compares the new data with existing data to identify any
    duplicate entries at the hole level.

    Returns:
        bool: True if duplicates are found, False otherwise.
    """
    try:
        st.session_state.existing_data_df = read_file(ALL_SCORES_PARQUET)
    except FileNotFoundError:
        st.session_state.existing_data_df = pd.DataFrame(columns=['TEGNum', 'Round', 'Hole', 'Pl'])

    # Create hole-level keys for comparison (TEG, Round, Hole, Player)
    new_data_keys = st.session_state.new_data_df[['TEGNum', 'Round', 'Hole', 'Pl']].drop_duplicates()

    # Ensure NUMERIC types for both dataframes
    if not st.session_state.existing_data_df.empty:
        st.session_state.existing_data_df['TEGNum'] = pd.to_numeric(st.session_state.existing_data_df['TEGNum'])
        st.session_state.existing_data_df['Round'] = pd.to_numeric(st.session_state.existing_data_df['Round'])
        st.session_state.existing_data_df['Hole'] = pd.to_numeric(st.session_state.existing_data_df['Hole'])

    new_data_keys['TEGNum'] = pd.to_numeric(new_data_keys['TEGNum'])
    new_data_keys['Round'] = pd.to_numeric(new_data_keys['Round'])
    new_data_keys['Hole'] = pd.to_numeric(new_data_keys['Hole'])

    # Find duplicates at hole level
    duplicates = st.session_state.existing_data_df.merge(
        new_data_keys,
        on=['TEGNum', 'Round', 'Hole', 'Pl'],
        how='inner'
    )

    # Store the actual duplicate keys (only records that exist in both datasets)
    duplicate_keys_only = duplicates[['TEGNum', 'Round', 'Hole', 'Pl']].drop_duplicates()

    st.session_state.duplicates_df = duplicates
    st.session_state.duplicate_keys_only = duplicate_keys_only
    st.session_state.all_new_data_keys = new_data_keys

    return not duplicates.empty


def analyze_hole_level_differences() -> tuple[pd.DataFrame, bool]:
    """Analyzes differences between existing and new data for duplicate records.

    This function compares the scores of duplicate records at the hole level
    to identify any discrepancies.

    Returns:
        tuple: A tuple containing:
            - differences_df (pd.DataFrame): A DataFrame showing the
              differences.
            - has_differences (bool): True if any differences were found,
              False otherwise.
    """
    if st.session_state.duplicates_df.empty:
        return pd.DataFrame(), False

    # Get the duplicate hole-level keys
    duplicate_keys = st.session_state.duplicates_df[['TEGNum', 'Round', 'Hole', 'Pl']].drop_duplicates()

    # Get existing scores for duplicate records
    existing_duplicates = st.session_state.existing_data_df.merge(
        duplicate_keys,
        on=['TEGNum', 'Round', 'Hole', 'Pl'],
        how='inner'
    )[['TEGNum', 'Round', 'Hole', 'Pl', 'Sc']].rename(columns={'Sc': 'Score_existing'})

    # Get new scores for duplicate records
    new_duplicates = st.session_state.new_data_df.merge(
        duplicate_keys,
        on=['TEGNum', 'Round', 'Hole', 'Pl'],
        how='inner'
    )[['TEGNum', 'Round', 'Hole', 'Pl', 'Score']].rename(columns={'Score': 'Score_new'})

    # Merge to compare scores
    comparison = existing_duplicates.merge(
        new_duplicates,
        on=['TEGNum', 'Round', 'Hole', 'Pl'],
        how='inner'
    )

    # Find rows where scores differ
    differences = comparison[comparison['Score_existing'] != comparison['Score_new']].copy()

    # Format for display with requested column names
    if not differences.empty:
        differences_display = differences[['Pl', 'TEGNum', 'Round', 'Hole', 'Score_existing', 'Score_new']].copy()
        differences_display.columns = ['Pl', 'TEG', 'Round', 'Hole', 'Score (existing)', 'Score (google sheets)']

        # Sort for easy reading
        differences_display = differences_display.sort_values(['TEG', 'Round', 'Pl', 'Hole'])

        return differences_display, True
    else:
        return pd.DataFrame(), False


def execute_data_update(overwrite: bool = False, new_data_only: bool = False):
    """Executes the main data update process.

    This is the core data processing function that handles the overwrite
    logic, processes raw rounds into calculated scoring data, updates the main
    data files, and triggers a cache refresh.

    Args:
        overwrite (bool, optional): Whether to overwrite existing duplicate
            data. Defaults to False.
        new_data_only (bool, optional): Whether to process only non-duplicate
            data. Defaults to False.
    """
    existing_df = st.session_state.existing_data_df
    new_data_df = st.session_state.new_data_df

    # Capture changed rounds for optional commentary generation
    # This doesn't affect the data update flow - errors are logged but don't block
    try:
        changed_rounds = new_data_df[['TEGNum', 'Round']].drop_duplicates()
        changed_rounds_dict = {}
        for _, row in changed_rounds.iterrows():
            teg = int(row['TEGNum'])
            round_num = int(row['Round'])
            if teg not in changed_rounds_dict:
                changed_rounds_dict[teg] = []
            changed_rounds_dict[teg].append(round_num)
        st.session_state.changed_rounds = changed_rounds_dict
        logger.info(f"Captured changed rounds: {changed_rounds_dict}")
    except Exception as e:
        logger.warning(f"Could not capture changed rounds for commentary: {e}")
        # Don't fail the data update if this fails

    if overwrite:
        # Remove existing data that will be replaced (using hole-level matching now)
        if hasattr(st.session_state, 'duplicate_keys_only') and not st.session_state.duplicate_keys_only.empty:
            duplicate_keys = st.session_state.duplicate_keys_only
            existing_df = existing_df.merge(duplicate_keys, on=['TEGNum', 'Round', 'Hole', 'Pl'], how='left', indicator=True)
            existing_df = existing_df[existing_df['_merge'] == 'left_only'].drop(columns=['_merge'])

    elif new_data_only:
        # Filter new data to exclude duplicates (process only non-duplicate data)
        if hasattr(st.session_state, 'duplicate_keys_only') and not st.session_state.duplicate_keys_only.empty:
            duplicate_keys = st.session_state.duplicate_keys_only
            # Remove duplicate records from new data, keeping only truly new records
            new_data_df = new_data_df.merge(duplicate_keys, on=['TEGNum', 'Round', 'Hole', 'Pl'], how='left', indicator=True)
            new_data_df = new_data_df[new_data_df['_merge'] == 'left_only'].drop(columns=['_merge'])

    # load_and_prepare_handicap_data() - Load player handicap data for scoring calculations
    hc_long = load_and_prepare_handicap_data(HANDICAPS_CSV)
    
    # process_round_for_all_scores() - Convert raw scores to calculated metrics (GrossVP, Stableford, etc.)
    processed_rounds = process_round_for_all_scores(new_data_df, hc_long)

    if not processed_rounds.empty:
        # Ensure consistent data types before combining datasets
        existing_df['TEGNum'] = pd.to_numeric(existing_df['TEGNum'])
        existing_df['Round'] = pd.to_numeric(existing_df['Round'])
        processed_rounds['TEGNum'] = pd.to_numeric(processed_rounds['TEGNum'])
        processed_rounds['Round'] = pd.to_numeric(processed_rounds['Round'])

        # Combine existing and new data
        final_df = pd.concat([existing_df, processed_rounds], ignore_index=True)

        # Collect all files for batch commit to GitHub
        import os
        batch_files = []
        is_railway = os.getenv('RAILWAY_ENVIRONMENT')

        # write_file() - Save updated dataset to main scores file
        file_info = write_file(ALL_SCORES_PARQUET, final_df, f"Updated data with {len(processed_rounds)} new records", defer_github=is_railway)
        if file_info:
            batch_files.append(file_info)
        st.success(f"✅ Updated data saved to {ALL_SCORES_PARQUET}.")

        # Update derivative datasets and clear caches
        with st.spinner("💾 Updating all-data..."):
            # update_all_data() - Regenerates master dataset with new records (returns file infos)
            update_files = update_all_data(ALL_SCORES_PARQUET, ALL_DATA_PARQUET, ALL_DATA_CSV_MIRROR, defer_github=is_railway)
            if update_files:
                batch_files.extend(update_files)
            st.success("💾 All-data updated and CSV created.")

        # CRITICAL: Clear Streamlit caches BEFORE regenerating dependent caches
        # This ensures that load_all_data() and other cached functions read the
        # freshly updated files rather than stale cached versions.
        # Previously this was at the end of the update process, causing commentary
        # and streaks caches to be built from old data.
        logger.info("Clearing Streamlit caches before cache regeneration...")
        st.cache_data.clear()
        clear_all_caches()
        logger.info("Caches cleared - dependent caches will now use fresh data")

        # Update TEG status files to reflect completion changes
        with st.spinner("📊 Updating TEG status files..."):
            status_files = update_teg_status_files(defer_github=is_railway)
            if status_files:
                batch_files.extend(status_files)
            st.success("📊 TEG status files updated.")

        # Update streaks cache with latest data
        with st.spinner("🏁 Updating streaks cache..."):
            try:
                streaks_file = update_streaks_cache(defer_github=is_railway)
                if streaks_file:
                    batch_files.append(streaks_file)
                    st.success("🏁 Streaks cache updated.")
                else:
                    st.error("❌ Streaks cache update returned None - check logs for errors")
                    logger.error("update_streaks_cache returned None - cache may not have been updated")
            except Exception as e:
                st.error(f"❌ Failed to update streaks cache: {e}")
                logger.error(f"Exception in update_streaks_cache: {e}", exc_info=True)
                # Continue with other updates even if streaks fails

        # Update commentary caches with latest data
        with st.spinner("📝 Updating commentary caches..."):
            try:
                commentary_files = update_commentary_caches(defer_github=is_railway)
                if commentary_files:
                    batch_files.extend(commentary_files)
                    st.success("📝 Commentary caches updated.")
                elif commentary_files is None:
                    st.error("❌ Commentary cache update failed - check logs for errors")
                    logger.error("update_commentary_caches returned None - caches may not have been updated")
                else:
                    # Empty list returned (valid for non-Railway)
                    st.success("📝 Commentary caches updated.")
            except Exception as e:
                st.error(f"❌ Failed to update commentary caches: {e}")
                logger.error(f"Exception in update_commentary_caches: {e}", exc_info=True)
                # Continue with other updates even if commentary fails

        # Update bestball cache with latest data
        with st.spinner("🏀 Updating bestball cache..."):
            try:
                bestball_file = update_bestball_cache(defer_github=is_railway)
                if bestball_file:
                    batch_files.append(bestball_file)
                    st.success("🏀 Bestball cache updated.")
                else:
                    st.error("❌ Bestball cache update returned None - check logs for errors")
                    logger.error("update_bestball_cache returned None - cache may not have been updated")
            except Exception as e:
                st.error(f"❌ Failed to update bestball cache: {e}")
                logger.error(f"Exception in update_bestball_cache: {e}", exc_info=True)
                # Continue with batch commit even if bestball fails

        # Batch commit all files to GitHub in single commit (Railway only)
        if is_railway and batch_files:
            with st.spinner(f"🚀 Pushing {len(batch_files)} files to GitHub..."):
                from utils import batch_commit_to_github
                batch_commit_to_github(batch_files, f"Data update: {len(processed_rounds)} new records + cache updates")
                st.success(f"🚀 Pushed {len(batch_files)} files to GitHub in single commit.")

        # DON'T clear Railway volume cache after updates!
        # The freshly written files (streaks, commentary, etc.) need to stay in the volume
        # so that report generation can read them immediately after the data update.
        # Previously this was clearing the volume AFTER writing new files, causing
        # report generation to fail because files were deleted from volume and
        # GitHub propagation hadn't completed yet.
        #
        # The volume cache will naturally refresh when GitHub is updated and files
        # are re-read on subsequent page loads.
        #
        # if is_railway:
        #     with st.spinner("🗑️ Clearing Railway volume cache..."):
        #         result = clear_volume_cache()
        #         logger.info(f"Volume cache clear result: {result}")
        #         st.success("🗑️ Volume cache cleared.")

        # Note: Streamlit caches were already cleared earlier (after all-data update)
        # to ensure cache regeneration used fresh data. No need to clear again here.
    else:
        st.warning("⚠️ No new records to append.")


def create_data_summary_display(new_data_df: pd.DataFrame) -> pd.DataFrame:
    """Creates a summary display of the loaded data for user confirmation.

    This function provides a clear summary view of the data that will be
    processed, allowing the user to verify that it is correct before
    proceeding.

    Args:
        new_data_df (pd.DataFrame): The newly loaded data.

    Returns:
        pd.DataFrame: A pivot table showing scores by player and round.
    """
    # Group by key dimensions and sum scores for overview
    summary_df = new_data_df.groupby(['TEGNum', 'Round', 'Pl'])['Score'].sum().reset_index()
    
    # Create pivot table for easy visual verification
    summary_pivot = summary_df.pivot(index='Pl', columns=['Round', 'TEGNum'], values='Score').fillna('-')
    
    return summary_pivot


# === SECTION DIVIDER ===

"""Data processing functions for tournament data deletion operations.

This module provides functions for managing the data deletion workflow,
including state management, data backups, and safe data deletion with
validation.
"""


import streamlit as st
import pandas as pd
from datetime import datetime
from utils import read_file, write_file, backup_file, clear_all_caches, update_teg_status_files, update_streaks_cache, update_commentary_caches, update_bestball_cache


# State constants for deletion workflow
STATE_INITIAL = "initial"
STATE_PREVIEW = "preview" 
STATE_CONFIRMED = "confirmed"


def initialize_deletion_state(force_reset: bool = False):
    """Initializes or resets the session state for the data deletion workflow.

    This function manages the multi-step data deletion process using session
    state to ensure a clean state between operations and prevent accidental
    data loss.

    Args:
        force_reset (bool, optional): If True, forces a reset of all state
            variables. Defaults to False.
    """
    if force_reset or 'delete_page_state' not in st.session_state:
        st.session_state.delete_page_state = STATE_INITIAL
        st.session_state.scores_df = None
        st.session_state.selected_teg = None
        st.session_state.selected_rounds = []


def load_scores_data():
    """Loads tournament scores data into the session state.

    This function loads the main scores dataset for deletion operations and
    uses the session state to avoid repeated file reads.
    """
    from utils import ALL_SCORES_PARQUET
    
    st.session_state.scores_df = read_file(ALL_SCORES_PARQUET)


def get_available_tegs_and_rounds(scores_df: pd.DataFrame) -> tuple[list, callable]:
    """Gets the available TEGs and their rounds for selection.

    This function provides the available options for data deletion, ordering
    the TEGs in reverse chronological order and enabling dynamic round
    selection based on the chosen TEG.

    Args:
        scores_df (pd.DataFrame): The tournament scores data.

    Returns:
        tuple: A tuple containing:
            - teg_nums (list): A list of available TEG numbers.
            - get_rounds_for_teg (callable): A function that returns the
              available rounds for a given TEG.
    """
    teg_nums = sorted(scores_df['TEGNum'].unique(), reverse=True)
    
    def get_rounds_for_teg(selected_teg):
        """Get available rounds for a specific TEG."""
        return sorted(scores_df[scores_df['TEGNum'] == selected_teg]['Round'].unique())
    
    return teg_nums, get_rounds_for_teg


def create_timestamped_backups() -> tuple[str, str]:
    """Creates timestamped backups of the main data files before deletion.

    This function creates safety backups before any data deletion operation,
    using timestamps to ensure unique filenames and provide a recovery path.

    Returns:
        tuple: A tuple containing the paths to the backed-up scores and data
        files.
    """
    from utils import ALL_SCORES_PARQUET, ALL_DATA_PARQUET
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create backup file paths in backups directory
    scores_backup_path = f"data/backups/all_scores_backup_{timestamp}.parquet"
    backup_file(ALL_SCORES_PARQUET, scores_backup_path)
    
    data_backup_path = f"data/backups/all_data_backup_{timestamp}.parquet"
    backup_file(ALL_DATA_PARQUET, data_backup_path)
    
    return scores_backup_path, data_backup_path


def preview_deletion_data(scores_df: pd.DataFrame, selected_teg: int, selected_rounds: list) -> pd.DataFrame:
    """Creates a preview of the data that will be deleted.

    This function shows the user exactly what data will be removed before
    confirmation, providing a final safety check before an irreversible
    operation.

    Args:
        scores_df (pd.DataFrame): The tournament scores data.
        selected_teg (int): The selected TEG number.
        selected_rounds (list): The selected round numbers.

    Returns:
        pd.DataFrame: A DataFrame containing the rows that will be deleted.
    """
    deletion_filter = (
        (scores_df['TEGNum'] == selected_teg) & 
        (scores_df['Round'].isin(selected_rounds))
    )
    
    scores_to_delete = scores_df[deletion_filter]
    
    return scores_to_delete


def execute_data_deletion(selected_teg: int, selected_rounds: list):
    """Executes the complete data deletion workflow.

    This function performs the entire deletion process, including creating
    backups, filtering the data, removing the selected data from all relevant
    files, updating the CSV mirror, and clearing caches.

    Args:
        selected_teg (int): The TEG number to delete.
        selected_rounds (list): The round numbers to delete.
    """
    from utils import ALL_SCORES_PARQUET, ALL_DATA_PARQUET, ALL_DATA_CSV_MIRROR
    
    # Create safety backups first
    scores_backup_path, data_backup_path = create_timestamped_backups()
    st.info(f"Backups created:\\n- {scores_backup_path}\\n- {data_backup_path}")

    # Load both main data files
    scores_df = st.session_state.scores_df
    
    try:
        data_df = read_file(ALL_DATA_PARQUET)
    except Exception as e:
        st.error(f"Error reading ALL_DATA_PARQUET: {e}")
        return

    # Create deletion filter
    deletion_filter = (
        (scores_df['TEGNum'] == selected_teg) & 
        (scores_df['Round'].isin(selected_rounds))
    )
    
    # Remove selected data from both datasets
    filtered_scores_df = scores_df[~deletion_filter]
    filtered_data_df = data_df[~((data_df['TEGNum'] == selected_teg) & (data_df['Round'].isin(selected_rounds)))]

    # Collect all files for batch commit to GitHub
    import os
    batch_files = []
    is_railway = os.getenv('RAILWAY_ENVIRONMENT')

    # Update all data files with filtered data
    deletion_message = f"Deleted TEG {selected_teg}, Rounds {selected_rounds}"
    file_info = write_file(ALL_SCORES_PARQUET, filtered_scores_df, deletion_message, defer_github=is_railway)
    if file_info:
        batch_files.append(file_info)

    file_info = write_file(ALL_DATA_PARQUET, filtered_data_df, deletion_message, defer_github=is_railway)
    if file_info:
        batch_files.append(file_info)

    # Recreate CSV mirror from updated parquet data
    file_info = write_file(ALL_DATA_CSV_MIRROR, filtered_data_df, f"Recreated CSV mirror after deletion", defer_github=is_railway)
    if file_info:
        batch_files.append(file_info)

    # Update TEG status files to reflect completion changes
    status_files = update_teg_status_files(defer_github=is_railway)
    if status_files:
        batch_files.extend(status_files)

    # Update streaks cache with latest data
    streaks_file = update_streaks_cache(defer_github=is_railway)
    if streaks_file:
        batch_files.append(streaks_file)

    # Update commentary caches with latest data
    commentary_files = update_commentary_caches(defer_github=is_railway)
    if commentary_files:
        batch_files.extend(commentary_files)

    # Update bestball cache with latest data
    bestball_file = update_bestball_cache(defer_github=is_railway)
    if bestball_file:
        batch_files.append(bestball_file)

    # Batch commit all files to GitHub in single commit (Railway only)
    if is_railway and batch_files:
        with st.spinner(f"🚀 Pushing {len(batch_files)} files to GitHub..."):
            from utils import batch_commit_to_github
            batch_commit_to_github(batch_files, deletion_message)
            st.success(f"🚀 Pushed {len(batch_files)} files to GitHub in single commit.")

    # Clear all caches to reflect changes
    st.cache_data.clear()
    clear_all_caches()

    st.success("Data has been successfully deleted and files have been updated.")


def validate_deletion_selection(selected_rounds: list) -> bool:
    """Validates that the deletion selection is valid.

    This function ensures that the user has selected at least one round for
    deletion to prevent accidental empty deletion operations.

    Args:
        selected_rounds (list): The list of selected round numbers.

    Returns:
        bool: True if the selection is valid, False otherwise.
    """
    return len(selected_rounds) > 0