import streamlit as st

results_page = st.Page("pages/1TEG Results.py", title="TEG Results", icon=":material/add_circle:")
history_page = st.Page("pages/2TEG History.py", title="TEG History", icon=":material/delete:")
pb_page = st.Page("pages/3PBs both test.py", title="Personal Bests") 
records_page = st.Page("pages/3TEG Records.py", title="TEG Records") 
hc_page = st.Page("pages/4Handicaps.py", title="Handicaps") 
latest_rd_page = st.Page("pages/4Round & TEG Context.py", title="Latest Round")
top_pages = st.Page("pages/12Top TEGs and Rounds.py", title="Best TEGs and Rounds")
scoring_pg = st.Page("pages/scoring.py", title="Scoring")
players_pg = st.Page("pages/players.py", title="The Players")

pg = st.navigation([results_page, history_page])

pg = st.navigation(
        {
            "History": [results_page],
            "Records & PBs": [records_page, pb_page, top_pages],
            "Scoring": [scoring_pg],
            "Players": [players_pg],
            "Latest TEG": [latest_rd_page],
        }
    )



st.set_page_config(page_title="TEG Stats Home", page_icon=":material/edit:")
pg.run()
