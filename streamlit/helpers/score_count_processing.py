"""Data processing functions for score distribution analysis.

This module contains functions for counting score distributions by player,
creating percentage distribution charts, filtering data by TEG and par value,
and formatting score count data for display.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import numpy as np


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