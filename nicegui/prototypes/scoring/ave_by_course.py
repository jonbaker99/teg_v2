"""Course Averages and Records - Player performance analysis by course.

This page provides a detailed analysis of player performance by course,
allowing users to filter by geographical area and view various statistics,
including course records, averages, and best/worst performances.

Corresponds to Streamlit page: streamlit/ave_by_course.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import get_round_data, load_course_info
from helpers.course_analysis_processing import (
    prepare_area_filter_options,
    filter_data_by_area,
    calculate_course_round_counts,
    create_course_performance_table,
    create_course_summary_table
)


# ===== INLINE HELPER FUNCTIONS =====
def create_course_records_table(filtered_data):
    """Create table showing best gross score for each course."""
    records_data = []

    for course in filtered_data['Course'].unique():
        course_data = filtered_data[filtered_data['Course'] == course]
        min_score = course_data['Sc'].min()
        best_rounds = course_data[course_data['Sc'] == min_score]

        for _, round_data in best_rounds.iterrows():
            gross_v_par = f"+{int(round_data['GrossVP'])}" if round_data['GrossVP'] > 0 else str(int(round_data['GrossVP']))
            combined_score = f"{int(round_data['Sc'])} ({gross_v_par})"
            teg_round = f"{round_data['TEG']} R{int(round_data['Round'])}"

            records_data.append({
                'Course': course,
                'Score': combined_score,
                'Player': round_data['Player'],
                'Date': round_data['Date'],
                'TEG / Round': teg_round
            })

    records_df = pd.DataFrame(records_data)
    records_df['_sort_score'] = records_df['Score'].str.extract(r'(\d+)').astype(int)
    records_df = records_df.sort_values(['_sort_score', 'Date'])
    records_df = records_df.drop('_sort_score', axis=1)

    return records_df


def create_net_course_records_table(filtered_data):
    """Create table showing best net vs par for each course."""
    records_data = []

    for course in filtered_data['Course'].unique():
        course_data = filtered_data[filtered_data['Course'] == course]
        min_net_vp = course_data['NetVP'].min()
        best_rounds = course_data[course_data['NetVP'] == min_net_vp]

        for _, round_data in best_rounds.iterrows():
            net_v_par = f"+{int(round_data['NetVP'])}" if round_data['NetVP'] > 0 else str(int(round_data['NetVP']))
            teg_round = f"{round_data['TEG']} R{int(round_data['Round'])}"

            records_data.append({
                'Course': course,
                'Net vs Par': net_v_par,
                'Player': round_data['Player'],
                'Date': round_data['Date'],
                'TEG / Round': teg_round
            })

    records_df = pd.DataFrame(records_data)
    records_df['_sort_score'] = records_df['Net vs Par'].str.replace('+', '').astype(int)
    records_df = records_df.sort_values(['_sort_score', 'Date'])
    records_df = records_df.drop('_sort_score', axis=1)

    return records_df


def create_course_records_summary(filtered_data):
    """Create summary showing how many records each player holds."""
    player_courses = {}

    for course in filtered_data['Course'].unique():
        course_data = filtered_data[filtered_data['Course'] == course]
        min_score = course_data['Sc'].min()
        record_holders = course_data[course_data['Sc'] == min_score]['Player'].unique()

        for player in record_holders:
            if player not in player_courses:
                player_courses[player] = set()
            player_courses[player].add(course)

    summary_data = []
    for player, courses in player_courses.items():
        summary_data.append({'Player': player, 'Records held': len(courses)})

    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values(['Records held', 'Player'], ascending=[False, True])

    return summary_df


def create_net_course_records_summary(filtered_data):
    """Create summary showing how many net records each player holds."""
    player_courses = {}

    for course in filtered_data['Course'].unique():
        course_data = filtered_data[filtered_data['Course'] == course]
        min_net_vp = course_data['NetVP'].min()
        record_holders = course_data[course_data['NetVP'] == min_net_vp]['Player'].unique()

        for player in record_holders:
            if player not in player_courses:
                player_courses[player] = set()
            player_courses[player].add(course)

    summary_data = []
    for player, courses in player_courses.items():
        summary_data.append({'Player': player, 'Net Records held': len(courses)})

    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values(['Net Records held', 'Player'], ascending=[False, True])

    return summary_df


def ave_by_course_content():
    """Display course performance analysis with area filtering."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Course Averages and Records').classes('text-h5 font-bold mt-6')
    ui.label('Player performance breakdown by course with geographical filtering').classes('text-sm text-gray-600')
    ui.separator()

    # ===== CONTROLS =====
    with ui.row().classes('w-full gap-4 items-center'):
        ui.label('Filter by area:').classes('font-semibold')
        area_selector = ui.select([], label='').classes('w-48')

    ui.separator()

    # ===== DATA DISPLAY AREA =====
    content_area = ui.card().classes('w-full')

    # ===== STATE VARIABLES =====
    state = {
        'all_rd_data': None,
        'course_info': None,
        'area_options': [],
        'all_area_label': None,
        'data_loaded': False
    }

    def load_data():
        """Load all data once on page load."""
        try:
            state['all_rd_data'] = get_round_data(ex_50=True, ex_incomplete=False)
            state['course_info'] = load_course_info()
            state['area_options'], state['all_area_label'] = prepare_area_filter_options(state['course_info'])

            area_selector.set_options(state['area_options'])
            if state['area_options']:
                area_selector.value = state['area_options'][0]

            state['data_loaded'] = True
        except Exception as e:
            print(f'Error loading data: {e}')

    def display_course_analysis():
        """Display course analysis in 6 tabs."""
        try:
            if not state['data_loaded'] or not area_selector.value:
                return

            selected_area = area_selector.value
            filtered_rd_data = filter_data_by_area(state['all_rd_data'], state['course_info'], selected_area, state['all_area_label'])

            # Pre-calculate all data
            course_count = calculate_course_round_counts(filtered_rd_data)
            mean_course_data = create_course_performance_table(filtered_rd_data, 'mean')
            min_course_data = create_course_performance_table(filtered_rd_data, 'min')
            max_course_data = create_course_performance_table(filtered_rd_data, 'max')
            course_summary = create_course_summary_table(course_count, mean_course_data, min_course_data, max_course_data)
            course_records = create_course_records_table(filtered_rd_data)
            course_records_summary = create_course_records_summary(filtered_rd_data)
            net_course_records = create_net_course_records_table(filtered_rd_data)
            net_course_records_summary = create_net_course_records_summary(filtered_rd_data)

            content_area.clear()

            with content_area:
                ui.code('''
load_all_data(exclude_teg_50=True)
read_file('data/round_info.csv')
prepare_course_scores_data(all_data, round_info)
''', language='python').classes('mb-4')

                # ===== SECTION STATE =====
                section_state = {'current': 'course_records'}

                def set_section(section_id):
                    section_state['current'] = section_id

                # ===== BUTTON BAR =====
                with ui.row().classes('gap-2 mb-4'):
                    ui.button('Course Records', on_click=lambda: set_section('course_records'))
                    ui.button('Net Records', on_click=lambda: set_section('net_records'))
                    ui.button('Summary by Course', on_click=lambda: set_section('summary_by_course'))
                    ui.button('Averages', on_click=lambda: set_section('averages'))
                    ui.button('Bests', on_click=lambda: set_section('bests'))
                    ui.button('Worsts', on_click=lambda: set_section('worsts'))

                # ===== SECTION 1: COURSE RECORDS (GROSS) =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'course_records')
                with card:
                    ui.label('Course Records (Gross)').classes('text-base font-semibold mb-3')
                    ui.html(course_records.to_html(
                        index=False,
                        justify='left',
                        classes='full-width table-left-align datawrapper-table'
                    ), sanitize=False)

                    ui.html("<hr style='border: none; border-top: 1px solid #ccc; margin: 1.5em 0;' />", sanitize=False)

                    ui.label('Summary by Player').classes('text-base font-semibold mb-3')
                    ui.html(course_records_summary.to_html(
                        index=False,
                        justify='left',
                        classes='datawrapper-table'
                    ), sanitize=False)

                # ===== SECTION 2: NET RECORDS =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'net_records')
                with card:
                    ui.label('Course Records (Net)').classes('text-base font-semibold mb-3')
                    ui.html(net_course_records.to_html(
                        index=False,
                        justify='left',
                        classes='full-width table-left-align datawrapper-table'
                    ), sanitize=False)

                    ui.html("<hr style='border: none; border-top: 1px solid #ccc; margin: 1.5em 0;' />", sanitize=False)

                    ui.label('Net Records Summary by Player').classes('text-base font-semibold mb-3')
                    ui.html(net_course_records_summary.to_html(
                        index=False,
                        justify='left',
                        classes='datawrapper-table'
                    ), sanitize=False)

                # ===== SECTION 3: SUMMARY BY COURSE =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'summary_by_course')
                with card:
                    ui.html(course_summary.to_html(
                        index=False,
                        justify='left',
                        classes='full-width datawrapper-table'
                    ), sanitize=False)

                # ===== SECTION 4: AVERAGES =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'averages')
                with card:
                    ui.html(mean_course_data.to_html(
                        index=False,
                        justify='left',
                        classes='full-width datawrapper-table'
                    ), sanitize=False)

                # ===== SECTION 5: BESTS =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'bests')
                with card:
                    ui.html(min_course_data.to_html(
                        index=False,
                        justify='left',
                        classes='full-width datawrapper-table'
                    ), sanitize=False)

                # ===== SECTION 6: WORSTS =====
                card = ui.card().classes('w-full')
                card.bind_visibility_from(section_state, 'current', lambda v: v == 'worsts')
                with card:
                    ui.html(max_course_data.to_html(
                        index=False,
                        justify='left',
                        classes='full-width datawrapper-table'
                    ), sanitize=False)

        except Exception as e:
            content_area.clear()
            with content_area:
                ui.label(f'Error loading course analysis: {str(e)}').classes('text-red-600')
                print(f'Error in ave_by_course: {e}')
                import traceback
                traceback.print_exc()

    # ===== EVENT HANDLERS =====
    area_selector.on_value_change(lambda: display_course_analysis())

    # ===== INITIAL LOAD =====
    load_data()
    if state['data_loaded'] and state['area_options']:
        display_course_analysis()
