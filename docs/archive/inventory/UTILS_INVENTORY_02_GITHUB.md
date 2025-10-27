# Utils.py Inventory - Section 2: GitHub I/O Functions

**Section:** GitHub I/O Functions
**Function Count:** 5 functions
**Lines in utils.py:** 137-360
**Estimated Complexity:** Medium to Complex

---

## Section Overview

This section documents all functions that interact with the GitHub repository. These functions are critical for the Railway production environment, where data persists in GitHub rather than local storage. They handle:

- Reading data files (CSV, Parquet, text) from GitHub
- Writing data files to GitHub
- Batch committing multiple files in a single operation
- Text-specific I/O operations

**Architecture Context:** In production (Railway), these are the PRIMARY data storage mechanism. All application data is versioned and persisted in the GitHub repository.

---

## Functions

### 1. `read_from_github(file_path: str) -> Union[pd.DataFrame, str]`

**Line Numbers:** 137-169 (33 lines)
**Function Type:** IO
**Complexity:** Medium

**Purpose:**
Reads a file from the GitHub repository, automatically handling different file types:
- CSV files → returns as pandas DataFrame
- Parquet files → returns as pandas DataFrame
- Other text files → returns as decoded string

Uses PyGithub library to access the GitHub API with authentication via `GITHUB_TOKEN` environment variable or Streamlit secrets.

**Full Signature:**
```python
def read_from_github(file_path: str) -> Union[pd.DataFrame, str]:
    """Reads a file from the GitHub repository.

    This function reads a file from the specified path in the GitHub repository.
    It handles both CSV and Parquet files, decoding them appropriately.

    Args:
        file_path (str): The path to the file in the GitHub repository.

    Returns:
        pd.DataFrame or str: A pandas DataFrame if the file is a CSV or
        Parquet file, otherwise the decoded content of the file as a string.
    """
```

**Parameters:**
- `file_path` (str): Path to file in repository (e.g., "data/all-scores.parquet", "data/handicaps.csv")

**Returns:**
- `Union[pd.DataFrame, str]`:
  - DataFrame if CSV or Parquet file
  - String if any other file type

**Dependencies:**
- **External Packages:**
  - `pandas` (read_csv, read_parquet)
  - `github` (PyGithub library)
  - `base64` (decode)
  - `io` (BytesIO, StringIO)
  - `os` (environment variables)
- **Internal Functions:**
  - `get_current_branch()` - Gets branch to read from
  - Uses constants: `GITHUB_REPO`
- **Streamlit-Specific:** Yes - accesses `st.secrets`
- **File I/O:** No (GitHub API only)

**Environment Variables & Secrets:**
```python
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN')
```

**API Calls:**
```python
g = Github(token)
repo = g.get_repo(GITHUB_REPO)
content = repo.get_contents(file_path, ref=get_current_branch())
```

**Used By (Usage Sites):**
- `streamlit/admin_volume_management.py` - Volume backup operations
- `streamlit/utils.py` internal calls:
  - `read_file()` - Used when volume cache miss occurs
  - `backup_file()` - Reading source file to backup
  - `load_and_prepare_handicap_data()` - Via read_file()
  - `update_teg_status_files()` - Via read_file()

**Function Type Analysis:**
- **Classification:** IO - GitHub API operations
- **Streamlit-Specific:** Yes - uses `st.secrets`
- **Network Operations:** Yes - GitHub API calls
- **Error Handling:** Minimal (throws exceptions)
- **Data Transformation:** Yes - decoding base64, creating DataFrames

**Error Scenarios:**
- `FileNotFoundError` - If file doesn't exist in GitHub
- `github.GithubException` - If authentication fails or API error occurs
- `ValueError` - If unsupported file type

**Technical Notes:**
- Uses base64 encoding/decoding because GitHub API returns base64-encoded content
- For Parquet files: decodes to bytes, then reads with BytesIO
- For CSV files: decodes to string, then parses with StringIO
- Gets branch via `get_current_branch()` to support multiple branches
- No local caching here - that's handled by `read_file()`

**Migration Recommendation:**
- **Target Module:** Keep in utils.py OR move to `streamlit/github_client.py`
- **Rationale:** GitHub-specific I/O operation; could be consolidated with other GitHub functions into dedicated module
- **Priority:** MEDIUM - Important but stable
- **Breaking Changes:** Would break Railway production data loading if removed

**Potential Issues:**
- No retry logic for network failures
- Could time out on large files
- Hardcoded branch switching via `get_current_branch()` - could support explicit branch parameter

---

### 2. `read_text_from_github(file_path: str) -> str`

**Line Numbers:** 172-193 (22 lines)
**Function Type:** IO
**Complexity:** Medium

