"""
NiceGUI Prototype Page 1 - Stableford Scores by Round (Standalone)

Super minimal: Just show stableford scores by player and round.
- Dropdown to select TEG
- Raw data (what the function returns)
- Simple table
Done.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nicegui import ui
import pandas as pd

# Import functions
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import (
    filter_data_by_teg,
    aggregate_data,
    get_teg_leaderboard
)

# Load data
all_data = load_all_data()
available_tegs = sorted(all_data['TEGNum'].unique())

# Title
ui.label('Stableford Scores by Round').classes('text-h5')

# Dropdown and Refresh
with ui.row().classes('gap-4 items-end'):
    teg_select = ui.select(
        label='Select TEG:',
        options=available_tegs,
        value=available_tegs[-1] if available_tegs else None
    )
    refresh_btn = ui.button('Refresh')

ui.separator()

# Raw data section
ui.label('Raw Data (from aggregate_data())').classes('text-sm font-semibold')
raw_data_box = ui.card()

# Table section
ui.label('Table Display').classes('text-sm font-semibold mt-4')
table_box = ui.card()

# Using the new get_teg_leaderboard function
ui.separator().classes('mt-8')
ui.label('Using get_teg_leaderboard() Function').classes('text-sm font-semibold mt-4')

# Raw data section (get_teg_leaderboard)
ui.label('Raw Data (from get_teg_leaderboard())').classes('text-sm font-semibold')
raw_data_box_2 = ui.card()

# Table section (get_teg_leaderboard)
ui.label('Table Display').classes('text-sm font-semibold mt-4')
table_box_2 = ui.card()

def refresh():
    """Load and display data."""
    try:
        teg_num = int(teg_select.value)

        # Filter and aggregate
        teg_data = filter_data_by_teg(all_data, teg_num)
        result = aggregate_data(teg_data, aggregation_level='Round')

        if result.empty:
            ui.notify('No data for this TEG')
            return

        # Show raw data (what aggregate_data returns)
        raw_data_box.clear()
        with raw_data_box:
            ui.label(f'Shape: {result.shape[0]} rows × {result.shape[1]} columns')
            ui.label(f'Columns: {list(result.columns)}')
            ui.code(result.to_string(), language='text')

        # Pivot data: Player rows × Round columns
        pivoted = result.pivot_table(
            index='Player',
            columns='Round',
            values='Stableford',
            aggfunc='first'
        )

        # Add total column
        pivoted['Total'] = pivoted.sum(axis=1)

        # Rename columns to R1, R2, R3, R4 format
        pivoted.columns = [f'R{int(col)}' if isinstance(col, (int, float)) else col for col in pivoted.columns]

        # Reset index to make Player a column
        pivoted = pivoted.reset_index()

        # Show table
        table_box.clear()
        with table_box:
            rows = pivoted.to_dict(orient='records')
            columns = [
                {'name': col, 'label': col, 'field': col, 'align': 'left' if col == 'Player' else 'right'}
                for col in pivoted.columns
            ]
            ui.table(columns=columns, rows=rows)

        # Using get_teg_leaderboard function (simpler!)
        leaderboard = get_teg_leaderboard(result, 'Stableford')

        if leaderboard.empty:
            raw_data_box_2.clear()
            table_box_2.clear()
        else:
            # Show raw data
            raw_data_box_2.clear()
            with raw_data_box_2:
                ui.label(f'Shape: {leaderboard.shape[0]} rows × {leaderboard.shape[1]} columns')
                ui.label(f'Columns: {list(leaderboard.columns)}')
                ui.code(leaderboard.to_string(), language='text')

            # Show table
            table_box_2.clear()
            with table_box_2:
                rows_2 = leaderboard.to_dict(orient='records')
                columns_2 = [
                    {'name': col, 'label': col, 'field': col, 'align': 'left' if col in ['Rank', 'Player'] else 'right'}
                    for col in leaderboard.columns
                ]
                ui.table(columns=columns_2, rows=rows_2)

    except Exception as e:
        ui.notify(f'Error: {str(e)}', type='negative')

refresh_btn.on('click', refresh)
teg_select.on('update:model-value', lambda _: refresh())

# Load on start
refresh()

# Start the app
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Page 1: Stableford Scores', reload=True)
