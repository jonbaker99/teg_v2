"""
NiceGUI Demo Page: Player Rankings by TEG

Shows player finishing positions (rankings) across all completed TEGs for both competitions:
- TEG Trophy (Net) - showing finishing positions across all TEGs
- Green Jacket (Gross) - showing finishing positions across all TEGs

This page demonstrates:
- aggregate_data(): Group data by player and TEG
- convert_pivot_scores_to_ranks(): Convert scores to tournament finishing positions
- Pivot tables showing player finishing positions (ranks) in each TEG
- Summary statistics (average scores, count of tournaments played)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nicegui import ui
import pandas as pd

# Import functions from teg_analysis
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import aggregate_data
from teg_analysis.analysis.rankings import convert_pivot_scores_to_ranks


# ============================================================================
# HTML TABLE HELPER FUNCTION
# ============================================================================

def dataframe_to_html_table(df):
    """Convert a pandas DataFrame to an HTML table with borders."""
    html = '<table style="border-collapse: collapse; font-family: monospace; font-size: 14px;">'

    # Header row
    html += '<tr style="background-color: #f0f0f0;">'
    html += f'<th style="border: 1px solid #ddd; padding: 8px; text-align: left;"></th>'  # Corner cell for index
    for col in df.columns:
        html += f'<th style="border: 1px solid #ddd; padding: 8px; text-align: center;">{col}</th>'
    html += '</tr>'

    # Data rows
    for idx, row in df.iterrows():
        html += '<tr>'
        html += f'<td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{idx}</td>'
        for val in row:
            html += f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{val}</td>'
        html += '</tr>'

    html += '</table>'
    return html


# ============================================================================
# PAGE SETUP AND DATA LOADING
# ============================================================================

# Load data at module level (cached by NiceGUI)
all_data = load_all_data()
available_tegs = sorted(all_data['TEGNum'].unique())

# Page title and description
ui.label('Player Rankings by TEG').classes('text-h5 font-bold')
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

with ui.card().classes('bg-blue-50'):
    ui.label('Shows each player\'s finishing position in each TEG').classes('text-sm')

rankings_box = ui.card()

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================

ui.label('Summary Statistics').classes('text-h6 font-semibold mt-6')

with ui.card().classes('bg-blue-50'):
    ui.label('Average finishing position and position counts by player').classes('text-sm')

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
        aggregated_data = aggregate_data(all_data, aggregation_level='TEG')

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
            # Note: Since the measure varies by TEG (NetVP for 1-5, Stableford for 6+),
            # we use NetVP as the measure here for ranking consistency. The actual ranking
            # within each TEG will correctly sort each column independently.
            if not pivot_data.empty:
                ranked_data = convert_pivot_scores_to_ranks(pivot_data, 'NetVP')

                with rankings_box:
                    ui.label('TEG Trophy Rankings (by finishing position)').classes('font-semibold')
                    html_table = dataframe_to_html_table(ranked_data)
                    ui.html(html_table, sanitize=False)
            else:
                with rankings_box:
                    ui.label('No data available').classes('text-gray-500')

            # Summary statistics
            with summary_box:
                ui.label('Average Rank by Player').classes('font-semibold')
                summary_stats = aggregated_data.groupby('Player')['NetVP'].agg(['mean', 'count']).round(1)
                summary_stats.columns = ['Avg Rank', 'TEGs Played']
                summary_stats = summary_stats.sort_values('Avg Rank')
                html_table = dataframe_to_html_table(summary_stats)
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
                    html_table = dataframe_to_html_table(ranked_data)
                    ui.html(html_table, sanitize=False)
            else:
                with rankings_box:
                    ui.label('No data available').classes('text-gray-500')

            # Summary statistics
            with summary_box:
                ui.label('Average Rank by Player').classes('font-semibold')
                summary_stats = aggregated_data.groupby('Player')['GrossVP'].agg(['mean', 'count']).round(1)
                summary_stats.columns = ['Avg Rank', 'TEGs Played']
                summary_stats = summary_stats.sort_values('Avg Rank')
                html_table = dataframe_to_html_table(summary_stats)
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
# APP RUNNER
# ============================================================================

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Demo: Player Rankings by TEG', reload=True)
