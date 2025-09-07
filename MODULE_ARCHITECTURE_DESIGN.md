# Module Architecture Design

## Refined Module Structure (Based on Analysis)

### Module 1: `utils_core_io.py` 
**Purpose**: Environment-aware file operations
**Risk Level**: 🟡 MEDIUM (Used by helpers, but clear boundaries)

**Functions** (6 total):
- `read_file()` - Used in 2+ files 
- `write_file()` - Used in helpers
- `backup_file()` - Used in helpers  
- `read_from_github()` - Internal to read_file
- `write_to_github()` - Internal to write_file
- `save_to_parquet()` - Used internally

**Dependencies**: 
- External: github, pandas, streamlit
- Internal: get_base_directory (from utils_helper_utilities)

**Import Pattern**: Often imported individually or with clear_all_caches

---

### Module 2: `utils_helper_utilities.py`
**Purpose**: Simple utility functions with minimal dependencies  
**Risk Level**: 🟢 LOW (Safe to move first)

**Functions** (8 total):
- `get_base_directory()` - Used by 2+ files
- `get_current_branch()` - Used internally
- `get_player_name()` - Pure utility function
- `get_teg_rounds()` / `get_tegnum_rounds()` - Used by 3+ files
- `convert_trophy_name()` / `get_trophy_full_name()` - Used by 2+ files
- `list_fields_by_aggregation_level()` - Used by 2+ files

**Dependencies**:
- External: pandas, pathlib, subprocess
- Internal: None (self-contained)

**Import Pattern**: Usually imported individually

---

### Module 3: `utils_data_input.py`
**Purpose**: External data loading (Google Sheets, handicaps)
**Risk Level**: 🟡 MEDIUM (Used by data update workflow)

**Functions** (2 total):
- `get_google_sheet()` - Used by data update
- `load_and_prepare_handicap_data()` - Cached, used by processing

**Dependencies**:
- External: gspread, google-auth
- Internal: read_file (from utils_core_io)

**Import Pattern**: Used in data update workflows

---

### Module 4: `utils_data_processing.py` 
**Purpose**: Pre-parquet data transformation
**Risk Level**: 🔴 HIGH (Complex processing pipeline)

**Functions** (7 total):
- `process_round_for_all_scores()` - Core scoring engine
- `add_cumulative_scores()` - Complex calculations
- `reshape_round_data()` - Data transformation
- `add_round_info()` - Data enrichment
- `summarise_existing_rd_data()` - Used by updates
- `check_hc_strokes_combinations()` - Validation
- `aggregate_data()` - Core aggregation function

**Dependencies**:
- External: pandas, numpy
- Internal: get_player_name (from utils_helper_utilities), read_file (from utils_core_io)

**Import Pattern**: Used in data processing workflows

---

### Module 5: `utils_data_retrieval.py`
**Purpose**: Post-parquet cached data loading
**Risk Level**: 🔴 HIGHEST (Most critical caching functions)

**Functions** (13 total):
- `load_all_data()` - **MOST CRITICAL** (16+ files, TTL cache)
- `exclude_incomplete_tegs_function()` - Used with load_all_data
- `get_complete_teg_data()` - Cached, 7+ files
- `get_teg_data_inc_in_progress()` - Cached variant
- `get_round_data()` - Cached, 8+ files
- `get_9_data()` - Cached, 2+ files  
- `get_Pl_data()` - Cached, player data
- `get_ranked_teg_data()` - Cached, 7+ files
- `get_ranked_round_data()` - Cached, 7+ files
- `get_ranked_frontback_data()` - Cached, 2+ files
- `get_scorecard_data()` - Cached, 4+ files
- `get_teg_metadata()` - Cached, 4+ files
- `load_course_info()` - Cached, 1+ files

**Dependencies**:
- External: pandas, streamlit (for caching)
- Internal: aggregate_data (from utils_data_processing), add_ranks (from utils_statistical_analysis)

**Import Pattern**: Often imported in groups by analysis type

---

### Module 6: `utils_statistical_analysis.py`
**Purpose**: Post-parquet performance analysis  
**Risk Level**: 🟡 MEDIUM (Complex but well-defined)

