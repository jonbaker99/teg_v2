"""Streamlit page for analyzing final round comebacks and collapses.

This page explores dramatic final round performances in TEG tournaments, showing:
- Biggest final round score differentials (best and worst performances)
- Biggest leads lost by players leading after the penultimate round
- Biggest leads lost during the final round itself
- Biggest comebacks in the final round, regardless of whether the player won

The analysis works for both Gross (Green Jacket) and Stableford (Trophy) competitions.
"""

# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import load_all_data, read_file, load_datawrapper_css

# Import comeback analysis functions
from helpers.comeback_analysis import (
    calculate_final_round_differentials,
    calculate_biggest_leads_lost_after_r3,
    calculate_biggest_leads_lost_in_r4,
    calculate_biggest_comebacks
)

# === PAGE LAYOUT CONFIGURATION ===
from utils import get_page_layout
layout = get_page_layout(__file__)
st.set_page_config(layout=layout)

# === PAGE TITLE ===
st.title('Final Round Comebacks & Collapses')

# Load CSS styling for consistent table appearance
load_datawrapper_css()

# === DATA LOADING ===
with st.spinner("Loading data..."):
    # Load complete dataset (excludes TEG 50)
    all_scores = load_all_data(exclude_teg_50=True)

    # Load round info for TEG metadata
    round_info = read_file('data/round_info.csv')

# === USER INTERFACE ===
st.markdown("""
This page analyzes the most dramatic final round performances in TEG history,
looking at both amazing comebacks and heartbreaking collapses.
""")

# Competition selection
competition = st.radio(
    "Choose competition:",
    ["Gross (Green Jacket)", "Stableford (Trophy)"],
    horizontal=True
)

# Set measure based on selection
measure = 'GrossVP' if competition == "Gross (Green Jacket)" else 'Stableford'
measure_label = 'Gross vs Par' if measure == 'GrossVP' else 'Stableford Points'
better_direction = 'Lower is better' if measure == 'GrossVP' else 'Higher is better'

# Number of records to show
n_records = st.number_input(
    "Number of records to show in each section",
    min_value=1,
    max_value=20,
    value=5,
    step=1
)

st.markdown("---")

# === SECTION 1: BIGGEST FINAL ROUND DIFFERENTIALS ===
st.markdown(f"### 1. Best & Worst Final Rounds")
st.markdown(f"*Best and worst final round performances ({better_direction})*")

with st.spinner("Calculating final round differentials..."):
    differentials = calculate_final_round_differentials(all_scores, round_info, measure)

