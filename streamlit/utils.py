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

#print("utils module is being imported")

# Configure Logging
#logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Constants and Configurations
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the current file
CONFIG: Dict[str, str] = {
    "ROUND_INFO_PATH": os.path.join(BASE_DIR, "../data/round_info.csv")  # Update this for round_info.csv
}

FILE_PATH_ALL_DATA = os.path.join(BASE_DIR, "../data/all-data.parquet")  # Dynamically construct the path
TOTAL_HOLES = 18

PLAYER_DICT = {
    'AB': 'Alex BAKER',
    'JB': 'Jon BAKER',
    'DM': 'David MULLIN',
    'GW': 'Gregg WILLIAMS',
    'HM': 'Henry MELLER',
    'SN': 'Stuart NEUMANN',
    'JP': 'John PATTERSON',
    # Add more player initials and names as needed
}

TEG_ROUNDS = {
    'TEG 1': 1,
    'TEG 2': 3,
    # Add more TEGs if necessary
}

TEG_OVERRIDES = {
    'TEG 5': {
        'Best Net': 'Gregg WILLIAMS',
        'Best Gross': 'Stuart NEUMANN*'
    }
}

@st.cache_data
def load_all_data(exclude_teg_50: bool = False, exclude_incomplete_tegs: bool = False) -> pd.DataFrame:
    """
    Load the main dataset from the specified file path with optional filters.
    
    Parameters:
        exclude_teg_50 (bool): If True, excludes data with TEG 50.
        exclude_incomplete_tegs (bool): If True, excludes TEGs with incomplete rounds.
    
    Returns:
        pd.DataFrame: The filtered dataset.
    """
    if os.path.exists(FILE_PATH_ALL_DATA):
        df = pd.read_parquet(FILE_PATH_ALL_DATA)
    else:
        st.error(f"File not found: {FILE_PATH_ALL_DATA}")
        return pd.DataFrame()  # Return an empty DataFrame if file is missing

    # Ensure 'Year' is of integer type
    df['Year'] = df['Year'].astype('Int64')
    
    # Exclude TEG 50 if the flag is set
    if exclude_teg_50:
        df = df[df['TEGNum'] != 50]
    
    # Exclude incomplete TEGs if the flag is set
    if exclude_incomplete_tegs:
        df = exclude_incomplete_tegs_function(df)
    
    return df


def exclude_incomplete_tegs_function(df: pd.DataFrame) -> pd.DataFrame:
    """
    Exclude TEGs with incomplete rounds based on the number of unique rounds in the data.
    
    Parameters:
        df (pd.DataFrame): The dataset to filter.
    
    Returns:
        pd.DataFrame: The dataset with incomplete TEGs excluded.
    """
    # Compute the number of unique rounds per TEGNum
    observed_rounds = df.groupby('TEGNum')['Round'].nunique()
    
    # Create a DataFrame with TEGNum and observed rounds
    teg_rounds = observed_rounds.reset_index(name='ObservedRounds')
    
    # Apply get_teg_rounds to get the expected number of rounds per TEGNum
    teg_rounds['ExpectedRounds'] = teg_rounds['TEGNum'].apply(get_teg_rounds)
    
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

    # Map player names
    long_df['Player'] = long_df['Pl'].apply(get_player_name)

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


def save_to_parquet(df: pd.DataFrame, output_file: str) -> None:
    """
    Save DataFrame to a Parquet file.

    Parameters:
        df (pd.DataFrame): DataFrame containing the updated golf data.
        output_file (str): Path to save the Parquet file.
    """
    df.to_parquet(output_file, index=False)
    logger.info(f"Data successfully saved to {output_file}")


