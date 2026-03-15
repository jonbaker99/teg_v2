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


from teg_analysis.constants import (
    STREAKS_PARQUET, BESTBALL_PARQUET, ROUND_INFO_CSV,
    COMMENTARY_ROUND_EVENTS_PARQUET, COMMENTARY_ROUND_SUMMARY_PARQUET,
    COMMENTARY_TOURNAMENT_SUMMARY_PARQUET, COMMENTARY_ROUND_STREAKS_PARQUET,
    COMMENTARY_TOURNAMENT_STREAKS_PARQUET,
)


def clear_all_caches():
    """Clear Streamlit caches if Streamlit is available, otherwise no-op."""
    if st is not None:
        try:
            st.cache_data.clear()
        except Exception:
            pass


def _get_deps():
    """Get function dependencies (deferred to avoid circular imports at module level)."""
    from teg_analysis.core.data_loader import load_all_data
    from teg_analysis.io import read_file, write_file
    from teg_analysis.core.data_transforms import add_cumulative_scores, add_rankings_and_gaps
    from teg_analysis.analysis.streaks import build_streaks
    from teg_analysis.analysis.commentary import (create_round_events, create_round_summary,
        create_tournament_summary, create_round_streaks_summary, create_tournament_streaks_summary)
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

        # Get dependencies
        deps = _get_deps()
        load_all_data = deps['load_all_data']
        write_file = deps['write_file']
        build_streaks = deps['build_streaks']

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
        # Get dependencies
        deps = _get_deps()
        load_all_data = deps['load_all_data']
        write_file = deps['write_file']

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

        # Get dependencies
        deps = _get_deps()
        load_all_data = deps['load_all_data']
        read_file = deps['read_file']
        write_file = deps['write_file']
        create_round_events = deps['create_round_events']
        create_round_summary = deps['create_round_summary']
        create_tournament_summary = deps['create_tournament_summary']
        create_round_streaks_summary = deps['create_round_streaks_summary']
        create_tournament_streaks_summary = deps['create_tournament_streaks_summary']

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
    from teg_analysis.io import read_file

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
