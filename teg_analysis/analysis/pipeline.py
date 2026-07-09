"""Data processing pipeline and cache management functions.

This module provides the main data processing pipeline used for updates,
including cache generation for streaks, bestball, and commentary summaries.
"""


import logging
import pandas as pd
import os
from typing import List

logger = logging.getLogger(__name__)


from teg_analysis.constants import (
    STREAKS_PARQUET, BESTBALL_PARQUET, ROUND_INFO_CSV,
    COMMENTARY_ROUND_EVENTS_PARQUET, COMMENTARY_ROUND_SUMMARY_PARQUET,
    COMMENTARY_TOURNAMENT_SUMMARY_PARQUET, COMMENTARY_ROUND_STREAKS_PARQUET,
    COMMENTARY_TOURNAMENT_STREAKS_PARQUET,
)


def clear_all_caches():
    """No-op placeholder for cache clearing.

    The Streamlit app should call st.cache_data.clear() directly.
    This exists so pipeline code can call it without knowing the runtime.
    """
    pass


def update_streaks_cache(all_data: pd.DataFrame, defer_github: bool = False):
    """
    Update the streaks cache file with current streak calculations.

    Args:
        all_data (pd.DataFrame): Hole-level data (including incomplete TEGs)
            already loaded by the caller — see :func:`load_all_data`.
        defer_github (bool): If True, defer GitHub push for batch commit

    Returns:
        dict: File info if defer_github=True, None otherwise

    Raises on any failure (build/write) so a stale cache can never be reported as
    success — the orchestrators in ``data_update`` collect the error into
    ``cache_errors`` rather than losing the primary write.

    Called whenever source data changes (data updates, deletions).
    """
    from teg_analysis.io import write_file
    from teg_analysis.analysis.streaks import build_streaks

    logger.info("Updating streaks cache file")

    if all_data is None or all_data.empty:
        logger.warning("No data available for streak calculation")
        return None

    streaks_df = build_streaks(all_data)
    logger.info(f"Calculated {len(streaks_df)} streak records")

    file_info = write_file(STREAKS_PARQUET, streaks_df, "Update streaks cache", defer_github=defer_github)
    logger.info(f"Streaks cache updated successfully: {STREAKS_PARQUET}")

    # Clear streamlit cache to ensure fresh data on next load (only if not deferred)
    if not defer_github:
        clear_all_caches()

    return file_info


def update_bestball_cache(all_data: pd.DataFrame, defer_github: bool = False):
    """
    Update the bestball/worstball cache file.

    Args:
        all_data (pd.DataFrame): Hole-level data (including incomplete TEGs)
            already loaded by the caller — see :func:`load_all_data`.
        defer_github (bool): If True, defer GitHub push for batch commit

    Returns:
        dict: File info if defer_github=True, None otherwise

    Raises on any failure so a stale cache can never be reported as success.
    """
    from teg_analysis.io import write_file
    from teg_analysis.analysis.bestball import (
        prepare_bestball_data, calculate_bestball_scores, calculate_worstball_scores,
    )

    if all_data is None or all_data.empty:
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


def update_commentary_caches(all_data: pd.DataFrame, defer_github: bool = False):
    """
    Update the commentary cache files with current event and summary data.

    Args:
        all_data (pd.DataFrame): Hole-level data (including incomplete TEGs)
            already loaded by the caller — see :func:`load_all_data`.
        defer_github (bool): If True, defer GitHub push for batch commit

    Returns:
        list: List of file infos if defer_github=True, None otherwise

    This function:
    1. Reads round info + the (freshly regenerated) streaks cache
    2. Calls create_round_events() to generate event log
    3. Calls create_round_summary() to generate round summaries
    4. Calls create_tournament_summary() to generate tournament summaries
    5. Calls create_round_streaks_summary() to generate round streaks
    6. Calls create_tournament_streaks_summary() to generate tournament streaks
    7. Saves results to commentary parquet files
    8. Clears streamlit cache

    Raises on any failure so a stale cache can never be reported as success.

    Called whenever source data changes (data updates, deletions).
    """
    from teg_analysis.io import read_file, write_file
    from teg_analysis.analysis.commentary import (
        create_round_events, create_round_summary, create_tournament_summary,
        create_round_streaks_summary, create_tournament_streaks_summary,
    )

    logger.info("Updating commentary cache files")

    if all_data is None or all_data.empty:
        logger.warning("No data available for commentary generation")
        return None

    round_info = read_file(ROUND_INFO_CSV)
    streaks_df = read_file(STREAKS_PARQUET)
    logger.info(f"Loaded {len(round_info)} round info records and {len(streaks_df)} streak records")

    file_infos = []

    events_df = create_round_events(all_data_df=all_data)
    file_info = write_file(COMMENTARY_ROUND_EVENTS_PARQUET, events_df, "Update commentary round events cache", defer_github=defer_github)
    if file_info:
        file_infos.append(file_info)

    round_summary_df = create_round_summary(all_data_df=all_data, round_info_df=round_info)
    file_info = write_file(COMMENTARY_ROUND_SUMMARY_PARQUET, round_summary_df, "Update commentary round summary cache", defer_github=defer_github)
    if file_info:
        file_infos.append(file_info)

    tournament_summary_df = create_tournament_summary(all_data_df=all_data, round_info_df=round_info)
    file_info = write_file(COMMENTARY_TOURNAMENT_SUMMARY_PARQUET, tournament_summary_df, "Update commentary tournament summary cache", defer_github=defer_github)
    if file_info:
        file_infos.append(file_info)

    round_streaks_df = create_round_streaks_summary(all_data_df=all_data, streaks_df=streaks_df)
    file_info = write_file(COMMENTARY_ROUND_STREAKS_PARQUET, round_streaks_df, "Update commentary round streaks cache", defer_github=defer_github)
    if file_info:
        file_infos.append(file_info)

    tournament_streaks_df = create_tournament_streaks_summary(all_data_df=all_data, streaks_df=streaks_df)
    file_info = write_file(COMMENTARY_TOURNAMENT_STREAKS_PARQUET, tournament_streaks_df, "Update commentary tournament streaks cache", defer_github=defer_github)
    if file_info:
        file_infos.append(file_info)

    # Clear streamlit cache to ensure fresh data on next load (only if not deferred)
    if not defer_github:
        clear_all_caches()

    logger.info("Commentary cache files updated successfully")

    return file_infos if defer_github else None


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
        # Try Railway environment variables
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
            raise ValueError("Google credentials not found in environment variables. Set GOOGLE_TYPE and related env vars.")
        
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
    from teg_analysis.io import read_file
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


def update_all_data(csv_file: str, parquet_file: str, defer_github: bool = False):
    """
    Load data from a CSV file, apply cumulative scores and averages, and save it as a Parquet file.

    Parameters:
        csv_file (str): Path to the input CSV file.
        parquet_file (str): Path to the output Parquet file.
        defer_github (bool): If True, defer GitHub push for batch commit

    Returns:
        list: List of file infos if defer_github=True, None otherwise
    """
    logger.info(f"Updating all data from {csv_file} to {parquet_file}")

    # Deferred imports (avoid circular imports at module load).
    from teg_analysis.io import read_file, write_file
    from teg_analysis.core.data_transforms import add_cumulative_scores, add_rankings_and_gaps

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
    logger.info(f"Transformed data saved to {parquet_file}")

    if not defer_github:
        clear_all_caches()

    return file_infos if defer_github else None
