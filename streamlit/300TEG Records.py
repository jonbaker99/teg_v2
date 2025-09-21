# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import get_ranked_teg_data, get_ranked_round_data, get_ranked_frontback_data, load_datawrapper_css

# Import display helper functions
from helpers.display_helpers import prepare_records_table


# === PAGE CONFIGURATION ===
st.title("TEG Records")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load ranked TEG data (complete TEGs only, excludes TEG 50)
tegs_ranked = get_ranked_teg_data()

# Load ranked round data (complete TEGs only, excludes TEG 50)
rounds_ranked = get_ranked_round_data()

# Load ranked 9-hole data (complete TEGs only, excludes TEG 50)
frontback_ranked = get_ranked_frontback_data()


# === TABBED RECORDS DISPLAY ===
tab1, tab2, tab3 = st.tabs(["Best TEGs", "Best Rounds", "Best 9s"])

with tab1:
    st.markdown("### TEG Records")
    teg_records_table = prepare_records_table(tegs_ranked, 'teg')
    st.write(
        teg_records_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd'
        ),
        unsafe_allow_html=True
    )

with tab2:
    st.markdown("### Round Records")
    round_records_table = prepare_records_table(rounds_ranked, 'round')
    st.write(
        round_records_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd'
        ),
        unsafe_allow_html=True
    )

with tab3:
    st.markdown("### 9-Hole Records")
    nine_records_table = prepare_records_table(frontback_ranked, 'frontback')
    st.write(
        nine_records_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd'
        ),
        unsafe_allow_html=True
    )