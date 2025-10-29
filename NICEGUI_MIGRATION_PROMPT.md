# NiceGUI Migration Prompt: Phase 1 - History Section

## Project Context

**TEG Analysis Application:** A Python application for analyzing TEG (annual golf tournament) data. Currently uses Streamlit for the web interface, now migrating to NiceGUI for improved frontend flexibility.

**Migration Goal:** Systematically recreate all Streamlit functionality in NiceGUI prototypes, starting with prototype pages that demonstrate data flow and page structure before final polish.

**Development Philosophy:** Start simple with minimalist prototypes showing correct data in correct places using simple HTML tables. No styling, animations, or advanced UI features until data accuracy is verified.

---

## Migration Overview: 5 Phases

The Streamlit application (`streamlit/page_config.py`) defines 27 pages across 5 sections (Data management excluded):

| Phase | Section | Pages | Status |
|-------|---------|-------|--------|
| 1 | **History** | 5 | ← START HERE |
| 2 | Records | 3 | Not started |
| 3 | Scoring | 11 | Not started |
| 4 | Latest TEG | 4 | Not started |
| 5 | Scorecards | 4 | Not started |

**Phase 1 History Pages:**
1. `101TEG History.py` → TEG History (list of all TEGs with winners)
2. `101TEG Honours Board.py` → Honours Board (tournament wins/placements by player)
3. `102TEG Results.py` → Full Results (detailed results for each TEG)
4. `player_history.py` → Player Rankings (ranking table across all TEGs)
5. `teg_reports.py` → TEG Reports (detailed report for selected TEG)

---

## File Structure Plan

### Current State
```
nicegui/
├── demo_pages_*.py        # Existing demos (will relocate)
├── demo_main.py           # Existing demo runner
├── shared_setup.py        # Existing shared setup
└── ui_helpers.py          # Existing navigation helpers
```

### Target State (After Phase 1)
```
nicegui/
├── demos/                              # Relocated demo pages
│   ├── demo_main.py
│   ├── demo_pages_player_history.py
│   ├── demo_pages_sc_count.py
│   └── demo_pages_leaderboard.py
├── prototypes/                         # New prototype pages
│   ├── prototype_main.py              # Main runner with section nav
│   ├── shared_setup_prototypes.py     # CSS + data loading
│   ├── history/                       # Phase 1 pages
│   │   ├── teg_history.py            # 101TEG History
│   │   ├── honours_board.py          # 101TEG Honours Board
│   │   ├── full_results.py           # 102TEG Results
│   │   ├── player_rankings.py        # player_history
│   │   └── teg_reports.py            # teg_reports
│   ├── records/                       # Phase 2 (future)
│   │   └── [3 records pages]
│   ├── scoring/                       # Phase 3 (future)
│   │   └── [11 scoring pages]
│   ├── latest/                        # Phase 4 (future)
│   │   └── [4 latest TEG pages]
│   └── scorecards/                    # Phase 5 (future)
│       └── [4 scorecard pages]
└── helpers/                            # NiceGUI-specific helpers
    └── ui_helpers.py                  # Navigation, UI components
```

---

## Development Principles & Rules

### 1. Minimalist Approach
- **Simple HTML tables** for all output (no fancy DataFrames, plots, or charts yet)
- **Basic layout** - labels, separators, one column
- **No styling bells and whistles** - proof of concept first
- Goal: Verify correct data in correct places

### 2. Data Completeness
- Compare Streamlit page output with NiceGUI prototype
- **ALL data points** shown in Streamlit must appear in prototype
- Use Streamlit page as reference for what to display
- Create data verification checklist for each page

### 3. Function Extraction Rules

When encountering code in Streamlit pages, decide where it belongs:

| Code Type | Location | Examples |
|-----------|----------|----------|
| General reusable logic (not UI-specific) | `teg_analysis/` modules | Data transformations, calculations, aggregations |
| Reusable but NiceGUI-specific | `nicegui/helpers/` | Formatting, HTML generation, UI components |
| Page-specific with no reuse | Keep on page | One-off display logic, page-specific calculations |

**Examples:**
- ❌ **DON'T:** Create `create_history_table()` on the page if it could be reused
- ✅ **DO:** Move `prepare_complete_history_table_fast()` to analysis module if general
- ✅ **DO:** Create `format_history_table_html()` in helpers if NiceGUI-specific
- ✅ **DO:** Keep page-specific sorting/filtering on the page itself

---

## Code Templates

### Template 1: Prototype Page Structure

