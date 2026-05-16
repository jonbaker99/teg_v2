"""Scoring calculations and utilities.

This module provides scoring-related functions for the TEG analysis system,
including scoring calculations, formatting, and various scoring utilities.
"""


import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# === CORE SCORING FUNCTIONS ===

def format_vs_par(value: float) -> str:
    """Formats a value as a vs-par score (e.g., '-5', 'E', '+3').

    Args:
        value: The numerical value to format.

    Returns:
        str: The formatted vs-par score.
    """
    if value is None or (isinstance(value, float) and value != value):  # Check for NaN
        return 'N/A'

    value = int(value)

    if value > 0:
        return f'+{value}'
    elif value == 0:
        return 'E'
    else:
        return str(value)


def get_net_competition_measure(teg_num: int) -> str:
    """Gets the net competition measure for a specific TEG.

    For TEGs 1-7, net competition is based on total net vs par.
    From TEG 8 onwards, net competition is based on stableford points.

    Args:
        teg_num (int): The TEG number.

    Returns:
        str: Either 'NetVP' (for TEGs 1-7) or 'Stableford' (for TEG 8+).
    """
    if teg_num <= 7:
        return 'NetVP'
    else:
        return 'Stableford'


# === SCORE FORMATTING ===

def format_vs_par_value(value: float) -> str:
    """Formats vs-par values for display.

    This function provides consistent formatting for vs-par scores across all
    scoring displays.

    Args:
        value (float): The vs-par value to format.

    Returns:
        str: A formatted string (e.g., "+1.50", "-0.50", "=").
    """
    if value > 0:
        return f"+{value:.2f}"
    elif value < 0:
        return f"{value:.2f}"
    else:
        return "="


def prepare_average_scores_by_par(all_data: pd.DataFrame) -> pd.DataFrame:
    """Calculates and formats average scores by par value for each player.

    This function shows how each player performs on different par values (Par
    3, 4, 5) to help identify strengths and weaknesses.

    Args:
        all_data (pd.DataFrame): The complete hole-by-hole scoring data.

    Returns:
        pd.DataFrame: A formatted table with average scores by par, ready for
        display.
    """
    # Calculate average GrossVP by player and par value
    avg_grossvp = all_data.groupby(['Player', 'PAR'])['GrossVP'].mean().unstack(fill_value=0)

    # Add overall average column
    avg_grossvp['Total'] = all_data.groupby('Player')['GrossVP'].mean()

    # Sort by overall performance (best to worst)
    avg_grossvp = avg_grossvp.sort_values('Total', ascending=True)
    avg_grossvp = avg_grossvp.round(2)

    # Format all values using consistent vs-par formatting
    for column in avg_grossvp.columns:
        avg_grossvp[column] = avg_grossvp[column].apply(format_vs_par_value)

    # Prepare for display
    avg_grossvp.reset_index(inplace=True)
    avg_grossvp.columns.name = None
    avg_grossvp.columns = ['Player'] + [f'Par {col}' if col != 'Total' else col for col in avg_grossvp.columns[1:]]

    return avg_grossvp


