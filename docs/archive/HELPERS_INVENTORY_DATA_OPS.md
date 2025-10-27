# Helpers Inventory: Data Operations Modules

**Category:** Data Update & Deletion Operations
**Total Modules:** 2
**Total LOC:** ~604 lines
**Streamlit Dependencies:** Yes (Both modules)
**Overall Status:** ⚠️ Mixed (Data validation core + Streamlit UI workflow)

---

## Module: `helpers/data_update_processing.py`

**Lines of Code:** 380
**Purpose:** Manages the multi-step data update workflow including Google Sheets data validation, duplicate detection, and cache regeneration.
**Created/Refactored:** Well-structured with clear state management
**Status:** ⚠️ Mixed - Core logic + Streamlit UI workflow

### Module-Level Information

**Imports:**
- External: `pandas`, `logging`
- Internal: `streamlit as st` (UI workflow management)
- Streamlit: Yes - session state, spinner, error messages
- Utils: Extensive imports for core data processing

**Used By (pages):**
- `1000Data update.py`

**Dependencies ON Other Helpers:**
- None (uses utils functions)

---

### State Management Constants

**STATE_* constants** (lines 34-38)
- `STATE_INITIAL` - Initial page state
- `STATE_DATA_LOADED` - Data loaded from Google Sheets
- `STATE_PROCESSING` - Processing data
- `STATE_OVERWRITE_CONFIRM` - Awaiting overwrite confirmation

These manage the multi-step workflow in Streamlit.

---

### Core Data Processing Functions

#### Function 1: `initialize_update_state()`

**Line Numbers:** 41-55
**Type:** STREAMLIT

**Purpose:**
Initializes session state for data update workflow.

**Must Stay In:** `streamlit/helpers/`

---

#### Function 2: `process_google_sheets_data()`

**Line Numbers:** 58-82
**Type:** PURE (can be extracted)

**Signature:**
```python
def process_google_sheets_data(raw_df: pd.DataFrame) -> pd.DataFrame:
```

**Purpose:**
Transforms wide-format Google Sheets data to long format, validates completeness, removes invalid scores.

**Key Steps:**
1. Reshape from wide to long format (by hole)
2. Remove NaN and 0 scores
3. Filter to complete 18-hole rounds

**Parameters:**
- `raw_df` (pd.DataFrame): Raw Google Sheets data

**Returns:**
- `pd.DataFrame`: Processed long-format data

**Dependencies:**
- `reshape_round_data()` from utils
- Pandas groupby/filtering

**Complexity:** Medium

**Migration Target:** `teg_analysis/data/validation.py`
**Priority:** 🟡 (can move, but currently tightly integrated with workflow)

---

#### Function 3: `check_for_duplicate_data()`

**Line Numbers:** 85-126
**Type:** PURE (can be extracted)

**Purpose:**
Identifies duplicate records by comparing new data with existing data at hole level.

**Key Algorithm:**
1. Load existing data from parquet
2. Create hole-level keys (TEG, Round, Hole, Player)
3. Find intersection (duplicates)
4. Store duplicate keys for later use

**Returns:**
- `bool`: True if duplicates found

**Side Effects:**
- Sets session state variables with duplicate data

**Complexity:** Medium

**Migration Target:** `teg_analysis/data/validation.py`
**Priority:** 🟡

---

#### Function 4: `analyze_hole_level_differences()`

**Line Numbers:** 129-182
**Type:** PURE DATA

**Purpose:**
Compares scores for duplicate records to identify actual score differences.

**Returns:**
- `tuple`: (differences_df, has_differences)

**Complexity:** Medium

**Migration Target:** `teg_analysis/data/validation.py`
**Priority:** 🟡

---

#### Function 5: `execute_data_update()`

**Line Numbers:** 185-359
**Type:** MIXED - CRITICAL WORKFLOW FUNCTION

**Signature:**
```python
def execute_data_update(overwrite: bool = False, new_data_only: bool = False):
```

**Purpose:**
Core data update orchestration - the main workflow function that:
1. Combines existing and new data (with overwrite/dedup logic)
2. Processes rounds through handicap calculations
3. Saves to parquet/CSV files
4. Updates all derived caches (streaks, commentary, bestball, TEG status)
5. Commits to GitHub (Railway only)

**Key Workflow:**
```
1. Handle overwrite/new_data_only logic
2. Load handicap data
3. Process rounds for all scores (GrossVP, NetVP, Stableford, etc.)
4. Combine with existing data
5. Save all-scores file
6. Update all-data file
7. Clear Streamlit caches (!important - must happen early)
8. Update TEG status files
9. Update streaks cache
10. Update commentary caches
11. Update bestball cache
12. Batch commit to GitHub
```