```python
"""[Section] - [Page Title]

Brief description of what data is shown and which Streamlit page this mimics.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # teg_analysis
sys.path.insert(0, str(Path(__file__).parent.parent))  # nicegui

from nicegui import ui
import pandas as pd

# Import analysis functions from teg_analysis
from teg_analysis.analysis.aggregation import aggregate_data  # Example
from teg_analysis.core.data_loader import load_all_data       # Example

# Import helpers
from helpers.ui_helpers import create_nav_header

# Import shared setup (CSS, cached data)
from prototypes.shared_setup_prototypes import all_data_history


@ui.page('/history/page-name')  # Route relative to section
def page_function_name():
    """Page description matching Streamlit page."""
    create_nav_header('history')  # Section identifier

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Page Title').classes('text-h5 font-bold mt-6')
    ui.label('Brief description').classes('text-sm text-gray-600')
    ui.separator()

    # ===== CONTROLS (if needed) =====
    # Dropdowns, filters, buttons, etc.

    # ===== DATA DISPLAY =====
    output_box = ui.card()

    # ===== REFRESH FUNCTION =====
    def refresh():
        """Load data and update displays."""
        try:
            output_box.clear()

            # Load/process data
            # Create HTML table
            # Display with ui.html()

        except Exception as e:
            ui.notify(f'Error: {str(e)}', type='negative')
            print(f'Error: {e}')

    # ===== INITIAL LOAD =====
    refresh()
```

### Template 2: shared_setup_prototypes.py

```python
"""Shared setup for NiceGUI prototype pages.

Contains:
- CSS styling
- Cached data loading for all prototypes
"""

from nicegui import ui
from teg_analysis.core.data_loader import load_all_data

# ===== CSS STYLING =====
# Minimal styling - plain tables for now
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
    }
</style>
''', shared=True)

# ===== CACHED DATA LOADING =====
# Load data once at module level, cached by NiceGUI
all_data_history = load_all_data()
all_data_records = load_all_data(exclude_teg_50=True)
all_data_scoring = load_all_data(exclude_incomplete_tegs=False)
# Add more as needed for each section
```

### Template 3: prototype_main.py

```python
"""NiceGUI Prototype Application Runner

Organizes prototype pages by section:
- History (Phase 1)
- Records (Phase 2)
- Scoring (Phase 3)
- Latest TEG (Phase 4)
- Scorecards (Phase 5)

Run with: python prototype_main.py (from project root)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nicegui import ui

# Import shared setup (CSS, data)
from nicegui.prototypes.shared_setup_prototypes import *

# ===== PHASE 1: HISTORY =====
from nicegui.prototypes.history import teg_history
from nicegui.prototypes.history import honours_board
from nicegui.prototypes.history import full_results
from nicegui.prototypes.history import player_rankings
from nicegui.prototypes.history import teg_reports

# ===== FUTURE PHASES =====
# from nicegui.prototypes.records import *
# from nicegui.prototypes.scoring import *
# etc.

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='TEG Analysis Prototypes', reload=True)
```

---

## Function Extraction Decision Tree

When you encounter code in a Streamlit page:

```
Is the code reusable for multiple pages/sections?
├─ YES → Is it UI/frontend-specific?
│   ├─ YES → Put in nicegui/helpers/
│   │         Example: format_ranking_table_html()
│   └─ NO → Put in teg_analysis/
│            Example: aggregate_player_rankings()
└─ NO → Keep it on the page
         Example: Apply player name wrapping just for this page
```

### Common Patterns to Extract

**Pattern 1: Data Processing Functions**
- Location: `teg_analysis/` (analysis, aggregation, scoring, etc.)
- Example: `prepare_complete_history_table_fast()` from `101TEG History.py`
- Reason: Reusable across multiple frontend frameworks

**Pattern 2: Formatting/Display Functions**
- Location: `nicegui/helpers/` (if NiceGUI-specific HTML generation)
- Example: `format_history_table_html()` wrapping player names with spans
- Reason: NiceGUI-specific but reusable across pages

**Pattern 3: Page-Specific Filters**
- Location: Keep on page
- Example: "Show only completed TEGs" filter specific to Honours Board
- Reason: Unlikely to be reused, specific to page logic

---

## Phase 1: History Section Breakdown

### Page 1: TEG History (101TEG History.py)

**Streamlit File:** `streamlit/101TEG History.py`

**What it shows:**
- Complete list of all TEGs (past, current, future)
- Columns: TEG | Area | TEG Trophy (winner) | Green Jacket (winner) | HMM Wooden Spoon (winner)
- Styled with wrapped player names and area labels
- Footnote for historical context
- Save prompt if winners were calculated but not cached

**Data Points to Capture:**
- [ ] TEG number
- [ ] Course/Area name (first part only)
- [ ] TEG Trophy winner (Net competition)
- [ ] Green Jacket winner (Gross competition)
- [ ] HMM Wooden Spoon winner (last place)
- [ ] Footnote about TEG 5 anomaly

