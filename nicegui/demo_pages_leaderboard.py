"""
NiceGUI Demo Page: Current TEG Leaderboard

Shows the leaderboard for the current/latest TEG with two main competitions:
- TEG Trophy (Net) - using Stableford points for TEG 6+, NetVP for TEG 1-5
- Green Jacket (Gross) - using GrossVP

Features:
- Automatically selects the most recent TEG
- Displays ranked leaderboards for both competitions with round-by-round breakdown
- Shows Player | R1 --- RN | Total format
- Allows manual TEG selection

This page demonstrates:
- load_all_data(): Load raw tournament data
- get_teg_leaderboard(): Create ranked leaderboard
- get_current_in_progress_teg_fast(): Detect latest TEG
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
    get_current_in_progress_teg_fast
)
from teg_analysis.analysis.scoring import get_net_competition_measure

# ============================================================================
# CUSTOM STYLING FOR FOREST GREEN BUTTONS
# ============================================================================

ui.add_css('''
    .forest-green-button {
        background-color: #228B22 !important;
        color: white !important;
    }
    .forest-green-button:hover {
        background-color: #1a6b1a !important;
    }
''')


# ============================================================================
# PAGE SETUP AND DATA LOADING
# ============================================================================

# Load data at module level (cached by NiceGUI)
all_data = load_all_data(exclude_teg_50=True)

# Get available TEGs
available_tegs = sorted(all_data['TEGNum'].unique())
available_teg_labels = [f"TEG {num}" for num in available_tegs]

# Get the current/latest TEG
try:
    current_teg, _ = get_current_in_progress_teg_fast()
except:
    current_teg = max(available_tegs) if available_tegs else None

# Page title and description
ui.label('Current TEG Leaderboard').classes('text-h5 font-bold')
ui.label(
    'View the leaderboard for the current or selected TEG. Shows both the '
    'TEG Trophy (Net) and Green Jacket (Gross) competitions with round-by-round breakdown.'
).classes('text-sm text-gray-600')

ui.separator()

# ============================================================================
# TEG SELECTION
# ============================================================================

ui.label('Controls').classes('text-h6 font-semibold mt-4')

with ui.row().classes('gap-4 items-end'):
    teg_select = ui.select(
        label='Select TEG:',
        options=available_teg_labels,
        value=f'TEG {current_teg}' if current_teg else available_teg_labels[-1] if available_teg_labels else None
    ).classes('w-48')
    refresh_btn = ui.button('Refresh', icon='refresh')

ui.separator()

# ============================================================================
# LEADERBOARD DISPLAYS WITH TABS
# ============================================================================

# Create tab selection buttons
with ui.row().classes('gap-2 mt-6'):
    trophy_btn = ui.button('TEG Trophy (Net)', icon='emoji_events').props('no-caps')
    jacket_btn = ui.button('Green Jacket (Gross)', icon='workspace_premium').props('no-caps')

# Create containers for each leaderboard
trophy_section = ui.card()
jacket_section = ui.card()

# Status card (created once, cleared on refresh)
ui.label('Tournament Status').classes('text-h6 font-semibold mt-6')
status_box = ui.card().classes('bg-gray-50')

# Helper function to toggle visibility
def show_trophy():
    trophy_section.visible = True
    jacket_section.visible = False
    trophy_btn.classes(add='forest-green-button').props(add='unelevated')
    jacket_btn.classes(remove='forest-green-button').props(remove='unelevated')

def show_jacket():
    trophy_section.visible = False
    jacket_section.visible = True
    jacket_btn.classes(add='forest-green-button').props(add='unelevated')
    trophy_btn.classes(remove='forest-green-button').props(remove='unelevated')

# Assign button handlers
trophy_btn.on_click(show_trophy)
jacket_btn.on_click(show_jacket)

# Show trophy by default
show_trophy()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_round_leaderboard_html(teg_data, measure, ascending=False, title="Leaderboard"):
    """
    Create an HTML table showing Player | R1 | R2 | ... | RN | Total

    Args:
        teg_data: Raw hole-by-hole DataFrame with Pl, Round, and measure columns
        measure: Column name to use for scoring (e.g., 'Stableford', 'GrossVP', 'NetVP')
        ascending: If True, lower scores are better; if False, higher scores are better
        title: Title for the leaderboard
    """
    if teg_data.empty or measure not in teg_data.columns:
        return '<p style="color: gray;">No data available</p>'

    # Aggregate data to Round level first
    round_agg = aggregate_data(teg_data, aggregation_level='Round')

    if round_agg.empty:
        return '<p style="color: gray;">No data available</p>'

    # Create pivot table: Player x Round with measure as values
    pivot = round_agg.pivot_table(
        index='Player',
        columns='Round',
        values=measure,
        aggfunc='sum'
    )

    if pivot.empty:
        return '<p style="color: gray;">No leaderboard data available</p>'

    # Calculate totals
    pivot['Total'] = pivot.sum(axis=1)

    # Sort by total (ascending or descending)
    pivot = pivot.sort_values('Total', ascending=ascending)

    # Round columns for display
    round_cols = [col for col in pivot.columns if col != 'Total']
    round_cols = sorted([col for col in round_cols if isinstance(col, int)])

    # Reorder columns: Round columns then Total
    cols = round_cols + ['Total']
    pivot = pivot[cols]

    # Create HTML table
    html_table = '<table style="border-collapse: collapse; width: 100%; font-family: monospace;">'
    html_table += '<thead style="background-color: #f0f0f0;">'
    html_table += '<tr>'
    html_table += '<th style="border: 1px solid #ccc; padding: 8px; text-align: left;">Player</th>'

    # Add round headers
    for round_num in round_cols:
        html_table += f'<th style="border: 1px solid #ccc; padding: 8px; text-align: center;">R{round_num}</th>'

    html_table += '<th style="border: 1px solid #ccc; padding: 8px; text-align: center; font-weight: bold;">Total</th>'
    html_table += '</tr>'
    html_table += '</thead>'
    html_table += '<tbody>'

    # Add rows
    for player, row in pivot.iterrows():
        html_table += '<tr>'
        html_table += f'<td style="border: 1px solid #ccc; padding: 8px;">{player}</td>'

        for round_num in round_cols:
            value = row[round_num]
            if pd.isna(value):
                cell_content = '-'
            else:
                cell_content = f'{int(value)}'
            html_table += f'<td style="border: 1px solid #ccc; padding: 8px; text-align: center;">{cell_content}</td>'

        total = row['Total']
        if pd.isna(total):
            total_content = '-'
        else:
            total_content = f'{int(total)}'
        html_table += f'<td style="border: 1px solid #ccc; padding: 8px; text-align: center; font-weight: bold;">{total_content}</td>'
        html_table += '</tr>'

    html_table += '</tbody>'
    html_table += '</table>'

    return html_table




# ============================================================================
# REFRESH FUNCTION
# ============================================================================

def refresh():
    """Load data and refresh all displays."""
    try:
        # Get selected TEG
        teg_str = teg_select.value
        teg_num = int(teg_str.replace('TEG ', ''))

        # Clear displays
        trophy_section.clear()
        jacket_section.clear()
        status_box.clear()

        # Filter data for selected TEG
        teg_data = filter_data_by_teg(all_data, teg_num)

        print(f"\n=== DEBUG INFO ===")
        print(f"TEG: {teg_num}")
        print(f"Raw data shape: {teg_data.shape}")
        print(f"Raw data columns: {list(teg_data.columns)}")
        print(f"Raw data sample:\n{teg_data.head()}")

        if teg_data.empty:
            with trophy_section:
                ui.label('No data available for this TEG').classes('text-gray-500')
            with jacket_section:
                ui.label('No data available for this TEG').classes('text-gray-500')
            return

        # Test aggregation
        print(f"\nTesting aggregation...")
        agg_test = aggregate_data(teg_data, aggregation_level='Round')
        print(f"Aggregated data shape: {agg_test.shape}")
        print(f"Aggregated data columns: {list(agg_test.columns)}")
        print(f"Aggregated data sample:\n{agg_test.head(20)}")

        # ====== TEG TROPHY (NET) ======
        measure = get_net_competition_measure(teg_num)
        print(f"\nNet competition measure for TEG {teg_num}: {measure}")

        with trophy_section:
            ui.label(f'Using {measure} | {teg_str}').classes('text-sm text-gray-600')

            # Create HTML table
            if measure == 'Stableford':
                # Higher Stableford is better
                html = create_round_leaderboard_html(teg_data, measure, ascending=False)
            else:  # NetVP
                # Lower NetVP is better
                html = create_round_leaderboard_html(teg_data, measure, ascending=True)

            print(f"Trophy HTML length: {len(html)}")
            print(f"Trophy HTML preview: {html[:200]}...")
            ui.html(html, sanitize=False)

        # ====== GREEN JACKET (GROSS) ======
        with jacket_section:
            ui.label(f'Using GrossVP | {teg_str}').classes('text-sm text-gray-600')

            # Create HTML table (lower GrossVP is better)
            html = create_round_leaderboard_html(teg_data, 'GrossVP', ascending=True)
            print(f"Jacket HTML length: {len(html)}")
            print(f"Jacket HTML preview: {html[:200]}...")
            ui.html(html, sanitize=False)

        # Show tournament status
        num_rounds = teg_data['Round'].nunique()
        num_players = teg_data['Pl'].nunique()
        with status_box:
            ui.label(f'Tournament Status: {num_players} players | {num_rounds} rounds completed').classes('text-sm')

    except Exception as e:
        import traceback
        error_msg = f'Error: {str(e)}'
        ui.notify(error_msg, type='negative')
        print(f'Detailed error: {e}')
        print(traceback.format_exc())

        # Display error in all views
        with trophy_section:
            ui.label(error_msg).classes('text-red-500')
        with jacket_section:
            ui.label(error_msg).classes('text-red-500')


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
    ui.run(title='Demo: Current TEG Leaderboard', reload=True)
