"""Streamlit page for displaying the current TEG leaderboard.

This page automatically displays the leaderboard for the most recent TEG,
whether it is in progress or completed. It provides a detailed view of the
competition, including:
- Leaderboards for the "TEG Trophy & Spoon" (Net) and "Green Jacket" (Gross)
  competitions.
- Interactive charts showing the cumulative progress of each player.
- Detailed scorecards for each round of the tournament.

The page uses helper functions to:
- Load and process the data for the latest tournament.
- Automatically detect the tournament status (in-progress or complete).
- Create and display formatted leaderboards, charts, and scorecards.
"""
# === IMPORTS ===
import streamlit as st
import pandas as pd
from typing import List, Dict, Any
import logging

# Import data loading functions from main utils
from utils import get_teg_rounds, get_round_data, load_all_data, load_datawrapper_css, read_file

# Import chart creation functions
from make_charts import create_cumulative_graph, adjusted_grossvp, adjusted_stableford

# Import leaderboard display functions (shared utilities)
from leaderboard_utils import create_leaderboard, generate_table_html, format_value, get_champions, get_last_place, display_leaderboard, display_net_leaderboard

# Import scorecard generation functions
from scorecard_utils import generate_round_comparison_html, load_scorecard_css

#=== HELPER FOR CHARTS =====
# --- helper: white-filled markers with coloured outlines for Plotly ---
def _add_series_markers(fig, size=3, border_width=1):
    for tr in fig.data:
        if getattr(tr, "type", None) == "scatter":
            # outline uses the line colour for the trace
            line_col = getattr(tr, "line", {}).get("color", None) if isinstance(tr.line, dict) else tr.line.color
            tr.mode = "lines+markers" if (tr.mode is None or "markers" not in tr.mode) else tr.mode
            tr.marker = dict(
                symbol="circle",
                size=size,
                color="white",                          # fill
                line=dict(width=border_width, color=line_col)  # outline
            )
    return fig



# === CONFIGURATION ===

# === PAGE LAYOUT CONFIGURATION ===
from utils import get_page_layout
layout = get_page_layout(__file__)
st.set_page_config(layout=layout)

# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page constants
PAGE_TITLE = "Current Leaderboard"
MEASURES = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
PLAYER_COLUMN = 'Player'


# === DATA LOADING ===
# Load CSS styling for consistent table appearance
load_datawrapper_css()

# Load scorecard CSS styling for the scorecards tab
load_scorecard_css()

# Configuration: Exclude TEG 50 from all analysis
ex_teg_50 = True
if not ex_teg_50:
    st.markdown("# TEG 50 IS INCLUDED... BE CAREFUL")

try:
    with st.spinner("Loading data..."):
        # Load round-level data (includes incomplete TEGs, excludes TEG 50)
        # Purpose: Latest leaderboard needs current tournament data, even if incomplete
        round_df = get_round_data(ex_50=ex_teg_50)
        
        # Load complete dataset for chart generation (excludes TEG 50)
        # Purpose: Charts need full hole-by-hole data to show cumulative progress
        all_data = load_all_data(exclude_teg_50=ex_teg_50)

    # === DATA VALIDATION ===
    # Verify required columns exist in the dataset
    required_columns = [PLAYER_COLUMN, 'TEGNum', 'TEG', 'Round'] + MEASURES
    missing_columns = [col for col in required_columns if col not in round_df.columns]
    if missing_columns:
        st.error(f"Missing columns in data: {', '.join(missing_columns)}")
        logger.error(f"Missing columns in data: {', '.join(missing_columns)}")
        st.stop()

    # Prepare tournament list
    teg_order = round_df[['TEG', 'TEGNum']].drop_duplicates().sort_values('TEGNum')
    tegs = teg_order['TEG'].tolist()

    if not tegs:
        st.warning("No TEGs available in the data.")
        st.stop()

    # === AUTOMATIC LATEST TOURNAMENT SELECTION ===
    # Automatically select the most recent tournament (different from TEG Results page)
    # Purpose: Leaderboard page focuses on current/latest tournament progress
    chosen_teg = all_data.loc[all_data['TEGNum'].idxmax(), 'TEG']

    # Filter data for the latest tournament
    leaderboard_df = round_df[round_df['TEG'] == chosen_teg]

    if leaderboard_df.empty:
        st.warning(f"No data available for {chosen_teg}.")
        st.stop()

    # === TOURNAMENT STATUS DETERMINATION ===
    # Determine if tournament is complete or in progress using fast status files
    teg_num = int(chosen_teg.split()[-1])  # Extract number from "TEG 18"

    # Check if TEG is completed
    try:
        completed_tegs = read_file('data/completed_tegs.csv')
        if not completed_tegs.empty and teg_num in completed_tegs['TEGNum'].values:
            current_rounds = completed_tegs[completed_tegs['TEGNum'] == teg_num]['Rounds'].iloc[0]
            is_complete = True
        else:
            # Check if TEG is in progress
            in_progress_tegs = read_file('data/in_progress_tegs.csv')
            if not in_progress_tegs.empty and teg_num in in_progress_tegs['TEGNum'].values:
                current_rounds = in_progress_tegs[in_progress_tegs['TEGNum'] == teg_num]['Rounds'].iloc[0]
                is_complete = False
            else:
                # Fallback to original method if not in status files
                current_rounds = leaderboard_df['Round'].nunique()
                total_rounds = get_teg_rounds(chosen_teg)
                is_complete = current_rounds >= total_rounds
    except Exception:
        # Fallback to original method if status files not available
        current_rounds = leaderboard_df['Round'].nunique()
        total_rounds = get_teg_rounds(chosen_teg)
        is_complete = current_rounds >= total_rounds

    # Set appropriate labels based on tournament status
    page_header = f"{chosen_teg} Results" if is_complete else f"{chosen_teg} Leaderboard"
    leader_label = "Champion" if is_complete else "Leader"

    # Display page header
    st.subheader(page_header)

    # === MAIN CONTENT TABS ===
    # Three main sections: Trophy (Net), Green Jacket (Gross), and Scorecards
    tab1, tab2, tab3 = st.tabs(["TEG Trophy & Spoon", "Green Jacket", "Scorecards"])

    # === TEG TROPHY TAB (NET COMPETITION) ===
    with tab1:

        # display_net_leaderboard() - Shows formatted leaderboard with automatic measure detection
        display_net_leaderboard(
            leaderboard_df, 
            f"{chosen_teg} Trophy Leaderboard",
            leader_label
        )

