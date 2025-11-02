"""Personal Bests & Worsts - Each player's best and worst performances.

This page provides a detailed view of each player's personal best and worst
performances, categorized by TEGs and individual rounds.

Corresponds to Streamlit page: streamlit/302Personal Best Rounds & TEGs.py
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
    get_ranked_teg_data,
    get_ranked_round_data,
    get_ranked_frontback_data
)
from helpers.best_performance_processing import (
    get_measure_name_mappings,
    prepare_personal_best_teg_table,
    prepare_personal_best_round_table,
    prepare_personal_worst_teg_table,
    prepare_personal_worst_round_table,
    prepare_round_data_with_identifiers,
    prepare_pb_teg_summary_table,
    prepare_pb_round_summary_table,
    prepare_pb_nine_summary_table
)


def personal_best_content():
    """Display personal bests and worsts for each player."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Personal Bests & Worsts').classes('text-h5 font-bold mt-6')
    ui.label('Each player\'s best and worst performances by category').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA DISPLAY AREA =====
    content_area = ui.card().classes('w-full')

    # ===== STATE VARIABLES =====
    state = {
        'teg_data_ranked': None,
        'rd_data_formatted': None,
        'nine_data_ranked': None,
        'pb_teg_summary': None,
        'pb_round_summary': None,
        'pb_nine_summary': None,
        'data_loaded': False
    }

    def load_data():
        """Load all data once on page load."""
        try:
            teg_data = get_ranked_teg_data()
            rd_data = get_ranked_round_data()
            nine_data = get_ranked_frontback_data()
            rd_data_formatted = prepare_round_data_with_identifiers(rd_data)

            state['teg_data_ranked'] = teg_data
            state['rd_data_formatted'] = rd_data_formatted
            state['nine_data_ranked'] = nine_data
            state['pb_teg_summary'] = prepare_pb_teg_summary_table(teg_data)
            state['pb_round_summary'] = prepare_pb_round_summary_table(rd_data)
            state['pb_nine_summary'] = prepare_pb_nine_summary_table(nine_data)
            state['data_loaded'] = True
        except Exception as e:
            print(f'Error loading data: {e}')

    def display_personal_best():
        """Load and display personal best data."""
        try:
            if not state['data_loaded']:
                return

            name_mapping, _ = get_measure_name_mappings()
            friendly_names = list(name_mapping.keys())

            content_area.clear()

            with content_area:
                ui.code('''
load_all_data(exclude_teg_50=True)
read_file(STREAKS_PARQUET)
identify_aggregate_records_and_pbs(all_data, aggregation_level='Player')
identify_all_time_worsts(all_data)
identify_streak_records(all_data, streaks_df)
identify_score_count_records(all_data)
''', language='python').classes('mb-4')
                # ===== SECTION STATE =====
                section_state = {'current': 'pb_summary'}

                def set_section(section_id):
                    section_state['current'] = section_id

                # ===== BUTTON BAR =====
                with ui.row().classes('gap-2 mb-4'):
                    ui.button('PB Summary', on_click=lambda: set_section('pb_summary'))
                    ui.button('Best TEGs', on_click=lambda: set_section('best_tegs'))
                    ui.button('Best Rounds', on_click=lambda: set_section('best_rounds'))
                    ui.button('Worst TEGs', on_click=lambda: set_section('worst_tegs'))
                    ui.button('Worst Rounds', on_click=lambda: set_section('worst_rounds'))

                # ===== SECTION 1: PB SUMMARY =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'pb_summary')
                with card:
                    ui.label('Summary View:').classes('font-semibold mb-2')
                    with ui.row().classes('gap-4'):
                        summary_toggle = ui.toggle(
                            {'rounds': 'Best Rounds', 'tegs': 'Best TEGs', 'nines': 'Best 9s'},
                            value='rounds'
                        ).classes('gap-2')

                    summary_area = ui.card().classes('w-full mt-4')

                    def update_summary():
                        summary_area.clear()
                        with summary_area:
                            if summary_toggle.value == 'rounds':
                                ui.label('Personal Best Rounds').classes('text-base font-semibold mb-3')
                                ui.html(state['pb_round_summary'].to_html(
                                    escape=False,
                                    index=False,
                                    justify='left',
                                    classes='datawrapper-table table-left-align pb-table'
                                ), sanitize=False)
                            elif summary_toggle.value == 'tegs':
                                ui.label('Personal Best TEGs').classes('text-base font-semibold mb-3')
                                ui.html(state['pb_teg_summary'].to_html(
                                    escape=False,
                                    index=False,
                                    justify='left',
                                    classes='datawrapper-table table-left-align pb-table'
                                ), sanitize=False)
                            else:  # nines
                                ui.label('Personal Best 9s').classes('text-base font-semibold mb-3')
                                ui.html(state['pb_nine_summary'].to_html(
                                    escape=False,
                                    index=False,
                                    justify='left',
                                    classes='datawrapper-table table-left-align pb-table'
                                ), sanitize=False)

                    summary_toggle.on_value_change(lambda: update_summary())
                    update_summary()

                # ===== SECTION 2: BEST TEGs =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'best_tegs')
                with card:
                    ui.label('Measure:').classes('font-semibold mb-3')
                    measure_selector_2 = ui.select(friendly_names, value=friendly_names[0]).classes('w-48')
                    results_area_2 = ui.card().classes('w-full mt-4')

                    def update_best_tegs():
                        selected_friendly_name = measure_selector_2.value
                        selected_measure = name_mapping.get(selected_friendly_name, selected_friendly_name)
                        results_area_2.clear()
                        with results_area_2:
                            ui.label(f'Personal Best TEGs: {selected_friendly_name}').classes('text-base font-semibold mb-3')
                            personal_best_tegs = prepare_personal_best_teg_table(
                                state['teg_data_ranked'],
                                selected_measure,
                                selected_friendly_name
                            )
                            ui.html(personal_best_tegs.to_html(
                                escape=False,
                                index=False,
                                justify='left',
                                classes='datawrapper-table narrow-first left-second left-4th left-5th'
                            ), sanitize=False)

                    measure_selector_2.on_value_change(lambda: update_best_tegs())
                    update_best_tegs()

                # ===== SECTION 3: BEST ROUNDS =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'best_rounds')
                with card:
                    ui.label('Measure:').classes('font-semibold mb-3')
                    measure_selector_3 = ui.select(friendly_names, value=friendly_names[0]).classes('w-48')
                    results_area_3 = ui.card().classes('w-full mt-4')

                    def update_best_rounds():
                        selected_friendly_name = measure_selector_3.value
                        selected_measure = name_mapping.get(selected_friendly_name, selected_friendly_name)
                        results_area_3.clear()
                        with results_area_3:
                            ui.label(f'Personal Best Rounds: {selected_friendly_name}').classes('text-base font-semibold mb-3')
                            personal_best_rounds = prepare_personal_best_round_table(
                                state['rd_data_formatted'],
                                selected_measure,
                                selected_friendly_name
                            )
                            ui.html(personal_best_rounds.to_html(
                                escape=False,
                                index=False,
                                justify='left',
                                classes='datawrapper-table narrow-first left-second left-4th left-5th'
                            ), sanitize=False)

                    measure_selector_3.on_value_change(lambda: update_best_rounds())
                    update_best_rounds()

                # ===== SECTION 4: WORST TEGs =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'worst_tegs')
                with card:
                    ui.label('Measure:').classes('font-semibold mb-3')
                    measure_selector_4 = ui.select(friendly_names, value=friendly_names[0]).classes('w-48')
                    results_area_4 = ui.card().classes('w-full mt-4')

                    def update_worst_tegs():
                        selected_friendly_name = measure_selector_4.value
                        selected_measure = name_mapping.get(selected_friendly_name, selected_friendly_name)
                        results_area_4.clear()
                        with results_area_4:
                            ui.label(f'Personal Worst TEGs: {selected_friendly_name}').classes('text-base font-semibold mb-3')
                            personal_worst_tegs = prepare_personal_worst_teg_table(
                                state['teg_data_ranked'],
                                selected_measure,
                                selected_friendly_name
                            )
                            ui.html(personal_worst_tegs.to_html(
                                escape=False,
                                index=False,
                                justify='left',
                                classes='datawrapper-table narrow-first left-second left-4th left-5th'
                            ), sanitize=False)

                    measure_selector_4.on_value_change(lambda: update_worst_tegs())
                    update_worst_tegs()

                # ===== SECTION 5: WORST ROUNDS =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'worst_rounds')
                with card:
                    ui.label('Measure:').classes('font-semibold mb-3')
                    measure_selector_5 = ui.select(friendly_names, value=friendly_names[0]).classes('w-48')
                    results_area_5 = ui.card().classes('w-full mt-4')

                    def update_worst_rounds():
                        selected_friendly_name = measure_selector_5.value
                        selected_measure = name_mapping.get(selected_friendly_name, selected_friendly_name)
                        results_area_5.clear()
                        with results_area_5:
                            ui.label(f'Personal Worst Rounds: {selected_friendly_name}').classes('text-base font-semibold mb-3')
                            personal_worst_rounds = prepare_personal_worst_round_table(
                                state['rd_data_formatted'],
                                selected_measure,
                                selected_friendly_name
                            )
                            ui.html(personal_worst_rounds.to_html(
                                escape=False,
                                index=False,
                                justify='left',
                                classes='datawrapper-table narrow-first left-second left-4th left-5th'
                            ), sanitize=False)

                    measure_selector_5.on_value_change(lambda: update_worst_rounds())
                    update_worst_rounds()

        except Exception as e:
            content_area.clear()
            with content_area:
                ui.label(f'Error loading personal best data: {str(e)}').classes('text-red-600')
                print(f'Error in personal_best: {e}')
                import traceback
                traceback.print_exc()

    # ===== INITIAL LOAD =====
    load_data()
    display_personal_best()
