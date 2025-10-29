"""Shared setup for NiceGUI prototype pages.

This module contains:
- Minimal CSS styling (basic table styling)
- Shared data loading (cached across all prototype pages)

Import this module in prototype_main.py before importing page modules.
All prototypes use simple HTML tables for output - no fancy styling yet.
"""

from nicegui import ui
from teg_analysis.core.data_loader import load_all_data

# ============================================================================
# MINIMAL CSS STYLING (basic table styling for readable output)
# ============================================================================

ui.add_head_html('''
<style>
    /* Basic table styling for readable output */
    table {
        border-collapse: collapse;
        width: 100%;
        font-family: monospace;
    }
    table td, table th {
        border: 1px solid #ccc;
        padding: 8px;
        text-align: left;
    }
    table th {
        background-color: #f0f0f0;
        font-weight: bold;
    }
</style>
''', shared=True)

# ============================================================================
# SHARED DATA LOADING (cached across all prototype pages)
# ============================================================================

# History section data
all_data_history = load_all_data()

# Records section data (excludes TEG 50 - partial data)
all_data_records = load_all_data(exclude_teg_50=True)

# Scoring section data (includes incomplete TEGs)
all_data_scoring = load_all_data(exclude_incomplete_tegs=False)

# Latest TEG section data
all_data_latest = load_all_data(exclude_teg_50=True)

# Scorecards section data
all_data_scorecards = load_all_data()
