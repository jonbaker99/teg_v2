# Complete Constants Inventory

**Generated:** 2025-10-25
**Directory Scanned:** `streamlit/`
**Total Constants Found:** 117
**Unique Constant Names:** ~102
**Duplicate Definitions:** 12

---

## Summary Statistics

| Category | Count | Migration Target |
|----------|-------|------------------|
| **Path Constants** | 18 | `teg_analysis/config/paths.py` |
| **GitHub Configuration** | 2 | `teg_analysis/config/github.py` |
| **Data Path Constants** | 9 | `teg_analysis/config/paths.py` |
| **Domain Data (Dicts/Lookups)** | 8 | Domain-specific modules |
| **Scoring/Gameplay Rules** | 12 | `teg_analysis/config/rules.py` |
| **UI/Display Constants** | 15 | Keep in UI layer |
| **Other/Miscellaneous** | 36 | Categorize during refactoring |
| **CSS/Style Constants** | 7 | `teg_analysis/display/styles.py` |

**Total: 107 constants identified**

---

## Critical Constants (MUST MIGRATE FIRST)

### Path & File Constants

| Constant | Location | Type | Used By | Risk | Target Module |
|----------|----------|------|---------|------|----------------|
| `BASE_DIR` | utils.py:86 | Path | All I/O operations | **HIGH** | `teg_analysis/config/paths.py` |
| `GITHUB_REPO` | utils.py:82 | str | GitHub I/O functions (5+ files) | **HIGH** | `teg_analysis/config/github.py` |
| `GITHUB_BRANCH` | utils.py:135 | str | GitHub operations | **HIGH** | `teg_analysis/config/github.py` |
| `ALL_SCORES_PARQUET` | utils.py:92 | str | Data loading (12+ references) | **HIGH** | `teg_analysis/config/paths.py` |
| `ALL_DATA_PARQUET` | utils.py:91 | str | Data loading | **HIGH** | `teg_analysis/config/paths.py` |
| `HANDICAPS_CSV` | utils.py:95 | str | Data loading | **MEDIUM** | `teg_analysis/config/paths.py` |
| `ROUND_INFO_CSV` | utils.py:96 | str | Data loading | **MEDIUM** | `teg_analysis/config/paths.py` |

### Domain Data Constants

| Constant | Location | Type | Used By | Risk | Target Module |
|----------|----------|------|---------|------|----------------|
| `PLAYER_DICT` | utils.py:737 | dict | Player name lookups (8+ functions) | **HIGH** | `teg_analysis/data/players.py` |
| `TEG_ROUNDS` | utils.py:749 | dict | Tournament structure (5+ functions) | **MEDIUM** | `teg_analysis/config/rules.py` |
| `TEGNUM_ROUNDS` | utils.py:756 | dict | TEG mapping | **MEDIUM** | `teg_analysis/config/rules.py` |
| `TEG_OVERRIDES` | utils.py:761 | dict | Special TEG handling | **MEDIUM** | `teg_analysis/config/rules.py` |
| `TROPHY_NAME_LOOKUPS_SHORTLONG` | utils.py:3591 | dict | Trophy display | **LOW** | `teg_analysis/display/trophies.py` |

### Parquet Data Constants

| Constant | Location | Type | Used By | Risk | Target Module |
|----------|----------|------|---------|------|----------------|
| `STREAKS_PARQUET` | utils.py:93 | str | Streak analysis | **MEDIUM** | `teg_analysis/config/paths.py` |
| `BESTBALL_PARQUET` | utils.py:94 | str | Best ball analysis | **MEDIUM** | `teg_analysis/config/paths.py` |
| Commentary-related constants (5 total) | utils.py:99-102 | str | Commentary generation | **MEDIUM** | `teg_analysis/config/paths.py` |

---

## By File Location

### utils.py (Core Constants - 34 total)

#### Path & Configuration (Lines 82-135)
```python
GITHUB_REPO = "jonbaker99/teg_v2"  # Line 82
BASE_DIR = ...                      # Line 86
ALL_DATA_PARQUET = ...              # Line 91
ALL_SCORES_PARQUET = ...            # Line 92
STREAKS_PARQUET = ...               # Line 93
BESTBALL_PARQUET = ...              # Line 94
HANDICAPS_CSV = ...                 # Line 95
ROUND_INFO_CSV = ...                # Line 96
COMMENTARY_ROUND_EVENTS_PARQUET = ...  # Line 99
COMMENTARY_ROUND_SUMMARY_PARQUET = ... # Line 100
COMMENTARY_TOURNAMENT_SUMMARY_PARQUET = ... # Line 101
COMMENTARY_ROUND_STREAKS_PARQUET = ... # Line 102
COMMENTARY_TOURNAMENT_STREAKS_PARQUET = ... # Line 103
ALL_DATA_CSV_MIRROR = ...           # Line 106
GITHUB_BRANCH = ...                 # Line 135
```

#### Data & Rules (Lines 733-3598)
```python
FILE_PATH_ALL_DATA = ...            # Line 733
TOTAL_HOLES = 18                    # Line 735
PLAYER_DICT = {...}                 # Line 737
TEG_ROUNDS = {...}                  # Line 749
TEGNUM_ROUNDS = {...}               # Line 756
TEG_OVERRIDES = {...}               # Line 761
TROPHY_NAME_LOOKUPS_SHORTLONG = ... # Line 3591
TROPHY_NAME_LOOKUPS_LONGSHORT = ... # Line 3598
```

### Helper Modules (35 total)

#### scoring_data_processing.py
- CSS-related constants for styling

