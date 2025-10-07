"""Page configuration for the TEG Streamlit application.

This file serves as the single source of truth for all page definitions,
section groupings, and navigation configuration. It defines the structure of
the application's navigation, including page titles, icons, and section
layouts.
"""

import streamlit as st

# Page definitions with titles, icons, and section groupings
PAGE_DEFINITIONS = {
    # History section
    "101TEG History.py": {"title": "TEG History", "icon": ":material/lists:", "section": "History"},
    "101TEG Honours Board.py": {"title": "TEG Honours Board", "icon": ":material/trophy:", "section": "History"},
    "102TEG Results.py": {"title": "Full Results", "icon": ":material/sports_score:", "section": "History"},
    "player_history.py": {"title": "Rankings by TEG by Player", "icon": ":material/123:", "section": "History"},

    # Records section
    "300TEG Records.py": {"title": "TEG Records", "icon": ":material/military_tech:", "section": "Records"},
    "301Best_TEGs_and_Rounds.py": {"title": "Top TEGs and Rounds", "icon": ":material/social_leaderboard:", "section": "Records"},
    "302Personal Best Rounds & TEGs.py": {"title": "Personal Bests", "icon": ":material/golf_course:", "section": "Records"},

    # Scoring analysis section
    # "400scoring.py": {"title": "Scoring", "icon": ":material/strategy:", "section": "Scoring"},
    "birdies_etc.py": {"title": "Eagles / Birdies / Pars", "icon": ":material/strategy:", "section": "Scoring"},
    "streaks.py": {"title": "Streaks", "icon": ":material/trending_up:", "section": "Scoring"},
    "ave_by_par.py": {"title": "Average by par", "icon": ":material/strategy:", "section": "Scoring"},
    "ave_by_teg.py": {"title": "Average by TEG", "icon": ":material/strategy:", "section": "Scoring"},
    "ave_by_course.py": {"title": "Course averages and records", "icon": ":material/strategy:", "section": "Scoring"},
    "score_by_course.py": {"title": "All rounds", "icon": ":material/strategy:", "section": "Scoring"},
    "sc_count.py": {"title": "Scoring distributions", "icon": ":material/strategy:", "section": "Scoring"},
    "biggest_changes.py": {"title": "Changes vs previous round", "icon": ":material/strategy:", "section": "Scoring"},

    # Bestball/Eclectics section
    "bestball.py": {"title": "Bestball and worstball", "icon": ":material/strategy:", "section": "Bestball"},
    "eclectic.py": {"title": "Eclectic Scores", "icon": ":material/golf_course:", "section": "Bestball"},
    "best_eclectics.py": {"title": "Eclectic Records", "icon": ":material/emoji_events:", "section": "Bestball"},

    # Current/Latest TEG section
    "leaderboard.py": {"title": "Latest Leaderboard", "icon": ":material/leaderboard:", "section": "Latest"},
    "latest_round.py": {"title": "Latest Round in context", "icon": ":material/sports_golf:", "section": "Latest"},
    "latest_teg_context.py": {"title": "Latest TEG in context", "icon": ":material/sports_golf:", "section": "Latest"},
    "500Handicaps.py": {"title": "Handicaps", "icon": ":material/accessible:", "section": "Latest"},

    # Scorecards section
    "scorecard_v2.py": {"title": "Scorecard", "icon": ":material/leaderboard:", "section": "Scorecards"},
    # "scorecard_v2_mobile.py": {"title": "Scorecard (mobile)", "icon": ":material/leaderboard:", "section": "Scorecards"},

    # Data management section
    "1000Data update.py": {"title": "Data update", "icon": ":material/update:", "section": "Data"},
    "1001Report Generation.py": {"title": "Report generation", "icon": ":material/robot:", "section": "Data"},
    "data_edit.py": {"title": "Data edit", "icon": ":material/edit:", "section": "Data"},
    "delete_data.py": {"title": "Delete data", "icon": ":material/skull:", "section": "Data"},
    # "data_test_temp.py": {"title": "TEMP DATA TESTING", "icon": ":material/check_circle:", "section": "Data"},
    "admin_volume_management.py": {"title": "Data volume management", "icon": ":material/check_circle:", "section": "Data"},
    # "navigation_test.py": {"title": "Navigation Test", "icon": ":material/science:", "section": "Data"},
    # "commentary_runner.py": {"title": "Commentary generation", "icon": ":material/robot:", "section": "Data"},
}

