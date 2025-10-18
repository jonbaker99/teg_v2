# TEG Golf Tournament App - Complete Codebase Inventory

**Documentation Date:** 2025-10-17 - 2025-10-18
**Purpose:** Exhaustive documentation of current codebase before refactoring
**Status:** ✅ COMPLETE

---

## Table of Contents

1. [Directory Structure Overview](#directory-structure-overview)
2. [File Inventory by Category](#file-inventory-by-category)
3. [Function Inventory](#function-inventory)
4. [Dependency Map](#dependency-map)
5. [Duplication Analysis](#duplication-analysis)
6. [Migration Planning Matrix](#migration-planning-matrix)

---

## Documentation Legend

### File Categories
- 🎨 **UI** - Streamlit page/UI component
- 🧮 **Analysis** - Data analysis/calculation logic
- 📊 **Data** - Data loading/persistence
- 🎯 **Helper** - Utility/helper functions
- ⚙️ **Config** - Configuration/constants
- 🔧 **Admin** - Administrative/maintenance tools
- 📝 **Commentary** - Report generation

### Function Types
- `PURE` - Pure function (no side effects, framework-agnostic)
- `UI` - Streamlit-specific UI function
- `IO` - Data input/output function
- `MIXED` - Contains both business logic and UI
- `CONFIG` - Configuration/constants

### Migration Priority
- 🔴 **HIGH** - Core business logic, frequently used
- 🟡 **MEDIUM** - Important but less frequently used
- 🟢 **LOW** - Nice to have, rarely used
- ⚪ **KEEP** - Stays in current location

---

## Directory Structure Overview

```
/teg_v2/
├── streamlit/                    # Streamlit application
│   ├── pages/                    # Streamlit page files (30+ files)
│   ├── helpers/                  # Helper modules (organized by domain)
│   ├── commentary/               # Report generation system
│   ├── styles/                   # CSS stylesheets
│   ├── utils.py                  # Main utilities (LARGE - 2000+ lines)
│   ├── page_config.py            # Page configuration
│   ├── scorecard_utils.py        # Scorecard-specific utilities
│   ├── make_charts.py            # Chart generation
│   └── [other supporting files]
├── data/                         # Data files
│   ├── all-scores.parquet
│   ├── all-data.parquet
│   └── [other data files]
└── [other directories]
```

---

## File Inventory by Category

### Core Utility Files

#### `streamlit/utils.py` (⚠️ MASSIVE - ~2000 lines)
**Category:** 🧮📊🎯 MIXED - Contains everything
**Status:** ⚠️ NEEDS SPLITTING
**Dependencies:** pandas, streamlit, github, gspread
**Imports From:** page_config

**Function Groups:**
1. Configuration & Setup (20+ functions)
2. Data Loading (15+ functions)
3. Data Processing (30+ functions)
4. Formatting & Display (25+ functions)
5. GitHub Operations (10+ functions)
6. Navigation & UI Helpers (15+ functions)
7. Scoring Calculations (20+ functions)
8. Statistics & Analysis (15+ functions)

**Critical Note:** This file is the heart of the current mess. It contains:
- Framework-agnostic business logic ✅ Should move
- Streamlit-specific UI helpers ❌ Should stay
- Data I/O ✅ Should move
- Mixed concerns ⚠️ Needs splitting

**Detailed Function Inventory:** See [Utils.py Function Inventory](#utilspy-detailed-inventory)

---

#### `streamlit/page_config.py`
**Category:** ⚙️ CONFIG
**Status:** ✅ STAYS (Streamlit-specific)
**Purpose:** Page definitions and navigation structure
**Dependencies:** streamlit
**Line Count:** ~300

**Key Components:**
- `PAGE_DEFINITIONS` - Dict of all pages with metadata
- `SECTION_CONFIG` - Section organization
- `build_navigation()` - Constructs navigation structure

**Migration Decision:** STAYS in streamlit/ (UI configuration)

---

#### `streamlit/scorecard_utils.py`
**Category:** 🧮 ANALYSIS + 🎨 UI (MIXED)
**Status:** ⚠️ NEEDS SPLITTING
**Purpose:** Scorecard generation and display
**Dependencies:** pandas, streamlit

**Functions to Split:**
- Scorecard HTML generation → Should be format-agnostic
- Scorecard calculations → Pure analysis
- Streamlit display helpers → Stay in streamlit/

---

#### `streamlit/make_charts.py`
**Category:** 🧮 ANALYSIS + 🎨 UI (MIXED)
**Status:** ⚠️ NEEDS REVIEW
**Purpose:** Chart generation (likely Altair)
**Dependencies:** altair, pandas, streamlit

**Functions to Review:**
- Chart data preparation → Pure analysis
- Chart rendering → Stays with Streamlit

---

### Helper Modules (streamlit/helpers/)

#### `helpers/scoring_data_processing.py`
**Category:** 🧮 ANALYSIS
**Status:** ✅ GOOD CANDIDATE FOR MIGRATION
**Purpose:** Scoring calculations and formatting
**Dependencies:** pandas, numpy
**Streamlit Dependencies:** ❌ NONE

**Functions:**
```python
format_vs_par_value(value: float) -> str                                    # Type: PURE
prepare_average_scores_by_par(all_data: pd.DataFrame) -> pd.DataFrame      # Type: PURE  
format_scoring_stats_columns(df: pd.DataFrame) -> pd.DataFrame             # Type: PURE
calculate_multi_score_running_sum(...)                                      # Type: PURE
summarize_multi_score_running_sum(...)                                      # Type: PURE
```

**Migration Target:** `teg_analysis/analysis/scoring.py`
**Priority:** 🔴 HIGH

---

#### `helpers/scoring_achievements_processing.py`
**Category:** 🧮 ANALYSIS
**Status:** ✅ GOOD CANDIDATE FOR MIGRATION
**Purpose:** Eagles, birdies, pars analysis
**Dependencies:** pandas, numpy
**Streamlit Dependencies:** ❌ NONE

**Functions:**
```python
get_scoring_achievement_fields() -> list[list[str]]                        # Type: PURE
create_achievement_tab_labels(chart_fields_all) -> list[str]              # Type: PURE
format_achievement_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame    # Type: PURE
prepare_achievement_table_data(scoring_stats, chart_fields) -> pd.DataFrame # Type: PURE
```

**Migration Target:** `teg_analysis/analysis/achievements.py`
**Priority:** 🔴 HIGH

---

#### `helpers/streak_analysis_processing.py`
**Category:** 🧮 ANALYSIS
**Status:** ✅ GOOD CANDIDATE FOR MIGRATION
**Purpose:** Streak calculations
**Dependencies:** pandas, numpy
**Streamlit Dependencies:** ❌ NONE

**Functions:** [TO BE DOCUMENTED]

**Migration Target:** `teg_analysis/analysis/streaks.py`
**Priority:** 🔴 HIGH

---

#### `helpers/score_count_processing.py`
**Category:** 🧮 ANALYSIS
**Status:** ✅ GOOD CANDIDATE FOR MIGRATION
**Purpose:** Score distribution analysis
**Dependencies:** pandas, numpy
**Streamlit Dependencies:** ❌ NONE

**Functions:**
```python
count_scores_by_player(data, field='GrossVP') -> pd.DataFrame             # Type: PURE
format_score_count_display(count_data, score_field, display_name) -> pd.DataFrame  # Type: PURE
prepare_chart_data_with_special_handling(...) -> pd.DataFrame             # Type: PURE
convert_counts_to_percentages(count_data: pd.DataFrame) -> pd.DataFrame   # Type: PURE
```

**Migration Target:** `teg_analysis/analysis/score_distribution.py`
**Priority:** 🟡 MEDIUM

---

#### `helpers/display_helpers.py`
**Category:** 🎯 HELPER (FORMATTING)
**Status:** ⚠️ NEEDS REVIEW
**Purpose:** Data formatting for display
**Dependencies:** pandas

**Functions:** [TO BE DOCUMENTED - likely mix of pure formatting and UI-specific]

**Migration Target:** Mix of `teg_analysis/formatters/` and `streamlit/streamlit_utils.py`
**Priority:** 🟡 MEDIUM

---

#### `helpers/latest_round_processing.py`
**Category:** 🧮 ANALYSIS
**Status:** ✅ GOOD CANDIDATE FOR MIGRATION
**Purpose:** Current round/tournament analysis
**Dependencies:** pandas

**Functions:** [TO BE DOCUMENTED]

**Migration Target:** `teg_analysis/analysis/current_tournament.py`
**Priority:** 🔴 HIGH (for live tournament feature)

---

#### `helpers/data_update_processing.py`
**Category:** 📊 DATA + 🧮 ANALYSIS (MIXED)
**Status:** ⚠️ NEEDS SPLITTING
**Purpose:** Data update workflow
**Dependencies:** pandas, streamlit

**Functions:** [TO BE DOCUMENTED]

**Migration Targets:** 
- Data operations → `teg_analysis/core/data_writer.py`
- Validation logic → `teg_analysis/core/validators.py`
- UI workflow → Stays in streamlit/

**Priority:** 🟡 MEDIUM

---

#### `helpers/data_deletion_processing.py`
**Category:** 📊 DATA + 🧮 ANALYSIS (MIXED)
**Status:** ⚠️ NEEDS SPLITTING
**Purpose:** Data deletion workflow
**Dependencies:** pandas, streamlit

**Functions:**
```python
create_timestamped_backups() -> tuple[str, str]                           # Type: IO
preview_deletion_data(...) -> pd.DataFrame                                 # Type: PURE
execute_data_deletion(...)                                                 # Type: IO
```

**Migration Targets:**
- Backup operations → `teg_analysis/core/backup.py`
- Data filtering → Pure analysis
- UI workflow → Stays in streamlit/

**Priority:** 🟢 LOW

---

#### `helpers/commentary_generator.py`
**Category:** 📝 COMMENTARY + 🧮 ANALYSIS (MIXED)
**Status:** ⚠️ NEEDS REVIEW
**Purpose:** Tournament report generation orchestration
**Dependencies:** Various

**Functions:** [TO BE DOCUMENTED]

**Migration Target:** Likely stays separate as commentary system, but validate dependencies
**Priority:** 🟢 LOW (separate concern)

---

### Streamlit Pages (streamlit/pages/)

**Total:** 30+ page files

#### Refactored Pages (Following Template) ✅
- `300TEG Records.py`
- `102TEG Results.py`
- `400scoring.py`
- `1000Data update.py`
- `101TEG History.py`
- `scorecard_v2.py`

#### Pages to Refactor 🚧
[TO BE DOCUMENTED - All remaining pages listed in REFACTORING_TEMPLATE.md]

---

### Administrative Files

#### `streamlit/admin_volume_management.py`
**Category:** 🔧 ADMIN
**Status:** ⚪ KEEP (Railway-specific)
**Purpose:** GitHub ↔ Railway volume sync
**Dependencies:** requests, streamlit, github

**Functions:** [TO BE DOCUMENTED - All administrative]

**Migration Decision:** STAYS (deployment-specific)

---

#### `streamlit/commentary_runner.py`
**Category:** 🔧 ADMIN
**Status:** ⚪ KEEP (UI for commentary)
**Purpose:** UI for running commentary generation
**Dependencies:** streamlit

**Migration Decision:** STAYS (Streamlit UI)

---

### Commentary System (streamlit/commentary/)

**Category:** 📝 COMMENTARY
**Status:** 🔍 NEEDS SEPARATE REVIEW

**Files:**
- `generate_tournament_commentary_v2.py`
- `generate_round_report.py`
- `prompts.py`
- `pattern_analysis.py`
- [Others TO BE DOCUMENTED]

**Note:** Commentary system is a separate subsystem that may have its own refactoring needs

---

## Utils.py Detailed Inventory

### Section 1: Configuration & Setup

| Function Name | Lines | Type | Dependencies | Migration Target | Priority |
|--------------|-------|------|--------------|------------------|----------|
| `get_page_layout()` | 10 | UI | streamlit, page_config | KEEP in streamlit_utils.py | ⚪ |
| `clear_all_caches()` | 3 | UI | streamlit | KEEP in streamlit_utils.py | ⚪ |
| `get_base_directory()` | 15 | IO | pathlib | teg_analysis/core/paths.py | 🟡 |
| `get_current_branch()` | 20 | IO | subprocess, os | teg_analysis/core/env.py | 🟡 |
| [MORE TO DOCUMENT] | | | | | |

### Section 2: Data Loading

| Function Name | Lines | Type | Dependencies | Migration Target | Priority |
|--------------|-------|------|--------------|------------------|----------|
| `read_from_github()` | 30 | IO | github, pandas | teg_analysis/core/data_loader.py | 🔴 |
| `read_text_from_github()` | 20 | IO | github | teg_analysis/core/data_loader.py | 🔴 |
| `write_to_github()` | 40 | IO | github, pandas | teg_analysis/core/data_writer.py | 🔴 |
| `write_text_to_github()` | 25 | IO | github | teg_analysis/core/data_writer.py | 🔴 |
| `batch_update_github()` | 60 | IO | github, pandas | teg_analysis/core/data_writer.py | 🔴 |
| `read_file()` | 25 | IO | pandas | teg_analysis/core/data_loader.py | 🔴 |
| `write_file()` | 30 | IO | pandas | teg_analysis/core/data_writer.py | 🔴 |
| `load_all_data()` | 40 | IO+PURE | pandas | teg_analysis/core/data_loader.py | 🔴 |
| [MORE TO DOCUMENT] | | | | | |

### Section 3: Scoring & Analysis

| Function Name | Lines | Type | Dependencies | Migration Target | Priority |
|--------------|-------|------|--------------|------------------|----------|
| `score_type_stats()` | ? | PURE | pandas | teg_analysis/analysis/scoring.py | 🔴 |
| `max_scoretype_per_round()` | ? | PURE | pandas | teg_analysis/analysis/scoring.py | 🔴 |
| `max_scoretype_per_teg()` | ? | PURE | pandas | teg_analysis/analysis/scoring.py | 🔴 |
| `apply_score_types()` | ? | PURE | pandas | teg_analysis/analysis/scoring.py | 🔴 |
| [MORE TO DOCUMENT] | | | | | |

### Section 4: Formatting & Display

| Function Name | Lines | Type | Dependencies | Migration Target | Priority |
|--------------|-------|------|--------------|------------------|----------|
| `format_vs_par()` | 10 | PURE | none | teg_analysis/formatters/display.py | 🔴 |
| `load_datawrapper_css()` | 15 | UI | streamlit | KEEP in streamlit_utils.py | ⚪ |
| `load_teg_reports_css()` | 15 | UI | streamlit | KEEP in streamlit_utils.py | ⚪ |
| [MORE TO DOCUMENT] | | | | | |

### Section 5: Navigation & UI

| Function Name | Lines | Type | Dependencies | Migration Target | Priority |
|--------------|-------|------|--------------|------------------|----------|
| `add_custom_navigation_links()` | 80 | UI | streamlit | KEEP in streamlit_utils.py | ⚪ |
| `add_section_navigation_links()` | 60 | UI | streamlit | KEEP in streamlit_utils.py | ⚪ |
| `create_custom_navigation_section()` | 40 | UI | streamlit | KEEP in streamlit_utils.py | ⚪ |
| `apply_custom_navigation_css()` | 30 | UI | streamlit | KEEP in streamlit_utils.py | ⚪ |
| `get_app_base_url()` | 10 | UI | streamlit | KEEP in streamlit_utils.py | ⚪ |
| `convert_filename_to_streamlit_url()` | 15 | UI | none | KEEP in streamlit_utils.py | ⚪ |
| [MORE TO DOCUMENT] | | | | | |

---

## Function Inventory (Master List)

### Template for Each Function

```markdown
#### `function_name()`
- **File:** path/to/file.py
- **Lines:** 10-50
- **Type:** PURE | UI | IO | MIXED
- **Purpose:** Brief description
- **Parameters:** 
  - `param1` (type): description
  - `param2` (type): description
- **Returns:** return_type - description
- **Dependencies:**
  - External: pandas, numpy
  - Internal: other_function()
  - Streamlit: Yes/No
- **Used By:** 
  - page1.py
  - page2.py
- **Duplicates:** Similar to function_x() in file_y.py
- **Migration Target:** teg_analysis/module/file.py
- **Priority:** 🔴/🟡/🟢/⚪
- **Notes:** Any special considerations
```

---

## Dependency Map

### Page Dependencies (Example - needs completion)

```
400scoring.py
├── utils.load_all_data()
├── utils.score_type_stats()
├── utils.max_scoretype_per_round()
├── utils.load_datawrapper_css()
├── helpers/scoring_data_processing.format_vs_par_value()
├── helpers/scoring_data_processing.prepare_average_scores_by_par()
└── helpers/scoring_data_processing.format_scoring_stats_columns()
```

**Dependency Analysis:**
- ✅ All analysis functions are pure (no Streamlit)
- ⚠️ load_datawrapper_css() is Streamlit-specific
- 🔴 utils functions need to be moved to teg_analysis

---

## Duplication Analysis

### Identified Duplicates

#### Score Formatting Functions
**Functions:**
1. `utils.format_vs_par()` - Main implementation
2. `helpers/scoring_data_processing.format_vs_par_value()` - Duplicate?
3. `helpers/display_helpers.format_vs_par()` - Another duplicate?

**Resolution:** [TO BE DETERMINED after full audit]

---

#### Data Loading Patterns
**Functions:**
1. `utils.load_all_data()` - Main loader
2. `utils.read_file()` - Generic file reader
3. Various page-specific data loading

**Resolution:** [TO BE DETERMINED]

---

## Migration Planning Matrix

| Current Location | Function/Module | New Location | Dependencies to Update | Estimated Effort |
|------------------|-----------------|--------------|----------------------|------------------|
| utils.py | `load_all_data()` | teg_analysis/core/data_loader.py | 30+ pages | 2 hours |
| utils.py | Scoring functions | teg_analysis/analysis/scoring.py | 10+ pages | 3 hours |
| helpers/scoring_data_processing.py | All functions | teg_analysis/analysis/scoring.py | 5 pages | 1 hour |
| [MORE TO ADD] | | | | |

---

## Next Steps

### Phase 1: Complete Documentation (CURRENT)
- [ ] Document all functions in utils.py
- [ ] Document all helper modules
- [ ] Document all page files
- [ ] Map all dependencies
- [ ] Identify all duplicates
- [ ] Create complete migration matrix

### Phase 2: Planning
- [ ] Prioritize migrations
- [ ] Design new module structure
- [ ] Plan breaking changes
- [ ] Create migration order

### Phase 3: Execution
- [ ] Move core data loading
- [ ] Move domain-specific analysis
- [ ] Update all imports
- [ ] Test each migration

---

## Subagent Tasks

### Task 1: Utils.py Function Inventory
**Agent:** Subagent 1
**Output:** Complete function list with signatures, purposes, dependencies
**File:** UTILS_INVENTORY.md

### Task 2: Helper Modules Inventory
**Agent:** Subagent 2
**Output:** Complete documentation of all helper modules
**File:** HELPERS_INVENTORY.md

### Task 3: Page Files Inventory
**Agent:** Subagent 3
**Output:** List all pages with their dependencies
**File:** PAGES_INVENTORY.md

### Task 4: Dependency Graph
**Agent:** Subagent 4
**Output:** Visual dependency map
**File:** DEPENDENCIES.md + dependency_graph.png

### Task 5: Duplication Report
**Agent:** Subagent 5
**Output:** All duplicate/similar functions identified
**File:** DUPLICATES.md

---

## Documentation Status - ALL TASKS COMPLETE ✅

### Completed Documentation

- ✅ **Utils.py:** 102 functions documented across 17 files
- ✅ **Helpers:** 20 modules (173 functions) documented across 6 files
- ✅ **Pages:** 40 pages (235 functions) documented across 8 files
- ✅ **Dependencies:** Complete dependency map across 79 files
- ✅ **Duplicates:** 530 functions analyzed, all duplicates identified

### Documentation Files Created

**Total:** 50+ markdown files + 2 JSON data files

**For detailed information, see:**
- [README.md](README.md) - Documentation package overview
- [MASTER_DOCUMENTATION_GUIDE.md](MASTER_DOCUMENTATION_GUIDE.md) - Task completion summary
- Individual inventory files for each component

**Last Updated:** 2025-10-18
**Status:** Ready for refactoring phase
