# Phase 4, Task 4.1: `teg_analysis/` Package Structure Design

**Status:** Design Phase
**Date:** 2025-10-25
**Duration Estimate:** 3 hours
**Risk Level:** LOW (planning only, no code changes)

---

## Executive Summary

This document defines the target architecture for refactoring the TEG analysis codebase. The current monolithic `utils.py` (4,400+ lines, 102 functions) and scattered helper modules (20 files) will be reorganized into a clean, modular `teg_analysis/` package with 5 logical subsystems.

**Architecture Principle:** Separation of Concerns
- **I/O Layer:** File operations, GitHub integration, data persistence
- **Core Layer:** Data loading, transformations, cumulative calculations
- **Analysis Layer:** Scoring, rankings, aggregation, commentary generation
- **Display Layer:** Formatting, tables, charts, UI helpers
- **API Layer:** Future REST API endpoints (reserved)

---

## Part 1: Proposed Package Structure

### Directory Tree

```
teg_analysis/
├── __init__.py                      # Package initialization & public API
│
├── core/                            # Data structures, loading, transformations
│   ├── __init__.py                  # Core module initialization
│   ├── data_loader.py              # Data loading functions (from utils.py Sections 4A-4B)
│   │   ├── load_all_data()
│   │   ├── process_round_for_all_scores()
│   │   ├── add_cumulative_scores()
│   │   ├── add_rankings_and_gaps()
│   │   └── ... (20+ functions)
│   │
│   ├── data_transforms.py          # Data transformation helpers
│   │   ├── reshape_round_data()
│   │   ├── save_to_parquet()
│   │   ├── check_hc_strokes_combinations()
│   │   └── load_and_prepare_handicap_data()
│   │
│   └── models.py                   # Data classes/types (optional, future)
│       └── (Defined as refactoring evolves)
│
├── io/                              # Input/Output operations
│   ├── __init__.py                  # I/O module initialization
│   ├── file_operations.py          # Environment-aware file I/O (from utils.py Section 3)
│   │   ├── read_file()
│   │   ├── write_file()
│   │   ├── read_text_file()
│   │   ├── write_text_file()
│   │   ├── backup_file()
│   │   └── (5 functions)
│   │
│   ├── github_operations.py        # GitHub API operations (from utils.py Section 2)
│   │   ├── read_from_github()
│   │   ├── read_text_from_github()
│   │   ├── write_text_to_github()
│   │   ├── write_to_github()
│   │   ├── batch_commit_to_github()
│   │   └── (5 functions)
│   │
│   └── volume_operations.py        # Railway volume management helpers (from utils.py Section 3)
│       ├── _is_railway()
│       ├── _get_volume_path()
│       ├── _get_local_path()
│       ├── _ensure_volume_dir()
│       ├── clear_volume_cache()
│       └── (5 functions)
│
├── analysis/                        # Analysis and calculations
│   ├── __init__.py                  # Analysis module initialization
│   ├── scoring.py                  # Scoring calculations (from helpers/scoring_data_processing.py + utils.py)
│   │   ├── Functions from helpers/scoring_data_processing.py (12)
│   │   ├── format_vs_par() [from utils.py]
│   │   └── get_net_competition_measure() [from utils.py]
│   │
│   ├── rankings.py                 # Ranking calculations (from utils.py Section 7B)
│   │   ├── add_ranks()
│   │   ├── get_ranked_teg_data()
│   │   ├── get_ranked_round_data()
│   │   ├── get_ranked_frontback_data()
│   │   ├── get_best()
│   │   ├── get_worst()
│   │   ├── ordinal()
│   │   └── safe_ordinal()
│   │
│   ├── aggregation.py              # Aggregation functions (from utils.py Section 7A)
│   │   ├── aggregate_data()
│   │   ├── get_complete_teg_data()
│   │   ├── get_teg_data_inc_in_progress()
│   │   ├── get_round_data()
│   │   ├── get_9_data()
│   │   ├── get_teg_winners()
│   │   └── (6+ functions)
│   │
│   ├── streaks.py                  # Streak analysis (from helpers/streak_analysis_processing.py + utils.py)
│   │   ├── Functions from helpers/streak_analysis_processing.py (15)
│   │   ├── update_streaks_cache() [from utils.py]
│   │   └── (15+ functions)
│   │
│   ├── commentary.py               # Commentary generation (from utils.py Section 6A-6C)
│   │   ├── create_round_summary()
│   │   ├── create_round_events()
│   │   ├── create_tournament_summary()
│   │   ├── create_round_streaks_summary()
│   │   ├── create_tournament_streaks_summary()
│   │   ├── update_commentary_caches()
│   │   └── (6+ functions)
│   │
│   ├── records.py                  # Records identification (from helpers/records_identification.py)
│   │   └── All functions from records_identification.py (10)
│   │
│   └── pipeline.py                 # Data processing pipeline (from utils.py Section 5)
│       ├── update_all_data()
│       ├── update_bestball_cache()
│       ├── get_google_sheet()
│       ├── summarise_existing_rd_data()
│       ├── add_round_info()
│       └── (5+ functions)
│
├── display/                         # Display and formatting
│   ├── __init__.py                  # Display module initialization
│   ├── formatters.py               # Value formatting (from utils.py Section 8A + helpers)
│   │   ├── format_vs_par()
│   │   ├── Functions from helpers/display_helpers.py
│   │   ├── Functions from leaderboard_utils.py (format_leaderboard_value)
│   │   ├── Functions from make_charts.py (format_chart_value)
│   │   └── (20+ functions)
│   │
│   ├── tables.py                   # Table generation (from utils.py + helpers)
│   │   ├── create_stat_section()
│   │   ├── datawrapper_table()
│   │   ├── define_score_types()
│   │   ├── apply_score_types()
│   │   ├── score_type_stats()
│   │   └── (8+ functions)
│   │
│   └── charts.py                   # Chart generation helpers
│       └── Functions from make_charts.py (3 functions)
│
└── api/                             # Public API (Future - for REST API)
    ├── __init__.py
    ├── routes.py                   # API endpoints (future)
    └── schemas.py                  # API data schemas (future)
```

