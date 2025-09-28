# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import get_ranked_teg_data, get_ranked_round_data, get_ranked_frontback_data, load_datawrapper_css, get_round_data, get_9_data

# Import display helper functions
from helpers.display_helpers import prepare_records_table, prepare_worst_records_table
from helpers.worst_performance_processing import get_filtered_teg_data


# === PAGE CONFIGURATION ===
st.title("TEG Records")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load ranked data for best records (complete TEGs only, excludes TEG 50)
tegs_ranked = get_ranked_teg_data()
rounds_ranked = get_ranked_round_data()
frontback_ranked = get_ranked_frontback_data()

# Load data for worst records
teg_data = get_filtered_teg_data()  # Excludes TEG 2
round_data = get_round_data()
frontback_data = get_9_data()


# === TABBED RECORDS DISPLAY ===
tab1, tab2, tab3 = st.tabs(["TEG Records", "Round Records", "9-Hole Records"])

with tab1:
    teg_records_table = prepare_records_table(tegs_ranked, 'teg')
    st.write(
        teg_records_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
        ),
        unsafe_allow_html=True
    )

    teg_worst_table = prepare_worst_records_table(teg_data, 'teg')
    st.write(
        teg_worst_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
        ),
        unsafe_allow_html=True
    )

with tab2:
    round_records_table = prepare_records_table(rounds_ranked, 'round')
    st.write(
        round_records_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
        ),
        unsafe_allow_html=True
    )

    round_worst_table = prepare_worst_records_table(round_data, 'round')
    st.write(
        round_worst_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
        ),
        unsafe_allow_html=True
    )

with tab3:
    nine_records_table = prepare_records_table(frontback_ranked, 'frontback')
    st.write(
        nine_records_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
        ),
        unsafe_allow_html=True
    )

    nine_worst_table = prepare_worst_records_table(frontback_data, 'frontback')
    st.write(
        nine_worst_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
        ),
        unsafe_allow_html=True
    )

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)