# ----- BEGIN: Trophy chart section (drop-in) -----
        st.markdown("")  # spacing
        st.markdown(f"##### TEG Trophy race: {chosen_teg}")

        chart_container = st.container()
        radio_container = st.container()

        with radio_container:
            stableford_chart_type = st.segmented_control(
                "Choose Stableford chart type:",
                options=["Standard", "Adjusted scale (score vs. net par)", "Ranking"],
                key="stableford_chart_type",
                default="Adjusted scale (score vs. net par)",
            )
            if stableford_chart_type == "Ranking":
                st.caption("Shows tournament ranking progression (1st, 2nd, 3rd, etc.)")
            else:
                st.caption("Adjusted view 'zooms in' by showing performance vs. net par to more clearly show gaps.")

        # Build the chosen chart
        if stableford_chart_type == "Standard":
            fig_stableford = create_cumulative_graph(
                all_data, chosen_teg, "Stableford Cum TEG",
                f"Trophy race: {chosen_teg}",
                y_axis_label="Cumulative Stableford Points",
                chart_type="stableford"
            )
            label_short = "Cumulative stableford points"

        elif stableford_chart_type == "Adjusted scale (score vs. net par)":
            fig_stableford = create_cumulative_graph(
                all_data, chosen_teg, "Adjusted Stableford",
                f"Trophy race (Adjusted scale): {chosen_teg}",
                y_calculation=adjusted_stableford,
                y_axis_label="Cumulative Stableford Points vs. net par",
                chart_type="stableford"
            )
            label_short = "Cumulative stableford points (adjusted scale)"

        else:  # Ranking
            fig_stableford = create_cumulative_graph(
                all_data, chosen_teg, "Rank_Stableford_TEG",
                f"Trophy race (Ranking): {chosen_teg}",
                y_axis_label="Tournament Ranking",
                chart_type="ranking"
            )
            # Integer ticks and reversed axis so 1st is at the top
            n_players = leaderboard_df["Player"].nunique()
            fig_stableford.update_yaxes(
                range=[n_players + 0.5, 0.5],  # reversed
                tickmode="linear",
                dtick=1,
                tick0=1
            )
            label_short = "Tournament ranking progression"

        # Common styling for all variants
        _add_series_markers(fig_stableford, size=3, border_width=1)
        fig_stableford.update_xaxes(range=[0.5, 72.5])  # padding without adding extra tick

        with chart_container:
            if stableford_chart_type == "Ranking":
                st.caption(f"{label_short} | Lower = better")
            else:
                st.caption(f"{label_short} | Higher = better")
            st.plotly_chart(fig_stableford, use_container_width=True, config=dict({"displayModeBar": False}))
        # ----- END: Trophy chart section -----

        

    # === GREEN JACKET TAB (GROSS SCORE COMPETITION) ===
    with tab2: 
        
        # display_leaderboard() - Shows formatted leaderboard for gross scores
        display_leaderboard(
            leaderboard_df=leaderboard_df, 
            value_column='GrossVP', 
            title=f"{chosen_teg} Green Jacket Leaderboard",
            leader_label=leader_label, 
            ascending=True,  # Lower gross scores are better
            competition_name="Green Jacket"
        )

        # ----- BEGIN: Green Jacket chart section (drop-in) -----
        st.markdown("")  # spacing
        st.markdown(f"##### Green Jacket race: {chosen_teg}")

        chart_container = st.container()
        radio_container = st.container()

        with radio_container:
            grossvp_chart_type = st.segmented_control(
                "Choose chart type:",
                options=["Standard", "Adjusted scale (gross score vs. bogey)", "Ranking"],
                key="grossvp_chart_type",
                default="Adjusted scale (gross score vs. bogey)",
            )
            if grossvp_chart_type == "Ranking":
                st.caption("Shows tournament ranking progression (1st, 2nd, 3rd, etc.)")
            else:
                st.caption("Adjusted view 'zooms in' by showing performance vs. bogey golf (par+1).")

        # Build the chosen chart
        if grossvp_chart_type == "Standard":
            fig_grossvp = create_cumulative_graph(
                all_data, chosen_teg, "GrossVP Cum TEG",
                f"Green Jacket race: {chosen_teg}",
                y_axis_label="Cumulative gross vs par",
                chart_type="gross"
            )
            label_short = "Cumulative gross score vs. par"

        elif grossvp_chart_type == "Adjusted scale (gross score vs. bogey)":
            fig_grossvp = create_cumulative_graph(
                all_data, chosen_teg, "Adjusted GrossVP",
                f"Green Jacket race (Adjusted scale): {chosen_teg}",
                y_calculation=adjusted_grossvp,
                y_axis_label="Cumulative gross vs. bogey golf (par+1)",
                chart_type="gross"
            )
            label_short = "Cumulative gross score (adjusted scale vs. bogey)"

        else:  # Ranking
            fig_grossvp = create_cumulative_graph(
                all_data, chosen_teg, "Rank_GrossVP_TEG",
                f"Green Jacket race (Ranking): {chosen_teg}",
                y_axis_label="Tournament Ranking",
                chart_type="ranking"
            )
            # Integer ticks and reversed axis so 1st is at the top
            n_players = leaderboard_df["Player"].nunique()
            fig_grossvp.update_yaxes(
                range=[n_players + 0.5, 0.5],  # reversed
                tickmode="linear",
                dtick=1,
                tick0=1
            )
            label_short = "Tournament ranking progression"

        # Common styling for all variants
        _add_series_markers(fig_grossvp, size=3, border_width=1)
        fig_grossvp.update_xaxes(range=[0.5, 72.5])

        with chart_container:
            if grossvp_chart_type == "Ranking":
                st.caption(f"{label_short} | Lower = better")
            else:
                st.caption(f"{label_short} | Lower = better")
            st.plotly_chart(fig_grossvp, use_container_width=True, config=dict({"displayModeBar": False}))
        # ----- END: Green Jacket chart section -----


    # === SCORECARDS TAB ===
    with tab3:
        st.markdown(f'### {chosen_teg} Scorecards')
        # st.caption('Detailed hole-by-hole scorecards for each round')

        # Extract TEG number from chosen_teg string (e.g., "TEG 18" -> 18)
        try:
            teg_num = int(chosen_teg.split()[-1])
        except (ValueError, IndexError):
            st.error(f"Could not extract TEG number from '{chosen_teg}'")
            teg_num = None

        if teg_num is not None:
            # Get available rounds for this TEG (only existing rounds)
            available_rounds = sorted(leaderboard_df['Round'].unique())

            if not available_rounds:
                st.warning(f"No round data available for {chosen_teg}")
            else:
                # Create sub-tabs for each available round
                round_labels = [f"Round {round_num}" for round_num in available_rounds]
                round_tabs = st.tabs(round_labels)

                # Display scorecard for each round in its own sub-tab
                for i, round_num in enumerate(available_rounds):
                    with round_tabs[i]:
                        try:
                            # Generate the round comparison HTML using existing function
                            scorecard_html = generate_round_comparison_html(teg_num, round_num)

                            # Display the scorecard
                            st.markdown(scorecard_html, unsafe_allow_html=True)

                        except Exception as round_error:
                            st.error(f"Error loading scorecard for Round {round_num}: {str(round_error)}")
                            logger.error(f"Error loading scorecard for TEG {teg_num} Round {round_num}: {str(round_error)}")


except Exception as e:
    # Comprehensive error handling for production stability
    st.error(f"An error occurred: {str(e)}")
    logger.error(f"An error occurred: {str(e)}", exc_info=True)

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
st.markdown("")
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)