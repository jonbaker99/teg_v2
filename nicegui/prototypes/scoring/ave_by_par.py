"""Average Score by Par - Performance breakdown by hole par value.

This page displays a breakdown of player performance based on the par of the
hole (Par 3, 4, and 5). It allows users to filter the data by TEG to see
performance in a specific tournament or across all tournaments.

Corresponds to Streamlit page: streamlit/ave_by_par.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import load_all_data, get_teg_filter_options, filter_data_by_teg
from helpers.par_analysis_processing import (
    calculate_par_performance_matrix,
    format_par_performance_table
)


@ui.page('/scoring/ave-by-par')
def ave_by_par_page():
    """Display average score performance broken down by hole par value."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Average Score by Par').classes('text-h5 font-bold mt-6')
    ui.label('Player performance breakdown by hole par value (3, 4, 5)').classes('text-sm text-gray-600')
    ui.separator()

    # ===== CONTROLS =====
    with ui.row().classes('w-full gap-4 items-center'):
        ui.label('Select TEG:').classes('font-semibold')
        teg_selector = ui.select([], label='').classes('w-48')

    ui.separator()

    # ===== DATA DISPLAY AREA =====
    content_area = ui.card().classes('w-full')

    # ===== STATE VARIABLES =====
    state = {
        'all_data': None,
        'teg_options': [],
        'data_loaded': False
    }

    def load_data():
        """Load all data once on page load."""
        try:
            state['all_data'] = load_all_data(exclude_incomplete_tegs=False)
            state['teg_options'] = get_teg_filter_options(state['all_data'])
            teg_selector.set_options(state['teg_options'])

            # Set default to first option (usually "All TEGs")
            if state['teg_options']:
                teg_selector.value = state['teg_options'][0]

            state['data_loaded'] = True
        except Exception as e:
            print(f'Error loading data: {e}')

    def display_par_performance():
        """Load and display par performance analysis."""
        try:
            if not state['data_loaded'] or not teg_selector.value:
                return

            selected_tegnum = teg_selector.value
            filtered_data = filter_data_by_teg(state['all_data'], selected_tegnum)

            # Calculate and format the performance matrix
            par_performance_matrix = calculate_par_performance_matrix(filtered_data)
            formatted_par_table = format_par_performance_table(par_performance_matrix)

            content_area.clear()

            with content_area:
                ui.label('Performance by Hole Par').classes('text-base font-semibold mb-3')
                ui.html(formatted_par_table.to_html(
                    classes='dataframe, datawrapper-table full-width',
                    index=False,
                    justify='left'
                ), sanitize=False)

        except Exception as e:
            content_area.clear()
            with content_area:
                ui.label(f'Error loading par performance: {str(e)}').classes('text-red-600')
                print(f'Error in ave_by_par: {e}')
                import traceback
                traceback.print_exc()

    # ===== EVENT HANDLERS =====
    teg_selector.on_value_change(lambda: display_par_performance())

    # ===== INITIAL LOAD =====
    load_data()
    if state['data_loaded'] and state['teg_options']:
        display_par_performance()
