"""
NiceGUI Demo Page: Metadata & Reference Functions

This page demonstrates metadata and reference data functions from teg_analysis.core.metadata and data_loader.
Each function shows:
1. Function signature
2. Function call with actual parameters being used
3. Raw data output (exactly what the function returns)

Functions demonstrated:
- get_teg_metadata(): Get metadata for a TEG or specific round
- load_course_info(): Load unique course/area combinations
- get_player_name(): Convert player initials to full names

This serves as a learning tool for developers understanding the reference data system.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nicegui import ui
import pandas as pd

# Import functions from teg_analysis
from teg_analysis.core.data_loader import load_all_data, get_player_name
from teg_analysis.core.metadata import get_teg_metadata, load_course_info


# ============================================================================
# PAGE SETUP AND DATA LOADING
# ============================================================================

# Load data at module level (cached by NiceGUI)
all_data = load_all_data()
available_tegs = sorted(all_data['TEGNum'].unique())
available_rounds = sorted(all_data['Round'].unique())

# Page title and description
ui.label('Function Explorer: Metadata & Reference Functions').classes('text-h5 font-bold')
ui.label(
    'Explore metadata and reference data functions that provide information about TEGs, courses, and players. '
    'These functions load configuration and reference data from CSV files.'
).classes('text-sm text-gray-600')

ui.separator()

# ============================================================================
# INPUT CONTROLS
# ============================================================================

ui.label('Controls').classes('text-h6 font-semibold mt-4')

with ui.row().classes('gap-4 items-end'):
    teg_select = ui.select(
        label='Select TEG:',
        options=available_tegs,
        value=available_tegs[-1] if available_tegs else None
    ).classes('w-48')
    round_select = ui.select(
        label='Select Round:',
        options=available_rounds,
        value=1
    ).classes('w-48')
    refresh_btn = ui.button('Refresh All', icon='refresh')

ui.separator()

# ============================================================================
# FUNCTION 1: get_teg_metadata (TEG-level)
# ============================================================================

ui.label('Function 1a: get_teg_metadata() - TEG-level').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `get_teg_metadata(teg_num, round_num=None) → dict`')
    ui.label('Purpose: Get metadata (area, course, date, year) for a TEG or specific round').classes('text-sm')
    ui.markdown('**Returns:** Dictionary with metadata fields or empty dict if not found')

ui.label('Raw Data Output (TEG-level)').classes('text-sm font-semibold mt-4')
get_teg_meta_raw_box = ui.card()

# ============================================================================
# FUNCTION 2: get_teg_metadata (Round-level)
# ============================================================================

ui.label('Function 1b: get_teg_metadata() - Round-level').classes('text-h6 font-semibold mt-6')

ui.label('Raw Data Output (Round-level)').classes('text-sm font-semibold mt-4')
get_round_meta_raw_box = ui.card()

# ============================================================================
# FUNCTION 3: load_course_info
# ============================================================================

ui.label('Function 2: load_course_info()').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `load_course_info() → pd.DataFrame`')
    ui.label('Purpose: Load unique course and area combinations from round_info.csv').classes('text-sm')
    ui.markdown('**Returns:** DataFrame with columns [Course, Area]')

ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
load_course_raw_box = ui.card()

# ============================================================================
# FUNCTION 4: get_player_name
# ============================================================================

ui.label('Function 3: get_player_name()').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `get_player_name(initials) → str`')
    ui.label('Purpose: Convert player initials to full names').classes('text-sm')
    ui.markdown('**Returns:** Full player name or "Unknown Player" if not found')

ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
get_player_name_raw_box = ui.card()


# ============================================================================
# REFRESH FUNCTION - Updates all displays
# ============================================================================

def refresh():
    """Load data and refresh all function displays."""
    try:
        teg_num = int(teg_select.value)
        round_num = int(round_select.value)

        # ====== FUNCTION 1a: get_teg_metadata (TEG-level) ======
        teg_meta = get_teg_metadata(teg_num)

        get_teg_meta_raw_box.clear()
        with get_teg_meta_raw_box:
            ui.label(f'Call: get_teg_metadata(teg_num={teg_num})').classes('text-xs text-gray-600 font-mono')
            if teg_meta:
                import json
                ui.code(json.dumps(teg_meta, indent=2, default=str), language='text')
            else:
                ui.label('(No metadata found for this TEG)').classes('text-gray-500 text-sm')

        # ====== FUNCTION 1b: get_teg_metadata (Round-level) ======
        round_meta = get_teg_metadata(teg_num, round_num=round_num)

        get_round_meta_raw_box.clear()
        with get_round_meta_raw_box:
            ui.label(f'Call: get_teg_metadata(teg_num={teg_num}, round_num={round_num})').classes('text-xs text-gray-600 font-mono')
            if round_meta:
                import json
                ui.code(json.dumps(round_meta, indent=2, default=str), language='text')
            else:
                ui.label('(No metadata found for this TEG/Round)').classes('text-gray-500 text-sm')

        # ====== FUNCTION 2: load_course_info ======
        course_info = load_course_info()

        load_course_raw_box.clear()
        with load_course_raw_box:
            ui.label('Call: load_course_info()').classes('text-xs text-gray-600 font-mono')
            ui.label(f'Shape: {course_info.shape[0]} rows × {course_info.shape[1]} columns').classes('text-xs mt-2')
            ui.label(f'Columns: {list(course_info.columns)}').classes('text-xs')
            ui.code(course_info.to_string(), language='text')

        # ====== FUNCTION 3: get_player_name ======
        # Get unique players from the data
        unique_players = sorted(all_data['Pl'].unique())
        player_name_examples = []

        # Show first few players
        for player_code in unique_players[:5]:
            full_name = get_player_name(player_code)
            player_name_examples.append(f'  get_player_name("{player_code}") = "{full_name}"')

        get_player_name_raw_box.clear()
        with get_player_name_raw_box:
            ui.label('Call: get_player_name(initials) - Examples:').classes('text-xs text-gray-600 font-mono')
            ui.code('\n'.join(player_name_examples), language='text')

    except Exception as e:
        ui.notify(f'Error: {str(e)}', type='negative')
        print(f'Detailed error: {e}')  # For debugging


# ============================================================================
# BUTTON HANDLERS AND INITIAL LOAD
# ============================================================================

refresh_btn.on('click', refresh)
teg_select.on('update:model-value', lambda _: refresh())
round_select.on('update:model-value', lambda _: refresh())

# Load data on page start
refresh()


# ============================================================================
# APP RUNNER
# ============================================================================

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Demo: Metadata & Reference Functions', reload=True)
