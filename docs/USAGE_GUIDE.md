# TEG Analysis Package - Migration Guide

**Version:** 1.0.0 (Post-Refactor)
**Last Updated:** 2025-01-27

---

## Overview

This guide shows you how to use the `teg_analysis` package in your applications. The package is UI-independent and works with any Python framework.

**Supported frameworks:**
- ✅ Streamlit (existing integration)
- ✅ FastAPI / Flask / Django (REST APIs)
- ✅ Dash / Plotly (dashboards)
- ✅ Jupyter notebooks (analysis)
- ✅ CLI scripts (automation)

---

## Quick Start

### Basic Usage

```python
# Load all tournament data
from teg_analysis.core.data_loader import load_all_data
df = load_all_data()

# Filter to specific TEG
from teg_analysis.analysis.aggregation import filter_data_by_teg
teg_18 = filter_data_by_teg(df, 18)

# Get winners
from teg_analysis.analysis.aggregation import get_teg_winners
winners = get_teg_winners(df)

# Format scores
from teg_analysis.display.formatters import format_vs_par
score_text = format_vs_par(2)  # "+2"
```

### Installation

The package is already part of your codebase. No additional installation needed.

**Package location:** `teg_v2/teg_analysis/`

**To use in Python:**
```python
# If running from project root
import teg_analysis
from teg_analysis.core.data_loader import load_all_data

# If running from elsewhere, add to sys.path first
import sys
sys.path.append('/path/to/teg_v2')
import teg_analysis
```

---

## Framework-Specific Guides

### 1. Streamlit (Existing Integration)

**Current setup works perfectly** - no changes needed!

```python
# streamlit/pages/your_page.py
# Still works via wrappers in utils.py
from utils import load_all_data, get_teg_metadata
df = load_all_data()
metadata = get_teg_metadata(18)
```

**Optional: Use direct imports**
```python
# More explicit (but wrappers work fine too)
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.core.metadata import get_teg_metadata

df = load_all_data()
metadata = get_teg_metadata(18)

# Display with Streamlit
import streamlit as st
st.dataframe(df)
```

---

### 2. FastAPI (REST API)

**Create a REST API to serve TEG data:**

```python
# api/main.py
from fastapi import FastAPI, HTTPException
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.core.metadata import get_teg_metadata
from teg_analysis.analysis.aggregation import (
    get_current_in_progress_teg_fast,
    filter_data_by_teg,
    get_teg_winners
)

app = FastAPI(title="TEG Analysis API", version="1.0.0")

# Load data once at startup
@app.on_event("startup")
async def startup_event():
    global df
    df = load_all_data()

# GET /current - Get current TEG
@app.get("/current")
def get_current():
    teg_num, rounds = get_current_in_progress_teg_fast()
    return {"teg_num": teg_num, "rounds_played": rounds}

# GET /teg/{teg_num} - Get TEG metadata
@app.get("/teg/{teg_num}")
def get_teg(teg_num: int):
    metadata = get_teg_metadata(teg_num)
    if not metadata:
        raise HTTPException(status_code=404, detail="TEG not found")
    return metadata

# GET /teg/{teg_num}/data - Get TEG data
@app.get("/teg/{teg_num}/data")
def get_teg_data(teg_num: int):
    teg_data = filter_data_by_teg(df, teg_num)
    return teg_data.to_dict(orient='records')

# GET /winners - Get all TEG winners
@app.get("/winners")
def get_winners():
    winners = get_teg_winners(df)
    return winners.to_dict(orient='records')

# Run with: uvicorn api.main:app --reload
```

**Full example:** See `examples/example_fastapi.py` (248 lines)

---

### 3. Dash (Interactive Dashboard)

**Create an interactive dashboard:**

```python
# dashboard/app.py
import dash
from dash import dcc, html, Input, Output
import plotly.express as px
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import filter_data_by_teg, aggregate_data

# Load data
df = load_all_data()

# Create Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("TEG Analysis Dashboard"),

    # TEG selector
    dcc.Dropdown(
        id='teg-selector',
        options=[{'label': f'TEG {i}', 'value': i} for i in range(1, 19)],
        value=18
    ),

    # Chart
    dcc.Graph(id='scores-chart')
])

@app.callback(
    Output('scores-chart', 'figure'),
    Input('teg-selector', 'value')
)
def update_chart(teg_num):
    # Get TEG data
    teg_data = filter_data_by_teg(df, teg_num)
    player_summary = aggregate_data(teg_data, level='player')

    # Create chart
    fig = px.bar(
        player_summary,
        x='Player',
        y='GrossVP',
        title=f'TEG {teg_num} Results'
    )
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)

# Run with: python dashboard/app.py
```