### Module Count Summary

| Module | Function Count | Source |
|--------|---|---|
| **core/data_loader.py** | 20+ | utils.py Sections 4A-4B |
| **core/data_transforms.py** | 4 | utils.py Section 4B |
| **io/file_operations.py** | 5 | utils.py Section 3 |
| **io/github_operations.py** | 5 | utils.py Section 2 |
| **io/volume_operations.py** | 5 | utils.py Section 3 helpers |
| **analysis/scoring.py** | 14 | helpers/ + utils.py |
| **analysis/rankings.py** | 10 | utils.py Section 7B |
| **analysis/aggregation.py** | 10 | utils.py Section 7A |
| **analysis/streaks.py** | 16 | helpers/ + utils.py |
| **analysis/commentary.py** | 6 | utils.py Section 6A-6C |
| **analysis/records.py** | 10 | helpers/records_identification.py |
| **analysis/pipeline.py** | 7 | utils.py Section 5 |
| **display/formatters.py** | 20+ | utils.py Section 8 + helpers/ |
| **display/tables.py** | 8 | utils.py Section 8 |
| **display/charts.py** | 3 | make_charts.py |
| **TOTAL CORE MODULES** | **143+** | From utils.py + helpers/ |
| **Streamlit UI Layer** | 10-15 | Stay in streamlit/utils.py |
| **GRAND TOTAL** | **153-158** | All functions accounted for |

---

## Part 2: Functions Staying in `streamlit/utils.py`

These functions have tight Streamlit dependencies and should remain in the UI layer:

### Configuration & Setup (Streamlit-specific)
- `get_page_layout()` - Page layout configuration (Streamlit-specific)
- `clear_all_caches()` - Streamlit cache management
- `get_base_directory()` - Directory setup (could move, but keep for now)
- `get_current_branch()` - Git branch detection (could move, utility)

### Navigation & UI Helpers (Streamlit-specific)
- `add_custom_navigation_links()` - Custom navigation generation
- `add_section_navigation_links()` - Section navigation
- `create_custom_navigation_section()` - Custom navigation layout
- `apply_custom_navigation_css()` - CSS application
- `convert_filename_to_streamlit_url()` - URL generation

### CSS & Styling (Streamlit-specific)
- `load_css_file()` - CSS loading
- `load_datawrapper_css()` - Datawrapper CSS
- `load_teg_reports_css()` - TEG reports CSS
- `load_course_info()` - Course reference data

### Caching Wrappers (to be added)
These will wrap teg_analysis functions with Streamlit caching:
```python
@st.cache_data
def load_all_data():
    from teg_analysis.core import load_all_data as _load
    return _load()
```

**Estimated:** 15-20 functions remain in streamlit/utils.py

---

## Part 3: Caching Strategy Decision

### Problem
Many functions use `@st.cache_data` decorator. Where should these decorators live after refactoring?

### Option A: Keep Caching in New Modules (RECOMMENDED)

**Pros:**
- Caching logic stays with the function
- Better performance out-of-the-box
- Clear intent: "this function is cached"

**Cons:**
- New modules depend on Streamlit
- Not suitable for external API (Phase 5+)

**Example:**
```python
# teg_analysis/core/data_loader.py
import streamlit as st

@st.cache_data
def load_all_data() -> pd.DataFrame:
    """Load all tournament data with caching"""
    ...
```

### Option B: Remove Caching from New Modules

**Pros:**
- New modules are Streamlit-independent
- Better for future API/library usage
- Cleaner separation of concerns

**Cons:**
- Caching must be re-implemented in calling code
- More boilerplate in streamlit/utils.py
- Performance impact if cache settings differ

**Example:**
```python
# teg_analysis/core/data_loader.py (no streamlit dependency)
def load_all_data() -> pd.DataFrame:
    """Load all tournament data"""
    ...

# streamlit/utils.py (caching layer)
import streamlit as st
from teg_analysis.core import load_all_data as _load_all_data

@st.cache_data
def load_all_data() -> pd.DataFrame:
    """Cached wrapper for core loading function"""
    return _load_all_data()
```

