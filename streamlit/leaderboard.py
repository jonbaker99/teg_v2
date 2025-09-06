import streamlit as st
import pandas as pd
from typing import List, Dict, Any
import logging
from utils import get_teg_rounds, get_round_data, load_all_data, load_datawrapper_css
from make_charts import create_cumulative_graph, adjusted_grossvp, adjusted_stableford
from leaderboard_utils import create_leaderboard, generate_table_html, format_value, get_champions, get_last_place, display_leaderboard


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
PAGE_TITLE = "Current Leaderboard"
MEASURES = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
PLAYER_COLUMN = 'Player'




# =========== CODE TO MAKE PAGE

load_datawrapper_css()

ex_teg_50 = True
if not ex_teg_50:
    st.markdown("# TEG 50 IS INCLUDED... BE CAREFUL")

if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

try:
    with st.spinner("Loading data..."):
        round_df = get_round_data(ex_50 = ex_teg_50)
        all_data = load_all_data(exclude_teg_50=ex_teg_50)
    
    #st.write(round_df)

    required_columns = [PLAYER_COLUMN, 'TEGNum', 'TEG', 'Round'] + MEASURES
    missing_columns = [col for col in required_columns if col not in round_df.columns]
    if missing_columns:
        st.error(f"Missing columns in data: {', '.join(missing_columns)}")
        logger.error(f"Missing columns in data: {', '.join(missing_columns)}")
        st.stop()

    teg_order = round_df[['TEG', 'TEGNum']].drop_duplicates().sort_values('TEGNum')
    tegs = teg_order['TEG'].tolist()

    if not tegs:
        st.warning("No TEGs available in the data.")
        st.stop()

    #chosen_teg = st.radio('Select TEG', tegs, horizontal=True)
    chosen_teg = all_data.loc[all_data['TEGNum'].idxmax(), 'TEG']

    leaderboard_df = round_df[round_df['TEG'] == chosen_teg]

    if leaderboard_df.empty:
        st.warning(f"No data available for {chosen_teg}.")
        st.stop()

    current_rounds = leaderboard_df['Round'].nunique()
    total_rounds = get_teg_rounds(chosen_teg)
    is_complete = current_rounds >= total_rounds

    page_header = f"{chosen_teg} Results" if is_complete else f"{chosen_teg} Scoreboard"
    leader_label = "Champion" if is_complete else "Leader"

    st.markdown('')

    # st.subheader(page_header)

    tab1, tab2 = st.tabs(["TEG Trophy & Spoon", "Green Jacket"])

    with tab1:

        display_leaderboard(
            leaderboard_df, 
            'Stableford', 
            f"{chosen_teg} Trophy Leaderboard (Best Stableford)",
            leader_label, 
            ascending=False
        )

        # st.divider()
        st.markdown('')

        cht_label = f'TEG Trophy race: {chosen_teg}'
        st.markdown(f'##### {cht_label}')

        # Create containers
        chart_container = st.container()
        radio_container = st.container()

        with radio_container:

            stableford_chart_type = st.radio(
                    "Choose Stableford chart type:",
                    ('Standard', 'Adjusted scale (score vs. net par)'),
                    key='stableford_chart_type',
                    index=1, #set adjusted to default
                    horizontal=True
                )
            st.caption("Adjusted view 'zooms in' by showing performance vs. net par to more clearly show gaps between players")

        # Create and display Stableford chart
        if stableford_chart_type == 'Standard':
            fig_stableford = create_cumulative_graph(all_data, chosen_teg, 'Stableford Cum TEG', 
                                                    f'Trophy race: {chosen_teg}',
                                                    y_axis_label='Cumulative Stableford Points',
                                                    chart_type='stableford')
            cht_label = f'Trophy race: {chosen_teg}'
            label_short = 'Cumulative stableford points'
        else:
            fig_stableford = create_cumulative_graph(all_data, chosen_teg, 'Adjusted Stableford', 
                                                    f'Trophy race (Adjusted scale): {chosen_teg}', 
                                                    y_calculation=adjusted_stableford,
                                                    y_axis_label='Cumulative Stableford Points vs. net par',
                                                    chart_type='stableford')
            cht_label = f'Trophy race (Adjusted scale): {chosen_teg}'
            label_short = 'Cumulative stableford points (adjusted scale)'

        with chart_container:
            # st.markdown(f'**{cht_label}**')
            st.caption(f'{label_short} | Higher = better')
            #st.plotly_chart(fig_stableford, use_container_width=True, config=dict({'staticPlot': True}))
            #st.plotly_chart(fig_stableford, use_container_width=True)
            st.plotly_chart(fig_stableford, use_container_width=True, config=dict({'displayModeBar': False}))

    with tab2: 
        display_leaderboard(
            leaderboard_df=leaderboard_df, 
            value_column='GrossVP', 
            title=f"{chosen_teg} Green Jacket Leaderboard (Best Gross)",
            # title="",
            leader_label=leader_label, 
            ascending=True
        )

        st.markdown('')
        # st.divider()

        cht_label = f'Green Jacket race: {chosen_teg}'
        st.markdown(f'##### {cht_label}')

        # Create containers
        chart_container = st.container()
        radio_container = st.container()

        with radio_container:
            grossvp_chart_type = st.radio(
                "Choose chart type:",
                ('Standard', 'Adjusted scale (gross score vs. bogey)'),
                key='grossvp_chart_type',
                index=1, #set adjusted to default
                horizontal=True
            )
            st.caption("Adjusted view 'zooms in' by showing performance vs. bogey golf to more clearly show gaps between players")
        
        # Create and display Green Jacket chart
        if grossvp_chart_type == 'Standard':
            fig_grossvp = create_cumulative_graph(all_data, chosen_teg, 'GrossVP Cum TEG', 
                                                f'Green Jacket race: {chosen_teg}',
                                                y_axis_label='Cumulative gross vs par',
                                                chart_type='gross')
            cht_label = f'Green Jacket race: {chosen_teg}'
            label_short = 'Cumulative gross score vs. par'
        else:
            fig_grossvp = create_cumulative_graph(all_data, chosen_teg, 'Adjusted GrossVP', 
                                                f'Green Jacket race (Adjusted scale): {chosen_teg}', 
                                                y_calculation=adjusted_grossvp,
                                                y_axis_label='Cumulative gross vs. bogey golf (par+1)',
                                                chart_type='gross')
            cht_label = f'Green Jacket race (Adjusted scale): {chosen_teg}'
            label_short = 'Cumulative gross score (adjusted scale vs. bogey)'

        
        with chart_container:
            #st.markdown(f'**{cht_label}**')
            st.caption(f'{label_short} | Lower = better')
            #st.plotly_chart(fig_grossvp, use_container_width=True, config=dict({'staticPlot': True}))
            st.plotly_chart(fig_grossvp, use_container_width=True, config=dict({'displayModeBar': False}))


except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    logger.error(f"An error occurred: {str(e)}", exc_info=True)

