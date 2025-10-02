# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import get_ranked_teg_data, get_ranked_round_data, get_ranked_frontback_data, load_datawrapper_css, get_round_data, get_9_data, load_all_data

# Import display helper functions
from helpers.display_helpers import prepare_records_table, prepare_worst_records_table, prepare_streak_records_table, prepare_score_count_records_table
from helpers.worst_performance_processing import get_filtered_teg_data

# Import streak analysis functions
from helpers.streak_analysis_processing import prepare_record_best_streaks_data, prepare_record_worst_streaks_data


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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["TEG Records", "Round Records", "9-Hole Records", "Streaks", "Score Counts"])

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

with tab4:
    # Load data for streak records (excluding TEG 50 like other streak analysis)
    all_data = load_all_data(exclude_teg_50=True)

    # Best Streaks table
    best_streaks_data = prepare_record_best_streaks_data(all_data)
    best_streaks_table = prepare_streak_records_table(best_streaks_data, 'Best Streaks:')
    st.write(
        best_streaks_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
        ),
        unsafe_allow_html=True
    )

    # Worst Streaks table
    worst_streaks_data = prepare_record_worst_streaks_data(all_data)
    worst_streaks_table = prepare_streak_records_table(worst_streaks_data, 'Worst Streaks:')
    st.write(
        worst_streaks_table.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
        ),
        unsafe_allow_html=True
    )

with tab5:
    # Score Count Records
    best_score_counts, worst_score_counts = prepare_score_count_records_table(all_data)

    # Display best score counts
    if not best_score_counts.empty:
        st.write(
            best_score_counts.to_html(
                escape=False,
                index=False,
                justify='left',
                classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
            ),
            unsafe_allow_html=True
        )

    # Display worst score counts
    if not worst_score_counts.empty:
        st.write(
            worst_score_counts.to_html(
                escape=False,
                index=False,
                justify='left',
                classes='datawrapper-table bold-2nd left-4th left-3rd full-width records-table'
            ),
            unsafe_allow_html=True
        )

    # Caption explaining score count logic
    st.caption("Eagles, Birdies and Pars also include better scores")

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)