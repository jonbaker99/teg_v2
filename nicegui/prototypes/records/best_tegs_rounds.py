"""Top TEGs and Rounds - Display best and worst TEGs/rounds by measure.

This page allows users to explore the best and worst TEGs and individual
rounds based on different scoring measures (Gross, Score, Net, Stableford).

Corresponds to Streamlit page: streamlit/301Best_TEGs_and_Rounds.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import get_ranked_teg_data, get_ranked_round_data
from helpers.best_performance_processing import (
    get_measure_name_mappings,
    prepare_best_teg_table,
    prepare_best_round_table,
    prepare_worst_teg_table,
    prepare_worst_round_table,
    prepare_round_data_with_identifiers
)


def best_tegs_rounds_content():
    """Display top TEGs and rounds by selected measure."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Top TEGs and Rounds').classes('text-h5 font-bold mt-6')
    ui.label('Best and worst performances by scoring measure').classes('text-sm text-gray-600')
    ui.separator()

    # ===== CONTROLS =====
    with ui.row().classes('w-full gap-4 items-center'):
        ui.label('Measure:').classes('font-semibold')

        # Get measure mappings for friendly names
        name_mapping, _ = get_measure_name_mappings()
        friendly_names = list(name_mapping.keys())

        measure_selector = ui.select(friendly_names, value=friendly_names[0]).classes('w-48')

        ui.label('Records to show:').classes('font-semibold ml-6')
        n_records_input = ui.number(
            value=3, min=1, max=100, step=1
        ).classes('w-24')

    ui.separator()

    # ===== DATA DISPLAY AREA =====
    content_area = ui.card().classes('w-full')

    # ===== STATE VARIABLES =====
    state = {
        'teg_data_ranked': None,
        'rd_data_formatted': None
    }

    def load_data():
        """Load all data once on page load."""
        try:
            teg_data = get_ranked_teg_data()
            rd_data = get_ranked_round_data()
            state['teg_data_ranked'] = teg_data
            state['rd_data_formatted'] = prepare_round_data_with_identifiers(rd_data)
        except Exception as e:
            print(f'Error loading data: {e}')

    def display_results():
        """Load and display best/worst TEGs and rounds."""
        try:
            if state['teg_data_ranked'] is None or state['rd_data_formatted'] is None:
                return

            selected_friendly_name = measure_selector.value
            selected_measure = name_mapping.get(selected_friendly_name, selected_friendly_name)
            n_keep = int(n_records_input.value)

            content_area.clear()

            with content_area:
                # ===== TABS FOR BEST/WORST =====
                with ui.tabs() as tabs:
                    # Tab 1: Best TEGs
                    with ui.tab('Best TEGs'):
                        ui.label(f'Top {n_keep} TEGs: {selected_friendly_name}').classes('text-base font-semibold mb-3')
                        best_tegs_table = prepare_best_teg_table(
                            state['teg_data_ranked'],
                            selected_measure,
                            selected_friendly_name,
                            n_keep
                        )
                        ui.html(best_tegs_table.to_html(
                            escape=False,
                            index=False,
                            justify='left',
                            classes='datawrapper-table narrow-first left-second'
                        ), sanitize=False)

                    # Tab 2: Best Rounds
                    with ui.tab('Best Rounds'):
                        ui.label(f'Top {n_keep} Rounds: {selected_friendly_name}').classes('text-base font-semibold mb-3')
                        best_rounds_table = prepare_best_round_table(
                            state['rd_data_formatted'],
                            selected_measure,
                            selected_friendly_name,
                            n_keep
                        )
                        ui.html(best_rounds_table.to_html(
                            escape=False,
                            index=False,
                            justify='left',
                            classes='datawrapper-table narrow-first left-second'
                        ), sanitize=False)

                    # Tab 3: Worst TEGs
                    with ui.tab('Worst TEGs'):
                        ui.label(f'Worst {n_keep} TEGs: {selected_friendly_name}').classes('text-base font-semibold mb-3')
                        worst_tegs_table = prepare_worst_teg_table(
                            state['teg_data_ranked'],
                            selected_measure,
                            selected_friendly_name,
                            n_keep
                        )
                        ui.html(worst_tegs_table.to_html(
                            escape=False,
                            index=False,
                            justify='left',
                            classes='datawrapper-table narrow-first left-second'
                        ), sanitize=False)

                    # Tab 4: Worst Rounds
                    with ui.tab('Worst Rounds'):
                        ui.label(f'Worst {n_keep} Rounds: {selected_friendly_name}').classes('text-base font-semibold mb-3')
                        worst_rounds_table = prepare_worst_round_table(
                            state['rd_data_formatted'],
                            selected_measure,
                            selected_friendly_name,
                            n_keep
                        )
                        ui.html(worst_rounds_table.to_html(
                            escape=False,
                            index=False,
                            justify='left',
                            classes='datawrapper-table narrow-first left-second'
                        ), sanitize=False)

                ui.separator().classes('my-4')

                # ===== NOTES =====
                ui.label('Note: TEG 2 is excluded from all TEG-level analysis as it only had 3 rounds compared to the standard 4 rounds.').classes('text-sm text-gray-600')

        except Exception as e:
            content_area.clear()
            with content_area:
                ui.label(f'Error loading results: {str(e)}').classes('text-red-600')
                print(f'Error in best_tegs_rounds: {e}')
                import traceback
                traceback.print_exc()

    # ===== EVENT HANDLERS =====
    measure_selector.on_value_change(lambda: display_results())
    n_records_input.on_value_change(lambda: display_results())

    # ===== INITIAL LOAD =====
    load_data()
    display_results()
