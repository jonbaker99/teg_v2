"""TEG Records - Comprehensive all-time records across categories.

This page presents a comprehensive view of all-time records for the TEG
competition, categorized into TEG records, round records, 9-hole records,
streaks, and score counts.

Corresponds to Streamlit page: streamlit/300TEG Records.py
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
    get_ranked_frontback_data,
    get_round_data,
    get_9_data,
    load_all_data
)
from helpers.display_helpers import (
    prepare_records_table,
    prepare_worst_records_table,
    prepare_streak_records_table,
    prepare_score_count_records_table
)
from helpers.worst_performance_processing import get_filtered_teg_data
from helpers.streak_analysis_processing import (
    prepare_record_best_streaks_data,
    prepare_record_worst_streaks_data
)


def teg_records_content():
    """Display comprehensive TEG records across all categories."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('TEG Records').classes('text-h5 font-bold mt-6')
    ui.label('Comprehensive all-time records across all competition categories').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA DISPLAY AREA =====
    content_area = ui.card().classes('w-full')

    # ===== STATE VARIABLES =====
    state = {
        'tegs_ranked': None,
        'rounds_ranked': None,
        'frontback_ranked': None,
        'teg_data': None,
        'round_data': None,
        'frontback_data': None,
        'all_data': None,
        'data_loaded': False
    }

    def load_data():
        """Load all data once on page load."""
        try:
            state['tegs_ranked'] = get_ranked_teg_data()
            state['rounds_ranked'] = get_ranked_round_data()
            state['frontback_ranked'] = get_ranked_frontback_data()
            state['teg_data'] = get_filtered_teg_data()
            state['round_data'] = get_round_data()
            state['frontback_data'] = get_9_data()
            state['all_data'] = load_all_data(exclude_teg_50=True)
            state['data_loaded'] = True
        except Exception as e:
            print(f'Error loading data: {e}')

    def display_records():
        """Load and display all records in tabs."""
        try:
            if not state['data_loaded']:
                return

            content_area.clear()

            with content_area:
                # ===== SECTION STATE =====
                section_state = {'current': 'teg_records'}

                def set_section(section_id):
                    section_state['current'] = section_id

                # ===== BUTTON BAR =====
                with ui.row().classes('gap-2 mb-4'):
                    ui.button('TEG Records', on_click=lambda: set_section('teg_records'))
                    ui.button('Round Records', on_click=lambda: set_section('round_records'))
                    ui.button('9-Hole Records', on_click=lambda: set_section('nine_hole_records'))
                    ui.button('Streaks', on_click=lambda: set_section('streaks'))
                    ui.button('Score Counts', on_click=lambda: set_section('score_counts'))

                # ===== SECTION 1: TEG RECORDS =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'teg_records')
                with card:
                    # Best TEG records
                    teg_records_table = prepare_records_table(state['tegs_ranked'], 'teg')
                    ui.html(teg_records_table.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
                    ), sanitize=False)

                    # Dashed line separator
                    ui.html(
                        "<hr style='border: none; border-top: 1px dashed #bbb; margin: 1em 0;' />",
                        sanitize=False
                    )

                    # Worst TEG records
                    teg_worst_table = prepare_worst_records_table(state['teg_data'], 'teg')
                    ui.html(teg_worst_table.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
                    ), sanitize=False)

                # ===== SECTION 2: ROUND RECORDS =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'round_records')
                with card:
                    # Best round records
                    round_records_table = prepare_records_table(state['rounds_ranked'], 'round')
                    ui.html(round_records_table.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
                    ), sanitize=False)

                    # Dashed line separator
                    ui.html(
                        "<hr style='border: none; border-top: 1px dashed #bbb; margin: 1em 0;' />",
                        sanitize=False
                    )

                    # Worst round records
                    round_worst_table = prepare_worst_records_table(state['round_data'], 'round')
                    ui.html(round_worst_table.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
                    ), sanitize=False)

                # ===== SECTION 3: 9-HOLE RECORDS =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'nine_hole_records')
                with card:
                    # Best 9-hole records
                    nine_records_table = prepare_records_table(state['frontback_ranked'], 'frontback')
                    ui.html(nine_records_table.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
                    ), sanitize=False)

                    # Dashed line separator
                    ui.html(
                        "<hr style='border: none; border-top: 1px dashed #bbb; margin: 1em 0;' />",
                        sanitize=False
                    )

                    # Worst 9-hole records
                    nine_worst_table = prepare_worst_records_table(state['frontback_data'], 'frontback')
                    ui.html(nine_worst_table.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
                    ), sanitize=False)

                # ===== SECTION 4: STREAKS =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'streaks')
                with card:
                    # Best streaks
                    best_streaks_data = prepare_record_best_streaks_data(state['all_data'])
                    best_streaks_table = prepare_streak_records_table(best_streaks_data, 'Best Streaks:')
                    ui.html(best_streaks_table.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
                    ), sanitize=False)

                    # Dashed line separator
                    ui.html(
                        "<hr style='border: none; border-top: 1px dashed #bbb; margin: 1em 0;' />",
                        sanitize=False
                    )

                    # Worst streaks
                    worst_streaks_data = prepare_record_worst_streaks_data(state['all_data'])
                    worst_streaks_table = prepare_streak_records_table(worst_streaks_data, 'Worst Streaks:')
                    ui.html(worst_streaks_table.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
                    ), sanitize=False)

                    ui.label('* and counting...').classes('text-sm text-gray-600 mt-2')

                # ===== SECTION 5: SCORE COUNTS =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'score_counts')
                with card:
                    # Score count records
                    best_score_counts, worst_score_counts = prepare_score_count_records_table(state['all_data'])

                    # Display best score counts
                    if not best_score_counts.empty:
                        ui.html(best_score_counts.to_html(
                            escape=False,
                            index=False,
                            justify='left',
                            classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
                        ), sanitize=False)

                    # Display worst score counts
                    if not worst_score_counts.empty:
                        ui.html(worst_score_counts.to_html(
                            escape=False,
                            index=False,
                            justify='left',
                            classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
                        ), sanitize=False)

                    ui.label('Eagles, Birdies and Pars also include better scores').classes('text-sm text-gray-600 mt-2')

        except Exception as e:
            content_area.clear()
            with content_area:
                ui.label(f'Error loading records: {str(e)}').classes('text-red-600')
                print(f'Error in teg_records: {e}')
                import traceback
                traceback.print_exc()

    # ===== INITIAL LOAD =====
    load_data()
    display_records()
