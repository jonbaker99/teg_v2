"""NiceGUI Prototype Application - Single Page Application with Persistent Navigation

Uses NiceGUI's ui.sub_pages architecture to create a single-page application with
a persistent navigation bar that appears on all 24 pages.

Navigation Sections (6 categories):
- Home: Index/landing page
- History (5 pages): TEG winners, results, player rankings, reports
- Records (4 pages): Tournament records, best/worst performances, personal bests
- Scoring (6 pages): Scoring analysis, achievements, streaks, course/par breakdowns
- Latest TEG (4 pages): Current tournament status, handicaps, context analysis
- Scorecards (4 pages): Scorecard viewers, team formats, eclectic scores

Run with: python prototype_main.py (from project root)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent))  # nicegui root

from nicegui import ui

# Import global stylesheet
from styles import apply_global_styles

# Import shared setup (CSS, cached data)
from prototypes.shared_setup_prototypes import (
    all_data_history,
    all_data_records,
    all_data_scoring,
    all_data_latest,
    all_data_scorecards
)

# ============================================================================
# IMPORT CONTENT FUNCTIONS (not @ui.page decorated)
# ============================================================================

# Index page
from prototypes import prototype_index

# Phase 1: History (5 pages)
from prototypes.history import teg_history, honours_board, teg_results, player_rankings, teg_reports

# Phase 2: Records (4 pages)
from prototypes.records import teg_records, best_tegs_rounds, final_round_comebacks, personal_best

# Phase 3: Scoring (6 pages)
from prototypes.scoring import ave_by_par, birdies_etc, scoring_hub, ave_by_teg, ave_by_course, streaks

# Phase 4: Latest TEG (4 pages)
from prototypes.latest import handicaps, leaderboard, latest_teg_context, latest_round_context

# Phase 5: Scorecards (4 pages)
from prototypes.scorecard import best_worstball, eclectic_records, eclectic_scores, scorecard


# ============================================================================
# ROOT FUNCTION - Persistent Navigation Bar + Sub-Pages
# ============================================================================

def root():
    """Root application container with persistent navigation and sub-pages.

    The navigation bar persists across all page transitions, creating a true
    single-page application (SPA) experience with no full page reloads.
    """

    # ===== APPLY GLOBAL STYLESHEET =====
    apply_global_styles()

    # ===== PERSISTENT NAVIGATION BAR =====
    with ui.header().classes('bg-blue-600 text-white sticky top-0 z-50'):
        with ui.row().classes('w-full items-center justify-between px-6 py-3'):
            # Application title
            ui.label('TEG Analysis Prototypes').classes('text-h6 font-bold')

            # Navigation sections
            with ui.row().classes('gap-2'):
                # Home
                ui.button('Home', icon='home').props('flat color=white').on_click(
                    lambda: ui.navigate.to('/')
                )

                # History section
                ui.button('History', icon='history').props('flat color=white').on_click(
                    lambda: ui.navigate.to('/history/teg-history')
                )

                # Records section
                ui.button('Records', icon='trophy').props('flat color=white').on_click(
                    lambda: ui.navigate.to('/records/teg-records')
                )

                # Scoring section
                ui.button('Scoring', icon='analytics').props('flat color=white').on_click(
                    lambda: ui.navigate.to('/scoring/ave-by-par')
                )

                # Latest TEG section
                ui.button('Latest TEG', icon='leaderboard').props('flat color=white').on_click(
                    lambda: ui.navigate.to('/latest/handicaps')
                )

                # Scorecards section
                ui.button('Scorecards', icon='golf_course').props('flat color=white').on_click(
                    lambda: ui.navigate.to('/scorecard/best-worstball')
                )

    # ===== SUB-PAGES DEFINITION =====
    # Register all 24 pages (1 index + 23 prototype pages)
    ui.sub_pages({
        # Index/Home
        '/': prototype_index.index_content,

        # ===== PHASE 1: HISTORY (5 pages) =====
        '/history/teg-history': teg_history.teg_history_content,
        '/history/honours-board': honours_board.honours_board_content,
        '/history/player-rankings': player_rankings.player_rankings_content,
        '/history/teg-reports': teg_reports.teg_reports_content,
        '/history/teg-results': teg_results.teg_results_content,

        # ===== PHASE 2: RECORDS (4 pages) =====
        '/records/teg-records': teg_records.teg_records_content,
        '/records/best-tegs-rounds': best_tegs_rounds.best_tegs_rounds_content,
        '/records/final-round-comebacks': final_round_comebacks.final_round_comebacks_content,
        '/records/personal-best': personal_best.personal_best_content,

        # ===== PHASE 3: SCORING (6 pages) =====
        '/scoring/ave-by-par': ave_by_par.ave_by_par_content,
        '/scoring/birdies-etc': birdies_etc.birdies_etc_content,
        '/scoring/scoring-hub': scoring_hub.scoring_hub_content,
        '/scoring/ave-by-teg': ave_by_teg.ave_by_teg_content,
        '/scoring/ave-by-course': ave_by_course.ave_by_course_content,
        '/scoring/streaks': streaks.streaks_content,

        # ===== PHASE 4: LATEST TEG (4 pages) =====
        '/latest/handicaps': handicaps.handicaps_content,
        '/latest/leaderboard': leaderboard.leaderboard_content,
        '/latest/teg-context': latest_teg_context.latest_teg_context_content,
        '/latest/round-context': latest_round_context.latest_round_context_content,

        # ===== PHASE 5: SCORECARDS (4 pages) =====
        '/scorecard/best-worstball': best_worstball.best_worstball_content,
        '/scorecard/eclectic-records': eclectic_records.eclectic_records_content,
        '/scorecard/eclectic-scores': eclectic_scores.eclectic_scores_content,
        '/scorecard/scorecard': scorecard.scorecard_content,
    })


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(root, title='TEG Analysis Prototypes - Single Page Application', reload=True)
