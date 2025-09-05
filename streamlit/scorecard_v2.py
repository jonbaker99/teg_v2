import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

from utils import load_all_data, get_scorecard_data, get_teg_metadata, format_date_for_scorecard
from scorecard_utils import (
    load_scorecard_css,
    generate_single_round_html, 
    generate_tournament_html,
    generate_round_comparison_html
)


# Load data for dropdowns
all_data = load_all_data(exclude_incomplete_tegs=False)

# Load CSS
css_loaded = load_scorecard_css()

st.title('Scorecards')

if not css_loaded:
    st.warning("CSS not loaded - scorecard will not display correctly")


# Create tabs with session state persistence
if 'active_scorecard_tab' not in st.session_state:
    st.session_state.active_scorecard_tab = 0

with st.expander("Scorecard selection", expanded=True):
    tab_names = ["1 Round / All Players", "1 Player / All Rounds", "1 Round / 1 Player"]

    # Display names
    display_names = ["Round Comparison (all players)", "Tournament view (one player)", "Single Player Round"]

    selected_tab_display  = st.radio("Choose scorecard type:", display_names, 
                        horizontal=False,
                        key='scorecard_tab_selector')

    selected_tab = tab_names[display_names.index(selected_tab_display)]



    # Page-level controls
    # st.markdown("---")
    st.caption("Scorecard selection")
    col1, col2, col3 = st.columns(3)

    with col1:
        pl_options = sorted(all_data['Pl'].unique())
        selected_pl = st.selectbox('Player', pl_options, 
                                disabled=(selected_tab == "1 Round / All Players"),
                                key='page_player')

    with col2:
        tegnum_options = sorted(all_data['TEGNum'].unique())
        selected_tegnum = st.selectbox('Tournament', tegnum_options, 
                                    index=len(tegnum_options)-1,
                                    key='page_tegnum')

    with col3:
        round_options = sorted(all_data[all_data['TEGNum'] == selected_tegnum]['Round'].unique())
        selected_round = st.selectbox('Round', round_options,
                                    disabled=(selected_tab == "1 Player / All Rounds"),
                                    index=len(round_options)-1,
                                    key='page_round')

# st.markdown("---")

# Tab 1: Single Round (existing functionality)
if selected_tab == "1 Round / 1 Player":
    # Filter data
    rd_data = get_scorecard_data(selected_tegnum, selected_round, selected_pl)

    
    if len(rd_data) == 0:
        st.error("No data found for the selected round")
    else:
        # Prepare data
        output_cols = ['Hole', 'PAR', 'SI', 'HCStrokes', 'Sc', 'GrossVP', 'NetVP', 'Stableford']
        output_data = rd_data[output_cols].copy()
        
        def to_int_or_zero(x):
            if pd.isna(x):
                return 0
            return int(x)
        
        numeric_columns = output_data.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_columns:
            output_data[col] = output_data[col].map(to_int_or_zero)
        
        if len(output_data) == 18:
            scorecard_html = generate_single_round_html(selected_pl, selected_tegnum, selected_round)
            st.markdown(scorecard_html, unsafe_allow_html=True)
        else:
            st.error(f"Expected 18 holes, found {len(output_data)} holes for this round.")

# Tab 2: Tournament View
elif selected_tab == "1 Player / All Rounds":
    # Filter data for selected player and tournament
    tournament_data = get_scorecard_data(selected_tegnum, player_code=selected_pl)

    
    if len(tournament_data) == 0:
        st.error("No data found for the selected player and tournament.")
    else:
        # Get player name and TEG name
        player_name = tournament_data['Player'].iloc[0]
        teg_name = f"TEG {selected_tegnum}"
        
        # Generate tournament view
        tournament_html = generate_tournament_html(selected_pl, selected_tegnum)
        st.markdown(tournament_html, unsafe_allow_html=True)

# Tab 3: Round Comparison
elif selected_tab == "1 Round / All Players":
    # Filter data for selected tournament and round
    comparison_data = get_scorecard_data(selected_tegnum, selected_round)
    
    if len(comparison_data) == 0:
        st.error("No data found for the selected tournament and round.")
    else:
        teg_name = f"TEG {selected_tegnum}"
        
        # Generate round comparison view
        comparison_html = generate_round_comparison_html(selected_tegnum, selected_round)
        st.markdown(comparison_html, unsafe_allow_html=True)