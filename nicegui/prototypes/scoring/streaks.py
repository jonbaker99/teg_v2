"""Streaks - Comprehensive streak analysis across tournaments.

This page analyzes player streaks including:
- Career maximum and current streaks (good and bad)
- All-time record streaks by type
- Streak analysis within specific windows (TEG, Round, Player)

Corresponds to Streamlit page: streamlit/streaks.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import load_all_data, read_file, STREAKS_PARQUET
from helpers.streak_analysis_processing import (
    prepare_good_streaks_data,
    prepare_bad_streaks_data,
    prepare_current_good_streaks_data,
    prepare_current_bad_streaks_data,
    calculate_window_streaks,
    prepare_record_best_streaks_data,
    prepare_record_worst_streaks_data
)


def streaks_content():
    """Display comprehensive streak analysis."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Streaks').classes('text-h5 font-bold mt-6')
    ui.label('Career streaks, record streaks, and window-based analysis').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA LOADING =====
    state = {
        'all_data': None,
        'streaks_df': None,
        'streak_tables': {},
        'data_loaded': False
    }

    def load_data():
        """Load all streak data once on page load."""
        try:
            state['all_data'] = load_all_data(exclude_teg_50=True)

            # Pre-calculate all streak tables
            state['streak_tables'] = {
                'good_max': prepare_good_streaks_data(state['all_data']),
                'bad_max': prepare_bad_streaks_data(state['all_data']),
                'good_current': prepare_current_good_streaks_data(state['all_data']),
                'bad_current': prepare_current_bad_streaks_data(state['all_data'])
            }

            # Sort all tables by Player
            for key, table in state['streak_tables'].items():
                if 'Player' in table.columns:
                    state['streak_tables'][key] = table.sort_values('Player').reset_index(drop=True)

            # Load streak detail data
            state['streaks_df'] = read_file(STREAKS_PARQUET)

            state['data_loaded'] = True
        except Exception as e:
            print(f'Error loading data: {e}')

    def display_streaks():
        """Display streak analysis in 3 main tabs."""
        try:
            if not state['data_loaded']:
                return

            with ui.tabs() as main_tabs:
                # ===== TAB 1: STREAKS BY PLAYER =====
                with ui.tab('Streaks by Player'):
                    ui.label('Select streak type:').classes('font-semibold mb-3')

                    # Segmented controls for Good/Bad and Max/Current
                    with ui.row().classes('gap-6 mb-4'):
                        category_toggle = ui.toggle(
                            {'good': 'Good', 'bad': 'Bad'},
                            value='good'
                        ).classes('gap-2')

                        type_toggle = ui.toggle(
                            {'max': 'Max', 'current': 'Current'},
                            value='max'
                        ).classes('gap-2')

                    results_area_1 = ui.card().classes('w-full')

                    def update_streaks_by_player():
                        category = category_toggle.value
                        streak_type = type_toggle.value

                        # Select appropriate table
                        if category == 'good':
                            if streak_type == 'max':
                                streaks_summary = state['streak_tables']['good_max']
                            else:
                                streaks_summary = state['streak_tables']['good_current']
                        else:  # bad
                            if streak_type == 'max':
                                streaks_summary = state['streak_tables']['bad_max']
                            else:
                                streaks_summary = state['streak_tables']['bad_current']

                        results_area_1.clear()
                        with results_area_1:
                            ui.html(streaks_summary.to_html(
                                index=False,
                                justify='left',
                                classes='datawrapper-table'
                            ), sanitize=False)
                            ui.label('*: current streak is maximum streak').classes('text-xs text-gray-600 mt-2')

                    category_toggle.on_value_change(lambda: update_streaks_by_player())
                    type_toggle.on_value_change(lambda: update_streaks_by_player())
                    update_streaks_by_player()

                # ===== TAB 2: RECORD STREAKS =====
                with ui.tab('Record Streaks'):
                    ui.label('All-time record streaks for each streak type across all players and tournaments.').classes('text-sm text-gray-600 mb-3')

                    with ui.tabs() as record_tabs:
                        # Sub-tab: Best Streaks
                        with ui.tab('Best Streaks'):
                            best_streaks = prepare_record_best_streaks_data(state['all_data'])
                            ui.html(best_streaks.to_html(
                                index=False,
                                justify='left',
                                classes='datawrapper-table table-left-align centre-2nd'
                            ), sanitize=False)
                            ui.label('*: current streak is record streak').classes('text-xs text-gray-600 mt-2')

                        # Sub-tab: Worst Streaks
                        with ui.tab('Worst Streaks'):
                            worst_streaks = prepare_record_worst_streaks_data(state['all_data'])
                            ui.html(worst_streaks.to_html(
                                index=False,
                                justify='left',
                                classes='datawrapper-table table-left-align centre-2nd'
                            ), sanitize=False)
                            ui.label('*: current streak is record streak').classes('text-xs text-gray-600 mt-2')

                # ===== TAB 3: STREAK DETAIL =====
                with ui.tab('Streak detail'):
                    ui.label('Select filters to analyze streaks within a specific window (TEG, Round, or Player).').classes('text-sm text-gray-600')
                    ui.label('Leave filters blank to see all data.').classes('text-sm text-gray-600 mb-4')

                    # Prepare data for window analysis
                    streaks_df = state['streaks_df'].merge(
                        state['all_data'][['HoleID', 'TEG', 'TEGNum', 'Round', 'Pl', 'Player']],
                        on=['HoleID', 'Pl']
                    )
                    streaks_df = streaks_df.sort_values(['Pl', 'TEGNum', 'Round', 'Career Count'])

                    # Create filter dropdowns
                    with ui.row().classes('gap-4 items-start'):
                        # TEG filter
                        teg_options = ['All'] + sorted(
                            streaks_df['TEG'].unique(),
                            key=lambda x: int(x.split()[1])
                        )
                        teg_selector = ui.select(teg_options, value='All', label='TEG').classes('w-40')

                        # Round filter
                        round_options = ['All'] + sorted(streaks_df['Round'].unique())
                        round_selector = ui.select(round_options, value='All', label='Round').classes('w-40')

                        # Player filter
                        player_options = ['All'] + sorted(streaks_df['Pl'].unique())
                        player_selector = ui.select(player_options, value='All', label='Player').classes('w-40')

                    results_area_3 = ui.card().classes('w-full mt-4')

                    def update_streak_detail():
                        selected_teg = teg_selector.value
                        selected_round = round_selector.value
                        selected_player = player_selector.value

                        # Apply filters
                        filtered_df = streaks_df.copy()

                        if selected_teg != 'All':
                            filtered_df = filtered_df[filtered_df['TEG'] == selected_teg]

                        if selected_round != 'All':
                            filtered_df = filtered_df[filtered_df['Round'] == selected_round]

                        if selected_player != 'All':
                            filtered_df = filtered_df[filtered_df['Pl'] == selected_player]

                        # Build filter summary
                        filter_summary = []
                        if selected_teg != 'All':
                            filter_summary.append(f"TEG: {selected_teg}")
                        if selected_round != 'All':
                            filter_summary.append(f"Round: {selected_round}")
                        if selected_player != 'All':
                            player_name = filtered_df['Player'].iloc[0] if len(filtered_df) > 0 else selected_player
                            filter_summary.append(f"Player: {player_name}")

                        results_area_3.clear()

                        with results_area_3:
                            if filter_summary:
                                ui.label(f"Showing streaks for: {', '.join(filter_summary)}").classes('font-semibold mb-2')
                            else:
                                ui.label("Showing streaks for: All data (career-level)").classes('font-semibold mb-2')

                            ui.label(f"Analyzing {len(filtered_df)} holes").classes('text-sm text-gray-600 mb-3')

                            # Calculate and display results
                            if len(filtered_df) > 0:
                                try:
                                    results_df = calculate_window_streaks(filtered_df)

                                    if len(results_df) > 0:
                                        ui.html(results_df.to_html(
                                            index=False,
                                            justify='left',
                                            classes='datawrapper-table table-left-align centre-3rd'
                                        ), sanitize=False)
                                    else:
                                        ui.label('No streak data available for the selected filters.').classes('text-gray-600')
                                except Exception as e:
                                    ui.label(f'Error calculating streaks: {str(e)}').classes('text-red-600')
                            else:
                                ui.label('No data matches the selected filters.').classes('text-orange-600')

                    teg_selector.on_value_change(lambda: update_streak_detail())
                    round_selector.on_value_change(lambda: update_streak_detail())
                    player_selector.on_value_change(lambda: update_streak_detail())
                    update_streak_detail()

        except Exception as e:
            ui.label(f'Error loading streaks: {str(e)}').classes('text-red-600')
            print(f'Error in streaks: {e}')
            import traceback
            traceback.print_exc()

    # ===== INITIAL LOAD =====
    load_data()
    display_streaks()
