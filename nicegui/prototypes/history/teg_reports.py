"""TEG Reports - Detailed reports for each tournament and individual rounds.

This page displays:
- Dropdown selector to choose a TEG
- Tabs for Full Tournament Report (if complete) and individual Round Reports
- Markdown content rendered to HTML
- Satire mode option for completed tournaments

Corresponds to Streamlit page: streamlit/teg_reports.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd
import markdown

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import load_all_data, read_file, read_text_file, get_teg_rounds


def read_teg_report_file(file_path: str) -> str:
    """Read a TEG report file, handling potential read errors gracefully."""
    try:
        return read_text_file(file_path)
    except FileNotFoundError:
        return f"Report not found: {file_path}"
    except Exception as e:
        return f"Error reading report: {str(e)}"


@ui.page('/history/teg-reports')
def teg_reports_page():
    """Display detailed tournament and round reports."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('TEG Reports').classes('text-h5 font-bold mt-6')
    ui.label('Detailed tournament and round-by-round reports').classes('text-sm text-gray-600')
    ui.separator()

    # ===== CONTROLS =====
    with ui.row().classes('w-full gap-4 items-center'):
        ui.label('Select TEG:').classes('font-semibold')
        teg_selector = ui.select([], label='', value=None).classes('w-48')

    # ===== DATA DISPLAY AREA =====
    content_card = ui.card().classes('w-full')

    # ===== STATE VARIABLES =====
    state = {
        'all_tegs': [],
        'is_complete': False,
        'current_teg': None,
        'satire_mode': False
    }

    def load_teg_list():
        """Load list of available TEGs."""
        try:
            all_data = load_all_data(exclude_teg_50=True)
            if all_data.empty:
                return []

            # Get unique TEGs sorted by TEGNum descending (latest first)
            teg_list = all_data.sort_values('TEGNum', ascending=False)[['TEG', 'TEGNum']].drop_duplicates()
            teg_names = teg_list['TEG'].tolist()
            state['all_tegs'] = teg_names

            # Set default to latest TEG
            if teg_names:
                teg_selector.set_options(teg_names)
                teg_selector.value = teg_names[0]
                state['current_teg'] = teg_names[0]

            return teg_names

        except Exception as e:
            print(f'Error loading TEG list: {e}')
            return []

    def is_teg_complete(teg_name: str) -> bool:
        """Check if a TEG is complete or in-progress."""
        try:
            completed_tegs = read_file('data/completed_tegs.csv')
            if completed_tegs.empty:
                return False

            # Check if TEG is in completed list
            matching = completed_tegs[completed_tegs['TEG'].str.contains(teg_name, na=False)]
            return not matching.empty

        except Exception:
            # Default to incomplete if we can't determine
            return False

    def display_reports():
        """Load and display reports for selected TEG."""
        try:
            if not teg_selector.value:
                content_card.clear()
                with content_card:
                    ui.label('Please select a TEG').classes('text-gray-600')
                return

            teg_name = teg_selector.value
            state['current_teg'] = teg_name
            state['is_complete'] = is_teg_complete(teg_name)

            # Extract TEG number from name (e.g., "TEG 25" from "TEG 25 - 2024")
            import re
            match = re.search(r'TEG (\d+)', teg_name)
            teg_num = int(match.group(1)) if match else None

            if not teg_num:
                content_card.clear()
                with content_card:
                    ui.label(f'Could not extract TEG number from: {teg_name}').classes('text-red-600')
                return

            content_card.clear()

            with content_card:
                # Create tabs for reports
                with ui.tabs() as tabs:
                    # Full TEG Report tab (only for complete TEGs)
                    if state['is_complete']:
                        with ui.tab(f'Full TEG Report (TEG {teg_num})'):
                            with ui.row().classes('w-full gap-4 items-center'):
                                ui.label('View Type:').classes('font-semibold')
                                report_type = ui.select(
                                    ['Normal', 'Satire'],
                                    label='',
                                    value='Normal'
                                ).classes('w-32')

                            report_content = ui.card().classes('w-full mt-4')

                            def load_full_report():
                                """Load full TEG report based on selected type."""
                                try:
                                    report_type_val = report_type.value
                                    if report_type_val == 'Satire':
                                        file_path = f'data/commentary/drafts/teg_{teg_num}_satire.md'
                                    else:
                                        file_path = f'data/commentary/teg_{teg_num}_main_report.md'

                                    content = read_teg_report_file(file_path)
                                    html_content = markdown.markdown(content)

                                    report_content.clear()
                                    with report_content:
                                        ui.html(html_content, sanitize=False)

                                except Exception as e:
                                    report_content.clear()
                                    with report_content:
                                        ui.label(f'Error loading report: {str(e)}').classes('text-red-600')

                            report_type.on_value_change(lambda: load_full_report())
                            load_full_report()

                    # Round Reports tabs
                    try:
                        num_rounds = get_teg_rounds(teg_num)
                    except Exception:
                        num_rounds = 4  # Default to 4 rounds

                    for round_num in range(1, num_rounds + 1):
                        with ui.tab(f'Round {round_num}'):
                            round_card = ui.card().classes('w-full')

                            try:
                                # Try new format first, then old format
                                file_path = f'data/commentary/round_reports/TEG{teg_num}_R{round_num}_report.md'
                                try:
                                    content = read_teg_report_file(file_path)
                                except:
                                    # Try alternative format
                                    file_path = f'data/commentary/round_reports/TEG_{teg_num}_Round_{round_num}_report.md'
                                    content = read_teg_report_file(file_path)

                                html_content = markdown.markdown(content)

                                with round_card:
                                    ui.html(html_content, sanitize=False)

                            except Exception as e:
                                with round_card:
                                    ui.label(f'Error loading Round {round_num} report: {str(e)}').classes('text-red-600')

                # Display completion status
                if state['is_complete']:
                    ui.label(f'TEG {teg_num} is complete').classes('text-sm text-green-600 mt-4')
                else:
                    ui.label(f'TEG {teg_num} is in progress').classes('text-sm text-orange-600 mt-4')

        except Exception as e:
            content_card.clear()
            with content_card:
                ui.label(f'Error: {str(e)}').classes('text-red-600')
                print(f'Error in teg_reports: {e}')
                import traceback
                traceback.print_exc()

    # ===== EVENT HANDLERS =====
    teg_selector.on_value_change(lambda: display_reports())

    # ===== INITIAL LOAD =====
    load_teg_list()
    if teg_selector.value:
        display_reports()
