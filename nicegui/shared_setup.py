"""Shared setup for NiceGUI demo pages.

This module contains:
- Shared CSS styling (forest green buttons, ranking table styling)
- Shared data loading (cached across all pages)

Import this module in demo_main.py before importing page modules.
"""

from nicegui import ui
from teg_analysis.core.data_loader import load_all_data

# ============================================================================
# CUSTOM STYLING FOR FOREST GREEN BUTTONS AND RANKING TABLES
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
# SHARED DATA LOADING (cached across all pages)
# ============================================================================

all_data_player_history = load_all_data()
all_data_leaderboard = load_all_data(exclude_teg_50=True)
all_data_sc_count = load_all_data(exclude_incomplete_tegs=False)