**Key Functions to Use:**
- `load_cached_winners()` from `helpers/history_data_processing.py`
- `prepare_complete_history_table_fast()` from `helpers/history_data_processing.py`
- `calculate_and_save_missing_winners()` (may not implement in prototype)

**Expected Output:**
Simple HTML table with columns: TEG | Area | TEG Trophy | Green Jacket | HMM Wooden Spoon

**Data Verification Checklist:**
- [ ] All TEGs 1-N included
- [ ] Winners are correct (spot-check 3-4 TEGs)
- [ ] Area names present (first part of location string)
- [ ] No NaN/None values where data exists

---

### Page 2: Honours Board (101TEG Honours Board.py)

**Streamlit File:** `streamlit/101TEG Honours Board.py`

**What it shows:**
- Player tournament wins across all categories
- Columns: Player | TEG Trophy Wins | Green Jacket Wins | Wooden Spoon Wins | Total Wins
- Sorted by total wins descending
- Different data than player rankings (count of wins, not finishing positions)

**Data Points to Capture:**
- [ ] Player name
- [ ] Count of TEG Trophy wins
- [ ] Count of Green Jacket wins
- [ ] Count of Wooden Spoon wins
- [ ] Total wins per player

**Key Functions to Use:**
- Winners data (from teg_history)
- Group and count wins per player

**Expected Output:**
Simple HTML table with columns: Player | TEG Trophy Wins | Green Jacket Wins | Wooden Spoon | Total

**Data Verification Checklist:**
- [ ] All players with wins included
- [ ] Win counts are accurate (spot-check 3-4 players)
- [ ] Total column adds correctly
- [ ] Sorted by total descending

---

### Page 3: Full Results (102TEG Results.py)

**Streamlit File:** `streamlit/102TEG Results.py`

**What it shows:**
- Results for a selected TEG
- Controls: Dropdown to select TEG
- For chosen TEG: Complete leaderboard by round
- Columns: Player | R1 | R2 | R3 | R4 | Total

**Data Points to Capture:**
- [ ] TEG selector dropdown
- [ ] Round-by-round scores per player
- [ ] Total score
- [ ] All players in selected TEG

**Key Functions to Use:**
- `filter_data_by_teg()`
- `aggregate_data()` with aggregation_level='Round'
- Pivot table creation

**Expected Output:**
HTML table showing Player | R1 | R2 | R3 | R4 | Total

**Data Verification Checklist:**
- [ ] Dropdown includes all TEGs
- [ ] Correct rounds displayed (TEG-dependent: 3-4 rounds)
- [ ] All players included
- [ ] Totals calculated correctly
- [ ] Round counts vary by TEG appropriately

---

### Page 4: Player Rankings (player_history.py)

**Streamlit File:** `streamlit/player_history.py`

**What it shows:**
- Player rankings by TEG (finishing positions)
- Controls: Competition selector (Net vs Gross)
- Table: Player | TEG 1 | TEG 2 | ... | TEG N (with ranks 1, 2=, 3, etc.)
- Summary: Average rank by player

**Data Points to Capture:**
- [ ] Competition selector (TEG Trophy Net / Green Jacket Gross)
- [ ] Player names
- [ ] Finishing positions per TEG (1, 2=, 3, etc.)
- [ ] Average finishing position
- [ ] Count of each finishing position

**Key Functions to Use:**
- `aggregate_data()` by TEG
- `convert_pivot_scores_to_ranks()`
- `calculate_average_rank_from_ranked_df()`

**Expected Output:**
HTML table showing Player | TEG 1 | TEG 2 | ... | TEG N with rankings
Plus summary table: Player | Average Rank

**Data Verification Checklist:**
- [ ] Both competitions selectable
- [ ] Ranks show correctly (1, 2=, 3, etc.)
- [ ] All TEGs included as columns
- [ ] Average rank calculated correctly
- [ ] No missing data where player participated

---

### Page 5: TEG Reports (teg_reports.py)

**Streamlit File:** `streamlit/teg_reports.py`

**What it shows:**
- Detailed report for selected TEG
- Controls: TEG selector, section checkboxes (Summary, Scores, Rounds, Holes)
- Variable sections displayed based on checkboxes
- Summary: Winners, round counts, player count
- Scores: Net and Gross leaderboards
- Rounds: Per-round leaderboards
- Holes: Hole-by-hole data

**Data Points to Capture:**
- [ ] TEG selector
- [ ] Section toggles (Summary, Scores, Rounds, Holes)
- [ ] Tournament summary (winners, rounds, players)
- [ ] Net competition leaderboard
- [ ] Gross competition leaderboard
- [ ] Per-round leaderboards
- [ ] Hole-by-hole breakdown

**Key Functions to Use:**
- `filter_data_by_teg()`
- `aggregate_data()` with different aggregation levels (None, 'Round', etc.)
- `get_net_competition_measure()`
- Pivot table creation for various views

