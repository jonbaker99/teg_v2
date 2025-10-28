"""NiceGUI helper components and utilities.

This module provides reusable NiceGUI-specific components that can be used
across multiple pages in NiceGUI applications.
"""

from nicegui import ui


def create_nav_header(current_page: str):
    """Create navigation header with buttons to switch between pages.

    This is a NiceGUI-specific component that creates a persistent header
    with navigation buttons. It applies forest green styling to the current page.

    Args:
        current_page: The name of the current page ('player_rankings', 'sc_count', 'leaderboard')

    Example:
        @ui.page('/')
        def some_page():
            create_nav_header('player_rankings')
            # ... rest of page content
    """
    with ui.header().classes('header_bg'):
        with ui.row().classes('w-full items-center gap-2'):
            ui.label('TEG Analysis Demos').classes('text-h6 font-bold')
            ui.space()

            # Navigation buttons - use forest green for selected, transparent for unselected
            rankings_btn = ui.button('Player Rankings', icon='bar_chart').props('no-caps unelevated')
            rankings_btn.on_click(lambda: ui.navigate.to('/'))
            if current_page == 'player_rankings':
                rankings_btn.style('background-color: #228B22 !important; color: white !important;')
            else:
                rankings_btn.style('background-color: transparent !important; color: inherit !important;')

            sc_btn = ui.button('Score Distribution', icon='assessment').props('no-caps unelevated')
            sc_btn.on_click(lambda: ui.navigate.to('/sc-count'))
            if current_page == 'sc_count':
                sc_btn.style('background-color: #228B22 !important; color: white !important;')
            else:
                sc_btn.style('background-color: transparent !important; color: inherit !important;')

            leaderboard_btn = ui.button('Leaderboard', icon='emoji_events').props('no-caps unelevated')
            leaderboard_btn.on_click(lambda: ui.navigate.to('/leaderboard'))
            if current_page == 'leaderboard':
                leaderboard_btn.style('background-color: #228B22 !important; color: white !important;')
            else:
                leaderboard_btn.style('background-color: transparent !important; color: inherit !important;')
