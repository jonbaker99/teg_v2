# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import get_round_data, get_9_data, load_datawrapper_css

# Import display helper functions
from helpers.display_helpers import prepare_worst_records_table
from helpers.worst_performance_processing import get_filtered_teg_data


# === PAGE CONFIGURATION ===
st.title("TEG Worsts")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load TEG data excluding TEG 2 for meaningful worst performance analysis
teg_data = get_filtered_teg_data()

# Load round data for worst round analysis
round_data = get_round_data()

# Load 9-hole data for worst 9-hole segment analysis
frontback_data = get_9_data()


# === TABBED WORST RECORDS DISPLAY ===
tab1, tab2, tab3 = st.tabs(["Worst TEGs", "Worst Rounds", "Worst 9s"])

with tab1:
    st.markdown("### TEG Worst Records")
    teg_worst_table = prepare_worst_records_table(teg_data, 'teg')
    st.write(
        teg_worst_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd'
        ),
        unsafe_allow_html=True
    )
    st.caption('Excludes TEG 2')

with tab2:
    st.markdown("### Round Worst Records")
    round_worst_table = prepare_worst_records_table(round_data, 'round')
    st.write(
        round_worst_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd'
        ),
        unsafe_allow_html=True
    )

with tab3:
    st.markdown("### 9-Hole Worst Records")
    nine_worst_table = prepare_worst_records_table(frontback_data, 'frontback')
    st.write(
        nine_worst_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd'
        ),
        unsafe_allow_html=True
    )