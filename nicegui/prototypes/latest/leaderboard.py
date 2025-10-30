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
from teg_analysis.display.html_tables import create_round_leaderboard_html


def leaderboard_content():
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
                try:
                    # Generate leaderboard with round-by-round breakdown
                    # For latest TEG (assumed to be >= TEG 6), use Stableford
                    leaderboard_html = create_round_leaderboard_html(
                        teg_data,
                        measure='Stableford',
                        ascending=False,  # Higher is better for Stableford
                        title='Net Competition Leaderboard'
                    )
                    ui.html(leaderboard_html, sanitize=False)
                except Exception as e:
                    ui.label(f'Error loading Net leaderboard: {str(e)}').classes('text-red-600')

            # ===== TAB 2: GREEN JACKET (GROSS) =====
            with ui.tab('Green Jacket (Gross)'):
                try:
                    # Generate leaderboard with round-by-round breakdown
                    leaderboard_html = create_round_leaderboard_html(
                        teg_data,
                        measure='GrossVP',
                        ascending=True,  # Lower is better for GrossVP
                        title='Gross Competition Leaderboard'
                    )
                    ui.html(leaderboard_html, sanitize=False)
                except Exception as e:
                    ui.label(f'Error loading Gross leaderboard: {str(e)}').classes('text-red-600')

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
