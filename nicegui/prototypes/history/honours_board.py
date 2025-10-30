"""Honours Board - Player tournament wins across all competitions.

This page displays:
- TEG Trophy wins summary (Net competition winners)
- Green Jacket wins summary (Gross competition winners)
- HMM Wooden Spoon wins summary (Last place)
- Doubles (players who won both Trophy and Jacket in same TEG)
- Eagles scored in tournament history
- Holes in One scored in tournament history

Corresponds to Streamlit page: streamlit/101TEG Honours Board.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading and processing utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import load_all_data, get_teg_winners
from utils_win_tables import summarise_teg_wins, compress_ranges
from helpers.history_data_processing import (
    calculate_trophy_jacket_doubles,
    get_eagles_data,
    get_holes_in_one_data,
    load_cached_winners
)


def honours_board_content():
    """Display player honours boards for various tournament achievements."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Honours Board').classes('text-h5 font-bold mt-6')
    ui.label('Player tournament wins and notable achievements').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA DISPLAY AREA =====
    content_area = ui.card().classes('w-full')

    def display_honours():
        """Load and display all honours board data."""
        try:
            content_area.clear()

            with content_area:
                # Load data
                all_data = load_all_data(exclude_incomplete_tegs=True, exclude_teg_50=True)
                if all_data.empty:
                    ui.label('No data available').classes('text-red-600')
                    return

                # Get winners from data
                winners_df = get_teg_winners(all_data)
                if winners_df.empty:
                    ui.label('No winners data available').classes('text-red-600')
                    return

                # ===== SECTION SELECTOR =====
                section_state = {'current': 'trophy'}

                def set_section(section_name):
                    section_state['current'] = section_name

                # Button bar to select section
                with ui.row().classes('gap-2 mb-4 flex-wrap'):
                    ui.button('Trophy Wins', on_click=lambda: set_section('trophy')).props('flat')
                    ui.button('Jacket Wins', on_click=lambda: set_section('jacket')).props('flat')
                    ui.button('Spoon', on_click=lambda: set_section('spoon')).props('flat')
                    ui.button('Doubles', on_click=lambda: set_section('doubles')).props('flat')
                    ui.button('Eagles', on_click=lambda: set_section('eagles')).props('flat')
                    ui.button('Holes in One', on_click=lambda: set_section('aces')).props('flat')

                # ===== SECTION 1: TEG TROPHY WINS =====
                trophy_card = ui.card().classes('w-full')
                trophy_card.bind_visibility_from(section_state, 'current', lambda v: v == 'trophy')

                with trophy_card:
                    try:
                        trophy_summary = summarise_teg_wins(winners_df, 'TEG Trophy')
                        if not trophy_summary.empty:
                            trophy_summary['TEGs'] = trophy_summary['TEGs'].apply(
                                lambda x: x
                            )
                            trophy_html = trophy_summary.to_html(index=False, escape=False, classes='datawrapper-table')
                            ui.html(trophy_html, sanitize=False)
                        else:
                            ui.label('No data available').classes('text-gray-600')
                    except Exception as e:
                        ui.label(f'Error loading Trophy wins: {str(e)}').classes('text-red-600')

                # ===== SECTION 2: GREEN JACKET WINS =====
                jacket_card = ui.card().classes('w-full')
                jacket_card.bind_visibility_from(section_state, 'current', lambda v: v == 'jacket')

                with jacket_card:
                    try:
                        jacket_summary = summarise_teg_wins(winners_df, 'Green Jacket')
                        if not jacket_summary.empty:
                            jacket_summary['TEGs'] = jacket_summary['TEGs'].apply(
                                lambda x: x
                            )
                            jacket_html = jacket_summary.to_html(index=False, escape=False, classes='datawrapper-table')
                            ui.html(jacket_html, sanitize=False)
                        else:
                            ui.label('No data available').classes('text-gray-600')
                    except Exception as e:
                        ui.label(f'Error loading Jacket wins: {str(e)}').classes('text-red-600')

                # ===== SECTION 3: HMM WOODEN SPOON WINS =====
                spoon_card = ui.card().classes('w-full')
                spoon_card.bind_visibility_from(section_state, 'current', lambda v: v == 'spoon')

                with spoon_card:
                    try:
                        spoon_summary = summarise_teg_wins(winners_df, 'HMM Wooden Spoon')
                        if not spoon_summary.empty:
                            spoon_summary['TEGs'] = spoon_summary['TEGs'].apply(
                                lambda x: x
                            )
                            spoon_html = spoon_summary.to_html(index=False, escape=False, classes='datawrapper-table')
                            ui.html(spoon_html, sanitize=False)
                        else:
                            ui.label('No data available').classes('text-gray-600')
                    except Exception as e:
                        ui.label(f'Error loading Spoon data: {str(e)}').classes('text-red-600')

                # ===== SECTION 4: DOUBLES (TROPHY + JACKET SAME TEG) =====
                doubles_card = ui.card().classes('w-full')
                doubles_card.bind_visibility_from(section_state, 'current', lambda v: v == 'doubles')

                with doubles_card:
                    try:
                        # Clean winners data (remove asterisks)
                        clean_winners = winners_df.copy()
                        if 'TEG Trophy' in clean_winners.columns:
                            clean_winners['TEG Trophy'] = clean_winners['TEG Trophy'].str.replace('*', '', regex=False)
                        if 'Green Jacket' in clean_winners.columns:
                            clean_winners['Green Jacket'] = clean_winners['Green Jacket'].str.replace('*', '', regex=False)

                        doubles_df, doubles_count = calculate_trophy_jacket_doubles(clean_winners)
                        if not doubles_df.empty:
                            ui.label(f'Total doubles: {doubles_count}').classes('text-sm font-semibold mb-2')
                            doubles_html = doubles_df.to_html(index=False, escape=False, classes='datawrapper-table')
                            ui.html(doubles_html, sanitize=False)
                        else:
                            ui.label('No doubles found').classes('text-gray-600')
                    except Exception as e:
                        ui.label(f'Error loading Doubles data: {str(e)}').classes('text-red-600')

                # ===== SECTION 5: EAGLES =====
                eagles_card = ui.card().classes('w-full')
                eagles_card.bind_visibility_from(section_state, 'current', lambda v: v == 'eagles')

                with eagles_card:
                    try:
                        eagles_df = get_eagles_data(all_data)
                        if not eagles_df.empty:
                            ui.label(f'Total eagles: {len(eagles_df)}').classes('text-sm font-semibold mb-2')
                            eagles_html = eagles_df.to_html(index=False, escape=False, classes='datawrapper-table')
                            ui.html(eagles_html, sanitize=False)
                        else:
                            ui.label('No eagles found in tournament history').classes('text-gray-600')
                    except Exception as e:
                        ui.label(f'Error loading Eagles data: {str(e)}').classes('text-red-600')

                # ===== SECTION 6: HOLES IN ONE =====
                aces_card = ui.card().classes('w-full')
                aces_card.bind_visibility_from(section_state, 'current', lambda v: v == 'aces')

                with aces_card:
                    try:
                        aces_df = get_holes_in_one_data(all_data)
                        if not aces_df.empty:
                            ui.label(f'Total holes in one: {len(aces_df)}').classes('text-sm font-semibold mb-2')
                            aces_html = aces_df.to_html(index=False, escape=False, classes='datawrapper-table')
                            ui.html(aces_html, sanitize=False)
                        else:
                            ui.label('No holes in one found in tournament history').classes('text-gray-600')
                    except Exception as e:
                        ui.label(f'Error loading Holes in One data: {str(e)}').classes('text-red-600')

        except Exception as e:
            content_area.clear()
            with content_area:
                ui.label(f'Error: {str(e)}').classes('text-red-600')
                print(f'Error in honours_board: {e}')
                import traceback
                traceback.print_exc()

    # ===== INITIAL LOAD =====
    display_honours()
