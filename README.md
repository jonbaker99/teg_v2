# TEG Golf Analytics Dashboard

This repository contains a Streamlit application for analyzing and visualizing golf data for the TEG (The El Golfo) society. It provides a comprehensive set of tools for tracking player performance, viewing historical data, and managing tournament information.

## Features

*   **Interactive Leaderboards:** View real-time leaderboards for ongoing tournaments, with support for both net and gross scoring.
*   **Historical Data:** Explore the complete history of TEG winners, including an honours board for major achievements.
*   **Performance Analysis:** Analyze player performance by course, par, and other metrics.
*   **Scorecards:** View detailed hole-by-hole scorecards for any player, round, or tournament.
*   **Data Management:** A secure interface for updating, editing, and deleting tournament data.

## Architecture Refactoring (2025)

The TEG application is undergoing a major architectural refactoring to separate calculation logic from UI presentation, enabling the core analytics to be used with any frontend framework (Streamlit, FastAPI, Flask, etc.).

### The `teg_analysis` Package

A pure Python package containing all golf analytics calculations, completely independent of Streamlit:

*   **`teg_analysis.io`**: Data loading from files and GitHub API
*   **`teg_analysis.core`**: Core calculations (handicaps, scoring, statistics)
*   **`teg_analysis.analysis`**: Complex aggregations (records, history, tournaments)
*   **`teg_analysis.display`**: Data formatting and table preparation (no rendering)

### Refactoring Progress

*   **Phase I (Complete)**: Migrated I/O layer to `teg_analysis.io` - all data loading centralized
*   **Phase II (Complete)**: Migrated Core layer to `teg_analysis.core` - handicap and scoring calculations
*   **Phase III (Complete)**: Migrated Display layer to `teg_analysis.display` - formatters and table utilities
*   **Phase IV (Complete)**: Migrated Analysis layer to `teg_analysis.analysis` - 202 functions migrated from `streamlit/helpers/`
*   **Phase V (Documented)**: Make `teg_analysis` fully UI-agnostic by removing remaining Streamlit dependencies

For detailed Phase V execution plans, see [docs/PHASE_5_DOCUMENTATION_INDEX.md](docs/PHASE_5_DOCUMENTATION_INDEX.md)

### Future Refactoring: Separate Analysis from I/O

Some functions in `teg_analysis.analysis` currently mix data analysis with file writing operations. This violates the separation of concerns principle and makes functions harder to test and reuse. A future improvement would be to refactor these functions:

**Current Pattern (coupled):**
```python
def prepare_best_teg_table(df, teg_num):
    # Analyze data...
    result = df[df['TEGNum'] == teg_num]
    # Write to file
    result.to_csv('output.csv')
    return result
```

**Better Pattern (separated):**
```python
def calculate_best_teg_table(df, teg_num):
    """Pure analysis function - returns data only."""
    result = df[df['TEGNum'] == teg_num]
    return result

def save_best_teg_table(df, filepath):
    """I/O function - handles file operations."""
    df.to_csv(filepath)
```

**Benefits:**
- ✅ Functions become pure (deterministic, testable)
- ✅ Reusable for different output formats (CSV, JSON, API, web display)
- ✅ No side effects when used in interactive demos
- ✅ Easier to mock and unit test
- ✅ Composable (chain multiple analyses)

**Affected Functions:**
- `prepare_*()` functions in `aggregation.py` (e.g., `prepare_best_teg_table`, `prepare_worst_teg_table`, etc.)
- `create_*()` functions that write output
- Any function combining analysis with file I/O

This refactoring can be tackled incrementally as needed.

## Project Structure

The repository is organized as follows:

*   **`teg_analysis/`**: Pure Python package for all golf analytics calculations (UI-independent)
    *   `io/`: Data loading from CSV/Parquet files and GitHub API
    *   `core/`: Core calculations (handicaps, scoring, Stableford points)
    *   `analysis/`: Complex aggregations (records, history, tournaments, pipeline)
    *   `display/`: Data formatting and table preparation utilities
*   **`streamlit/`**: Streamlit web application (UI layer)
    *   `helpers/`: Streamlit-specific wrappers and remaining UI utilities (many functions migrated to `teg_analysis/`)
    *   `*.py`: Numbered page files organized by function (100s=History, 200s=Results, 300s=Records, etc.)
    *   `nav.py`: Main navigation controller and entry point
*   **`docs/`**: Project documentation including phase completion summaries and execution plans
*   **`data/`**: Tournament data files (CSV/Parquet), handicaps, and course information
*   **`dev_notebooks/`**: Jupyter notebooks for development and ad-hoc analysis
*   **`*.py`**: Root-level scripts for testing and data management

## Setup and Installation

To set up the development environment, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/jonbaker99/teg_v2.git
    cd teg_v2
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

### Streamlit Application (Main)

To run the Streamlit application, execute the following command from the root directory:

```bash
streamlit run streamlit/nav.py
```

This will start the application on your local machine, and you can access it in your web browser at `http://localhost:8501`.

### NiceGUI Demo Pages (Development/Learning)

Comprehensive function explorer demos are available using NiceGUI:

```bash
cd nicegui
python run_all_demos_comprehensive.py
# Navigate to http://localhost:8080
```

**Features:**
- Interactive demos of 80+ `teg_analysis` functions
- Shows exact function calls with parameters for every function
- Demonstrates how functions work with real data
- Educational resource showing NiceGUI multi-page routing
- 6 demo pages: Aggregation, Rankings, Records, Scoring, Metadata, Streaks

**Available Demos:**
- `run_all_demos_comprehensive.py` - Full demo of all 80+ functions (recommended)
- `demo_pages_*.py` - Individual standalone demos (can be run independently)
- `demo_hub.py` - Navigation hub with routing examples

## Data Management

The application provides a set of tools for managing the data used in the analysis. These tools are available in the "Data" section of the application and include:

*   **Data Update:** Load new round data from a Google Sheet.
*   **Data Edit:** Directly edit the CSV data files.
*   **Delete Data:** Safely delete tournament data with backups.

All data changes are automatically synced with the GitHub repository to ensure data integrity and version control.