# Section display names and conditional logic
SECTION_CONFIG = {
    "History": {
        "display_name": "History",
        "show_when_incomplete": True,
        "show_when_complete": True,
        "order": 1
    },
    "Records": {
        "display_name": "Records & PBs",
        "show_when_incomplete": True,
        "show_when_complete": True,
        "order": 3
    },
    "Latest": {
        "display_name": "Current TEG",  # when incomplete
        "display_name_complete": "Latest TEG",  # when complete
        "show_when_incomplete": True,
        "show_when_complete": True,
        "order": 2  # Always 2nd position
    },
    "Scoring": {
        "display_name": "Scoring analysis",
        "show_when_incomplete": True,
        "show_when_complete": True,
        "order": 4
    },
    "Bestball": {
        "display_name": "Bestballs / Eclectics",
        "show_when_incomplete": True,
        "show_when_complete": True,
        "order": 5
    },
    "Scorecards": {
        "display_name": "Scorecards",
        "show_when_incomplete": True,
        "show_when_complete": True,
        "order": 6
    },
    "Data": {
        "display_name": "Data",
        "show_when_incomplete": True,
        "show_when_complete": True,
        "order": 7
    }
}


def get_section_layouts() -> dict:
    """Calculates the optimal column layout for each section.

    This function determines the number of columns to use for displaying pages
    within each section, based on the number of pages in that section.

    Returns:
        dict: A dictionary mapping each section to its optimal number of
        columns.
    """
    section_counts = {}
    for page_info in PAGE_DEFINITIONS.values():
        section = page_info["section"]
        section_counts[section] = section_counts.get(section, 0) + 1

    # Calculate optimal columns (max 4, min 2)
    layouts = {}
    for section, count in section_counts.items():
        if count <= 2:
            layouts[section] = 2
        elif count <= 4:
            layouts[section] = count
        else:
            layouts[section] = 4
    return layouts


# Auto-calculated section layouts
SECTION_LAYOUTS = get_section_layouts()


def generate_navigation_structure(has_incomplete_teg: bool = False) -> dict:
    """Generates the navigation structure from the page definitions.

    This function builds the navigation structure for the Streamlit app based
    on the page definitions and the current TEG status.

    Args:
        has_incomplete_teg (bool, optional): Whether there is an incomplete
            TEG. Defaults to False.

    Returns:
        dict: A dictionary representing the navigation structure, where keys
        are section display names and values are lists of `st.Page` objects.
    """
    # Group pages by section
    sections = {}
    for filename, page_info in PAGE_DEFINITIONS.items():
        section = page_info["section"]
        if section not in sections:
            sections[section] = []
        sections[section].append((filename, page_info))

    # Build navigation structure based on TEG status
    nav_structure = {}

    # Get sections in proper order
    section_order = []
    for section, pages in sections.items():
        section_config = SECTION_CONFIG.get(section, {})

        # Skip sections not shown for current TEG status
        if has_incomplete_teg and not section_config.get("show_when_incomplete", True):
            continue
        if not has_incomplete_teg and not section_config.get("show_when_complete", True):
            continue

        # Use order from SECTION_CONFIG
        order = section_config.get("order", 999)

        section_order.append((order, section, pages))

    # Sort by order
    section_order.sort(key=lambda x: x[0])

    # Build the navigation structure
    for order, section, pages in section_order:
        section_config = SECTION_CONFIG.get(section, {})

        # Get display name based on TEG status
        if has_incomplete_teg and section == "Latest":
            display_name = section_config.get("display_name", section)
        elif not has_incomplete_teg and section == "Latest":
            display_name = section_config.get("display_name_complete", section)
        else:
            display_name = section_config.get("display_name", section)

        # Create st.Page objects for each file
        page_objects = []
        for filename, page_info in pages:
            page_obj = st.Page(
                filename,
                title=page_info["title"],
                icon=page_info.get("icon", "")
            )
            page_objects.append(page_obj)

        nav_structure[display_name] = page_objects

    return nav_structure