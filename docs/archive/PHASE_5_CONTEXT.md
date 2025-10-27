# Phase 5 Context: Background, Decisions, and Architecture

**READ THIS FIRST** before executing any Phase 5 tasks.

---

## 📖 PROJECT HISTORY

### The Journey So Far

**Phase I** (Complete): I/O Layer
- Migrated 26 functions for file and GitHub operations
- Created `teg_analysis/io/`

**Phase II** (Complete): Core Layer
- Migrated 23 functions for data loading and transformation
- Created `teg_analysis/core/`

**Phase III & IV** (Complete): Analysis + Display Layers
- Migrated 202 functions from 19 helper modules
- Created `teg_analysis/analysis/` and `teg_analysis/display/`

**Phase V** (This Phase): Complete UI Independence
- Make `teg_analysis` truly framework-agnostic
- Remove all Streamlit dependencies from core

### Why Phase 5 is Needed

Despite migrating 202 functions, the package is NOT yet UI-independent because:

1. **Streamlit Dependencies Embedded**
   - 23 `import streamlit` statements in analysis code
   - 42 calls to `st.error()`, `st.warning()`, `st.button()`, etc.
   - Functions show UI elements instead of returning data

2. **Incomplete Migration**
   - 83 calculation functions still in `streamlit/utils.py`
   - ~39 never made it to `teg_analysis`
   - ~20+ duplicates exist in both places

3. **Cannot Use Elsewhere**
   - `import teg_analysis` fails without Streamlit installed
   - Cannot use in FastAPI, Dash, Jupyter, CLI
   - Tied to one UI framework

---

## 🎯 USER REQUIREMENTS

### Primary Objective
> "The brief was to centralize the analysis so it could be used with alternative UIs."

### Specific Requirements (from user)

1. **UI Independence**
   - Calculations must return data only (Option B chosen)
   - No Streamlit dependencies in core calculations
   - Usable with any framework

2. **Streamlit App Must Continue Working**
   - Existing Streamlit app stays functional
   - No breaking the current UI

3. **Wrapper Pattern (User Choice: 1C)**
   - Keep original functions in `utils.py` as Streamlit wrappers
   - Wrappers call `teg_analysis` internally
   - Thin delegation layer

4. **Cache Management (User Choice: 2C)**
   - Cache functions stay in `utils.py` as Streamlit utilities
   - `st.cache_data`, cache clearing, etc. are UI-specific

5. **Error Handling (User Choice: 3)**
   - Handled within Streamlit-specific folders
   - Pure functions raise exceptions or return error data
   - UI layer displays errors with `st.error()`

6. **Full Page Updates (User Choice: 5C)**
   - Update ALL 57 Streamlit pages to use new architecture
   - No partial migration

---

## 🏗️ ARCHITECTURE DECISIONS

### The Three-Layer Pattern

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: teg_analysis (Pure Calculations)              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  • NO UI dependencies                                   │
│  • Returns: DataFrames, dicts, lists, primitives        │
│  • Errors: Raises exceptions (ValueError, RuntimeError) │
│  • Framework agnostic                                   │
│  • Installable as standalone package                    │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ imports
                          │
┌─────────────────────────────────────────────────────────┐
│  Layer 2: streamlit/utils.py (UI Wrappers)              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  • Imports from teg_analysis                            │
│  • Adds: @st.cache_data decorators                      │
│  • Handles: st.error(), st.warning() display            │
│  • Provides: Streamlit-optimized functions              │
│  • Thin layer - just wraps, doesn't reimplement        │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ imports
                          │