**Functions** (10 total):
- `add_ranks()` - Used by ranked data functions
- `get_best()` / `get_worst()` - Used by 4+ files
- `get_teg_winners()` - Used by 2+ files
- `chosen_rd_context()` / `chosen_teg_context()` - Used by 2+ files each
- `define_score_types()` / `apply_score_types()` - Score categorization
- `score_type_stats()` - Used by 3+ files
- `max_scoretype_per_round()` - Used by 3+ files

**Dependencies**:
- External: pandas
- Internal: load_all_data (from utils_data_retrieval), ordinal (from utils_display_formatting)

**Import Pattern**: Often imported in groups for analysis

---

### Module 7: `utils_display_formatting.py`
**Purpose**: HTML generation and value formatting
**Risk Level**: 🟡 MEDIUM (Widely used but stable functions)

**Functions** (8 total):
- `load_datawrapper_css()` - **MOST USED** (22+ files)
- `datawrapper_table()` - Used with CSS, 4+ files
- `create_stat_section()` - Used by 2+ files
- `format_vs_par()` - Used by 2+ files
- `format_date_for_scorecard()` - Used by 4+ files
- `ordinal()` / `safe_ordinal()` - Used by formatting functions
- `load_css_file()` - Used internally

**Dependencies**:
- External: streamlit
- Internal: get_base_directory (from utils_helper_utilities)

**Import Pattern**: load_datawrapper_css imported almost everywhere

---

### Module 8: `utils_data_management.py`
**Purpose**: Data updates, validation, and system operations
**Risk Level**: 🟡 MEDIUM (Administrative functions)

**Functions** (3 total):
- `update_all_data()` - Data update workflow
- `check_for_complete_and_duplicate_data()` - Data validation
- `clear_all_caches()` - System operation

**Dependencies**:
- External: streamlit
- Internal: Multiple modules for data operations

**Import Pattern**: Used by administrative/update workflows

## Migration Sequence (Risk-Based)

### Batch 1: LOWEST RISK 🟢
**Module**: `utils_helper_utilities.py`
- Self-contained functions
- No complex dependencies
- Easy to test individually

### Batch 2: LOW-MEDIUM RISK 🟡
**Modules**: `utils_core_io.py`, `utils_display_formatting.py`
- Clear function boundaries
- Well-defined dependencies
- Load_datawrapper_css is stable despite high usage

### Batch 3: MEDIUM RISK 🟡  
**Modules**: `utils_data_input.py`, `utils_data_management.py`
- Used by specific workflows
- Limited cross-dependencies

### Batch 4: HIGH RISK 🔴
**Module**: `utils_data_processing.py`
- Complex data transformations
- Internal dependencies

### Batch 5: HIGHEST RISK 🔴
**Modules**: `utils_data_retrieval.py`, `utils_statistical_analysis.py` 
- Critical cached functions
- Complex interdependencies
- load_all_data() requires extreme care

## Dependency Resolution Strategy

### Cross-Module Dependencies
1. **utils_data_retrieval** → **utils_statistical_analysis** (add_ranks)
2. **utils_data_retrieval** → **utils_data_processing** (aggregate_data)  
3. **utils_statistical_analysis** → **utils_display_formatting** (ordinal)
4. **All modules** → **utils_helper_utilities** (get_base_directory, get_player_name)

### Resolution Approach
- Import specific functions rather than entire modules
- Use delayed imports where needed to prevent circular dependencies
- Keep interdependent functions in same module where possible

## API Compatibility Design

### Main utils.py Structure
```python
# Re-export all functions to maintain compatibility
from utils_helper_utilities import *
from utils_core_io import *
from utils_data_input import *
from utils_data_processing import *
from utils_data_retrieval import *
from utils_statistical_analysis import *
from utils_display_formatting import *
from utils_data_management import *

# Keep constants in main utils.py
ALL_DATA_PARQUET = "data/all-data.parquet"
# ... other constants
```

### Import Compatibility
- All existing `from utils import ...` statements work unchanged
- Functions maintain exact signatures and behavior  
- Caching decorators preserved exactly
- Constants remain accessible

## Module Creation Strategy

### Step-by-Step Process
1. Create new module file
2. Copy functions with exact signatures
3. Update internal imports only
4. Test module imports in isolation
5. Update main utils.py to re-export
6. Run smoke tests
7. Verify no behavior changes

### Validation Steps
- Run smoke test after each module
- Check that cached functions still cache properly
- Verify import statements still work
- Test representative pages load correctly