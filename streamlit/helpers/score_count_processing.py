"""
Data processing functions for score distribution analysis.

This module contains functions for:
- Counting score distributions by player
- Creating percentage distribution charts
- Filtering data by TEG and par value
- Formatting score count data for display
"""

import pandas as pd
import plotly.express as px
import streamlit as st


def get_filtering_options(all_data):
    """
    Get filtering options for score count analysis.
    
    Args:
        all_data (pd.DataFrame): Complete tournament data
        
    Returns:
        tuple: (tegnum_options, par_options) for dropdown selections
        
    Purpose:
        Provides filtering options for score distribution analysis
        Enables focused analysis by tournament or par value
    """
    tegnum_options = ['All TEGs'] + sorted(all_data['TEGNum'].unique().tolist(), reverse=True)
    par_options = ['All holes'] + sorted(all_data['PAR'].unique().tolist())
    
    return tegnum_options, par_options


def apply_teg_and_par_filters(all_data, selected_tegnum, selected_par):
    """
    Apply TEG and par filters to tournament data.
    
    Args:
        all_data (pd.DataFrame): Complete tournament data
        selected_tegnum: Selected TEG number or "All TEGs"
        selected_par: Selected par value or "All holes"
        
    Returns:
        tuple: (filtered_data, teg_desc, par_desc) for analysis and display
        
    Purpose:
        Applies user-selected filters for score distribution analysis
        Returns descriptive labels for chart titles and captions
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


def count_scores_by_player(df, field='GrossVP'):
    """
    Count score distributions by player.
    
    Args:
        df (pd.DataFrame): Filtered tournament data
        field (str): Score field to analyze ('GrossVP' or 'Sc')
        
    Returns:
        pd.DataFrame: Score count matrix with players as columns, scores as rows
        
    Purpose:
        Creates distribution matrix showing how many times each player achieved each score
        Enables comparison of scoring patterns across players
        Sorted by score value for logical display order
    """
    # Group by score and player, count occurrences
    summary = df.groupby([field, 'Pl']).size().unstack(fill_value=0)
    
    # Sort by score value (ascending for logical order)
    summary = summary.sort_index(ascending=True)
    
    # Sort columns (players) alphabetically
    summary = summary.sort_index(axis=1)
    
    return summary


def create_percentage_distribution_chart(df, teg_desc, par_desc):
    """
    Create percentage distribution bar chart for score counts.
    
    Args:
        df (pd.DataFrame): Score count data with first column as index
        teg_desc (str): TEG description for chart title
        par_desc (str): Par description for chart title
        
    Returns:
        plotly.graph_objects.Figure: Percentage distribution bar chart
        
    Purpose:
        Creates visual representation of score distributions as percentages
        Shows relative frequency of each score for each player
        Enables pattern recognition across different scoring categories
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


def prepare_score_count_display(count_data, score_field, display_name, is_percentage=False):
    """
    Prepare score count data for table display.

    Args:
        count_data (pd.DataFrame): Raw score count matrix or percentage data
        score_field (str): Original score field name
        display_name (str): User-friendly display name
        is_percentage (bool): Whether data contains percentages that need formatting

    Returns:
        pd.DataFrame: Formatted data ready for display

    Purpose:
        Formats score count data for clean table display
        Handles data type conversions and column renaming
        Resets index to make score field a regular column
        Applies percentage formatting when needed
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


def prepare_chart_data_with_special_handling(display_data, score_field):
    """
    Prepare data for chart with special value handling.
    
    Args:
        display_data (pd.DataFrame): Formatted display data
        score_field (str): Original score field name
        
    Returns:
        pd.DataFrame: Chart-ready data with special values converted
        
    Purpose:
        Handles special formatting cases for charting
        Converts formatted values back to numeric for proper chart display
        Specifically handles "=" (even par) conversion to 0
    """
    chart_data = display_data.copy()
    
    # Handle special case for vs par data (convert "=" back to 0 for charting)
    if score_field == 'GrossVP':
        display_column = 'vs Par'
        chart_data.loc[chart_data[display_column] == '=', display_column] = 0
    
    return chart_data


def convert_counts_to_percentages(count_data):
    """
    Convert score count data to percentage distribution per player.

    Args:
        count_data (pd.DataFrame): Raw score count matrix with scores as rows, players as columns

    Returns:
        pd.DataFrame: Percentage distribution where each player's column sums to 100%

    Purpose:
        Converts absolute counts to percentages for relative comparison across players
        Each player's scores sum to 100%, enabling pattern recognition regardless of total holes played
    """
    # Calculate percentage of total for each player (column-wise)
    percentage_data = count_data.div(count_data.sum(axis=0), axis=1) * 100

    # Round to 1 decimal place for clean display
    percentage_data = percentage_data.round(1)

    return percentage_data


def format_percentage_for_display(percentage_data):
    """
    Format percentage data for table display with % symbols.

    Args:
        percentage_data (pd.DataFrame): Percentage data with numeric values

    Returns:
        pd.DataFrame: Formatted data with percentages as strings with % symbols

    Purpose:
        Converts numeric percentage values to formatted strings for clean table display
        Applies consistent formatting as "25.5%" for readability
    """
    # Create a copy to avoid modifying original data
    formatted_data = percentage_data.copy()

    # Apply percentage formatting to all numeric columns
    for col in formatted_data.columns:
        if pd.api.types.is_numeric_dtype(formatted_data[col]):
            formatted_data[col] = formatted_data[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "0.0%")

    return formatted_data


def create_stacked_bar_chart(count_data, teg_desc, par_desc, score_field):
    """
    Create stacked bar chart showing score distribution by player.

    Args:
        count_data (pd.DataFrame): Score count matrix with scores as rows, players as columns
        teg_desc (str): TEG description for chart title
        par_desc (str): Par description for chart title
        score_field (str): Score field being analyzed ('GrossVP' or 'Sc')

    Returns:
        plotly.graph_objects.Figure: Stacked bar chart with one column per player

    Purpose:
        Creates visual representation of score distributions as stacked bars
        Each player gets one column, with score types stacked and colored
        Shows relative scoring patterns across players
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