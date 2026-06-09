"""Navigation structure — single source of truth for the webapp nav and the
Contents site map.

Mirrors the Streamlit app's section grouping, page titles and ordering
(see streamlit/page_config.py), excluding the Data-admin section.

Each section has:
  - label:   dropdown / heading text (matches Streamlit's section display name)
  - active:  set of ``active_page`` values that should highlight this section
  - pages:   list of (title, url, active_key) tuples in display order
"""

NAV_SECTIONS = [
    {
        "label": "TEG History",
        "active": {"history", "honours", "results", "player-rankings", "teg-reports"},
        "pages": [
            ("TEG History", "/history", "history"),
            ("TEG Honours Board", "/honours", "honours"),
            ("Full Results", "/results", "results"),
            ("Player Rankings", "/player-rankings", "player-rankings"),
            ("TEG Reports", "/teg-reports", "teg-reports"),
        ],
    },
    {
        "label": "Latest TEG",
        "active": {"leaderboard", "latest-round", "latest-teg", "handicaps"},
        "pages": [
            ("Latest Leaderboard", "/leaderboard", "leaderboard"),
            ("Latest Round in context", "/latest-round", "latest-round"),
            ("Latest TEG in context", "/latest-teg", "latest-teg"),
            ("Handicaps", "/handicaps", "handicaps"),
        ],
    },
    {
        "label": "Records & PBs",
        "active": {"records", "top-performances", "personal-bests"},
        "pages": [
            ("TEG Records", "/records", "records"),
            ("Top TEGs and Rounds", "/top-performances", "top-performances"),
            ("Personal Bests", "/personal-bests", "personal-bests"),
        ],
    },
    {
        "label": "Scoring analysis",
        "active": {"scoring"},
        "pages": [
            ("Eagles / Birdies / Pars", "/scoring/birdies", "scoring"),
            ("Streaks", "/scoring/streaks", "scoring"),
            ("Average by par", "/scoring/by-par", "scoring"),
            ("Average by TEG", "/scoring/by-teg", "scoring"),
            ("Course averages and records", "/scoring/by-course", "scoring"),
            ("All rounds", "/scoring/all-rounds", "scoring"),
            ("Score matrix", "/scoring/matrix", "scoring"),
            ("Scoring distributions", "/scoring/distributions", "scoring"),
            ("Changes vs previous round", "/scoring/changes", "scoring"),
            ("Heatmap (WIP)", "/scoring/heatmap", "scoring"),
            ("Final Round Comebacks", "/scoring/comebacks", "scoring"),
        ],
    },
    {
        "label": "Scorecards",
        "active": {"scorecards", "scorecard"},
        "pages": [
            ("Scorecard", "/scorecard", "scorecard"),
            ("Best/Worstball", "/bestball", "scorecards"),
            ("Eclectic Scores", "/eclectic", "scorecards"),
            ("Eclectic Records", "/eclectic-records", "scorecards"),
        ],
    },
]