---

### 4. Jupyter Notebook (Data Analysis)

**Explore data interactively:**

```python
# notebook.ipynb
import pandas as pd
import matplotlib.pyplot as plt
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import aggregate_data
from teg_analysis.analysis.rankings import add_ranks

# Load data
df = load_all_data()
print(f"Loaded {len(df)} rows")

# Aggregate to player level
player_summary = aggregate_data(df, level='player')

# Add rankings
player_summary = add_ranks(player_summary, 'GrossVP', ascending=True)

# Display top 10
player_summary.head(10)

# Plot
player_summary.plot(x='Player', y='GrossVP', kind='bar', figsize=(12, 6))
plt.title('Average Gross vs Par by Player')
plt.ylabel('Gross vs Par')
plt.show()

# Analyze specific player
from teg_analysis.analysis.aggregation import filter_data_by_player
jb_data = filter_data_by_player(df, 'JB')
jb_data.describe()
```

---

### 5. CLI Script (Automation)

**Create command-line tools:**

```python
#!/usr/bin/env python3
# scripts/get_current_teg.py
import argparse
from teg_analysis.analysis.aggregation import get_current_in_progress_teg_fast
from teg_analysis.core.metadata import get_teg_metadata

def main():
    parser = argparse.ArgumentParser(description='Get current TEG info')
    parser.add_argument('--detail', action='store_true', help='Show detailed info')
    args = parser.parse_args()

    # Get current TEG
    teg_num, rounds = get_current_in_progress_teg_fast()

    print(f"Current TEG: {teg_num}")
    print(f"Rounds played: {rounds}")

    if args.detail:
        for round_num in range(1, rounds + 1):
            metadata = get_teg_metadata(teg_num, round_num)
            print(f"\nRound {round_num}:")
            print(f"  Date: {metadata['Date']}")
            print(f"  Course: {metadata['Course']}")
            print(f"  Area: {metadata['Area']}")

if __name__ == '__main__':
    main()

# Usage:
# python scripts/get_current_teg.py
# python scripts/get_current_teg.py --detail
```

---

## Common Use Cases

### Use Case 1: Load and Filter Data

```python
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import (
    filter_data_by_teg,
    filter_data_by_player,
    filter_data_by_round
)

# Load all data
df = load_all_data()

# Filter by TEG
teg_18 = filter_data_by_teg(df, 18)

# Filter by player
jb_data = filter_data_by_player(df, 'JB')

# Filter by specific round
round_3 = filter_data_by_round(df, teg_num=18, round_num=3)

# Combine filters
jb_teg_18 = filter_data_by_teg(jb_data, 18)
```

### Use Case 2: Calculate Rankings

```python
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.rankings import add_ranks, ordinal, get_best

# Load data
df = load_all_data()

# Add rankings by TEG
df_ranked = add_ranks(df, score_col='GrossVP', group_col='TEGNum')

# Format rank as ordinal
df_ranked['Rank_text'] = df_ranked['Rank'].apply(ordinal)

# Get top 10 best rounds
best_rounds = get_best(df, metric='GrossVP', n=10)
```

### Use Case 3: Calculate Winners

```python
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import get_teg_winners
from teg_analysis.display.formatters import format_vs_par

# Load data
df = load_all_data()

# Get all winners
winners = get_teg_winners(df)

# Format scores
winners['BestGross_formatted'] = winners['BestGross'].apply(format_vs_par)
winners['BestNet_formatted'] = winners['BestNet'].apply(format_vs_par)

# Display
print(winners[['TEGNum', 'BestGrossPlayer', 'BestGross_formatted',
               'BestNetPlayer', 'BestNet_formatted']])
```

### Use Case 4: Get Metadata

```python
from teg_analysis.core.metadata import get_teg_metadata, load_course_info
from teg_analysis.core.data_loader import get_player_name

# Get TEG/round metadata
metadata = get_teg_metadata(teg_num=18, round_num=3)
print(f"TEG 18 Round 3 played at {metadata['Course']} on {metadata['Date']}")

# Get course info
course_info = load_course_info()
courses = course_info['Course'].unique()
print(f"Courses played: {', '.join(courses)}")

# Convert player code to name
name = get_player_name('JB')  # "Jon Baker"
```