def get_google_sheet(sheet_name: str, worksheet_name: str) -> pd.DataFrame:
    """
    Load data from a specified Google Sheet and worksheet using credentials stored in Streamlit secrets.
    """
    logger.info(f"Fetching data from Google Sheet: {sheet_name}, Worksheet: {worksheet_name}")
    
    # Define the required scope for Google Sheets and Drive access
    SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    try:
        # Use service account info from Streamlit secrets
        service_account_info = st.secrets["google"]
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
        
        # Authorize and access the Google Sheets API
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).worksheet(worksheet_name)
        
        # Fetch data from the sheet
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
        hc_lookup = pd.read_csv(file_path)
    except FileNotFoundError:
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
    round_info = pd.read_csv(CONFIG["ROUND_INFO_PATH"])

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
        df = pd.read_csv(csv_file)
        logger.debug("CSV data loaded.")
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_file}")
        raise

    # Add round info
    df = add_round_info(df)
    logger.debug("Round info added.")

    # Apply cumulative score and average calculations
    df_transformed = add_cumulative_scores(df)
    logger.debug("Cumulative scores and averages applied.")

    # Add 'Year' column and convert to pandas nullable integer type
    df_transformed['Year'] = pd.to_datetime(
        df_transformed['Date'], dayfirst=True, errors='coerce'
    ).dt.year.astype('Int64')

    # Save the transformed dataframe to a Parquet file
    save_to_parquet(df_transformed, parquet_file)

    # Save the transformed dataframe to a CSV file for manual review
    df_transformed.to_csv(csv_output_file, index=False)
    logger.info(f"Transformed data saved to {csv_output_file}")


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
    all_scores_df = pd.read_csv(all_scores_path)
    all_data_df = pd.read_parquet(all_data_path)
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


def format_vs_par(value: float) -> str:
    """
    Format the value against par.

    Parameters:
        value (float): The value to format.

    Returns:
        str: Formatted string.
    """
    value = int(value)
    if value > 0:
        return f"+{value}"
    elif value < 0:
        return f"{value}"
    else:
        return "="


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
        'Stableford': 'sum'
    }).reset_index()

    results = []

    # Get unique TEG numbers
    for teg_num in df['TEGNum'].unique():
        # Filter data for the current TEG
        teg_data = grouped[grouped['TEGNum'] == teg_num]

        # Identify the best gross, best net, and worst net players
        best_gross_player = teg_data.loc[teg_data['GrossVP'].idxmin(), 'Player']
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
def get_round_data():
    all_data = load_all_data(exclude_teg_50 = True, exclude_incomplete_tegs= False)
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
    return df[df[measure_fn] == top_n]


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

def chosen_rd_context(ranked_rd_df, teg = 'TEG 15',rd = 4, measure = None):
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
            <strong><span class='name'>John Doe</span> • <span class='score'>95</span> • <span class='date'>2023-05-01</span></strong>
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
            row_str = f" {divider}".join(f"<span class='{col}'>{row[col]}</span>" for col in df.columns)
            rows.append(f"<strong>{row_str}</strong>")
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

def get_base_directory():
    # Get the current working directory
    current_dir = Path.cwd()
    
    # Check if we're in the Streamlit subfolder or not
    if current_dir.name == "Streamlit":
        # If we're in the Streamlit folder, go up one level to TEG
        BASE_DIR = current_dir.parent
    else:
        # Assume we are already in the TEG directory
        BASE_DIR = current_dir
    
    return BASE_DIR


def datawrapper_table_css():
    st.markdown("""
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

                .datawrapper-table {
                    font-family: Roboto, Arial, sans-serif !important;
                    border-collapse: separate !important;
                    border-spacing: 0 !important;
                    font-size: 14px !important;
                    width: 100%;
                    max-width: 600px;
                    margin-bottom: 40px !important;
                    border: none !important; /* Removes the external table border */
                }
                .datawrapper-table th, .datawrapper-table td {
                    text-align: center !important;
                    padding: 12px 8px !important;
                    border: none !important;
                    border-bottom: 1px solid #e0e0e0 !important;
                    word-wrap: break-word;
                }
                .datawrapper-table th {
                    font-weight: bold !important;
                    border-bottom: 2px solid #000 !important;
                }
                .datawrapper-table tr:hover {
                    background-color: #f5f5f5 !important;
                }

            </style>
        """, unsafe_allow_html=True)
