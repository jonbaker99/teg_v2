# Constant Migration Plan

**Purpose:** Document how constants will migrate during refactoring to prevent orphaned definitions
**Status:** Pre-Refactoring Phase 1.5
**Last Updated:** 2025-10-25

---

## Part 1: Critical Constants (Move First - Week 1)

### 1. BASE_DIR (utils.py:86)
**Type:** Path object
**Current Usage:** All file I/O operations
**Risk:** **CRITICAL** - Breaks all file operations if orphaned

**Used by Functions:**
- `_get_local_path()` - Line 447
- `read_file()` - Line 411
- `write_file()` - Line 430
- `backup_file()` - Line 460
- All GitHub operations (12+ functions)

**Import Chain:**
```
BASE_DIR (utils.py:86)
  ├─ Direct reference in all I/O functions
  ├─ Passed as argument to helper functions
  └─ Cannot be removed from utils.py imports
```

**Migration Plan:**
1. Create `teg_analysis/config/paths.py`
2. Move `BASE_DIR` definition to new module
3. Update `utils.py` to import: `from teg_analysis.config.paths import BASE_DIR`
4. Update all internal references in utils.py
5. Test: `pytest tests/test_data_loading.py -v`

**Backward Compatibility:** MAINTAIN (re-export from utils.py for 1 release)

---

### 2. GitHub Configuration (GITHUB_REPO, GITHUB_BRANCH)
**Type:** String constants
**Location:** utils.py:82, 135
**Risk:** **HIGH** - Breaks all GitHub I/O

**Used by Functions:**
- `read_from_github()` - Line 137
- `write_to_github()` - Line 180
- `batch_commit_to_github()` - Line 200
- `read_text_from_github()` - Line 172
- `write_text_to_github()` - Line 195

**Migration Plan:**
1. Create `teg_analysis/config/github.py`
2. Move both constants together
3. Test GitHub operations: `pytest tests/test_imports.py::TestExternalDependencies -v`

---

### 3. Data File Path Constants (ALL_SCORES_PARQUET, etc.)
**Type:** String paths
**Location:** utils.py:91-103 (13 constants total)
**Risk:** **HIGH** - 12+ references each

**Critical Constants:**
```python
ALL_DATA_PARQUET = "data/all-data.parquet"          # Line 91
ALL_SCORES_PARQUET = "data/all-scores.parquet"      # Line 92 (MOST USED)
STREAKS_PARQUET = "data/streaks.parquet"            # Line 93
BESTBALL_PARQUET = "data/bestball.parquet"          # Line 94
HANDICAPS_CSV = "data/handicaps.csv"                # Line 95
ROUND_INFO_CSV = "data/round_info.csv"              # Line 96
COMMENTARY_ROUND_EVENTS_PARQUET = "..."             # Line 99
COMMENTARY_ROUND_SUMMARY_PARQUET = "..."            # Line 100
COMMENTARY_TOURNAMENT_SUMMARY_PARQUET = "..."       # Line 101
COMMENTARY_ROUND_STREAKS_PARQUET = "..."            # Line 102
COMMENTARY_TOURNAMENT_STREAKS_PARQUET = "..."       # Line 103
```

**Used by Functions:**
- `load_all_data()` - 4+ references
- `load_and_prepare_handicap_data()` - 1 reference
- Data backup functions - 3+ references
- Commentary functions - 5+ references

**Migration Plan:**
1. Consolidate all into `teg_analysis/config/paths.py`
2. Organize by category (data, commentary, backup)
3. Document each path's purpose
4. Test: `pytest tests/test_data_loading.py::TestLoadAllData -v`

---

## Part 2: Domain Data Constants (Move Week 1-2)

### 4. PLAYER_DICT
**Type:** Dictionary mapping player codes to names
**Location:** utils.py:737
**Risk:** **HIGH** - Display functions will show errors if orphaned

**Current Definition:**
```python
PLAYER_DICT = {
    'AB': 'Alice Brown',
    'CD': 'Charlie Davis',
    'EF': 'Eve Foster',
    # ... 30+ entries
}
```

