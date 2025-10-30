"""Handicaps - Display and manage player handicaps.

This page provides a comprehensive view of player handicaps, including:
- Current handicaps for the upcoming TEG with changes from previous
- Handicap history (all past handicaps)
- Draft handicap calculations for next TEG (if tournament is in progress)
- Interface for saving newly calculated handicaps

Corresponds to Streamlit page: streamlit/500Handicaps.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import (
    get_current_handicaps_formatted,
    read_file,
    get_hc,
    get_next_teg_and_check_if_in_progress_fast,
    get_current_in_progress_teg_fast,
    write_file,
    HANDICAPS_CSV,
    clear_all_caches
)


def format_change(val: float) -> str:
    """Format handicap change for display."""
    if val > 0:
        return f"+{val}"
    elif val < 0:
        return str(val)
    else:
        return "-"


def format_handicap_value(val: float) -> str:
    """Format handicap value for display."""
    if pd.isna(val) or val == 0:
        return "-"
    return str(int(val))


def handicaps_content():
    """Display and manage player handicaps."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Handicaps').classes('text-h5 font-bold mt-6')
    ui.label('Current and historical player handicaps').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA LOADING =====
    try:
        last_completed, next_tegnum, in_progress = get_next_teg_and_check_if_in_progress_fast()
        next_teg = f'TEG {next_tegnum}'
        last_completed_teg = next_tegnum - 1

        current_handicaps, handicaps_were_calculated = get_current_handicaps_formatted(last_completed_teg, next_tegnum)
        current_handicaps = current_handicaps.sort_values(by=next_teg, ascending=True)

        # ===== CURRENT HANDICAPS DISPLAY =====
        with ui.card().classes('w-full mb-6'):
            # Title with draft indicator
            if not handicaps_were_calculated:
                ui.label(f'{next_teg} Handicaps').classes('text-lg font-semibold')
            else:
                ui.label(f'{next_teg} Handicaps (Draft)').classes('text-lg font-semibold')
                ui.label('ⓘ Draft handicaps subject to final review').classes('text-sm text-blue-600 mb-3')

            # Display handicaps as metric-style cards in a grid
            with ui.row().classes('gap-4 w-full'):
                for idx, (_, row) in enumerate(current_handicaps.iterrows()):
                    with ui.column().classes('flex items-center'):
                        player_name = row['Handicap']
                        hc_value = row[next_teg]
                        change_value = row['Change']

                        with ui.card().classes('w-32'):
                            ui.label(player_name).classes('text-xs font-semibold text-center')
                            ui.label(str(hc_value)).classes('text-2xl font-bold text-center text-blue-600')

                            # Format and display change
                            change_str = format_change(change_value)
                            if change_value > 0:
                                change_color = 'text-red-600'  # Higher handicap is worse
                            elif change_value < 0:
                                change_color = 'text-green-600'  # Lower handicap is better
                            else:
                                change_color = 'text-gray-600'

                            ui.label(change_str).classes(f'text-sm text-center {change_color}')

            ui.label('Change shows difference in HC vs previous TEG').classes('text-xs text-gray-600 mt-3')

        # ===== SAVE HANDICAPS (if draft) =====
        if handicaps_were_calculated:
            with ui.card().classes('w-full mb-6 bg-blue-50'):
                ui.label('Save Calculated Handicaps?').classes('text-base font-semibold')
                ui.label('Press button below to save these calculated handicaps to the system').classes('text-sm text-gray-600 mb-4')

                def save_handicaps():
                    try:
                        calculated_handicaps_for_save = get_hc(next_tegnum)

                        # Read existing handicaps
                        existing_handicaps = read_file(HANDICAPS_CSV)

                        # Create new row for this TEG
                        new_row = {"TEG": next_teg}
                        for _, row in calculated_handicaps_for_save.iterrows():
                            player_initial = row['Pl']
                            handicap = row['hc']
                            new_row[player_initial] = handicap

                        # Fill missing players
                        for col in existing_handicaps.columns[1:]:
                            if col not in new_row:
                                new_row[col] = 0

                        # Add new row
                        new_row_df = pd.DataFrame([new_row])
                        updated_handicaps = pd.concat([existing_handicaps, new_row_df], ignore_index=True)

                        # Save to file
                        write_file(HANDICAPS_CSV, updated_handicaps, f"Add calculated handicaps for {next_teg}")

                        # Clear caches
                        clear_all_caches()

                        ui.notify(f'✅ Handicaps saved successfully!', type='positive')
                        # Reload page after brief delay
                        import time
                        time.sleep(1)
                        ui.navigate.reload()

                    except Exception as e:
                        ui.notify(f'❌ Error saving handicaps: {str(e)}', type='negative')

                ui.button('💾 Save to File', on_click=save_handicaps).props('color=primary')

        # ===== HANDICAP HISTORY =====
        with ui.expansion('Handicap History').classes('w-full'):
            try:
                historic_handicaps = read_file(HANDICAPS_CSV)
                historic_handicaps = historic_handicaps[historic_handicaps['TEG'] != 'TEG 50']

                # Format all columns except the first one
                for col in historic_handicaps.columns[1:]:
                    historic_handicaps[col] = historic_handicaps[col].apply(format_handicap_value)

                ui.html(historic_handicaps.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table full-width'
                ), sanitize=False)

            except FileNotFoundError:
                ui.label(f'File not found: {HANDICAPS_CSV}').classes('text-red-600')
            except pd.errors.EmptyDataError:
                ui.label('The handicaps file is empty.').classes('text-orange-600')
            except Exception as e:
                ui.label(f'Error reading handicaps file: {str(e)}').classes('text-red-600')

        # ===== DRAFT HANDICAPS (if tournament in progress) =====
        if in_progress:
            in_progress_teg, rounds_played = get_current_in_progress_teg_fast()
            next_next_tegnum = next_tegnum + 1

            with ui.expansion(f'Draft Handicaps for TEG {next_next_tegnum} (after {rounds_played} rounds of TEG {in_progress_teg})').classes('w-full'):
                try:
                    draft_hc = get_hc(next_next_tegnum).sort_values("hc_raw", ascending=True, na_position="last").reset_index(drop=True)
                    ui.html(draft_hc.to_html(
                        index=False,
                        justify='left',
                        classes='datawrapper-table'
                    ), sanitize=False)

                except Exception as e:
                    ui.label(f'Error loading draft handicaps: {str(e)}').classes('text-red-600')

    except Exception as e:
        ui.label(f'Error loading handicaps: {str(e)}').classes('text-red-600')
        print(f'Error in handicaps: {e}')
        import traceback
        traceback.print_exc()
