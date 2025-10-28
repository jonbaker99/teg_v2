"""
NiceGUI Unified Demo Navigation

Combines three demo pages into a single application with unified navigation:
- Player Rankings by TEG (route: '/')
- Scoring Distribution (route: '/sc-count')
- Current TEG Leaderboard (route: '/leaderboard')

Navigate directly between pages using the header buttons without going through a menu.

This page demonstrates:
- Multi-page routing using @ui.page() decorators
- Shared data loading across pages
- Persistent navigation header
- Reusable helper functions
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # For teg_analysis imports
sys.path.insert(0, str(Path(__file__).parent))  # For local nicegui module imports

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
from teg_analysis.analysis.rankings import convert_pivot_scores_to_ranks, calculate_average_rank_from_ranked_df
from teg_analysis.analysis.scoring import get_net_competition_measure
from teg_analysis.display.formatters import format_crosstab_columns
from teg_analysis.display.html_tables import (
    generate_ranking_table_html,
    dataframe_to_html_table,
    create_round_leaderboard_html
)
from ui_helpers import create_nav_header


# ============================================================================
# CUSTOM STYLING FOR FOREST GREEN BUTTONS
# ============================================================================

ui.add_head_html('''
<style>
    .forest-green-button {
        background-color: #228B22 !important;
        color: white !important;
    }
    .forest-green-button:hover {
        background-color: #1a6b1a !important;
    }

    /* === RANKING TABLE STYLING (first-place and last-place cells) === */
    table td.first-place,
    table td.last-place {
        position: relative;
        text-align: center;
    }

    table td.first-place::before,
    table td.last-place::before {
        content: "";
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%,-50%);
        width: 20px;
        height: 20px;
        border-radius: 15%;
        z-index: 1;
    }

    table td.first-place span,
    table td.last-place span {
        position: relative;
        z-index: 2;
        display: inline-block;
        width: 20px;
        line-height: 20px;
        font-weight: bold;
    }

    /* First place: green background, white text */
    table td.first-place::before {
        background: green;
    }

    table td.first-place span {
        color: white;
    }

    /* Last place: light pink background, dark red text */
    table td.last-place::before {
        background: #FAE9E8;
    }

    table td.last-place span {
        color: #8b0000;
    }
</style>
''', shared=True)


# ============================================================================
# MODULE-LEVEL DATA LOADING (shared across all pages)
# ============================================================================

all_data_player_history = load_all_data()
all_data_leaderboard = load_all_data(exclude_teg_50=True)
all_data_sc_count = load_all_data(exclude_incomplete_tegs=False)




# ============================================================================
# PAGE 1: PLAYER RANKINGS BY TEG
# ============================================================================

@ui.page('/')
def player_rankings_page():
    """Player Rankings by TEG page."""
    create_nav_header('player_rankings')

    # Page title and description
    ui.label('Player Rankings by TEG').classes('text-h5 font-bold mt-6')
    ui.label(
        'View player rankings across all completed TEGs. Shows finishing positions '
        'for both the TEG Trophy (Net) and Green Jacket (Gross) competitions.'
    ).classes('text-sm text-gray-600')

    ui.separator()

    # ============================================================================
    # COMPETITION SELECTION
    # ============================================================================

    ui.label('Controls').classes('text-h6 font-semibold mt-4')

    with ui.row().classes('gap-4 items-end'):
        competition_options = {'TEG Trophy (Net)': 'net', 'Green Jacket (Gross)': 'gross'}
        competition_select = ui.select(
            label='Competition:',
            options=competition_options,
            value='TEG Trophy (Net)'
        ).classes('w-64')
        refresh_btn = ui.button('Refresh', icon='refresh')

    ui.separator()

    # ============================================================================
    # RANKINGS TABLE
    # ============================================================================

    ui.label('Rankings by TEG').classes('text-h6 font-semibold mt-6')

    # with ui.card().classes('bg-blue-50'):
    #     ui.label('Shows each player\'s finishing position in each TEG').classes('text-sm')
    # ui.label('Shows each player\'s finishing position in each TEG').classes('text-sm text-gray-600')

    rankings_box = ui.card()

    # ============================================================================
    # SUMMARY STATISTICS
    # ============================================================================

    ui.label('Summary Statistics').classes('text-h6 font-semibold mt-6')

    # with ui.card().classes('bg-blue-50'):
    #     ui.label('Average finishing position and position counts by player').classes('text-sm')
    # ui.label('Average finishing position and position counts by player').classes('text-sm')
    summary_box = ui.card()

    # ============================================================================
    # REFRESH FUNCTION
    # ============================================================================

    def refresh():
        """Load data and refresh all displays."""
        try:
            # Map competition display name back to value
            competition = competition_options.get(competition_select.value, 'net')

            # Clear existing content
            rankings_box.clear()
            summary_box.clear()

            # Aggregate data by TEG and Player
            aggregated_data = aggregate_data(all_data_player_history, aggregation_level='TEG')

            if competition == 'net':
                # TEG Trophy (Net) - use dynamic measure based on TEG number
                ui.label('TEG Trophy Rankings (Net Competition)').classes('text-h6 font-semibold mt-4')
                ui.label('Note: Uses NetVP for TEGs 1-5, Stableford for TEGs 6+').classes('text-xs text-gray-600')

                # Create pivot table with scores, then convert to ranks
                pivot_data = aggregated_data.pivot_table(
                    index='Player',
                    columns='TEGNum',
                    values='NetVP',
                    aggfunc='min'
                )

                # Convert scores to ranks (handling the dynamic measure)
                if not pivot_data.empty:
                    ranked_data = convert_pivot_scores_to_ranks(pivot_data, 'NetVP')

                    with rankings_box:
                        ui.label('TEG Trophy Rankings (by finishing position)').classes('font-semibold')
                        html_table = generate_ranking_table_html(ranked_data)
                        ui.html(html_table, sanitize=False)
                else:
                    with rankings_box:
                        ui.label('No data available').classes('text-gray-500')

                # Summary statistics - based on rankings from the table above
                with summary_box:
                    ui.label('Average Rank by Player').classes('font-semibold')
                    summary_stats = calculate_average_rank_from_ranked_df(ranked_data)
                    html_table = dataframe_to_html_table(summary_stats, include_index=False)
                    ui.html(html_table, sanitize=False)

            else:  # Gross
                # Green Jacket (Gross)
                ui.label('Green Jacket Rankings (Gross vs Par)').classes('text-h6 font-semibold mt-4')

                # Create pivot table with scores, then convert to ranks
                pivot_data = aggregated_data.pivot_table(
                    index='Player',
                    columns='TEGNum',
                    values='GrossVP',
                    aggfunc='min'
                )

                # Convert scores to ranks
                if not pivot_data.empty:
                    ranked_data = convert_pivot_scores_to_ranks(pivot_data, 'GrossVP')

                    with rankings_box:
                        ui.label('Green Jacket Rankings (by finishing position)').classes('font-semibold')
                        html_table = generate_ranking_table_html(ranked_data)
                        ui.html(html_table, sanitize=False)
                else:
                    with rankings_box:
                        ui.label('No data available').classes('text-gray-500')

                # Summary statistics - based on rankings from the table above
                with summary_box:
                    ui.label('Average Rank by Player').classes('font-semibold')
                    summary_stats = calculate_average_rank_from_ranked_df(ranked_data)
                    html_table = dataframe_to_html_table(summary_stats, include_index=False)
                    ui.html(html_table, sanitize=False)

        except Exception as e:
            ui.notify(f'Error: {str(e)}', type='negative')
            print(f'Detailed error: {e}')

    # ============================================================================
    # BUTTON HANDLERS AND INITIAL LOAD
    # ============================================================================

    refresh_btn.on('click', refresh)
    competition_select.on('update:model-value', lambda _: refresh())

    # Load data on page start
    refresh()


# ============================================================================
# PAGE 2: SCORING DISTRIBUTION
# ============================================================================

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


# ============================================================================
# PAGE 3: CURRENT TEG LEADERBOARD
# ============================================================================

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


# ============================================================================
# APP RUNNER
# ============================================================================

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='TEG Analysis Demos', reload=True)
