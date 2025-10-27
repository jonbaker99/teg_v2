# TEG Analysis Package - Architecture

**Version:** 1.0.0 (Phase 5 Complete)
**Last Updated:** 2025-01-27

---

## Overview

The `teg_analysis` package is a modular, UI-independent Python package for analyzing TEG (annual golf tournament) data. It separates pure business logic from UI concerns, enabling use with any Python framework (Streamlit, FastAPI, Dash, Django, Flask, CLI, Jupyter, etc.).

### Design Philosophy

1. **UI Independence:** Core logic has no UI dependencies
2. **Layer Separation:** Clear boundaries between I/O, core logic, analysis, and display
3. **Reusability:** Functions can be used in any context
4. **Testability:** Pure functions are easy to test
5. **Framework Agnostic:** Works with Streamlit, FastAPI, or any Python framework

---

## Package Structure

```
teg_analysis/
├── __init__.py              # Package entry point
├── io/                      # Input/Output operations
│   ├── file_operations.py   # File I/O (local, Railway volume cache)
│   ├── github_operations.py # GitHub API integration
│   └── volume_operations.py # Railway volume management
├── core/                    # Core business logic
│   ├── data_loader.py       # Data loading functions
│   ├── data_transforms.py   # Data transformation utilities
│   └── metadata.py          # TEG/round metadata operations
├── analysis/                # Analysis & calculations
│   ├── aggregation.py       # Data aggregation functions
│   ├── rankings.py          # Ranking & sorting logic
│   ├── scoring.py           # Scoring calculations
│   ├── records.py           # Records analysis
│   ├── streaks.py           # Streak calculations
│   ├── pipeline.py          # Data pipeline operations
│   └── commentary.py        # Commentary generation
└── display/                 # Display utilities
    ├── formatters.py        # Data formatting functions
    ├── tables.py            # Table generation
    ├── navigation.py        # Navigation helpers
    └── charts.py            # Chart utilities
```

---

## Layer Responsibilities

### 1. I/O Layer (`teg_analysis.io`)

**Purpose:** Handle all file and external service interactions

**Modules:**
- **file_operations.py:** Local file I/O with Railway volume caching
- **github_operations.py:** GitHub API integration for production deployment
- **volume_operations.py:** Railway volume cache management

**Key Functions:**
- `read_file(path)` - Read CSV/Parquet with automatic caching
- `write_file(path, data)` - Write data with GitHub sync
- File operations are environment-aware (local vs Railway)

**Dependencies:** pandas, PyGithub (for production)

**Note:** Currently has direct Streamlit imports for caching - needs refactoring for full UI independence

---

### 2. Core Layer (`teg_analysis.core`)

**Purpose:** Core business logic and data operations

**Modules:**
- **data_loader.py:** Load and prepare tournament data
- **data_transforms.py:** Transform and validate data
- **metadata.py:** TEG/round/course metadata operations

**Key Functions:**
- `load_all_data()` - Load complete tournament dataset
- `get_player_name(initials)` - Convert player codes to names
- `get_teg_metadata(teg_num)` - Get TEG/round metadata
- `get_scorecard_data()` - Get scorecard-specific data

**Dependencies:** pandas, numpy

**Note:** `data_loader.py` has direct Streamlit import - needs wrapping in try/except

---

### 3. Analysis Layer (`teg_analysis.analysis`)

**Purpose:** Perform calculations and analysis

**Modules:**
- **aggregation.py:** Aggregate data by player/TEG/round/hole
- **rankings.py:** Ranking, sorting, best/worst calculations
- **scoring.py:** Scoring rules and calculations
- **records.py:** Records analysis
- **streaks.py:** Streak calculations
- **pipeline.py:** Data processing pipelines
- **commentary.py:** Generate commentary from data

**Key Functions:**
- `aggregate_data(data, level)` - Aggregate to any level
- `filter_data_by_teg(data, teg_num)` - Filter by tournament
- `add_ranks(df)` - Add ranking columns
- `ordinal(n)` - Convert to ordinal (1st, 2nd, etc.)
- `get_teg_winners(df)` - Calculate tournament winners

**Dependencies:** pandas, numpy

**Note:** Several modules have direct Streamlit imports from `streamlit.utils` - needs refactoring

---

### 4. Display Layer (`teg_analysis.display`)

**Purpose:** Format data for presentation (UI-agnostic)

**Modules:**
- **formatters.py:** Format values for display
- **tables.py:** Table generation utilities
- **navigation.py:** Navigation helpers
- **charts.py:** Chart data preparation

**Key Functions:**
- `format_vs_par(value)` - Format score vs par (+3, -2, =)
- `convert_trophy_name(name)` - Convert trophy names
- `define_score_types(gross_vp)` - Categorize score types

**Dependencies:** pandas

**Note:** `tables.py` has direct Streamlit import - needs wrapping

---

## Dependency Flow

```
┌─────────────────┐
│   Application   │  (Streamlit, FastAPI, Dash, etc.)
│   (UI Layer)    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  teg_analysis   │
│    Package      │
└────────┬────────┘
         │
   ┌─────┴─────┬─────────┬─────────┐
   │           │         │         │
   ↓           ↓         ↓         ↓
┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
│  IO  │  │ Core │  │ Anal │  │ Disp │
└──────┘  └──────┘  └──────┘  └──────┘
```

**Design Principle:** Layers only depend downward, never upward

---

## Import Patterns

### Correct Usage

