"""TEG Results - Complete results for a selected TEG with leaderboards and charts.

This page displays:
- TEG selector (dropdown with latest as default)
- TEG Trophy leaderboard (Net competition)
- Green Jacket leaderboard (Gross competition)
- Scorecards for each round (sub-tabs)
- Full tournament report (markdown)
- Optional cumulative score charts

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
                # Get number of rounds
                try:
                    num_rounds = get_teg_rounds(teg_num)
                except:
                    num_rounds = 4

                # Create main tabs
                with ui.tabs() as tabs:
                    # Tab 1: TEG Trophy Leaderboard
                    with ui.tab(f'TEG Trophy Leaderboard'):
                        try:
                            trophy_agg = aggregate_data(teg_data, aggregation_level='Player')
                            if not trophy_agg.empty:
                                # Determine competition measure
                                if teg_num <= 5:
                                    measure = 'NetVP'
                                else:
                                    measure = 'Stableford'

                                if measure in trophy_agg.columns:
                                    # Sort by measure (ascending for NetVP, descending for Stableford)
                                    if measure == 'Stableford':
                                        leaderboard = trophy_agg.sort_values(measure, ascending=False)
                                    else:
                                        leaderboard = trophy_agg.sort_values(measure, ascending=True)

                                    # Add rank column
                                    leaderboard.insert(0, 'Rank', range(1, len(leaderboard) + 1))

                                    ui.label('TEG Trophy Leaderboard').classes('text-sm font-semibold')
                                    leaderboard_html = leaderboard.to_html(index=False, escape=False, classes='datawrapper-table')
                                    ui.html(leaderboard_html, sanitize=False)
                                else:
                                    ui.label(f'Measure {measure} not found in data').classes('text-gray-600')
                            else:
                                ui.label('No Trophy data available').classes('text-gray-600')
                        except Exception as e:
                            ui.label(f'Error loading Trophy leaderboard: {str(e)}').classes('text-red-600')

                    # Tab 2: Green Jacket Leaderboard
                    with ui.tab('Green Jacket Leaderboard'):
                        try:
                            jacket_agg = aggregate_data(teg_data, aggregation_level='Player')
                            if not jacket_agg.empty and 'GrossVP' in jacket_agg.columns:
                                # Sort by GrossVP
                                leaderboard = jacket_agg.sort_values('GrossVP', ascending=True)

                                # Add rank column
                                leaderboard.insert(0, 'Rank', range(1, len(leaderboard) + 1))

                                ui.label('Green Jacket Leaderboard').classes('text-sm font-semibold')
                                leaderboard_html = leaderboard.to_html(index=False, escape=False, classes='datawrapper-table')
                                ui.html(leaderboard_html, sanitize=False)
                            else:
                                ui.label('No Gross data available').classes('text-gray-600')
                        except Exception as e:
                            ui.label(f'Error loading Jacket leaderboard: {str(e)}').classes('text-red-600')

                    # Tab 3: Round Scorecards
                    with ui.tab('Round Scorecards'):
                        try:
                            # Create sub-tabs for each round
                            with ui.tabs() as round_tabs:
                                for round_num in range(1, num_rounds + 1):
                                    with ui.tab(f'Round {round_num}'):
                                        try:
                                            # Generate scorecard HTML for this round
                                            scorecard_html = generate_round_comparison_html(teg_num, round_num)
                                            ui.html(scorecard_html, sanitize=False)

                                        except Exception as e:
                                            ui.label(f'Error loading Round {round_num}: {str(e)}').classes('text-red-600')

                        except Exception as e:
                            ui.label(f'Error loading scorecards: {str(e)}').classes('text-red-600')

                    # Tab 4: Tournament Report
                    with ui.tab('Tournament Report'):
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
