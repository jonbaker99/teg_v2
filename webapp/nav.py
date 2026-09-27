"""Navigation structure — single source of truth for public webapp links.

``NAV_SECTIONS`` drives the desktop dropdowns, tablet disclosure menu, Contents
site map, and phone Explore sheet. It intentionally has no dependency on the
frozen Streamlit application.

Each section has:
  - label:   dropdown / heading text
  - active:  set of ``active_page`` values that should highlight this section
  - pages:   list of (title, url, active_key, icon) tuples in display order

``icon`` is a Google Material Symbols name (the bare ligature, e.g. "trophy"),
defined once here. ``base.html`` and ``contents.html`` render it with the
Material Symbols web font.
"""

NAV_SECTIONS = [
    {
        "label": "TEG History",
        "active": {"history", "honours", "results", "player-rankings", "teg-reports"},
        "pages": [
            ("TEG History", "/history", "history", "lists"),
            ("TEG Honours Board", "/honours", "honours", "trophy"),
            ("Past results", "/results", "results", "sports_score"),
            ("Player Rankings", "/player-rankings", "player-rankings", "123"),
            ("TEG Reports", "/teg-reports", "teg-reports", "description"),
            # Player Profiles hidden from nav 2026-09-18: pages need more work
            # before going live. Route/templates untouched, just unlinked.
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
            ("Score history", "/scoring/matrix", "scoring", "table_chart"),
            ("Scoring distributions", "/scoring/distributions", "scoring", "strategy"),
            ("Round score distribution", "/scoring/round-distribution", "scoring", "bar_chart"),
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


# Phone quick access deliberately covers four common destinations. Explore is
# the fifth bottom-bar control and exposes every page in ``NAV_SECTIONS``.
# These are shortcuts, not a second public-page registry: all complete link
# grouping and page inventory remains above.
MOBILE_SHORTCUTS = [
    {
        "label": "Latest",
        "icon": "leaderboard",
        "url": "/leaderboard",
        "active": NAV_SECTIONS[1]["active"],
    },
    {
        "label": "History",
        "icon": "lists",
        "url": "/history",
        "active": NAV_SECTIONS[0]["active"],
    },
    {
        "label": "Records",
        "icon": "military_tech",
        "url": "/records",
        "active": NAV_SECTIONS[2]["active"],
    },
    {
        "label": "Cards",
        "icon": "sports_golf",
        "url": "/scorecard",
        "active": NAV_SECTIONS[4]["active"],
    },
]


def navigation_for_teg(
    teg_num: int, *, in_progress: bool = False, report: tuple[str, str] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Build request-local navigation labels for the current TEG.

    Keep the shared registry unchanged. Hide the TEG context shortcut while
    play is under way; its direct route remains available.
    """
    teg_label = f"TEG {teg_num}"

    def page_title(title: str, key: str) -> str:
        if key == "leaderboard":
            return "Latest Leaderboard" if in_progress else "Final leaderboard"
        if key == "latest-teg":
            return f"{teg_label} in context"
        if key == "handicaps":
            return f"TEG {teg_num if in_progress else teg_num + 1} handicaps"
        return title

    sections = list(NAV_SECTIONS)
    latest = NAV_SECTIONS[1]
    pages = []
    for title, url, key, icon in latest["pages"]:
        if in_progress and key == "latest-teg":
            continue
        pages.append((page_title(title, key), url, key, icon))
        if key == "leaderboard" and report:
            report_title, report_url = report
            pages.append((report_title, report_url, "teg-reports", "description"))
    sections[1] = {
        **latest,
        "label": teg_label,
        "pages": pages,
    }
    shortcuts = list(MOBILE_SHORTCUTS)
    shortcuts[0] = {**MOBILE_SHORTCUTS[0], "label": teg_label}
    return sections, shortcuts
