"""Best/Worstball Analysis - Team format comparison of best and worst hole scores.

This page displays bestball (best score per hole across team) and worstball (worst score
per hole across team) performances. Users can:
- Switch between Bestball and Worstball views
- Filter by TEG tournament
- Customize sorting order (Normal/Reversed) and number of rows displayed

Corresponds to Streamlit page: streamlit/bestball.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import (
    read_file,
    get_teg_filter_options,
    filter_data_by_teg,
    BESTBALL_PARQUET
)
from helpers.bestball_processing import format_team_scores_for_display


@ui.page('/scorecard/best-worstball')
def best_worstball_page():
    """Display best and worst ball team performances."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Best/Worstball').classes('text-h5 font-bold mt-6')
    ui.label('Shows best & worst bestball / worstball across all players in a round').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA LOADING =====
    state = {
        'all_bestball_data': None,
        'data_loaded': False,
        'view_mode': 'Bestball',
        'selected_teg': None,
        'sort_order': 'Normal',
        'n_rows': 3
    }

    def load_data():
        """Load bestball/worstball data."""
        try:
            state['all_bestball_data'] = read_file(BESTBALL_PARQUET)
            state['data_loaded'] = True

            # Set initial values
            teg_options = get_teg_filter_options(state['all_bestball_data'])
            if teg_options:
                state['selected_teg'] = teg_options[0]
                teg_selector.set_options(teg_options)
                teg_selector.value = state['selected_teg']

        except FileNotFoundError:
            ui.label(f'Bestball data file not found at {BESTBALL_PARQUET}').classes('text-red-600')
            state['data_loaded'] = False

    # ===== CONTROLS =====
    with ui.row().classes('w-full gap-4 items-center mb-4'):
        ui.label('View:').classes('font-semibold')
        view_toggle = ui.toggle(
            ['Bestball', 'Worstball'],
            value='Bestball'
        )

    with ui.expansion('More display options'):
        with ui.column().classes('w-full gap-4'):
            # TEG selection
            with ui.row().classes('w-full gap-4 items-center'):
                ui.label('Select TEG:').classes('font-semibold')
                teg_selector = ui.select([], label='').classes('w-48')

            # Sort order and number of rows in two columns
            with ui.row().classes('w-full gap-4'):
                with ui.column():
                    ui.label('Sort order:').classes('font-semibold')
                    sort_toggle = ui.toggle(
                        ['Normal', 'Reversed'],
                        value='Normal'
                    )

                with ui.column():
                    ui.label('Number of rows to show:').classes('font-semibold')
                    n_rows_spinner = ui.number(value=3, min=1, max=100, step=1).classes('w-32')

    ui.separator()

    # ===== DATA DISPLAY AREA =====
    display_area = ui.card().classes('w-full')

    def update_display():
        """Update the displayed table based on current selections."""
        try:
            if not state['data_loaded'] or not state['selected_teg']:
                return

            display_area.clear()

            with display_area:
                # Determine best_or_worst label
                is_bestball = state['view_mode'] == 'Bestball'
                is_normal = state['sort_order'] == 'Normal'
                best_or_worst = "Best" if (is_bestball) == (is_normal) else "Worst"
                sort_by_best = best_or_worst == "Best"

                # Filter data by TEG
                filtered_data = filter_data_by_teg(
                    state['all_bestball_data'],
                    state['selected_teg']
                )

                # Separate by format
                bestball_data = filtered_data[filtered_data['Format'] == 'Bestball']
                worstball_data = filtered_data[filtered_data['Format'] == 'Worstball']

                # Format data
                bestball_output = format_team_scores_for_display(bestball_data, sort_by_best)
                worstball_output = format_team_scores_for_display(worstball_data, sort_by_best)

                # Apply row limit
                bestball_output = bestball_output.head(state['n_rows']).drop(columns='TEGNum', errors='ignore')
                worstball_output = worstball_output.head(state['n_rows']).drop(columns='TEGNum', errors='ignore')

                # Select appropriate data to display
                output = bestball_output if state['view_mode'] == 'Bestball' else worstball_output

                # Display title and table
                ui.label(f"{best_or_worst} {state['view_mode'].lower()}").classes('text-base font-semibold mb-3')
                ui.html(output.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ), sanitize=False)

        except Exception as e:
            display_area.clear()
            with display_area:
                ui.label(f'Error loading data: {str(e)}').classes('text-red-600')
                print(f'Error in best_worstball: {e}')
                import traceback
                traceback.print_exc()

    # ===== EVENT HANDLERS =====
    def handle_view_change():
        state['view_mode'] = view_toggle.value
        update_display()

    def handle_teg_change():
        state['selected_teg'] = teg_selector.value
        update_display()

    def handle_sort_change():
        state['sort_order'] = sort_toggle.value
        update_display()

    def handle_rows_change():
        state['n_rows'] = int(n_rows_spinner.value)
        update_display()

    view_toggle.on_value_change(handle_view_change)
    teg_selector.on_value_change(handle_teg_change)
    sort_toggle.on_value_change(handle_sort_change)
    n_rows_spinner.on_value_change(handle_rows_change)

    # ===== INITIAL LOAD =====
    load_data()
    if state['data_loaded']:
        update_display()
