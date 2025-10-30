"""Eclectic Records - Best eclectic scores by TEG and Course.

This page showcases the best eclectic scores across all tournaments. An eclectic score
is the best score achieved on each hole over multiple rounds, creating a theoretical
best possible round. Displays:
- Top 3 eclectic scores by TEG (overall and personal best)
- Top 3 eclectic scores by Course (overall and personal best)

Corresponds to Streamlit page: streamlit/best_eclectics.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import load_all_data
from eclectic_utils import calculate_eclectic_by_dimension


def get_overall_top_eclectics(data: pd.DataFrame, dimension: str, top_n: int = 3) -> pd.DataFrame:
    """Gets the overall top N eclectics across all players, including ties."""
    all_results = []
    players = sorted(data['Player'].unique())

    for player in players:
        player_data = data[data['Player'] == player]
        if player_data.empty:
            continue

        eclectics, actual_dimension = calculate_eclectic_by_dimension(player_data, dimension)
        if eclectics.empty:
            continue

        eclectics['Player'] = player
        all_results.append(eclectics)

    if not all_results:
        return pd.DataFrame()

    combined_results = pd.concat(all_results, ignore_index=True)
    combined_results = combined_results.sort_values('Total')

    if len(combined_results) >= top_n:
        nth_score = combined_results.iloc[top_n-1]['Total']
        return combined_results[combined_results['Total'] <= nth_score]
    else:
        return combined_results


def get_personal_best_eclectics(data: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Gets each player's best eclectic score(s), including ties."""
    all_results = []
    players = sorted(data['Player'].unique())

    for player in players:
        player_data = data[data['Player'] == player]
        if player_data.empty:
            continue

        eclectics, actual_dimension = calculate_eclectic_by_dimension(player_data, dimension)
        if eclectics.empty:
            continue

        best_score = eclectics['Total'].min()
        best_eclectics = eclectics[eclectics['Total'] == best_score]
        best_eclectics['Player'] = player
        all_results.append(best_eclectics)

    if not all_results:
        return pd.DataFrame()

    return pd.concat(all_results, ignore_index=True).sort_values(['Total', 'Player'])


def format_eclectic_display_table(df: pd.DataFrame) -> pd.DataFrame:
    """Formats the eclectic table for display with summary columns only."""
    if df.empty:
        return pd.DataFrame()

    # Get the dimension column name
    dimension_col = [col for col in df.columns
                     if col not in ['Player', 'Total', 'Rounds'] and not isinstance(col, int)][0]

    # Select only summary columns
    display_cols = ['Player', dimension_col, 'Total', 'Rounds']

    formatted_df = df[display_cols].copy()

    # Format numeric columns
    for col in ['Total', 'Rounds']:
        if col in formatted_df.columns:
            formatted_df[col] = formatted_df[col].apply(lambda x: int(x) if pd.notna(x) else '-')

    return formatted_df


def eclectic_records_content():
    """Display eclectic score records by TEG and Course."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Eclectic Records').classes('text-h5 font-bold mt-6')
    ui.label('Best eclectic scores by TEG and Course').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA LOADING =====
    state = {
        'all_data': None,
        'data_loaded': False
    }

    def load_data():
        """Load all data once on page load."""
        try:
            state['all_data'] = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
            state['data_loaded'] = True
        except Exception as e:
            print(f'Error loading data: {e}')

    def display_records():
        """Display eclectic records in tabs."""
        try:
            if not state['data_loaded']:
                return

            with ui.tabs() as tabs:
                # ===== TAB 1: TEG ECLECTICS =====
                with ui.tab('TEGs'):
                    with ui.card().classes('w-full mb-6'):
                        ui.label('Top 3 TEG Eclectics').classes('text-base font-semibold mb-3')

                        overall_top_tegs = get_overall_top_eclectics(state['all_data'], 'TEGNum', top_n=3)
                        if not overall_top_tegs.empty:
                            formatted_top_tegs = format_eclectic_display_table(overall_top_tegs)
                            ui.html(formatted_top_tegs.to_html(
                                index=False,
                                justify='left',
                                classes='datawrapper-table'
                            ), sanitize=False)
                        else:
                            ui.label('No TEG data available').classes('text-gray-600')

                    with ui.card().classes('w-full'):
                        ui.label('Personal Best TEG Eclectics').classes('text-base font-semibold mb-3')

                        pb_tegs = get_personal_best_eclectics(state['all_data'], 'TEGNum')
                        if not pb_tegs.empty:
                            formatted_pb_tegs = format_eclectic_display_table(pb_tegs)
                            ui.html(formatted_pb_tegs.to_html(
                                index=False,
                                justify='left',
                                classes='datawrapper-table'
                            ), sanitize=False)
                        else:
                            ui.label('No TEG data available').classes('text-gray-600')

                # ===== TAB 2: COURSE ECLECTICS =====
                with ui.tab('Courses'):
                    with ui.card().classes('w-full mb-6'):
                        ui.label('Top 3 Course Eclectics').classes('text-base font-semibold mb-3')

                        overall_top_courses = get_overall_top_eclectics(state['all_data'], 'Course', top_n=3)
                        if not overall_top_courses.empty:
                            formatted_top_courses = format_eclectic_display_table(overall_top_courses)
                            ui.html(formatted_top_courses.to_html(
                                index=False,
                                justify='left',
                                classes='datawrapper-table'
                            ), sanitize=False)
                        else:
                            ui.label('No course data available').classes('text-gray-600')

                    with ui.card().classes('w-full'):
                        ui.label('Personal Best Course Eclectics').classes('text-base font-semibold mb-3')

                        pb_courses = get_personal_best_eclectics(state['all_data'], 'Course')
                        if not pb_courses.empty:
                            formatted_pb_courses = format_eclectic_display_table(pb_courses)
                            ui.html(formatted_pb_courses.to_html(
                                index=False,
                                justify='left',
                                classes='datawrapper-table'
                            ), sanitize=False)
                        else:
                            ui.label('No course data available').classes('text-gray-600')

        except Exception as e:
            ui.label(f'Error loading records: {str(e)}').classes('text-red-600')
            print(f'Error in eclectic_records: {e}')
            import traceback
            traceback.print_exc()

    # ===== INITIAL LOAD =====
    load_data()
    if state['data_loaded']:
        display_records()
