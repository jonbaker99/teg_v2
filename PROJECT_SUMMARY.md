# Project Summary: TEG Golf Data Application

This document provides an overview of the TEG Golf Data application, its objectives, key considerations, the work completed so far, potential watch-outs, and the planned next steps.

## 1. Project Overview and Objectives

The project is a Streamlit application designed for analyzing golf data, specifically for "TEG" (Tournament Event Golf) rounds. Its primary objectives are:

*   **Data Ingestion:** Allow users to add new golf round data via a Streamlit interface, reading from Google Sheets.
*   **Data Processing:** Process raw round data, add metadata (e.g., handicaps, cumulative scores), and transform it into a structured format suitable for analysis.
*   **Data Storage:** Maintain a master data file that is accessible both locally and when the application is deployed (e.g., on Railway). This data needs to be synchronized via GitHub.
*   **Data Analysis & Visualization:** Provide various analytical views and visualizations within the Streamlit app (e.g., TEG History, Results, Handicaps, Leaderboards).
*   **Data Management:** Offer functionality to delete existing data and perform data integrity checks.
*   **Flexibility:** Support both local development/analysis and cloud deployment (Railway).

## 2. Considerations and Required Functionality

During our discussions, several key considerations and functional requirements were highlighted:

*   **Multi-Environment Deployment:** The application must function seamlessly both locally (for ad-hoc analysis and development) and when deployed on Railway.
*   **GitHub as Source of Truth:** GitHub serves as the central synchronization point for the core data files, ensuring consistency across environments.
*   **Data File Formats:** While Parquet is preferred for in-app performance due to its efficiency, a human-readable CSV mirror of the main data file is required for easy ad-hoc local analysis.
*   **Streamlit Caching:** Effective use of Streamlit's `@st.cache_data` is crucial for application responsiveness, with caches needing to be cleared upon data updates.
*   **Data Integrity:** The system needs checks to ensure data completeness and identify duplicates.
*   **User Experience:** The application should be stable and predictable, especially during multi-step processes and page navigation.
*   **Code Maintainability:** Code should be clear, simple, and well-commented, especially for a beginner-level coder.

## 3. What We've Done So Far

We've made significant progress in improving the application's stability, data handling, and initial performance:

*   **Dependency Review:** Confirmed core dependencies from `requirements.txt` (pandas, numpy, streamlit, gspread, PyGithub, etc.).
*   **Data I/O Refactoring:**
    *   **Parquet Adoption:** Transitioned the primary `all-scores` data file from `.csv` to the more performant `.parquet` format.
    *   **Centralized Constants:** Consolidated all file path constants (e.g., `ALL_SCORES_PARQUET`, `HANDICAPS_CSV`) into `streamlit/utils.py` for easier management.
    *   **Smart `read_file`/`write_file`:** Enhanced `read_file` and `write_file` functions in `utils.py` to automatically determine file type (CSV/Parquet) from the file extension, simplifying their usage.
    *   **One-Time Conversion Script:** Created and executed `one_time_convert_to_parquet.py` to convert your existing `all-scores.csv` to `all-scores.parquet` as a one-off migration step.
*   **Application Stability & Error Handling:**
    *   **`read_file` Argument Fix:** Corrected all instances where `read_file` was incorrectly called with two arguments (e.g., `read_file(path, 'csv')`) to the new single-argument format (`read_file(path)`). This was a widespread fix across `500Handicaps.py`, `data_diagnostic_newteg.py`, `utils.py`, and `debug_github.py`.
    *   **Data Type Consistency:** Ensured `TEGNum` and `Round` columns are consistently treated as numeric types (`pd.to_numeric`) before concatenation in `1000Data update.py` to prevent `Expected bytes, got 'int'` errors during Parquet writes.
    *   **Robust Session State Management:**
        *   Implemented a robust "state machine" logic in `streamlit/1000Data update.py` to manage the multi-step data update process. This prevents `NoneType` errors and rogue UI elements when navigating between pages.
        *   Applied the same state machine pattern to `streamlit/delete_data.py` to proactively enhance its stability and predictability.
    *   **GitHub Branch Handling:** Updated `get_current_branch` in `utils.py` to reliably determine the current Git branch, prioritizing Railway's `RAILWAY_GIT_BRANCH` environment variable for deployed environments.
    *   **Backup Path Fix:** Corrected `create_backup` in `delete_data.py` to use relative paths for GitHub backups, resolving `path cannot start with a slash` errors on Railway.
*   **Initial Performance Optimization (Pandas):**
    *   **Vectorized Player Name Lookup:** Replaced the `.apply(get_player_name)` call with the more efficient `long_df['Pl'].map(PLAYER_DICT).fillna('Unknown Player')` in `process_round_for_all_scores` within `utils.py`.

## 4. Things to Watch Out For

*   **Railway Deployment:** Always ensure your Railway deployment is using the correct branch and that the `RAILWAY_GIT_BRANCH` environment variable is correctly picked up (though our latest change should handle this automatically).
*   **Google Sheet Credentials:** Ensure your `st.secrets["google"]` configuration (for local development) and Railway environment variables (for deployment) are correctly set up for Google Sheets API access.
*   **Data Consistency:** While we've added type enforcement, always be mindful of data types, especially when merging or concatenating DataFrames from different sources.
*   **New Features:** When adding new features, especially those involving multi-step user flows or data manipulation, consider applying the state machine pattern to ensure stability.

## 5. Next Steps

Our primary goal moving forward is to continue improving the application's performance.

1.  **Pandas Optimization: Efficient Data Types:**
    *   Define explicit `dtype` mappings for all relevant columns (e.g., `category` for categorical data, specific integer types for numeric data) in `utils.py`.
    *   Modify `read_file` (and potentially `load_all_data`) to apply these dtypes upon data loading. This will reduce memory footprint and speed up operations.

2.  **Further Pandas Vectorization:**
    *   Review other data processing functions in `utils.py` (e.g., `add_cumulative_scores`, `get_teg_winners`) for opportunities to replace loops or less efficient operations with vectorized Pandas methods.

3.  **Code Modularity (Optional):**
    *   Consider refactoring the large `utils.py` file into smaller, more specialized modules (e.g., `data_io.py`, `data_processing.py`, `analysis.py`) to improve code organization and maintainability. This is a lower priority but beneficial for long-term development.

This summary should provide a clear roadmap for continuing our work.
