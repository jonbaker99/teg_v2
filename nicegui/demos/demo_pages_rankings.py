"""
NiceGUI Demo Page: Ranking Functions

This page demonstrates core ranking functions from teg_analysis.analysis.rankings.
Each function shows:
1. Function signature
2. Function call with actual parameters being used
3. Raw data output (exactly what the function returns)

Functions demonstrated:
- add_ranks(): Add ranking columns to DataFrames
- get_best(): Get best performances by measure
- get_worst(): Get worst performances by measure
- ordinal(): Convert numbers to ordinal format (1st, 2nd, 3rd)

This serves as a learning tool for developers understanding the ranking system.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nicegui import ui
import pandas as pd

# Import functions from teg_analysis
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import filter_data_by_teg, aggregate_data
from teg_analysis.analysis.rankings import (
    add_ranks,
    get_best,
    get_worst,
    ordinal
)


# ============================================================================
# PAGE SETUP AND DATA LOADING
# ============================================================================

# Load data at module level (cached by NiceGUI)
all_data = load_all_data()
available_tegs = sorted(all_data['TEGNum'].unique())

# Page title and description
ui.label('Function Explorer: Ranking Functions').classes('text-h5 font-bold')
ui.label(
    'Explore how ranking functions identify top and bottom performers. '
    'Select a TEG to see how rankings are calculated and used to find best/worst scores.'
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
# FUNCTION 1: add_ranks
# ============================================================================

ui.label('Function 1: add_ranks()').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `add_ranks(df, fields_to_rank=None, rank_ascending=None) → pd.DataFrame`')
    ui.label('Purpose: Add ranking columns for different measures (Sc, GrossVP, NetVP, Stableford)').classes('text-sm')
    ui.markdown('**Returns:** DataFrame with new columns like `Rank_within_player_Sc`, `Rank_within_all_Stableford`, etc.')

ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
add_ranks_raw_box = ui.card()

# ============================================================================
# FUNCTION 2: get_best
# ============================================================================

ui.label('Function 2: get_best()').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `get_best(df, measure_to_use, player_level=False, top_n=1) → pd.DataFrame`')
    ui.label('Purpose: Filter ranked data to show only the best performances').classes('text-sm')
    ui.markdown('**Measures:** Sc, GrossVP, NetVP, Stableford | **player_level:** Per-player vs all-time | **top_n:** Top N results')

ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
get_best_raw_box = ui.card()

# ============================================================================
# FUNCTION 3: get_worst
# ============================================================================

ui.label('Function 3: get_worst()').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `get_worst(df, measure_to_use, player_level=False, top_n=1) → pd.DataFrame`')
    ui.label('Purpose: Filter ranked data to show only the worst performances').classes('text-sm')
    ui.markdown('**Measures:** Sc, GrossVP, NetVP, Stableford | **player_level:** Per-player vs all-time | **top_n:** Top N results')

ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
get_worst_raw_box = ui.card()

# ============================================================================
# FUNCTION 4: ordinal
# ============================================================================

ui.label('Function 4: ordinal()').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.markdown('**Signature:** `ordinal(n) → str`')
    ui.label('Purpose: Convert numbers to ordinal representation (1st, 2nd, 3rd, 4th, etc.)').classes('text-sm')
    ui.markdown('**Returns:** String with ordinal format')

ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
ordinal_raw_box = ui.card()


# ============================================================================
# REFRESH FUNCTION - Updates all displays
# ============================================================================

def refresh():
    """Load data and refresh all function displays."""
    try:
        teg_num = int(teg_select.value)

        # Prepare data: filter and aggregate to Round level
        filtered_data = filter_data_by_teg(all_data, teg_num)
        aggregated_data = aggregate_data(filtered_data, aggregation_level='Round')

        # ====== FUNCTION 1: add_ranks ======
        ranked_data = add_ranks(aggregated_data, fields_to_rank=['Sc', 'Stableford'])

        add_ranks_raw_box.clear()
        with add_ranks_raw_box:
            ui.label(f"Call: add_ranks(aggregated_data, fields_to_rank=['Sc', 'Stableford'])").classes('text-xs text-gray-600 font-mono')
            ui.label(f'Shape: {ranked_data.shape[0]} rows × {ranked_data.shape[1]} columns')
            # Show only new rank columns
            rank_cols = [col for col in ranked_data.columns if 'Rank' in col]
            ui.label(f'New rank columns: {rank_cols}')
            display_data = ranked_data[['Player'] + rank_cols].drop_duplicates()
            ui.code(display_data.head(10).to_string(), language='text')

        # ====== FUNCTION 2: get_best ======
        best_stableford = get_best(ranked_data, measure_to_use='Stableford', player_level=False, top_n=1)

        get_best_raw_box.clear()
        with get_best_raw_box:
            ui.label(f"Call: get_best(ranked_data, measure_to_use='Stableford', player_level=False, top_n=1)").classes('text-xs text-gray-600 font-mono')
            if best_stableford.empty:
                ui.label('No best data available').classes('text-gray-500')
            else:
                ui.label(f'Shape: {best_stableford.shape[0]} rows × {best_stableford.shape[1]} columns')
                display_cols = ['Player', 'Round', 'Stableford', 'Rank_within_all_Stableford']
                display_cols = [col for col in display_cols if col in best_stableford.columns]
                ui.code(best_stableford[display_cols].to_string(), language='text')

        # ====== FUNCTION 3: get_worst ======
        worst_stableford = get_worst(ranked_data, measure_to_use='Stableford', player_level=False, top_n=1)

        get_worst_raw_box.clear()
        with get_worst_raw_box:
            ui.label(f"Call: get_worst(ranked_data, measure_to_use='Stableford', player_level=False, top_n=1)").classes('text-xs text-gray-600 font-mono')
            if worst_stableford.empty:
                ui.label('No worst data available').classes('text-gray-500')
            else:
                ui.label(f'Shape: {worst_stableford.shape[0]} rows × {worst_stableford.shape[1]} columns')
                display_cols = ['Player', 'Round', 'Stableford', 'Rank_within_all_Stableford']
                display_cols = [col for col in display_cols if col in worst_stableford.columns]
                ui.code(worst_stableford[display_cols].to_string(), language='text')

        # ====== FUNCTION 4: ordinal ======
        # Show examples of ordinal conversion
        ordinal_raw_box.clear()
        with ordinal_raw_box:
            ui.label('Examples of ordinal() conversion:').classes('text-xs text-gray-600 font-mono')
            ordinal_examples = []
            for n in range(1, 6):
                ordinal_examples.append(f'  ordinal({n}) = "{ordinal(n)}"')
            ordinal_examples.append(f'  ordinal(11) = "{ordinal(11)}"')
            ordinal_examples.append(f'  ordinal(21) = "{ordinal(21)}"')
            ordinal_examples.append(f'  ordinal(102) = "{ordinal(102)}"')
            ui.code('\n'.join(ordinal_examples), language='text')

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
    ui.run(title='Demo: Ranking Functions', reload=True)
