"""Current TEG Leaderboard page.

Displays the leaderboard for a selected TEG with two main competitions:
- TEG Trophy (Net) - using Stableford points for TEG 6+, NetVP for TEG 1-5
- Green Jacket (Gross) - using GrossVP

Features round-by-round breakdown (Player | R1 ... RN | Total format) with
automatic selection of the most recent TEG and manual TEG selection option.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # For teg_analysis imports
sys.path.insert(0, str(Path(__file__).parent))  # For local nicegui module imports

from nicegui import ui

# Import functions from teg_analysis
from teg_analysis.analysis.aggregation import (
    filter_data_by_teg,
    get_current_in_progress_teg_fast
)
from teg_analysis.analysis.scoring import get_net_competition_measure
from teg_analysis.display.html_tables import create_round_leaderboard_html

# Import shared components
from ui_helpers import create_nav_header
from shared_setup import all_data_leaderboard


@ui.page('/leaderboard')
def leaderboard_page():
    """Current TEG Leaderboard page."""
    create_nav_header('leaderboard')

    # Get available TEGs
    available_tegs = sorted(all_data_leaderboard['TEGNum'].unique())
    available_teg_labels = [f"TEG {num}" for num in available_tegs]

    # Get the current/latest TEG
    try:
        current_teg, _ = get_current_in_progress_teg_fast()
    except:
        current_teg = max(available_tegs) if available_tegs else None

    # Page title and description
    ui.label('Current TEG Leaderboard').classes('text-h5 font-bold mt-6')
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
    # LEADERBOARD DISPLAYS WITH BUTTON NAVIGATION
    # ============================================================================

    # Create button selection
    with ui.row().classes('gap-2 mt-6'):
        trophy_btn = ui.button('TEG Trophy (Net)', icon='emoji_events').props('no-caps unelevated')
        jacket_btn = ui.button('Green Jacket (Gross)', icon='workspace_premium').props('no-caps unelevated')

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
        trophy_btn.style('background-color: #228B22 !important; color: white !important;')
        jacket_btn.style('background-color: transparent !important; color: inherit !important;')

    def show_jacket():
        trophy_section.visible = False
        jacket_section.visible = True
        jacket_btn.style('background-color: #228B22 !important; color: white !important;')
        trophy_btn.style('background-color: transparent !important; color: inherit !important;')

    # Assign button handlers
    trophy_btn.on_click(show_trophy)
    jacket_btn.on_click(show_jacket)

    # Show trophy by default
    show_trophy()

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
            teg_data = filter_data_by_teg(all_data_leaderboard, teg_num)

            if teg_data.empty:
                with trophy_section:
                    ui.label('No data available for this TEG').classes('text-gray-500')
                with jacket_section:
                    ui.label('No data available for this TEG').classes('text-gray-500')
                return

            # ====== TEG TROPHY (NET) ======
            measure = get_net_competition_measure(teg_num)

            with trophy_section:
                ui.label(f'Using {measure} | {teg_str}').classes('text-sm text-gray-600')

                # Create HTML table
                if measure == 'Stableford':
                    # Higher Stableford is better
                    html = create_round_leaderboard_html(teg_data, measure, ascending=False)
                else:  # NetVP
                    # Lower NetVP is better
                    html = create_round_leaderboard_html(teg_data, measure, ascending=True)

                ui.html(html, sanitize=False)

            # ====== GREEN JACKET (GROSS) ======
            with jacket_section:
                ui.label(f'Using GrossVP | {teg_str}').classes('text-sm text-gray-600')

                # Create HTML table (lower GrossVP is better)
                html = create_round_leaderboard_html(teg_data, 'GrossVP', ascending=True)
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
