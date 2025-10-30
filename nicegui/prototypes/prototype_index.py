"""NiceGUI Prototype Application - Index/Home Page

This page serves as the root entry point for the prototype application,
providing navigation to all available prototype pages organized by phase.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent))  # nicegui root

from nicegui import ui


def index_content():
    """Display home page with navigation to all prototype pages."""

    # ===== MAIN CONTENT =====
    with ui.column().classes('w-full p-6'):
        ui.label('TEG Analysis - NiceGUI Prototypes').classes('text-h4 font-bold mb-2')
        ui.label('Select a section below to explore the prototypes').classes('text-base text-gray-600 mb-6')
        ui.separator()

        ui.label('Phase 1: History Section').classes('text-h6 font-bold mt-6')
        ui.label('Select a page below to view the prototype').classes('text-sm text-gray-600')
        ui.separator()

        # ===== PHASE 1: HISTORY (5 pages) =====
        with ui.column().classes('gap-3 w-full'):
            # TEG History
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('TEG History', icon='history').on_click(
                    lambda: ui.navigate.to('/history/teg-history')
                ).props('no-caps').classes('bg-blue-500 text-white')
                ui.label('Complete list of all TEGs with competition winners').classes('text-sm text-gray-700 mt-1')

            # Honours Board
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Honours Board', icon='emoji_events').on_click(
                    lambda: ui.navigate.to('/history/honours-board')
                ).props('no-caps').classes('bg-blue-500 text-white')
                ui.label('Tournament wins, doubles, eagles, and holes in one').classes('text-sm text-gray-700 mt-1')

            # Player Rankings
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Player Rankings', icon='bar_chart').on_click(
                    lambda: ui.navigate.to('/history/player-rankings')
                ).props('no-caps').classes('bg-blue-500 text-white')
                ui.label('Player finishing positions across all TEGs').classes('text-sm text-gray-700 mt-1')

            # TEG Reports
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('TEG Reports', icon='description').on_click(
                    lambda: ui.navigate.to('/history/teg-reports')
                ).props('no-caps').classes('bg-blue-500 text-white')
                ui.label('Tournament and round-by-round reports with markdown').classes('text-sm text-gray-700 mt-1')

            # TEG Results
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('TEG Results', icon='leaderboard').on_click(
                    lambda: ui.navigate.to('/history/teg-results')
                ).props('no-caps').classes('bg-blue-500 text-white')
                ui.label('Individual TEG results with leaderboards by round').classes('text-sm text-gray-700 mt-1')

        # ===== PHASE 2: RECORDS (4 pages) =====
        ui.separator().classes('mt-8')
        ui.label('Phase 2: Records Section').classes('text-h6 font-bold mt-6')
        ui.label('All-time records, best/worst performances, personal records').classes('text-sm text-gray-600')
        ui.separator()

        with ui.column().classes('gap-3 w-full'):
            # TEG Records
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('TEG Records', icon='trophy').on_click(
                    lambda: ui.navigate.to('/records/teg-records')
                ).props('no-caps').classes('bg-green-500 text-white')
                ui.label('Comprehensive all-time records across 5 categories').classes('text-sm text-gray-700 mt-1')

            # Best TEGs and Rounds
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Top TEGs & Rounds', icon='star').on_click(
                    lambda: ui.navigate.to('/records/best-tegs-rounds')
                ).props('no-caps').classes('bg-green-500 text-white')
                ui.label('Best and worst performances by scoring measure').classes('text-sm text-gray-700 mt-1')

            # Final Round Comebacks
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Final Round Comebacks', icon='trending_up').on_click(
                    lambda: ui.navigate.to('/records/final-round-comebacks')
                ).props('no-caps').classes('bg-green-500 text-white')
                ui.label('Dramatic final rounds, leads lost, and big comebacks').classes('text-sm text-gray-700 mt-1')

            # Personal Best
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Personal Bests & Worsts', icon='person').on_click(
                    lambda: ui.navigate.to('/records/personal-best')
                ).props('no-caps').classes('bg-green-500 text-white')
                ui.label('Each player\'s best and worst performances by category').classes('text-sm text-gray-700 mt-1')

        # ===== PHASE 3: SCORING (6 pages) =====
        ui.separator().classes('mt-8')
        ui.label('Phase 3: Scoring Section').classes('text-h6 font-bold mt-6')
        ui.label('Scoring analysis, achievements, and streaks').classes('text-sm text-gray-600')
        ui.separator()

        with ui.column().classes('gap-3 w-full'):
            # Average by Par
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Average by Par', icon='show_chart').on_click(
                    lambda: ui.navigate.to('/scoring/ave-by-par')
                ).props('no-caps').classes('bg-amber-500 text-white')
                ui.label('Performance breakdown by hole par value (3, 4, 5)').classes('text-sm text-gray-700 mt-1')

            # Birds etc.
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Eagles, Birdies etc.', icon='celebration').on_click(
                    lambda: ui.navigate.to('/scoring/birdies-etc')
                ).props('no-caps').classes('bg-amber-500 text-white')
                ui.label('Scoring achievements by type (career, single-round, single-TEG)').classes('text-sm text-gray-700 mt-1')

            # Scoring Hub
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Scoring Hub', icon='analytics').on_click(
                    lambda: ui.navigate.to('/scoring/scoring-hub')
                ).props('no-caps').classes('bg-amber-500 text-white')
                ui.label('Comprehensive 4-section scoring analysis dashboard').classes('text-sm text-gray-700 mt-1')

            # Player Performance Over Time
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Performance Over Time', icon='trending_up').on_click(
                    lambda: ui.navigate.to('/scoring/ave-by-teg')
                ).props('no-caps').classes('bg-amber-500 text-white')
                ui.label('Interactive line chart of Gross vs Par by player across all TEGs').classes('text-sm text-gray-700 mt-1')

            # Course Averages
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Course Averages', icon='golf_course').on_click(
                    lambda: ui.navigate.to('/scoring/ave-by-course')
                ).props('no-caps').classes('bg-amber-500 text-white')
                ui.label('Course performance analysis with 6 views and area filtering').classes('text-sm text-gray-700 mt-1')

            # Streaks
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Streaks', icon='timeline').on_click(
                    lambda: ui.navigate.to('/scoring/streaks')
                ).props('no-caps').classes('bg-amber-500 text-white')
                ui.label('Career and record streaks with detailed window-based filtering').classes('text-sm text-gray-700 mt-1')

        # ===== PHASE 4: LATEST TEG (4 pages) =====
        ui.separator().classes('mt-8')
        ui.label('Phase 4: Latest TEG Section').classes('text-h6 font-bold mt-6')
        ui.label('Current tournament status, handicaps, leaderboards, and context analysis').classes('text-sm text-gray-600')
        ui.separator()

        with ui.column().classes('gap-3 w-full'):
            # Handicaps
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Handicaps', icon='trending_down').on_click(
                    lambda: ui.navigate.to('/latest/handicaps')
                ).props('no-caps').classes('bg-purple-500 text-white')
                ui.label('Current player handicaps with history and draft management').classes('text-sm text-gray-700 mt-1')

            # Latest Leaderboard
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Latest Leaderboard', icon='leaderboard').on_click(
                    lambda: ui.navigate.to('/latest/leaderboard')
                ).props('no-caps').classes('bg-purple-500 text-white')
                ui.label('Current tournament leaderboard (Net/Gross) with round scorecards').classes('text-sm text-gray-700 mt-1')

            # TEG Context
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('TEG Context', icon='compare').on_click(
                    lambda: ui.navigate.to('/latest/teg-context')
                ).props('no-caps').classes('bg-purple-500 text-white')
                ui.label('Selected TEG analysis with comparison metrics and records').classes('text-sm text-gray-700 mt-1')

            # Round Context
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Round Context', icon='schedule').on_click(
                    lambda: ui.navigate.to('/latest/round-context')
                ).props('no-caps').classes('bg-purple-500 text-white')
                ui.label('Selected round analysis with cumulative charts and scorecard').classes('text-sm text-gray-700 mt-1')

        # ===== PHASE 5: SCORECARDS (4 pages) =====
        ui.separator().classes('mt-8')
        ui.label('Phase 5: Scorecards Section').classes('text-h6 font-bold mt-6')
        ui.label('Scorecard viewing, team formats, and eclectic score analysis').classes('text-sm text-gray-600')
        ui.separator()

        with ui.column().classes('gap-3 w-full'):
            # Best/Worstball
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Best/Worstball', icon='strategy').on_click(
                    lambda: ui.navigate.to('/scorecard/best-worstball')
                ).props('no-caps').classes('bg-red-500 text-white')
                ui.label('Best and worst team hole scores with filtering and sorting').classes('text-sm text-gray-700 mt-1')

            # Eclectic Records
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Eclectic Records', icon='emoji_events').on_click(
                    lambda: ui.navigate.to('/scorecard/eclectic-records')
                ).props('no-caps').classes('bg-red-500 text-white')
                ui.label('Top eclectic scores by TEG and course').classes('text-sm text-gray-700 mt-1')

            # Eclectic Scores
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Eclectic Scores', icon='golf_course').on_click(
                    lambda: ui.navigate.to('/scorecard/eclectic-scores')
                ).props('no-caps').classes('bg-red-500 text-white')
                ui.label('Interactive eclectic score exploration with flexible filtering').classes('text-sm text-gray-700 mt-1')

            # Scorecards
            with ui.row().classes('gap-4 items-start w-full'):
                ui.button('Scorecards', icon='leaderboard').on_click(
                    lambda: ui.navigate.to('/scorecard/scorecard')
                ).props('no-caps').classes('bg-red-500 text-white')
                ui.label('Detailed scorecards in three formats (single/tournament/comparison)').classes('text-sm text-gray-700 mt-1')