**Used by Functions (8+ total):**
- `format_player_name()` - Lookup
- All player display functions - Rendering
- Leaderboard generation - Display
- Results pages - Display
- Export functions - Data

**Migration Plan:**
1. Create `teg_analysis/data/players.py`
2. Move dict as-is (no transformation needed)
3. Export from new location
4. Update utils.py to import: `from teg_analysis.data.players import PLAYER_DICT`
5. Test: `pytest tests/test_helpers.py -v`

**Verification:**
```bash
# After migration, verify:
python -c "from teg_analysis.data.players import PLAYER_DICT; print(len(PLAYER_DICT))"
# Should output: 32 (or current count)
```

---

### 5. Tournament Structure Constants
**Type:** Dictionary mappings
**Location:** utils.py:749-761
**Risk:** **MEDIUM** - Analysis breaks if orphaned

**Constants:**
```python
TEG_ROUNDS = {1: 4, 2: 4, 3: 4, ...}              # Which TEGs have how many rounds
TEGNUM_ROUNDS = {1: 4, 2: 4, ...}                 # Alternative mapping
TEG_OVERRIDES = {50: 3, ...}                      # Special cases
```

**Used by:**
- Tournament validation functions
- Round enumeration
- Data processing

**Migration Plan:**
1. Create `teg_analysis/config/rules.py`
2. Move all tournament structure constants together
3. Add documentation explaining each

---

## Part 3: UI/Display Constants (Move Week 2-3)

### 6. Trophy Name Lookups
**Type:** Dictionary mappings
**Location:** utils.py:3591-3598
**Risk:** **LOW** - Only affects trophy display formatting

**Migration Plan:**
1. Create `teg_analysis/display/trophies.py`
2. Move both `TROPHY_NAME_LOOKUPS_SHORTLONG` and `TROPHY_NAME_LOOKUPS_LONGSHORT`
3. Keep together as they're interdependent

---

### 7. Scattered UI Constants (Low Risk)
**Type:** Colors, fonts, dimensions, spacing
**Location:** Various page files
**Risk:** **LOW** - Affects only UI rendering

**Migration Plan:**
1. Consolidate into `teg_analysis/display/constants.py`
2. Organize by category:
   - `COLOR_*` → `teg_analysis/display/colors.py`
   - `FONT_*` → `teg_analysis/display/typography.py`
   - `LAYOUT_*` → `teg_analysis/display/layout.py`
3. Create imports for convenience

---

## Part 4: Duplicate Consolidation (Week 3-4)

### Identified Duplicates to Consolidate

| Constant Name | Files | Action | Target |
|---|---|---|---|
| `PAGE_TITLE` | 3 files | Consolidate | Create centralized config |
| `PAGE_LAYOUT` | 2 files | Consolidate | `teg_analysis/display/layout.py` |
| `CSS_PATH` | 4 files | Consolidate | `teg_analysis/display/styles.py` |
| `CHART_HEIGHT` | 2 files | Consolidate | `teg_analysis/display/charts.py` |
| `CHART_WIDTH` | 2 files | Consolidate | `teg_analysis/display/charts.py` |
| `COLOR_*` | 5+ files | Consolidate | `teg_analysis/display/colors.py` |
| `FONT_SIZE_*` | 3 files | Consolidate | `teg_analysis/display/typography.py` |

---

## Part 5: Migration Dependency Order

### Dependency Graph
```
┌─────────────────────────────────────────┐
│  Step 1: Foundation (NO DEPENDENCIES)   │
│  ├─ BASE_DIR                            │
│  ├─ PLAYER_DICT                         │
│  ├─ TOTAL_HOLES                         │
│  └─ All path constants                  │
└──────────┬──────────────────────────────┘
           │
┌──────────▼──────────────────────────────┐
│  Step 2: GitHub Configuration            │
│  ├─ GITHUB_REPO                         │
│  └─ GITHUB_BRANCH                       │
└──────────┬──────────────────────────────┘
           │
┌──────────▼──────────────────────────────┐
│  Step 3: Tournament Rules                │
│  ├─ TEG_ROUNDS (uses PLAYER_DICT)       │
│  ├─ TEGNUM_ROUNDS                       │
│  └─ TEG_OVERRIDES                       │
└──────────┬──────────────────────────────┘
           │
┌──────────▼──────────────────────────────┐
│  Step 4: UI Constants                    │
│  ├─ Trophy lookups                      │
│  ├─ Colors & fonts                      │
│  ├─ Layout dimensions                   │
│  └─ CSS paths                           │
└─────────────────────────────────────────┘
```

