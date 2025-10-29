"""
NiceGUI Demo Page: Records Identification Functions

This page demonstrates record identification functions from teg_analysis.analysis.records.
Each function shows:
1. Function signature
2. Function call with actual parameters being used
3. Raw data output (exactly what the function returns)

Functions demonstrated:
- identify_aggregate_records_and_pbs(): Find records and personal bests/worsts
- identify_all_time_worsts(): Find all-time worst performances
- identify_streak_records(): Find streak records

This serves as a learning tool for developers understanding the records system.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nicegui import ui
import pandas as pd

# Import functions from teg_analysis
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import filter_data_by_teg, aggregate_data
from teg_analysis.analysis.rankings import add_ranks
from teg_analysis.analysis.records import (
    identify_aggregate_records_and_pbs,
    identify_all_time_worsts,
    identify_streak_records
)


# ============================================================================
# PAGE SETUP AND DATA LOADING
# ============================================================================

# Load data at module level (cached by NiceGUI)
all_data = load_all_data()
available_tegs = sorted(all_data['TEGNum'].unique())

# Page title and description
ui.label('Function Explorer: Records Identification Functions').classes('text-h5 font-bold')
ui.label(
    'Explore how the system identifies records, personal bests, and all-time worst performances. '
    'These functions work with ranked data to identify special achievements.'
).classes('text-sm text-gray-600')

ui.separator()

# ============================================================================
# INPUT CONTROLS
# ============================================================================

ui.label('Controls').classes('text-h6 font-semibold mt-4')

with ui.row().classes('gap-4 items-end'):
    teg_select = ui.select(
        label='Select TEG:',
        options=[f'TEG {t}' for t in available_tegs],
        value=f'TEG {available_tegs[-1]}' if available_tegs else None
    ).classes('w-48')
    refresh_btn = ui.button('Refresh All', icon='refresh')

ui.separator()

# ============================================================================
# FUNCTION 1: identify_aggregate_records_and_pbs
# ============================================================================

ui.label('Function 1: identify_aggregate_records_and_pbs()').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `identify_aggregate_records_and_pbs(df, selected_teg, selected_round=None) → dict`')
    ui.label('Purpose: Find all-time records, personal bests, and personal worsts for a TEG or round').classes('text-sm')
    ui.markdown('**Returns:** Dictionary with lists of records, personal_bests, and personal_worsts')

ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
identify_records_raw_box = ui.card()

# ============================================================================
# FUNCTION 2: identify_all_time_worsts
# ============================================================================

ui.label('Function 2: identify_all_time_worsts()').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `identify_all_time_worsts(df, selected_teg, selected_round=None) → list`')
    ui.label('Purpose: Identify all-time worst performances in a TEG or round').classes('text-sm')
    ui.markdown('**Returns:** List of dictionaries with player, metric, and value information')

ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
identify_worsts_raw_box = ui.card()

# ============================================================================
# FUNCTION 3: identify_streak_records
# ============================================================================

ui.label('Function 3: identify_streak_records()').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `identify_streak_records(all_data, streaks_df, selected_teg, selected_round=None) → dict`')
    ui.label('Purpose: Identify when player streaks match all-time streak records').classes('text-sm')
    ui.markdown('**Returns:** Dictionary containing a list of matching streak records')

ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
identify_streaks_raw_box = ui.card()


# ============================================================================
# REFRESH FUNCTION - Updates all displays
# ============================================================================

def refresh():
    """Load data and refresh all function displays."""
    try:
        selected_teg_str = teg_select.value  # e.g., "TEG 18"
        teg_num = int(selected_teg_str.split()[-1])

        # Prepare data: filter and aggregate to Round level, then add ranks
        # filtered_data = filter_data_by_teg(all_data, teg_num)
        filtered_data = all_data
        aggregated_data = aggregate_data(filtered_data, aggregation_level='Round')
        ranked_data = add_ranks(aggregated_data)

        # ====== FUNCTION 1: identify_aggregate_records_and_pbs ======
        records_dict = identify_aggregate_records_and_pbs(ranked_data, selected_teg=selected_teg_str)
        # records_dict = identify_aggregate_records_and_pbs(ranked_data)

        identify_records_raw_box.clear()
        with identify_records_raw_box:
            ui.label(f"Call: identify_aggregate_records_and_pbs(ranked_data, selected_teg='{selected_teg_str}')").classes('text-xs text-gray-600 font-mono')
            result_text = []
            result_text.append(f"Records found: {len(records_dict.get('records', []))}")
            result_text.append(f"Personal Bests found: {len(records_dict.get('personal_bests', []))}")
            result_text.append(f"Personal Worsts found: {len(records_dict.get('personal_worsts', []))}")
            result_text.append("")
            result_text.append("Full output:")

            # Format the dictionary for display
            import json
            result_text.append(json.dumps(records_dict, indent=2, default=str))

            ui.code('\n'.join(result_text), language='text')

        # ====== FUNCTION 2: identify_all_time_worsts ======
        worsts_list = identify_all_time_worsts(ranked_data, selected_teg=selected_teg_str)
        

        identify_worsts_raw_box.clear()
        with identify_worsts_raw_box:
            ui.label(f"Call: identify_all_time_worsts(ranked_data, selected_teg='{selected_teg_str}')").classes('text-xs text-gray-600 font-mono')
            result_text = []
            result_text.append(f"All-time worsts found: {len(worsts_list)}")
            result_text.append("")

            if worsts_list:
                import json
                result_text.append(json.dumps(worsts_list, indent=2, default=str))
            else:
                result_text.append("(No all-time worsts for this TEG)")

            ui.code('\n'.join(result_text), language='text')

        # ====== FUNCTION 3: identify_streak_records ======
        # Note: This function requires a streaks_df which we'll create an empty one for demo purposes
        try:
            # Try to use the function - it may fail gracefully if no streaks data
            empty_streaks = pd.DataFrame()
            streaks_dict = identify_streak_records(all_data, empty_streaks, selected_teg=selected_teg_str)

            identify_streaks_raw_box.clear()
            with identify_streaks_raw_box:
                ui.label(f"Call: identify_streak_records(all_data, empty_streaks_df, selected_teg='{selected_teg_str}')").classes('text-xs text-gray-600 font-mono')
                #ui.label(f"Call: identify_streak_records(all_data, empty_streaks_df')").classes('text-xs text-gray-600 font-mono')
                result_text = []
                result_text.append(f"Streak records found: {len(streaks_dict.get('records', []))}")
                result_text.append("")
                result_text.append("Output:")

                import json
                result_text.append(json.dumps(streaks_dict, indent=2, default=str))

                ui.code('\n'.join(result_text), language='text')
        except Exception as streak_error:
            identify_streaks_raw_box.clear()
            with identify_streaks_raw_box:
                ui.label(f"Call: identify_streak_records(all_data, empty_streaks_df, selected_teg='{selected_teg_str}')").classes('text-xs text-gray-600 font-mono')
                ui.label('Note: Streak records require full streak data (see error below):').classes('text-xs text-gray-500')
                ui.code(f'Error: {str(streak_error)}', language='text')

    except Exception as e:
        ui.notify(f'Error: {str(e)}', type='negative')
        print(f'Detailed error: {e}')  # For debugging


# ============================================================================
# BUTTON HANDLERS AND INITIAL LOAD
# ============================================================================

refresh_btn.on('click', refresh)
teg_select.on('update:model-value', lambda _: refresh())

# Load data on page start
refresh()


# ============================================================================
# APP RUNNER
# ============================================================================

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Demo: Records Identification Functions', reload=True)
