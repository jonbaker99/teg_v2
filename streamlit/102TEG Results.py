# === IMPORTS ===
import streamlit as st
import pandas as pd
from typing import List, Dict, Any
import logging

# Import data loading functions from main utils
from utils import get_teg_rounds, get_round_data, load_all_data, load_datawrapper_css

# Import chart creation functions
from make_charts import create_cumulative_graph, adjusted_grossvp, adjusted_stableford

# Import leaderboard display functions (shared utilities)
from leaderboard_utils import create_leaderboard, generate_table_html, format_value, get_champions, get_last_place, display_leaderboard, display_net_leaderboard

# Import scorecard generation functions
from scorecard_utils import generate_round_comparison_html, load_scorecard_css


# === CONFIGURATION ===
# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page constants
PAGE_TITLE = "TEG Results"
PAGE_ICON = "⛳"
MEASURES = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
PLAYER_COLUMN = 'Player'


# === DATA LOADING ===
# Load CSS styling for consistent table appearance
load_datawrapper_css()

# Load scorecard CSS styling for the scorecards tab
load_scorecard_css()

# # Add sidebar refresh button for data updates
# if st.sidebar.button("Refresh Data"):
#     st.cache_data.clear()
#     st.rerun()

try:
    with st.spinner("Loading data..."):
        # Load round-level data (includes incomplete TEGs for tournament selection)
        # Purpose: User needs to select from all available tournaments, including in-progress ones
        round_df = get_round_data()
        
        # Load complete dataset for chart generation
        # Purpose: Charts need full hole-by-hole data to show cumulative progress
        all_data = load_all_data()

    # === DATA VALIDATION ===
    # Verify required columns exist in the dataset
    required_columns = [PLAYER_COLUMN, 'TEGNum', 'TEG', 'Round'] + MEASURES
    missing_columns = [col for col in required_columns if col not in round_df.columns]
    if missing_columns:
        st.error(f"Missing columns in data: {', '.join(missing_columns)}")
        logger.error(f"Missing columns in data: {', '.join(missing_columns)}")
        st.stop()

    # Prepare tournament selection list
    teg_order = round_df[['TEG', 'TEGNum']].drop_duplicates().sort_values('TEGNum')
    tegs = teg_order['TEG'].tolist()

    if not tegs:
        st.warning("No TEGs available in the data.")
        st.stop()

    # === USER INTERFACE ===
    
    # Tournament selection radio buttons
    # Default to most recent tournament (last in list)
    chosen_teg = st.radio('Select TEG', tegs, horizontal=True, index=len(tegs)-1)

    # Filter data for selected tournament
    leaderboard_df = round_df[round_df['TEG'] == chosen_teg]

    if leaderboard_df.empty:
        st.warning(f"No data available for {chosen_teg}.")
        st.stop()

    # === TOURNAMENT STATUS DETERMINATION ===
    # Determine if tournament is complete or in progress
    current_rounds = leaderboard_df['Round'].nunique()
    total_rounds = get_teg_rounds(chosen_teg)  # Get expected rounds for this TEG
    is_complete = current_rounds >= total_rounds

    # Set appropriate labels based on tournament status
    page_header = f"{chosen_teg} Results" if is_complete else f"{chosen_teg} Scoreboard"
    leader_label = "Champion" if is_complete else "Leader"

    st.markdown('')  # Add spacing

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

        st.markdown('')  # Add spacing between sections

        # Chart section header
        cht_label = f'TEG Trophy race: {chosen_teg}'
        st.markdown(f'##### {cht_label}')

        # Create containers for better layout control
        chart_container = st.container()
        radio_container = st.container()

        # Chart type selection controls
        with radio_container:
            stableford_chart_type = st.radio(
                "Choose Stableford chart type:",
                ('Standard', 'Adjusted scale (score vs. net par)'),
                key='stableford_chart_type',
                index=1,  # Default to adjusted scale for better visualization
                horizontal=True
            )
            st.caption("Adjusted view 'zooms in' by showing performance vs. net par to more clearly show gaps between players")

        # Chart generation based on user selection
        if stableford_chart_type == 'Standard':
            # create_cumulative_graph() - Generates interactive Plotly chart showing cumulative progress
            fig_stableford = create_cumulative_graph(
                all_data, chosen_teg, 'Stableford Cum TEG', 
                f'Trophy race: {chosen_teg}',
                y_axis_label='Cumulative Stableford Points',
                chart_type='stableford'
            )
            cht_label = f'Trophy race: {chosen_teg}'
            label_short = 'Cumulative stableford points'
        else:
            # Adjusted scale chart uses different calculation for better visualization
            fig_stableford = create_cumulative_graph(
                all_data, chosen_teg, 'Adjusted Stableford', 
                f'Trophy race (Adjusted scale): {chosen_teg}', 
                y_calculation=adjusted_stableford,  # Custom calculation function
                y_axis_label='Cumulative Stableford Points vs. net par',
                chart_type='stableford'
            )
            cht_label = f'Trophy race (Adjusted scale): {chosen_teg}'
            label_short = 'Cumulative stableford points (adjusted scale)'

        # Display the chart
        with chart_container:
            st.caption(f'{label_short} | Higher = better')
            # st.plotly_chart() - Renders interactive chart with disabled toolbar for cleaner appearance
            st.plotly_chart(fig_stableford, use_container_width=True, config=dict({'displayModeBar': False}))
        

    # === GREEN JACKET TAB (GROSS SCORE COMPETITION) ===
    with tab2: 
        
        # display_leaderboard() - Shows formatted leaderboard for gross scores
        display_leaderboard(
            leaderboard_df=leaderboard_df, 
            value_column='GrossVP', 
            title=f"{chosen_teg} Green Jacket Leaderboard (Best Gross)",
            leader_label=leader_label, 
            ascending=True  # Lower gross scores are better
        )

        st.markdown('')  # Add spacing between sections

        # Chart section header
        cht_label = f'Green Jacket race: {chosen_teg}'
        st.markdown(f'##### {cht_label}')

        # Create containers for better layout control
        chart_container = st.container()
        radio_container = st.container()

        # Chart type selection controls
        with radio_container:
            grossvp_chart_type = st.radio(
                "Choose chart type:",
                ('Standard', 'Adjusted scale (gross score vs. bogey)'),
                key='grossvp_chart_type',
                index=1,  # Default to adjusted scale for better visualization
                horizontal=True
            )
            st.caption("Adjusted view 'zooms in' by showing performance vs. bogey golf to more clearly show gaps between players")
        
        # Chart generation based on user selection
        if grossvp_chart_type == 'Standard':
            # create_cumulative_graph() - Standard cumulative gross vs par chart
            fig_grossvp = create_cumulative_graph(
                all_data, chosen_teg, 'GrossVP Cum TEG', 
                f'Green Jacket race: {chosen_teg}',
                y_axis_label='Cumulative gross vs par',
                chart_type='gross'
            )
            cht_label = f'Green Jacket race: {chosen_teg}'
            label_short = 'Cumulative gross score vs. par'
        else:
            # Adjusted scale shows performance vs bogey golf for better comparison
            fig_grossvp = create_cumulative_graph(
                all_data, chosen_teg, 'Adjusted GrossVP', 
                f'Green Jacket race (Adjusted scale): {chosen_teg}', 
                y_calculation=adjusted_grossvp,  # Custom calculation function
                y_axis_label='Cumulative gross vs. bogey golf (par+1)',
                chart_type='gross'
            )
            cht_label = f'Green Jacket race (Adjusted scale): {chosen_teg}'
            label_short = 'Cumulative gross score (adjusted scale vs. bogey)'

        # Display the chart
        with chart_container:
            st.caption(f'{label_short} | Lower = better')
            # st.plotly_chart() - Renders interactive chart with disabled toolbar
            st.plotly_chart(fig_grossvp, use_container_width=True, config=dict({'displayModeBar': False}))

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
            # Get available rounds for this TEG
            available_rounds = sorted(leaderboard_df['Round'].unique())

            if not available_rounds:
                st.warning(f"No round data available for {chosen_teg}")
            else:
                # Create sub-tabs for each round
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