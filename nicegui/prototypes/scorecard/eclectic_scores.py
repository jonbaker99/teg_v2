"""Eclectic Scores - Interactive eclectic score exploration with flexible filtering.

This page allows users to explore eclectic scores with flexible filtering by player, TEG,
and course. Users can compare eclectics across different dimensions:
- By Player
- By TEG
- By Course
- By Teams (Heroes vs. Wildcats)
- Combined (all data)

Displays hole-by-hole breakdown plus totals.

Corresponds to Streamlit page: streamlit/eclectic.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import load_all_data, load_course_info
from eclectic_utils import calculate_eclectic_by_dimension, format_eclectic_table


def get_selection_options(all_data: pd.DataFrame, course_info: pd.DataFrame) -> tuple:
    """Gets the options for the selection dropdowns."""
    players = sorted(all_data['Player'].unique().tolist())
    tegs = sorted(all_data['TEGNum'].unique().tolist(), reverse=True)
    courses = sorted(course_info['Course'].unique().tolist())

    return players, tegs, courses


def filter_data_for_eclectic(all_data: pd.DataFrame, selected_player: str,
                              selected_teg: str, selected_course: str) -> pd.DataFrame:
    """Filters the data based on user selections."""
    filtered = all_data.copy()

    if selected_player != 'All Players':
        filtered = filtered[filtered['Player'] == selected_player]

    if selected_teg != 'All TEGs':
        teg_num = int(selected_teg.replace('TEG ', ''))
        filtered = filtered[filtered['TEGNum'] == teg_num]

    if selected_course != 'All Courses':
        filtered = filtered[filtered['Course'] == selected_course]

    return filtered


@ui.page('/scorecard/eclectic-scores')
def eclectic_scores_page():
    """Display eclectic scores with flexible filtering."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Eclectic Scores').classes('text-h5 font-bold mt-6')
    ui.label('The eclectic score takes the best score on each hole from multiple rounds').classes(
        'text-sm text-gray-600'
    )
    ui.separator()

    # ===== DATA LOADING =====
    state = {
        'all_data': None,
        'course_info': None,
        'data_loaded': False,
        'selected_player': 'All Players',
        'selected_teg': 'All TEGs',
        'selected_course': 'All Courses',
        'comparison_dimension': None
    }

    def load_data():
        """Load all data once on page load."""
        try:
            state['all_data'] = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
            state['course_info'] = load_course_info()
            state['data_loaded'] = True

            # Initialize selector options
            players, tegs, courses = get_selection_options(state['all_data'], state['course_info'])

            player_options = ['All Players'] + players
            teg_options = ['All TEGs'] + [f'TEG {teg}' for teg in tegs]
            course_options = ['All Courses'] + courses

            player_selector.set_options(player_options)
            teg_selector.set_options(teg_options)
            course_selector.set_options(course_options)

            player_selector.value = 'All Players'
            teg_selector.value = 'All TEGs'
            course_selector.value = 'All Courses'

        except Exception as e:
            print(f'Error loading data: {e}')

    # ===== CONTROLS SECTION =====
    ui.label('Selections').classes('text-base font-semibold')

    with ui.row().classes('w-full gap-4'):
        with ui.column():
            ui.label('Players').classes('font-semibold text-sm')
            player_selector = ui.select([], label='').classes('w-40')

        with ui.column():
            ui.label('TEGs').classes('font-semibold text-sm')
            teg_selector = ui.select([], label='').classes('w-40')

        with ui.column():
            ui.label('Courses').classes('font-semibold text-sm')
            course_selector = ui.select([], label='').classes('w-40')

    ui.separator()

    ui.label('Comparison').classes('text-base font-semibold')

    # Comparison radio buttons
    all_display_options = ["Player", "TEG", "Course", "Heroes vs. Wildcats", "Combined"]
    comparison_radio = ui.radio(all_display_options, value="Player").props('inline')

    ui.separator()

    # ===== DATA DISPLAY AREA =====
    display_area = ui.card().classes('w-full')

    def update_display():
        """Update the displayed eclectic scores."""
        try:
            if not state['data_loaded']:
                return

            display_area.clear()

            with display_area:
                # Determine which comparison option is selected
                selected_option = comparison_radio.value

                # Map display names to internal dimensions
                option_mapping = {}

                # Check which dimensions are enabled based on selections
                player_enabled = state['selected_player'] == 'All Players'
                teg_enabled = state['selected_teg'] == 'All TEGs'
                course_enabled = state['selected_course'] == 'All Courses'

                if player_enabled or state['selected_player'] != 'All Players':
                    option_mapping["Player"] = "Player"

                if teg_enabled or state['selected_teg'] != 'All TEGs':
                    option_mapping["TEG"] = "TEGNum"

                if course_enabled or state['selected_course'] != 'All Courses':
                    option_mapping["Course"] = "Course"

                option_mapping["Heroes vs. Wildcats"] = "Teams"
                option_mapping["Combined"] = "Combined"

                # Validate selected option
                if selected_option not in option_mapping:
                    ui.label('Select comparison options to view eclectic scores').classes('text-gray-600')
                    return

                comparison_dimension = option_mapping[selected_option]

                # Filter data
                filtered_data = filter_data_for_eclectic(
                    state['all_data'],
                    state['selected_player'],
                    state['selected_teg'],
                    state['selected_course']
                )

                if filtered_data.empty:
                    ui.label('No data matches your selections. Please adjust your filters').classes('text-gray-600')
                    return

                # Calculate eclectic scores
                eclectic_results, actual_dimension = calculate_eclectic_by_dimension(
                    filtered_data,
                    comparison_dimension
                )

                if eclectic_results.empty:
                    ui.label('No eclectic scores could be calculated with your selections').classes('text-gray-600')
                    return

                # Format results
                formatted_results = format_eclectic_table(eclectic_results, actual_dimension)

                ui.label('Eclectic Scores').classes('text-base font-semibold mb-2')

                # Show summary info
                total_rounds = len(filtered_data.groupby(['Player', 'TEGNum', 'Round']))
                ui.label(f'Based on {total_rounds} rounds from your selections').classes('text-sm text-gray-600 mb-3')

                # Display table
                ui.html(formatted_results.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ), sanitize=False)

        except Exception as e:
            display_area.clear()
            with display_area:
                ui.label(f'Error loading eclectic scores: {str(e)}').classes('text-red-600')
                print(f'Error in eclectic_scores: {e}')
                import traceback
                traceback.print_exc()

    # ===== EVENT HANDLERS =====
    def handle_player_change():
        state['selected_player'] = player_selector.value
        update_display()

    def handle_teg_change():
        state['selected_teg'] = teg_selector.value
        update_display()

    def handle_course_change():
        state['selected_course'] = course_selector.value
        update_display()

    def handle_comparison_change():
        update_display()

    player_selector.on_value_change(handle_player_change)
    teg_selector.on_value_change(handle_teg_change)
    course_selector.on_value_change(handle_course_change)
    comparison_radio.on_value_change(handle_comparison_change)

    # ===== INITIAL LOAD =====
    load_data()
    if state['data_loaded']:
        update_display()
