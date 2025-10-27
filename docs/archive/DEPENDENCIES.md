# Complete Dependency Map - TEG Analysis System

**Status:** COMPLETE
**Generated:** October 2025
**Total Files Analyzed:** 79 Python files
**Coverage:** All files in streamlit/, helpers/, and commentary/

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [File-Level Dependencies](#file-level-dependencies)
3. [Import Matrix](#import-matrix)
4. [Dependency Layers](#dependency-layers)
5. [Critical Path Analysis](#critical-path-analysis)
6. [Function Call Chains](#function-call-chains)
7. [Data Flow Diagrams](#data-flow-diagrams)
8. [Migration Impact Analysis](#migration-impact-analysis)
9. [Circular Dependency Analysis](#circular-dependency-analysis)

---

## Executive Summary

### Key Statistics

| Metric | Value |
|--------|-------|
| **Total Files** | 79 |
| **Total Imports** | 67 unique modules |
| **Critical Functions** | 15 (heavily used) |
| **Helper Modules** | 20 |
| **Page Files** | 40+ |
| **Circular Dependencies** | 0 (clean architecture) |

### Dependency Overview

The TEG codebase follows a clean 3-layer architecture:

```
Layer 0: External Libraries (pandas, streamlit, numpy, etc.)
    ↓
Layer 1: Core Utilities (utils.py)
    ↓
Layer 2: Helper Modules (helpers/)
    ↓
Layer 3: Page Files (streamlit/*.py)
```

### Most Critical Functions (by usage count)

1. **`utils.load_all_data()`** - 22 files depend on this
2. **`utils.read_file()`** - 16 files depend on this
3. **`utils.format_vs_par()`** - 13 files depend on this
4. **`utils.write_file()`** - 6 files depend on this
5. **`utils.get_page_layout()`** - 24 files depend on this
6. **`utils.add_custom_navigation_links()`** - 24 files depend on this

---

## File-Level Dependencies

### Core Modules

#### **utils.py** (4,406 lines, 102 functions)

**Direct Imports:**
- External: `pandas`, `streamlit`, `numpy`, `logging`, `google.oauth2`, `gspread`, `github`, `pathlib`, `subprocess`, `datetime`, `base64`, `io`, `re`, `sys`
- Internal: `page_config` (local module)

**Imported By:**
- Nearly all page files (40+ files)
- Most helper modules
- Commentary generation modules

**Key Exports (most used):**
- `load_all_data()` - Primary data loading function
- `read_file()` / `write_file()` - Environment-aware file I/O
- `format_vs_par()` - Score formatting utility
- `get_page_layout()` - Layout configuration
- `add_custom_navigation_links()` - Navigation helper

**Dependency Level:** Layer 1 (depends only on external libraries)

---

#### **helpers/** directory (20 modules, ~6,842 lines)

**Primary Dependencies:**
- `utils.py` (read_file, write_file, various utilities)
- External: `pandas`, `numpy`, `streamlit` (some modules only)

**By Purity:**

| Module | Depends On | Streamlit? | Migration Ready? |
|--------|-----------|-----------|------------------|
| `scoring_data_processing.py` | pandas, numpy | No | Yes |
| `streak_analysis_processing.py` | pandas, numpy | No | Yes |
| `records_identification.py` | pandas, numpy | No | Yes |
| `best_performance_processing.py` | pandas, numpy | No | Yes |
| `worst_performance_processing.py` | pandas, numpy | No | Yes |
| `comeback_analysis.py` | pandas, numpy | No | Yes |
| `history_data_processing.py` | pandas, numpy | No | Yes |
| `course_analysis_processing.py` | pandas, numpy | No | Yes |
| `bestball_processing.py` | pandas, numpy | No | Yes |
| `par_analysis_processing.py` | pandas, numpy | No | Yes |
| `display_helpers.py` | pandas, numpy | No | Yes |
| `scorecard_data_processing.py` | pandas, numpy | No | Yes |
| `score_count_processing.py` | pandas, numpy, streamlit | **Yes** | Partial |
| `data_update_processing.py` | utils, streamlit | **Yes** | Partial |
| `data_deletion_processing.py` | utils, streamlit | **Yes** | Partial |
| `commentary_generator.py` | utils, streamlit | **Yes** | Partial |
| `latest_round_processing.py` | pandas, streamlit | **Yes** | No |
| `records_css.py` | CSS only | No | Yes |

**Dependency Level:** Layer 2 (depends on utils.py and external libraries)

---

### Page Files (40+ files)

#### **Typical Page Structure**

```python
# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np

# Core utils imports
from utils import (
    load_all_data,           # Data loading
    get_page_layout,         # Layout config
    add_custom_navigation_links,  # Navigation
    format_vs_par,           # Formatting
    read_file,              # File I/O
    # ... specific functions needed
)

# Helper imports (specific to page)
from helpers.scoring_data_processing import ...
from helpers.records_identification import ...
```

#### **Import Dependencies by Page Category**

**History Pages (6 pages)**
- `101TEG History.py` → utils, `history_data_processing`
- `102TEG Results.py` → utils, `display_helpers`
- `101TEG Honours Board.py` → utils, `display_helpers`
- `contents.py` → utils only
- `teg_reports.py` → utils, multiple helpers
- `player_history.py` → utils, `history_data_processing`

**Records Pages (4 pages)**
- `300TEG Records.py` → utils, `records_identification`, `display_helpers`
- `301Best_TEGs_and_Rounds.py` → utils, `best_performance_processing`
- `302Personal Best Rounds & TEGs.py` → utils, `best_performance_processing`
- `303Final Round Comebacks.py` → utils, `comeback_analysis`

**Scoring Analysis (10 pages)**
- `400scoring.py` → utils, `scoring_data_processing`
- `streaks.py` → utils, `streak_analysis_processing`
- `ave_by_par.py` → utils, `par_analysis_processing`
- `ave_by_teg.py` → utils, `scoring_data_processing`
- `ave_by_course.py` → utils, `course_analysis_processing`
- `birdies_etc.py` → utils, `scoring_achievements_processing`
- `score_by_course.py` → utils, `course_analysis_processing`
- `score_matrix.py` → utils, `scoring_data_processing`
- `score_heatmaps.py` → utils, `course_analysis_processing`
- `biggest_changes.py` → utils, `display_helpers`

**Latest TEG (4 pages)**
- `leaderboard.py` → utils, `display_helpers`
- `latest_round.py` → utils, `latest_round_processing`
- `latest_teg_context.py` → utils, multiple helpers
- `500Handicaps.py` → utils, display helpers

**Scorecard Pages (4 pages)**
- `scorecard_v2.py` → utils, `scorecard_data_processing`
- `bestball.py` → utils, `bestball_processing`
- `eclectic.py` → utils, `bestball_processing`
- `best_eclectics.py` → utils, `bestball_processing`

**Admin Pages (5 pages)**
- `1000Data update.py` → utils, `data_update_processing`
- `1001Report Generation.py` → utils, `commentary_generator`
- `delete_data.py` → utils, `data_deletion_processing`
- `admin_volume_management.py` → utils
- `data_edit.py` → utils

**Dependency Level:** Layer 3 (depends on utils.py and helpers/)

---

## Import Matrix

### What Imports What?

```markdown
MODULE IMPORTS MATRIX (Files that use each module)

utils.py:
  - Used by: 40+ page files, all helper modules, commentary modules
  - Key functions imported:
    * load_all_data: 22 files
    * read_file: 16 files
    * format_vs_par: 13 files
    * write_file: 6 files
    * get_page_layout: 24 files (all pages)
    * add_custom_navigation_links: 24 files (all pages)

helpers.scoring_data_processing:
  - Used by: 400scoring.py, ave_by_teg.py, score_matrix.py

helpers.streak_analysis_processing:
  - Used by: streaks.py, 300TEG Records.py (5 references)

helpers.records_identification:
  - Used by: 300TEG Records.py, 302Personal Best Rounds & TEGs.py

helpers.best_performance_processing:
  - Used by: 301Best_TEGs_and_Rounds.py, 302Personal Best Rounds & TEGs.py

helpers.worst_performance_processing:
  - Used by: 303Final Round Comebacks.py

helpers.comeback_analysis:
  - Used by: 303Final Round Comebacks.py

helpers.display_helpers:
  - Used by: 102TEG Results.py, 300TEG Records.py, leaderboard.py, latest_round.py

helpers.latest_round_processing:
  - Used by: latest_round.py (exclusive)

helpers.scorecard_data_processing:
  - Used by: scorecard_v2.py (exclusive)

helpers.bestball_processing:
  - Used by: bestball.py, eclectic.py, best_eclectics.py

helpers.history_data_processing:
  - Used by: 101TEG History.py, teg_reports.py

helpers.course_analysis_processing:
  - Used by: ave_by_course.py, score_by_course.py, score_heatmaps.py

helpers.commentary_generator:
  - Used by: 1001Report Generation.py

helpers.data_update_processing:
  - Used by: 1000Data update.py

helpers.data_deletion_processing:
  - Used by: delete_data.py

helpers.par_analysis_processing:
  - Used by: ave_by_par.py

helpers.scoring_achievements_processing:
  - Used by: birdies_etc.py

helpers.score_count_processing:
  - Used by: sc_count.py (3 references)
```

---

## Dependency Layers

### Architectural Layers

```
LAYER 0: External Libraries Only
├── Most helper modules (16/20)
│   ├── scoring_data_processing.py
│   ├── streak_analysis_processing.py
│   ├── records_identification.py
│   ├── best_performance_processing.py
│   ├── worst_performance_processing.py
│   ├── comeback_analysis.py
│   ├── history_data_processing.py
│   ├── course_analysis_processing.py
│   ├── bestball_processing.py
│   ├── par_analysis_processing.py
│   ├── display_helpers.py
│   ├── scorecard_data_processing.py
│   ├── scoring_achievements_processing.py
│   ├── records_css.py
│   └── ... (more pure analysis modules)
│
└── Dependencies: pandas, numpy only (no streamlit, no utils)
    Impact: EASY TO MIGRATE - Can move to separate library
    Complexity: Medium (50-1000 lines each)

LAYER 1: Core Utilities
├── utils.py (102 functions, 4,406 lines)
│
└── Dependencies: External libraries only
    Impact: CRITICAL - Foundation of entire system
    Complexity: HIGH (40 functions are complex)
    Cached: 25 functions use @st.cache_data

LAYER 2: Mixed Helper Modules
├── 4 helper modules with Streamlit dependencies
│   ├── score_count_processing.py
│   ├── data_update_processing.py
│   ├── data_deletion_processing.py
│   ├── latest_round_processing.py
│   └── commentary_generator.py
│
├── Dependencies: utils.py + streamlit
│   Impact: MEDIUM - Need splitting before migration
│   Complexity: HIGH (mixed concerns)
│
└── Note: These need separation of concerns:
    - Core logic → can migrate
    - UI/display → stays in streamlit/

LAYER 3: Page Files
├── 40+ user-facing pages
│
├── Dependencies: utils.py + layer 2 helpers
│   Impact: LOW - Leaves page files alone
│   Complexity: MEDIUM (typically 200-400 lines)
│
└── Pattern: Most follow same structure
    1. Import utils
    2. Import specific helper(s)
    3. Set page config
    4. Load data with load_all_data()
    5. Process with helpers
    6. Display with st.* functions
```

### Dependency Flow Diagram

```
                LAYER 0: External Libraries
                    pandas, numpy, streamlit,
                    google-auth, github, etc.
                           |
                    _________|_________
                   |                   |
              utils.py          Pure Helpers (16 modules)
              (102 funcs)        - scoring
              - I/O              - analysis
              - caching          - calculations
              - GitHub           - records
              - config           - performance
                   |__________________|
                           |
                    _______|_______
                   |               |
              Mixed Helpers    Page Files
              (4 modules)       (40+ pages)
              - data update     - history
              - deletion        - records
              - commentary      - scoring
              - latest round    - results
                   |               |
                   |_______________|
                           |
                    Streamlit Display
```

---

## Critical Path Analysis

### Most Depended-Upon Functions

Ranked by number of files that depend on them:

| Rank | Function | Files | Category | Migration Priority | Impact |
|------|----------|-------|----------|-----------------|--------|
| 1 | `utils.get_page_layout()` | 24 | Config | Must be last | Critical |
| 2 | `utils.add_custom_navigation_links()` | 24 | UI | Must be last | Critical |
| 3 | `utils.load_all_data()` | 22 | Data Loading | Must be first | Critical |
| 4 | `utils.read_file()` | 16 | I/O | Very Early | Critical |
| 5 | `utils.format_vs_par()` | 13 | Formatting | Early-Mid | High |
| 6 | `utils.write_file()` | 6 | I/O | Very Early | High |
| 7 | `helpers.display_helpers.*` | 6 | Display | Mid-phase | High |
| 8 | `utils.get_teg_winners()` | 4 | Analysis | Early-Mid | Medium |
| 9 | `utils.aggregate_data()` | 4 | Analysis | Early-Mid | Medium |
| 10 | `utils.get_best()` / `get_worst()` | 4 | Analysis | Early-Mid | Medium |
| 11 | `helpers.streak_analysis_processing.*` | 3 | Analysis | Mid-phase | Medium |
| 12 | `helpers.records_identification.*` | 2 | Analysis | Mid-phase | Medium |
| 13 | `helpers.best_performance_processing.*` | 2 | Analysis | Mid-phase | Medium |
| 14 | `utils.load_datawrapper_css()` | 10 | CSS | Mid-late | Medium |
| 15 | `helpers.latest_round_processing.*` | 2 | Display | Mid-phase | Low |

### Migration Priority Order

#### Phase 1: MUST MIGRATE FIRST (I/O & Data Loading)
1. `utils.read_file()` - 16 files need this
2. `utils.write_file()` - 6 files need this
3. `utils.load_all_data()` - 22 files need this

**Why First:** All data operations depend on these functions. Moving them establishes the foundation.

#### Phase 2: Analysis Functions (Early-Mid)
4. `utils.format_vs_par()` - 13 files
5. Core data transformation functions from utils
6. Pure helper modules (scoring, records, analysis)

**Why Early:** Calculations can be tested independently, make up core business logic.

#### Phase 3: Display & Formatting (Mid-Phase)
7. `helpers.display_helpers` functions
8. Formatting and styling utilities
9. CSS loading functions

**Why Middle:** Depends on data being loaded correctly, enables UI testing.

#### Phase 4: UI Integration (Late Phase)
10. `utils.get_page_layout()` - 24 files
11. `utils.add_custom_navigation_links()` - 24 files
12. Navigation and layout functions

**Why Last:** Dependent on all data being ready, UI layer on top.

---

## Function Call Chains

### Critical Function Chains (Data Load Path)

```
USER VISITS PAGE
    ↓
page_file.py (e.g., 400scoring.py)
    ↓
    calls: load_all_data()
    ↓
utils.load_all_data()
    ├── calls: read_file(ALL_SCORES_PARQUET)
    │   ├── calls: _is_railway()
    │   ├── calls: _get_volume_path() or _get_local_path()
    │   └── calls: read_from_github() [if Railway]
    │       └── calls: github.get_repo().get_contents()
    │
    ├── calls: read_file(HANDICAPS_CSV)
    │   └── (same pattern as above)
    │
    ├── calls: process_round_for_all_scores()
    │   ├── calls: add_cumulative_scores()
    │   ├── calls: add_rankings_and_gaps()
    │   └── applies vectorized pandas operations
    │
    └── returns: df (cached for 24hrs or until clear)

page_file continues
    ↓
    calls: helper.specific_analysis()
    ├── Example: prepare_average_scores_by_par()
    │   ├── calls: pandas.groupby()
    │   ├── calls: calculate stats
    │   └── returns: processed DataFrame
    │
    └── Example: get_teg_winners()
        ├── calls: aggregate_data()
        ├── calls: add_ranks()
        └── returns: ranked DataFrame

page_file continues
    ↓
    calls: st.dataframe(), st.altair_chart(), etc.
    ↓
DISPLAY RENDERED
```

### Key Call Chains by Category

#### **Data Update Chain**

```
1000Data update.py
    ├── calls: load_all_data()
    ├── calls: [User validation]
    ├── calls: data_update_processing.update_data()
    │   ├── calls: pandas operations
    │   ├── calls: utils.write_file()
    │   │   ├── calls: write_to_github()
    │   │   └── calls: st.cache_data.clear()
    │   └── calls: utils.batch_commit_to_github()
    │
    └── calls: st.success("Data updated!")
```

#### **Record Detection Chain**

```
300TEG Records.py
    ├── calls: load_all_data()
    ├── calls: records_identification.identify_all_records()
    │   ├── calls: identify_teg_records()
    │   ├── calls: identify_round_records()
    │   ├── calls: identify_player_records()
    │   └── returns: {record_type: [records]}
    │
    └── calls: display_helpers.prepare_records_table()
        ├── calls: pandas.DataFrame operations
        └── returns: formatted output
```

---

## Data Flow Diagrams

### Primary Data Flow (Read Path)

```
LOCAL ENVIRONMENT:
    File System (data/*.csv, data/*.parquet)
            ↓
    utils.read_file()
            ↓
    pandas.read_csv() / read_parquet()
            ↓
    Cached DataFrame
            ↓
    Page Processing

RAILWAY ENVIRONMENT:
    GitHub Repository (jonbaker99/teg_v2)
            ↓
    utils.read_from_github()
            ↓
    PyGithub API (github.get_repo().get_contents())
            ↓
    BytesIO stream
            ↓
    pandas.read_csv() / read_parquet()
            ↓
    Railway Volume Cache (persistent)
            ↓
    Cached DataFrame
            ↓
    Page Processing
```

### Data Update Flow (Write Path)

```
USER SUBMITS FORM
    ↓
Page validation (streamlit widgets)
    ↓
Call helper update function
    (e.g., data_update_processing.update_data())
    ↓
    Modify DataFrame
    ↓
    Call utils.write_file()
    ├─→ LOCAL: Write to data/
    │   └─→ Store in filesystem
    │
    └─→ RAILWAY:
        ├─→ Write to volume cache
        ├─→ Write to GitHub via PyGithub
        └─→ Clear Streamlit cache (@st.cache_data.clear())
            ↓
        All pages see fresh data on next load
    ↓
Display success message
```

### Commentary Generation Flow

```
User triggers report generation
    ↓
1001Report Generation.py
    ├─→ loads: load_all_data()
    ├─→ calls: commentary_generator.generate_reports_for_changes()
    │   ├─→ analyzes: round events
    │   ├─→ calculates: round summary stats
    │   ├─→ calculates: tournament summary
    │   ├─→ interfaces: Claude API (for AI generation)
    │   └─→ returns: generated report text
    │
    └─→ stores: write_text_to_github("commentary.md")
            ↓
        GitHub Repository
```

---

## Migration Impact Analysis

### Function-by-Function Migration Impact

#### TOP PRIORITY: `utils.load_all_data()`

**Current Location:** `streamlit/utils.py:150`
**New Location:** `teg_analysis/core/data_loader.py`
**Migration Type:** MOVE
**Impact Level:** 🔴 CRITICAL

**Files Requiring Import Updates:** 22

```
Pages:
  - 101TEG History.py (line 5)
  - 102TEG Results.py (line 7)
  - 300TEG Records.py (line 8)
  - 301Best_TEGs_and_Rounds.py (line 5)
  - 302Personal Best Rounds & TEGs.py (line 7)
  - 303Final Round Comebacks.py (line 5)
  - 400scoring.py (line 20)
  - 500Handicaps.py (line 10)
  - 101TEG Honours Board.py (line 8)
  - ave_by_course.py (line 7)
  - ave_by_par.py (line 6)
  - ave_by_teg.py (line 5)
  - bestball.py (line 8)
  - best_eclectics.py (line 8)
  - birdies_etc.py (line 5)
  - leaderboard.py (line 7)
  - latest_round.py (line 5)
  - latest_teg_context.py (line 5)
  - player_history.py (line 5)
  - scorecard_v2.py (line 8)
  - score_by_course.py (line 5)
  - streaks.py (line 7)

Dependencies Called:
  - read_file()
  - process_round_for_all_scores()
  - get_incomplete_tegs()
  - exclude_incomplete_tegs_function()

Migration Steps:
1. Create new module at teg_analysis/core/data_loader.py
2. Copy function and dependencies
3. Update 22 import statements
4. Test all pages with new import
5. Remove old utils.load_all_data()
6. Run full app tests

Estimated Time: 1 hour (automated replacement + testing)
```

#### HIGH PRIORITY: `utils.read_file()` and `utils.write_file()`

**Current Location:** `streamlit/utils.py:section-3`
**New Location:** `teg_analysis/io/file_operations.py`
**Migration Type:** MOVE (with environment awareness)
**Impact Level:** 🔴 CRITICAL

**Files Requiring Updates:** 16 + 6 = 22 files

```
Migration Strategy:
1. Extract I/O functions as group (cohesive)
2. Migrate helper functions first:
   - _is_railway()
   - _get_volume_path()
   - _get_local_path()
   - _ensure_volume_dir()
3. Then migrate public functions
4. Test with local and Railway environments
5. Verify cache behavior

Estimated Time: 1.5 hours
```

#### HIGH PRIORITY: `utils.format_vs_par()`

**Current Location:** `streamlit/utils.py:section-7a`
**Files Using:** 13
**Type:** PURE FUNCTION
**Migration:** Can be moved to analysis library

```
migrate with: get_teg_rounds(), get_net_competition_measure()
(these are pure functions with no side effects)

Estimated Time: 30 minutes
```

#### MEDIUM PRIORITY: Helper Modules (16 pure)

**All of these can be migrated independently:**

```
Phase 1 (Easy):
- scoring_data_processing.py (180 lines)
- scoring_achievements_processing.py (115 lines)
- par_analysis_processing.py (73 lines)
- records_identification.py (627 lines)
- best_performance_processing.py (633 lines)
- worst_performance_processing.py (175 lines)
- comeback_analysis.py (436 lines)
- history_data_processing.py (792 lines)
- course_analysis_processing.py (161 lines)
- bestball_processing.py (132 lines)
- display_helpers.py (467 lines)
- scorecard_data_processing.py (155 lines)
- scoring_achievements_processing.py (115 lines)
- records_css.py (65 lines)

Time Estimate: 3-4 hours total
Risk: VERY LOW - These are pure functions
```

#### MEDIUM PRIORITY: Mixed Modules

```
These need separation before migration:

1. score_count_processing.py
   - Pure core: can migrate
   - Streamlit UI code: stays in streamlit/

2. data_update_processing.py
   - Pure logic: can migrate to teg_analysis/
   - UI/forms: stay in streamlit/

3. data_deletion_processing.py
   - Similar split needed

4. commentary_generator.py
   - Core generation: can migrate
   - UI display: stays in streamlit/

Time Estimate: 6-8 hours (includes refactoring for separation)
Risk: MEDIUM - Needs careful separation of concerns
```

#### LOW PRIORITY: UI Functions

```
These must stay in streamlit/ (by design):

- get_page_layout() - Layout configuration
- add_custom_navigation_links() - Navigation UI
- add_section_navigation_links() - Navigation UI
- create_custom_navigation_section() - Navigation
- load_css_file() - CSS loading (Streamlit only)
- load_datawrapper_css() - CSS loading
- create_stat_section() - HTML generation
- datawrapper_table() - Table rendering
- clear_all_caches() - Streamlit cache API

Time Estimate: No migration needed
Risk: NONE - These belong in streamlit/
```

---

## Circular Dependency Analysis

### Circular Dependency Check

**Result: NONE FOUND ✅**

The codebase has a clean, acyclic dependency graph:

```
Checked Scenarios:
✅ utils ↔ helpers: No circular imports
✅ page ↔ page: Pages don't import from each other
✅ helpers ↔ helpers: Helper modules don't cross-depend
✅ page ↔ utils: Pages only import from utils (one direction)
✅ external ↔ internal: External libs don't depend on project code
```

### Dependency Graph Integrity

```
All imports follow strict hierarchy:

External Libraries
    ↓ (used by)
utils.py
    ↓ (used by)
helpers/
    ↓ (used by)
pages/

No backward references found.
No circular patterns detected.
No cross-contamination between layers.
```

---

## Summary & Recommendations

### Key Findings

1. **Clean Architecture** - No circular dependencies, clear layering
2. **Well-Centralized** - Dependency on utils.py creates single point of coordination
3. **Migration-Ready** - 16/20 helpers are pure functions, easily movable
4. **Critical Dependencies** - load_all_data, read_file, write_file are load-bearing walls

### Recommended Actions

1. **Immediate (Week 1):**
   - Document all function signatures in utils.py
   - Create migration plan for I/O functions (read/write)
   - Plan tests for each layer

2. **Short-term (Month 1):**
   - Migrate pure helper modules (low risk)
   - Split mixed modules (medium risk)
   - Update imports in pages

3. **Medium-term (Month 2-3):**
   - Extract core analysis library
   - Establish clear interfaces
   - Add comprehensive tests

4. **Long-term (Ongoing):**
   - Database integration
   - API layer
   - Performance monitoring

---

**Document Version:** 1.0
**Last Updated:** October 18, 2025
**Next Review:** After any major refactoring