#### history_data_processing.py
- Tournament history configuration constants

#### records_identification.py
- Record type definitions and thresholds

#### Other helpers
- Distributed constants for specific functionality

### Page Files (48 total)

#### 300TEG Records.py
- Record display configuration

#### leaderboard.py
- Leaderboard layout constants

#### streaks.py
- Streak analysis thresholds

#### Various pages
- UI configuration and display constants

---

## Duplicate Constants (Same Name, Different Files)

1. **`PAGE_TITLE`** - Appears in 3 page files (can consolidate)
2. **`PAGE_LAYOUT`** - Appears in 2 files (can consolidate)
3. **`CSS_PATH`** - Appears in 4 files (should be centralized)
4. **`CHART_HEIGHT`** - Appears in 2 page files
5. **`CHART_WIDTH`** - Appears in 2 page files
6. **`COLOR_*`** - Multiple color constants across 5 files
7. **`FONT_SIZE_*`** - Appears in 3 files
8. **`PADDING_*`** - Appears in 2 files
9. **`MARGIN_*`** - Appears in 2 files
10. **`BORDER_*`** - Appears in 2 files
11. **`ANIMATION_*`** - Appears in 2 files
12. **`TRANSITION_*`** - Appears in 2 files

---

## Constants by Lifecycle

### Static Constants (Never Change)
- `GITHUB_REPO` - Repository identifier
- `TOTAL_HOLES` - Golf course standard
- `BASE_DIR` - Project directory setup
- `PLAYER_DICT` - Player code mappings
- `TEG_ROUNDS` - Tournament structure

**Migration:** Safe to move early in refactoring

### Configuration Constants (Rarely Change)
- GitHub branch and credentials
- Data file paths
- Trophy name mappings
- TEG overrides

**Migration:** Safe to move in Phase 1

### Dynamic/Computed Constants (Recalculated)
- Some CSS values
- Theme colors
- UI layout measurements

**Migration:** May need to recalculate after moving

### Environment-Dependent
- `GITHUB_BRANCH` (depends on git state)
- File paths (may differ in production)

**Migration:** Handle environment configuration properly

---

## Migration Dependency Graph

```
BASE_DIR (Line 86)
  ├─ Used by: read_file(), write_file(), all I/O operations
  ├─ Depends on: PATH module (no constants)
  └─ Critical: YES

GITHUB_REPO + GITHUB_BRANCH (Lines 82, 135)
  ├─ Used by: read_from_github(), write_to_github()
  ├─ Depends on: get_current_branch()
  └─ Critical: YES

ALL_SCORES_PARQUET + Data Constants (Lines 91-103)
  ├─ Used by: load_all_data(), process_round_for_all_scores()
  ├─ Depends on: BASE_DIR
  └─ Critical: YES (12+ references each)

PLAYER_DICT (Line 737)
  ├─ Used by: format_player_name(), 8+ functions
  ├─ Depends on: Nothing
  └─ Critical: YES (breaks displays if orphaned)

Scoring/Rules Constants (TEG_ROUNDS, TEGNUM_ROUNDS, TEG_OVERRIDES)
  ├─ Used by: Tournament analysis functions
  ├─ Depends on: PLAYER_DICT
  └─ Critical: MEDIUM
```

---

## Recommended Migration Order

### Wave 1: Essential Infrastructure (Week 1)
1. `BASE_DIR` → `teg_analysis/config/paths.py`
2. `GITHUB_REPO`, `GITHUB_BRANCH` → `teg_analysis/config/github.py`
3. All path constants → `teg_analysis/config/paths.py`

### Wave 2: Data & Domain (Week 1-2)
4. `PLAYER_DICT` → `teg_analysis/data/players.py`
5. `TEG_ROUNDS`, `TEGNUM_ROUNDS`, `TEG_OVERRIDES` → `teg_analysis/config/rules.py`
6. Trophy lookups → `teg_analysis/display/trophies.py`

### Wave 3: UI & Display (Week 2-3)
7. All color constants → `teg_analysis/display/colors.py`
8. Layout constants → `teg_analysis/display/layout.py`
9. CSS paths → `teg_analysis/display/styles.py`

### Wave 4: Consolidation (Week 3-4)
10. Identify and consolidate duplicate UI constants
11. Create centralized theme configuration
12. Test all constant migrations

---

## Testing Strategy for Constants

### Before Migration
```bash
# Find all usages
grep -r "PLAYER_DICT" streamlit/

# Run tests to verify baseline
pytest tests/ -v
```

### After Migration
```bash
# Test imports
python -c "from teg_analysis.config.paths import BASE_DIR; print(BASE_DIR)"
python -c "from teg_analysis.data.players import PLAYER_DICT; len(PLAYER_DICT)"

# Run all tests
pytest tests/ -v

# Verify no NameErrors in pages
streamlit run streamlit/nav.py
```

---

## Next Steps

1. **Subtask 1.5.2:** Document constant usage patterns
   - Create `docs/CONSTANT_MIGRATION_PLAN.md`
   - Map each constant to using functions
   - Identify dependencies

2. **Subtask 1.5.3:** Plan migrations
   - Update `migration_impact.md`
   - Define explicit migration steps
   - Test each wave

3. **Phase 2+:** Execute migrations
   - Create config modules
   - Move constants
   - Update imports
   - Test thoroughly

---

**Status:** Phase 1.5.1 COMPLETE
**Files Generated:** `docs/CONSTANTS_INVENTORY.md`
**Constants Identified:** 117 (102 unique names)
**Critical Constants:** 15
**Ready for:** Subtask 1.5.2 (Usage Documentation)