**Expected Output:**
Multiple HTML tables depending on section selection

**Data Verification Checklist:**
- [ ] TEG selector includes all TEGs
- [ ] Section checkboxes toggle correctly
- [ ] Summary data accurate (winners, counts)
- [ ] Net leaderboard correct for TEG number
- [ ] Gross leaderboard correct
- [ ] Round-by-round data complete
- [ ] Hole-by-hole data present

---

## Phase 1 Implementation Order

**Recommended implementation sequence:**

1. **teg_history.py** - Simplest, just a static table of all TEGs
2. **honours_board.py** - Simple grouping/counting of winners
3. **player_rankings.py** - Uses existing analysis functions, similar to demo
4. **full_results.py** - More complex filtering and aggregation
5. **teg_reports.py** - Most complex, multiple conditional sections

---

## Code Organization: Where Things Go

### If code should be in `teg_analysis/`
Examples:
- `prepare_complete_history_table_fast()` → Already exists or should be in `analysis/history.py`
- `load_cached_winners()` → Should be in `core/cache.py` or similar
- Rank conversion logic → Already in `analysis/rankings.py`
- TEG aggregation → Already in `analysis/aggregation.py`

### If code should be in `nicegui/helpers/`
Examples:
- Functions that generate HTML tables with specific formatting
- Functions that wrap player names in HTML spans
- Functions that apply NiceGUI-specific styling
- Navigation helpers (already exists as `ui_helpers.py`)

### If code should stay on page
Examples:
- Page-specific selection logic (which TEG to show)
- Page-specific section toggles
- One-off data transformations for display
- Button/control callbacks

---

## Verification & Testing Approach

### For Each Prototype Page:

1. **Open Streamlit page** in browser at the same time
2. **Create data checklist** - List every data point shown in Streamlit
3. **Build prototype** - Implement page with simple HTML table
4. **Verify completeness:**
   - [ ] All data points from Streamlit present in prototype
   - [ ] Numbers/values match between Streamlit and prototype
   - [ ] Column order matches (roughly)
   - [ ] No spurious NaN/empty rows/columns
5. **Spot-check data:**
   - Select 3-4 specific data points
   - Verify they match Streamlit output exactly
   - Check edge cases (TEGs with fewer rounds, players with no data, etc.)
6. **Run prototype_main.py:**
   - Navigate to page
   - Test any controls/filters
   - Verify no errors in console

### Sample Verification Checklist for teg_history.py:

```
Data Checklist:
- [ ] TEG 1 displayed
- [ ] TEG 1 Area: "Moortown"
- [ ] TEG 1 TEG Trophy winner: "Jon Baker"
- [ ] TEG 1 Green Jacket winner: "Malcolm Cramp"
- [ ] TEG 1 HMM Wooden Spoon: "Phil..."
[... continue for 3-4 sample TEGs ...]
- [ ] All TEGs up to latest included
- [ ] Footnote about TEG 5 present

Verification:
- [ ] Counts match (e.g., 50 total TEGs if that's the current number)
- [ ] No duplicate TEG rows
- [ ] No duplicate winners
- [ ] Winners are real players (spot check)
```

---

## Next Steps (After Phase 1)

Once Phase 1 (History) is complete:

1. **Phase 2: Records** - 3 pages (TEG Records, Top TEGs/Rounds, Personal Bests)
2. **Phase 3: Scoring** - 11 pages (Birdies/Eagles, Streaks, Averages, etc.)
3. **Phase 4: Latest TEG** - 4 pages (Leaderboard, Round Context, etc.)
4. **Phase 5: Scorecards** - 4 pages (Scorecard, Best/Worstball, Eclectics, etc.)

Each phase follows the same pattern:
1. Understand Streamlit pages
2. Extract/identify functions needed
3. Create minimalist prototypes
4. Verify data completeness
5. Move to next phase

---

## Important Notes

- **Keep prototypes simple** - Plain HTML tables, basic layout
- **Data accuracy first** - Verify numbers before any styling
- **Use Streamlit as reference** - If in doubt about what to show, check Streamlit page
- **Function extraction matters** - Proper organization now saves time later
- **Test as you go** - Verify each page before moving to next
- **Document discoveries** - If you find functions should be extracted, note for future phases

---

## Getting Started

When ready to begin:

1. Create `nicegui/prototypes/` folder structure
2. Create `nicegui/prototypes/shared_setup_prototypes.py`
3. Create `nicegui/prototypes/prototype_main.py`
4. Create `nicegui/prototypes/history/` folder
5. Start with `teg_history.py` - the simplest page
6. Work through each History page in the recommended order
7. Verify each before moving to next

Good luck! 🎯
