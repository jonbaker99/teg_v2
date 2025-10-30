"""Eagles, Birdies, Pars etc. - Scoring achievements analysis.

This page provides a detailed breakdown of various scoring achievements,
allowing users to explore career totals, single-round bests, and single-TEG bests.

Corresponds to Streamlit page: streamlit/birdies_etc.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import score_type_stats, max_scoretype_per_round, max_scoretype_per_teg
from helpers.scoring_achievements_processing import (
    get_scoring_achievement_fields,
    prepare_achievement_table_data,
    create_section_title
)


@ui.page('/scoring/birdies-etc')
def birdies_etc_page():
    """Display scoring achievements: eagles, birdies, pars, and poor scores."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Eagles, Birdies etc.').classes('text-h5 font-bold mt-6')
    ui.label('Scoring achievements and career totals').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA LOADING =====
    state = {
        'scoring_stats': None,
        'max_by_round': None,
        'max_by_teg': None,
        'chart_fields_all': None,
        'data_loaded': False
    }

    def load_data():
        """Load all data once on page load."""
        try:
            state['scoring_stats'] = score_type_stats()
            state['max_by_round'] = max_scoretype_per_round()
            state['max_by_teg'] = max_scoretype_per_teg()
            state['chart_fields_all'] = get_scoring_achievement_fields()
            state['data_loaded'] = True
        except Exception as e:
            print(f'Error loading data: {e}')

    def display_achievements():
        """Display achievement data in tabs."""
        try:
            if not state['data_loaded']:
                return

            # ===== MAIN TABS =====
            with ui.tabs() as tabs:
                # ===== TAB 1: CAREER TOTALS =====
                with ui.tab('Career Totals'):
                    # Score type selector
                    score_type_options = {
                        'Eagles': state['chart_fields_all'][0],
                        'Birdies': state['chart_fields_all'][1],
                        'Pars': state['chart_fields_all'][2],
                        'Triple Bogey+': state['chart_fields_all'][3],
                    }

                    ui.label('Select score type:').classes('font-semibold mb-3')
                    score_type_toggle = ui.toggle(score_type_options, value='Eagles').classes('gap-2')

                    results_area_1 = ui.card().classes('w-full mt-4')

                    def update_career_totals():
                        selected_score_type = score_type_toggle.value
                        selected_chart_fields = score_type_options[selected_score_type]
                        section_title = create_section_title(selected_chart_fields)
                        formatted_table = prepare_achievement_table_data(state['scoring_stats'], selected_chart_fields)

                        results_area_1.clear()
                        with results_area_1:
                            ui.label(f'Career {section_title}').classes('text-base font-semibold mb-3')
                            ui.html(formatted_table.to_html(
                                index=False,
                                justify='left',
                                classes='datawrapper-table'
                            ), sanitize=False)

                    score_type_toggle.on_value_change(lambda: update_career_totals())
                    update_career_totals()

                # ===== TAB 2: MOST IN A ROUND =====
                with ui.tab('Most in a Round'):
                    ui.label('Single-round maximum achievements').classes('text-base font-semibold mb-3')
                    reordered_table = state['max_by_round'][['Player', 'Eagles', 'Birdies', 'Pars_or_Better', 'TBPs']].copy()
                    reordered_table = reordered_table.rename(columns={'Pars_or_Better': 'Pars'})
                    ui.html(reordered_table.to_html(
                        index=False,
                        justify='left',
                        classes='datawrapper-table'
                    ), sanitize=False)

                # ===== TAB 3: MOST IN A TEG =====
                with ui.tab('Most in a TEG'):
                    ui.label('Single-TEG maximum achievements').classes('text-base font-semibold mb-3')
                    reordered_table = state['max_by_teg'][['Player', 'Eagles', 'Birdies', 'Pars_or_Better', 'TBPs']].copy()
                    reordered_table = reordered_table.rename(columns={'Pars_or_Better': 'Pars'})
                    ui.html(reordered_table.to_html(
                        index=False,
                        justify='left',
                        classes='datawrapper-table'
                    ), sanitize=False)

        except Exception as e:
            ui.label(f'Error loading achievements: {str(e)}').classes('text-red-600')
            print(f'Error in birdies_etc: {e}')
            import traceback
            traceback.print_exc()

    # ===== INITIAL LOAD =====
    load_data()
    display_achievements()
