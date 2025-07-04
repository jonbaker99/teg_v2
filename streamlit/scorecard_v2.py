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

st.title('Scorecard v2 - Enhanced Visual Design')

if not css_loaded:
    st.warning("CSS not loaded - scorecard may not display correctly")


# Create tabs
tab1, tab2, tab3 = st.tabs(["Single Round", "Tournament View", "Round Comparison"])

# Tab 1: Single Round (existing functionality)
with tab1:
    st.markdown('**Select round to view enhanced scorecard**')
    
    # Create dropdowns
    pl_options = sorted(all_data['Pl'].unique())
    default_pl = pl_options[0] if pl_options else None
    
    tegnum_options = sorted(all_data['TEGNum'].unique())
    default_tegnum = max(tegnum_options) if tegnum_options else None
    
    def get_max_round(tegnum):
        return all_data[all_data['TEGNum'] == tegnum]['Round'].max()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_pl = st.selectbox('Select Player', pl_options, index=pl_options.index(default_pl), key='tab1_player')
    
    with col2:    
        selected_tegnum = st.selectbox('Select TEGNum', tegnum_options, index=tegnum_options.index(default_tegnum), key='tab1_teg')
    
    with col3:
        max_round = get_max_round(selected_tegnum)
        round_options = sorted(all_data[all_data['TEGNum'] == selected_tegnum]['Round'].unique())
        selected_round = st.selectbox('Select Round', round_options, index=round_options.index(max_round) if max_round in round_options else 0, key='tab1_round')
    
    # Filter data
    rd_data = get_scorecard_data(selected_tegnum, selected_round, selected_pl)

    
    if len(rd_data) == 0:
        st.error("No data found for the selected criteria.")
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
with tab2:
    st.markdown('**Select player and tournament to view all rounds**')
    
    col1, col2 = st.columns(2)
    
    with col1:
        pl_options_t2 = sorted(all_data['Pl'].unique())
        selected_pl_t2 = st.selectbox('Select Player', pl_options_t2, key='tab2_player')
    
    with col2:
        tegnum_options_t2 = sorted(all_data['TEGNum'].unique())
        selected_tegnum_t2 = st.selectbox('Select Tournament', tegnum_options_t2, index=len(tegnum_options_t2)-1, key='tab2_teg')
    
    # Filter data for selected player and tournament
    tournament_data = get_scorecard_data(selected_tegnum_t2, player_code=selected_pl_t2)

    
    if len(tournament_data) == 0:
        st.error("No data found for the selected player and tournament.")
    else:
        # Get player name and TEG name
        player_name = tournament_data['Player'].iloc[0]
        teg_name = f"TEG {selected_tegnum_t2}"
        
        # Generate tournament view
        tournament_html = generate_tournament_html(selected_pl_t2, selected_tegnum_t2)
        st.markdown(tournament_html, unsafe_allow_html=True)

# Tab 3: Round Comparison
with tab3:
    st.markdown('**Select tournament and round to compare all players**')
    
    col1, col2 = st.columns(2)
    
    with col1:
        tegnum_options_t3 = sorted(all_data['TEGNum'].unique())
        selected_tegnum_t3 = st.selectbox('Select Tournament', tegnum_options_t3, index=len(tegnum_options_t3)-1, key='tab3_teg')
    
    with col2:
        round_options_t3 = sorted(all_data[all_data['TEGNum'] == selected_tegnum_t3]['Round'].unique())
        selected_round_t3 = st.selectbox('Select Round', round_options_t3, index=len(round_options_t3)-1, key='tab3_round')
    
    # Filter data for selected tournament and round
    comparison_data = get_scorecard_data(selected_tegnum_t3, selected_round_t3)
    
    if len(comparison_data) == 0:
        st.error("No data found for the selected tournament and round.")
    else:
        teg_name = f"TEG {selected_tegnum_t3}"
        
        # Generate round comparison view
        comparison_html = generate_round_comparison_html(selected_tegnum_t3, selected_round_t3)
        st.markdown(comparison_html, unsafe_allow_html=True)