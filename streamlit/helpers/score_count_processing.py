"""Data processing functions for score distribution analysis.

This module contains functions for counting score distributions by player,
creating percentage distribution charts, filtering data by TEG and par value,
and formatting score count data for display.
"""

import pandas as pd
import plotly.express as px
import streamlit as st


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