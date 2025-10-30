"""
Unified Demo App Runner

This script starts the complete demo application with all demo pages and hub.

Entry Point:
    python run_all_demos.py

Routes:
    /                    - Demo Hub (navigation center)
    /demo/aggregation    - Aggregation Functions demo
    /demo/rankings       - Ranking Functions demo
    /demo/records        - Records Identification demo
    /demo/scoring        - Scoring Functions demo
    /demo/metadata       - Metadata & Reference demo

Architecture:
    - Hub page provides navigation and education
    - Each demo page is a separate @ui.page() route
    - Shared data loading via teg_analysis library
    - All pages run in the same NiceGUI app instance
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nicegui import ui
import pandas as pd

# ============================================================================
# IMPORT DEMO PAGES
# These imports register the routes with the NiceGUI app
# ============================================================================

print("Loading demo pages...")

# Import individual demo page functions and register them as routes
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import (
    filter_data_by_teg, aggregate_data, get_teg_leaderboard,
    get_round_leaderboard, get_teg_winners
)
from teg_analysis.analysis.rankings import add_ranks, get_best, get_worst, ordinal
from teg_analysis.analysis.records import (
    identify_aggregate_records_and_pbs, identify_all_time_worsts, identify_streak_records
)
from teg_analysis.analysis.scoring import (
    get_net_competition_measure, prepare_average_scores_by_par, format_vs_par
)
from teg_analysis.core.metadata import get_teg_metadata, load_course_info
from teg_analysis.core.data_loader import get_player_name


# ============================================================================
# DEFINE ROUTES
# ============================================================================

# Hub page route
@ui.page('/')
def hub():
    """Hub page - navigation center and learning resource."""
    # Inline the hub content here to make it self-contained
    ui.label('TEG Analysis Function Explorer').classes('text-h4 font-bold')
    ui.label('Interactive demos and learning tools for teg_analysis functions').classes('text-sm text-gray-600')
    ui.separator()

    with ui.expansion('How This Multi-Page App Works').classes('w-full'):
        ui.markdown('''
        ## NiceGUI Multi-Page Routing

        This demo hub uses NiceGUI's **@ui.page()** decorator to create a multi-page application.

        ### Key Concepts

        **1. Page Routes with @ui.page()**
        ```python
        @ui.page('/')
        def hub_page():
            ui.label('Hub Page')

        @ui.page('/demo/aggregation')
        def aggregation_demo():
            ui.label('Aggregation Demo')
        ```

        **2. Programmatic Navigation**
        ```python
        # Navigate to a route
        ui.button('Go to Demo', on_click=lambda: ui.navigate.to('/demo/aggregation'))

        # Navigation options
        ui.navigate.back()        # Back button
        ui.navigate.reload()      # Refresh page
        ui.navigate.to(url, new_tab=True)  # Open in new tab
        ```

        **3. App Runner**
        ```python
        # Run the app with ui.run()
        ui.run(title='My App', reload=True)
        ```

        ### Architecture

        - **Hub Page** (`/`) - Navigation center
        - **Demo Pages** (`/demo/aggregation`, `/demo/rankings`, etc.) - Individual demos
        - **Shared Navigation** - Back button on each demo
        - **Single Process** - All pages share the same data/session

        ### Advantages
        - Fast navigation (no page reloads in SPA mode)
        - Shared state across pages
        - Modular organization
        - Easy to add new pages

        For more info, see [NiceGUI Docs](https://nicegui.io/)
        ''').classes('text-sm')

    ui.separator()

    ui.label('Available Demo Pages').classes('text-h6 font-semibold mt-6 mb-4')

    demo_pages = [
        {
            'name': 'Aggregation Functions',
            'route': '/demo/aggregation',
            'functions': ['filter_data_by_teg', 'aggregate_data', 'get_teg_leaderboard', 'get_round_leaderboard', 'get_teg_winners'],
            'description': 'Learn how to filter tournament data by TEG, aggregate to different levels, and generate leaderboards.',
        },
        {
            'name': 'Ranking Functions',
            'route': '/demo/rankings',
            'functions': ['add_ranks', 'get_best', 'get_worst', 'ordinal'],
            'description': 'Explore ranking calculations, identifying top/bottom performers, and ordinal number formatting.',
        },
        {
            'name': 'Records Identification',
            'route': '/demo/records',
            'functions': ['identify_aggregate_records_and_pbs', 'identify_all_time_worsts', 'identify_streak_records'],
            'description': 'Discover how records, personal bests, and all-time worst performances are identified.',
        },
        {
            'name': 'Scoring Functions',
            'route': '/demo/scoring',
            'functions': ['get_net_competition_measure', 'prepare_average_scores_by_par', 'format_vs_par'],
            'description': 'Understand scoring calculations, vs-par formatting, and different competition rules across TEGs.',
        },
        {
            'name': 'Metadata & Reference',
            'route': '/demo/metadata',
            'functions': ['get_teg_metadata', 'load_course_info', 'get_player_name'],
            'description': 'Access metadata for TEGs, course information, and player reference data.',
        },
    ]

    with ui.column().classes('w-full'):
        with ui.row().classes('gap-4 w-full'):
            for i, page in enumerate(demo_pages[:3]):
                with ui.card().classes('flex-grow'):
                    with ui.column():
                        ui.label(page['name']).classes('text-h6 font-semibold')
                        ui.label(page['description']).classes('text-sm text-gray-600 mb-4')
                        ui.label('Functions:').classes('text-xs font-semibold text-gray-500 mt-2')
                        for func in page['functions']:
                            ui.label(f'• {func}').classes('text-xs ml-2 text-gray-700')
                        ui.label(f'Route: {page["route"]}').classes('text-xs font-mono text-gray-500 mt-3 pt-2 border-t')
                        ui.button(
                            'Launch Demo →',
                            on_click=lambda route=page['route']: ui.navigate.to(route)
                        ).classes('w-full mt-4').props('outline')

        with ui.row().classes('gap-4 w-full'):
            for page in demo_pages[3:]:
                with ui.card().classes('flex-grow'):
                    with ui.column():
                        ui.label(page['name']).classes('text-h6 font-semibold')
                        ui.label(page['description']).classes('text-sm text-gray-600 mb-4')
                        ui.label('Functions:').classes('text-xs font-semibold text-gray-500 mt-2')
                        for func in page['functions']:
                            ui.label(f'• {func}').classes('text-xs ml-2 text-gray-700')
                        ui.label(f'Route: {page["route"]}').classes('text-xs font-mono text-gray-500 mt-3 pt-2 border-t')
                        ui.button(
                            'Launch Demo →',
                            on_click=lambda route=page['route']: ui.navigate.to(route)
                        ).classes('w-full mt-4').props('outline')


# ============================================================================
# AGGREGATION DEMO PAGE
# ============================================================================

@ui.page('/demo/aggregation')
def demo_aggregation():
    """Aggregation functions demo page."""
    # Add back button
    with ui.row().classes('mb-4'):
        ui.button('← Back to Hub', on_click=lambda: ui.navigate.to('/')).props('outline')

    all_data = load_all_data()
    available_tegs = sorted(all_data['TEGNum'].unique())

    ui.label('Function Explorer: Aggregation Functions').classes('text-h5 font-bold')
    ui.label(
        'Explore how core aggregation functions work. Select a TEG, then see how '
        'each function filters, aggregates, and transforms the data into useful outputs.'
    ).classes('text-sm text-gray-600')

    ui.separator()

    ui.label('Controls').classes('text-h6 font-semibold mt-4')

    with ui.row().classes('gap-4 items-end'):
        teg_select = ui.select(
            label='Select TEG:',
            options=available_tegs,
            value=available_tegs[-1] if available_tegs else None
        ).classes('w-48')
        refresh_btn = ui.button('Refresh All', icon='refresh')

    ui.separator()

    # Functions sections
    for i, (title, func_num) in enumerate([
        ('Function 1: filter_data_by_teg()', 1),
        ('Function 2: aggregate_data()', 2),
        ('Function 3: get_teg_leaderboard()', 3),
        ('Function 4: get_round_leaderboard()', 4),
        ('Function 5: get_teg_winners()', 5),
    ]):
        ui.label(title).classes('text-h6 font-semibold mt-6')

        with ui.card().classes('bg-blue-50'):
            if func_num == 1:
                ui.markdown('**Signature:** `filter_data_by_teg(all_data, selected_tegnum) → pd.DataFrame`')
                ui.label('Purpose: Filter raw tournament data to a specific TEG').classes('text-sm')
            elif func_num == 2:
                ui.markdown('**Signature:** `aggregate_data(data, aggregation_level, measures=None, additional_group_fields=None) → pd.DataFrame`')
                ui.label('Purpose: Aggregate data by grouping at different levels').classes('text-sm')
            elif func_num == 3:
                ui.markdown('**Signature:** `get_teg_leaderboard(df, measure, teg_num=None) → pd.DataFrame`')
                ui.label('Purpose: Transform round-level aggregated data into a leaderboard').classes('text-sm')
            elif func_num == 4:
                ui.markdown('**Signature:** `get_round_leaderboard(df, measure, teg_num=None, round_num=None) → pd.DataFrame`')
                ui.label('Purpose: Create a single-round leaderboard').classes('text-sm')
            elif func_num == 5:
                ui.markdown('**Signature:** `get_teg_winners(df) → pd.DataFrame`')
                ui.label('Purpose: Generate winners summary across all TEGs').classes('text-sm')

        ui.label('Raw Data Output').classes('text-sm font-semibold mt-4')
        output_box = ui.card()

        def refresh():
            try:
                teg_num = int(teg_select.value)
                filtered_data = filter_data_by_teg(all_data, teg_num)
                aggregated_data = aggregate_data(filtered_data, aggregation_level='Round')
                leaderboard = get_teg_leaderboard(aggregated_data, measure='Stableford')
                round_leaderboard = get_round_leaderboard(all_data, measure='Stableford', teg_num=teg_num, round_num=1)
                winners = get_teg_winners(all_data)

                output_box.clear()
                with output_box:
                    if func_num == 1:
                        ui.label(f'Call: filter_data_by_teg(all_data, teg_num={teg_num})').classes('text-xs text-gray-600 font-mono')
                        ui.label(f'Shape: {filtered_data.shape[0]} rows × {filtered_data.shape[1]} columns')
                        ui.code(filtered_data.head(5).to_string(), language='text')
                    elif func_num == 2:
                        ui.label(f"Call: aggregate_data(filtered_data, aggregation_level='Round')").classes('text-xs text-gray-600 font-mono')
                        ui.label(f'Shape: {aggregated_data.shape[0]} rows × {aggregated_data.shape[1]} columns')
                        ui.code(aggregated_data.head(5).to_string(), language='text')
                    elif func_num == 3:
                        ui.label(f"Call: get_teg_leaderboard(aggregated_data, measure='Stableford')").classes('text-xs text-gray-600 font-mono')
                        if not leaderboard.empty:
                            ui.label(f'Shape: {leaderboard.shape[0]} rows × {leaderboard.shape[1]} columns')
                            ui.code(leaderboard.to_string(), language='text')
                    elif func_num == 4:
                        ui.label(f"Call: get_round_leaderboard(all_data, measure='Stableford', teg_num={teg_num}, round_num=1)").classes('text-xs text-gray-600 font-mono')
                        if not round_leaderboard.empty:
                            ui.label(f'Shape: {round_leaderboard.shape[0]} rows × {round_leaderboard.shape[1]} columns')
                            ui.code(round_leaderboard.to_string(), language='text')
                    elif func_num == 5:
                        ui.label('Call: get_teg_winners(all_data)').classes('text-xs text-gray-600 font-mono')
                        if not winners.empty:
                            ui.label(f'Shape: {winners.shape[0]} rows × {winners.shape[1]} columns')
                            ui.code(winners.head(5).to_string(), language='text')
            except Exception as e:
                output_box.clear()
                with output_box:
                    ui.label(f'Error: {str(e)}').classes('text-red-600')

        refresh_btn.on('click', refresh)
        teg_select.on('update:model-value', lambda _: refresh())

    refresh()


# ============================================================================
# RANKINGS DEMO PAGE
# ============================================================================

@ui.page('/demo/rankings')
def demo_rankings():
    """Ranking functions demo page."""
    with ui.row().classes('mb-4'):
        ui.button('← Back to Hub', on_click=lambda: ui.navigate.to('/')).props('outline')

    all_data = load_all_data()
    available_tegs = sorted(all_data['TEGNum'].unique())

    ui.label('Function Explorer: Ranking Functions').classes('text-h5 font-bold')
    ui.label('Explore ranking functions and how to identify best/worst performers.').classes('text-sm text-gray-600')

    ui.separator()

    with ui.row().classes('gap-4 items-end'):
        teg_select = ui.select(
            label='Select TEG:',
            options=available_tegs,
            value=available_tegs[-1] if available_tegs else None
        ).classes('w-48')
        refresh_btn = ui.button('Refresh All', icon='refresh')

    ui.separator()

    ui.label('Function 1: add_ranks()').classes('text-h6 font-semibold mt-6')
    with ui.card().classes('bg-blue-50'):
        ui.markdown('**Signature:** `add_ranks(df, fields_to_rank=None, rank_ascending=None) → pd.DataFrame`')
        ui.label('Purpose: Add ranking columns for different measures').classes('text-sm')

    add_ranks_box = ui.card()

    ui.label('Function 2: get_best()').classes('text-h6 font-semibold mt-6')
    with ui.card().classes('bg-blue-50'):
        ui.markdown('**Signature:** `get_best(df, measure_to_use, player_level=False, top_n=1) → pd.DataFrame`')
        ui.label('Purpose: Get best performances by measure').classes('text-sm')

    get_best_box = ui.card()

    ui.label('Function 3: ordinal()').classes('text-h6 font-semibold mt-6')
    with ui.card().classes('bg-blue-50'):
        ui.markdown('**Signature:** `ordinal(n) → str`')
        ui.label('Purpose: Convert numbers to ordinal format').classes('text-sm')

    ordinal_box = ui.card()

    def refresh():
        try:
            teg_num = int(teg_select.value)
            filtered_data = filter_data_by_teg(all_data, teg_num)
            aggregated_data = aggregate_data(filtered_data, aggregation_level='Round')
            ranked_data = add_ranks(aggregated_data)

            add_ranks_box.clear()
            with add_ranks_box:
                rank_cols = [col for col in ranked_data.columns if 'Rank' in col]
                display_data = ranked_data[['Player'] + rank_cols].drop_duplicates()
                ui.code(display_data.head(5).to_string(), language='text')

            best = get_best(ranked_data, 'Stableford', False, 1)
            get_best_box.clear()
            with get_best_box:
                if not best.empty:
                    ui.code(best[['Player', 'Stableford']].to_string(), language='text')

            ordinal_box.clear()
            with ordinal_box:
                examples = '\n'.join([f'ordinal({i}) = "{ordinal(i)}"' for i in range(1, 6)])
                ui.code(examples, language='text')
        except Exception as e:
            ui.notify(f'Error: {str(e)}', type='negative')

    refresh_btn.on('click', refresh)
    teg_select.on('update:model-value', lambda _: refresh())
    refresh()


# ============================================================================
# RECORDS DEMO PAGE
# ============================================================================

@ui.page('/demo/records')
def demo_records():
    """Records identification demo page."""
    with ui.row().classes('mb-4'):
        ui.button('← Back to Hub', on_click=lambda: ui.navigate.to('/')).props('outline')

    ui.label('Function Explorer: Records Identification Functions').classes('text-h5 font-bold')
    ui.label('Explore how records and all-time worst performances are identified.').classes('text-sm text-gray-600')

    ui.separator()

    all_data = load_all_data()
    available_tegs = sorted(all_data['TEGNum'].unique())

    with ui.row().classes('gap-4 items-end'):
        teg_select = ui.select(
            label='Select TEG:',
            options=[f'TEG {t}' for t in available_tegs],
            value=f'TEG {available_tegs[-1]}' if available_tegs else None
        ).classes('w-48')
        refresh_btn = ui.button('Refresh All', icon='refresh')

    ui.separator()

    ui.label('Function 1: identify_aggregate_records_and_pbs()').classes('text-h6 font-semibold mt-6')
    with ui.card().classes('bg-blue-50'):
        ui.markdown('**Signature:** `identify_aggregate_records_and_pbs(df, selected_teg, selected_round=None) → dict`')
        ui.label('Purpose: Find records and personal bests').classes('text-sm')

    records_box = ui.card()

    ui.label('Function 2: identify_all_time_worsts()').classes('text-h6 font-semibold mt-6')
    with ui.card().classes('bg-blue-50'):
        ui.markdown('**Signature:** `identify_all_time_worsts(df, selected_teg, selected_round=None) → list`')
        ui.label('Purpose: Find all-time worst performances').classes('text-sm')

    worsts_box = ui.card()

    def refresh():
        try:
            selected_teg_str = teg_select.value
            teg_num = int(selected_teg_str.split()[-1])

            filtered_data = filter_data_by_teg(all_data, teg_num)
            aggregated_data = aggregate_data(filtered_data, aggregation_level='Round')
            ranked_data = add_ranks(aggregated_data)

            records_dict = identify_aggregate_records_and_pbs(ranked_data, selected_teg_str)
            worsts_list = identify_all_time_worsts(ranked_data, selected_teg_str)

            records_box.clear()
            with records_box:
                import json
                output = {
                    'records': len(records_dict.get('records', [])),
                    'personal_bests': len(records_dict.get('personal_bests', [])),
                    'personal_worsts': len(records_dict.get('personal_worsts', []))
                }
                ui.code(json.dumps(output, indent=2), language='json')

            worsts_box.clear()
            with worsts_box:
                import json
                ui.code(json.dumps(worsts_list[:3] if worsts_list else [], indent=2, default=str), language='json')
        except Exception as e:
            ui.notify(f'Error: {str(e)}', type='negative')

    refresh_btn.on('click', refresh)
    teg_select.on('update:model-value', lambda _: refresh())
    refresh()


# ============================================================================
# SCORING DEMO PAGE
# ============================================================================

@ui.page('/demo/scoring')
def demo_scoring():
    """Scoring functions demo page."""
    with ui.row().classes('mb-4'):
        ui.button('← Back to Hub', on_click=lambda: ui.navigate.to('/')).props('outline')

    all_data = load_all_data()
    available_tegs = sorted(all_data['TEGNum'].unique())

    ui.label('Function Explorer: Scoring Functions').classes('text-h5 font-bold')
    ui.label('Explore scoring utilities and calculations.').classes('text-sm text-gray-600')

    ui.separator()

    with ui.row().classes('gap-4 items-end'):
        teg_select = ui.select(
            label='Select TEG:',
            options=available_tegs,
            value=available_tegs[-1] if available_tegs else None
        ).classes('w-48')
        refresh_btn = ui.button('Refresh All', icon='refresh')

    ui.separator()

    ui.label('Function 1: get_net_competition_measure()').classes('text-h6 font-semibold mt-6')
    with ui.card().classes('bg-blue-50'):
        ui.markdown('**Signature:** `get_net_competition_measure(teg_num) → str`')
        ui.label('Purpose: Determine net competition measure for a TEG').classes('text-sm')

    net_measure_box = ui.card()

    ui.label('Function 2: prepare_average_scores_by_par()').classes('text-h6 font-semibold mt-6')
    with ui.card().classes('bg-blue-50'):
        ui.markdown('**Signature:** `prepare_average_scores_by_par(all_data) → pd.DataFrame`')
        ui.label('Purpose: Calculate average scores by par value').classes('text-sm')

    avg_scores_box = ui.card()

    ui.label('Function 3: format_vs_par()').classes('text-h6 font-semibold mt-6')
    with ui.card().classes('bg-blue-50'):
        ui.markdown('**Signature:** `format_vs_par(value) → str`')
        ui.label('Purpose: Format values as vs-par scores').classes('text-sm')

    format_box = ui.card()

    def refresh():
        try:
            teg_num = int(teg_select.value)

            net_measure = get_net_competition_measure(teg_num)
            net_measure_box.clear()
            with net_measure_box:
                ui.label(f'Result: "{net_measure}"').classes('font-mono text-sm')

            avg_scores = prepare_average_scores_by_par(all_data)
            avg_scores_box.clear()
            with avg_scores_box:
                ui.code(avg_scores.head(5).to_string(), language='text')

            format_box.clear()
            with format_box:
                examples = '\n'.join([f'format_vs_par({v}) = "{format_vs_par(v)}"' for v in [-5, -2, 0, 2, 5]])
                ui.code(examples, language='text')
        except Exception as e:
            ui.notify(f'Error: {str(e)}', type='negative')

    refresh_btn.on('click', refresh)
    teg_select.on('update:model-value', lambda _: refresh())
    refresh()


# ============================================================================
# METADATA DEMO PAGE
# ============================================================================

@ui.page('/demo/metadata')
def demo_metadata():
    """Metadata functions demo page."""
    with ui.row().classes('mb-4'):
        ui.button('← Back to Hub', on_click=lambda: ui.navigate.to('/')).props('outline')

    all_data = load_all_data()
    available_tegs = sorted(all_data['TEGNum'].unique())
    available_rounds = sorted(all_data['Round'].unique())

    ui.label('Function Explorer: Metadata & Reference Functions').classes('text-h5 font-bold')
    ui.label('Explore metadata and reference data functions.').classes('text-sm text-gray-600')

    ui.separator()

    with ui.row().classes('gap-4 items-end'):
        teg_select = ui.select(
            label='Select TEG:',
            options=available_tegs,
            value=available_tegs[-1] if available_tegs else None
        ).classes('w-48')
        round_select = ui.select(
            label='Select Round:',
            options=available_rounds,
            value=1
        ).classes('w-48')
        refresh_btn = ui.button('Refresh All', icon='refresh')

    ui.separator()

    ui.label('Function 1: get_teg_metadata()').classes('text-h6 font-semibold mt-6')
    with ui.card().classes('bg-blue-50'):
        ui.markdown('**Signature:** `get_teg_metadata(teg_num, round_num=None) → dict`')
        ui.label('Purpose: Get metadata for a TEG or round').classes('text-sm')

    metadata_box = ui.card()

    ui.label('Function 2: load_course_info()').classes('text-h6 font-semibold mt-6')
    with ui.card().classes('bg-blue-50'):
        ui.markdown('**Signature:** `load_course_info() → pd.DataFrame`')
        ui.label('Purpose: Load unique course/area combinations').classes('text-sm')

    course_box = ui.card()

    ui.label('Function 3: get_player_name()').classes('text-h6 font-semibold mt-6')
    with ui.card().classes('bg-blue-50'):
        ui.markdown('**Signature:** `get_player_name(initials) → str`')
        ui.label('Purpose: Convert initials to full names').classes('text-sm')

    player_box = ui.card()

    def refresh():
        try:
            teg_num = int(teg_select.value)
            round_num = int(round_select.value)

            teg_meta = get_teg_metadata(teg_num)
            metadata_box.clear()
            with metadata_box:
                import json
                ui.code(json.dumps(teg_meta, indent=2, default=str)[:200] + '...', language='json')

            course_info = load_course_info()
            course_box.clear()
            with course_box:
                ui.code(course_info.head(5).to_string(), language='text')

            unique_players = sorted(all_data['Pl'].unique())
            player_box.clear()
            with player_box:
                examples = '\n'.join([f'get_player_name("{p}") = "{get_player_name(p)}"' for p in unique_players[:5]])
                ui.code(examples, language='text')
        except Exception as e:
            ui.notify(f'Error: {str(e)}', type='negative')

    refresh_btn.on('click', refresh)
    teg_select.on('update:model-value', lambda _: refresh())
    round_select.on('update:model-value', lambda _: refresh())
    refresh()


# ============================================================================
# APP RUNNER
# ============================================================================

if __name__ in {"__main__", "__mp_main__"}:
    print("Starting Demo App with NiceGUI")
    print("Navigate to http://localhost:8080 in your browser")
    print("Press Ctrl+C to stop")
    ui.run(title='TEG Analysis Demo Explorer', reload=True, port=8080)
