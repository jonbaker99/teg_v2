"""Score Distribution by Player and TEG page.

Displays the distribution of different score types (raw scores, scores vs par,
or stableford points) broken down by player or by TEG number. Includes filters
for specific players, TEGs, and hole par values.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # For teg_analysis imports
sys.path.insert(0, str(Path(__file__).parent))  # For local nicegui module imports

import pandas as pd
from nicegui import ui

# Import functions from teg_analysis
from teg_analysis.display.formatters import format_crosstab_columns
from teg_analysis.display.html_tables import dataframe_to_html_table

# Import shared components
from ui_helpers import create_nav_header
from shared_setup import all_data_sc_count


@ui.page('/sc-count')
def sc_count_page():
    """Score Distribution page."""
    create_nav_header('sc_count')

    # Page title and description
    ui.label('Scoring Distribution').classes('text-h5 font-bold mt-6')
    ui.label(
        'Explore the distribution of different score types. See how often each score '
        '(or score vs par, or stableford points) appears in the dataset.'
    ).classes('text-sm text-gray-600')

    ui.separator()

    # ============================================================================
    # FILTER CONTROLS
    # ============================================================================

    ui.label('Controls').classes('text-h6 font-semibold mt-4')

    with ui.row().classes('gap-4 items-center flex-wrap'):
        score_type_options = {
            'Scores': 'Sc',
            'Scores vs Par': 'GrossVP',
            'Stableford Points': 'Stableford'
        }
        score_type_select = ui.select(
            label='Score Type:',
            options=score_type_options,
            value='Stableford Points'
        ).classes('w-48')

    with ui.row().classes('gap-4 items-center flex-wrap'):
        # Get available options
        available_players = ['All players'] + sorted(all_data_sc_count['Pl'].unique().tolist())
        available_tegs = ['All TEGs'] + sorted([f"TEG {num}" for num in all_data_sc_count['TEGNum'].unique()])
        available_pars = sorted(all_data_sc_count['PAR'].unique().tolist())

        player_select = ui.select(
            label='Player:',
            options=available_players,
            value='All players'
        ).classes('w-48')

        teg_select = ui.select(
            label='TEG:',
            options=available_tegs,
            value='All TEGs'
        ).classes('w-48')

        par_select = ui.select(
            label='Par:',
            options=['All pars'] + [str(p) for p in available_pars],
            value='All pars'
        ).classes('w-40')

    display_mode = ui.radio(
        options=['Count', 'Percentage'],
        value='Percentage'
    ).props('inline')
    ui.label('Display Mode:').classes('text-sm')

    refresh_btn = ui.button('Refresh', icon='refresh')

    ui.separator()

    # ============================================================================
    # DISPLAY AREAS WITH BUTTON NAVIGATION
    # ============================================================================

    # Create button navigation
    with ui.row().classes('gap-2 mt-6'):
        player_btn = ui.button('Distribution by Player', icon='people').props('no-caps unelevated')
        teg_btn = ui.button('Distribution by TEG', icon='calendar_month').props('no-caps unelevated')

    # Create containers for each view
    player_dist_box = ui.card()
    teg_dist_box = ui.card()

    # Helper function to toggle visibility
    def show_player():
        player_dist_box.visible = True
        teg_dist_box.visible = False
        player_btn.style('background-color: #228B22 !important; color: white !important;')
        teg_btn.style('background-color: transparent !important; color: inherit !important;')

    def show_teg():
        player_dist_box.visible = False
        teg_dist_box.visible = True
        teg_btn.style('background-color: #228B22 !important; color: white !important;')
        player_btn.style('background-color: transparent !important; color: inherit !important;')

    # Assign button handlers
    player_btn.on_click(show_player)
    teg_btn.on_click(show_teg)

    # Show player view by default
    show_player()

    # ============================================================================
    # REFRESH FUNCTION
    # ============================================================================

    def refresh():
        """Load data and refresh displays."""
        try:
            # Get selected values and map score type from display name to field name
            score_type_display = score_type_select.value
            score_type = score_type_options.get(score_type_display, 'Stableford')
            selected_player = player_select.value
            selected_teg = teg_select.value
            selected_par = par_select.value
            mode = display_mode.value

            # Clear displays
            player_dist_box.clear()
            teg_dist_box.clear()

            # Apply filters
            filtered_data = all_data_sc_count.copy()

            # Filter by player
            if selected_player != 'All players':
                filtered_data = filtered_data[filtered_data['Pl'] == selected_player]

            # Filter by TEG
            if selected_teg != 'All TEGs':
                teg_num = int(selected_teg.replace('TEG ', ''))
                filtered_data = filtered_data[filtered_data['TEGNum'] == teg_num]

            # Filter by par
            if selected_par != 'All pars':
                par_val = int(selected_par)
                filtered_data = filtered_data[filtered_data['Par'] == par_val]

            # ====== BY PLAYER ======
            with player_dist_box:
                ui.label(
                    f'Score distribution by player ({score_type_display} | '
                    f'{selected_teg} | Par {selected_par})'
                ).classes('font-semibold')

                if filtered_data.empty:
                    ui.label('No data available for selected filters').classes('text-gray-500')
                else:
                    # Create crosstab: player vs score value
                    crosstab_player = pd.crosstab(
                        filtered_data['Pl'],
                        filtered_data[score_type]
                    )

                    # Format column headers based on score type
                    crosstab_player = format_crosstab_columns(crosstab_player, score_type)

                    if mode == 'Percentage':
                        # Convert to percentages
                        crosstab_player = (crosstab_player.div(crosstab_player.sum(axis=1), axis=0) * 100).round(1)
                        crosstab_player = crosstab_player.applymap(lambda x: f'{x:.1f}%' if pd.notna(x) else '')
                    else:
                        crosstab_player = crosstab_player.astype(int)

                    html_table = dataframe_to_html_table(crosstab_player)
                    ui.html(html_table, sanitize=False)

            # ====== BY TEG ======
            with teg_dist_box:
                ui.label(
                    f'Score distribution by TEG ({score_type_display} | '
                    f'{selected_player} | Par {selected_par})'
                ).classes('font-semibold')

                if filtered_data.empty:
                    ui.label('No data available for selected filters').classes('text-gray-500')
                else:
                    # Create crosstab: TEG vs score value
                    crosstab_teg = pd.crosstab(
                        filtered_data['TEGNum'],
                        filtered_data[score_type]
                    )
                    crosstab_teg.index = [f'TEG {num}' for num in crosstab_teg.index]

                    # Format column headers based on score type
                    crosstab_teg = format_crosstab_columns(crosstab_teg, score_type)

                    if mode == 'Percentage':
                        # Convert to percentages
                        crosstab_teg = (crosstab_teg.div(crosstab_teg.sum(axis=1), axis=0) * 100).round(1)
                        crosstab_teg = crosstab_teg.applymap(lambda x: f'{x:.1f}%' if pd.notna(x) else '')
                    else:
                        crosstab_teg = crosstab_teg.astype(int)

                    html_table = dataframe_to_html_table(crosstab_teg)
                    ui.html(html_table, sanitize=False)

        except Exception as e:
            ui.notify(f'Error: {str(e)}', type='negative')
            print(f'Detailed error: {e}')

    # ============================================================================
    # BUTTON HANDLERS AND INITIAL LOAD
    # ============================================================================

    refresh_btn.on('click', refresh)
    score_type_select.on('update:model-value', lambda _: refresh())
    player_select.on('update:model-value', lambda _: refresh())
    teg_select.on('update:model-value', lambda _: refresh())
    par_select.on('update:model-value', lambda _: refresh())
    display_mode.on('update:model-value', lambda _: refresh())

    # Load data on page start
    refresh()
