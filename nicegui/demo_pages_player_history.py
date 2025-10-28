"""Player Rankings by TEG page.

Displays player rankings across all completed TEGs for the two main competitions:
- TEG Trophy (Net competition using dynamic measure: NetVP for TEGs 1-5, Stableford for TEGs 6+)
- Green Jacket (Gross vs Par competition)

Includes summary statistics showing average finishing position by player.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # For teg_analysis imports
sys.path.insert(0, str(Path(__file__).parent))  # For local nicegui module imports

from nicegui import ui

# Import functions from teg_analysis
from teg_analysis.analysis.aggregation import aggregate_data
from teg_analysis.analysis.rankings import convert_pivot_scores_to_ranks, calculate_average_rank_from_ranked_df
from teg_analysis.display.html_tables import generate_ranking_table_html, dataframe_to_html_table

# Import shared components
from ui_helpers import create_nav_header
from shared_setup import all_data_player_history


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

    title_box = ui.card().classes('bg-transparent border-0 shadow-none')
    rankings_box = ui.card()

    # ============================================================================
    # SUMMARY STATISTICS
    # ============================================================================

    ui.label('Summary Statistics').classes('text-h6 font-semibold mt-6')

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
            title_box.clear()
            rankings_box.clear()
            summary_box.clear()

            # Aggregate data by TEG and Player
            aggregated_data = aggregate_data(all_data_player_history, aggregation_level='TEG')

            if competition == 'net':
                # TEG Trophy (Net) - use dynamic measure based on TEG number
                with title_box:
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
                with title_box:
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