**Purpose:**
Specialized variant of `read_from_github()` optimized for text files (markdown, JSON, text, etc.). Returns content as decoded string instead of attempting DataFrame parsing. Cleaner API for text-specific operations.

**Full Signature:**
```python
def read_text_from_github(file_path: str) -> str:
    """Reads a text file from the GitHub repository.

    This function is optimized for reading text files (e.g., .md, .txt, .json)
    from the GitHub repository. It returns the content as a decoded string.

    Args:
        file_path (str): The path to the file in the GitHub repository.

    Returns:
        str: The decoded content of the file as a string.
    """
```

**Parameters:**
- `file_path` (str): Path to text file in repository (e.g., "README.md", "config.json")

**Returns:**
- `str`: Full file content as decoded string

**Dependencies:**
- **External Packages:**
  - `github` (PyGithub)
  - `base64` (decode)
  - `os` (environment)
- **Internal Functions:**
  - `get_current_branch()` - Gets branch to read from
  - Uses constants: `GITHUB_REPO`
- **Streamlit-Specific:** Yes - accesses `st.secrets`
- **File I/O:** No (GitHub API)

**Used By (Usage Sites):**
- `streamlit/utils.py` internal calls:
  - `read_text_file()` - Used when Railway volume cache miss occurs
  - `write_text_file()` - For reading before updating
- Commentary/reporting functions for reading external data

**Function Type Analysis:**
- **Classification:** IO - GitHub API operation
- **Streamlit-Specific:** Yes - `st.secrets`
- **Network Operations:** Yes - GitHub API
- **Data Transformation:** Base64 decoding only

**Comparison with `read_from_github()`:**
| Aspect | read_from_github() | read_text_from_github() |
|--------|-------------------|------------------------|
| File Types | CSV, Parquet, text | Text only |
| Return Type | DataFrame or str | Always str |
| Processing | May create DataFrame | Simple decode |
| Use Case | Data files primarily | Config, markdown, JSON |

**Migration Recommendation:**
- **Target Module:** Keep in utils.py OR consolidate with `read_from_github()`
- **Rationale:** Redundant with `read_from_github()`; could be merged
- **Priority:** LOW - Could be consolidated
- **Breaking Changes:** Minor - would need to check file type before calling

---

### 3. `write_text_to_github(file_path: str, content: str, commit_message: str = "Update text file") -> None`

**Line Numbers:** 196-240 (45 lines)
**Function Type:** IO
**Complexity:** Medium

**Purpose:**
Writes text content to GitHub repository, creating new file if doesn't exist or updating if it does. Handles all encoding/authentication/commit details automatically.

**Full Signature:**
```python
def write_text_to_github(
    file_path: str,
    content: str,
    commit_message: str = "Update text file"
) -> None:
    """Writes a text file to the GitHub repository.

    This function writes string content to the specified file path in the GitHub
    repository. If the file already exists, it will be updated. Otherwise,
    a new file will be created.

    Args:
        file_path (str): The path to the file in the GitHub repository.
        content (str): The text content to write to the file.
        commit_message (str, optional): The commit message to use for the
            write operation. Defaults to "Update text file".
    """
```

**Parameters:**
- `file_path` (str): Path where file will be created/updated
- `content` (str): Text content to write
- `commit_message` (str, optional): Git commit message. Defaults to "Update text file"

**Returns:**
- None

**Dependencies:**
- **External Packages:**
  - `github` (PyGithub)
  - `base64` (encode)
  - `os` (environment)
- **Internal Functions:**
  - `get_current_branch()` - Gets branch to write to
  - Uses constants: `GITHUB_REPO`
- **Streamlit-Specific:** Yes - `st.secrets`
- **File I/O:** No (GitHub API)

**Workflow:**
1. Connect to GitHub API with authentication
2. Encode content to UTF-8 bytes, then base64
3. Try to get existing file SHA (for update)
4. If exists: call `update_file()` with SHA
5. If not exists: call `create_file()` to create new
6. Log success/failure

**Used By (Usage Sites):**
- `streamlit/utils.py` internal calls:
  - `write_text_file()` - Used when writing text in production
  - `update_teg_status_files()` - Via write_file()

**Function Type Analysis:**
- **Classification:** IO - GitHub API operation
- **Streamlit-Specific:** Yes - `st.secrets`
- **Network Operations:** Yes - GitHub API
- **Side Effects:** Creates/updates file in GitHub repo
- **Error Handling:** Try-except for create vs update

**Technical Notes:**
- Encodes content as UTF-8 then base64 to match GitHub API requirements
- Uses try-except to distinguish between "file exists" (update) and "file not found" (create)
- Logs both operations with logger (set to ERROR level in production)
- Branch determined via `get_current_branch()`