def format_scoring_stats_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Formats columns in the scoring statistics DataFrame for display.

    This function standardizes number formatting and column names for scoring
    tables, and handles infinite values.

    Args:
        df (pd.DataFrame): The raw scoring statistics data.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for display.
    """
    # Create a copy to avoid modifying the original
    formatted_df = df.copy()

    # Format count column as integer
    col1 = formatted_df.columns[1]
    formatted_df[col1] = formatted_df[col1].astype(int)

    # Format frequency column, handling infinite values
    col2 = formatted_df.columns[2]
    formatted_df[col2] = formatted_df[col2].apply(
        lambda x: 'n/a' if np.isinf(x) else f"{x:,.1f}"
    )

    # Clean up column names (replace underscores with spaces)
    formatted_df.columns = [col.replace('_', ' ') for col in formatted_df.columns]

    return formatted_df


# === STREAK CALCULATIONS ===

def calculate_multi_score_running_sum(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates running streaks for different score types.

    This function tracks consecutive achievements (e.g., birdies, pars or
    better) to find the longest streaks for each player.

    Args:
        df (pd.DataFrame): Hole-by-hole data with 'Career Count' for ordering.

    Returns:
        pd.DataFrame: The original data with added 'RunningSum' columns for
        each score type.
    """
    # Sort by player and chronological order
    df_sorted = df.sort_values(['Player', 'Career Count'])

    # Define score type conditions based on GrossVP values
    score_types = {
        'Pars_or_Better': lambda x: x <= 0,  # Par or better (birdie, eagle)
        'Birdies': lambda x: x == -1,        # Exactly birdie
        'TBPs': lambda x: x > 2              # Triple bogey or worse
    }

    # Initialize running sum columns
    for score_type in score_types:
        df_sorted[f'RunningSum_{score_type}'] = 0

    # Calculate running sums for each player
    def calc_running_sums(group):
        """Calculate consecutive streaks within a single player's data."""
        for score_type, condition in score_types.items():
            running_sum = 0
            for i, row in group.iterrows():
                if condition(row['GrossVP']):
                    running_sum += 1
                else:
                    running_sum = 0  # Reset streak
                group.at[i, f'RunningSum_{score_type}'] = running_sum
        return group

    # Apply calculation to each player's data
    df_sorted = df_sorted.groupby('Player', group_keys=False).apply(calc_running_sums)

    # Merge calculated columns back to original dataframe
    merge_columns = ['Player', 'Career Count'] + [f'RunningSum_{score_type}' for score_type in score_types]
    df = df.merge(df_sorted[merge_columns], on=['Player', 'Career Count'], how='left')

    return df


def summarize_multi_score_running_sum(df: pd.DataFrame) -> pd.DataFrame:
    """Summarizes the maximum streak lengths for each player and score type.

    This function creates the final "Longest Streaks" table showing each
    player's best streaks.

    Args:
        df (pd.DataFrame): Data with 'RunningSum' columns from
            `calculate_multi_score_running_sum()`.

    Returns:
        pd.DataFrame: A summary showing the longest streak for each player and
        score type.
    """
    score_types = ['Birdies', 'Pars_or_Better', 'TBPs']

    # Verify required columns exist
    for score_type in score_types:
        if f'RunningSum_{score_type}' not in df.columns:
            raise ValueError(f"RunningSum_{score_type} column not found. Please calculate running sums first.")

    # Get maximum streak length for each player/score type
    summary = df.groupby('Player').agg({
        f'RunningSum_{score_type}': 'max' for score_type in score_types
    }).reset_index()

    # Clean up column names
    summary.columns = ['Player'] + score_types

    # Sort by best "Pars or Better" streak
    summary = summary.sort_values('Pars_or_Better', ascending=False)

    return summary


# === PAR-BASED SCORING ANALYSIS ===


def calculate_par_performance_matrix(filtered_data: pd.DataFrame) -> pd.DataFrame:
    """Calculates the average GrossVP performance by player and par value.

    This function creates a comprehensive view of how each player performs on
    different par holes, including an overall average for comparison.

    Args:
        filtered_data (pd.DataFrame): The tournament data for analysis.

    Returns:
        pd.DataFrame: A player-by-par performance matrix with totals, sorted
        by total performance.
    """
    # Create pivot table of average GrossVP by player and par
    avg_grossvp = filtered_data.groupby(['Player', 'PAR'])['GrossVP'].mean().unstack(fill_value=0)
    
    # Add total column with overall average
    avg_grossvp['Total'] = filtered_data.groupby('Player')['GrossVP'].mean()
    
    # Sort by total performance (ascending = best first)
    avg_grossvp = avg_grossvp.sort_values('Total', ascending=True)
    
    # Round to 2 decimal places for clean display
    avg_grossvp = avg_grossvp.round(2)
    
    return avg_grossvp


