# TASK 4: Complete Dependency Map

**Assigned To:** Subagent 4 / Manual Documentation
**Priority:** 🟡 HIGH
**Estimated Time:** 3-4 hours
**Status:** ⏳ NOT STARTED
**Prerequisites:** Tasks 1, 2, 3 must be completed first

---

## Objective

Create a complete dependency graph showing:
- What imports what
- Function call chains
- Circular dependencies (if any)
- Critical paths
- Migration impact analysis

---

## Dependency Types to Track

### 1. File-Level Dependencies

```
filename.py
├── imports from utils
├── imports from helpers
├── imports from other modules
└── external package imports
```

### 2. Function-Level Dependencies

```
page.calculate_scoreboard()
├── calls utils.load_all_data()
│   ├── calls read_from_github()
│   └── calls pandas.read_parquet()
├── calls helpers.scoring.format_scores()
└── calls pandas.groupby()
```

### 3. Data Flow Dependencies

```
Data Files → Loaders → Processors → Formatters → Display
```

---

## Output Formats

### 1. Text-Based Dependency Lists

For each file, create a dependency section:

```markdown
## File: `400scoring.py`

### Direct Imports
- `utils.py`
  - load_all_data()
  - score_type_stats()
  - max_scoretype_per_round()
  - load_datawrapper_css()
  
- `helpers/scoring_data_processing.py`
  - format_vs_par_value()
  - prepare_average_scores_by_par()
  - format_scoring_stats_columns()

- External packages:
  - streamlit
  - pandas
  - numpy

### Indirect Dependencies (transitive)
- utils.load_all_data() → read_from_github() → github API
- helpers.scoring → pandas operations

### Is Imported By
- [None - this is a page file]

### Call Graph
```
400scoring.py
├── load_all_data() [utils.py:150]
│   ├── read_from_github() [utils.py:75]
│   │   └── github.get_repo()
│   └── pandas.read_parquet()
├── score_type_stats() [utils.py:400]
│   └── apply_score_types() [utils.py:380]
└── prepare_average_scores_by_par() [helpers/scoring:25]
    └── pandas.groupby()
```
```

### 2. Matrix Format

Create import matrix showing what imports what:

```markdown
## Import Matrix

|                | utils | helpers/scoring | helpers/streaks | make_charts |
|----------------|-------|-----------------|-----------------|-------------|
| 400scoring.py  | ✅ 4  | ✅ 3           | ❌              | ❌          |
| streaks.py     | ✅ 5  | ❌             | ✅ 6           | ✅ 1        |
| scoring.py     | ✅ 2  | ❌             | ❌              | ❌          |

Legend:
- ✅ = imports from this module
- Number = count of imported functions
- ❌ = no imports
```

### 3. Dependency Depth Analysis

```markdown
## Dependency Layers

### Layer 0: No Dependencies (Pure/External Only)
- helpers/scoring_data_processing.py (only pandas/numpy)
- helpers/streak_analysis_processing.py (only pandas/numpy)

### Layer 1: Depends on Layer 0
- utils.py (depends on external packages only)

### Layer 2: Depends on Layer 1
- helpers/display_helpers.py (depends on utils)
- make_charts.py (depends on utils)

### Layer 3: Depends on Layer 2
- Page files (depend on utils, helpers)

### Circular Dependencies ⚠️
[List any circular dependencies found - these are problematic]
```

---

## Critical Path Analysis

Identify the "critical" functions that many others depend on:

```markdown
## Most Depended-Upon Functions

### 1. utils.load_all_data()
**Used by:** 32 files
**Impact:** 🔴 CRITICAL - Breaking change affects entire app
**Migration Priority:** Must migrate FIRST

### 2. utils.format_vs_par()
**Used by:** 18 files
**Impact:** 🔴 HIGH - Formatting function
**Migration Priority:** Early migration

### 3. helpers.scoring.format_scores()
**Used by:** 8 files
**Impact:** 🟡 MEDIUM
**Migration Priority:** Mid-phase

[Continue for top 10-15 critical functions]
```

---

## Migration Impact Matrix

For each planned migration, show impact:

```markdown
## Migration Impact: utils.load_all_data()

**Current Location:** utils.py line 150
**New Location:** teg_analysis/core/data_loader.py
**Migration Type:** MOVE (function stays same)

### Files Requiring Import Updates: 32

**High Priority Pages (10):**
- 400scoring.py - Line 15: `from utils import load_all_data`
- streaks.py - Line 12: `from utils import load_all_data`
[List all]

**Helper Modules (5):**
- helpers/display_helpers.py - Line 8
[List all]

**Other Files (17):**
[List all]

### Function Dependencies
- Calls: read_from_github(), get_current_branch()
- These must be migrated BEFORE or WITH this function

### Breaking Changes
- Import path changes from `utils` → `teg_analysis.core.data_loader`
- No signature changes
- No behavior changes

### Migration Strategy
1. Create new location
2. Copy function
3. Test new location
4. Update all imports (can be scripted)
5. Remove old location
6. Test entire app

### Estimated Update Time
- Automated import replacement: 10 minutes
- Manual testing: 30 minutes
- Total: 40 minutes
```

---

## Circular Dependency Detection

Check for problematic circular imports:

```markdown
## Circular Dependencies

### Check 1: utils ↔ helpers
- utils.py imports from helpers?: [Yes/No]
- helpers import from utils?: [Yes/No]
- Result: [SAFE / CIRCULAR DETECTED]

### Check 2: page ↔ page
- Do any pages import from other pages?: [Yes/No]
- Result: [SAFE / CROSS-CONTAMINATION]

### Check 3: helpers ↔ helpers
- helper_a imports helper_b?: [Yes/No]
- helper_b imports helper_a?: [Yes/No]
- Result: [SAFE / CIRCULAR DETECTED]

### Action Items
[List any circular dependencies that need breaking]
```

---

## Data Flow Diagram

Document the data flow through the system:

```markdown
## Data Flow

### Primary Data Path
```
GitHub Repository (all-scores.parquet)
    ↓
utils.read_from_github()
    ↓
utils.load_all_data()
    ↓ [filters applied]
pandas.DataFrame
    ↓
Page files / Helpers
    ↓ [calculations]
Processed DataFrames
    ↓ [formatting]
Display-ready data
    ↓
Streamlit display (st.dataframe, st.altair_chart, etc.)
```

### Alternative Paths
- Local development: Direct file read → pandas
- Cached data: st.cache_data → Skip GitHub
- User uploads: Streamlit file uploader → Processing

### Write Paths
```
User input (streamlit UI)
    ↓
Page file (data validation)
    ↓
Helper (data processing)
    ↓
utils.write_to_github()
    ↓
GitHub Repository
```
```

---

## Tools & Scripts

### Automated Dependency Extraction

```bash
# Find all imports
grep -r "^import \|^from " streamlit/ > imports.txt

# Find all function calls to a specific function
grep -rn "load_all_data()" streamlit/

# Create import graph (using Python)
python analyze_imports.py > dependency_graph.json
```

### Python Script for Analysis

```python
#!/usr/bin/env python3
"""
Analyze Python imports and create dependency graph.
"""

import ast
import os
from pathlib import Path
from collections import defaultdict

def analyze_file(filepath):
    """Extract imports from a Python file."""
    with open(filepath) as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return []
    
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
    
    return imports

def build_dependency_graph(root_dir):
    """Build complete dependency graph."""
    graph = defaultdict(list)
    
    for filepath in Path(root_dir).rglob("*.py"):
        imports = analyze_file(filepath)
        graph[str(filepath)] = imports
    
    return graph

# Run analysis
if __name__ == "__main__":
    graph = build_dependency_graph("streamlit/")
    # Output graph in desired format
```

---

## Output Files

### 1. `DEPENDENCIES.md`
Complete text-based dependency documentation

### 2. `dependency_graph.json`
Machine-readable dependency data

### 3. `migration_impact.md`
Impact analysis for each planned migration

### 4. Visual diagrams (optional)
- `dependency_graph.png` - Visual graph
- `data_flow.png` - Data flow diagram

---

## Success Criteria

- ✅ All file dependencies documented
- ✅ All function dependencies documented
- ✅ Critical paths identified
- ✅ Circular dependencies checked
- ✅ Migration impact assessed for each function
- ✅ Data flow documented
- ✅ Import matrix created
- ✅ Ready for migration planning