**Error Scenarios:**
- GitHub authentication failure → Exception raised
- Network error → Exception raised
- Invalid file path → GitHub API error

**Migration Recommendation:**
- **Target Module:** Keep in utils.py OR move to `streamlit/github_client.py`
- **Rationale:** Core GitHub operation, should remain in utils.py
- **Priority:** MEDIUM - Critical for data persistence
- **Breaking Changes:** Would break any file writing if removed

---

### 4. `write_to_github(file_path: str, data: Union[pd.DataFrame, str], commit_message: str = "Update data") -> None`

**Line Numbers:** 243-285 (43 lines)
**Function Type:** IO
**Complexity:** Medium

**Purpose:**
Writes either a pandas DataFrame or string data to GitHub. Automatically detects file type and formats appropriately:
- CSV path → writes as CSV
- Parquet path → writes as Parquet binary
- Other → writes as text

**Full Signature:**
```python
def write_to_github(
    file_path: str,
    data: Union[pd.DataFrame, str],
    commit_message: str = "Update data"
) -> None:
    """Writes a file to the GitHub repository.

    This function writes data to the specified file path in the GitHub
    repository. It can handle both pandas DataFrames (CSV or Parquet) and
    string data. If the file already exists, it will be updated. Otherwise,
    a new file will be created.

    Args:
        file_path (str): The path to the file in the GitHub repository.
        data (pd.DataFrame or str): The data to write to the file.
        commit_message (str, optional): The commit message to use for the
            write operation. Defaults to "Update data".
    """
```

**Parameters:**
- `file_path` (str): Path for file in GitHub (e.g., "data/all-scores.parquet")
- `data` (Union[pd.DataFrame, str]): Data to write - DataFrame or string
- `commit_message` (str, optional): Git commit message

**Returns:**
- None

**Dependencies:**
- **External Packages:**
  - `pandas` (to_csv, to_parquet)
  - `github` (PyGithub)
  - `base64` (encode)
  - `io` (BytesIO)
  - `os` (environment)
- **Internal Functions:**
  - `get_current_branch()` - Gets branch to write to
  - Uses constants: `GITHUB_REPO`
- **Streamlit-Specific:** Yes - calls `st.cache_data.clear()`
- **File I/O:** No (GitHub API)

**Workflow:**
1. Prepare content based on file type:
   - CSV: `data.to_csv(index=False)`
   - Parquet: `data.to_parquet()` into BytesIO buffer
   - String: use as-is
2. Try to update existing file, fallback to create new
3. Clear Streamlit cache to ensure fresh data

**Used By (Usage Sites):**
- `streamlit/utils.py` internal calls:
  - `write_file()` - Railway GitHub sync
  - `batch_commit_to_github()` - Individual file handling
  - `backup_file()` - Backup to GitHub
- `streamlit/helpers/data_update_processing.py` - Data updates (via batch_commit)
- `streamlit/helpers/data_deletion_processing.py` - Data deletions (via batch_commit)

**Function Type Analysis:**
- **Classification:** IO - GitHub API operation
- **Streamlit-Specific:** Yes - calls `st.cache_data.clear()`
- **Network Operations:** Yes - GitHub API
- **Side Effects:** GitHub repo modification + cache clear
- **Data Transformation:** DataFrame → CSV/Parquet serialization

**Technical Notes:**
- Calls `st.cache_data.clear()` after successful write to ensure consistency
- Uses BytesIO for Parquet serialization to get bytes for API
- File type detection based on file extension
- Bare except clause (could be improved with specific exception handling)

**Error Scenarios:**
- Invalid DataFrame for CSV/Parquet → pandas error
- GitHub API failure → Exception
- Cache clear failure → Logged but continues

**Improvement Opportunities:**
- Add explicit file type handling for unsupported extensions
- Implement specific exception catching instead of bare except
- Add retry logic for network failures
- Add size validation before write

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** Critical for Railway data persistence
- **Priority:** CRITICAL - Cannot be migrated without major refactoring
- **Breaking Changes:** Would completely break production data writing

---

### 5. `batch_commit_to_github(files_data: list, commit_message: str = "Batch update data") -> None`

**Line Numbers:** 287-359 (73 lines)
**Function Type:** IO
**Complexity:** Complex

**Purpose:**
Optimizes multiple file writes by combining them into a SINGLE GitHub commit. This is significantly more efficient than calling `write_to_github()` multiple times, as it reduces API calls and Git operations.

Uses GitHub's Tree API to create a multi-file commit in one operation.