def format_par_performance_table(avg_grossvp: pd.DataFrame) -> pd.DataFrame:
    """Formats the par performance table for display.

    This function applies consistent formatting for vs-par values, using +/-
    notation and renaming columns for a user-friendly display.

    Args:
        avg_grossvp (pd.DataFrame): The raw performance matrix.

    Returns:
        pd.DataFrame: A formatted table ready for HTML display.
    """
    def format_vs_par_value(value):
        """Format vs-par values with appropriate +/- symbols."""
        if pd.isna(value):
            return ""
        if value > 0:
            return f"+{value:.2f}"
        elif value < 0:
            return f"{value:.2f}"
        else:
            return "="
    
    # Apply formatting to all columns
    for column in avg_grossvp.columns:
        avg_grossvp[column] = avg_grossvp[column].apply(format_vs_par_value)
    
    # Reset index to make Player a regular column
    avg_grossvp.reset_index(inplace=True)
    avg_grossvp.columns.name = None
    
    # Rename columns for display
    avg_grossvp.columns = ['Player'] + [f'Par {col}' if col != 'Total' else col for col in avg_grossvp.columns[1:]]
    
    return avg_grossvp


# === SCORING ACHIEVEMENTS ===


def get_scoring_achievement_fields() -> list[list[str]]:
    """Defines the score achievement fields for the tabbed display.

    This function centralizes the definition of score achievement categories,
    where each pair contains the achievement count and the holes per
    achievement metric.

    Returns:
        list: A list of field pairs for achievements and frequency metrics.
    """
    chart_fields = [
        ['Eagles', 'Holes_per_Eagle'],
        ['Birdies', 'Holes_per_Birdie'],
        ['Pars_or_Better', 'Holes_per_Par_or_Better'],
        ['TBPs', 'Holes_per_TBP']
    ]
    
    return chart_fields



