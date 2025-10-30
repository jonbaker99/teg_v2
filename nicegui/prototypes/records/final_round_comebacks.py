"""Final Round Comebacks & Collapses - Analyzes dramatic final round performances.

This page explores dramatic final round performances in TEG tournaments, showing:
- Biggest final round score differentials (best and worst performances)
- Biggest leads lost by players leading after the penultimate round
- Biggest leads lost during the final round itself
- Biggest comebacks in the final round, regardless of whether the player won

Corresponds to Streamlit page: streamlit/303Final Round Comebacks.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import load_all_data, read_file
from helpers.comeback_analysis import (
    calculate_final_round_differentials,
    calculate_biggest_leads_lost_after_r3,
    calculate_biggest_leads_lost_in_r4,
    calculate_biggest_comebacks
)


@ui.page('/records/final-round-comebacks')
def final_round_comebacks_page():
    """Display final round comebacks and collapses analysis."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Final Round Comebacks & Collapses').classes('text-h5 font-bold mt-6')
    ui.label('Dramatic final round performances, leads lost, and big comebacks').classes('text-sm text-gray-600')
    ui.separator()

    # ===== CONTROLS =====
    with ui.row().classes('w-full gap-4 items-center'):
        ui.label('Competition:').classes('font-semibold')
        competition_toggle = ui.toggle(
            {'Gross': 'Gross (Green Jacket)', 'Stableford': 'Stableford (Trophy)'},
            value='Gross'
        ).classes('gap-2')

        ui.label('Records to show:').classes('font-semibold ml-6')
        n_records_input = ui.number(
            value=5, min=1, max=20, step=1
        ).classes('w-24')

    ui.separator()

    # ===== DATA DISPLAY AREA =====
    content_area = ui.card().classes('w-full')

    # ===== STATE VARIABLES =====
    state = {
        'all_scores': None,
        'round_info': None,
        'current_measure': 'GrossVP',
        'current_n_records': 5
    }

    def load_data():
        """Load all data once on page load."""
        try:
            state['all_scores'] = load_all_data(exclude_teg_50=True)
            state['round_info'] = read_file('data/round_info.csv')
        except Exception as e:
            print(f'Error loading data: {e}')

    def format_score_value(value, measure):
        """Format a score value based on measure type."""
        if measure == 'GrossVP':
            if value > 0:
                return f"+{int(value)}"
            elif value < 0:
                return f"{int(value)}"
            else:
                return "="
        else:  # Stableford
            return str(int(value))

    def display_comebacks():
        """Load and display comeback analysis."""
        try:
            if state['all_scores'] is None or state['round_info'] is None:
                return

            # Determine measure and measure label
            measure = 'GrossVP' if competition_toggle.value == 'Gross' else 'Stableford'
            measure_label = 'Gross vs Par' if measure == 'GrossVP' else 'Stableford Points'
            better_direction = 'Lower is better' if measure == 'GrossVP' else 'Higher is better'
            n_records = int(n_records_input.value)

            state['current_measure'] = measure
            state['current_n_records'] = n_records

            content_area.clear()

            with content_area:
                # ===== SECTION 1: BEST & WORST FINAL ROUNDS =====
                ui.label('1. Best & Worst Final Rounds').classes('text-lg font-semibold mt-4 mb-2')
                ui.label(f'Best and worst final round performances ({better_direction})').classes('text-sm text-gray-600 mb-3')

                differentials = calculate_final_round_differentials(state['all_scores'], state['round_info'], measure)

                if not differentials.empty:
                    # Best performances
                    ui.label('Best Final Round Performances').classes('text-base font-semibold mt-3 mb-2')
                    best_final_rounds = differentials.head(n_records).copy()
                    best_final_rounds['Rank After R3'] = best_final_rounds['Rank After R3'].astype(int).astype(str)
                    best_final_rounds['Final Rank'] = best_final_rounds['Final Rank'].astype(int).astype(str)
                    best_final_rounds['Final Round'] = best_final_rounds['Final Round'].astype(int)
                    best_final_rounds['Final Round Score'] = best_final_rounds['Final Round Score'].apply(
                        lambda x: format_score_value(x, measure)
                    )
                    best_final_rounds['Total Score'] = best_final_rounds['Total Score'].apply(
                        lambda x: format_score_value(x, measure)
                    )

                    ui.html(best_final_rounds.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table'
                    ), sanitize=False)

                    # Worst performances
                    ui.label('Worst Final Round Performances').classes('text-base font-semibold mt-4 mb-2')
                    worst_final_rounds = differentials.tail(n_records).iloc[::-1].copy()
                    worst_final_rounds['Rank After R3'] = worst_final_rounds['Rank After R3'].astype(int).astype(str)
                    worst_final_rounds['Final Rank'] = worst_final_rounds['Final Rank'].astype(int).astype(str)
                    worst_final_rounds['Final Round'] = worst_final_rounds['Final Round'].astype(int)
                    worst_final_rounds['Final Round Score'] = worst_final_rounds['Final Round Score'].apply(
                        lambda x: format_score_value(x, measure)
                    )
                    worst_final_rounds['Total Score'] = worst_final_rounds['Total Score'].apply(
                        lambda x: format_score_value(x, measure)
                    )

                    ui.html(worst_final_rounds.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table'
                    ), sanitize=False)

                    # Worst by leaders
                    ui.label('Worst Final Round Performances by Leaders').classes('text-base font-semibold mt-4 mb-2')
                    ui.label('Leaders going into the final round (Rank After R3 = 1)').classes('text-sm text-gray-600 mb-2')

                    leaders_only = differentials[differentials['Rank After R3'] == 1.0].copy()
                    if not leaders_only.empty:
                        leaders_only = leaders_only.sort_values('Final Round Score', ascending=not (measure == 'GrossVP'))
                        worst_leaders = leaders_only.head(n_records).copy()
                        worst_leaders['Rank After R3'] = worst_leaders['Rank After R3'].astype(int).astype(str)
                        worst_leaders['Final Rank'] = worst_leaders['Final Rank'].astype(int).astype(str)
                        worst_leaders['Final Round'] = worst_leaders['Final Round'].astype(int)
                        worst_leaders['Final Round Score'] = worst_leaders['Final Round Score'].apply(
                            lambda x: format_score_value(x, measure)
                        )
                        worst_leaders['Total Score'] = worst_leaders['Total Score'].apply(
                            lambda x: format_score_value(x, measure)
                        )

                        ui.html(worst_leaders.to_html(
                            escape=False,
                            index=False,
                            justify='left',
                            classes='datawrapper-table'
                        ), sanitize=False)
                    else:
                        ui.label('No leader data available').classes('text-gray-600')
                else:
                    ui.label(f'No data available').classes('text-gray-600')

                ui.separator().classes('my-4')

                # ===== SECTION 2: BIGGEST LEADS LOST (AFTER R3) =====
                ui.label('2. Biggest Leads Lost Going Into Final Round').classes('text-lg font-semibold mt-4 mb-2')
                ui.label('Leaders after the penultimate round who didn\'t win').classes('text-sm text-gray-600 mb-3')

                leads_lost_r3 = calculate_biggest_leads_lost_after_r3(state['all_scores'], state['round_info'], measure)

                if not leads_lost_r3.empty:
                    display_leads_r3 = leads_lost_r3.head(n_records).copy()
                    display_leads_r3['Gap to 2nd'] = display_leads_r3['Gap to 2nd'].apply(
                        lambda x: f"+{x:.0f}" if x > 0 else f"{x:.0f}"
                    )
                    display_leads_r3['Leader Final Position'] = display_leads_r3['Leader Final Position'].astype(int).astype(str)

                    ui.html(display_leads_r3.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table'
                    ), sanitize=False)
                else:
                    ui.label(f'No leads lost after R3 found').classes('text-gray-600')

                ui.separator().classes('my-4')

                # ===== SECTION 3: BIGGEST LEADS LOST DURING R4 =====
                ui.label('3. Biggest Leads Lost During Final Round').classes('text-lg font-semibold mt-4 mb-2')
                ui.label('Maximum lead held during the final round by players who didn\'t win').classes('text-sm text-gray-600 mb-3')

                leads_lost_r4 = calculate_biggest_leads_lost_in_r4(state['all_scores'], state['round_info'], measure)

                if not leads_lost_r4.empty:
                    display_leads_r4 = leads_lost_r4.head(n_records).copy()
                    display_leads_r4['Max Lead in R4'] = display_leads_r4['Max Lead in R4'].apply(
                        lambda x: f"+{x:.0f}" if x > 0 else f"{x:.0f}"
                    )
                    display_leads_r4['Final Gap'] = display_leads_r4['Final Gap'].apply(
                        lambda x: f"+{x:.0f}" if x > 0 else f"{x:.0f}"
                    )
                    display_leads_r4['Hole of Max Lead'] = display_leads_r4['Hole of Max Lead'].astype(int).astype(str)

                    ui.html(display_leads_r4.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table'
                    ), sanitize=False)
                else:
                    ui.label(f'No leads lost during R4 found').classes('text-gray-600')

                ui.separator().classes('my-4')

                # ===== SECTION 4: BIGGEST COMEBACKS =====
                ui.label('4. Biggest Comebacks in Final Round').classes('text-lg font-semibold mt-4 mb-2')
                ui.label('Largest improvements from position after R3, regardless of winning').classes('text-sm text-gray-600 mb-3')

                comebacks = calculate_biggest_comebacks(state['all_scores'], state['round_info'], measure)

                if not comebacks.empty:
                    display_comebacks = comebacks.head(n_records).copy()
                    display_comebacks['Gap After R3'] = display_comebacks['Gap After R3'].apply(
                        lambda x: format_score_value(x, measure)
                    )
                    display_comebacks['Player R4 Score'] = display_comebacks['Player R4 Score'].apply(
                        lambda x: format_score_value(x, measure)
                    )
                    display_comebacks['Leader R4 Score'] = display_comebacks['Leader R4 Score'].apply(
                        lambda x: format_score_value(x, measure)
                    )
                    display_comebacks['Gap Closed'] = display_comebacks['Gap Closed'].apply(
                        lambda x: f"+{x:.0f}" if x > 0 else f"{x:.0f}"
                    )
                    display_comebacks['Final Position'] = display_comebacks['Final Position'].astype(int).astype(str)

                    ui.html(display_comebacks.to_html(
                        escape=False,
                        index=False,
                        justify='left',
                        classes='datawrapper-table'
                    ), sanitize=False)
                else:
                    ui.label(f'No comeback data available').classes('text-gray-600')

                ui.separator().classes('my-4')

                # ===== NOTES =====
                ui.label('Notes:').classes('text-sm font-semibold')
                ui.html("""
                <ul class="text-sm text-gray-700 ml-4">
                    <li>Analysis excludes TEG 2 (only had 3 rounds)</li>
                    <li>Stableford analysis only includes TEG 6 onwards (when Stableford was introduced)</li>
                    <li>"Gap Closed" shows improvement in position relative to leader/winner</li>
                    <li>All gaps are calculated as absolute differences in scoring</li>
                </ul>
                """, sanitize=False)

        except Exception as e:
            content_area.clear()
            with content_area:
                ui.label(f'Error loading comebacks: {str(e)}').classes('text-red-600')
                print(f'Error in final_round_comebacks: {e}')
                import traceback
                traceback.print_exc()

    # ===== EVENT HANDLERS =====
    competition_toggle.on_value_change(lambda: display_comebacks())
    n_records_input.on_value_change(lambda: display_comebacks())

    # ===== INITIAL LOAD =====
    load_data()
    display_comebacks()
