# TEG Streamlit Page Refactoring Template

This document provides the standardized structure for refactoring TEG Streamlit pages to improve maintainability and readability for Python beginners.

## Core Principles

1. **Clear Structure**: Follow 4-section pattern with descriptive comments
2. **Data Loading First**: Load all data at start with purpose explanations
3. **Extract Complex Functions**: Move data processing to helper modules
4. **Comment Function Calls**: Explain what each function does and why
5. **Preserve Existing Logic**: Different data loading patterns are intentional
6. **Beginner-Friendly**: Code should be readable by Python newcomers

## Standard Page Structure

```python
# === IMPORTS ===
import streamlit as st
import pandas as pd
# ... other standard imports

# Import data loading functions from main utils
from utils import load_all_data, other_needed_functions

# Import page-specific helper functions
from helpers.page_name_processing import (
    helper_function_1,
    helper_function_2,
    helper_function_3
)

# === CONFIGURATION ===
st.title('Page Title')

# Any page-specific configuration (CSS, settings, etc.)

# === DATA LOADING ===
# Clear comment explaining what data is needed and why
# Purpose: Explain why this specific data loading pattern is used
data = load_all_data(exclude_incomplete_tegs=True)  # or whatever is needed

# Additional data loading with purpose explanations
other_data = load_other_data()

# === USER INTERFACE ===
# Clean Streamlit UI code with function call comments

# helper_function_1() - Brief explanation of what this does
processed_data = helper_function_1(data)

# Display results
st.dataframe(processed_data)
```

## Completed Refactorings (Templates to Follow)

### Simple Pages
- **300TEG Records.py** (127→94 lines)
  - Template for simple data display pages
  - Minimal data processing, focus on clean presentation

### Complex Interactive Pages  
- **102TEG Results.py**
  - Template for pages with charts and interactive elements
  - Shows how to handle complex UI with clear structure

### Data-Heavy Analysis Pages
- **400scoring.py** (162→154 lines)
  - Template for pages with extensive data analysis
  - Multiple visualizations and calculations

### State Machine Pages
- **1000Data update.py** (184→159 lines)
  - Template for multi-step workflows
  - State management and error handling

### Core Functional Pages
- **101TEG History.py** (196→126 lines)
  - Historical data with tables and charts
- **scorecard_v2.py** (128→153 lines)
  - Interactive selection and display logic

## Helper Module Organization

### helpers/display_helpers.py
- Data formatting functions
- Table styling and presentation
- Value transformation for display

### helpers/[page]_data_processing.py  
- Page-specific data processing logic
- Complex calculations and transformations
- Data validation and preparation

## Data Loading Patterns (Preserve These!)

Different pages have different data requirements - **DO NOT standardize these**:

```python
# Records/History pages - exclude incomplete and TEG 50
load_all_data(exclude_incomplete_tegs=True, exclude_teg_50=True)

# Current tournament pages - include incomplete for live updates  
load_all_data(exclude_incomplete_tegs=False)

# Analysis pages - may exclude TEG 50 for statistical accuracy
load_all_data(exclude_teg_50=True)
```

## Extraction Guidelines

### Extract to Helpers:
- Functions >10 lines with clear purpose
- Complex data transformations
- Reusable logic across pages
- Data validation and preparation
- Chart/table formatting logic

### Keep in Main Page:
- Simple Streamlit UI calls
- Page-specific configuration
- Basic variable assignments
- Short conditional logic

## Comment Standards

### Data Loading Comments:
```python
# Load complete TEG data excluding incomplete tournaments
# Purpose: Historical analysis requires only completed tournaments for accurate records
all_data = load_all_data(exclude_incomplete_tegs=True)
```

### Function Call Comments:
```python
# calculate_running_averages() - Computes rolling averages for trend analysis
trend_data = calculate_running_averages(scoring_data, window_size=5)
```

### Section Comments:
```python
# === USER INTERFACE - CHART SELECTION ===
# === DATA PROCESSING ===  
# === RESULTS DISPLAY ===
```

## Remaining Pages to Refactor

### Phase 3 Priority Pages:
1. **301Best_TEGs_and_Rounds.py** - Personal bests analysis
2. **302Personal Best Rounds & TEGs.py** - Individual records  
3. **ave_by_course.py** - Course-specific analysis
4. **ave_by_par.py** - Par-based scoring analysis
5. **streaks.py** - Streak and consistency analysis

### Phase 4 Current Tournament Pages:
6. **latest_round.py** - Latest round display
7. **latest_teg_context.py** - Current tournament context
8. **birdies_etc.py** - Scoring achievement tracking

### Phase 5 Specialized Analysis:
9. **biggest_changes.py** - Performance change analysis
10. **bestball.py** - Team format analysis  
11. **sc_count.py** - Score distribution analysis
12. **teg_worsts.py** - Worst performance tracking

### Administrative/Utility Pages:
- **delete_data.py** - Data removal functionality
- **500Handicaps.py** - Handicap management

## Quality Checks

After refactoring each page:

1. ✅ **Structure**: Follows 4-section pattern
2. ✅ **Comments**: Data loading and function calls explained  
3. ✅ **Extraction**: Complex logic moved to helpers
4. ✅ **Functionality**: All features work as before
5. ✅ **Readability**: Code understandable to beginners
6. ✅ **Imports**: Clean helper module imports

## Future Improvements

- **FUTURE: Review all utils functions for duplications and improvements**
- **FUTURE: Change font styling on records pages**
- Consider consolidating similar data processing patterns
- Standardize chart styling across pages
- Improve error handling consistency