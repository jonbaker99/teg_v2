"""Latest Leaderboard - Current tournament leaderboard and progress tracking.

This page displays the leaderboard for the most recent TEG with:
- TEG Trophy and Spoon (Net competition) leaderboard
- Green Jacket (Gross competition) leaderboard
- Round-by-round scorecards
- Cumulative progress charts with multiple viewing modes

Corresponds to Streamlit page: streamlit/leaderboard.py
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
from utils import load_all_data, get_teg_rounds, get_round_data
from scorecard_utils import generate_round_comparison_html


@ui.page('/latest/leaderboard')
def leaderboard_page():
    """Display current tournament leaderboard and progress."""

    ui.label('Latest Leaderboard').classes('text-h5 font-bold mt-6')
    ui.label('Current tournament leaderboard and cumulative progress').classes('text-sm text-gray-600')
    ui.separator()

    try:
        all_data = load_all_data(exclude_incomplete_tegs=False)

        if all_data.empty:
            ui.label('No tournament data available').classes('text-gray-600')
            return

        # Get latest TEG
        latest_teg = all_data['TEGNum'].max()
        teg_data = all_data[all_data['TEGNum'] == latest_teg]

        if teg_data.empty:
            ui.label(f'No data for TEG {latest_teg}').classes('text-gray-600')
            return

        num_rounds = get_teg_rounds(latest_teg)

        with ui.tabs() as tabs:
            # ===== TAB 1: TEG TROPHY (NET) =====
            with ui.tab('TEG Trophy (Net)'):
                ui.label('Net Competition Leaderboard').classes('text-base font-semibold mb-3')

                # Aggregate by player
                from teg_analysis.analysis.aggregation import aggregate_data
                agg_data = aggregate_data(teg_data, aggregation_level='Player')

                if not agg_data.empty and 'Stableford' in agg_data.columns:
                    leaderboard = agg_data.sort_values('Stableford', ascending=False)
                    leaderboard.insert(0, 'Rank', range(1, len(leaderboard) + 1))
                    ui.html(leaderboard.to_html(
                        index=False,
                        escape=False,
                        classes='datawrapper-table'
                    ), sanitize=False)
                else:
                    ui.label('No leaderboard data available').classes('text-gray-600')

            # ===== TAB 2: GREEN JACKET (GROSS) =====
            with ui.tab('Green Jacket (Gross)'):
                ui.label('Gross Competition Leaderboard').classes('text-base font-semibold mb-3')

                from teg_analysis.analysis.aggregation import aggregate_data
                agg_data = aggregate_data(teg_data, aggregation_level='Player')

                if not agg_data.empty and 'GrossVP' in agg_data.columns:
                    leaderboard = agg_data.sort_values('GrossVP', ascending=True)
                    leaderboard.insert(0, 'Rank', range(1, len(leaderboard) + 1))
                    ui.html(leaderboard.to_html(
                        index=False,
                        escape=False,
                        classes='datawrapper-table'
                    ), sanitize=False)
                else:
                    ui.label('No leaderboard data available').classes('text-gray-600')

            # ===== TAB 3: SCORECARDS =====
            with ui.tab('Scorecards'):
                with ui.tabs() as scorecard_tabs:
                    for round_num in range(1, num_rounds + 1):
                        with ui.tab(f'Round {round_num}'):
                            try:
                                scorecard_html = generate_round_comparison_html(latest_teg, round_num)
                                ui.html(scorecard_html, sanitize=False)
                            except Exception as e:
                                ui.label(f'Error loading Round {round_num}: {str(e)}').classes('text-red-600')

    except Exception as e:
        ui.label(f'Error loading leaderboard: {str(e)}').classes('text-red-600')
        print(f'Error in leaderboard: {e}')
        import traceback
        traceback.print_exc()
