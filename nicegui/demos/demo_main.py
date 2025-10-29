"""Demo application runner for NiceGUI multi-page TEG analysis app.

This runner file imports and initializes all demo pages with their shared setup.
The application includes:
- Player Rankings by TEG (route: '/')
- Scoring Distribution (route: '/sc-count')
- Current TEG Leaderboard (route: '/leaderboard')

Run this file with: python demo_main.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # For teg_analysis imports
sys.path.insert(0, str(Path(__file__).parent.parent))  # For nicegui root imports

from nicegui import ui

# Import shared setup (loads CSS styling and initializes cached data)
from demos import shared_setup

# Import all demo pages (registers @ui.page() decorators)
from demos import demo_pages_player_history
from demos import demo_pages_sc_count
from demos import demo_pages_leaderboard

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='TEG Analysis Demos', reload=True)