def format_achievement_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Formats the achievement DataFrame columns for display.

    This function formats achievement counts as integers and frequency ratios
    as decimals, handling infinite values and cleaning up column names.

    Args:
        df (pd.DataFrame): The raw achievement data with counts and ratios.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for HTML display.
    """
    # Create copy to avoid modifying original dataframe
    formatted_df = df.copy()
    
    # Format achievement count as integer (column 1)
    col1 = formatted_df.columns[1]
    formatted_df[col1] = formatted_df[col1].astype(int)

    # Format frequency ratio (column 2) - handle infinity for zero achievements
    col2 = formatted_df.columns[2]
    formatted_df[col2] = formatted_df[col2].apply(
        lambda x: 'n/a' if np.isinf(x) else f"{x:,.1f}"
    )

    # Clean column names by removing underscores
    formatted_df.columns = [col.replace('_', ' ') for col in formatted_df.columns]

    return formatted_df


def prepare_achievement_table_data(scoring_stats: pd.DataFrame, chart_fields: list) -> pd.DataFrame:
    """Prepares achievement table data for a specific score type.

    This function extracts the relevant columns for a specific achievement
    type, sorts the data, and applies formatting for a clean display.

    Args:
        scoring_stats (pd.DataFrame): The complete scoring statistics data.
        chart_fields (list): A field pair for a specific achievement type.

    Returns:
        pd.DataFrame: A formatted table ready for display.
    """
    # Select relevant columns for this achievement type
    table_columns = ['Player'] + chart_fields
    table_df = scoring_stats[table_columns].copy()
    
    # Sort by achievement count (desc) then frequency (asc - lower is better)
    table_df = table_df.sort_values(by=chart_fields, ascending=[False, True])
    
    # Apply formatting for display
    formatted_table = format_achievement_dataframe_columns(table_df)
    
    return formatted_table



# === SCORE DISTRIBUTION ANALYSIS ===


def apply_teg_and_par_filters(all_data: pd.DataFrame, selected_tegnum: str or int, selected_par: str or int) -> tuple[pd.DataFrame, str, str]:
    """Applies TEG and par filters to tournament data.

    This function applies user-selected filters for score distribution
    analysis and returns descriptive labels for chart titles and captions.

    Args:
        all_data (pd.DataFrame): The complete tournament data.
        selected_tegnum (str or int): The selected TEG number or "All TEGs".
        selected_par (str or int): The selected par value or "All holes".

    Returns:
        tuple: A tuple containing:
            - filtered_data (pd.DataFrame): The filtered data.
            - teg_desc (str): A description of the TEG filter.
            - par_desc (str): A description of the par filter.
    """
    # Apply TEG filter
    if selected_tegnum != 'All TEGs':
        selected_tegnum_int = int(selected_tegnum)
        filtered_data_teg = all_data[all_data['TEGNum'] == selected_tegnum_int]
        teg_desc = f'TEG {selected_tegnum_int} only'
    else:
        filtered_data_teg = all_data
        teg_desc = 'All TEGs'

    # Apply par filter
    if selected_par != 'All holes':
        selected_par_int = int(selected_par)
        filtered_data = filtered_data_teg[all_data['PAR'] == selected_par_int]
        par_desc = f'Par {selected_par_int}s only'
    else:
        filtered_data = filtered_data_teg
        par_desc = 'All holes'

    return filtered_data, teg_desc, par_desc


def count_scores_by_player(df: pd.DataFrame, field: str = 'GrossVP') -> pd.DataFrame:
    """Counts score distributions by player.

    This function creates a distribution matrix showing how many times each
    player achieved each score, enabling comparison of scoring patterns.

    Args:
        df (pd.DataFrame): The filtered tournament data.
        field (str, optional): The score field to analyze ('GrossVP' or
            'Sc'). Defaults to 'GrossVP'.

    Returns:
        pd.DataFrame: A score count matrix with players as columns and scores
        as rows.
    """
    # Group by score and player, count occurrences
    summary = df.groupby([field, 'Pl']).size().unstack(fill_value=0)
    
    # Sort by score value (ascending for logical order)
    summary = summary.sort_index(ascending=True)
    
    # Sort columns (players) alphabetically
    summary = summary.sort_index(axis=1)
    
    return summary



def prepare_score_count_display(count_data: pd.DataFrame, score_field: str, display_name: str, is_percentage: bool = False) -> pd.DataFrame:
    """Prepares score count data for table display.

    This function formats score count data for a clean table display,
    handling data type conversions, column renaming, and percentage
    formatting.

    Args:
        count_data (pd.DataFrame): The raw score count matrix or percentage
            data.
        score_field (str): The original score field name.
        display_name (str): The user-friendly display name.
        is_percentage (bool, optional): Whether the data contains
            percentages that need formatting. Defaults to False.

    Returns:
        pd.DataFrame: The formatted data ready for display.
    """
    display_data = count_data.reset_index()
    display_data.columns.name = None

    # Handle specific formatting for the score field (first column)
    if score_field == 'Sc':
        display_data[score_field] = display_data[score_field].astype(int)
    elif score_field == 'Stableford':
        display_data[score_field] = display_data[score_field].astype(int)
    elif score_field == 'GrossVP':
        display_data[score_field] = display_data[score_field].apply(format_vs_par)

    # Apply percentage formatting to player columns (not the first column)
    if is_percentage:
        player_columns = [col for col in display_data.columns if col != score_field]
        for col in player_columns:
            if pd.api.types.is_numeric_dtype(display_data[col]):
                display_data[col] = display_data[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "0.0%")

    # Rename score column to user-friendly name
    display_data = display_data.rename(columns={score_field: display_name})

    return display_data



def convert_counts_to_percentages(count_data: pd.DataFrame) -> pd.DataFrame:
    """Converts score count data to a percentage distribution per player.

    This function converts absolute counts to percentages for relative
    comparison across players.

    Args:
        count_data (pd.DataFrame): A raw score count matrix with scores as
            rows and players as columns.

    Returns:
        pd.DataFrame: A percentage distribution where each player's column
        sums to 100%.
    """
    # Calculate percentage of total for each player (column-wise)
    percentage_data = count_data.div(count_data.sum(axis=0), axis=1) * 100

    # Round to 1 decimal place for clean display
    percentage_data = percentage_data.round(1)

    return percentage_data






