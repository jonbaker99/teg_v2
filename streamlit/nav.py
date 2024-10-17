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
hc_page = st.Page("500Handicaps.py", title="Handicaps", icon=":material/accessible:") 
latest_rd_page = st.Page("500Round & TEG Context.py", title="Latest Round", icon=":material/sports_golf:")
top_pages = st.Page("301Best_TEGs_and_Rounds.py", title="Best TEGs and Rounds", icon=":material/social_leaderboard:")
scoring_pg = st.Page("400scoring.py", title="Scoring", icon=":material/strategy:")
data_pg = st.Page("1000Data update.py", title="Data update")
leaderboard_pg = st.Page("leaderboard.py", title="Latest Leaderboard", icon=":material/leaderboard:")
#players_pg = st.Page("pages/players.py", title="The Players")

#pg = st.navigation([results_page, history_page])

pg = st.navigation(
        {
            #"Home": [home_page],
            "History": [history_page, results_page],
            "Records & PBs": [records_page, top_pages, pb_page],
            "Scoring": [scoring_pg],
            #"Players": [players_pg],
            "Latest TEG": [leaderboard_pg, latest_rd_page, hc_page],
            "Data":[data_pg]
        }
    )

pg.run()






# import pandas as pd

# # Sample DataFrame
# data = {
#     'Player': ['John', 'Alice', 'Bob'],
#     'Score': [10, 15, 12]
# }

# df = pd.DataFrame(data)
# df = df.reset_index(drop=True)

# # Apply Pandas Styler to left-align the 'Player' column
# styled_df = df.style.set_properties(subset=['Player'], **{'text-align': 'left'})

# # with stylable_container(
#     key="container_with_border",
#     css_styles="""
#         {
#             border: 1px solid rgba(49, 51, 63, 0.2);
#             border-radius: 0.5rem;
#             padding: calc(1em - 1px)
#         }
#         """,
# ):
#     st.markdown("This is a container with a border.")
#     st.write(styled_df.to_html(index=False, classes='datawrapper-table'), unsafe_allow_html=True)

# Display the styled DataFrame (in a Jupyter environment or export to HTML)
#'index = false'

# 'no index false'
# st.write(styled_df.to_html(classes='datawrapper-table'), unsafe_allow_html=True)

# st.markdown(styled_df.to_html)