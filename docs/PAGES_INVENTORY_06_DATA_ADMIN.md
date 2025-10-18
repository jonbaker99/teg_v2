# Streamlit Pages Inventory - Section 6: Data & Admin (System Management)

**Section:** Data Management & Administration
**Pages:** 5
**Total Lines:** ~2,240
**Refactoring Status:** ✅ 100% (5/5 refactored)

---

## Contents Overview

This section documents all 5 user-facing pages in the Data & Admin section, which manage tournament data, generate reports, handle deletions, and provide system diagnostics. These are admin functions requiring careful handling.

| Page | File | Lines | Status | Complexity |
|------|------|-------|--------|-----------|
| Data Update | 1000Data update.py | 379 | ✅ | Complex |
| Report Generation | 1001Report Generation.py | 609 | ✅ | Complex |
| Data Edit | data_edit.py | 291 | ✅ | Medium |
| Delete Data | delete_data.py | 124 | ✅ | Medium |
| Volume Management | admin_volume_management.py | 817 | ✅ | Complex |

---

## Page: `1000Data update.py`

**Title:** Data Update (Tournament Data Pipeline)
**Lines of Code:** 379
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Complex

### Purpose

Administrative interface for updating tournament data from Google Sheets import with automatic derived field calculation (handicaps, scores vs par, etc.) and GitHub commit for version control. Critical operational page for maintaining tournament data. Admins visit to refresh data from Google Sheets and commit updates.

### Data Loading

- **Functions:**
  - `read_file()` - Reads existing data
  - `write_file()` - Writes updated data
  - Google Sheets API integration
  - Extensive validation pipeline
- **Files:** all-scores.parquet, round_info.csv, handicaps.csv, Google Sheets
- **Key Parameters:** Various validation parameters
- **Caching:** Cleared after update (st.cache_data.clear())

### Dependencies

**From utils.py:**
- Extensive set (20+ functions) for data operations:
  - `read_file()` - File loader
  - `write_file()` - File writer
  - Data format functions
  - GitHub integration functions (commit, push)
  - Cache control

**From helpers/data_update_processing.py:**
- `validate_input_data()` - Input validation
- `calculate_derived_fields()` - Handicaps, GrossVP, Stableford
- `transform_data_format()` - Format normalization
- `commit_to_github()` - GitHub operations
- Other data processing pipeline functions

**From google.auth & gspread:**
- Google Sheets API integration
- OAuth authentication

**Streamlit Components:**
- `st.button()` - Trigger buttons (Import, Update, Refresh)
- `st.spinner()` - Loading indicators
- `st.success()` - Success messages
- `st.error()` - Error messages
- `st.expander()` - Validation details
- `st.dataframe()` - Preview tables
- `st.cache_data.clear()` - Cache management
- `st.markdown()` - Display content

### Embedded Logic

**Functions Defined:** Minimal (orchestration only)

**Analysis:** Well-extracted to data_update_processing helper. Page is pure UI orchestration.

### User Interactions

**Widgets:**
- Button: Import data from Google Sheets
- Button: Validate imported data
- Button: Save to local/GitHub
- Button: Refresh cache
- Expanders: Show validation results, preview data
- Status displays: Success/error messages

**Session State:** Progress tracking (success/error states)

### Display Components

**Charts:** None

**Tables:**
- Data preview tables (before/after validation)
- Validation results table
- Error log

**Layout:**
- Button controls
- Status messages
- Collapsible validation details
- Data preview section

### CSS/Styling

- `load_datawrapper_css()` - Table styling
- Standard alert colors for status

### Migration Analysis

**Complexity:** Complex

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Consider adding rollback functionality - future feature
3. Add comprehensive error recovery - future feature
4. Document Google Sheets format requirements - 1 hour

**Estimated Effort:** 1-2 hours (documentation only)

**Blockers:** None critical

### Page-Specific Notes

