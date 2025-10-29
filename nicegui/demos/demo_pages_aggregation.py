"""
NiceGUI Demo Page: Aggregation Functions

This page demonstrates core aggregation functions from teg_analysis.analysis.aggregation.
Each function shows:
1. Function signature
2. Function call with actual parameters being used
3. Raw data output (exactly what the function returns)

Functions demonstrated:
- filter_data_by_teg(): Filter tournament data by TEG number
- aggregate_data(): Aggregate data to different levels (TEG, Round, Player, etc.)
- get_teg_leaderboard(): Create a full-TEG leaderboard with rankings
- get_round_leaderboard(): Create a single-round leaderboard
- get_teg_winners(): Generate winners across all TEGs

This serves as a learning tool for developers understanding the data pipeline.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nicegui import ui
import pandas as pd

# Import functions from teg_analysis
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import (
    filter_data_by_teg,
    aggregate_data,
    get_teg_leaderboard,
    get_round_leaderboard,
    get_teg_winners
)


# ============================================================================
# PAGE SETUP AND DATA LOADING
# ============================================================================

# Load data at module level (cached by NiceGUI)
all_data = load_all_data()
available_tegs = sorted(all_data['TEGNum'].unique())

# Page title and description
ui.label('Function Explorer: Aggregation Functions').classes('text-h5 font-bold')
ui.label(
    'Explore how core aggregation functions work. Select a TEG, then see how '
    'each function filters, aggregates, and transforms the data into useful outputs.'
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
    refresh_btn = ui.button('Refresh All', icon='refresh')

ui.separator()

# ============================================================================
# FUNCTION 1: filter_data_by_teg
# ============================================================================

ui.label('Function 1: filter_data_by_teg()').classes('text-h6 font-semibold mt-6')

# Function details
with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `filter_data_by_teg(all_data, selected_tegnum) → pd.DataFrame`')
    ui.label('Purpose: Filter raw tournament data to a specific TEG').classes('text-sm')
    ui.markdown('**Returns:** DataFrame with only rows matching the selected TEG')

# Raw data section
ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
filter_raw_box = ui.card()

# ============================================================================
# FUNCTION 2: aggregate_data
# ============================================================================

ui.label('Function 2: aggregate_data()').classes('text-h6 font-semibold mt-6')

# Function details
with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `aggregate_data(data, aggregation_level, measures=None, additional_group_fields=None) → pd.DataFrame`')
    ui.label('Purpose: Aggregate data by grouping at different levels (TEG, Round, Player, etc.)').classes('text-sm')
    ui.markdown('**Aggregation levels:** Player, TEG, Round, FrontBack (9-hole), Hole')

# Raw data section
ui.label('Raw Data Output (aggregated to Round level)').classes('text-sm font-semibold mt-4')
aggregate_raw_box = ui.card()

# ============================================================================
# FUNCTION 3: get_teg_leaderboard
# ============================================================================

ui.label('Function 3: get_teg_leaderboard()').classes('text-h6 font-semibold mt-6')

# Function details
with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `get_teg_leaderboard(df, measure, teg_num=None) → pd.DataFrame`')
    ui.label('Purpose: Transform round-level aggregated data into a leaderboard with rankings').classes('text-sm')
    ui.markdown('**Available measures:** Stableford, GrossVP, NetVP, Sc')

# Raw data section
ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
leaderboard_raw_box = ui.card()

# ============================================================================
# FUNCTION 4: get_round_leaderboard
# ============================================================================

ui.label('Function 4: get_round_leaderboard()').classes('text-h6 font-semibold mt-6')

# Function details
with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `get_round_leaderboard(df, measure, teg_num=None, round_num=None) → pd.DataFrame`')
    ui.label('Purpose: Create a single-round leaderboard (vs a full-TEG leaderboard)').classes('text-sm')
    ui.markdown('**Available measures:** Stableford, GrossVP, NetVP, Sc')

# Raw data section
ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
round_leaderboard_raw_box = ui.card()

# ============================================================================
# FUNCTION 5: get_teg_winners
# ============================================================================

ui.label('Function 5: get_teg_winners()').classes('text-h6 font-semibold mt-6')

# Function details
with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `get_teg_winners(df) → pd.DataFrame`')
    ui.label('Purpose: Generate winners summary across all TEGs (Best Gross, Best Net, Worst Net)').classes('text-sm')
    ui.markdown('**Returns:** DataFrame with TEG Trophy, Green Jacket, and Wooden Spoon winners')

# Raw data section
ui.label('Raw Data Output (all TEGs)').classes('text-sm font-semibold mt-4')
winners_raw_box = ui.card()


# ============================================================================
# REFRESH FUNCTION - Updates all displays
# ============================================================================

def refresh():
    """Load data and refresh all function displays."""
    try:
        teg_num = int(teg_select.value)

        # ====== FUNCTION 1: filter_data_by_teg ======
        filtered_data = filter_data_by_teg(all_data, teg_num)

        filter_raw_box.clear()
        with filter_raw_box:
            ui.label(f'Call: filter_data_by_teg(all_data, teg_num={teg_num})').classes('text-xs text-gray-600 font-mono')
            ui.label(f'Shape: {filtered_data.shape[0]} rows × {filtered_data.shape[1]} columns')
            ui.label(f'Columns: {list(filtered_data.columns)[:5]}... (showing first 5)')
            ui.code(filtered_data.head(10).to_string(), language='text')

        # ====== FUNCTION 2: aggregate_data ======
        aggregated_data = aggregate_data(filtered_data, aggregation_level='Round')

        aggregate_raw_box.clear()
        with aggregate_raw_box:
            ui.label(f"Call: aggregate_data(filtered_data, aggregation_level='Round')").classes('text-xs text-gray-600 font-mono')
            ui.label(f'Shape: {aggregated_data.shape[0]} rows × {aggregated_data.shape[1]} columns')
            ui.label(f'Columns: {list(aggregated_data.columns)}')
            ui.code(aggregated_data.to_string(), language='text')

        # ====== FUNCTION 3: get_teg_leaderboard ======
        leaderboard = get_teg_leaderboard(aggregated_data, measure='Stableford')

        leaderboard_raw_box.clear()
        with leaderboard_raw_box:
            ui.label(f"Call: get_teg_leaderboard(aggregated_data, measure='Stableford')").classes('text-xs text-gray-600 font-mono')
            if leaderboard.empty:
                ui.label('No leaderboard data available').classes('text-gray-500')
            else:
                ui.label(f'Shape: {leaderboard.shape[0]} rows × {leaderboard.shape[1]} columns')
                ui.label(f'Columns: {list(leaderboard.columns)}')
                ui.code(leaderboard.to_string(), language='text')

        # ====== FUNCTION 4: get_round_leaderboard ======
        # Show round 1 leaderboard as an example
        round_leaderboard = get_round_leaderboard(all_data, measure='Stableford', teg_num=teg_num, round_num=1)

        round_leaderboard_raw_box.clear()
        with round_leaderboard_raw_box:
            ui.label(f"Call: get_round_leaderboard(all_data, measure='Stableford', teg_num={teg_num}, round_num=1)").classes('text-xs text-gray-600 font-mono')
            if round_leaderboard.empty:
                ui.label('No round leaderboard data available').classes('text-gray-500')
            else:
                ui.label(f'Shape: {round_leaderboard.shape[0]} rows × {round_leaderboard.shape[1]} columns')
                ui.label(f'Columns: {list(round_leaderboard.columns)}')
                ui.code(round_leaderboard.to_string(), language='text')

        # ====== FUNCTION 5: get_teg_winners ======
        winners = get_teg_winners(all_data)

        winners_raw_box.clear()
        with winners_raw_box:
            ui.label(f'Call: get_teg_winners(all_data)').classes('text-xs text-gray-600 font-mono')
            if winners.empty:
                ui.label('No winners data available').classes('text-gray-500')
            else:
                ui.label(f'Shape: {winners.shape[0]} rows × {winners.shape[1]} columns')
                ui.label(f'Columns: {list(winners.columns)}')
                ui.code(winners.to_string(), language='text')

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
    ui.run(title='Demo: Aggregation Functions', reload=True)
