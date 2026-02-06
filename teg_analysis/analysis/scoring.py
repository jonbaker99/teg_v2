"""Scoring calculations and utilities.

This module provides scoring-related functions for the TEG analysis system,
including scoring calculations, formatting, and various scoring utilities.
"""


import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# === CORE SCORING FUNCTIONS (from utils.py) ===

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

    For TEGs 1-5, net competition is based on total net vs par.
    For TEG 6 onwards, net competition is based on stableford points.

    Args:
        teg_num (int): The TEG number.

    Returns:
        str: Either 'NetVP' (for TEGs 1-5) or 'Stableford' (for TEG 6+).
    """
    if teg_num <= 7:
        return 'NetVP'
    else:
        return 'Stableford'


# === SCORE FORMATTING (from helpers/scoring_data_processing.py) ===

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
    formatted_df.iloc[:, 1] = formatted_df.iloc[:, 1].astype(int)

    # Format frequency column, handling infinite values
    formatted_df.iloc[:, 2] = formatted_df.iloc[:, 2].apply(
        lambda x: 'n/a' if np.isinf(x) else f"{x:,.1f}"
    )

    # Clean up column names (replace underscores with spaces)
    formatted_df.columns = [col.replace('_', ' ') for col in formatted_df.columns]

    return formatted_df


# === STREAK CALCULATIONS (from helpers/scoring_data_processing.py) ===

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
"""Data processing functions for scoring analysis pages.

This module contains functions for score formatting and aggregation, streak
calculations and analysis, and score type statistics processing.
"""


import pandas as pd
import numpy as np


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
    formatted_df.iloc[:, 1] = formatted_df.iloc[:, 1].astype(int)
    
    # Format frequency column, handling infinite values
    formatted_df.iloc[:, 2] = formatted_df.iloc[:, 2].apply(
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


# === PAR-BASED SCORING ANALYSIS (from helpers/par_analysis_processing.py) ===

"""Data processing functions for par-based scoring analysis.

This module contains functions for processing scores by par value (Par 3, Par 4,
Par 5), creating player performance matrices by par, and formatting vs-par
values for display.
"""


import pandas as pd
import numpy as np


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


# === SECTION DIVIDER ===

"""Data processing functions for scoring achievements analysis.

This module contains functions for processing career scoring achievements
statistics, formatting the data for display, and creating tabbed displays for
different score types.
"""


import pandas as pd
import numpy as np


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


def create_achievement_tab_labels(chart_fields_all: list[list[str]]) -> list[str]:
    """Creates user-friendly tab labels from achievement field names.

    This function converts internal field names to display-ready tab labels by
    replacing underscores with spaces for a cleaner UI presentation.

    Args:
        chart_fields_all (list): A list of all achievement field pairs.

    Returns:
        list: A list of tab labels.
    """
    tab_labels = [chart_fields[0].replace("_", " ") for chart_fields in chart_fields_all]
    return tab_labels


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
    formatted_df.iloc[:, 1] = formatted_df.iloc[:, 1].astype(int)
    
    # Format frequency ratio (column 2) - handle infinity for zero achievements
    formatted_df.iloc[:, 2] = formatted_df.iloc[:, 2].apply(
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


def create_section_title(chart_fields: list) -> str:
    """Creates a section title from achievement field names.

    This function converts an internal field name to a user-friendly section
    title by removing underscores and adding proper context.

    Args:
        chart_fields (list): A field pair for an achievement type.

    Returns:
        str: A cleaned section title for display.
    """
    section_title = chart_fields[0].replace("_", " ")
    return section_title


# === SECTION DIVIDER ===

"""Data processing functions for score distribution analysis.