```python
# ✓ Direct import from teg_analysis
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import filter_data_by_teg
from teg_analysis.display.formatters import format_vs_par

data = load_all_data()
teg18 = filter_data_by_teg(data, 18)
```

### Also Supported (via Streamlit utils.py wrappers)

```python
# ✓ Import via utils.py wrappers (backward compatibility)
from utils import load_all_data, filter_data_by_teg, format_vs_par

data = load_all_data()
teg18 = filter_data_by_teg(data, 18)
```

### Incorrect Usage

```python
# ✗ Don't import Streamlit-specific wrappers
from streamlit.utils import some_streamlit_specific_function
```

---

## Streamlit Integration Layer

The `streamlit/utils.py` file serves as a **thin integration layer**:

**Responsibilities:**
1. Add `@st.cache_data` decorators for caching
2. Handle Streamlit-specific UI (st.error, st.warning)
3. Provide cached wrappers around teg_analysis functions
4. Manage Streamlit session state
5. CSS and navigation helpers

**Pattern:**
```python
# In streamlit/utils.py
@st.cache_data
def load_all_data_cached():
    """Streamlit wrapper with caching."""
    from teg_analysis.core.data_loader import load_all_data
    return load_all_data()
```

---

## Phase 5 Refactoring Summary

### What Was Accomplished

**Wave 1:** Cleaned teg_analysis package
- Created `metadata.py` and `navigation.py` modules
- Moved 9 functions from utils.py to teg_analysis
- Removed 40+ `st.*` calls from analysis modules

**Wave 2:** Deduplicated streamlit/utils.py
- Replaced 25 duplicate functions with thin wrappers
- Reduced code by 257 lines
- Established clear separation pattern

**Wave 3:** Skipped (not needed - wrappers maintain compatibility)

**Wave 4:** Validation & Documentation
- Created 4 test files
- Created FastAPI example
- Identified 9 remaining Streamlit imports to fix
- Created comprehensive documentation

### Known Issues (Wave 4 Testing)

The following files have direct Streamlit imports that should be wrapped in try/except:

1. `teg_analysis/core/data_loader.py` - 2 imports
2. `teg_analysis/analysis/aggregation.py` - 1 import
3. `teg_analysis/analysis/commentary.py` - 1 import
4. `teg_analysis/analysis/pipeline.py` - 2 imports
5. `teg_analysis/display/tables.py` - 1 import
6. `teg_analysis/io/file_operations.py` - 1 import
7. `teg_analysis/io/github_operations.py` - 1 import

**Recommendation:** Create a follow-up task to wrap these in conditional imports:

```python
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    st = None
    HAS_STREAMLIT = False
```

---

## Best Practices

### 1. Pure Functions

**Do:** Write pure functions in teg_analysis
```python
def calculate_score(data: pd.DataFrame) -> dict:
    """Pure calculation - no side effects."""
    result = data.sum()
    return {'total': result}
```

**Don't:** Mix UI and logic
```python
def calculate_score(data: pd.DataFrame):
    result = data.sum()
    st.write(f"Total: {result}")  # ✗ UI in business logic
```

### 2. Return Data, Don't Display It

**Do:** Return structured data
```python
def get_winners(df: pd.DataFrame) -> pd.DataFrame:
    return df.nsmallest(3, 'GrossVP')
```

**Don't:** Display directly
```python
def get_winners(df: pd.DataFrame):
    winners = df.nsmallest(3, 'GrossVP')
    st.dataframe(winners)  # ✗ Display in analysis function
```

### 3. UI-Specific Code in UI Layer

**Do:** Keep UI logic separate
```python
# In streamlit page
from teg_analysis.analysis import get_winners
winners = get_winners(data)
st.dataframe(winners)  # ✓ UI in UI layer
```

---

## Migration Guide

### For New UIs (FastAPI, Dash, etc.)

1. Import directly from teg_analysis:
```python
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import filter_data_by_teg
```

2. Handle caching in your framework:
```python
# FastAPI with caching
from functools import lru_cache

@lru_cache(maxsize=1)
def get_data():
    return load_all_data()
```

3. See [examples/example_fastapi.py](../examples/example_fastapi.py) for complete example

### For Existing Streamlit Pages

No changes required! Wrappers in `streamlit/utils.py` maintain backward compatibility.

Optionally, update imports to use teg_analysis directly for clarity:
```python
# Before
from utils import filter_data_by_teg

# After (optional)
from teg_analysis.analysis.aggregation import filter_data_by_teg
```

---

## Testing

Run validation tests:
```bash
# Test UI independence
python tests/test_independence.py

# Test core functions
python tests/test_core_functions.py

# Check for Streamlit imports
python tests/test_no_streamlit_imports.py

# Performance benchmarks
python tests/test_teg_analysis_performance.py
```

---

## Future Improvements

1. **Fix remaining Streamlit imports:** Wrap 9 direct imports in try/except blocks
2. **Add type hints:** Complete type annotations for all functions
3. **Create unit tests:** Comprehensive test coverage
4. **API documentation:** Auto-generate API docs with Sphinx
5. **Performance optimization:** Profile and optimize slow functions
6. **Async support:** Add async versions of I/O functions

---

## See Also

- [API_REFERENCE.md](API_REFERENCE.md) - Complete function reference
- [ALTERNATIVE_UIS.md](ALTERNATIVE_UIS.md) - Framework integration examples
- [PHASE_5_COMPLETION.md](PHASE_5_COMPLETION.md) - Phase 5 summary
- [examples/example_fastapi.py](../examples/example_fastapi.py) - FastAPI example
