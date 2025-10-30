"""Player Rankings - Player ranking positions across all TEGs.

This page displays:
- Player × TEG matrix showing finishing positions for each tournament
- Separate tabs for TEG Trophy (Net) and Green Jacket (Gross) competitions
- Average position summary for each player
- Count of placements (1st, 2nd, etc.)

Corresponds to Streamlit page: streamlit/player_history.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading and analysis utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import get_complete_teg_data, get_net_competition_measure
from teg_analysis.analysis.aggregation import aggregate_data
from teg_analysis.analysis.rankings import (
    convert_pivot_scores_to_ranks,
    calculate_average_rank_from_ranked_df
)


def create_net_competition_ranking_table(teg_data: pd.DataFrame, row_dimension: str = 'Player') -> pd.DataFrame:
    """Create ranking table for Net competition (TEG Trophy).

    Args:
        teg_data: Complete TEG data with player scores
        row_dimension: 'Player' or 'Initials'

    Returns:
        DataFrame with players as rows and TEGs as columns, containing ranking positions
    """
    try:
        # Determine which measure to use based on TEG
        teg_nums = teg_data['TEGNum'].unique()

        # Create aggregate by TEG for scoring measure
        agg_data = aggregate_data(teg_data, aggregation_level='TEG')

        if agg_data.empty:
            return pd.DataFrame()

        # For each TEG, get the appropriate Net competition measure
        # TEGs 1-5 use NetVP, TEGs 6+ use Stableford
        pivot_dict = {}

        for teg_num in sorted(teg_nums):
            teg_specific_data = teg_data[teg_data['TEGNum'] == teg_num]
            agg_specific = aggregate_data(teg_specific_data, aggregation_level='TEG')

            if agg_specific.empty:
                continue

            # Determine the measure for this TEG
            if teg_num <= 5:
                measure = 'NetVP'
            else:
                measure = 'Stableford'

            # Create pivot with TEG as column
            teg_name = teg_specific_data['TEG'].iloc[0] if not teg_specific_data.empty else f'TEG {teg_num}'

            if measure in agg_specific.columns:
                teg_pivot = agg_specific.set_index('Player')[measure].rename(teg_name)
                pivot_dict[teg_num] = (teg_name, teg_pivot)

        # Combine all TEG pivots
        if not pivot_dict:
            return pd.DataFrame()

        # Create full pivot table
        all_pivots = []
        for teg_num in sorted(pivot_dict.keys()):
            teg_name, teg_pivot = pivot_dict[teg_num]
            all_pivots.append(teg_pivot)

        combined_pivot = pd.concat(all_pivots, axis=1)

        # Convert scores to ranks
        ranked_df = convert_pivot_scores_to_ranks(combined_pivot, measure='NetVP')

        return ranked_df

    except Exception as e:
        print(f'Error creating net ranking table: {e}')
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def create_teg_ranking_table(teg_data: pd.DataFrame, competition: str, row_dimension: str = 'Player') -> pd.DataFrame:
    """Create ranking table for specified competition.

    Args:
        teg_data: Complete TEG data
        competition: 'Net' for TEG Trophy or 'Gross' for Green Jacket
        row_dimension: 'Player' or 'Initials'

    Returns:
        DataFrame with players as rows and TEGs as columns with ranking positions
    """
    try:
        # Determine measure based on competition
        if competition == 'Net':
            # Use Net competition (TEG Trophy)
            measure_col = None  # Will be determined per TEG
            is_net = True
        else:
            # Gross competition (Green Jacket)
            measure_col = 'GrossVP'
            is_net = False

        teg_nums = sorted(teg_data['TEGNum'].unique())
        pivot_dict = {}

        for teg_num in teg_nums:
            teg_specific = teg_data[teg_data['TEGNum'] == teg_num]

            if teg_specific.empty:
                continue

            # Get TEG name
            teg_name = teg_specific['TEG'].iloc[0]

            # Determine measure for this TEG if Net competition
            if is_net:
                if teg_num <= 5:
                    measure = 'NetVP'
                else:
                    measure = 'Stableford'
            else:
                measure = 'GrossVP'

            # Aggregate by TEG
            agg_data = aggregate_data(teg_specific, aggregation_level='TEG')

            if agg_data.empty or measure not in agg_data.columns:
                continue

            # Create pivot for this TEG
            teg_pivot = agg_data.set_index('Player')[measure].rename(teg_name)
            pivot_dict[teg_num] = (teg_name, teg_pivot)

        if not pivot_dict:
            return pd.DataFrame()

        # Combine pivots
        all_pivots = [teg_pivot for _, (_, teg_pivot) in sorted(pivot_dict.items())]
        combined_pivot = pd.concat(all_pivots, axis=1)

        # Convert to ranks
        ranked_df = convert_pivot_scores_to_ranks(combined_pivot, measure=list(pivot_dict.values())[0][0])

        return ranked_df

    except Exception as e:
        print(f'Error creating ranking table: {e}')
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def player_rankings_content():
    """Display player rankings across all TEGs."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Player Rankings').classes('text-h5 font-bold mt-6')
    ui.label('Player finishing positions across all TEGs').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA DISPLAY AREA =====
    content_area = ui.card().classes('w-full')

    def display_rankings():
        """Load and display player rankings."""
        try:
            content_area.clear()

            with content_area:
                # Load complete TEG data
                teg_data = get_complete_teg_data()

                if teg_data.empty:
                    ui.label('No data available').classes('text-red-600')
                    return

                # Create tabs for different competitions
                with ui.tabs() as tabs:
                    # Tab 1: TEG Trophy (Net competition)
                    with ui.tab('TEG Trophy (Net)'):
                        try:
                            # Create ranking table for Net competition
                            trophy_rankings = create_teg_ranking_table(teg_data, 'Net')

                            if trophy_rankings.empty:
                                ui.label('No TEG Trophy ranking data available').classes('text-gray-600')
                            else:
                                # Display main ranking table
                                ui.label('Player Rankings').classes('text-sm font-semibold')
                                trophy_html = trophy_rankings.to_html(escape=False)
                                ui.html(trophy_html, sanitize=False)

                                # Calculate and display summary
                                ui.separator().classes('my-4')
                                ui.label('Summary Statistics').classes('text-sm font-semibold mt-4')

                                summary = calculate_average_rank_from_ranked_df(trophy_rankings)
                                if not summary.empty:
                                    summary_html = summary.to_html(escape=False)
                                    ui.html(summary_html, sanitize=False)

                        except Exception as e:
                            ui.label(f'Error loading TEG Trophy rankings: {str(e)}').classes('text-red-600')
                            print(f'Error: {e}')
                            import traceback
                            traceback.print_exc()

                    # Tab 2: Green Jacket (Gross competition)
                    with ui.tab('Green Jacket (Gross)'):
                        try:
                            # Create ranking table for Gross competition
                            jacket_rankings = create_teg_ranking_table(teg_data, 'Gross')

                            if jacket_rankings.empty:
                                ui.label('No Green Jacket ranking data available').classes('text-gray-600')
                            else:
                                # Display main ranking table
                                ui.label('Player Rankings').classes('text-sm font-semibold')
                                jacket_html = jacket_rankings.to_html(escape=False)
                                ui.html(jacket_html, sanitize=False)

                                # Calculate and display summary
                                ui.separator().classes('my-4')
                                ui.label('Summary Statistics').classes('text-sm font-semibold mt-4')

                                summary = calculate_average_rank_from_ranked_df(jacket_rankings)
                                if not summary.empty:
                                    summary_html = summary.to_html(escape=False)
                                    ui.html(summary_html, sanitize=False)

                        except Exception as e:
                            ui.label(f'Error loading Green Jacket rankings: {str(e)}').classes('text-red-600')
                            print(f'Error: {e}')
                            import traceback
                            traceback.print_exc()

        except Exception as e:
            content_area.clear()
            with content_area:
                ui.label(f'Error: {str(e)}').classes('text-red-600')
                print(f'Error in player_rankings: {e}')
                import traceback
                traceback.print_exc()

    # ===== INITIAL LOAD =====
    display_rankings()
