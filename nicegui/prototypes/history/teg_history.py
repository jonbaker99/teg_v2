"""TEG History - Complete list of all TEGs with winners.

This page displays:
- Complete history of all TEGs (past, present, and future)
- Winners for each competition: TEG Trophy (Net), Green Jacket (Gross), HMM Wooden Spoon
- Area information for each tournament
- TBC entries for incomplete/future TEGs

Corresponds to Streamlit page: streamlit/101TEG History.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import helper functions for loading and processing winners data
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from helpers.history_data_processing import load_cached_winners, prepare_complete_history_table_fast


def teg_history_content():
    """Display complete TEG history table with winners for each competition."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('TEG History').classes('text-h5 font-bold mt-6')
    ui.label('Complete list of all TEGs with competition winners').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA DISPLAY =====
    output_card = ui.card().classes('w-full')

    # ===== REFRESH/LOAD FUNCTION =====
    def load_and_display():
        """Load winners data and display complete history table."""
        try:
            output_card.clear()

            with output_card:
                # Load cached winners and check for missing winners
                cached_winners, missing_teg_nums = load_cached_winners()

                if cached_winners is None or cached_winners.empty:
                    ui.label('No winners data available').classes('text-orange-600')
                    return

                # Prepare complete history table (including future TEGs as TBC)
                history_table = prepare_complete_history_table_fast(cached_winners)

                if history_table.empty:
                    ui.label('No history data to display').classes('text-orange-600')
                    return

                # Convert DataFrame to HTML and display
                html_output = history_table.to_html(index=False, escape=False)
                ui.html(html_output, sanitize=False)

                # Add note if winners were missing
                if missing_teg_nums:
                    ui.label(
                        f'Note: Winners for TEGs {sorted(missing_teg_nums)} were calculated on-the-fly.'
                    ).classes('text-sm text-gray-600 mt-4')

                # Add footnote about TEG 5
                ui.label(
                    'TEG 5 Note: Different data format - outcomes may not be fully accurate'
                ).classes('text-xs text-gray-500 mt-2 italic')

        except Exception as e:
            with output_card:
                ui.label(f'Error loading data: {str(e)}').classes('text-red-600')
                print(f'Error in teg_history: {e}')
                import traceback
                traceback.print_exc()

    # ===== INITIAL LOAD =====
    load_and_display()
