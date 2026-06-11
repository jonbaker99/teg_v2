"""Navigation structure — single source of truth for the webapp nav and the
Contents site map.

Mirrors the Streamlit app's section grouping, page titles, ordering and icons
(see streamlit/page_config.py), excluding the Data-admin section.

Each section has:
  - label:   dropdown / heading text (matches Streamlit's section display name)
  - active:  set of ``active_page`` values that should highlight this section
  - pages:   list of (title, url, active_key, icon) tuples in display order

``icon`` is a Google Material Symbols name (the bare ligature, e.g. "trophy"),
matching the ``:material/<name>:`` icons defined in Streamlit's page_config.py.
Define it once here; base.html and contents.html render it via the Material
Symbols web font. Keep it in sync with page_config.py when icons change there.
"""

NAV_SECTIONS = [
    {
        "label": "TEG History",
        "active": {"history", "honours", "results", "player-rankings", "teg-reports"},
        "pages": [
            ("TEG History", "/history", "history", "lists"),
            ("TEG Honours Board", "/honours", "honours", "trophy"),
            ("Full Results", "/results", "results", "sports_score"),
            ("Player Rankings", "/player-rankings", "player-rankings", "123"),
            ("TEG Reports", "/teg-reports", "teg-reports", "description"),
        ],
    },
    {
        "label": "Latest TEG",
        "active": {"leaderboard", "latest-round", "latest-teg", "handicaps"},
        "pages": [
            ("Latest Leaderboard", "/leaderboard", "leaderboard", "leaderboard"),
            ("Latest Round in context", "/latest-round", "latest-round", "sports_golf"),
            ("Latest TEG in context", "/latest-teg", "latest-teg", "sports_golf"),
            ("Handicaps", "/handicaps", "handicaps", "accessible"),
        ],
    },
    {
        "label": "Records & PBs",
        "active": {"records", "top-performances", "personal-bests"},
        "pages": [
            ("TEG Records", "/records", "records", "military_tech"),
            ("Top TEGs and Rounds", "/top-performances", "top-performances", "social_leaderboard"),
            ("Personal Bests", "/personal-bests", "personal-bests", "golf_course"),
        ],
    },
    {
        "label": "Scoring analysis",
        "active": {"scoring"},
        "pages": [
            ("Eagles / Birdies / Pars", "/scoring/birdies", "scoring", "strategy"),
            ("Streaks", "/scoring/streaks", "scoring", "trending_up"),
            ("Average by par", "/scoring/by-par", "scoring", "strategy"),
            ("Average by TEG", "/scoring/by-teg", "scoring", "strategy"),
            ("Course averages and records", "/scoring/by-course", "scoring", "strategy"),
            ("All rounds", "/scoring/all-rounds", "scoring", "strategy"),
            ("Score matrix", "/scoring/matrix", "scoring", "table_chart"),
            ("Scoring distributions", "/scoring/distributions", "scoring", "strategy"),
            ("Changes vs previous round", "/scoring/changes", "scoring", "strategy"),
            ("Heatmap (WIP)", "/scoring/heatmap", "scoring", "strategy"),
            ("Final Round Comebacks", "/scoring/comebacks", "scoring", "trending_up"),
        ],
    },
    {
        "label": "Scorecards",
        "active": {"scorecards", "scorecard"},
        "pages": [
            ("Scorecard", "/scorecard", "scorecard", "leaderboard"),
            ("Best/Worstball", "/bestball", "scorecards", "strategy"),
            ("Eclectic Scores", "/eclectic", "scorecards", "golf_course"),
            ("Eclectic Records", "/eclectic-records", "scorecards", "emoji_events"),
        ],
    },
]
