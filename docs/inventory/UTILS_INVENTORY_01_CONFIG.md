# Utils.py Inventory - Section 1: Configuration & Setup Functions

**Section:** Configuration & Setup
**Function Count:** 8 functions + constants
**Lines in utils.py:** 1-136
**Estimated Complexity:** Simple to Medium

---

## Section Overview

This section documents the foundational configuration and setup functions that initialize the application environment. These functions handle:
- Page layout configuration
- Cache management
- Base directory detection
- Git branch determination
- Path and repository constants

All of these are critical for the application to run correctly in both local development and Railway production environments.

---

## Constants & Globals

### `GITHUB_REPO` (Line 82)
**Type:** String constant
**Value:** `"jonbaker99/teg_v2"`
**Purpose:** Identifies the GitHub repository used for data storage and retrieval
**Used By:** All GitHub I/O functions (`read_from_github`, `write_to_github`, `batch_commit_to_github`)

---

### `BASE_DIR` (Line 86)
**Type:** Path object
**Determination:**
- If current directory is "streamlit": parent directory (the project root)
- Otherwise: current working directory (assumed to be project root)
**Purpose:** Provides the root directory for local file operations
**Used By:** Local file I/O functions (`_get_local_path`, `read_file`, `write_file`)

---

### Data File Path Constants (Lines 91-106)

**Parquet Files (Primary Data Storage):**
- `ALL_DATA_PARQUET = "data/all-data.parquet"` - Main tournament data file
- `ALL_SCORES_PARQUET = "data/all-scores.parquet"` - Historical scores data
- `STREAKS_PARQUET = "data/streaks.parquet"` - Player streak calculations
- `BESTBALL_PARQUET = "data/bestball.parquet"` - Bestball/worstball data

**CSV Files (Reference Data):**
- `HANDICAPS_CSV = "data/handicaps.csv"` - Handicap reference
- `ROUND_INFO_CSV = "data/round_info.csv"` - Course and round metadata
- `ALL_DATA_CSV_MIRROR = "data/all-data.csv"` - CSV mirror of parquet for review

**Commentary Cache Files (Auto-generated on data changes):**
- `COMMENTARY_ROUND_EVENTS_PARQUET = "data/commentary_round_events.parquet"`
- `COMMENTARY_ROUND_SUMMARY_PARQUET = "data/commentary_round_summary.parquet"`
- `COMMENTARY_TOURNAMENT_SUMMARY_PARQUET = "data/commentary_tournament_summary.parquet"`
- `COMMENTARY_ROUND_STREAKS_PARQUET = "data/commentary_round_streaks.parquet"`
- `COMMENTARY_TOURNAMENT_STREAKS_PARQUET = "data/commentary_tournament_streaks.parquet"`

**Purpose:** Centralized file path management for all data operations
**Architecture:** Using relative paths allows the same code to work in local development and Railway production with different storage backends

---

### Player Dictionary (Lines 737-747)

```python
PLAYER_DICT = {
    'AB': 'Alex BAKER',
    'JB': 'Jon BAKER',
    'DM': 'David MULLIN',
    'GW': 'Gregg WILLIAMS',
    'HM': 'Henry MELLER',
    'SN': 'Stuart NEUMANN',
    'JP': 'John PATTERSON',
    'GP': 'Graham PATTERSON',
}
```

**Purpose:** Maps player initials to full names
**Type:** Dictionary mapping (str → str)
**Used By:** `get_player_name()`, `process_round_for_all_scores()`

---

### TEG Rounds Dictionary (Lines 749-759)

```python
TEG_ROUNDS = {
    'TEG 1': 1,
    'TEG 2': 3,
    # ... more TEGs
}

TEGNUM_ROUNDS = {
    int(teg.split()[1]): rounds
    for teg, rounds in TEG_ROUNDS.items()
}
```

**Purpose:** Specifies expected number of rounds for each tournament
**Type:** Two complementary dictionaries
  - `TEG_ROUNDS`: Maps "TEG X" string to round count
  - `TEGNUM_ROUNDS`: Maps integer TEG number to round count
**Used By:** `get_teg_rounds()`, `get_tegnum_rounds()`, `get_incomplete_tegs()`

---

### TEG Overrides Dictionary (Lines 761-766)

```python
TEG_OVERRIDES = {
    'TEG 5': {
        'Best Net': 'Gregg WILLIAMS',
        'Best Gross': 'Stuart NEUMANN*'
    }
}
```

**Purpose:** Manual overrides for edge cases where calculated winners differ from actual results
**Type:** Nested dictionary
**Used By:** `get_teg_winners()`

---

## Functions

### 1. `get_page_layout(page_file: str) -> str`