### Decision: **Option A - Keep Caching in New Modules (for now)**

**Rationale:**
- Phase 4 is planning, not API design
- Keep caching for performance continuity
- Can refactor to Option B in Phase 5+ if API becomes necessary
- Minimizes changes needed during migration

**Note for Phase 5:** When designing REST API, extract cache decorators to wrapper layer.

---

## Part 4: Helper Module Migration

### Current Helper Modules (20 files)

| Helper File | Function Count | Target Module |
|---|---|---|
| scoring_data_processing.py | 12 | analysis/scoring.py |
| streak_analysis_processing.py | 15 | analysis/streaks.py |
| records_identification.py | 10 | analysis/records.py |
| best_performance_processing.py | 8 | analysis/aggregation.py |
| worst_performance_processing.py | 8 | analysis/aggregation.py |
| history_data_processing.py | 11 | analysis/aggregation.py |
| display_helpers.py | 14 | display/formatters.py |
| leaderboard_utils.py | 8 | display/formatters.py |
| commentary_generator.py | 6 | analysis/commentary.py |
| course_analysis_processing.py | 9 | analysis/records.py |
| data_deletion_processing.py | 5 | io/file_operations.py |
| data_update_processing.py | 6 | io/pipeline.py |
| scoring_achievements_processing.py | 8 | analysis/scoring.py |
| par_analysis_processing.py | 7 | analysis/scoring.py |
| latest_round_processing.py | 9 | analysis/aggregation.py |
| comeback_analysis.py | 6 | analysis/aggregation.py |
| bestball_processing.py | 8 | analysis/aggregation.py |
| record_css.py | 3 | display/formatters.py |
| make_charts.py | 3 | display/charts.py |
| page_config.py | Constants | (Keep in streamlit/) |

**Total Helper Functions:** ~152

---

## Part 5: Key Decisions & Rationale

### Decision 1: Package Organization (by concern, not by data type)

**Why:** Makes it easier to find related functionality and understand dependencies

| Principle | Example |
|---|---|
| ✅ Group by concern | All I/O together, all analysis together |
| ❌ Group by data type | Don't separate "player data" from "score data" |
| ✅ Clear boundaries | Each package has ~1 purpose |
| ❌ Mega-modules | Avoid 2000-line modules |

### Decision 2: Keep Streamlit Caching for Now

**Why:** Maintain performance during migration, refactor later if needed for API

### Decision 3: Clear Boundary Between UI and Core

**Streamlit/utils.py stays:** UI configuration, navigation, CSS loading, caching wrappers
**teg_analysis/ contains:** Core logic, file operations, analysis

### Decision 4: Helper Module Consolidation

**Why:** 20 scattered files → 8 focused modules improves maintainability

---

## Part 6: Potential Risks & Mitigations

### Risk 1: Circular Dependencies

**Concern:** analysis/commentary.py needs functions from analysis/rankings.py

**Mitigation:**
- Map all dependencies before migration (Task 4.2)
- Create dependency graph
- Identify cycles and restructure if needed

### Risk 2: Streamlit Caching Complexity

**Concern:** Functions with `@st.cache_data` depend on Streamlit context

**Mitigation:**
- Keep caching in place during migration
- Add wrapper layer if needed
- Plan Phase 5 API refactoring

### Risk 3: Import Path Changes

**Concern:** Many files import from `utils`, all need updating

**Mitigation:**
- Create public API in `teg_analysis/__init__.py`
- Export commonly-used functions at package level
- Gradual migration (one module at a time)

### Risk 4: Performance During Migration

**Concern:** New package structure might impact load times

**Mitigation:**
- Keep caching in place
- Test performance after each module migration
- Profile before/after

---

## Part 7: Next Steps (Task 4.2)

Once this structure is approved:

1. **Create detailed function mapping** (`PHASE_4_FUNCTION_MAP.md`)
   - All 102 functions from utils.py assigned
   - All 152 functions from helpers assigned
   - 15-20 functions staying in streamlit/utils.py

2. **Create dependency graph** (`PHASE_4_DEPENDENCY_MAP.md`)
   - Identify all inter-module dependencies
   - Detect circular dependencies
   - Plan import order

3. **Create migration sequence** (`REFACTORING_MIGRATION_SEQUENCE.md`)
   - Phase I: I/O layer migration
   - Phase II: Core layer migration
   - Phase III: Analysis layer migration
   - Phase IV: Display layer migration
   - Include rollback procedures

4. **Define migration testing plan**
   - Test each module independently
   - Integration tests between modules
   - Full regression testing

---

## Summary

**Package Structure Defined:** ✅
- 5 logical packages (core, io, analysis, display, api)
- 143+ functions from utils.py + helpers
- Clear separation of concerns
- Streamlit caching strategy decided

**Ready for Task 4.2:** Detailed function mapping and dependency analysis

---

**Prepared by:** Claude Code (Phase 4 Executor)
**Date:** 2025-10-25
**Status:** Design Complete - Ready for Function Mapping