- **CRITICAL PAGE**: Manages all tournament data
- Requires careful testing before deployment
- GitHub integration for version control
- Cache clearing strategy important (no TTL, manual clear)
- Validation pipeline prevents bad data commits
- Good error handling and user feedback
- Should have audit logging (not currently implemented)

---

## Page: `1001Report Generation.py`

**Title:** Report Generation (AI Commentary Generation)
**Lines of Code:** 609
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Complex

### Purpose

AI-powered tournament report generation using Claude API with batch processing for round and full tournament reports. Generates automated commentary, analysis, and narrative reports for completed tournaments. Admins visit to generate reports in batch and manage commentary generation.

### Data Loading

- **Functions:**
  - `load_all_data()` - Tournament data
  - `read_file()` - File reading
  - Extensive commentary generation pipeline
- **Files:** all-scores.parquet, round_info.csv, output commentary markdown files
- **Key Parameters:** TEG selection, report type selection
- **Caching:** None (API calls not cached, new generation each time)

### Dependencies

**From utils.py:**
- `load_all_data()` - Tournament data
- `read_file()` - File loader
- `write_file()` - File writer
- Cache/config access

**From helpers/commentary_generator.py:**
- Report generation orchestration
- API call management

**From commentary/** (specialized modules):
- `commentary/batch_api.py` - Batch API calls
- `commentary/generate_commentary.py` - Commentary generation
- `commentary/generate_round_report.py` - Round report generation
- `commentary/generate_tournament_commentary_v2.py` - Tournament report generation
- `commentary/prompts.py` - AI prompt templates
- Other specialized commentary modules

**External:**
- `anthropic` - Claude API client
- `os.getenv()` - Environment variables (API keys)

**Streamlit Components:**
- `st.selectbox()` - TEG selection
- `st.multiselect()` - Round selection for batch
- `st.button()` - Generate button
- `st.spinner()` - Loading indicator
- `st.success()` - Success message
- `st.error()` - Error handling
- `st.expander()` - Advanced options
- `st.text_area()` - Manual prompt editing
- `st.progress()` - Progress bar for batch operations
- `st.markdown()` - Display generated text

### Embedded Logic

**Functions Defined:** Minimal (orchestration only)

**Analysis:** Well-extracted to commentary modules. Page is pure UI orchestration.

### User Interactions

**Widgets:**
- Selectbox: Choose TEG for report generation
- Multiselect: Choose specific rounds for batch generation
- Button: Generate reports
- Expander: Advanced options (custom prompts, model selection)
- Text area: Manual prompt editing
- Progress indicator during batch processing

**Session State:** Status tracking (generation in progress, success/error)

### Display Components

**Charts:** None

**Tables:** None

**Output:**
- Generated markdown reports
- Display in expandable sections
- Ready to save to files

**Layout:**
- TEG/Round selectors
- Generate button with progress
- Generated report display
- Advanced options expander

### CSS/Styling

- Standard Markdown rendering
- Status colors for success/error

### Migration Analysis

**Complexity:** Complex

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Consider adding report caching - future feature (1-2 hours)
3. Add cost tracking for API calls - future feature (1-2 hours)
4. Document prompt templates - 1-2 hours (documentation)

**Estimated Effort:** 2-4 hours (optional improvements)

**Blockers:** None critical

### Page-Specific Notes

- **IMPORTANT**: Uses external Claude API (requires API key)
- Expensive operation (API costs per report)
- Batch processing can take significant time
- Commentary generation quality depends on prompts
- Error handling critical for API failure scenarios
- Should implement rate limiting to control costs
- Generated reports become part of tournament history
- Good model for AI integration in Streamlit

---

## Page: `data_edit.py`

**Title:** Data Edit (Individual Score Editing)
**Lines of Code:** 291
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Interface for editing individual scores and data records with validation ensuring data integrity. Allows correcting mistakes, updating handicaps, or adjusting specific records. Admins visit to make targeted corrections to tournament data.

### Data Loading

- **Functions:**
  - `read_file()` - Reads data
  - `write_file()` - Writes changes
  - Validation functions
- **Files:** all-scores.parquet or specific tables
- **Key Parameters:** None (user selects record to edit)
- **Caching:** Cleared after edit

### Dependencies

**From utils.py:**
- `read_file()` - Data loader
- `write_file()` - Data saver
- `load_datawrapper_css()` - Table styling
- Cache control

**From helpers/data_update_processing.py:**
- Input validation functions
- Data formatting

**Streamlit Components:**
- `st.dataframe()` - Editable data table
- `st.data_editor()` - Built-in edit interface
- `st.button()` - Save/Cancel buttons
- `st.success()` / `st.error()` - Status messages
- `st.spinner()` - Save progress
- `st.selectbox()` - Record type selector

### Embedded Logic

**Functions Defined:** Validation logic (validation of edits)

**Analysis:** Validation logic should be extracted to helper

### User Interactions

**Widgets:**
- Selectbox: Choose record type (Scores, Handicaps, etc.)
- Data editor: In-place edit of records
- Button: Save changes
- Button: Cancel edits
- Validation feedback

**Session State:** Changed records tracking

### Display Components

**Charts:** None

**Tables:**
- Editable data table (st.data_editor)
- Shows selected record type
- Real-time edit capability

**Layout:**
- Record type selector
- Editable table
- Save/Cancel buttons
- Status feedback

### CSS/Styling

- `load_datawrapper_css()` - Table styling
- Standard Streamlit editor styling

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Add comprehensive validation - 1-2 hours
3. Add undo functionality - 2-3 hours (future feature)
4. Add audit logging - 1-2 hours (future feature)

**Estimated Effort:** 1-2 hours (validation improvements, optional)

**Blockers:** None

### Page-Specific Notes

- **CRITICAL**: Direct data editing capability
- Requires careful validation to prevent bad data
- Should have undo capability (not currently implemented)
- Audit logging important for compliance (track who changed what when)
- Used for correcting specific errors
- Less commonly used than data_update.py

---

## Page: `delete_data.py`

**Title:** Delete Data (Tournament Data Removal)
**Lines of Code:** 124
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Medium

### Purpose

Administrative interface for deleting tournament data (specific TEGs or rounds) with confirmation prompts to prevent accidental deletion. Updates GitHub repository after deletion. Admins visit to remove erroneous or duplicate tournament data.

### Data Loading

- **Functions:**
  - `read_file()` - Reads data
  - `write_file()` - Writes after deletion
  - Deletion filtering logic
- **Files:** all-scores.parquet, round_info.csv
- **Key Parameters:** TEG/Round selection for deletion
- **Caching:** Cleared after deletion (st.cache_data.clear())

### Dependencies

**From utils.py:**
- `read_file()` - Data loader
- `write_file()` - Data writer
- `load_datawrapper_css()` - Table styling
- GitHub integration
- Cache control

**From helpers/data_deletion_processing.py:**
- `get_teg_list_for_deletion()` - Available TEGs
- `get_round_list_for_deletion()` - Available rounds
- `preview_deletion_results()` - Shows what will be deleted
- `execute_deletion()` - Performs deletion
- `commit_deletion_to_github()` - GitHub ops

**Streamlit Components:**
- `st.selectbox()` - TEG/Round selection
- `st.dataframe()` - Preview of data to be deleted
- `st.button()` - Delete button
- `st.checkbox()` - Confirmation checkbox
- `st.warning()` - Warning message
- `st.error()` - Error display
- `st.success()` - Success feedback
- `st.rerun()` - Refresh after deletion
- `st.cache_data.clear()` - Cache clearing

### Embedded Logic

**Functions Defined:** Minimal (validation/confirmation only)

**Analysis:** All deletion logic extracted to data_deletion_processing helper.

### User Interactions

**Widgets:**
- Selectbox: Choose TEG or Round to delete
- Dataframe: Preview of data to be deleted
- Warning message explaining destructive action
- Checkbox: Confirm deletion intent
- Button: Execute deletion (only enables if confirmed)
- Status message after deletion

**Session State:** Confirmation state

### Display Components

**Charts:** None

**Tables:**
- Preview table showing records to be deleted
- Read-only display of affected data

**Layout:**
- Data type selector (TEG/Round)
- Deletion preview table
- Confirmation checkbox
- Delete button
- Status feedback

### CSS/Styling

- `load_datawrapper_css()` - Table styling
- Red alert styling for warning

### Migration Analysis

**Complexity:** Medium

**Migration Tasks:**
1. Already well-refactored (✅ complete)
2. Add audit logging for deletions - 1-2 hours (future feature)
3. Consider adding restore from backup - 2-3 hours (future feature)
4. Document deletion procedures - 1 hour

**Estimated Effort:** 1-2 hours (documentation + optional features)

**Blockers:** None

### Page-Specific Notes

- **DESTRUCTIVE OPERATION**: Irreversible by default
- Confirmation workflow prevents accidents
- Good error prevention design
- Should have audit trail (currently not implemented)
- Backup/restore capability would be valuable
- GitHub integration provides some version history
- Used rarely (only when data corruption occurs)

---

## Page: `admin_volume_management.py`

**Title:** Volume Management (System Diagnostics)
**Lines of Code:** 817
**Refactoring Status:** ✅ Fully Refactored
**Complexity:** Complex

### Purpose

Comprehensive admin dashboard showing system health including data volume statistics, cache status, file sizes, GitHub status, API usage, and other system diagnostics. Read-only dashboard for monitoring system health. Admins visit to check overall system status.

### Data Loading

- **Functions:**
  - Extensive file system operations
  - Cache inspection
  - GitHub API queries
  - File size calculations
- **Files:** All data files in system
- **Key Parameters:** None (inspection only, no writes)
- **Caching:** None (always fresh data)

### Dependencies

**From utils.py:**
- `get_base_directory()` - Base path
- `read_file()` - File operations
- Extensive utility functions (30+):
  - Data loading functions
  - Path operations
  - Cache functions
  - GitHub operations
  - Configuration access

**External:**
- `os.path` - File system operations
- `os.stat()` - File statistics
- `datetime` - Timestamp calculations
- `sys` - System information

**Streamlit Components:**
- `st.tabs()` - Multiple diagnostic views
- `st.metric()` - Display metrics (file sizes, counts, etc.)
- `st.expander()` - Collapsible detail sections
- `st.dataframe()` - Display data tables
- `st.json()` - Display JSON data
- `st.write()` - Display various data types
- `st.markdown()` - Display formatted text

### Embedded Logic

**Functions Defined:** Extensive diagnostic functions (~200+ lines)

**Functions:**
- `calculate_file_size()` - Gets file sizes
- `get_cache_status()` - Cache info
- `get_github_status()` - GitHub stats
- `calculate_data_volume()` - Total data volume
- `get_most_expensive_operations()` - Performance analysis
- Multiple diagnostic functions

**Analysis:**
- Total embedded logic: ~300+ lines
- Business logic: 80% (diagnostic calculations)
- UI orchestration: 20%
- Extraction recommendation: Extract diagnostic functions to admin_diagnostics helper

### User Interactions

**Widgets:**
- Tabs: Multiple diagnostic views
- Expanders: Collapsible detail sections
- No interactive inputs (read-only)
- Refresh via page reload

**Session State:** None (read-only)

### Display Components

**Charts:** None

**Tables:**
- Diagnostic data tables
- File listing tables
- Cache status tables
- GitHub metrics

**Metrics:**
- Data volume summary
- File counts
- Cache size
- Performance metrics

**Layout:**
- Tab-based organization
- Expanders for detailed sections
- Metrics display
- Summary tables

### CSS/Styling

- Standard Streamlit styling
- Custom metric colors

### Migration Analysis

**Complexity:** Complex

**Migration Tasks:**
1. Extract diagnostic functions to admin_diagnostics.py - 3-4 hours
2. Organize metrics by category - 1-2 hours
3. Add trend tracking (historical metrics) - 2-3 hours (future feature)
4. Create metrics export - 1-2 hours (future feature)
5. Add docstrings - 1-2 hours

**Estimated Effort:** 5-8 hours (optional improvements, no critical work)

**Blockers:** None

### Page-Specific Notes

- Largest page by line count (817 lines)
- Extensive diagnostic coverage
- Read-only (no data modification)
- Useful for system health monitoring
- Could benefit from helper extraction
- No critical bugs or issues
- Good model for admin dashboards
- Low priority for refactoring

---

## Section Summary

### Refactoring Status
- ✅ All 5 pages fully refactored and operational
- Critical admin functions well-implemented
- Good error handling and user feedback

### Page Categories

**Data Operations (Critical):**
- `1000Data update.py` - Data import and pipeline
- `delete_data.py` - Data removal
- `data_edit.py` - Targeted editing

**Report Generation (Extended):**
- `1001Report Generation.py` - AI commentary and reports

**System Management (Monitoring):**
- `admin_volume_management.py` - System diagnostics

### Key Findings

1. **Critical Operations**
   - Data update: Imports data, validates, commits to GitHub
   - Delete data: Removes data with confirmation
   - Report generation: Uses external Claude API (costs money)

2. **Safety Features**
   - Confirmation workflows (delete_data)
   - Validation pipeline (data_update)
   - Error handling and user feedback

3. **Integration Points**
   - Google Sheets API (data_update)
   - Claude API (report_generation) - requires API key
   - GitHub API (data_update, delete_data)

### Extraction Opportunities

1. **High Priority:**
   - Extract admin diagnostic functions from admin_volume_management.py - 3-4 hours
   - Extract validation from data_edit.py - 1-2 hours

2. **Medium Priority:**
   - Add audit logging to data operations - 2-3 hours (future feature)
   - Add cost tracking for Claude API - 1-2 hours (future feature)

3. **Low Priority:**
   - Documentation of procedures - 2-3 hours
   - Add backup/restore capability - 3-5 hours (future feature)

### Testing Priorities

1. **CRITICAL**:
   - `1000Data update.py`: Verify all validation rules work correctly
   - `delete_data.py`: Test confirmation workflow prevents accidents
   - `1001Report Generation.py`: Test API error handling

2. **Important**:
   - `data_edit.py`: Test data validation and undo
   - `admin_volume_management.py`: Verify all metrics calculated correctly

### Important Notes

**Security Considerations:**
- Google Sheets credentials required (data_update.py)
- Claude API key required (report_generation.py)
- GitHub credentials required (data_update.py, delete_data.py)
- All stored in environment variables (not hardcoded)

**Cost Considerations:**
- Claude API generates costs per report
- Should track and budget AI report generation
- Batch operations could be expensive

**Operational Procedures:**
- Data update process should run regularly
- Reports can be generated on-demand
- Deletions should be rare (data corruption only)
- Volume management should be checked periodically

**Missing Features** (could improve operations):
- Undo capability (data_edit, delete_data)
- Audit logging (all data operations)
- Backup/restore (system resilience)
- Cost tracking (API budget management)
- Rollback functionality (data_update)

### Total Effort to Refactor This Section
- Extract diagnostic functions: 3-4 hours
- Extract validation logic: 1-2 hours
- Add audit logging: 2-3 hours (future feature)
- Documentation: 2-3 hours
- Testing: 3-4 hours
- **Total: 11-19 hours (mostly optional improvements)**

### Notes
- This section is mission-critical for system operations
- All pages well-refactored and operational
- Good error handling already in place
- Main work would be optional improvements (audit logging, cost tracking)
- No critical bugs or issues
- Should prioritize thorough testing before any changes
- Consider implementing backup/restore for disaster recovery