**Full Signature:**
```python
def batch_commit_to_github(
    files_data: list,
    commit_message: str = "Batch update data"
) -> None:
    """Commits multiple files to GitHub in a single commit.

    This function optimizes GitHub API usage by creating a single commit with
    multiple file changes, which is significantly faster for bulk updates than
    committing each file individually.

    Args:
        files_data (list): A list of dictionaries, where each dictionary
            contains the `file_path` and `data` for a file to be committed.
            Example: `[{'file_path': 'data/file.csv', 'data': df}, ...]`.
        commit_message (str, optional): The commit message for the batch
            update. Defaults to "Batch update data".
    """
```

**Parameters:**
- `files_data` (list[dict]): List of dicts with 'file_path' and 'data' keys
  ```python
  [
      {'file_path': 'data/file1.parquet', 'data': df1},
      {'file_path': 'data/file2.parquet', 'data': df2},
      {'file_path': 'data/cache.parquet', 'data': df3},
  ]
  ```
- `commit_message` (str, optional): Commit message

**Returns:**
- None

**Dependencies:**
- **External Packages:**
  - `pandas` (to_csv, to_parquet)
  - `github` (Github, InputGitTreeElement)
  - `base64` (encode)
  - `io` (BytesIO)
  - `os` (environment)
- **Internal Functions:**
  - `get_current_branch()` - Gets branch to commit to
  - Uses constants: `GITHUB_REPO`
- **Streamlit-Specific:** Yes - calls `st.cache_data.clear()`
- **File I/O:** No (GitHub API)

**Workflow:**
1. Get current branch and its HEAD commit
2. For each file in files_data:
   - Format content (CSV, Parquet, or string)
   - Create Git blob (encoded for binary, utf-8 for text)
   - Create InputGitTreeElement referencing the blob
3. Create new tree with all blobs
4. Create new commit referencing the new tree
5. Update branch reference to point to new commit
6. Clear Streamlit cache

**Used By (Usage Sites):**
- `streamlit/helpers/data_update_processing.py` - Batch update data + caches
- `streamlit/helpers/data_deletion_processing.py` - Batch deletion + cache updates
- `streamlit/utils.py` internal:
  - `update_all_data()` - Can use defer_github with batch
  - Cache update functions - Can be deferred for batch

**Function Type Analysis:**
- **Classification:** IO - GitHub API operation
- **Streamlit-Specific:** Yes - `st.cache_data.clear()`
- **Network Operations:** Yes - Multiple GitHub API calls
- **Side Effects:** Single GitHub commit + cache clear
- **Complexity:** High - Multi-step Git tree operation

**Technical Notes:**
- Uses GitHub Tree API for atomic multi-file commit
- Significantly more efficient than multiple `write_to_github()` calls
- Supports both text (utf-8) and binary (base64) file formats
- InputGitTreeElement specifies file mode 100644 (regular file)
- Logs number of files committed

**Performance Comparison:**
| Operation | API Calls | Commits | Time |
|-----------|-----------|---------|------|
| 5 × write_to_github() | 5-10 | 5 | ~5 seconds |
| batch_commit_to_github([5 files]) | 5-6 | 1 | ~2 seconds |

**Error Scenarios:**
- Invalid file path → GitHub error
- DataFrame serialization failure → pandas error
- Branch not found → GitHub error
- Authentication failure → GitHub error

**Migration Recommendation:**
- **Target Module:** Keep in utils.py
- **Rationale:** Critical performance optimization for data updates
- **Priority:** CRITICAL - Cannot remove
- **Breaking Changes:** Would break batch data update operations

**Potential Improvements:**
- Add error recovery for individual file failures
- Implement rollback on commit failure
- Add optional dry-run mode
- Add detailed logging of each file operation

---

## Section Summary

**Section Statistics:**
- Total Functions: 5 GitHub I/O functions
- Total Lines: ~220 lines of code
- Complexity: Medium to Complex (lots of API handling)

**Key Points:**
1. All functions use PyGithub for GitHub API access
2. Authentication via `GITHUB_TOKEN` environment variable or Streamlit secrets
3. All operations are **production-critical** for Railway deployment
4. Branch support via `get_current_branch()` allows multi-branch workflows
5. Automatic cache clearing ensures data consistency

**Dependencies:**
- All depend on: `GITHUB_REPO`, `get_current_branch()`, `GITHUB_TOKEN`
- Dependent functions: ALL file I/O in Railway production
- Alternative flow: Local development uses file system instead

**Performance Considerations:**
- Individual writes: 1 commit + API calls per file
- Batch writes: 1 commit + fewer API calls total
- Network latency dominates execution time
- No built-in retry logic (could timeout)

**Security Notes:**
- `GITHUB_TOKEN` should have limited scopes (data repo only)
- Tokens stored in environment or Streamlit secrets
- No hardcoded credentials in code
- All operations logged for audit trail

---

