"""Core Data Transformation Functions

This module contains functions for transforming and enriching tournament data.
Includes handicap validation, cumulative calculations, ranking, and format conversions.
"""

import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any

from teg_analysis.io import read_file, write_file

logger = logging.getLogger(__name__)

# Constants
TOTAL_HOLES = 18
ROUND_INFO_CSV = 'data/round_info.csv'


def check_hc_strokes_combinations(transformed_df: pd.DataFrame) -> pd.DataFrame:
    """Checks for unique combinations of HC, SI, and HCStrokes.

    Args:
        transformed_df (pd.DataFrame): DataFrame containing the transformed
            golf data.

    Returns:
        pd.DataFrame: A DataFrame with unique combinations of HC, SI, and
        HCStrokes.
    """
    hc_si_strokes_df = transformed_df[['HC', 'SI', 'HCStrokes']].drop_duplicates()
    logger.info("Unique combinations of HC, SI, and HCStrokes obtained.")
    return hc_si_strokes_df


def add_cumulative_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Adds cumulative scores and averages to the DataFrame.

    This function calculates cumulative scores and averages for various
    measures across different periods (Round, TEG, Career).

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: The DataFrame with added cumulative scores and
        averages.
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
    """Adds TEG-level rankings and gaps to the leader for cumulative scores.

    This function adds the following columns:
    - Rank_GrossVP_TEG: Player's rank based on cumulative GrossVP.
    - Rank_Stableford_TEG: Player's rank based on cumulative Stableford.
    - Gap_GrossVP_TEG: Difference from the leader's cumulative GrossVP.
    - Gap_Stableford_TEG: Difference from the leader's cumulative Stableford.

    Args:
        df (pd.DataFrame): DataFrame with cumulative scores already
            calculated.

    Returns:
        pd.DataFrame: The DataFrame with added ranking and gap columns.
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


def save_to_parquet(df: pd.DataFrame, output_file: str):
    """Saves a DataFrame to a Parquet file.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        output_file (str): The path to the output Parquet file.
    """
    write_file(output_file, df, "Save to parquet")
    logger.info(f"Data successfully saved to {output_file}")


def reshape_round_data(df: pd.DataFrame, id_vars: List[str]) -> pd.DataFrame:
    """Reshapes round data from wide to long format or vice versa.

    Args:
        df (pd.DataFrame): The input DataFrame.
        id_vars (List[str]): Columns to use as identifier variables for melting.

    Returns:
        pd.DataFrame: The reshaped DataFrame.
    """
    try:
        # Melt the dataframe to long format
        melted_df = df.melt(id_vars=id_vars, var_name='Round', value_name='Score')
        logger.info("Data reshaped from wide to long format.")
        return melted_df
    except Exception as e:
        logger.error(f"Error reshaping data: {e}")
        return df


def load_and_prepare_handicap_data(file_path: str) -> pd.DataFrame:
    """Loads and prepares handicap data for merging with score data.

    Args:
        file_path (str): The path to the handicap file.

    Returns:
        pd.DataFrame: Prepared handicap data in long format.
    """
    try:
        hc_df = read_file(file_path)
        logger.info(f"Handicap data loaded from {file_path}")

        # Reshape to long format if needed
        if 'Pl' not in hc_df.columns:
            # Assume first column is player codes
            hc_df = hc_df.rename(columns={hc_df.columns[0]: 'Pl'})

        logger.info("Handicap data prepared and ready for merging.")
        return hc_df
    except Exception as e:
        logger.error(f"Error loading handicap data: {e}")
        return pd.DataFrame()


def summarise_existing_rd_data(existing_rows: pd.DataFrame) -> pd.DataFrame:
    """Summarize existing round data.

    Creates a pivot table showing scores by player, round, and TEG.

    Args:
        existing_rows (pd.DataFrame): DataFrame containing existing rows.

    Returns:
        pd.DataFrame: Pivoted summary DataFrame with players as rows,
                     rounds/TEGs as columns.

    Examples:
        >>> summary = summarise_existing_rd_data(existing_data)
        >>> print(summary)  # Shows scores or '-' for missing data
    """
    logger.info("Summarizing existing round data.")
    existing_summary_df = existing_rows.groupby(['TEGNum', 'Round', 'Pl'])['Sc'].sum().reset_index()
    existing_summary_pivot = existing_summary_df.pivot(index='Pl', columns=['Round', 'TEGNum'], values='Sc')
    summary = existing_summary_pivot.fillna('-').astype(str).replace(r'\.0$', '', regex=True)
    logger.info("Existing round data summarized.")
    return summary


def check_for_complete_and_duplicate_data(
    all_scores_path: str,
    all_data_path: str
) -> Dict[str, pd.DataFrame]:
    """Check for complete and duplicate data in scoring files.

    Validates data integrity by checking for incomplete rounds (< 18 holes)
    and duplicate entries (> 18 holes) in both all-scores.csv and all-data.parquet.

    Args:
        all_scores_path: Path to the all-scores CSV file
        all_data_path: Path to the all-data Parquet file

    Returns:
        dict: Summary with keys:
            - 'incomplete_scores': DataFrame of incomplete rounds in CSV
            - 'duplicate_scores': DataFrame of duplicate entries in CSV
            - 'incomplete_data': DataFrame of incomplete rounds in Parquet
            - 'duplicate_data': DataFrame of duplicate entries in Parquet

    Examples:
        >>> summary = check_for_complete_and_duplicate_data(
        ...     'data/all-scores.csv',
        ...     'data/all-data.parquet'
        ... )
        >>> if not summary['incomplete_scores'].empty:
        ...     print("Found incomplete rounds!")
    """
    logger.info("Checking for complete and duplicate data.")

    # Load the files
    all_scores_df = read_file(all_scores_path)
    all_data_df = read_file(all_data_path)
    logger.debug("All-scores and all-data files loaded.")

    # Group by TEG, Round, and Player and count entries
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
