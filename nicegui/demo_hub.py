"""
NiceGUI Demo Hub - Navigation Center

This page serves as both:
1. A functional navigation hub for all demo pages
2. An educational resource showing how NiceGUI's multi-page routing works

The hub demonstrates:
- @ui.page() decorator for defining routes
- ui.navigate.to() for programmatic navigation
- Multi-page SPA architecture
- How to organize demo content in a modular way
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nicegui import ui


# ============================================================================
# PAGE TITLE AND WELCOME
# ============================================================================

ui.label('TEG Analysis Function Explorer').classes('text-h4 font-bold')
ui.label('Interactive demos and learning tools for teg_analysis functions').classes('text-sm text-gray-600')

ui.separator()

# ============================================================================
# HOW IT WORKS SECTION (Educational)
# ============================================================================

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

# ============================================================================
# DEMO PAGES GRID
# ============================================================================

ui.label('Available Demo Pages').classes('text-h6 font-semibold mt-6 mb-4')

demo_pages = [
    {
        'name': 'Aggregation Functions',
        'route': '/demo/aggregation',
        'functions': ['filter_data_by_teg', 'aggregate_data', 'get_teg_leaderboard', 'get_round_leaderboard', 'get_teg_winners'],
        'description': 'Learn how to filter tournament data by TEG, aggregate to different levels, and generate leaderboards.',
        'color': 'blue',
    },
    {
        'name': 'Ranking Functions',
        'route': '/demo/rankings',
        'functions': ['add_ranks', 'get_best', 'get_worst', 'ordinal'],
        'description': 'Explore ranking calculations, identifying top/bottom performers, and ordinal number formatting.',
        'color': 'purple',
    },
    {
        'name': 'Records Identification',
        'route': '/demo/records',
        'functions': ['identify_aggregate_records_and_pbs', 'identify_all_time_worsts', 'identify_streak_records'],
        'description': 'Discover how records, personal bests, and all-time worst performances are identified.',
        'color': 'amber',
    },
    {
        'name': 'Scoring Functions',
        'route': '/demo/scoring',
        'functions': ['get_net_competition_measure', 'prepare_average_scores_by_par', 'format_vs_par'],
        'description': 'Understand scoring calculations, vs-par formatting, and different competition rules across TEGs.',
        'color': 'green',
    },
    {
        'name': 'Metadata & Reference',
        'route': '/demo/metadata',
        'functions': ['get_teg_metadata', 'load_course_info', 'get_player_name'],
        'description': 'Access metadata for TEGs, course information, and player reference data.',
        'color': 'teal',
    },
]

# Create demo cards in a responsive grid
with ui.column().classes('w-full'):
    # First row - 3 cards
    with ui.row().classes('gap-4 w-full'):
        for i, page in enumerate(demo_pages[:3]):
            with ui.card().classes('flex-grow'):
                with ui.column():
                    ui.label(page['name']).classes('text-h6 font-semibold')
                    ui.label(page['description']).classes('text-sm text-gray-600 mb-4')

                    # Function list
                    ui.label('Functions:').classes('text-xs font-semibold text-gray-500 mt-2')
                    for func in page['functions']:
                        ui.label(f'• {func}').classes('text-xs ml-2 text-gray-700')

                    # Route info
                    ui.label(f'Route: {page["route"]}').classes('text-xs font-mono text-gray-500 mt-3 pt-2 border-t')

                    # Launch button
                    ui.button(
                        'Launch Demo →',
                        on_click=lambda route=page['route']: ui.navigate.to(route)
                    ).classes('w-full mt-4').props('outline')

    # Second row - 2 cards (last page alone)
    with ui.row().classes('gap-4 w-full'):
        for page in demo_pages[3:]:
            with ui.card().classes('flex-grow'):
                with ui.column():
                    ui.label(page['name']).classes('text-h6 font-semibold')
                    ui.label(page['description']).classes('text-sm text-gray-600 mb-4')

                    # Function list
                    ui.label('Functions:').classes('text-xs font-semibold text-gray-500 mt-2')
                    for func in page['functions']:
                        ui.label(f'• {func}').classes('text-xs ml-2 text-gray-700')

                    # Route info
                    ui.label(f'Route: {page["route"]}').classes('text-xs font-mono text-gray-500 mt-3 pt-2 border-t')

                    # Launch button
                    ui.button(
                        'Launch Demo →',
                        on_click=lambda route=page['route']: ui.navigate.to(route)
                    ).classes('w-full mt-4').props('outline')

ui.separator()

# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================

with ui.expansion('Usage Instructions').classes('w-full'):
    ui.markdown('''
    ## How to Use the Demo Pages

    1. **Click "Launch Demo"** on any card above to navigate to that demo
    2. **Select a TEG** from the dropdown (where applicable)
    3. **Click "Refresh"** to see function outputs for that TEG
    4. **View raw data** - Shows the exact output from each function
    5. **See function calls** - Shows how the function was called with what parameters
    6. **Learn the API** - Use the signature and example calls as reference

    ## Tips

    - Functions are called in sequence, each using the output of the previous one
    - Raw data shows shape (rows × columns) and column names
    - Toggle "How This Works" section to learn about NiceGUI routing
    - Each demo is standalone and can be run independently

    ## Technical Details

    - **Entry point**: `run_all_demos.py` - Starts the unified app
    - **Hub page**: `demo_hub.py` - Navigation and learning
    - **Demo pages**: `demo_pages_*.py` - Individual function demos
    - **Data**: Uses `teg_analysis` library functions
    - **Framework**: NiceGUI (Python web UI)
    ''').classes('text-sm')

ui.separator()

# ============================================================================
# FOOTER
# ============================================================================

with ui.footer().classes('bg-gray-100 p-4'):
    with ui.row().classes('justify-between items-center w-full'):
        ui.label('TEG Analysis Function Explorer v1.0').classes('text-sm text-gray-600')
        ui.label('Built with NiceGUI').classes('text-xs text-gray-500')


# ============================================================================
# APP RUNNER (only runs if this file is executed directly)
# ============================================================================

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Demo Hub', reload=True)
