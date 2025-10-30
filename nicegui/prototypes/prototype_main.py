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
# INDEX PAGE (Home/Root)
# ============================================================================
# Must be imported first to serve as the root page

from prototypes import prototype_index

# ============================================================================
# PHASE 1: HISTORY (5 pages)
# ============================================================================
# Status: All 5 pages implemented and functional
# - teg_history: Complete TEG history with winners
# - honours_board: Win summaries, doubles, eagles, aces
# - teg_results: Individual TEG results with leaderboards
# - player_rankings: Player ranking positions across all TEGs
# - teg_reports: Tournament and round reports with markdown

from prototypes.history import teg_history
from prototypes.history import honours_board
from prototypes.history import teg_results
from prototypes.history import player_rankings
from prototypes.history import teg_reports

# ============================================================================
# PHASE 2: RECORDS (4 pages)
# ============================================================================
# Status: All 4 pages implemented and functional
# - teg_records: Comprehensive all-time records across categories
# - best_tegs_rounds: Top TEGs and rounds by measure selection
# - final_round_comebacks: Final round performances, leads lost, comebacks
# - personal_best: Each player's best/worst performances by category

from prototypes.records import teg_records
from prototypes.records import best_tegs_rounds
from prototypes.records import final_round_comebacks
from prototypes.records import personal_best

# ============================================================================
# PHASE 3: SCORING (6 pages)
# ============================================================================
# Status: All 6 pages implemented and functional
# - ave_by_par: Average score breakdown by hole par value
# - birdies_etc: Scoring achievements (eagles, birdies, pars, triple bogeys)
# - scoring_hub: Comprehensive 4-section scoring analysis hub
# - ave_by_teg: Interactive line chart showing performance over time
# - ave_by_course: Course performance analysis with 6 tabs
# - streaks: Streak analysis with nested tabs and filtering

from prototypes.scoring import ave_by_par
from prototypes.scoring import birdies_etc
from prototypes.scoring import scoring_hub
from prototypes.scoring import ave_by_teg
from prototypes.scoring import ave_by_course
from prototypes.scoring import streaks

# ============================================================================
# PHASE 4: LATEST TEG (4 pages)
# ============================================================================
# Status: All 4 pages implemented and functional
# - handicaps: Current player handicaps with history and draft updates
# - leaderboard: Current tournament leaderboard with Net/Gross competitions
# - latest_teg_context: Selected TEG analysis with comparison to other TEGs
# - latest_round_context: Selected round analysis with metrics and charts

from prototypes.latest import handicaps
from prototypes.latest import leaderboard
from prototypes.latest import latest_teg_context
from prototypes.latest import latest_round_context

# ============================================================================
# PHASE 5: SCORECARDS (4 pages)
# ============================================================================
# Status: All 4 pages implemented and functional
# - best_worstball: Best/worst team hole scores across rounds
# - eclectic_records: Top eclectic scores by TEG and course
# - eclectic_scores: Interactive eclectic score exploration
# - scorecard: Detailed scorecard viewing (single/tournament/comparison)

from prototypes.scorecard import best_worstball
from prototypes.scorecard import eclectic_records
from prototypes.scorecard import eclectic_scores
from prototypes.scorecard import scorecard

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='TEG Analysis Prototypes - Phases 1-5: Complete Migration', reload=True)