### Use Case 5: Calculate Streaks

```python
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.streaks import (
    build_streaks,
    prepare_good_streaks_data,
    prepare_bad_streaks_data
)

# Load data
df = load_all_data()

# Build streaks
streaks = build_streaks(df)

# Get good streaks (birdies, eagles, etc.)
good_streaks = prepare_good_streaks_data(streaks)
print("Top 10 good streaks:")
print(good_streaks.head(10))

# Get bad streaks (bogeys, doubles, etc.)
bad_streaks = prepare_bad_streaks_data(streaks)
print("\nTop 10 bad streaks:")
print(bad_streaks.head(10))
```

### Use Case 6: Identify Records

```python
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.records import (
    identify_aggregate_records_and_pbs,
    identify_streak_records
)

# Load data
df = load_all_data()

# Identify records and personal bests
records = identify_aggregate_records_and_pbs(df)

# Filter to just records (not PBs)
all_time_records = records[records['RecordType'] == 'Record']
print("All-time records:")
print(all_time_records[['Metric', 'Player', 'Value', 'TEGNum']])

# Identify streak records
streak_records = identify_streak_records(df)
print("\nStreak records:")
print(streak_records.head(10))
```

---

## File Operations (Railway-Aware)

The package automatically handles different environments:

```python
from teg_analysis.io.file_operations import read_file, write_file

# Read file (auto: local, Railway volume cache, or GitHub)
df = read_file('data/handicaps.csv')

# Write file (auto: local + GitHub sync in production)
write_file('data/results.csv', df, 'Update results')

# The package detects Railway environment and:
# - Uses volume cache for fast reads
# - Syncs to GitHub for persistence
# - Falls back to GitHub if cache miss
```

**You don't need to worry about the environment - it just works!**

---

## Data Structures

### Main DataFrame (from load_all_data())

```python
df = load_all_data()

# Key columns:
# - TEGNum (int): Tournament number (1-18)
# - Round (int): Round number (1-4)
# - Hole (int): Hole number (1-18)
# - Player (str): Player code ('JB', 'AS', etc.)
# - Date (str): Round date
# - Course (str): Course name
# - Area (str): Geographic area
# - Par (int): Hole par
# - Gross (int): Gross score for hole
# - HCStrokes (int): Handicap strokes for hole
# - Net (int): Net score for hole
# - GrossVP (int): Gross vs par for hole
# - NetVP (int): Net vs par for hole
# - Stableford (int): Stableford points for hole
```

### TEG Metadata (from get_teg_metadata())

```python
metadata = get_teg_metadata(teg_num=18, round_num=3)

# Returns dict with:
# {
#     'TEGNum': 18,
#     'Round': 3,
#     'Date': '2024-08-15',
#     'Course': 'Alwoodley',
#     'Area': 'Yorkshire',
#     'Par': 71,
#     'SSS': 72,
#     ...
# }
```

### Winners DataFrame (from get_teg_winners())

```python
winners = get_teg_winners(df)

# Columns:
# - TEGNum: Tournament number
# - BestGrossPlayer: Winner (gross)
# - BestGross: Winning gross score vs par
# - BestNetPlayer: Winner (net)
# - BestNet: Winning net score vs par
# - WorstNetPlayer: "Winner" of worst net
# - WorstNet: Worst net score vs par
```

---

## Best Practices

### 1. Load Data Once

```python
# Good: Load once, reuse
df = load_all_data()
teg_18 = filter_data_by_teg(df, 18)
teg_17 = filter_data_by_teg(df, 17)

# Bad: Load multiple times
teg_18 = filter_data_by_teg(load_all_data(), 18)  # Don't do this
teg_17 = filter_data_by_teg(load_all_data(), 17)  # Loads data twice!
```

### 2. Use Specific Imports

```python
# Good: Import specific functions
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import filter_data_by_teg

# Avoid: Import entire modules (slower, more memory)
import teg_analysis.analysis.aggregation as agg  # OK but verbose
```

### 3. Handle Missing Data

```python
from teg_analysis.core.metadata import get_teg_metadata

metadata = get_teg_metadata(teg_num=999)  # Doesn't exist
if metadata is None:
    print("TEG not found")
else:
    print(f"Course: {metadata['Course']}")
```