**Complex Features:**
- Captures changed rounds for optional commentary generation
- Proper cache clearing sequence (before cache regeneration)
- Batch GitHub commits (Railway only)
- Error handling with logging
- Session state management for UI feedback

**Complexity:** HIGH

**Note:** This function orchestrates many utils functions. The actual data processing is delegated to utils.

**Migration Target:** Core logic stays in analysis, UI/workflow stays in Streamlit
**Priority:** 🔴 (Complex, needs careful refactoring)

---

#### Function 6: `create_data_summary_display()`

**Line Numbers:** 362-380
**Type:** PURE

**Purpose:**
Creates summary display of loaded data for user confirmation.

**Migration Target:** `teg_analysis/data/`
**Priority:** 🟢

---

### Module Analysis

**Summary:**
- Total Functions: 6
- Pure Functions: 3 (data processing, analysis)
- Mixed Functions: 2 (with session state side effects)
- Streamlit-Dependent: 1 (init/state management)

**Migration Plan:**

**Keep in Streamlit:**
- `initialize_update_state()` - Session state management

**Can Extract to Analysis Layer:**
- `process_google_sheets_data()` → `teg_analysis/data/validation.py`
- `analyze_hole_level_differences()` → `teg_analysis/data/validation.py`
- `create_data_summary_display()` → `teg_analysis/data/`

**Needs Careful Refactoring:**
- `check_for_duplicate_data()` - Has session state side effects
- `execute_data_update()` - Complex orchestration function

**Key Characteristics:**
- Well-organized workflow
- Clear state management
- Good separation of concerns (mostly)
- Heavy orchestration of utils functions

**Risk:** MEDIUM | **Effort:** MEDIUM | **Complexity:** HIGH

---

## Module: `helpers/data_deletion_processing.py`

**Lines of Code:** 224
**Purpose:** Manages the multi-step data deletion workflow including preview, backup creation, and cache regeneration.
**Created/Refactored:** Well-structured
**Status:** ⚠️ Mixed - Data operations + Streamlit UI workflow

### Module-Level Information

**Imports:**
- External: `pandas`, `datetime`
- Internal: `streamlit as st`
- Streamlit: Yes - session state, error messages
- Utils: Imports for data file operations

**Used By (pages):**
- `delete_data.py`

**Dependencies ON Other Helpers:**
- None (uses utils functions)

---

### State Management

**STATE_* constants** (lines 14-17)
- `STATE_INITIAL` - Initial state
- `STATE_PREVIEW` - Preview deletion
- `STATE_CONFIRMED` - Confirmed deletion

---

### Core Functions

#### Function 1: `initialize_deletion_state()`

**Line Numbers:** 20-35
**Type:** STREAMLIT

**Purpose:**
Initializes session state for deletion workflow.

**Must Stay In:** `streamlit/helpers/`

---

#### Function 2: `load_scores_data()`

**Line Numbers:** 38-46
**Type:** MIXED

**Purpose:**
Loads scores data into session state.

**Could Extract:** Pure data loading logic

---

#### Function 3: `get_available_tegs_and_rounds()`

**Line Numbers:** 49-71
**Type:** PURE DATA

**Purpose:**
Gets available TEGs and rounds for selection dropdowns.

**Returns:**
- `tuple`: (teg_nums, get_rounds_for_teg callable)

**Migration Target:** `teg_analysis/data/`
**Priority:** 🟢

---

#### Function 4: `create_timestamped_backups()`

**Line Numbers:** 74-95
**Type:** PURE

**Purpose:**
Creates timestamped backups before deletion for safety.

**Key Features:**
- Creates dated backup file paths
- Calls `backup_file()` from utils

**Returns:**
- `tuple`: (scores_backup_path, data_backup_path)

**Migration Target:** `teg_analysis/data/backup.py`
**Priority:** 🟢

---

#### Function 5: `preview_deletion_data()`

**Line Numbers:** 98-120
**Type:** PURE

**Purpose:**
Creates preview of data that will be deleted for user confirmation.

**Returns:**
- `pd.DataFrame`: Rows that will be deleted

**Migration Target:** `teg_analysis/data/`
**Priority:** 🟢

---

#### Function 6: `execute_data_deletion()`

**Line Numbers:** 123-210
**Type:** MIXED - CRITICAL WORKFLOW

**Signature:**
```python
def execute_data_deletion(selected_teg: int, selected_rounds: list):
```

