"""Player Performance Over Time - Line chart showing Gross vs Par by TEG.

This page visualizes player performance over time by showing the average
Gross vs. Par score for each player in every TEG. It includes an interactive
line chart and a summary table.

Corresponds to Streamlit page: streamlit/ave_by_teg.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd
import plotly.graph_objects as go

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import load_all_data


def ave_by_teg_content():
    """Display player performance over time with interactive chart."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Player Performance Over Time').classes('text-h5 font-bold mt-6')
    ui.label('Average Gross vs Par score for each player across all TEGs').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA LOADING =====
    state = {
        'all_data': None,
        'data_loaded': False
    }

    def load_data():
        """Load all data once on page load."""
        try:
            state['all_data'] = load_all_data()
            state['data_loaded'] = True
        except Exception as e:
            print(f'Error loading data: {e}')

    def display_performance_chart():
        """Display interactive performance chart and data table."""
        try:
            if not state['data_loaded']:
                return

            # ===== PREPARE DATA FOR CHART =====
            # Calculate mean GrossVP for each player and TEG, then multiply by 18
            graph_data = state['all_data'].groupby(['TEGNum', 'Pl'])['GrossVP'].mean().reset_index()
            graph_data['GrossVP'] = graph_data['GrossVP'] * 18
            graph_data['sort_order'] = graph_data['TEGNum']
            graph_data['TEG'] = 'TEG ' + graph_data['TEGNum'].astype(str)
            graph_data = graph_data.rename(columns={'GrossVP': 'Gross vs Par', 'Pl': 'Player'})

            # ===== CREATE INTERACTIVE CHART =====
            fig = go.Figure()

            # Add traces for each player
            for player in sorted(graph_data['Player'].unique()):
                player_data = graph_data[graph_data['Player'] == player].sort_values('TEGNum')
                fig.add_trace(go.Scatter(
                    x=player_data['TEG'],
                    y=player_data['Gross vs Par'],
                    name=player,
                    mode='lines+markers',
                    line=dict(width=2.5),
                    marker=dict(size=6, line=dict(width=1, color='white'))
                ))

            # Update layout
            fig.update_layout(
                title=None,
                xaxis_title=None,
                yaxis_title='Gross vs Par',
                hovermode='closest',
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=1.02,
                    xanchor='right',
                    x=1,
                    bgcolor='rgba(255,255,255,0)',
                    bordercolor='rgba(0,0,0,0)'
                ),
                plot_bgcolor='#F8F8F8',
                paper_bgcolor='white',
                margin=dict(l=50, r=20, t=20, b=50),
                height=600,
                width=800
            )

            # Update axes styling
            fig.update_xaxes(
                showgrid=False,
                zeroline=False,
                showline=False,
                tickangle=270,
                ticks='',
            )

            fig.update_yaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='#E9E9E9',
                zeroline=False,
                showline=False,
                ticks=''
            )

            # ===== DISPLAY CHART =====
            ui.code('''
load_all_data(exclude_teg_50=True)
aggregate_data(all_data, aggregation_level='TEG')
calculate_average_stats(aggregated_data)
''', language='python').classes('mb-4')

            with ui.card().classes('w-full mb-6'):
                ui.label('Gross vs Par by Player by TEG').classes('text-base font-semibold mb-2')
                ui.label('Click on player in legend to highlight').classes('text-sm text-gray-600 mb-3')
                ui.plotly(fig).classes('w-full')

            # ===== PREPARE DATA TABLE =====
            df_copy = state['all_data'].copy()
            players = df_copy['Pl'].unique()
            player_dfs = []

            for player in sorted(players):
                player_df = df_copy[df_copy['Pl'] == player]
                player_avg = player_df.groupby('TEGNum')['GrossVP'].mean().reset_index()
                player_avg = player_avg.rename(columns={'GrossVP': player})
                player_dfs.append(player_avg)

            merged_df = player_dfs[0]
            for player_df in player_dfs[1:]:
                merged_df = pd.merge(merged_df, player_df, on='TEGNum', how='outer')

            # Multiply all values (except TEGNum) by 18
            merged_df.iloc[:, 1:] = merged_df.iloc[:, 1:] * 18

            # Format TEGNum as 'TEG {TEGNum}'
            merged_df['TEGNum'] = 'TEG ' + merged_df['TEGNum'].astype(str)
            merged_df = merged_df.reset_index(drop=True)

            # Format numbers to 1 decimal place with + prefix
            for col in merged_df.columns:
                if col != 'TEGNum':
                    merged_df[col] = merged_df[col].apply(
                        lambda x: f"{x:+.1f}" if pd.notnull(x) and isinstance(x, (int, float)) else "-"
                    )

            # Rename 'TEGNum' to 'TEG'
            merged_df = merged_df.rename(columns={'TEGNum': 'TEG'})

            # ===== DISPLAY DATA TABLE =====
            with ui.expansion('Data table').classes('w-full'):
                ui.html(merged_df.to_html(
                    index=False,
                    justify='center',
                    classes='datawrapper-table'
                ), sanitize=False)

        except Exception as e:
            ui.label(f'Error loading performance data: {str(e)}').classes('text-red-600')
            print(f'Error in ave_by_teg: {e}')
            import traceback
            traceback.print_exc()

    # ===== INITIAL LOAD =====
    load_data()
    display_performance_chart()