if not differentials.empty:
    # Best performances
    st.markdown(f"#### Best Final Round Performances")
    best_final_rounds = differentials.head(n_records).copy()

    # Format the display
    best_final_rounds['Rank After R3'] = best_final_rounds['Rank After R3'].astype(int).astype(str)
    best_final_rounds['Final Rank'] = best_final_rounds['Final Rank'].astype(int).astype(str)
    best_final_rounds['Final Round'] = best_final_rounds['Final Round'].astype(int)

    # Format scores based on measure
    if measure == 'GrossVP':
        best_final_rounds['Final Round Score'] = best_final_rounds['Final Round Score'].apply(
            lambda x: f"+{int(x)}" if x > 0 else (f"{int(x)}" if x < 0 else "=")
        )
        best_final_rounds['Total Score'] = best_final_rounds['Total Score'].apply(
            lambda x: f"+{int(x)}" if x > 0 else (f"{int(x)}" if x < 0 else "=")
        )
    else:
        best_final_rounds['Final Round Score'] = best_final_rounds['Final Round Score'].astype(int)
        best_final_rounds['Total Score'] = best_final_rounds['Total Score'].astype(int)

    st.write(
        best_final_rounds.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table'
        ),
        unsafe_allow_html=True
    )

    # Worst performances (all players)
    st.markdown(f"#### Worst Final Round Performances")
    worst_final_rounds = differentials.tail(n_records).iloc[::-1].copy()

    # Format the display
    worst_final_rounds['Rank After R3'] = worst_final_rounds['Rank After R3'].astype(int).astype(str)
    worst_final_rounds['Final Rank'] = worst_final_rounds['Final Rank'].astype(int).astype(str)
    worst_final_rounds['Final Round'] = worst_final_rounds['Final Round'].astype(int)

    # Format scores based on measure
    if measure == 'GrossVP':
        worst_final_rounds['Final Round Score'] = worst_final_rounds['Final Round Score'].apply(
            lambda x: f"+{int(x)}" if x > 0 else (f"{int(x)}" if x < 0 else "=")
        )
        worst_final_rounds['Total Score'] = worst_final_rounds['Total Score'].apply(
            lambda x: f"+{int(x)}" if x > 0 else (f"{int(x)}" if x < 0 else "=")
        )
    else:
        worst_final_rounds['Final Round Score'] = worst_final_rounds['Final Round Score'].astype(int)
        worst_final_rounds['Total Score'] = worst_final_rounds['Total Score'].astype(int)

    st.write(
        worst_final_rounds.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table'
        ),
        unsafe_allow_html=True
    )

    # Worst performances by leaders
    st.markdown(f"### Worst Final Round Performances by Leaders")
    st.caption("Leaders going into the final round (Rank After R3 = 1)")

    # Filter for leaders only
    leaders_only = differentials[differentials['Rank After R3'] == 1.0].copy()

    if not leaders_only.empty:
        # Sort by final round score (worst first)
        leaders_only = leaders_only.sort_values('Final Round Score', ascending=not (measure == 'GrossVP'))
        # worst_leaders = leaders_only.tail(n_records).iloc[::-1].copy() if measure == 'GrossVP' else leaders_only.head(n_records).copy()
        worst_leaders = leaders_only.head(n_records).copy()

        # Format the display
        worst_leaders['Rank After R3'] = worst_leaders['Rank After R3'].astype(int).astype(str)
        worst_leaders['Final Rank'] = worst_leaders['Final Rank'].astype(int).astype(str)
        worst_leaders['Final Round'] = worst_leaders['Final Round'].astype(int)

        # Format scores based on measure
        if measure == 'GrossVP':
            worst_leaders['Final Round Score'] = worst_leaders['Final Round Score'].apply(
                lambda x: f"+{int(x)}" if x > 0 else (f"{int(x)}" if x < 0 else "=")
            )
            worst_leaders['Total Score'] = worst_leaders['Total Score'].apply(
                lambda x: f"+{int(x)}" if x > 0 else (f"{int(x)}" if x < 0 else "=")
            )
        else:
            worst_leaders['Final Round Score'] = worst_leaders['Final Round Score'].astype(int)
            worst_leaders['Total Score'] = worst_leaders['Total Score'].astype(int)

        st.write(
            worst_leaders.to_html(
                escape=False,
                index=False,
                justify='left',
                classes='datawrapper-table'
            ),
            unsafe_allow_html=True
        )
    else:
        st.info("No leader data available")

else:
    st.info(f"No data available for {competition}")

st.markdown("---")

# === SECTION 2: BIGGEST LEADS LOST (AFTER R3) ===
st.markdown(f"## 2. Biggest Leads Lost Going Into Final Round")
st.markdown("*Leaders after the penultimate round who didn't win*")

with st.spinner("Calculating leads lost after R3..."):
    leads_lost_r3 = calculate_biggest_leads_lost_after_r3(all_scores, round_info, measure)

if not leads_lost_r3.empty:
    display_leads_r3 = leads_lost_r3.head(n_records).copy()

    # Format gap column
    if measure == 'GrossVP':
        display_leads_r3['Gap to 2nd'] = display_leads_r3['Gap to 2nd'].apply(
            lambda x: f"+{x:.0f}" if x > 0 else f"{x:.0f}"
        )
    else:
        display_leads_r3['Gap to 2nd'] = display_leads_r3['Gap to 2nd'].apply(lambda x: f"{x:.0f}")

    display_leads_r3['Leader Final Position'] = display_leads_r3['Leader Final Position'].astype(int).astype(str)

    st.write(
        display_leads_r3.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table'
        ),
        unsafe_allow_html=True
    )
else:
    st.info(f"No leads lost after R3 found for {competition}")