**Purpose:**
Core deletion orchestration - manages the complete deletion workflow:
1. Create backups
2. Load both data files
3. Create deletion filters
4. Remove selected data from both datasets
5. Save updated files
6. Update TEG status, streaks, commentary, bestball caches
7. Batch commit to GitHub
8. Clear caches

**Key Workflow:**
```
1. Backup creation (safety first)
2. Load and filter data
3. Save updated files
4. Update all caches
5. GitHub commit
6. Clear Streamlit caches
```

**Complex Features:**
- Dual-file deletion (ALL_SCORES_PARQUET + ALL_DATA_PARQUET)
- Cascading cache updates
- Batch GitHub commits
- Error handling

**Complexity:** HIGH

**Migration Target:** Orchestration stays in Streamlit, core logic extracts to analysis
**Priority:** 🔴 (Complex workflow)

---

#### Function 7: `validate_deletion_selection()`

**Line Numbers:** 213-224
**Type:** PURE

**Purpose:**
Validates that at least one round is selected for deletion.

**Returns:**
- `bool`: True if selection is valid

**Migration Target:** `teg_analysis/data/validation.py`
**Priority:** 🟢

---

### Module Analysis

**Summary:**
- Total Functions: 7
- Pure Functions: 4 (data operations, validation)
- Mixed Functions: 2 (with workflow state)
- Streamlit-Dependent: 1 (state init)

**Migration Plan:**

**Keep in Streamlit:**
- `initialize_deletion_state()` - Session state

**Can Extract:**
- `get_available_tegs_and_rounds()` → `teg_analysis/data/`
- `create_timestamped_backups()` → `teg_analysis/data/backup.py`
- `preview_deletion_data()` → `teg_analysis/data/`
- `validate_deletion_selection()` → `teg_analysis/data/validation.py`
- `load_scores_data()` (pure logic) → `teg_analysis/data/`

**Needs Refactoring:**
- `execute_data_deletion()` - Large orchestration function

**Risk:** MEDIUM | **Effort:** MEDIUM | **Complexity:** HIGH

---

## Cross-Module Summary

### Total Data Ops: 604 lines

| Module | LOC | Status | Type | Migration Strategy |
|--------|-----|--------|------|-------------------|
| data_update_processing.py | 380 | ⚠️ Mixed | Workflow | Split: 40% extract, 60% refactor |
| data_deletion_processing.py | 224 | ⚠️ Mixed | Workflow | Split: 50% extract, 50% refactor |

### Key Insights

1. **Two Large Orchestration Functions:**
   - `execute_data_update()` - Very complex, coordinates 10+ sub-operations
   - `execute_data_deletion()` - Complex, coordinates 8+ sub-operations

2. **Shared Patterns:**
   - Both follow similar multi-step workflow
   - Both require session state management
   - Both handle GitHub commits
   - Both regenerate caches

3. **Extractable Pure Functions:**
   - Data validation (duplicate checking)
   - Backup creation
   - Data preview generation
   - Filter validation

4. **Workflow-Critical Logic:**
   - State machine for multi-step UI
   - Cache clearing sequence (very important!)
   - GitHub batch commit orchestration

### Recommended Refactoring Strategy

**Phase 1: Extract Pure Functions**
```
teg_analysis/data/
  ├── validation.py (duplicate checking, schema validation)
  ├── backup.py (backup creation)
  └── preview.py (deletion/update preview)
```

**Phase 2: Create Workflow Layer**
```
streamlit/workflows/
  ├── data_update_workflow.py (orchestrates update process)
  └── data_deletion_workflow.py (orchestrates deletion process)
```

**Phase 3: Consolidate Cache Management**
```
teg_analysis/cache/
  └── manager.py (unified cache update orchestration)
```

### Complexity Assessment

| Function | Complexity | Refactoring Effort |
|----------|------------|-------------------|
| `process_google_sheets_data()` | Medium | LOW |
| `check_for_duplicate_data()` | Medium | MEDIUM |
| `analyze_hole_level_differences()` | Medium | LOW |
| `execute_data_update()` | HIGH | MEDIUM-HIGH |
| `execute_data_deletion()` | HIGH | MEDIUM-HIGH |

### Total Effort: MEDIUM | Total Risk: MEDIUM

These modules are suitable for refactoring but require careful planning. The orchestration functions are complex and tightly coupled to Streamlit's workflow management, cache system, and GitHub operations.

### Critical Considerations

1. **Cache Clearing Sequence:** Must clear Streamlit caches BEFORE regenerating dependent caches
2. **GitHub Batch Commits:** Railway-only feature, needs conditional logic
3. **Error Handling:** Failures during cache updates shouldn't stop the workflow
4. **Session State:** Multi-step workflows need persistent state across reloads

