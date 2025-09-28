# TEG App Navigation Links Documentation

This document provides comprehensive documentation for the centralized cross-page navigation system implemented across the TEG Streamlit application.

## Overview

The navigation system uses a centralized configuration approach where page definitions and navigation logic are managed in `utils.py`. This eliminates code duplication and makes maintenance much easier.

## Implementation Plan (In Progress)

**Objective**: Replace individual navigation implementations across 22+ pages with a centralized system.

### Phase 1: Create Centralized System
1. **Central Configuration**: Add `PAGE_DEFINITIONS` dictionary to `utils.py` containing all page metadata
2. **Helper Functions**: Implement `create_page_link()` and `add_navigation_links()` functions
3. **Icon Support**: Support optional icons/emojis (currently defaulting to none per user request)

### Phase 2: Update All Pages
Replace existing navigation code blocks in all pages with single function call:
```python
from utils import add_navigation_links
add_navigation_links(__file__)
```

### Phase 3: Benefits
- **Single source of truth**: Page titles and icons defined once
- **Easy maintenance**: Change titles/icons in one place, reflected everywhere
- **Reduced code duplication**: ~6-8 lines per page reduced to 2 lines
- **Consistent formatting**: All sections use same layout logic
- **Automatic current page exclusion**: Pages automatically excluded from their own navigation

## Centralized Navigation Configuration

The navigation system is built around a central configuration in `utils.py`:

### Page Definitions
```python
PAGE_DEFINITIONS = {
    # History section (3 columns)
    "101TEG History.py": {"title": "TEG History", "icon": "", "section": "History"},
    "101TEG Honours Board.py": {"title": "TEG Honours Board", "icon": "", "section": "History"},
    "102TEG Results.py": {"title": "Full Results", "icon": "", "section": "History"},
    "player_history.py": {"title": "Rankings by TEG by Player", "icon": "", "section": "History"},

    # Records section (2 columns)
    "300TEG Records.py": {"title": "TEG Records", "icon": "", "section": "Records"},
    "301Best_TEGs_and_Rounds.py": {"title": "Top TEGs and Rounds", "icon": "", "section": "Records"},
    "302Personal Best Rounds & TEGs.py": {"title": "Personal Bests", "icon": "", "section": "Records"},

    # Scoring analysis section (4 columns)
    "birdies_etc.py": {"title": "Eagles/Birdies/Pars", "icon": "", "section": "Scoring"},
    "streaks.py": {"title": "Streaks", "icon": "", "section": "Scoring"},
    "ave_by_course.py": {"title": "Course averages", "icon": "", "section": "Scoring"},
    "ave_by_par.py": {"title": "Average by par", "icon": "", "section": "Scoring"},
    "sc_count.py": {"title": "Scoring distributions", "icon": "", "section": "Scoring"},
    "ave_by_teg.py": {"title": "Average by TEG", "icon": "", "section": "Scoring"},
    "biggest_changes.py": {"title": "Changes vs previous", "icon": "", "section": "Scoring"},
    "score_by_course.py": {"title": "All rounds", "icon": "", "section": "Scoring"},

    # Bestball/Eclectics section (2 columns)
    "bestball.py": {"title": "Bestball and worstball", "icon": "", "section": "Bestball"},
    "eclectic.py": {"title": "Eclectic Scores", "icon": "", "section": "Bestball"},
    "best_eclectics.py": {"title": "Eclectic Records", "icon": "", "section": "Bestball"},

    # Latest TEG section (3 columns)
    "leaderboard.py": {"title": "Latest Leaderboard", "icon": "", "section": "Latest"},
    "latest_round.py": {"title": "Latest Round", "icon": "", "section": "Latest"},
    "latest_teg_context.py": {"title": "Latest TEG", "icon": "", "section": "Latest"},
    "500Handicaps.py": {"title": "Handicaps", "icon": "", "section": "Latest"},
}
```

### Usage in Pages

**New Implementation** (replaces all existing navigation code):
```python
# At the end of each page file
from utils import add_navigation_links
add_navigation_links(__file__)
```

**Old Implementation** (being replaced):
```python
# === NAVIGATION LINKS ===
st.markdown("---")
st.markdown("**Links to related pages:**")
# ... multiple lines of column/link code ...
```

### Key Benefits

1. **Centralized Management**: All page titles and icons defined in one place
2. **Automatic Layout**: Column layouts handled automatically by section
3. **Icon Flexibility**: Easy to add/remove icons globally by updating the dictionary
4. **Self-Exclusion**: Pages automatically excluded from their own navigation
5. **Consistency**: All navigation sections use identical formatting

## Maintenance Notes

### Adding New Pages
1. Add page definition to `PAGE_DEFINITIONS` in `utils.py`
2. Add navigation call to the new page: `add_navigation_links(__file__)`
3. No need to update other pages - they will automatically include the new page

### Changing Page Titles
1. Update the title in `PAGE_DEFINITIONS` only
2. All pages will automatically use the new title

### Adding/Removing Icons
1. Update the `icon` field in `PAGE_DEFINITIONS`
2. All navigation links will automatically use the new icon

### Testing
- Test navigation links after making changes to `PAGE_DEFINITIONS`
- Verify that current pages are excluded from their own navigation
- Check that column layouts work properly for each section

### Section Configuration
Current section layouts:
- **History**: 3 columns
- **Records**: 2 columns
- **Scoring**: 4 columns
- **Bestball**: 2 columns
- **Latest**: 3 columns

To change layouts, update `SECTION_LAYOUTS` in `utils.py`.

## Migration Status

**✅ Completed**: Documentation update with implementation plan
**✅ Completed**: Centralized navigation system created in `utils.py`
**✅ Completed**: All 22 page files updated to use the new system
**✅ Completed**: System tested and working across all sections

### Files Successfully Migrated:
- **History section (4 files)**: 101TEG History.py, 101TEG Honours Board.py, 102TEG Results.py, player_history.py
- **Records section (3 files)**: 300TEG Records.py, 301Best_TEGs_and_Rounds.py, 302Personal Best Rounds & TEGs.py
- **Scoring section (8 files)**: birdies_etc.py, streaks.py, ave_by_course.py, ave_by_par.py, sc_count.py, ave_by_teg.py, biggest_changes.py, score_by_course.py
- **Bestball section (3 files)**: bestball.py, eclectic.py, best_eclectics.py
- **Latest TEG section (4 files)**: leaderboard.py, latest_round.py, latest_teg_context.py, 500Handicaps.py

## Future Enhancements

With the centralized system in place, consider:
- Dynamic navigation based on user preferences
- Breadcrumb navigation
- Recently viewed pages functionality
- Keyboard shortcuts for navigation
- Analytics on page navigation patterns