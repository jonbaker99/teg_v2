"""Scorecard Viewer - Display and compare scorecards in multiple formats.

This page allows users to view detailed scorecards in three different formats:
1. Single Round / Single Player - One player's 18-hole scorecard for a specific round
2. Single Player / All Rounds - All rounds for one player in a tournament
3. Single Round / All Players - All players' scores side-by-side for one round

Supports Desktop and Mobile layout options for each view type.

Corresponds to Streamlit page: streamlit/scorecard_v2.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import load_all_data, get_scorecard_data
from scorecard_utils import (
    load_scorecard_css,
    generate_single_round_html,
    generate_tournament_html,
    generate_round_comparison_html,
    generate_single_round_html_mobile,
    generate_tournament_html_mobile,
    generate_round_comparison_html_mobile
)
from helpers.scorecard_data_processing import (
    prepare_scorecard_selection_options,
    get_round_options_for_tournament,
    validate_and_prepare_single_round_data
)


@ui.page('/scorecard/scorecard')
def scorecard_page():
    """Display and compare scorecards in multiple formats."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Scorecards').classes('text-h5 font-bold mt-6')
    ui.label('View detailed scorecards in multiple formats').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA LOADING =====
    state = {
        'all_data': None,
        'selection_options': None,
        'data_loaded': False,
        'scorecard_layout': 'Desktop',
        'scorecard_type': '1 Round / 1 Player',
        'selected_player': None,
        'selected_teg': None,
        'selected_round': None
    }

    def load_data():
        """Load all data once on page load."""
        try:
            state['all_data'] = load_all_data(exclude_incomplete_tegs=False)
            state['selection_options'] = prepare_scorecard_selection_options(state['all_data'])
            state['data_loaded'] = True

            # Initialize dropdowns
            if state['selection_options']['players']:
                player_selector.set_options(state['selection_options']['players'])
                state['selected_player'] = state['selection_options']['players'][0]
                player_selector.value = state['selected_player']

            if state['selection_options']['tournaments']:
                teg_selector.set_options(state['selection_options']['tournaments'])
                state['selected_teg'] = state['selection_options']['tournaments'][-1]
                teg_selector.value = state['selected_teg']

                # Set up rounds for initial TEG
                round_options = get_round_options_for_tournament(state['all_data'], state['selected_teg'])
                round_selector.set_options(round_options)
                if round_options:
                    state['selected_round'] = round_options[-1]
                    round_selector.value = state['selected_round']

        except Exception as e:
            print(f'Error loading data: {e}')

    # ===== CONTROLS SECTION =====
    with ui.expansion('Scorecard selection', open=True):
        with ui.column().classes('w-full gap-4'):
            # Layout selection
            with ui.row().classes('w-full gap-4 items-center'):
                ui.label('Scorecard layout:').classes('font-semibold')
                layout_toggle = ui.toggle(
                    ['Desktop', 'Mobile'],
                    value='Desktop'
                )

            # Scorecard type selection
            with ui.column():
                ui.label('Choose scorecard type:').classes('font-semibold')
                type_radio = ui.radio(
                    ['1 Round / 1 Player', '1 Player / All Rounds', '1 Round / All Players'],
                    value='1 Round / 1 Player'
                )

            # Selection controls
            ui.label('Scorecard selection').classes('font-semibold text-sm')

            with ui.row().classes('w-full gap-4'):
                with ui.column():
                    player_selector = ui.select([], label='Player').classes('w-40')

                with ui.column():
                    teg_selector = ui.select([], label='Tournament').classes('w-40')

                with ui.column():
                    round_selector = ui.select([], label='Round').classes('w-40')

    ui.separator()

    # ===== DATA DISPLAY AREA =====
    display_area = ui.card().classes('w-full')

    def update_display():
        """Update the displayed scorecard."""
        try:
            if not state['data_loaded'] or not state['selected_player'] or not state['selected_teg']:
                return

            display_area.clear()

            with display_area:
                scorecard_type = type_radio.value
                layout = layout_toggle.value

                # ===== SINGLE PLAYER ROUND SCORECARD =====
                if scorecard_type == "1 Round / 1 Player":
                    if not state['selected_round']:
                        ui.label('No round data available').classes('text-gray-600')
                        return

                    try:
                        rd_data = get_scorecard_data(
                            state['selected_teg'],
                            state['selected_round'],
                            state['selected_player']
                        )

                        is_valid, prepared_data, error_message = validate_and_prepare_single_round_data(rd_data)

                        if not is_valid:
                            ui.label(f'Error: {error_message}').classes('text-red-600')
                        else:
                            # Extract TEG number from TEG string
                            teg_num = int(state['selected_teg'].split()[-1])

                            if layout == "Desktop":
                                scorecard_html = generate_single_round_html(
                                    state['selected_player'],
                                    teg_num,
                                    state['selected_round']
                                )
                            else:
                                scorecard_html = generate_single_round_html_mobile(
                                    state['selected_player'],
                                    teg_num,
                                    state['selected_round']
                                )

                            ui.html(scorecard_html, sanitize=False)
                    except Exception as e:
                        ui.label(f'Error loading scorecard: {str(e)}').classes('text-red-600')

                # ===== TOURNAMENT VIEW (ONE PLAYER, ALL ROUNDS) =====
                elif scorecard_type == "1 Player / All Rounds":
                    try:
                        tournament_data = get_scorecard_data(
                            state['selected_teg'],
                            player_code=state['selected_player']
                        )

                        if len(tournament_data) == 0:
                            ui.label('No data found for the selected player and tournament').classes('text-gray-600')
                        else:
                            teg_num = int(state['selected_teg'].split()[-1])

                            if layout == "Desktop":
                                tournament_html = generate_tournament_html(
                                    state['selected_player'],
                                    teg_num
                                )
                            else:
                                tournament_html = generate_tournament_html_mobile(
                                    state['selected_player'],
                                    teg_num
                                )

                            ui.html(tournament_html, sanitize=False)
                    except Exception as e:
                        ui.label(f'Error loading tournament scorecard: {str(e)}').classes('text-red-600')

                # ===== ROUND COMPARISON (ALL PLAYERS, ONE ROUND) =====
                elif scorecard_type == "1 Round / All Players":
                    if not state['selected_round']:
                        ui.label('No round data available').classes('text-gray-600')
                        return

                    try:
                        comparison_data = get_scorecard_data(
                            state['selected_teg'],
                            state['selected_round']
                        )

                        if len(comparison_data) == 0:
                            ui.label('No data found for the selected tournament and round').classes('text-gray-600')
                        else:
                            teg_num = int(state['selected_teg'].split()[-1])

                            if layout == "Desktop":
                                comparison_html = generate_round_comparison_html(
                                    teg_num,
                                    state['selected_round']
                                )
                            else:
                                comparison_html = generate_round_comparison_html_mobile(
                                    teg_num,
                                    state['selected_round']
                                )

                            ui.html(comparison_html, sanitize=False)
                    except Exception as e:
                        ui.label(f'Error loading round comparison: {str(e)}').classes('text-red-600')

        except Exception as e:
            display_area.clear()
            with display_area:
                ui.label(f'Error loading scorecard: {str(e)}').classes('text-red-600')
                print(f'Error in scorecard: {e}')
                import traceback
                traceback.print_exc()

    # ===== EVENT HANDLERS =====
    def handle_layout_change():
        state['scorecard_layout'] = layout_toggle.value
        update_display()

    def handle_type_change():
        state['scorecard_type'] = type_radio.value
        # Update control disabled states based on new type
        update_control_states()
        update_display()

    def handle_player_change():
        state['selected_player'] = player_selector.value
        update_display()

    def handle_teg_change():
        state['selected_teg'] = teg_selector.value
        # Update round options when TEG changes
        if state['data_loaded']:
            round_options = get_round_options_for_tournament(state['all_data'], state['selected_teg'])
            round_selector.set_options(round_options)
            if round_options:
                state['selected_round'] = round_options[-1]
                round_selector.value = state['selected_round']
        update_display()

    def handle_round_change():
        state['selected_round'] = round_selector.value
        update_display()

    def update_control_states():
        """Update control disabled states based on scorecard type."""
        scorecard_type = type_radio.value

        # Determine which controls should be disabled
        if scorecard_type == "1 Round / 1 Player":
            # Player and Round enabled, TEG always enabled
            player_selector.enabled = True
            round_selector.enabled = True
        elif scorecard_type == "1 Player / All Rounds":
            # Player enabled, Round disabled
            player_selector.enabled = True
            round_selector.enabled = False
        elif scorecard_type == "1 Round / All Players":
            # Player disabled, Round enabled
            player_selector.enabled = False
            round_selector.enabled = True

    layout_toggle.on_value_change(handle_layout_change)
    type_radio.on_value_change(handle_type_change)
    player_selector.on_value_change(handle_player_change)
    teg_selector.on_value_change(handle_teg_change)
    round_selector.on_value_change(handle_round_change)

    # ===== INITIAL LOAD =====
    load_data()
    update_control_states()
    if state['data_loaded']:
        update_display()