**Line Numbers:** 24-42 (19 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
Retrieves the page layout setting ("wide" or "centered") for a Streamlit page from the PAGE_DEFINITIONS configuration. This allows per-page customization of layout without modifying individual page code.

**Full Signature:**
```python
def get_page_layout(page_file: str) -> str:
    """Get the layout setting for a page from PAGE_DEFINITIONS.

    Args:
        page_file: The __file__ variable from the calling page

    Returns:
        str: "wide" or "centered" (defaults to "centered" if not specified)
    """
```

**Parameters:**
- `page_file` (str): The `__file__` magic variable from the calling Streamlit page. Used to identify which page is requesting its layout.

**Returns:**
- `str`: Either "wide" or "centered". Defaults to "centered" if page not found in PAGE_DEFINITIONS.

**Dependencies:**
- **External Packages:** None
- **Internal Functions:** None directly; imports `PAGE_DEFINITIONS` from `page_config.py`
- **Streamlit-Specific:** No
- **File I/O:** No

**Imports Required:**
```python
from page_config import PAGE_DEFINITIONS
```

**Used By (Usage Sites):**
- `streamlit/101TEG History.py` (line 1)
- `streamlit/101TEG Honours Board.py` (line 1)
- `streamlit/102TEG Results.py` (line 1)
- `streamlit/300TEG Records.py` (line 1)
- `streamlit/301Best_TEGs_and_Rounds.py` (line 1)
- `streamlit/302Personal Best Rounds & TEGs.py` (line 1)
- `streamlit/303Final Round Comebacks.py` (line 1)
- `streamlit/500Handicaps.py` (line 1)
- At least 20+ other page files

**Function Type Analysis:**
- **Classification:** PURE - No side effects, deterministic output
- **Streamlit UI Dependencies:** No (just returns a string)
- **File I/O:** No
- **Data Processing:** Minimal - just dictionary lookup
- **External API Calls:** No

**Migration Recommendation:**
- **Target Module:** Keep in utils.py OR move to `streamlit/page_config.py`
- **Rationale:** Very simple helper function; low-cost to migrate but also low-cost to keep. Could be consolidated with PAGE_DEFINITIONS in page_config.py
- **Priority:** LOW - Not blocking other refactoring
- **Breaking Changes:** No - just needs import update in 20+ pages

**Technical Notes:**
- Uses `os.path.basename()` to extract just the filename (handles both relative and absolute paths)
- Defaults gracefully to "centered" if page not configured
- Assumes PAGE_DEFINITIONS is always defined in page_config.py

---

### 2. `clear_all_caches() -> None`

**Line Numbers:** 45-51 (7 lines)
**Function Type:** UI
**Complexity:** Simple

**Purpose:**
Wrapper function that clears all Streamlit data caches. Used after data updates or deletions to ensure fresh data loads on next page refresh. This is critical for maintaining data consistency in the cached environment.

**Full Signature:**
```python
def clear_all_caches():
    """Clears all Streamlit data caches.

    This function is a simple wrapper around `st.cache_data.clear()` to provide a
    centralized way to manage cache clearing.
    """
```

**Parameters:**
- None

**Returns:**
- None (has side effect of clearing Streamlit's cache)

**Dependencies:**
- **External Packages:** streamlit
- **Internal Functions:** None
- **Streamlit-Specific:** Yes - calls `st.cache_data.clear()`
- **File I/O:** No

**Calls:**
```python
st.cache_data.clear()
```

**Used By (Usage Sites):**
- `streamlit/1000Data update.py` - Called after updating data
- `streamlit/500Handicaps.py` - Called after handicap calculations
- `streamlit/9999_generate_caches.py` - Called when regenerating caches
- `streamlit/delete_data.py` - Called after data deletion
- Inside utils.py: `write_to_github()`, `batch_commit_to_github()`, `write_file()`, `write_text_file()`, `update_all_data()`, `update_streaks_cache()`, `update_commentary_caches()`, `update_teg_status_files()`

**Function Type Analysis:**
- **Classification:** UI - Directly calls Streamlit function
- **Streamlit-Specific:** Yes - `st.cache_data.clear()`
- **File I/O:** No
- **Data Processing:** No
- **Side Effects:** Clears all cached data in Streamlit

**Migration Recommendation:**
- **Target Module:** Keep in utils.py OR move to dedicated cache management module
- **Rationale:** UI/Streamlit-specific function; must remain in streamlit/ directory. Could be consolidated with other cache management functions.
- **Priority:** LOW - Simple wrapper, not critical path
- **Breaking Changes:** No - already centralized entry point

**Technical Notes:**
- Simple wrapper around `st.cache_data.clear()` provides single point of control for cache clearing
- Recommended to call whenever source data changes (updates, deletions, calculations)
- Alternative: Could be renamed to `refresh_cache()` or `invalidate_cache()` for clarity

---

### 3. `get_base_directory() -> Path`

**Line Numbers:** 54-75 (22 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
Determines the base (root) directory of the project dynamically. Handles both scenarios:
1. Running locally from within the `streamlit/` subfolder
2. Running from the project root directory

Returns the Path object pointing to the project root, which is then used by `_get_local_path()` for all local file operations.

**Full Signature:**
```python
def get_base_directory() -> Path:
    """Determines the base directory of the project.

    This function checks if the current working directory is the `streamlit`
    subfolder. If it is, it returns the parent directory. Otherwise, it assumes
    the current directory is the project root.

    Returns:
        pathlib.Path: The absolute path to the base directory of the project.
    """
```

**Parameters:**
- None

**Returns:**
- `Path`: Pathlib Path object pointing to the project root directory

**Dependencies:**
- **External Packages:** pathlib (built-in)
- **Internal Functions:** None
- **Streamlit-Specific:** No
- **File I/O:** No (just filesystem introspection)

**Used By (Usage Sites):**
- Called at module level to initialize `BASE_DIR` constant (line 86)
- Used by `_get_local_path()` to build absolute paths
- Indirectly used by all local file operations: `read_file()`, `write_file()`, `read_text_file()`, `write_text_file()`, `backup_file()`

**Function Type Analysis:**
- **Classification:** PURE - Deterministic, no side effects
- **Streamlit-Specific:** No
- **File I/O:** No (filesystem introspection only via Path.cwd())
- **Data Processing:** No
- **External API Calls:** No

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** Foundational function for path management; critical to keep in current location
- **Priority:** N/A - Should not be migrated
- **Breaking Changes:** Would break all local file operations if removed

**Technical Notes:**
- Uses `Path.cwd()` to get current working directory (not `os.getcwd()` which returns string)
- Checks `Path.cwd().name == "streamlit"` to detect if running from within streamlit folder
- Assumes if not in streamlit folder, then already in project root
- Robust to both development and production directory structures

---

### 4. `get_current_branch() -> str`

**Line Numbers:** 108-133 (26 lines)
**Function Type:** IO
**Complexity:** Medium

**Purpose:**
Determines the current Git branch, with support for both Railway (CI/CD environment) and local development:
1. **Railway:** Reads from `RAILWAY_GIT_BRANCH` environment variable (automatically set by Railway)
2. **Local Development:** Executes `git rev-parse --abbrev-ref HEAD` to get current branch
3. **Fallback:** Returns 'main' if unable to determine branch

This is used to ensure GitHub operations read/write from the correct branch.

**Full Signature:**
```python
def get_current_branch() -> str:
    """Gets the current git branch.

    This function determines the current git branch by checking for the
    `RAILWAY_GIT_BRANCH` environment variable (on Railway deployments) or by
    executing a git command locally. It defaults to 'main' if the branch
    cannot be determined.

    Returns:
        str: The name of the current git branch.
    """
```

**Parameters:**
- None

**Returns:**
- `str`: Git branch name (e.g., "main", "develop", "feature/new-feature")

**Dependencies:**
- **External Packages:** os (built-in), subprocess (built-in), logging (built-in)
- **Internal Functions:** None
- **Streamlit-Specific:** No
- **File I/O:** No (but executes subprocess command)

**Environment Variables:**
- `RAILWAY_GIT_BRANCH` - Set automatically by Railway platform
- Used as first choice for Railway deployments

**Subprocess Calls:**
```python
git rev-parse --abbrev-ref HEAD
```

**Used By (Usage Sites):**
- Called at module level to initialize `GITHUB_BRANCH` constant (line 135)
- Used by all GitHub I/O functions: `read_from_github()`, `write_to_github()`, `batch_commit_to_github()`, `write_text_to_github()`, etc.

**Function Type Analysis:**
- **Classification:** IO - Executes subprocess command and reads environment
- **Streamlit-Specific:** No
- **File I/O:** No (but subprocess/git operation)
- **External API Calls:** Yes - calls git subprocess
- **Side Effects:** None (read-only)

**Error Handling:**
- Catches all exceptions from git command and falls back to 'main'
- Logs warnings when unable to determine branch locally
- Gracefully handles missing git installation

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** Critical for GitHub integration; depends on environment setup
- **Priority:** N/A - Should not be migrated
- **Breaking Changes:** Would break all GitHub operations if removed

**Technical Notes:**
- Railway environment provides `RAILWAY_GIT_BRANCH` automatically
- Local git command needs git installed and repository initialized
- Default 'main' is safe for most scenarios
- Text output stripped to remove newline character
- Subprocess called with `text=True` for string output instead of bytes

---

## Section Summary

**Section Statistics:**
- Total Functions: 4 main functions
- Total Constants/Globals: 6 (repo, directories, data paths, dicts, overrides)
- Lines of Code: ~80 lines (functions only)
- Complexity: Mostly Simple, one Medium

**Key Points:**
1. All functions in this section are **foundational** - they initialize critical paths and settings
2. **PURE functions** (`get_page_layout`, `get_base_directory`) have no side effects and are safe to migrate
3. **UI/IO functions** (`clear_all_caches`, `get_current_branch`) must stay in utils.py for now
4. **Constants** should be considered as module-level configuration that everything else depends on

**Dependencies on This Section:**
- ALL other functions in utils.py depend on `BASE_DIR` for local operations
- ALL GitHub operations depend on `GITHUB_BRANCH`
- ALL page rendering depends on `get_page_layout()`
- Almost all data operations trigger `clear_all_caches()` after changes

**Potential Improvements:**
1. Could extract path constants to a dedicated `paths.py` configuration file
2. Could enhance `get_base_directory()` to validate the directory structure
3. Could add logging to track cache clearing patterns
4. Could document PLAYER_DICT, TEG_ROUNDS, and TEG_OVERRIDES more explicitly

---

