import os
import streamlit as st
from pathlib import Path
from streamlit_extras.stylable_container import stylable_container
import sys
sys.path.append(str(Path(__file__).parent))
from utils import has_incomplete_teg_fast


st.markdown(
    """
    <style>
    /* Keep for sidebar layout */
    [data-testid="stSidebar"]::before {
        content: "The El Golfo";
        display: block;
        font-size: 1.8rem;
        font-weight: bold;
        padding: 0.6rem 1rem 0.2rem 1rem;
        color: var(--text-color);
        font-family: var(--font);
    }

    /* TOP NAV: layout + spacing */
    [data-testid="stToolbar"] {
        display: flex;              /* ensure single row */
        align-items: center;
        flex-wrap: nowrap;          /* prevent wrapping */
        padding-left: 0.75rem;      /* small left padding */
        gap: 1rem;                  /* space between title and nav */
    }

    /* TOP NAV: title */
    [data-testid="stToolbar"]::before {
        content: "The El Golfo";
        font-size: 1.6rem;
        font-weight: bold;
        line-height: 1;
        white-space: nowrap;        /* keep on one line */
        color: var(--text-color);
        font-family: var(--font);
    }

    /* Hide titles on small screens */
    @media (max-width: 640px) {
        [data-testid="stSidebar"]::before,
        [data-testid="stToolbar"]::before {
            display: none;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)



# home_page = st.Page("home.py", title="Home")
honours_page = st.Page("101TEG Honours Board.py", title="TEG Honours Board", icon=":material/trophy:")
history_page = st.Page("101TEG History.py", title="TEG History", icon=":material/lists:")
results_page = st.Page("102TEG Results.py", title="Detailed TEG Results", icon=":material/sports_score:")
player_ranking_page = st.Page("player_history.py", title="Rankings by TEG by Player", icon=":material/123:")
pb_page = st.Page("302Personal Best Rounds & TEGs.py", title="Personal Bests", icon=":material/golf_course:") 
records_page = st.Page("300TEG Records.py", title="TEG Records", icon=":material/military_tech:") 
 
hc_page = st.Page("500Handicaps.py", title="Handicaps", icon=":material/accessible:") 
latest_rd_page = st.Page("latest_round.py", title="Latest Round in context", icon=":material/sports_golf:")
latest_teg_page = st.Page("latest_teg_context.py", title="Latest TEG in context", icon=":material/sports_golf:")
top_pages = st.Page("301Best_TEGs_and_Rounds.py", title="Top TEGs and Rounds", icon=":material/social_leaderboard:")
scoring_pg = st.Page("400scoring.py", title="Scoring", icon=":material/strategy:")
birdies_pg = st.Page("birdies_etc.py", title="Eagles / Birdies / Pars", icon=":material/strategy:")
streaks_pg = st.Page("streaks.py", title="Streaks", icon=":material/trending_up:")
bypar_pg = st.Page("ave_by_par.py", title="Average by par", icon=":material/strategy:")
byteg_pg = st.Page("ave_by_teg.py", title="Average by TEG", icon=":material/strategy:")
course_ave_pg = st.Page("ave_by_course.py", title="Course averages and records", icon=":material/strategy:")
course_rds_pg = st.Page("score_by_course.py", title="All rounds", icon=":material/strategy:")
data_pg = st.Page("1000Data update.py", title="Data update", icon=":material/update:")
data_edit_pg = st.Page("data_edit.py", title="Data edit", icon=":material/edit:")
delete_pg = st.Page("delete_data.py", title="Delete data", icon=":material/skull:")
leaderboard_pg = st.Page("leaderboard.py", title="Latest Leaderboard", icon=":material/leaderboard:")
scorecard_pg = st.Page("scorecard_v2.py", title="Scorecard", icon=":material/leaderboard:")
scorecard_mob_pg = st.Page("scorecard_v2_mobile.py", title="Scorecard (mobile)", icon=":material/leaderboard:")
sc_count_pg = st.Page("sc_count.py", title="Scoring distributions", icon=":material/strategy:")
bestball_pg = st.Page("bestball.py", title="Bestball and worstball", icon=":material/strategy:")
changes_pg = st.Page("biggest_changes.py", title="Changes vs previous round", icon=":material/strategy:")
eclectic_pg = st.Page("eclectic.py", title="Eclectic Scores", icon=":material/golf_course:")
eclectic_records_pg = st.Page("best_eclectics.py", title="Eclectic Records", icon=":material/emoji_events:")
data_test_pg = st.Page("data_test_temp.py", title="TEMP DATA TESTING", icon=":material/check_circle:")
data_management_pg = st.Page("admin_volume_management.py", title="Data volume management", icon=":material/check_circle:")



# Check if there are incomplete TEGs to determine navigation structure
try:
    has_incomplete_teg = has_incomplete_teg_fast()
except:
    # If there's any error checking for incomplete TEGs, default to no incomplete TEG
    has_incomplete_teg = False

# Build navigation structure based on TEG status
if has_incomplete_teg:
    # If TEG is in progress, show "Current TEG" section first
    nav_structure = {
        #"Home": [home_page],
        "Current TEG": [leaderboard_pg, latest_rd_page, latest_teg_page,scorecard_pg, scorecard_mob_pg, hc_page],
        "History": [history_page, honours_page, results_page, player_ranking_page],
        "Records & PBs": [records_page, pb_page, top_pages],
        # "Scorecards": [scorecard_pg, scorecard_mob_pg],
        "Scoring analysis": [birdies_pg, streaks_pg, course_ave_pg,  bypar_pg, sc_count_pg,byteg_pg,  changes_pg, course_rds_pg],
        "Bestballs / Eclectics": [bestball_pg, eclectic_pg, eclectic_records_pg],
        #"Players": [players_pg],
        "Data":[data_pg, data_edit_pg, delete_pg, data_test_pg, data_management_pg]
    }
else:
    # If no TEG in progress, use original structure with "Latest TEG" at the end
    nav_structure = {
        #"Home": [home_page],
        "History": [history_page, honours_page, results_page, player_ranking_page],
        "Records & PBs": [records_page, pb_page, top_pages],
        "Scorecards": [scorecard_pg, scorecard_mob_pg],
        "Scoring analysis": [birdies_pg, streaks_pg, course_ave_pg,  bypar_pg, sc_count_pg,byteg_pg,  changes_pg, course_rds_pg],
        # "Course scoring" :[course_ave_pg, course_rds_pg] ,
        "Bestballs / Eclectics": [bestball_pg, eclectic_pg, eclectic_records_pg],
        #"Players": [players_pg],
        "Latest TEG": [leaderboard_pg, latest_rd_page, latest_teg_page, hc_page],
        "Data":[data_pg, data_edit_pg, delete_pg, data_test_pg, data_management_pg]
    }

pg = st.navigation(nav_structure, position='top')

pg.run()