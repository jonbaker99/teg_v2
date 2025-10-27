# Utils.py Inventory - Section 3: Railway Volume Management Functions

**Section:** Railway Volume Management & Caching Layer
**Function Count:** 10 functions
**Lines in utils.py:** 361-709
**Estimated Complexity:** Medium to Complex

---

## Section Overview

This section documents the **critical abstraction layer** that enables the application to work seamlessly in both:
1. **Local Development** - Files stored on local filesystem
2. **Railway Production** - Files persisted in mounted volume (sync'd to GitHub)

These functions implement intelligent caching that:
- Reads from volume when available (fast, no API calls)
- Falls back to GitHub on cache miss (automatic download + caching)
- Handles both Railway and local environments transparently
- Manages volume directory structure and cleanup

**Architecture Pattern:** Environment-aware abstraction using dependency injection principles.

---

## Helper Functions (Internal)

### `_is_railway() -> bool`

**Line Numbers:** 369-375 (7 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
Simple boolean check that determines if code is running in Railway environment. Uses `RAILWAY_ENVIRONMENT` environment variable which is automatically set by Railway platform.

**Full Signature:**
```python
def _is_railway() -> bool:
    """Check if running on Railway environment.

    Returns:
        bool: True if running on Railway, False for local development
    """
```

**Returns:**
- `bool`: True if `RAILWAY_ENVIRONMENT` env var is set, False otherwise

**Dependencies:**
- `os` (built-in) - to check environment variable

**Used By (Throughout):**
- `_get_volume_path()` - Routing to volume vs local
- `_get_local_path()` - Routing to volume vs local
- `read_file()` - Determine read strategy
- `write_file()` - Determine write strategy
- `read_text_file()` - Determine read strategy
- `write_text_file()` - Determine write strategy
- `clear_volume_cache()` - Check if volume exists
- `get_app_base_url()` - Determine app URL

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** Foundational environment detection
- **Priority:** CRITICAL
- **Breaking Changes:** Would break all file I/O if removed

---

### `_get_volume_path(file_path: str) -> str`

**Line Numbers:** 378-387 (10 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
Converts a relative file path into an absolute Railway volume path. Railway mounts persistent storage at `/mnt/data_repo`.

**Full Signature:**
```python
def _get_volume_path(file_path: str) -> str:
    """Get Railway volume path for file.

    Args:
        file_path (str): Relative file path (e.g., 'data/file.csv')

    Returns:
        str: Absolute volume path (e.g., '/mnt/data_repo/data/file.csv')
    """
```

**Parameters:**
- `file_path` (str): Relative path from project root

**Returns:**
- `str`: Absolute path on Railway volume

**Examples:**
```python
_get_volume_path("data/all-scores.parquet")
# Returns: "/mnt/data_repo/data/all-scores.parquet"

_get_volume_path("data/handicaps.csv")
# Returns: "/mnt/data_repo/data/handicaps.csv"
```

**Used By:**
- `read_file()` - Get volume path to check/read cache
- `write_file()` - Get volume path to write cache
- `read_text_file()` - Get volume path for text files
- `write_text_file()` - Get volume path for text files
- `clear_volume_cache()` - Get path to delete cache files

**Migration Recommendation:**
- **Target Module:** Keep in utils.py or move to `config.py`
- **Rationale:** Simple path construction; could be config
- **Priority:** CRITICAL - Cannot remove
- **Breaking Changes:** Would break all volume operations

---

### `_get_local_path(file_path: str) -> Path`

**Line Numbers:** 390-399 (10 lines)
**Function Type:** PURE
**Complexity:** Simple

**Purpose:**
Converts a relative file path into an absolute local filesystem path using `BASE_DIR`. Used for local development where files are on the filesystem instead of mounted volume.

**Full Signature:**
```python
def _get_local_path(file_path: str) -> Path:
    """Get local filesystem path for file.

    Args:
        file_path (str): Relative file path (e.g., 'data/file.csv')

    Returns:
        Path: Absolute local path based on BASE_DIR
    """
```

**Parameters:**
- `file_path` (str): Relative path from project root

**Returns:**
- `Path`: Pathlib Path object with absolute path

**Examples:**
```python
_get_local_path("data/all-scores.parquet")
# Returns: Path("/home/user/projects/teg_v2/data/all-scores.parquet")
```

**Dependencies:**
- Uses `BASE_DIR` constant (from `get_base_directory()`)

**Used By:**
- `read_file()` - Get local path for local development
- `write_file()` - Get local path for local writes
- `read_text_file()` - Get local path for text reads
- `write_text_file()` - Get local path for text writes
- `backup_file()` - Get local path for backups

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** Depends on BASE_DIR constant
- **Priority:** CRITICAL
- **Breaking Changes:** Would break local development file I/O

---

### `_ensure_volume_dir(volume_path: str) -> None`

**Line Numbers:** 402-408 (7 lines)
**Function Type:** IO
**Complexity:** Simple

**Purpose:**
Ensures parent directory exists on Railway volume before writing files. Uses `os.makedirs(..., exist_ok=True)` to create directory structure if needed.

**Full Signature:**
```python
def _ensure_volume_dir(volume_path: str) -> None:
    """Ensure parent directory exists for volume path.

    Args:
        volume_path (str): Full path to file in volume
    """
```

**Parameters:**
- `volume_path` (str): Absolute volume path from `_get_volume_path()`

**Used By:**
- `read_file()` - Before caching file to volume
- `write_file()` - Before writing file to volume
- `read_text_file()` - Before caching text to volume
- `write_text_file()` - Before writing text to volume
- `backup_file()` - Before backing up to volume

**Technical Notes:**
- `exist_ok=True` makes this idempotent (safe to call multiple times)
- Uses `os.path.dirname()` to get parent directory only
- Creates full path hierarchy if needed (e.g., `data/nested/path/`)

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** Only used for volume operations
- **Priority:** MEDIUM - Could be inlined
- **Breaking Changes:** No - internal helper only

---

## Public Interface Functions

### `read_file(file_path: str) -> pd.DataFrame`

**Line Numbers:** 411-471 (61 lines)
**Function Type:** MIXED
**Complexity:** Complex

**Purpose:**
**PRIMARY PUBLIC API for reading files.** Intelligently routes between volume cache (Railway) and GitHub (with automatic caching). Implements smart caching strategy:

**Flow:**
1. **On Railway:**
   - Check if file exists in volume → read from volume (FAST, no API calls)
   - If not in volume → download from GitHub → cache to volume → return
2. **Local Development:**
   - Read directly from local filesystem

This is the **recommended way to read data files** throughout the application.

**Full Signature:**
```python
def read_file(file_path: str) -> pd.DataFrame:
    """Reads a file from the local filesystem or a mounted volume.

    This function reads a file from a mounted volume if running on Railway,
    or from the local filesystem if running locally. If the file is not
    found in the volume on Railway, it caches it from GitHub.

    Args:
        file_path (str): The path to the file.

    Returns:
        pd.DataFrame: The content of the file as a pandas DataFrame.

    Raises:
        ValueError: If the file type is not supported.
    """
```

**Parameters:**
- `file_path` (str): Path relative to project root (e.g., "data/all-scores.parquet")

**Returns:**
- `pd.DataFrame`: Loaded data

**Supported File Types:**
- `.csv` - Parsed with `pd.read_csv()`
- `.parquet` - Parsed with `pd.read_parquet()`

**Dependencies:**
- `pandas` (read_csv, read_parquet)
- `os` (path operations, environ check)
- Internal functions: `_is_railway()`, `_get_volume_path()`, `_get_local_path()`, `_ensure_volume_dir()`, `read_from_github()`

**Used By (Extensive usage - Core data loading):**
- `load_all_data()` - Loads ALL_DATA_PARQUET
- `load_and_prepare_handicap_data()` - Loads HANDICAPS_CSV
- `add_round_info()` - Loads ROUND_INFO_CSV
- `update_all_data()` - Loads source CSV
- Cache update functions - Loading source data
- 20+ page files - Loading tournament data
- Commentary functions - Loading summary/events data

**Function Type Analysis:**
- **Classification:** MIXED - File I/O + data processing
- **Streamlit-Specific:** No
- **Network Operations:** Conditional (GitHub fallback)
- **File I/O:** Yes (volume and GitHub)
- **Data Transformation:** DataFrames

**Caching Behavior:**

| Scenario | Location | Speed | API Calls |
|----------|----------|-------|-----------|
| Railway + volume cache hit | Volume | ~50ms | 0 |
| Railway + cache miss | GitHub → Volume | ~2-5s | 1-2 |
| Local development | Filesystem | ~100ms | 0 |

**Error Handling:**
- `FileNotFoundError` - If file doesn't exist locally
- `ValueError` - If unsupported file extension
- GitHub errors bubble up from `read_from_github()`

**Technical Notes:**
- Volume path check uses `os.path.exists()` for fast filesystem check
- Falls back to GitHub if volume read fails
- Logs all operations with logger
- DataFrame reading errors from pandas propagate up

**Improvement Opportunities:**
- Could add retry logic for GitHub failures
- Could add timeout protection
- Could validate file integrity (checksums)
- Could implement LRU cache eviction on volume

**Migration Recommendation:**
- **Target Module:** Keep in utils.py - CRITICAL
- **Rationale:** Core data loading abstraction; must stay
- **Priority:** CRITICAL - Cannot remove
- **Breaking Changes:** Would break entire application

---

### `write_file(file_path: str, data: pd.DataFrame, commit_message: str = "Update data", defer_github: bool = False) -> Optional[dict]`

**Line Numbers:** 474-540 (67 lines)
**Function Type:** MIXED
**Complexity:** Complex

**Purpose:**
**PRIMARY PUBLIC API for writing DataFrames.** Writes to both volume (if Railway) and GitHub. Supports deferred commits for batch operations.

**Flow:**
1. **On Railway:**
   - Write to volume (fast local write)
   - Write to GitHub (sync) OR defer for batch (if defer_github=True)
   - Clear Streamlit cache
2. **Local Development:**
   - Write to local filesystem only

**Full Signature:**
```python
def write_file(
    file_path: str,
    data: pd.DataFrame,
    commit_message: str = "Update data",
    defer_github: bool = False
) -> Optional[dict]:
    """Writes a file to the local filesystem or a mounted volume.

    This function writes a file to a mounted volume and optionally to GitHub
    if running on Railway, or to the local filesystem if running locally.

    Args:
        file_path (str): The path to the file.
        data (pd.DataFrame): The data to write.
        commit_message (str, optional): The commit message for the GitHub
            commit. Defaults to "Update data".
        defer_github (bool, optional): If True, the GitHub push is deferred
            for a batch commit. Defaults to False.

    Returns:
        dict or None: A dictionary with file information for batch commits
        if `defer_github` is True, otherwise None.
    """
```

**Parameters:**
- `file_path` (str): Path to write to (e.g., "data/all-scores.parquet")
- `data` (pd.DataFrame): Data to write
- `commit_message` (str, optional): Git commit message. Default: "Update data"
- `defer_github` (bool, optional): If True, returns dict for batch commit instead of writing immediately. Default: False

**Returns:**
- `dict` (if defer_github=True): `{'file_path': str, 'data': DataFrame}` for batch commit
- `None` (if defer_github=False): Normal return

**Supported File Types:**
- `.csv` - Written with `data.to_csv(index=False)`
- `.parquet` - Written with `data.to_parquet(index=False)`

**Dependencies:**
- `pandas` (to_csv, to_parquet)
- `streamlit` (cache clear)
- Internal: `_is_railway()`, `_get_volume_path()`, `_get_local_path()`, `_ensure_volume_dir()`, `write_to_github()`

**Used By (Extensive - Core data writing):**
- `update_all_data()` - Writes parquet and CSV
- `save_to_parquet()` - Saves data transforms
- Cache update functions - All defer GitHub for batch
- `500Handicaps.py` - Updates handicap data
- `update_teg_status_files()` - Writes status CSVs
- Data update/deletion helpers - Batch updates

**Function Type Analysis:**
- **Classification:** MIXED - File I/O + cache management
- **Streamlit-Specific:** Yes - calls `st.cache_data.clear()`
- **Network Operations:** Optional (GitHub if not deferred)
- **File I/O:** Yes (volume + GitHub)
- **Data Transformation:** DataFrame serialization

**Defer Strategy (for Batch Commits):**
```python
# Individual writes (immediate GitHub push for each)
write_file("data/file1.parquet", df1)  # Commits immediately
write_file("data/file2.parquet", df2)  # Commits immediately
# Result: 2 GitHub commits

# Batch writes (deferred)
file_infos = []
file_infos.append(write_file("data/file1.parquet", df1, defer_github=True))
file_infos.append(write_file("data/file2.parquet", df2, defer_github=True))
batch_commit_to_github(file_infos, "Batch update")  # Single commit
# Result: 1 GitHub commit
```

**Error Handling:**
- `ValueError` - If unsupported file extension
- Volume write errors logged but continue to GitHub
- GitHub errors bubble up (re-raised)
- Cache clear failure logged but continues

**Performance:**
- Volume write: ~100ms
- GitHub write (immediate): ~1-2 seconds
- Deferred return: ~1ms (just dict creation)

**Technical Notes:**
- Volume write happens BEFORE GitHub to ensure data safety
- If GitHub fails, volume still has data (partial consistency)
- Cache only cleared after successful write (if not deferred)
- Deferred mode returns dict with 'file_path' and 'data' keys

**Migration Recommendation:**
- **Target Module:** Keep in utils.py - CRITICAL
- **Rationale:** Core data persistence abstraction
- **Priority:** CRITICAL - Cannot remove
- **Breaking Changes:** Would break all data persistence

---

### `read_text_file(file_path: str) -> str`

**Line Numbers:** 543-589 (47 lines)
**Function Type:** MIXED
**Complexity:** Medium

**Purpose:**
**Like read_file() but for text files.** Reads markdown, JSON, text, etc. with same intelligent caching strategy (volume on Railway, local on development).

**Full Signature:**
```python
def read_text_file(file_path: str) -> str:
    """Reads a text file from the local filesystem or a mounted volume.

    This function reads text files (e.g., .md, .txt, .json) from a mounted volume
    if running on Railway, or from the local filesystem if running locally.
    If the file is not found in the volume on Railway, it fetches from GitHub
    and caches it to the volume.

    Args:
        file_path (str): The path to the text file.

    Returns:
        str: The content of the file as a string.
    """
```

**Parameters:**
- `file_path` (str): Path to text file (e.g., "reports/teg_17_summary.md")

**Returns:**
- `str`: Full file content as string

**Dependencies:**
- `os` (file operations, environ)
- Internal: `_is_railway()`, `_get_volume_path()`, `_get_local_path()`, `_ensure_volume_dir()`, `read_text_from_github()`

**Used By (Commentary & reports):**
- `1001Report Generation.py` - Reads/writes report content
- `102TEG Results.py` - Loads markdown content
- Commentary functions - Reading/writing analysis
- Story notes - Reading existing content

**Function Type Analysis:**
- **Classification:** MIXED - File I/O + text handling
- **Streamlit-Specific:** No
- **Network Operations:** Conditional (GitHub fallback)
- **File I/O:** Yes (volume and GitHub)
- **Data Transformation:** Text string only

**Technical Notes:**
- Uses `open(..., 'r', encoding='utf-8')` for local reads
- Path.read_text(encoding='utf-8') for local
- Falls back to GitHub with `read_text_from_github()`
- Caches to volume after GitHub fetch

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** Parallel to read_file() for text operations
- **Priority:** MEDIUM - Could consolidate with read_file()
- **Breaking Changes:** Minor - just check file extension

---

### `write_text_file(file_path: str, content: str, commit_message: str = "Update text file", defer_github: bool = False) -> Optional[dict]`

**Line Numbers:** 592-647 (56 lines)
**Function Type:** MIXED
**Complexity:** Medium

**Purpose:**
**Like write_file() but for text content.** Writes text files with same dual-storage strategy (volume + GitHub on Railway).

**Full Signature:**
```python
def write_text_file(
    file_path: str,
    content: str,
    commit_message: str = "Update text file",
    defer_github: bool = False
) -> Optional[dict]:
    """Writes a text file to the local filesystem or a mounted volume.

    This function writes text files to a mounted volume and optionally to GitHub
    if running on Railway, or to the local filesystem if running locally.

    Args:
        file_path (str): The path to the text file.
        content (str): The text content to write.
        commit_message (str, optional): The commit message for the GitHub
            commit. Defaults to "Update text file".
        defer_github (bool, optional): If True, the GitHub push is deferred
            for a batch commit. Defaults to False.

    Returns:
        dict or None: A dictionary with file information for batch commits
        if `defer_github` is True, otherwise None.
    """
```

**Parameters:**
- `file_path` (str): Path where text will be written
- `content` (str): Text content to write
- `commit_message` (str, optional): Git message
- `defer_github` (bool, optional): If True, defer GitHub write for batch

**Returns:**
- `dict` (if deferred): For batch commit
- `None` (if immediate)

**Dependencies:**
- `os` (file operations)
- `pathlib.Path` (local writes)
- Internal: `_is_railway()`, `_get_volume_path()`, `_get_local_path()`, `_ensure_volume_dir()`, `write_text_to_github()`

**Used By:**
- `1001Report Generation.py` - Writing report content
- Story notes generation - Writing analysis
- Configuration export - Writing text configs

**Function Type Analysis:**
- **Classification:** MIXED - File I/O + text handling
- **Streamlit-Specific:** Yes - calls `st.cache_data.clear()`
- **Network Operations:** Optional
- **File I/O:** Yes

**Technical Notes:**
- Uses `open(..., 'w', encoding='utf-8')` for writes
- Creates parent directories automatically
- Falls back to GitHub write if volume fails
- Cache clear only if not deferred

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** Parallel to write_file() for text
- **Priority:** MEDIUM
- **Breaking Changes:** Minor

---

### `clear_volume_cache(file_path: str = None) -> str`

**Line Numbers:** 650-687 (38 lines)
**Function Type:** IO
**Complexity:** Medium

**Purpose:**
Manually clears volume cache, either for specific file or entire volume. Useful for forcing refresh from GitHub or cleanup after deletions.

**Full Signature:**
```python
def clear_volume_cache(file_path: str = None) -> str:
    """Clears the volume cache for a specific file or all files.

    This function is useful for forcing a refresh from GitHub. It clears the
    cache on the mounted volume in a Railway environment.

    Args:
        file_path (str, optional): The path to the file to clear from the
            cache. If None, the entire volume cache is cleared. Defaults to
            None.

    Returns:
        str: A message indicating the result of the operation.
    """
```

**Parameters:**
- `file_path` (str, optional): Specific file to clear OR None to clear all

**Returns:**
- `str`: Status message

**Behavior:**
- `file_path=None` → Clears entire `/mnt/data_repo` directory
- `file_path="data/file.parquet"` → Deletes specific file from cache
- On local development → Returns "Not running on Railway" message

**Used By:**
- `admin_volume_management.py` - Manual cache management
- Could be called after bulk deletions
- Manual data integrity operations

**Technical Notes:**
- Returns early if not on Railway
- Uses `shutil.rmtree()` for directory deletion
- Catches exceptions and returns error message
- Doesn't clear Streamlit cache (separate operation)

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** Maintenance operation
- **Priority:** LOW - Not critical path
- **Breaking Changes:** No

---

### `backup_file(source_path: str, backup_path: str) -> None`

**Line Numbers:** 691-709 (19 lines)
**Function Type:** IO
**Complexity:** Medium

**Purpose:**
Creates a backup copy of a file by copying source to backup location. Handles both Railway (reads from GitHub, writes to GitHub) and local (filesystem copy) environments.

**Full Signature:**
```python
def backup_file(source_path: str, backup_path: str):
    """Creates a backup of a file.

    This function creates a backup of a file by copying it to a new location.
    It handles both Railway and local environments.

    Args:
        source_path (str): The path to the source file.
        backup_path (str): The path to the backup file.
    """
```

**Parameters:**
- `source_path` (str): File to backup from
- `backup_path` (str): Destination backup path

**Returns:**
- None

**Workflow:**
- **On Railway:** Read from GitHub → Write backup to GitHub
- **Locally:** Copy file using `shutil.copy()`

**Dependencies:**
- `shutil` (copy)
- Internal: `_is_railway()`, `read_from_github()`, `write_to_github()`, `BASE_DIR`, `_get_local_path()`

**Used By:**
- `1000Data update.py` - Backup before updating
- `delete_data.py` - Backup before deletion
- Data maintenance operations

**Technical Notes:**
- Creates backup directory if needed
- For local: uses `shutil.copy()` which preserves metadata
- For Railway: reads data → writes as backup file
- No version control (overwrites existing backup)

**Improvement Opportunities:**
- Could add timestamp to backup filename
- Could implement backup rotation (keep N backups)
- Could validate backup integrity after creation
- Could return success/failure status

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** File I/O operation
- **Priority:** MEDIUM - Not critical
- **Breaking Changes:** No

---

## Section Summary

**Section Statistics:**
- Total Public Functions: 6 (`read_file`, `write_file`, `read_text_file`, `write_text_file`, `clear_volume_cache`, `backup_file`)
- Total Helper Functions: 4 (`_is_railway`, `_get_volume_path`, `_get_local_path`, `_ensure_volume_dir`)
- Total Lines: ~350 lines of code
- Complexity: Mostly Medium, one Complex

**Key Architectural Patterns:**

1. **Environment-Aware Abstraction:**
   ```
   read_file(path)
   ├─ If Railway: check volume → GitHub → cache
   └─ If Local: read filesystem
   ```

2. **Unified API:**
   - Same function calls work in both environments
   - No conditional logic needed in calling code
   - Transparent fallback strategy

3. **Deferred Commit Pattern:**
   - `defer_github=True` → Returns dict for batch
   - Enables atomic multi-file commits
   - Performance optimization for bulk updates

**Performance Characteristics:**

| Operation | Railway (Cache Hit) | Railway (Cache Miss) | Local |
|-----------|-------------------|-------------------|-------|
| read_file() | 50-100ms | 2-5s | 100-200ms |
| write_file() | 500-1000ms | 1-2s | 100-300ms |

**Critical Dependencies:**
- ALL data operations depend on these functions
- ~50+ files import from this section
- Blocking any function breaks core functionality

**Production Readiness:**
- ✅ Handles Railway environment correctly
- ✅ Handles local development
- ✅ Intelligent caching strategy
- ⚠️ No retry logic for network failures
- ⚠️ No timeout protection
- ⚠️ Minimal error logging

**Recommended Improvements:**
1. Add exponential backoff retry on GitHub failures
2. Add timeout protection for network operations
3. Add file size validation
4. Add checksum verification
5. Add detailed operation logging
6. Consider compression for large files
7. Implement cache size management

---