---

## Part 6: Refactoring Timeline

### Week 1: Critical Infrastructure
- [ ] Monday: Create config modules, move BASE_DIR
- [ ] Tuesday: Move GitHub config, test all I/O
- [ ] Wednesday: Move data path constants
- [ ] Thursday-Friday: Move PLAYER_DICT, verify display functions

### Week 2: Domain Logic
- [ ] Move tournament structure constants
- [ ] Move trophy lookups
- [ ] Consolidate UI constants (colors, fonts)
- [ ] Run full test suite

### Week 3: Display Layer
- [ ] Consolidate layout constants
- [ ] Consolidate CSS paths
- [ ] Test all pages render correctly
- [ ] Verify no visual changes

### Week 4: Validation & Cleanup
- [ ] Run comprehensive test suite
- [ ] Verify all imports resolve
- [ ] Check for any orphaned constants
- [ ] Performance validation
- [ ] Production readiness

---

## Part 7: Testing & Verification

### Phase 1: Import Verification
```bash
# After moving each constant, test import
python -c "from teg_analysis.config.paths import BASE_DIR; print(BASE_DIR)"
python -c "from teg_analysis.config.github import GITHUB_REPO; print(GITHUB_REPO)"
python -c "from teg_analysis.data.players import PLAYER_DICT; print(len(PLAYER_DICT))"
```

### Phase 2: Function Verification
```bash
# Run tests for functions that use the constant
pytest tests/test_data_loading.py -v              # Tests BASE_DIR usage
pytest tests/test_imports.py -v                   # Tests all imports
pytest tests/test_helpers.py -v                   # Tests PLAYER_DICT usage
```

### Phase 3: Page Verification
```bash
# Run actual pages to verify display works
streamlit run streamlit/nav.py                    # Main navigation
streamlit run "streamlit/101TEG History.py"       # Test player names (PLAYER_DICT)
streamlit run "streamlit/300TEG Records.py"       # Test trophy names
```

### Phase 4: Regression Testing
```bash
# Full test suite
pytest tests/ -v

# Coverage report
pytest tests/ --cov=streamlit --cov-report=term
```

---

## Part 8: Fallback Procedures

### If Migration Breaks Something

1. **Identify the Problem**
   ```bash
   # Check which import failed
   python -c "from teg_analysis.config.paths import BASE_DIR"
   # or
   streamlit run streamlit/nav.py 2>&1 | head -20
   ```

2. **Rollback Immediately**
   ```bash
   # Return to last good commit
   git revert <failed-commit>
   ```

3. **Analyze & Fix**
   - Review import path
   - Check for missing __init__.py files
   - Verify circular dependencies

4. **Retry with Fix**
   - Apply fix
   - Test in isolation
   - Re-run full test suite

---

## Part 9: Backward Compatibility

### During Transition (Release N)
**Keep re-exports in utils.py:**
```python
# utils.py - Backward compatibility
from teg_analysis.config.paths import BASE_DIR, ALL_SCORES_PARQUET
from teg_analysis.config.github import GITHUB_REPO, GITHUB_BRANCH
from teg_analysis.data.players import PLAYER_DICT
```

### After Transition (Release N+1)
- Remove re-exports from utils.py
- Force all imports to use new locations
- Document migration in release notes

---

## Success Criteria

✅ All 117 constants mapped
✅ 15+ critical constants documented with usage
✅ Migration order determined (no circular dependencies)
✅ Target modules identified
✅ Test plan created
✅ Rollback procedure documented
✅ Backward compatibility approach defined

---

**Next Step:** Subtask 1.5.3 - Update migration_impact.md with this information
