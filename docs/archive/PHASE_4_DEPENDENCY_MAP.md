# Phase 4, Task 4.1: Dependency Analysis & Resolution

**Status:** Planning Document
**Date:** 2025-10-25
**Scope:** All inter-module dependencies and circular dependency resolution

---

## Executive Summary

Analysis of dependencies between proposed teg_analysis modules. Identifies load order, potential circular dependencies, and strategies to resolve them.

**Key Finding:** Mostly linear dependency chain with one complex area (commentary generation).

---

## Part 1: Module Dependency Graph

### Dependency Hierarchy (Load Order)

```
LEVEL 0 (No dependencies on other teg_analysis modules):
├── teg_analysis/io/          (depends only on: os, pathlib, pandas, PyGithub)
│   ├── volume_operations.py
│   ├── file_operations.py
│   └── github_operations.py
│
LEVEL 1 (Depends on: I/O + external libs):
├── teg_analysis/core/        (depends on: io/, os, pandas, numpy, streamlit)
│   ├── data_loader.py
│   └── data_transforms.py
│
LEVEL 2 (Depends on: Core + external libs):
├── teg_analysis/analysis/    (depends on: io/, core/, pandas, numpy, streamlit)
│   ├── scoring.py            (depends on: core/)
│   ├── rankings.py           (depends on: core/)
│   ├── aggregation.py        (depends on: core/, scoring, rankings)
│   ├── streaks.py            (depends on: core/)
│   ├── records.py            (depends on: core/)
│   ├── pipeline.py           (depends on: core/, io/, all analysis modules)
│   └── commentary.py         (depends on: core/, all analysis modules)
│
LEVEL 3 (Depends on: Analysis + external libs):
├── teg_analysis/display/     (depends on: core/, analysis/, pandas, streamlit)
│   ├── formatters.py         (depends on: scoring, rankings, aggregation)
│   ├── tables.py             (depends on: scoring, aggregation)
│   └── charts.py             (depends on: formatters)
│
LEVEL 4 (Future):
└── teg_analysis/api/         (depends on: core/, analysis/, display/)
```

### Import Dependency Matrix

```
            | io | core | analysis | display | api
------------|----|----- |----------|---------|----
io          | -  |      |          |         |
core        | ✓  | -    |          |         |
scoring     | ✓  | ✓    | -        |         |
rankings    | ✓  | ✓    | -        |         |
aggregation | ✓  | ✓    | ✓✓       | -       |
streaks     | ✓  | ✓    | -        |         |
records     | ✓  | ✓    | -        |         |
pipeline    | ✓✓ | ✓✓   | ✓✓✓      | -       |
commentary  | ✓  | ✓    | ✓✓✓      | -       |
formatters  | ✓  | ✓    | ✓✓       | -       |
tables      | ✓  | ✓    | ✓✓       | -       |
charts      | ✓  | ✓    | ✓        | ✓       | -
api         | ✓  | ✓    | ✓        | ✓       | -

Legend:
✓   = Single dependency
✓✓  = Multiple dependencies
✓✓✓ = Heavy dependencies
-   = No dependency
```

---

## Part 2: Identified Dependencies by Module

### teg_analysis/io/ - No Internal Dependencies

```
IO Module Dependencies:
├── volume_operations.py
│   ├── External: os, pathlib, logging
│   └── Internal: None
├── file_operations.py
│   ├── External: os, pathlib, pandas, streamlit
│   ├── Internal: volume_operations._is_railway()
│   └── Internal: volume_operations._get_volume_path()
└── github_operations.py
    ├── External: pandas, PyGithub, base64
    └── Internal: None

Load Order: 1. volume_operations
            2. file_operations (depends on volume_operations)
            3. github_operations (independent)
```

### teg_analysis/core/ - Depends on I/O

```
Core Module Dependencies:
├── data_loader.py
│   ├── External: pandas, numpy, streamlit, logging
│   ├── Internal: io.file_operations.read_file()
│   └── Internal: io.file_operations.write_file()
└── data_transforms.py
    ├── External: pandas, numpy
    └── Internal: data_loader functions (for cumulative calculations)

Load Order: 1. io/ (all modules)
            2. core/data_loader
            3. core/data_transforms (may use data_loader results)
```

### teg_analysis/analysis/ - Most Complex