### 4. Use Display Functions

```python
from teg_analysis.display.formatters import format_vs_par
from teg_analysis.analysis.rankings import ordinal

# Format scores
score_text = format_vs_par(2)  # "+2" not "2"

# Format ranks
rank_text = ordinal(1)  # "1st" not "1"
```

---

## Error Handling

### Common Errors

**1. Module not found**
```python
# Error: ModuleNotFoundError: No module named 'teg_analysis'

# Solution: Add project root to path
import sys
sys.path.append('/path/to/teg_v2')
import teg_analysis
```

**2. Empty DataFrame**
```python
from teg_analysis.analysis.aggregation import filter_data_by_teg

df = load_all_data()
teg_999 = filter_data_by_teg(df, 999)  # Doesn't exist

if teg_999.empty:
    print("No data for this TEG")
```

**3. Missing Environment Variables (Railway)**
```python
# If running locally and need GitHub access:
import os
os.environ['GITHUB_TOKEN'] = 'your_token_here'

# Or use a .env file
from dotenv import load_dotenv
load_dotenv()
```

---

## Performance Tips

### 1. Filter Early

```python
# Good: Filter then aggregate
teg_18 = filter_data_by_teg(df, 18)
summary = aggregate_data(teg_18, level='player')

# Less efficient: Aggregate all then filter
summary = aggregate_data(df, level='player')
teg_18_summary = summary[summary['TEGNum'] == 18]
```

### 2. Use Appropriate Aggregation Level

```python
# If you need player totals, aggregate to player level
player_summary = aggregate_data(df, level='player')

# If you need round details, aggregate to round level
round_summary = aggregate_data(df, level='round')

# Don't aggregate to hole level if you don't need it
```

### 3. Cache Expensive Operations

```python
# For Streamlit apps
import streamlit as st

@st.cache_data
def load_and_process_data():
    df = load_all_data()
    # Do expensive processing
    return df

df = load_and_process_data()
```

---

## Troubleshooting

### Issue: "No such file or directory: data/all-data.parquet"

**Cause:** Running from wrong directory or data files not present

**Solution:**
```python
# Check current directory
import os
print(os.getcwd())

# Change to project root
os.chdir('/path/to/teg_v2')

# Or use absolute paths in read_file()
```

### Issue: "KeyError: 'TEGNum'"

**Cause:** DataFrame doesn't have expected columns

**Solution:**
```python
# Check what columns exist
print(df.columns.tolist())

# Ensure you loaded data correctly
df = load_all_data()  # Not a filtered subset
```

### Issue: "Streamlit not found" when using package

**Cause:** You're using teg_analysis outside Streamlit, which is fine!

**Solution:** This is expected. The package gracefully handles missing Streamlit. Functions that need Streamlit will log warnings instead.

---

## Migration from Old Code

### If you have code using old helpers:

**Before (old structure):**
```python
from streamlit.helpers.display_helpers import format_vs_par
```

**After (new structure):**
```python
from teg_analysis.display.formatters import format_vs_par
```

### If you're using streamlit/utils.py:

**Current (works perfectly):**
```python
from utils import load_all_data  # Via wrapper
```

**Optional direct import:**
```python
from teg_analysis.core.data_loader import load_all_data
```

**Both work!** Wrappers maintain backward compatibility.

---

## Examples

See complete working examples in:
- **examples/example_fastapi.py** - Full REST API (248 lines)
- **tests/test_core_functions.py** - Usage examples for core functions
- **tests/test_independence.py** - Package independence examples

---

## Next Steps

1. **Explore the package:** Start with FUNCTION_REFERENCE.md to find functions you need
2. **Try examples:** Run example_fastapi.py to see API in action
3. **Build something:** Use the package in your preferred framework
4. **Refer to docs:** See ARCHITECTURE.md for design details

---

## Getting Help

**Documentation:**
- **[FUNCTION_REFERENCE.md](FUNCTION_REFERENCE.md)** - Complete function catalog
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Package architecture
- **[REFACTOR_HISTORY.md](REFACTOR_HISTORY.md)** - Refactoring history

**Code:**
- Check `teg_analysis/` source code (well-commented)
- See `examples/` for working examples
- Review `tests/` for usage patterns

---

**Last Updated:** 2025-01-27
**Package Version:** 1.0.0
