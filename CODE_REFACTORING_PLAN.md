# TEG Codebase Refactoring Plan

## Context
The TEG golf tournament analysis codebase needs to be made more maintainable and understandable for a Python beginner. Currently there are inconsistencies in structure, duplicated functions, and mixed responsibilities within page files.

## Target Architecture Approach

### ✅ Your Proposed Approach is Excellent Because:

1. **Separation of Concerns**: Data logic separate from UI logic
2. **Single Responsibility**: Each function has one clear purpose  
3. **Readability**: Clear comments explain what and why
4. **Maintainability**: Changes to data processing don't affect UI code
5. **Beginner-Friendly**: Easy to understand the flow of each page

### 📋 Recommended Page Structure Pattern

```python
# === IMPORTS === 
import streamlit as st
# ... other imports from utils

# === DATA LOADING ===
# Load complete TEG data only (excludes TEG 50 and incomplete TEGs)
# This ensures consistent historical analysis for trophy winners
all_data = load_all_data(exclude_incomplete_tegs=True, exclude_teg_50=True)

# Load round-level data including incomplete TEGs
# Needed for leaderboard display of current tournament in progress  
round_data = get_round_data(ex_50=True, ex_incomplete=False)

# === PAGE CONFIGURATION ===
st.title("Page Name")
load_datawrapper_css()  # Standard table styling

# === UI COMPONENTS ===
# Simple, clean Streamlit code with clear function calls
# display_leaderboard() - Shows formatted leaderboard with ranking
display_leaderboard(data, 'Stableford', 'TEG Trophy', 'Champion', False)
```

### 🏗️ Utility Organization Strategy

**Current Utils Files:**
- `utils.py` - Core data operations (1589 lines - needs breaking up)
- `leaderboard_utils.py` - Leaderboard-specific functions ✅ Good example

**Proposed Utils Structure:**
```
utils/
├── data_loading.py      # Core data loading (load_all_data, get_round_data, etc.)
├── data_processing.py   # Data transformations (add_cumulative_scores, etc.) 
├── display_helpers.py   # UI formatting (format_vs_par, create_stat_section)
├── chart_helpers.py     # Chart creation and configuration
└── leaderboard_utils.py # Leaderboard functions (already created ✅)
```

### 📊 Data Loading Patterns by Use Case

**Complete TEG Analysis** (exclude incomplete TEGs, exclude TEG 50):
- TEG History, TEG Records, Personal Bests
- *Reason*: Need consistent complete tournaments for historical analysis

**Current Tournament Tracking** (include incomplete TEGs, exclude TEG 50):
- Leaderboards, Latest Round, Scorecard
- *Reason*: Need to show current tournament progress

**Detailed Scoring Analysis** (include incomplete TEGs, exclude TEG 50):
- Scoring stats, Streaks, Round-level records
- *Reason*: Need all available data for granular statistics

**Special Cases**:
- Data Update pages might have different requirements
- Each page's data loading will be clearly commented with reasoning

## Implementation Plan

### Phase 1: Foundation & Pattern Setting
**Goal**: Establish clear patterns with 2-3 representative pages

**Target Pages for Phase 1:**
1. `102TEG Results.py` - Recently cleaned, good complexity example
2. `300TEG Records.py` - Simple structure, clear data needs
3. `400scoring.py` - Data-heavy page, good for extraction practice

**Tasks:**
- [ ] Create utils/ directory structure
- [ ] Document current data loading patterns across all pages
- [ ] Extract display helper functions from target pages
- [ ] Add clear data loading comments with reasoning
- [ ] Create page structure template

### Phase 2: Core Functional Pages
**Target Pages:**
- `101TEG History.py`
- `leaderboard.py` (enhance comments)
- `1000Data update.py`
- `scorecard_v2.py`

### Phase 3: Specialized & Remaining Pages
**Target Pages:**
- All other pages following established patterns

## Current State - Data Loading Audit

### Pages & Their Data Needs:
- `101TEG History.py`: Complete TEGs only (exclude_incomplete_tegs=True, exclude_teg_50=True)
- `102TEG Results.py`: All data (no exclusions) - *for tournament selection*
- `leaderboard.py`: Excludes TEG 50 only (ex_teg_50=True) - *for current leaderboard*  
- `400scoring.py`: Includes incomplete TEGs (exclude_incomplete_tegs=False) - *for all scoring data*
- `300TEG Records.py`: Uses ranked complete data - *for historical records*

**✅ These are all intentionally different and correct for each page's purpose**

## Success Metrics
- [ ] Every data loading call has clear comment explaining what and why
- [ ] All pages follow consistent structure pattern
- [ ] Utils files are organized and under 500 lines each
- [ ] No function duplication across pages
- [ ] Clear separation between data loading, processing, and UI
- [ ] Easy for Python beginners to understand page flow

## Progress Log

### ✅ Phase 1 Progress

**Completed:**
- [x] Created `helpers/` directory structure (renamed to avoid utils.py conflict)
- [x] Created `helpers/display_helpers.py` - Reusable display formatting functions
- [x] Created `helpers/records_css.py` - Page-specific CSS organization  
- [x] Created `helpers/scoring_data_processing.py` - Complex data processing functions
- [x] **Refactored `300TEG Records.py`** - ✨ **SIMPLE TEMPLATE EXAMPLE** ✨
- [x] **Refactored `102TEG Results.py`** - ✨ **COMPLEX PAGE EXAMPLE** ✨
- [x] **Refactored `leaderboard.py`** - ✨ **CONSISTENT STRUCTURE** ✨  
- [x] **Refactored `400scoring.py`** - ✨ **DATA-HEAVY EXAMPLE** ✨

**300TEG Records.py Transformation:**
- **Before**: 127 lines, mixed responsibilities, embedded CSS, local functions
- **After**: 94 lines, clear structure, commented sections, extracted utilities

**Key Improvements Made:**
1. **Clear data loading section** with purpose comments explaining WHY each dataset is loaded
2. **Extracted helper functions** to `utils/display_helpers.py` 
3. **Organized CSS** into separate `utils/records_css.py`
4. **Function call comments** explaining what each function does
5. **Section structure** with clear headers and organization
6. **Beginner-friendly** - easy to understand the flow

**New Structure Pattern Established:**
```python
# === IMPORTS === (organized by source)
# === DATA LOADING === (with purpose comments) 
# === PAGE CONFIGURATION === (title, CSS)
# === UI COMPONENTS === (clean Streamlit code with comments)
```

## Next Steps
1. **Apply pattern to 102TEG Results.py** - More complex example
2. **Apply pattern to 400scoring.py** - Data-heavy example  
3. **Document the template pattern** for future pages

---

**Status**: Phase 1 In Progress - Template Established ✅  
**Last Updated**: 2025-01-09  
**Current Focus**: Applying pattern to remaining Phase 1 pages