```
Analysis Module Dependencies:

scoring.py
├── Imports: core.data_loader, core.data_transforms
├── External: pandas, numpy, streamlit
└── Uses: load_all_data(), add_cumulative_scores()

rankings.py
├── Imports: core.data_loader, analysis.scoring
├── External: pandas, streamlit
└── Uses: get_net_competition_measure() [from scoring]

aggregation.py
├── Imports: core.data_loader, analysis.scoring, analysis.rankings
├── External: pandas, streamlit
└── Uses: Multiple functions from scoring and rankings

streaks.py
├── Imports: core.data_loader
├── External: pandas, numpy
└── Uses: load_all_data()

records.py
├── Imports: core.data_loader, analysis.aggregation
├── External: pandas
└── Uses: aggregation functions

pipeline.py  ** HEAVY DEPENDENCIES **
├── Imports: core.data_loader, core.data_transforms
├── Imports: io.file_operations, io.github_operations
├── Imports: analysis.scoring, analysis.aggregation, analysis.streaks
├── Imports: analysis.commentary
├── External: pandas, gspread, streamlit
└── Uses: update_all_data() - orchestrates all modules

commentary.py  ** HEAVY DEPENDENCIES **
├── Imports: core.data_loader, core.data_transforms
├── Imports: analysis.scoring, analysis.rankings, analysis.aggregation
├── Imports: analysis.streaks, analysis.records
├── External: pandas, numpy, streamlit, logging
└── Uses: create_round_summary() - needs data from multiple analysis modules

Load Order: 1. io/
            2. core/
            3. analysis/scoring
            4. analysis/rankings
            5. analysis/aggregation (depends on scoring + rankings)
            6. analysis/streaks (independent)
            7. analysis/records (depends on aggregation)
            8. analysis/pipeline (depends on all above + io)
            9. analysis/commentary (depends on most analysis modules)
```

### teg_analysis/display/ - Depends on Analysis + Core

```
Display Module Dependencies:

formatters.py
├── Imports: core.data_loader, analysis.scoring, analysis.rankings
├── External: pandas, streamlit
└── Uses: format_vs_par(), ordinal(), etc.

tables.py
├── Imports: core.data_loader, analysis.scoring, analysis.aggregation
├── External: pandas, streamlit
└── Uses: aggregate_data(), score_type_stats()

charts.py
├── Imports: analysis.*, display.formatters
├── External: pandas, plotly
└── Uses: format_chart_value()

Load Order: 1. io/, core/
            2. analysis/ (all modules)
            3. display/formatters
            4. display/tables
            5. display/charts
```

---

## Part 3: Circular Dependency Analysis

### Checked For Circular Dependencies

| Pair | Dependency | Risk | Mitigation |
|---|---|---|---|
| core ↔ io | None (one-way) | ✅ None | Safe |
| core ↔ analysis | core → analysis (one-way) | ✅ None | Safe |
| analysis.aggregation ↔ analysis.scoring | aggregation → scoring (one-way) | ✅ None | Safe |
| analysis.rankings ↔ analysis.scoring | rankings → scoring (one-way) | ✅ None | Safe |
| analysis.pipeline ↔ analysis.* | pipeline → all others (one-way) | ✅ None | Safe |
| analysis.commentary ↔ analysis.* | commentary → all others (one-way) | ✅ None | Safe |
| display ↔ analysis | display → analysis (one-way) | ✅ None | Safe |
| analysis.records ↔ analysis.aggregation | records → aggregation (one-way) | ✅ None | Safe |

**Result:** No circular dependencies detected! ✅

---

## Part 4: Streamlit Caching Dependencies

### Functions with @st.cache_data

**In teg_analysis/core/:**
- load_all_data()
- get_number_of_completed_rounds_by_teg()
- (4 more)

**In teg_analysis/analysis/:**
- get_complete_teg_data()
- get_round_data()
- get_teg_data_inc_in_progress()
- get_9_data()
- get_ranked_teg_data()
- get_ranked_round_data()
- get_ranked_frontback_data()
- (7 more)

### Caching Strategy

**Strategy:** Keep @st.cache_data in new modules (decided in Task 4.1)

```python
# teg_analysis/core/data_loader.py
import streamlit as st

@st.cache_data
def load_all_data() -> pd.DataFrame:
    """Load tournament data with caching"""
    ...

@st.cache_data
def process_round_for_all_scores() -> pd.DataFrame:
    """Process round data with caching"""
    ...
```

**Rationale:**
- Keeps performance during migration
- Familiar pattern to existing codebase
- Can refactor to Option B (wrapper caching) in Phase 5 if needed for API

**Note for Phase 5:** When designing REST API, move caching to wrapper layer in streamlit/utils.py

---

## Part 5: Migration Load Order (from Dependency Analysis)

### Phase I: Foundation (I/O Layer)
```
Dependencies: External libraries only
Risk: LOW
Duration: ~3 hours

1. teg_analysis/io/volume_operations.py
   - Helper functions for environment detection
   - No other teg_analysis dependencies

2. teg_analysis/io/file_operations.py
   - Depends on: volume_operations
   - Provides: read_file(), write_file(), backup_file()

3. teg_analysis/io/github_operations.py
   - Independent from other io modules
   - Provides: GitHub API operations
```

