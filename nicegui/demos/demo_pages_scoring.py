"""
NiceGUI Demo Page: Scoring Functions

This page demonstrates scoring-related functions from teg_analysis.analysis.scoring.
Each function shows:
1. Function signature
2. Function call with actual parameters being used
3. Raw data output (exactly what the function returns)

Functions demonstrated:
- get_net_competition_measure(): Determine net competition measure for a TEG
- prepare_average_scores_by_par(): Calculate average scores by par value
- format_vs_par(): Format values as vs-par scores

This serves as a learning tool for developers understanding the scoring system.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nicegui import ui
import pandas as pd

# Import functions from teg_analysis
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.scoring import (
    get_net_competition_measure,
    prepare_average_scores_by_par,
    format_vs_par
)


# ============================================================================
# PAGE SETUP AND DATA LOADING
# ============================================================================

# Load data at module level (cached by NiceGUI)
all_data = load_all_data()
available_tegs = sorted(all_data['TEGNum'].unique())

# Page title and description
ui.label('Function Explorer: Scoring Functions').classes('text-h5 font-bold')
ui.label(
    'Explore scoring utilities that handle score formatting, calculations, and analysis. '
    'These functions help with scoring consistency across different TEG rules.'
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
# FUNCTION 1: get_net_competition_measure
# ============================================================================

ui.label('Function 1: get_net_competition_measure()').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `get_net_competition_measure(teg_num) → str`')
    ui.label('Purpose: Determine the net competition measure for a specific TEG').classes('text-sm')
    ui.markdown('**Returns:** "NetVP" for TEGs 1-5, "Stableford" for TEG 6+')

ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
get_net_measure_raw_box = ui.card()

# ============================================================================
# FUNCTION 2: prepare_average_scores_by_par
# ============================================================================

ui.label('Function 2: prepare_average_scores_by_par()').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `prepare_average_scores_by_par(all_data) → pd.DataFrame`')
    ui.label('Purpose: Calculate average scores by par value (Par 3, 4, 5) for each player').classes('text-sm')
    ui.markdown('**Returns:** DataFrame showing average GrossVP by player and par, formatted as vs-par')

ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
prepare_avg_scores_raw_box = ui.card()

# ============================================================================
# FUNCTION 3: format_vs_par
# ============================================================================

ui.label('Function 3: format_vs_par()').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `format_vs_par(value) → str`')
    ui.label('Purpose: Format numeric values as vs-par scores (e.g., -5, E, +3)').classes('text-sm')
    ui.markdown('**Returns:** Formatted string (-N for under par, E for even, +N for over par)')

ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
format_vs_par_raw_box = ui.card()


# ============================================================================
# REFRESH FUNCTION - Updates all displays
# ============================================================================

def refresh():
    """Load data and refresh all function displays."""
    try:
        teg_num = int(teg_select.value)

        # ====== FUNCTION 1: get_net_competition_measure ======
        net_measure = get_net_competition_measure(teg_num)

        get_net_measure_raw_box.clear()
        with get_net_measure_raw_box:
            ui.label(f'Call: get_net_competition_measure(teg_num={teg_num})').classes('text-xs text-gray-600 font-mono')
            ui.label(f'Result: "{net_measure}"').classes('font-mono text-sm mt-2')
            ui.label('Explanation:').classes('text-xs text-gray-600 mt-3')
            if teg_num <= 5:
                ui.label(f'TEG {teg_num} uses NetVP (total net vs par) for net competition').classes('text-xs ml-4')
            else:
                ui.label(f'TEG {teg_num} uses Stableford points for net competition').classes('text-xs ml-4')

        # ====== FUNCTION 2: prepare_average_scores_by_par ======
        avg_scores = prepare_average_scores_by_par(all_data)

        prepare_avg_scores_raw_box.clear()
        with prepare_avg_scores_raw_box:
            ui.label('Call: prepare_average_scores_by_par(all_data)').classes('text-xs text-gray-600 font-mono')
            ui.label(f'Shape: {avg_scores.shape[0]} rows × {avg_scores.shape[1]} columns').classes('text-xs mt-2')
            ui.label(f'Columns: {list(avg_scores.columns)}').classes('text-xs')
            ui.code(avg_scores.head(10).to_string(), language='text')

        # ====== FUNCTION 3: format_vs_par ======
        format_vs_par_raw_box.clear()
        with format_vs_par_raw_box:
            ui.label('Call: format_vs_par(value) - Examples:').classes('text-xs text-gray-600 font-mono')
            format_examples = []
            test_values = [-5, -2, -1, 0, 1, 2, 5, None]
            for val in test_values:
                if val is None:
                    result = format_vs_par(val)
                    format_examples.append(f'  format_vs_par(None) = "{result}"')
                else:
                    result = format_vs_par(val)
                    format_examples.append(f'  format_vs_par({val:2d}) = "{result}"')
            ui.code('\n'.join(format_examples), language='text')

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
    ui.run(title='Demo: Scoring Functions', reload=True)
