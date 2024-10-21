import os
import streamlit as st
from pathlib import Path
from streamlit_extras.stylable_container import stylable_container


import streamlit as st

home_page = st.Page("home.py", title="Home")
history_page = st.Page("101TEG History.py", title="TEG History", icon=":material/trophy:")
results_page = st.Page("102TEG Results.py", title="TEG Results", icon=":material/sports_score:")
pb_page = st.Page("302Personal Best Rounds & TEGs.py", title="Personal Bests", icon=":material/golf_course:") 
records_page = st.Page("300TEG Records.py", title="TEG Records", icon=":material/military_tech:") 
worsts_page = st.Page("teg_worsts.py", title="TEG Worsts", icon=":material/sentiment_sad:") 
hc_page = st.Page("500Handicaps.py", title="Handicaps", icon=":material/accessible:") 
latest_rd_page = st.Page("latest_round.py", title="Latest Round in context", icon=":material/sports_golf:")
latest_teg_page = st.Page("latest_teg_context.py", title="Latest TEG in context", icon=":material/sports_golf:")
top_pages = st.Page("301Best_TEGs_and_Rounds.py", title="Best TEGs and Rounds", icon=":material/social_leaderboard:")
scoring_pg = st.Page("400scoring.py", title="Scoring", icon=":material/strategy:")
birdies_pg = st.Page("birdies_etc.py", title="Eagles / Birdies / Pars", icon=":material/strategy:")
bypar_pg = st.Page("ave_by_par.py", title="Average by par", icon=":material/strategy:")
byteg_pg = st.Page("ave_by_teg.py", title="Average by TEG", icon=":material/strategy:")
course_ave_pg = st.Page("ave_by_course.py", title="Average by course", icon=":material/strategy:")
course_rds_pg = st.Page("score_by_course.py", title="All rounds by course", icon=":material/strategy:")
streaks_pg = st.Page("streaks.py", title="Scoring streaks", icon=":material/strategy:")
data_pg = st.Page("1000Data update.py", title="Data update", icon=":material/update:")
delete_pg = st.Page("delete_data.py", title="Delete data", icon=":material/skull:")
leaderboard_pg = st.Page("leaderboard.py", title="Latest Leaderboard", icon=":material/leaderboard:")
scorecard_pg = st.Page("scorecard.py", title="Scorecard", icon=":material/leaderboard:")
#players_pg = st.Page("pages/players.py", title="The Players")

#pg = st.navigation([results_page, history_page])

pg = st.navigation(
        {
            #"Home": [home_page],
            "History": [history_page, results_page],
            "Records & PBs": [records_page, top_pages, pb_page, worsts_page],
            "Scoring": [byteg_pg, bypar_pg, birdies_pg, streaks_pg, course_rds_pg, course_ave_pg],
            #"Players": [players_pg],
            "Latest TEG": [leaderboard_pg, latest_rd_page, latest_teg_page, hc_page],
            "Data":[data_pg, delete_pg]
        }
    )

pg.run()