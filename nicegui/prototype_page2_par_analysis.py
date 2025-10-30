"""
NiceGUI Prototype Page 2 - Average Scores by Par (Standalone)

Shows average gross vs par scores broken down by hole par (Par 3, 4, 5).
Users can filter by specific TEG or view all tournaments combined.

Shows:
  1. RAW DATA - Direct output from prepare_average_scores_by_par() function
  2. FORMATTED TABLE - Clean table display
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nicegui import ui
import pandas as pd

# Import teg_analysis functions
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import filter_data_by_teg
from teg_analysis.analysis.scoring import prepare_average_scores_by_par

# Load data
all_data = load_all_data()
available_tegs = sorted(all_data['TEGNum'].unique())
filter_options = ['All TEGs'] + list(available_tegs)

# Title
ui.label('Average Scores by Hole Par').classes('text-h5')

# Dropdown and Refresh
with ui.row().classes('gap-4 items-end'):
    filter_select = ui.select(
        label='Filter by TEG:',
        options=filter_options,
        value='All TEGs'
    )
    refresh_button = ui.button('Refresh')

ui.separator()

# Raw data section
ui.label('Raw Data (from prepare_average_scores_by_par())').classes('text-sm font-semibold')
raw_data_container = ui.card()

# Table section
ui.label('Table Display').classes('text-sm font-semibold mt-4')
formatted_table_container = ui.card()

def refresh_data():
    """Load and display data."""
    try:
        selected_filter = filter_select.value

        # Filter data if specific TEG selected
        if selected_filter == 'All TEGs':
            filtered_data = all_data
            filter_label = 'All TEGs'
        else:
            teg_num = int(selected_filter)
            filtered_data = filter_data_by_teg(all_data, teg_num)
            filter_label = f'TEG {teg_num}'

        if filtered_data.empty:
            ui.notify(f'No data found for {filter_label}')
            return

        # Call analysis function
        par_analysis_result = prepare_average_scores_by_par(filtered_data)

        # Show raw data
        raw_data_container.clear()
        with raw_data_container:
            ui.label(f'Shape: {par_analysis_result.shape[0]} rows × {par_analysis_result.shape[1]} columns')
            ui.label(f'Columns: {list(par_analysis_result.columns)}')
            ui.code(par_analysis_result.to_string(), language='text')


        # Show table
        formatted_table_container.clear()
        with formatted_table_container:
            ui.label(f'{filter_label}').classes('font-semibold')
            rows = par_analysis_result.to_dict(orient='records')
            columns = [{'name': col, 'label': col, 'field': col} for col in par_analysis_result.columns]
            ui.table(columns=columns, rows=rows)

    except Exception as e:
        ui.notify(f'Error: {str(e)}', type='negative')

refresh_button.on('click', refresh_data)
filter_select.on('update:model-value', lambda _: refresh_data())

# Initial load
refresh_data()

# Start the app
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Page 2: Average Scores by Par', reload=True)
