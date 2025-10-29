"""NiceGUI Prototype Application Runner

Organizes prototype pages by section, systematically recreating Streamlit
functionality with minimalist design (simple HTML tables for data verification).

Sections (phases):
- Phase 1: History (5 pages) - TEG winners, results, player rankings
- Phase 2: Records (3 pages) - Tournament records, personal bests
- Phase 3: Scoring (11 pages) - Scoring analysis and distributions
- Phase 4: Latest TEG (4 pages) - Current tournament leaderboard and context
- Phase 5: Scorecards (4 pages) - Detailed scorecard analysis

Run with: python prototype_main.py (from project root)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent))  # nicegui root

from nicegui import ui

# Import shared setup (CSS, cached data)
from prototypes.shared_setup_prototypes import (
    all_data_history,
    all_data_records,
    all_data_scoring,
    all_data_latest,
    all_data_scorecards
)

# ============================================================================
# PHASE 1: HISTORY (5 pages)
# ============================================================================
# Currently importing: teg_history, honours_board, full_results,
#                      player_rankings, teg_reports
# Status: Implementation in progress

# from prototypes.history import teg_history
# from prototypes.history import honours_board
# from prototypes.history import full_results
# from prototypes.history import player_rankings
# from prototypes.history import teg_reports

# ============================================================================
# PHASE 2: RECORDS (3 pages) - FUTURE
# ============================================================================
# from prototypes.records import teg_records
# from prototypes.records import top_tegs_and_rounds
# from prototypes.records import personal_bests

# ============================================================================
# PHASE 3: SCORING (11 pages) - FUTURE
# ============================================================================
# from prototypes.scoring import eagles_birdies_pars
# from prototypes.scoring import streaks
# from prototypes.scoring import ave_by_par
# ... etc

# ============================================================================
# PHASE 4: LATEST TEG (4 pages) - FUTURE
# ============================================================================
# from prototypes.latest import leaderboard
# ... etc

# ============================================================================
# PHASE 5: SCORECARDS (4 pages) - FUTURE
# ============================================================================
# from prototypes.scorecards import scorecard
# ... etc

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='TEG Analysis Prototypes - Phase 1: History', reload=True)