st.markdown("---")

# === SECTION 3: BIGGEST LEADS LOST DURING R4 ===
st.markdown(f"## 3. Biggest Leads Lost During Final Round")
st.markdown("*Maximum lead held during the final round by players who didn't win*")

with st.spinner("Calculating leads lost during R4..."):
    leads_lost_r4 = calculate_biggest_leads_lost_in_r4(all_scores, round_info, measure)

if not leads_lost_r4.empty:
    display_leads_r4 = leads_lost_r4.head(n_records).copy()

    # Format numeric columns
    if measure == 'GrossVP':
        display_leads_r4['Max Lead in R4'] = display_leads_r4['Max Lead in R4'].apply(
            lambda x: f"+{x:.0f}" if x > 0 else f"{x:.0f}"
        )
        display_leads_r4['Final Gap'] = display_leads_r4['Final Gap'].apply(
            lambda x: f"+{x:.0f}" if x > 0 else f"{x:.0f}"
        )
    else:
        display_leads_r4['Max Lead in R4'] = display_leads_r4['Max Lead in R4'].apply(lambda x: f"{x:.0f}")
        display_leads_r4['Final Gap'] = display_leads_r4['Final Gap'].apply(lambda x: f"{x:.0f}")

    display_leads_r4['Hole of Max Lead'] = display_leads_r4['Hole of Max Lead'].astype(int).astype(str)

    st.write(
        display_leads_r4.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table'
        ),
        unsafe_allow_html=True
    )
else:
    st.info(f"No leads lost during R4 found for {competition}")

st.markdown("---")

# === SECTION 4: BIGGEST COMEBACKS ===
st.markdown(f"## 4. Biggest Comebacks in Final Round")
st.markdown("*Largest improvements from position after R3, regardless of winning*")

with st.spinner("Calculating biggest comebacks..."):
    comebacks = calculate_biggest_comebacks(all_scores, round_info, measure)

if not comebacks.empty:
    display_comebacks = comebacks.head(n_records).copy()

    # Format numeric columns
    if measure == 'GrossVP':
        display_comebacks['Gap After R3'] = display_comebacks['Gap After R3'].apply(
            lambda x: f"+{x:.0f}" if x > 0 else (f"{x:.0f}" if x < 0 else "=")
        )
        display_comebacks['Player R4 Score'] = display_comebacks['Player R4 Score'].apply(
            lambda x: f"+{x:.0f}" if x > 0 else (f"{x:.0f}" if x < 0 else "=")
        )
        display_comebacks['Leader R4 Score'] = display_comebacks['Leader R4 Score'].apply(
            lambda x: f"+{x:.0f}" if x > 0 else (f"{x:.0f}" if x < 0 else "=")
        )
        display_comebacks['Gap Closed'] = display_comebacks['Gap Closed'].apply(
            lambda x: f"+{x:.0f}" if x > 0 else f"{x:.0f}"
        )
    else:
        display_comebacks['Gap After R3'] = display_comebacks['Gap After R3'].apply(lambda x: f"{x:.0f}")
        display_comebacks['Player R4 Score'] = display_comebacks['Player R4 Score'].apply(lambda x: f"{x:.0f}")
        display_comebacks['Leader R4 Score'] = display_comebacks['Leader R4 Score'].apply(lambda x: f"{x:.0f}")
        display_comebacks['Gap Closed'] = display_comebacks['Gap Closed'].apply(lambda x: f"{x:.0f}")

    display_comebacks['Final Position'] = display_comebacks['Final Position'].astype(int).astype(str)

    st.write(
        display_comebacks.to_html(
            escape=False,
            index=False,
            justify='left',
            classes='datawrapper-table'
        ),
        unsafe_allow_html=True
    )
else:
    st.info(f"No comeback data available for {competition}")

# === NOTES ===
st.markdown("---")
st.caption("""
**Notes:**
- Analysis excludes TEG 2 (only had 3 rounds)
- Stableford analysis only includes TEG 6 onwards (when Stableford was introduced)
- "Gap Closed" shows improvement in position relative to leader/winner
- All gaps are calculated as absolute differences in scoring
""")

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)