┌─────────────────────────────────────────────────────────┐
│  Layer 3: streamlit/*.py (UI Pages)                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  • Uses utils.py wrappers (cached, error-handled)       │
│  • Can import teg_analysis directly for advanced use    │
│  • Contains: Layout, display logic, user interaction    │
│  • NO business logic - only presentation                │
└─────────────────────────────────────────────────────────┘
```

### Design Principles

**1. Separation of Concerns**
- **Calculation** (what to compute) → teg_analysis
- **Presentation** (how to show) → Streamlit pages
- **Integration** (connecting them) → utils.py

**2. Pure Functions**
```python
# GOOD: Pure calculation
def calculate_winners(data: pd.DataFrame) -> pd.DataFrame:
    """Returns winner DataFrame."""
    return data.groupby('TEG').first()

# BAD: Mixed calculation + UI
def calculate_winners(data: pd.DataFrame):
    """Calculates and displays winners."""
    winners = data.groupby('TEG').first()
    st.dataframe(winners)  # ❌ UI in calculation
    return winners
```

**3. Dependency Direction**
```
Pages → Utils → teg_analysis
(Never: teg_analysis → Utils)
(Never: teg_analysis → Pages)
```

**4. Error Handling Pattern**
```python
# In teg_analysis: Raise exceptions
def load_data(path):
    if not path.exists():
        raise FileNotFoundError(f"Data not found: {path}")
    return pd.read_csv(path)

# In utils.py: Catch and display
@st.cache_data
def load_data_cached(path):
    try:
        return teg_analysis.load_data(path)
    except FileNotFoundError as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()
```

---

## 📋 KEY DECISIONS LOG

### Decision 1: Wrapper Pattern vs Direct Migration

**Options Considered:**
- A) Delete utils.py entirely, pages import teg_analysis directly
- B) Keep utils.py as thin wrapper layer (CHOSEN)

**Decision:** Option B
**Rationale:**
- Easier migration (change imports, not logic)
- Can add Streamlit optimizations (caching, error display)
- Provides stable API for pages
- Can deprecate gradually

### Decision 2: Error Handling Strategy

**Options Considered:**
- A) Return status dicts `{"success": bool, "error": str}`
- B) Raise Python exceptions (CHOSEN)

**Decision:** Option B
**Rationale:**
- More Pythonic
- Easier to debug (stack traces)
- Standard pattern for libraries
- UI layer can catch and display as needed

### Decision 3: Function Splitting Strategy

**For functions that mix calculation + UI:**

**Pattern:**
```python
# Original (in utils.py):
def show_winners(data):
    winners = data.groupby('TEG').first()
    st.dataframe(winners)
    st.success("Winners calculated!")

# After refactor:

# In teg_analysis/analysis/aggregation.py:
def calculate_winners(data: pd.DataFrame) -> pd.DataFrame:
    """Pure calculation - just returns data."""
    return data.groupby('TEG').first()

# In streamlit/utils.py:
def show_winners_ui(data):
    """UI wrapper - uses teg_analysis."""
    try:
        winners = teg_analysis.analysis.calculate_winners(data)
        st.dataframe(winners)
        st.success("Winners calculated!")
    except Exception as e:
        st.error(f"Error: {e}")
```

### Decision 4: Caching Strategy

**Keep Streamlit caching in utils.py:**
```python
# utils.py
@st.cache_data(ttl=3600)
def get_winners_cached(data):
    """Cached wrapper for Streamlit."""
    return teg_analysis.analysis.get_winners(data)
```

**Rationale:**
- Caching is UI framework-specific
- `@st.cache_data` is Streamlit feature
- Other UIs use different caching (Redis, etc.)
- Keep teg_analysis cache-agnostic

### Decision 5: Validation and Progress Functions

**Functions like `check_for_complete_and_duplicate_data()`:**

**Approach:** Return structured data
```python
# In teg_analysis:
def validate_data(data: pd.DataFrame) -> dict:
    """Returns validation results."""
    return {
        'is_valid': True/False,
        'errors': [...],
        'warnings': [...],
        'duplicates': [...],
        'missing': [...]
    }

# In utils.py:
def display_validation_ui(data):
    """Displays validation results."""
    results = teg_analysis.validate_data(data)

    if not results['is_valid']:
        st.error("Validation failed!")
        for error in results['errors']:
            st.error(f"❌ {error}")

    if results['warnings']:
        for warning in results['warnings']:
            st.warning(f"⚠️ {warning}")
```

---

## 🔍 CODE ANALYSIS FINDINGS

### Current State Inventory

**File:** `streamlit/utils.py`
- **Total functions:** 100
- **I/O functions:** 17 (keep these)
- **Calculation functions:** 83 (need action)
  - **In teg_analysis:** 44 (duplicates - deduplicate)
  - **Not in teg_analysis:** 39 (need migration)

**Package:** `teg_analysis/`
- **Total functions:** 202 (from Phase III/IV)
- **With Streamlit imports:** 23 files
- **With st.* calls:** 42 calls across 5 files

**Pages:** `streamlit/`
- **Total page files:** 57
- **Import utils:** All 57
- **Need updating:** All 57

### Functions to Migrate by Destination

**To core/data_loader.py** (5 functions):
- load_all_data (duplicate)
- get_number_of_completed_rounds_by_teg
- get_incomplete_tegs (duplicate)
- exclude_incomplete_tegs_function (duplicate)
- load_and_prepare_handicap_data

**To core/transformations.py** (8 functions):
- process_round_for_all_scores (duplicate)
- check_hc_strokes_combinations (duplicate)
- add_cumulative_scores (duplicate)
- add_rankings_and_gaps (duplicate)
- reshape_round_data
- add_round_info (duplicate)
- summarise_existing_rd_data
- check_for_complete_and_duplicate_data

**To analysis/aggregation.py** (12 functions):
- create_round_summary (duplicate)
- create_round_events (duplicate)
- create_tournament_summary (duplicate)
- create_round_streaks_summary (duplicate)
- create_tournament_streaks_summary (duplicate)
- get_current_in_progress_teg_fast
- get_last_completed_teg_fast
- has_incomplete_teg_fast
- get_next_teg_and_check_if_in_progress
- get_next_teg_and_check_if_in_progress_fast
- filter_data_by_teg
- chosen_teg_context

**To analysis/pipeline.py** (3 functions):
- update_all_data
- save_to_parquet
- analyze_teg_completion

**To display/navigation.py** (8 new functions):
- add_custom_navigation_links
- add_section_navigation_links
- apply_custom_navigation_css
- create_custom_navigation_section
- convert_filename_to_streamlit_url
- get_app_base_url
- convert_trophy_name
- get_trophy_full_name

**To core/metadata.py** (3 new functions):
- get_teg_metadata
- load_course_info
- get_scorecard_data

### Streamlit Dependencies to Remove

**In aggregation.py** (42 calls):
- st.warning() - 8 times
- st.button() - 2 times
- st.spinner() - 2 times
- st.success() - 4 times
- st.error() - 4 times
- st.rerun() - 2 times
- st.cache_data.clear() - 2 times
- st.info() - 2 times
- st.session_state - 1 time

**Other files:**
- pipeline.py: UI progress indicators
- records.py: Display helpers
- scoring.py: Chart generation
- streaks.py: Data display

---

## 🎓 PATTERNS AND EXAMPLES

### Pattern 1: Pure Data Calculation

```python
# ✅ GOOD: Pure function in teg_analysis
def calculate_teg_winners(data: pd.DataFrame, teg_num: int) -> dict:
    """Calculate winners for a specific TEG.

    Args:
        data: Complete scoring data
        teg_num: TEG number to analyze

    Returns:
        dict: {'gross_winner': str, 'net_winner': str, 'spoon': str}

    Raises:
        ValueError: If teg_num not in data
    """
    teg_data = data[data['TEGNum'] == teg_num]

    if teg_data.empty:
        raise ValueError(f"TEG {teg_num} not found in data")

    return {
        'gross_winner': teg_data['GrossVP'].idxmin(),
        'net_winner': teg_data['NetVP'].idxmin(),
        'spoon': teg_data['NetVP'].idxmax()
    }
```

### Pattern 2: Streamlit Wrapper

```python
# ✅ GOOD: Wrapper in streamlit/utils.py
@st.cache_data(ttl=3600)
def get_teg_winners_cached(data: pd.DataFrame, teg_num: int) -> dict:
    """Cached Streamlit wrapper for calculate_teg_winners.

    Displays errors using st.error() if calculation fails.
    """
    try:
        return teg_analysis.analysis.calculate_teg_winners(data, teg_num)
    except ValueError as e:
        st.error(f"❌ Error: {e}")
        return {'gross_winner': None, 'net_winner': None, 'spoon': None}
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        logger.exception("Error calculating TEG winners")
        return {'gross_winner': None, 'net_winner': None, 'spoon': None}
```

### Pattern 3: Page Usage

```python
# ✅ GOOD: Page using wrapper
import streamlit as st
from utils import get_teg_winners_cached

st.title("TEG Winners")
data = load_data()
teg_num = st.number_input("TEG Number", value=18)

winners = get_teg_winners_cached(data, teg_num)

if winners['gross_winner']:
    st.success(f"🏆 Gross Winner: {winners['gross_winner']}")
    st.success(f"🥇 Net Winner: {winners['net_winner']}")
    st.info(f"🥄 Wooden Spoon: {winners['spoon']}")
```

### Pattern 4: Validation Functions

```python
# ✅ GOOD: Validation in teg_analysis
def validate_tournament_data(data: pd.DataFrame) -> dict:
    """Validate tournament data completeness.

    Returns:
        dict: {
            'valid': bool,
            'errors': list[str],
            'warnings': list[str],
            'duplicates': pd.DataFrame,
            'missing_rounds': list[int]
        }
    """
    errors = []
    warnings = []

    # Check required columns
    required = ['TEGNum', 'Player', 'Round', 'GrossVP']
    missing_cols = [c for c in required if c not in data.columns]
    if missing_cols:
        errors.append(f"Missing columns: {missing_cols}")

    # Check for duplicates
    duplicates = data[data.duplicated(subset=['TEGNum', 'Player', 'Round', 'Hole'])]
    if not duplicates.empty:
        warnings.append(f"Found {len(duplicates)} duplicate entries")

    # Check for missing rounds
    expected_rounds = 4
    actual_rounds = data.groupby('TEGNum')['Round'].nunique()
    incomplete = actual_rounds[actual_rounds < expected_rounds].index.tolist()
    if incomplete:
        warnings.append(f"TEGs with incomplete rounds: {incomplete}")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'duplicates': duplicates,
        'missing_rounds': incomplete
    }
```

---

## 🚫 ANTI-PATTERNS TO AVOID

### Anti-Pattern 1: UI in Calculations

```python
# ❌ BAD: UI mixed with calculation
def calculate_something(data):
    st.write("Calculating...")  # NO! This is UI
    result = data.sum()
    st.success(f"Result: {result}")  # NO! This is UI
    return result

# ✅ GOOD: Pure calculation
def calculate_something(data):
    return data.sum()
```

### Anti-Pattern 2: Framework-Specific Code

```python
# ❌ BAD: Streamlit session state in calculation
def get_cached_data():
    if 'data' not in st.session_state:  # NO!
        st.session_state.data = load_data()
    return st.session_state.data

# ✅ GOOD: Pure function, let wrapper handle caching
def load_data(path):
    return pd.read_csv(path)
```

### Anti-Pattern 3: Side Effects

```python
# ❌ BAD: Function modifies global state
def process_data(data):
    global processed_count  # NO!
    processed_count += 1
    st.write(f"Processed {processed_count} times")  # NO!
    return data.transform()

# ✅ GOOD: Pure function, no side effects
def process_data(data):
    return data.transform()
```

### Anti-Pattern 4: Hardcoded Paths

```python
# ❌ BAD: Hardcoded path
def load_data():
    return pd.read_csv("data/scores.csv")  # Breaks in other contexts

# ✅ GOOD: Path as parameter
def load_data(data_path: str):
    return pd.read_csv(data_path)
```

---

## 📚 REFERENCE MATERIALS

### Python Best Practices
- [PEP 8](https://pep8.org/) - Style Guide
- [PEP 257](https://www.python.org/dev/peps/pep-0257/) - Docstring Conventions
- [Type Hints](https://docs.python.org/3/library/typing.html)

### Architecture Patterns
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Separation of Concerns](https://en.wikipedia.org/wiki/Separation_of_concerns)
- [Dependency Inversion](https://en.wikipedia.org/wiki/Dependency_inversion_principle)

### Similar Projects
- [Scikit-learn](https://github.com/scikit-learn/scikit-learn) - Pure calculation library
- [Pandas](https://github.com/pandas-dev/pandas) - Framework-agnostic data analysis

---

## ✅ VALIDATION CHECKLIST

After reading this document, you should understand:

- [ ] Why Phase 5 is needed
- [ ] The three-layer architecture
- [ ] User requirements and decisions
- [ ] Pure function pattern
- [ ] Wrapper pattern
- [ ] Error handling strategy
- [ ] What to migrate where
- [ ] Anti-patterns to avoid
- [ ] How to validate your work

**Next:** Read the specific task document for your assigned phase.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-25
**Status:** 📋 Reference Material