### Phase II: Core Data Processing
```
Dependencies: I/O only
Risk: LOW (but high impact on rest of system)
Duration: ~4 hours

1. teg_analysis/core/data_loader.py
   - Depends on: io.file_operations
   - Provides: load_all_data(), process_round_for_all_scores()
   - Critical: 40+ pages depend on load_all_data()

2. teg_analysis/core/data_transforms.py
   - Depends on: core.data_loader
   - Provides: add_cumulative_scores(), add_rankings_and_gaps()
```

### Phase III: Analysis Layer (Order Matters!)
```
Dependencies: Core + other analysis modules (order-dependent)
Risk: MEDIUM (complex interdependencies)
Duration: ~6 hours

1. teg_analysis/analysis/scoring.py
   - Depends on: core
   - Provides: format_vs_par(), get_net_competition_measure()
   - Required by: rankings, aggregation, display

2. teg_analysis/analysis/rankings.py
   - Depends on: core, scoring
   - Provides: add_ranks(), ordinal(), ranking functions

3. teg_analysis/analysis/aggregation.py
   - Depends on: core, scoring, rankings
   - Provides: aggregate_data(), get_complete_teg_data()

4. teg_analysis/analysis/streaks.py
   - Depends on: core (only)
   - Provides: Streak analysis functions
   - Can load in parallel with scoring/rankings

5. teg_analysis/analysis/records.py
   - Depends on: core, aggregation
   - Provides: Records identification

6. teg_analysis/analysis/commentary.py
   - Depends on: core, scoring, rankings, aggregation, streaks, records
   - Provides: create_round_summary(), create_round_events()
   - Load last (depends on all others)

7. teg_analysis/analysis/pipeline.py
   - Depends on: core, io, all other analysis modules
   - Provides: update_all_data()
   - Load last (orchestrates all modules)
```

### Phase IV: Display Layer
```
Dependencies: Core + Analysis
Risk: LOW (leaf modules)
Duration: ~2 hours

1. teg_analysis/display/formatters.py
   - Depends on: core, analysis
   - Provides: Value formatting functions

2. teg_analysis/display/tables.py
   - Depends on: core, analysis, formatters
   - Provides: Table generation functions

3. teg_analysis/display/charts.py
   - Depends on: core, analysis, display.formatters
   - Provides: Chart helper functions
```

---

## Part 6: Risk Mitigation Strategies

### Risk 1: Breaking load_all_data() Dependency
**Impact:** HIGH - affects 40+ pages
**Mitigation:**
- Test core/data_loader.py independently first
- Keep original utils.py function as wrapper during transition
- Gradual cutover: redirect imports one at a time

### Risk 2: Caching Context Loss
**Impact:** MEDIUM - performance degradation
**Mitigation:**
- Keep @st.cache_data decorators in place
- Test cache behavior in new modules
- Monitor performance metrics

### Risk 3: Complex Commentary Dependencies
**Impact:** MEDIUM - create_round_summary() depends on many modules
**Mitigation:**
- Migrate analysis layer completely before commentary
- Test commentary independently
- Verify data consistency with original

### Risk 4: Import Path Changes
**Impact:** MEDIUM - many files importing from utils
**Mitigation:**
- Create public API in teg_analysis/__init__.py
- Export commonly-used functions at package level
- Update imports incrementally

---

## Part 7: Import Organization

### teg_analysis/__init__.py - Public API

```python
# Core exports (most commonly used)
from teg_analysis.core.data_loader import (
    load_all_data,
    process_round_for_all_scores,
    add_cumulative_scores,
    add_rankings_and_gaps,
)

from teg_analysis.io.file_operations import (
    read_file,
    write_file,
)

from teg_analysis.analysis.aggregation import (
    aggregate_data,
    get_complete_teg_data,
    get_ranked_teg_data,
)

# Less common but still exported
from teg_analysis.analysis.scoring import (
    format_vs_par,
    get_net_competition_measure,
)

# ... more exports

__all__ = [
    # Core
    "load_all_data",
    "process_round_for_all_scores",
    # I/O
    "read_file",
    "write_file",
    # Analysis
    "format_vs_par",
    "aggregate_data",
    # ... complete list
]
```

### Usage Pattern (after refactoring)

```python
# Option 1: Import from teg_analysis (recommended for common functions)
from teg_analysis import load_all_data, aggregate_data

# Option 2: Import from submodule (for specific functions)
from teg_analysis.analysis.scoring import format_vs_par
from teg_analysis.io.file_operations import read_file
```

---

## Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| Circular Dependencies | ✅ None found | Safe to migrate |
| Load Order | ✅ Defined | I/O → Core → Analysis → Display |
| Caching Strategy | ✅ Decided | Keep @st.cache_data in modules |
| Risk Assessment | ✅ Documented | Mitigations in place |
| Import API | ✅ Designed | Public API in __init__.py |

**Status:** Ready for migration sequence planning (Task 4.2)

---

**Prepared by:** Claude Code (Phase 4 Executor)
**Date:** 2025-10-25
**Status:** Dependency Analysis Complete
