"""Core Data Loading Functions

This module contains the primary data loading pipeline for the TEG analysis system.
It handles loading tournament data from Parquet files, merging with metadata,
and processing round-level data with handicap information.

Key Functions:
- load_all_data() - PRIMARY function (40+ pages depend on it)
- process_round_for_all_scores() - Core scoring calculations
- Helper functions for data preparation and validation
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any
from pathlib import Path
import os

from teg_analysis.io import read_file, write_file
from teg_analysis.constants import (
    ALL_DATA_PARQUET, ROUND_INFO_CSV, PLAYER_DICT, TEGNUM_ROUNDS,
)

logger = logging.getLogger(__name__)


def get_tegnum_rounds(teg_num: int) -> int:
    """Return the expected number of rounds for a given TEG number.

    Defaults to 4 unless the TEG is listed in TEGNUM_ROUNDS.
    """
    return TEGNUM_ROUNDS.get(teg_num, 4)


def load_all_data(exclude_teg_50: bool = True, exclude_incomplete_tegs: bool = False) -> pd.DataFrame:
    """Loads all data from the Parquet file and prepares it for use.

    This function loads the main data file, merges it with round information,
    and provides options to exclude certain data.

    Args:
        exclude_teg_50 (bool, optional): Whether to exclude TEG 50.
            Defaults to True.
        exclude_incomplete_tegs (bool, optional): Whether to exclude
            incomplete TEGs. Defaults to False.

    Returns:
        pd.DataFrame: The loaded and prepared data as a pandas DataFrame.
    """
    try:
        df = read_file(ALL_DATA_PARQUET)
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return pd.DataFrame()

    # Load round info data to get Area information
    try:
        round_info = read_file(ROUND_INFO_CSV)
        # Join to get Area information (select only columns we need to avoid duplicates)
        round_info_subset = round_info[['TEGNum', 'Round', 'Area']].copy()
        df = df.merge(round_info_subset, on=['TEGNum', 'Round'], how='left')
    except Exception as e:
        logger.warning(f"Could not load round info for Area data: {e}")

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
    """Gets the number of completed rounds for each TEG.

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: A DataFrame with the number of completed rounds for
        each TEG.
    """
    num_rounds = (
        df.groupby(['TEGNum', 'TEG'])['Round']
        .nunique()
        .reset_index(name="num_rounds")
    )
    return num_rounds


def get_incomplete_tegs(df: pd.DataFrame) -> pd.DataFrame:
    """Gets a list of incomplete TEGs.

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: A DataFrame with the TEG numbers of incomplete TEGs.
    """
    # Compute the number of unique COMPLETED rounds per TEGNum
    all_rounds = df.groupby('TEGNum')['Round'].nunique()

    # Create a DataFrame with TEGNum and observed rounds
    teg_rounds = all_rounds.reset_index(name='AllRounds')

    # Apply get_tegnum_rounds to get the expected number of rounds per TEGNum
    teg_rounds['ExpectedRounds'] = teg_rounds['TEGNum'].apply(get_tegnum_rounds)

    # Identify incomplete TEGs where observed rounds do not match expected rounds
    incomplete_tegs = teg_rounds[teg_rounds['AllRounds'] != teg_rounds['ExpectedRounds']]['TEGNum']

    return incomplete_tegs


def exclude_incomplete_tegs_function(df: pd.DataFrame) -> pd.DataFrame:
    """Excludes TEGs with incomplete rounds from the DataFrame.

    This function identifies and removes TEGs that do not have the expected
    number of rounds.

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: A DataFrame with incomplete TEGs excluded.
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
    """Retrieves the full name of a player from their initials.

    Args:
        initials (str): The initials of the player.

    Returns:
        str: The full name of the player, or 'Unknown Player' if the
        initials are not found.
    """
    return PLAYER_DICT.get(initials.upper(), 'Unknown Player')


def process_round_for_all_scores(long_df: pd.DataFrame, hc_long: pd.DataFrame) -> pd.DataFrame:
    """Processes round data to calculate various scores and metrics.

    This function takes long-format round data and handicap data, merges them,
    and calculates a variety of scores including Gross, Net, and Stableford.

    Args:
        long_df (pd.DataFrame): DataFrame containing round data.
        hc_long (pd.DataFrame): DataFrame containing handicap data.

    Returns:
        pd.DataFrame: A processed DataFrame with additional computed columns.
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


def add_round_info(all_data: pd.DataFrame) -> pd.DataFrame:
    """Adds round information metadata to the data.

    This function enriches the dataset with round-level metadata including
    course information, dates, and tournament context.

    Args:
        all_data (pd.DataFrame): The main tournament data.

    Returns:
        pd.DataFrame: Data enriched with round information.
    """
    try:
        round_info = read_file(ROUND_INFO_CSV)
        all_data = all_data.merge(round_info, on=['TEGNum', 'Round'], how='left', suffixes=('', '_ri'))
        return all_data
    except Exception as e:
        logger.warning(f"Could not add round info: {e}")
        return all_data
