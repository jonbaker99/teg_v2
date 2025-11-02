"""TEG Results - Complete results for a selected TEG with leaderboards and reports.

This page displays:
- TEG selector (dropdown with latest as default)
- TEG Trophy leaderboard (Net competition)
- Green Jacket leaderboard (Gross competition)
- Scorecards for each round (displayed vertically)
- Full tournament report (markdown)

Corresponds to Streamlit page: streamlit/102TEG Results.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import load_all_data, get_round_data, get_teg_rounds, read_text_file, get_net_competition_measure
from scorecard_utils import generate_round_comparison_html
from teg_analysis.analysis.aggregation import aggregate_data
from teg_analysis.display.html_tables import create_round_leaderboard_html
import markdown


def teg_results_content():
    """Display complete results for a selected TEG."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('TEG Results').classes('text-h5 font-bold mt-6')
    ui.label('Complete results for each TEG with leaderboards and reports').classes('text-sm text-gray-600')
    ui.separator()

    # ===== CONTROLS =====
    with ui.row().classes('w-full gap-4 items-center'):
        ui.label('Select TEG:').classes('font-semibold')
        teg_selector = ui.select([], label='', value=None).classes('w-48')

    # ===== DATA DISPLAY AREA =====
    content_area = ui.card().classes('w-full')

    # ===== STATE VARIABLES =====
    state = {
        'all_tegs': [],
        'current_teg_num': None
    }

    def load_teg_list():
        """Load list of available TEGs and set default to latest."""
        try:
            all_data = load_all_data(exclude_teg_50=True)
            if all_data.empty:
                return

            # Get unique TEGs sorted by TEGNum descending
            teg_list = all_data.sort_values('TEGNum', ascending=False)[['TEG', 'TEGNum']].drop_duplicates()
            teg_display = [f"{row['TEG']} (#{row['TEGNum']})" for _, row in teg_list.iterrows()]
            teg_nums = teg_list['TEGNum'].tolist()

            state['all_tegs'] = list(zip(teg_display, teg_nums))
            teg_selector.set_options([t[0] for t in state['all_tegs']])

            # Set default to latest
            if state['all_tegs']:
                teg_selector.value = state['all_tegs'][0][0]
                state['current_teg_num'] = state['all_tegs'][0][1]

        except Exception as e:
            print(f'Error loading TEG list: {e}')

    def display_teg_results():
        """Load and display results for selected TEG."""
        try:
            if not teg_selector.value:
                content_area.clear()
                with content_area:
                    ui.label('Please select a TEG').classes('text-gray-600')
                return

            # Get selected TEG number
            selected_teg = teg_selector.value
            teg_num = None
            for display, num in state['all_tegs']:
                if display == selected_teg:
                    teg_num = num
                    break

            if not teg_num:
                content_area.clear()
                with content_area:
                    ui.label('Could not determine TEG number').classes('text-red-600')
                return

            state['current_teg_num'] = teg_num

            # Load TEG data
            all_data = load_all_data(exclude_teg_50=True)
            teg_data = all_data[all_data['TEGNum'] == teg_num]

            if teg_data.empty:
                content_area.clear()
                with content_area:
                    ui.label(f'No data found for TEG {teg_num}').classes('text-red-600')
                return

            content_area.clear()

            with content_area:
                ui.code('''
load_all_data(exclude_teg_50=True)
create_round_leaderboard_html(teg_data, measure='Stableford', ascending=False)
create_round_leaderboard_html(teg_data, measure='GrossVP', ascending=True)
generate_round_comparison_html(teg_num, round_num)
''', language='python').classes('mb-4')

                # Get number of rounds
                try:
                    num_rounds = get_teg_rounds(teg_num)
                except:
                    num_rounds = 4

                # ===== SECTION 1: TEG Trophy Leaderboard =====
                ui.label('TEG Trophy Leaderboard').classes('text-h6 font-bold mt-6')
                try:
                    # Determine competition measure for this TEG
                    if teg_num <= 5:
                        measure = 'NetVP'
                        ascending = True  # Lower is better for NetVP
                    else:
                        measure = 'Stableford'
                        ascending = False  # Higher is better for Stableford

                    # Generate leaderboard HTML with round-by-round breakdown
                    leaderboard_html = create_round_leaderboard_html(
                        teg_data,
                        measure=measure,
                        ascending=ascending,
                        title='TEG Trophy Leaderboard'
                    )
                    ui.html(leaderboard_html, sanitize=False)
                except Exception as e:
                    ui.label(f'Error loading Trophy leaderboard: {str(e)}').classes('text-red-600')

                ui.separator()

                # ===== SECTION 2: Green Jacket Leaderboard =====
                ui.label('Green Jacket Leaderboard').classes('text-h6 font-bold mt-6')
                try:
                    # Generate leaderboard HTML for Gross competition (GrossVP - lower is better)
                    leaderboard_html = create_round_leaderboard_html(
                        teg_data,
                        measure='GrossVP',
                        ascending=True,  # Lower is better for GrossVP
                        title='Green Jacket Leaderboard'
                    )
                    ui.html(leaderboard_html, sanitize=False)
                except Exception as e:
                    ui.label(f'Error loading Jacket leaderboard: {str(e)}').classes('text-red-600')

                ui.separator()

                # ===== SECTION 3: Round Scorecards =====
                ui.label('Round Scorecards').classes('text-h6 font-bold mt-6')
                try:
                    for round_num in range(1, num_rounds + 1):
                        try:
                            ui.label(f'Round {round_num}').classes('text-sm font-semibold mt-4')
                            # Generate scorecard HTML for this round
                            scorecard_html = generate_round_comparison_html(teg_num, round_num)
                            ui.html(scorecard_html, sanitize=False)

                        except Exception as e:
                            ui.label(f'Error loading Round {round_num}: {str(e)}').classes('text-red-600')

                except Exception as e:
                    ui.label(f'Error loading scorecards: {str(e)}').classes('text-red-600')

                ui.separator()

                # ===== SECTION 4: Tournament Report =====
                ui.label('Tournament Report').classes('text-h6 font-bold mt-6')
                try:
                    report_path = f'data/commentary/teg_{teg_num}_main_report.md'
                    try:
                        report_content = read_text_file(report_path)
                        html_content = markdown.markdown(report_content)
                        ui.html(html_content, sanitize=False)
                    except FileNotFoundError:
                        ui.label(f'Tournament report not found: {report_path}').classes('text-gray-600')
                    except Exception as e:
                        ui.label(f'Error loading report: {str(e)}').classes('text-orange-600')

                except Exception as e:
                    ui.label(f'Error: {str(e)}').classes('text-red-600')

        except Exception as e:
            content_area.clear()
            with content_area:
                ui.label(f'Error: {str(e)}').classes('text-red-600')
                print(f'Error in teg_results: {e}')
                import traceback
                traceback.print_exc()

    # ===== EVENT HANDLERS =====
    teg_selector.on_value_change(lambda: display_teg_results())

    # ===== INITIAL LOAD =====
    load_teg_list()
    if teg_selector.value:
        display_teg_results()
