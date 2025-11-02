"""Scoring Hub - Comprehensive scoring analysis dashboard.

This page provides a deep dive into various scoring metrics, including:
- Average scores by par value (Par 3, 4, 5)
- Career scoring statistics (eagles, birdies, pars, triple bogeys)
- Single-round records for each score type
- Longest streaks for different scoring achievements

Corresponds to Streamlit page: streamlit/400scoring.py
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
    score_type_stats,
    load_all_data,
    max_scoretype_per_round
)
from helpers.scoring_data_processing import (
    prepare_average_scores_by_par,
    format_scoring_stats_columns,
    calculate_multi_score_running_sum,
    summarize_multi_score_running_sum
)


def scoring_hub_content():
    """Display comprehensive scoring analysis dashboard."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Scoring Analysis Hub').classes('text-h5 font-bold mt-6')
    ui.label('Detailed breakdown of scoring patterns, streaks, and achievements').classes('text-sm text-gray-600')
    ui.separator()

    # ===== TABLE OF CONTENTS =====
    with ui.card().classes('bg-blue-50 p-4 mb-4'):
        ui.label('Contents:').classes('font-semibold mb-2')
        ui.html("""
        <ol class="text-sm text-gray-700 ml-4">
            <li>Average score by par</li>
            <li>Career eagles, birdies, pars and triple bogey+</li>
            <li>Most of each type of score in a single round</li>
            <li>Longest streaks by player</li>
        </ol>
        """, sanitize=False)

    # ===== DATA LOADING =====
    state = {
        'all_data_incomplete': None,
        'all_data_clean': None,
        'scoring_stats': None,
        'max_by_round': None,
        'data_loaded': False
    }

    def load_data():
        """Load all data once on page load."""
        try:
            state['all_data_incomplete'] = load_all_data(exclude_incomplete_tegs=False)
            state['all_data_clean'] = load_all_data(exclude_teg_50=True)
            state['scoring_stats'] = score_type_stats()
            state['max_by_round'] = max_scoretype_per_round()
            state['data_loaded'] = True
        except Exception as e:
            print(f'Error loading data: {e}')

    def display_scoring_analysis():
        """Display all scoring analysis sections."""
        try:
            if not state['data_loaded']:
                return

            ui.code('''
load_all_data(exclude_incomplete_tegs=False)
load_all_data(exclude_teg_50=True)
score_type_stats()
max_scoretype_per_round()
prepare_average_scores_by_par(all_data_incomplete)
format_scoring_stats_columns(table_df)
calculate_multi_score_running_sum(all_data_clean)
summarize_multi_score_running_sum(streaks_data)
''', language='python').classes('mb-4')

            # ===== SECTION 1: AVERAGE SCORE BY PAR =====
            with ui.card().classes('w-full mb-6'):
                ui.label('1. Average Score by Par').classes('text-lg font-semibold mb-3')
                avg_scores_table = prepare_average_scores_by_par(state['all_data_incomplete'])
                ui.html(avg_scores_table.to_html(
                    classes='dataframe, datawrapper-table',
                    index=False,
                    justify='left'
                ), sanitize=False)

            # ===== SECTION 2: CAREER SCORING STATISTICS =====
            with ui.card().classes('w-full mb-6'):
                ui.label('2. Career Eagles, Birdies, Pars and Triple Bogey+').classes('text-lg font-semibold mb-3')

                scoring_categories = [
                    ['Eagles', 'Holes_per_Eagle'],
                    ['Birdies', 'Holes_per_Birdie'],
                    ['Pars_or_Better', 'Holes_per_Par_or_Better'],
                    ['TBPs', 'Holes_per_TBP']
                ]

                # Section state for category selection
                category_state = {'current': 'Eagles'}

                def set_category(cat_name):
                    category_state['current'] = cat_name

                # Button bar for category selection
                with ui.row().classes('gap-2 mb-4 flex-wrap'):
                    for category in scoring_categories:
                        ui.button(category[0], on_click=lambda cat=category[0]: set_category(cat)).props('flat')

                # Display cards for each category
                for category in scoring_categories:
                    chart_fields = category
                    section_title = chart_fields[0].replace("_", " ")

                    category_card = ui.card().classes('w-full')
                    category_card.bind_visibility_from(category_state, 'current', lambda v, c=category[0]: v == c)

                    with category_card:
                        table_df = state['scoring_stats'][['Player'] + chart_fields].sort_values(
                            by=chart_fields,
                            ascending=[False, True]
                        )

                        table_df = format_scoring_stats_columns(table_df)

                        ui.label(f'Career {section_title}').classes('text-base font-semibold mb-3')
                        ui.html(table_df.to_html(
                            index=False,
                            justify='left',
                            classes='datawrapper-table'
                        ), sanitize=False)

            # ===== SECTION 3: SINGLE ROUND MAXIMUMS =====
            with ui.card().classes('w-full mb-6'):
                ui.label('3. Most of Each Type of Score in a Single Round').classes('text-lg font-semibold mb-3')
                ui.html(state['max_by_round'].to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ), sanitize=False)

            # ===== SECTION 4: LONGEST STREAKS =====
            with ui.card().classes('w-full mb-6'):
                ui.label('4. Longest Streaks by Player').classes('text-lg font-semibold mb-3')

                # Calculate streak data
                streaks_data = calculate_multi_score_running_sum(state['all_data_clean'])
                streak_summary = summarize_multi_score_running_sum(streaks_data)

                ui.html(streak_summary.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ), sanitize=False)

        except Exception as e:
            ui.label(f'Error loading scoring analysis: {str(e)}').classes('text-red-600')
            print(f'Error in scoring_hub: {e}')
            import traceback
            traceback.print_exc()

    # ===== INITIAL LOAD =====
    load_data()
    display_scoring_analysis()