This module contains functions for counting score distributions by player,
creating percentage distribution charts, filtering data by TEG and par value,
and formatting score count data for display.
"""


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# NOTE: Some functions may use Streamlit for caching
# Importing conditionally for flexibility
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    st = None
    HAS_STREAMLIT = False


def get_filtering_options(all_data: pd.DataFrame) -> tuple[list, list]:
    """Gets filtering options for score count analysis.

    This function provides filtering options for score distribution analysis,
    enabling focused analysis by tournament or par value.

    Args:
        all_data (pd.DataFrame): The complete tournament data.

    Returns:
        tuple: A tuple containing:
            - tegnum_options (list): A list of TEG number options.
            - par_options (list): A list of par value options.
    """
    tegnum_options = ['All TEGs'] + sorted(all_data['TEGNum'].unique().tolist(), reverse=True)
    par_options = ['All holes'] + sorted(all_data['PAR'].unique().tolist())
    
    return tegnum_options, par_options


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


def create_percentage_distribution_chart(df: pd.DataFrame, teg_desc: str, par_desc: str) -> px.bar:
    """Creates a percentage distribution bar chart for score counts.

    This function provides a visual representation of score distributions as
    percentages, showing the relative frequency of each score for each player.

    Args:
        df (pd.DataFrame): The score count data with the first column as the
            index.
        teg_desc (str): A description of the TEG for the chart title.
        par_desc (str): A description of the par for the chart title.

    Returns:
        plotly.graph_objects.Figure: A percentage distribution bar chart.
    """
    # Prepare dataframe with first column as index
    chart_df = df.copy()
    chart_df.set_index(chart_df.columns[0], inplace=True)

    # Calculate percentage of total for each player
    df_percentage = chart_df.div(chart_df.sum(axis=0), axis=1)

    # Create Plotly bar chart
    fig = px.bar(df_percentage, barmode='group')
    fig.update_layout(
        title=f"% of total | {teg_desc} | {par_desc}",
        xaxis_title=chart_df.index.name,
        yaxis_title="% of Total",
        legend_title="Pl",
        bargap=0.3,
        bargroupgap=0.0,    
    )
    
    # Disable zooming for cleaner user experience
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True

    return fig


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
        from utils import format_vs_par
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


def prepare_chart_data_with_special_handling(display_data: pd.DataFrame, score_field: str) -> pd.DataFrame:
    """Prepares data for a chart with special value handling.

    This function handles special formatting cases for charting, such as
    converting formatted values back to numeric for proper display.

    Args:
        display_data (pd.DataFrame): The formatted display data.
        score_field (str): The original score field name.

    Returns:
        pd.DataFrame: Chart-ready data with special values converted.
    """
    chart_data = display_data.copy()
    
    # Handle special case for vs par data (convert "=" back to 0 for charting)
    if score_field == 'GrossVP':
        display_column = 'vs Par'
        chart_data.loc[chart_data[display_column] == '=', display_column] = 0
    
    return chart_data


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


def format_percentage_for_display(percentage_data: pd.DataFrame) -> pd.DataFrame:
    """Formats percentage data for table display with '%' symbols.

    This function converts numeric percentage values to formatted strings for
    a clean table display.

    Args:
        percentage_data (pd.DataFrame): The percentage data with numeric
            values.

    Returns:
        pd.DataFrame: Formatted data with percentages as strings.
    """
    # Create a copy to avoid modifying original data
    formatted_data = percentage_data.copy()

    # Apply percentage formatting to all numeric columns
    for col in formatted_data.columns:
        if pd.api.types.is_numeric_dtype(formatted_data[col]):
            formatted_data[col] = formatted_data[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "0.0%")

    return formatted_data


def create_stacked_bar_chart(count_data: pd.DataFrame, teg_desc: str, par_desc: str, score_field: str) -> px.bar:
    """Creates a stacked bar chart showing the score distribution by player.

    This function provides a visual representation of score distributions as
    stacked bars, with each player represented by a column.

    Args:
        count_data (pd.DataFrame): The score count matrix with scores as rows
            and players as columns.
        teg_desc (str): A description of the TEG for the chart title.
        par_desc (str): A description of the par for the chart title.
        score_field (str): The score field being analyzed ('GrossVP' or 'Sc').

    Returns:
        plotly.graph_objects.Figure: A stacked bar chart.
    """
    # Convert to percentages for stacked display
    percentage_data = convert_counts_to_percentages(count_data)

    # Prepare data in long format for plotly express
    # Reset index to make score values a column
    melted_data = percentage_data.reset_index()

    # Melt the dataframe to long format
    plot_data = pd.melt(
        melted_data,
        id_vars=[melted_data.columns[0]],  # Score column
        var_name='Player',
        value_name='Percentage'
    )

    # Rename the score column for clarity
    score_col_name = "Score" if score_field == 'Sc' else "vs Par"
    plot_data.rename(columns={melted_data.columns[0]: score_col_name}, inplace=True)

    # Create stacked bar chart
    fig = px.bar(
        plot_data,
        x='Player',
        y='Percentage',
        color=score_col_name,
        title=f"Score Distribution by Player | {teg_desc} | {par_desc}",
        labels={'Percentage': 'Percentage of Holes'},
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    # Update layout for better display
    fig.update_layout(
        xaxis_title="Player",
        yaxis_title="Percentage of Holes",
        bargap=0.2,
        yaxis=dict(ticksuffix='%')
    )

    # Disable zooming for cleaner user experience
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True

    return fig


def calculate_player_distributions(filtered_data: pd.DataFrame, selected_field: str, display_mode: str) -> tuple[pd.DataFrame, pd.Series]:
    """Calculates distribution data for each player and overall average.

    This function prepares the data needed for creating density/distribution
    plots showing how each player's scores are distributed.

    Args:
        filtered_data (pd.DataFrame): The filtered tournament data.
        selected_field (str): The score field to analyze ('Sc', 'GrossVP', or 'Stableford').
        display_mode (str): Either "Count" or "Percentage".

    Returns:
        tuple: A tuple containing:
            - player_distributions (pd.DataFrame): Distribution data for each player.
            - total_distribution (pd.Series): Overall distribution across all players (for overlay).
    """
    # Get count data for each player
    count_data = count_scores_by_player(filtered_data, selected_field)

    # Calculate total distribution (sum across all players)
    total_distribution = count_data.sum(axis=1)

    # Convert to percentage if needed
    if display_mode == "Percentage":
        # Convert each player's column to percentage
        player_distributions = convert_counts_to_percentages(count_data)
        # Convert total to percentage
        total_distribution = (total_distribution / total_distribution.sum()) * 100
    else:
        player_distributions = count_data

    return player_distributions, total_distribution


def sort_players_by_average(player_distributions: pd.DataFrame, selected_field: str) -> list:
    """Sorts players based on their average score for the selected metric.

    Args:
        player_distributions (pd.DataFrame): Distribution data with scores as index and players as columns.
        selected_field (str): The score field being analyzed ('Sc', 'GrossVP', or 'Stableford').

    Returns:
        list: Sorted list of player names.
    """
    # Calculate weighted average for each player
    score_values = player_distributions.index.values
    player_averages = {}

    for player in player_distributions.columns:
        # Get the distribution for this player (as weights)
        weights = player_distributions[player].values
        # Calculate weighted average
        if weights.sum() > 0:
            avg = np.average(score_values, weights=weights)
            player_averages[player] = avg
        else:
            player_averages[player] = 0

    # Sort based on field type
    if selected_field == 'Stableford':
        # Stableford: higher is better, so descending order
        sorted_players = sorted(player_averages.keys(), key=lambda x: player_averages[x], reverse=True)
    else:
        # Sc and GrossVP: lower is better, so ascending order
        sorted_players = sorted(player_averages.keys(), key=lambda x: player_averages[x])

    return sorted_players


def create_ridgeline_distribution_chart(
    player_distributions: pd.DataFrame,
    total_distribution: pd.Series,
    selected_field: str,
    display_mode: str,
    teg_desc: str,
    par_desc: str
) -> go.Figure:
    """Creates a multi-pane distribution chart (ridgeline plot) for each player.

    This function creates a vertically stacked distribution chart similar to
    The Economist's language information rate chart, with one distribution
    curve for each player, all aligned horizontally.

    Args:
        player_distributions (pd.DataFrame): Distribution data with scores as index and players as columns.
        total_distribution (pd.Series): Overall distribution for overlay (in percentage mode).
        selected_field (str): The score field being analyzed ('Sc', 'GrossVP', or 'Stableford').
        display_mode (str): Either "Count" or "Percentage".
        teg_desc (str): Description of TEG filter for title.
        par_desc (str): Description of par filter for title.

    Returns:
        plotly.graph_objects.Figure: A multi-pane distribution chart.
    """
    # Sort players by average
    sorted_players = sort_players_by_average(player_distributions, selected_field)

    # Create subplots - one row per player
    num_players = len(sorted_players)
    fig = make_subplots(
        rows=num_players,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.01,
        subplot_titles=sorted_players,
        x_title=None,
        y_title=None
    )

    # Define color palette for different players
    colors = [
        '#1f77b4',  # Blue
        '#ff7f0e',  # Orange
        '#2ca02c',  # Green
        '#d62728',  # Red
        '#9467bd',  # Purple
        '#8c564b',  # Brown
        '#e377c2',  # Pink
        '#7f7f7f',  # Gray
        '#bcbd22',  # Olive
        '#17becf',  # Cyan
    ]

    # Get x-axis values (score values)
    x_values = player_distributions.index.values

    # Determine y-axis range to keep all plots on same scale
    if display_mode == "Percentage":
        max_y = player_distributions.max().max()
    else:
        max_y = player_distributions.max().max()

    # Add a trace for each player
    for idx, player in enumerate(sorted_players, start=1):
        y_values = player_distributions[player].values

        # Get color for this player (cycle through colors if more players than colors)
        color = colors[(idx - 1) % len(colors)]
        # Convert hex to rgb for fill color with transparency
        rgb = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        fill_color = f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.5)'

        # Add main distribution trace (filled area) with spline smoothing
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                name=player,
                fill='tozeroy',
                mode='lines',
                line=dict(width=1.5, color=color, shape='spline', smoothing=1.3),
                fillcolor=fill_color,
                showlegend=False,
                hovertemplate=f'{player}<br>Score: %{{x}}<br>{"Percentage" if display_mode == "Percentage" else "Count"}: %{{y}}<extra></extra>'
            ),
            row=idx,
            col=1
        )

        # Add total distribution overlay if in percentage mode
        if display_mode == "Percentage":
            fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=total_distribution.values,
                    name='Total Average' if idx == 1 else None,
                    mode='lines',
                    line=dict(width=0.8, color='black', shape='spline', smoothing=1.3),
                    showlegend=(idx == 1),  # Only show legend for first trace
                    hovertemplate=f'Total Average<br>Score: %{{x}}<br>Percentage: %{{y}}<extra></extra>'
                ),
                row=idx,
                col=1
            )

        # Update y-axis for this subplot
        fig.update_yaxes(
            range=[0, max_y * 1.1],  # Add 10% padding
            showticklabels=False,
            showgrid=False,
            zeroline=True,
            row=idx,
            col=1
        )

        # Update x-axis for this subplot
        fig.update_xaxes(
            showticklabels=(idx == num_players),  # Only show labels on bottom plot
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=1,
            dtick=1,  # Gridline every 1 unit
            zeroline=True,
            row=idx,
            col=1
        )

    # Update overall layout
    score_label = {
        'Sc': 'Score',
        'GrossVP': 'Score vs Par',
        'Stableford': 'Stableford Points'
    }[selected_field]

    fig.update_layout(
        height=80 * num_players,  # Narrower charts - reduced from 150 to 80
        title=f"Distribution by Player | {teg_desc} | {par_desc}",
        showlegend=(display_mode == "Percentage"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        # Add left margin for player names
        margin=dict(l=150, r=50, t=80, b=50),
        # Set font to Open Sans with black color
        font=dict(
            family="Open Sans, sans-serif",
            color="black"
        )
    )

    # Move subplot titles to the left (outside the plot area) and color-code them
    # Calculate the height of each subplot in paper coordinates
    # With vertical_spacing=0.01, each plot gets (1 - (num_players-1)*0.01) / num_players
    total_spacing = (num_players - 1) * 0.01
    available_height = 1 - total_spacing
    subplot_height = available_height / num_players

    for idx, annotation in enumerate(fig['layout']['annotations']):
        # Get the corresponding color for this player
        player_color = colors[idx % len(colors)]

        # Calculate the y position for the middle of this subplot
        # Start from top (1.0) and work down
        y_top = 1 - (idx * (subplot_height + 0.01))
        y_middle = y_top - (subplot_height / 2)

        annotation['x'] = -0.12  # Position to the left of the y-axis
        annotation['y'] = y_middle  # Position at vertical middle of pane
        annotation['xanchor'] = 'right'  # Align right so text extends left
        annotation['yanchor'] = 'middle'  # Center vertically
        annotation['xref'] = 'paper'
        annotation['yref'] = 'paper'
        annotation['font'] = dict(size=11, family="Open Sans, sans-serif", color=player_color)

    # Update x-axis label for bottom subplot only
    fig.update_xaxes(title_text=score_label, row=num_players, col=1)

    return fig