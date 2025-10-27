# Migration Impact Analysis - Detailed Migration Plans

**Document Purpose:** Provide detailed migration strategies for each planned refactoring task
**Scope:** All utils and helper modules, phased migration approach
**Risk Level:** Low-to-Medium (depends on phase)

---

## Table of Contents

1. [Phase 1: I/O Functions (CRITICAL)](#phase-1-io-functions-critical)
2. [Phase 2: Data Loading (CRITICAL)](#phase-2-data-loading-critical)
3. [Phase 3: Pure Helpers (LOW RISK)](#phase-3-pure-helpers-low-risk)
4. [Phase 4: Mixed Modules (MEDIUM RISK)](#phase-4-mixed-modules-medium-risk)
5. [Phase 5: Analysis Functions](#phase-5-analysis-functions)
6. [Phase 6: UI Functions (NO MIGRATION)](#phase-6-ui-functions-no-migration)
7. [Testing Strategy](#testing-strategy)
8. [Rollback Plan](#rollback-plan)

---

## Phase 1: I/O Functions (CRITICAL)

### Migration Target

```
Current: streamlit/utils.py
New: teg_analysis/io/file_operations.py
New: teg_analysis/io/__init__.py
```

### Functions to Migrate

#### Helper Functions (Private)
- `_is_railway()` - Check if running on Railway
- `_get_volume_path()` - Get Railway volume path
- `_get_local_path()` - Get local file path
- `_ensure_volume_dir()` - Create directory if needed

#### Public Functions
- `read_file(file_path: str) -> pd.DataFrame` - Read CSV/Parquet (environment-aware)
- `write_file(df: pd.DataFrame, file_path: str)` - Write CSV/Parquet (with cache clear)
- `read_text_file(file_path: str) -> str` - Read text files
- `write_text_file(content: str, file_path: str)` - Write text files
- `backup_file(file_path: str)` - Create backup

#### Functions to Keep in utils.py (depends on GitHub API)
- `read_from_github()` - Direct GitHub access
- `write_to_github()` - Direct GitHub write
- `batch_commit_to_github()` - Batch operations
- `read_text_from_github()` - Text from GitHub
- `write_text_to_github()` - Text to GitHub

### Dependencies to Manage

```python
# New module needs:
import os
import pandas as pd
from pathlib import Path
from typing import Optional

# Optional: from utils import (these will be removed as circular dep)
# Will break: read_from_github, write_to_github calls
# Solution: Keep GitHub functions in utils.py, call from there
```

### Files Requiring Import Updates: 22

```
Updated imports in:
  100s (History): 101TEG History.py, 102TEG Results.py (2)
  200s (Records): 300TEG Records.py, 301Best_TEGs_and_Rounds.py, 302Personal Best Rounds & TEGs.py (3)
  300s (Scoring): 400scoring.py, 500Handicaps.py, streaks.py, ave_by_par.py, ave_by_teg.py, ave_by_course.py (6)
  400s (Records): birdies_etc.py, score_by_course.py, score_matrix.py, biggest_changes.py, score_heatmaps.py, sc_count.py (6)
  500s (Latest): leaderboard.py, latest_round.py, latest_teg_context.py, 101TEG Honours Board.py (4)
  600s (Scorecard): scorecard_v2.py, bestball.py, eclectic.py, best_eclectics.py (4)
  700s (Admin): 1000Data update.py, 1001Report Generation.py, delete_data.py, admin_volume_management.py, data_edit.py (5)
```

### Migration Steps

```
Step 1: Create module structure
  - Create teg_analysis/
  - Create teg_analysis/io/
  - Create teg_analysis/io/file_operations.py
  - Create teg_analysis/io/__init__.py

Step 2: Copy functions
  - Copy _is_railway() function
  - Copy _get_volume_path() function
  - Copy _get_local_path() function
  - Copy _ensure_volume_dir() function
  - Copy read_file() function
  - Copy write_file() function
  - Copy read_text_file() function
  - Copy write_text_file() function
  - Copy backup_file() function

Step 3: Update imports in new module
  - Change any utils. imports to teg_analysis.
  - Remove any streamlit imports (if read_file uses st.cache)

Step 4: Test new module independently
  - Test read_file with local CSV
  - Test read_file with local Parquet
  - Test read_text_file
  - Test write operations with cache clearing
  - Test on Railway environment

Step 5: Update all 22 files
  OLD: from utils import read_file, write_file
  NEW: from teg_analysis.io import read_file, write_file

Step 6: Ensure backward compatibility
  - Keep re-exports in utils.py for 1 version
  - Add deprecation warnings
  - Gradually migrate remaining code

Step 7: Full system testing
  - Run all pages
  - Test data updates
  - Test data deletion
  - Monitor cache behavior
```

### Risk Assessment

| Risk | Level | Mitigation |
|------|-------|-----------|
| Cache behavior changes | Medium | Test @st.cache behavior in new module |
| Railway volume path issues | Medium | Test thoroughly on Railway environment |
| Circular import (GitHub functions) | Low | Keep GitHub functions in utils.py |
| File I/O breaking | Low | High test coverage before migration |
| Environment detection fails | Low | Add fallback logic and logging |

### Estimated Time

- **Implementation:** 2 hours
- **Testing:** 2 hours
- **Documentation:** 1 hour
- **Total:** 5 hours

---

## Phase 2: Data Loading (CRITICAL)

### Migration Target

```
Current: streamlit/utils.py (6 functions)
New: teg_analysis/core/data_loader.py
New: teg_analysis/core/__init__.py
```

### Functions to Migrate

#### Core Data Loading
- `load_all_data()` - Main data loading function (with caching)
- `process_round_for_all_scores()` - Transform raw data
- `add_cumulative_scores()` - Add cumulative columns
- `add_rankings_and_gaps()` - Add ranking columns
- `get_number_of_completed_rounds_by_teg()` - Count rounds
- `get_incomplete_tegs()` - Filter incomplete
- `exclude_incomplete_tegs_function()` - Filter function
- `get_player_name()` - Player code → name lookup

#### Data Preparation
- `load_and_prepare_handicap_data()` - Handicap loading
- `check_hc_strokes_combinations()` - Validation
- `reshape_round_data()` - Wide ↔ Long format
- `save_to_parquet()` - Parquet persistence

### Dependencies

```python
# Will need from io module:
from teg_analysis.io import read_file, write_file

# Keep in utils:
read_from_github, write_to_github (GitHub-specific)

# External:
import pandas as pd
import numpy as np
```

### Critical Issue: @st.cache_data Decorator

**Problem:** These functions use `@st.cache_data` which is Streamlit-specific.

**Solutions:**

1. **Option A: Keep decorator in new location**
   ```python
   # In teg_analysis/core/data_loader.py
   import streamlit as st

   @st.cache_data
   def load_all_data():
       ...
   ```
   - Pro: No code changes needed
   - Con: Couples analysis to Streamlit

2. **Option B: Extract cache logic, separate function**
   ```python
   # teg_analysis/core/data_loader.py
   def _load_all_data_uncached():
       # Core logic without decorator

   # streamlit/utils.py (wrapper)
   import streamlit as st
   from teg_analysis.core import _load_all_data_uncached

   @st.cache_data
   def load_all_data():
       return _load_all_data_uncached()
   ```
   - Pro: Pure logic separated from caching
   - Con: Extra wrapper layer
   - **RECOMMENDED**

3. **Option C: Custom caching abstraction**
   ```python
   # teg_analysis/core/cache.py
   class CacheStrategy:
       def cache(self, func): ...

   # Then use in data_loader.py
   ```
   - Pro: Flexible, replaceable
   - Con: More complex

### Files Requiring Updates: 22

Same 22 files as Phase 1:
```
Changed import:
  OLD: from utils import load_all_data
  NEW: from teg_analysis.core import load_all_data
       from streamlit.utils import load_all_data  # (wrapper)
```

### Migration Steps

```
Step 1: Create core module
  - Create teg_analysis/core/
  - Create teg_analysis/core/data_loader.py
  - Create teg_analysis/core/__init__.py

Step 2: Extract cache-free version
  - Copy load_all_data logic to _load_all_data_uncached()
  - Copy all helper functions
  - Remove @st.cache_data decorator
  - Verify logic correctness

Step 3: Test core module
  - Test _load_all_data_uncached() locally
  - Verify data integrity
  - Compare output with original

Step 4: Create wrapper in utils
  - Import _load_all_data_uncached
  - Wrap with @st.cache_data
  - Re-export as load_all_data()

Step 5: Update imports in 22 files
  - Can point to utils.load_all_data OR
  - Point to teg_analysis.core via utils

Step 6: Test full pipeline
  - Run all pages
  - Verify cache behavior
  - Check data freshness after updates
  - Monitor performance

Step 7: Deprecate old version
  - Add warnings in utils.load_all_data()
  - Timeline: 2 versions before removal
```

### Dependency Chain

```
load_all_data() calls:
  ├─ read_file(ALL_SCORES_PARQUET) → Phase 1
  ├─ read_file(HANDICAPS_CSV) → Phase 1
  ├─ process_round_for_all_scores()
  │  ├─ add_cumulative_scores()
  │  ├─ add_rankings_and_gaps()
  │  └─ apply_score_types()
  └─ get_incomplete_tegs()
```

**Migration Order:** Must do Phase 1 (I/O) first!

### Risk Assessment

| Risk | Level | Mitigation |
|------|-------|-----------|
| Cache behavior changes | High | Extensive testing of @st.cache with new structure |
| Data pipeline breaks | High | Test output matches original exactly |
| Performance degrades | Medium | Profile before/after migration |
| Incomplete TEG filtering fails | Medium | Unit test edge cases (2-3 rounds, 4 rounds) |

### Estimated Time

- **Implementation:** 3 hours
- **Testing:** 4 hours
- **Optimization:** 2 hours
- **Total:** 9 hours

---

## Phase 3: Pure Helpers (LOW RISK)

### Candidates for Migration (16 modules)

All of these can be moved to `teg_analysis/analysis/` with minimal risk:

```
Scoring Analysis (4 modules):
  - scoring_data_processing.py (180 lines) → teg_analysis/analysis/scoring.py
  - scoring_achievements_processing.py (115 lines) → teg_analysis/analysis/achievements.py
  - par_analysis_processing.py (73 lines) → teg_analysis/analysis/par.py
  - score_count_processing.py (565 lines) → [split into analysis + UI]

Performance Analysis (5 modules):
  - records_identification.py (627 lines) → teg_analysis/analysis/records.py
  - best_performance_processing.py (633 lines) → teg_analysis/analysis/performance.py
  - worst_performance_processing.py (175 lines) → teg_analysis/analysis/performance.py
  - comeback_analysis.py (436 lines) → teg_analysis/analysis/comeback.py
  - history_data_processing.py (792 lines) → teg_analysis/analysis/history.py

Display Helpers (4 modules):
  - display_helpers.py (467 lines) → teg_analysis/display/formatters.py
  - scorecard_data_processing.py (155 lines) → teg_analysis/display/scorecard.py
  - records_css.py (65 lines) → streamlit/assets/css/records.css
  - course_analysis_processing.py (161 lines) → teg_analysis/analysis/course.py

Other:
  - bestball_processing.py (132 lines) → teg_analysis/analysis/bestball.py
```

### Why Low Risk?

1. **Pure functions** - No Streamlit, no utils dependency (mostly)
2. **No circular deps** - Don't import from other helpers
3. **Data in, data out** - Pandas operations only
4. **Well-tested** - Already in production, working

### Migration Pattern

For each module:

```
Step 1: Copy to new location
  - Copy file to teg_analysis/analysis/ (or appropriate subdir)

Step 2: Update internal imports
  - Look for: from streamlit.helpers import X
  - Change to: from teg_analysis.analysis import X
  - Most modules have no internal imports

Step 3: Update external references (pages)
  - OLD: from helpers.scoring_data_processing import func
  - NEW: from teg_analysis.analysis.scoring import func

Step 4: Test that page still works
  - Same output as before
  - No performance regression

Step 5: Update streamlit/helpers/__init__.py
  - Import from new location
  - Re-export for backward compatibility
  - Add deprecation notes
```

### Import Update Locations

```
Module: scoring_data_processing.py (used by: 400scoring.py, ave_by_teg.py, score_matrix.py)
  400scoring.py line 23:
    OLD: from helpers.scoring_data_processing import ...
    NEW: from teg_analysis.analysis.scoring import ...

Module: streak_analysis_processing.py (used by: streaks.py)
  streaks.py line 10:
    OLD: from helpers.streak_analysis_processing import ...
    NEW: from teg_analysis.analysis.streaks import ...

Module: records_identification.py (used by: 300TEG Records.py)
  300TEG Records.py line X:
    OLD: from helpers.records_identification import ...
    NEW: from teg_analysis.analysis.records import ...

[Continue for each module...]
```

### Estimated Time (Per Module)

- Simple (<200 lines): 20 minutes each → 4 modules × 20 min = 1.3 hours
- Medium (200-500 lines): 30 minutes each → 7 modules × 30 min = 3.5 hours
- Large (500+ lines): 45 minutes each → 5 modules × 45 min = 3.75 hours

**Total: ~8.5 hours** (assuming 2 people can work in parallel: ~4-5 hours)

### Testing for Phase 3

```
For each page that uses migrated module:
  1. Page still loads
  2. Data displayed is identical
  3. Charts render correctly
  4. No performance regression

Test pages (sample):
  - 400scoring.py (uses scoring_data_processing)
  - streaks.py (uses streak_analysis_processing)
  - 300TEG Records.py (uses records_identification)
  - 301Best_TEGs_and_Rounds.py (uses best_performance_processing)
```

---

## Phase 4: Mixed Modules (MEDIUM RISK)

### Candidates Requiring Refactoring (4 modules)

These modules mix pure logic with Streamlit dependencies. Need to split before migrating.

#### 1. `score_count_processing.py` (565 lines)

**Current:** 100% in helpers/
**Issue:** Mixes data processing with st.selectbox, st.metric, st.write

**Split Strategy:**

```
NEW: teg_analysis/analysis/score_count.py (Pure logic)
├── count_scores_by_player()
├── count_scores_by_teg()
├── count_scores_distribution()
└── ... (all pandas operations)

KEEP: streamlit/helpers/score_count_display.py (UI layer)
├── display_score_counts()
├── show_player_selector()
├── render_distribution_chart()
└── ... (all Streamlit widgets)
```

**Files Using:** sc_count.py
**Migration Plan:**
  1. Extract pure functions to core
  2. Keep display functions in streamlit/
  3. Update sc_count.py to use both

**Effort:** 3 hours

#### 2. `data_update_processing.py` (380 lines)

**Current:** 100% in helpers/
**Issue:** Mixes data validation & transformation with st.form, st.button

**Split Strategy:**

```
NEW: teg_analysis/operations/data_update.py (Pure logic)
├── validate_round_data()
├── update_tournament_data()
├── calculate_new_scores()
└── ... (validation & calculation)

KEEP: streamlit/helpers/data_update_ui.py (Forms & UI)
├── build_data_form()
├── handle_submission()
├── show_update_status()
└── ... (Streamlit widgets)
```

**Files Using:** 1000Data update.py
**Effort:** 3 hours

#### 3. `data_deletion_processing.py` (224 lines)

**Similar to above**

**Split:**
```
NEW: teg_analysis/operations/data_deletion.py (Core logic)
KEEP: streamlit/helpers/data_deletion_ui.py (UI)
```

**Effort:** 2 hours

#### 4. `commentary_generator.py` (460 lines)

**Current:** Complex - has data generation + Claude API + UI

**Split Strategy:**

```
NEW: teg_analysis/reporting/commentary.py (Core generation)
├── generate_round_summary()
├── generate_tournament_report()
├── format_commentary()
└── ... (text generation logic)

NEW: teg_analysis/ai/claude_integration.py (AI backend)
├── call_claude_api()
├── process_ai_response()
└── ... (Claude integration)

KEEP: streamlit/helpers/commentary_display.py (UI)
├── show_generation_progress()
├── display_report()
├── handle_downloads()
└── ... (Streamlit display)
```

**Files Using:** 1001Report Generation.py
**Effort:** 5 hours (most complex)

### Total Effort for Phase 4

```
score_count_processing.py: 3 hours
data_update_processing.py: 3 hours
data_deletion_processing.py: 2 hours
commentary_generator.py: 5 hours
─────────────────────────────
TOTAL: 13 hours
```

### Risk Mitigation

- Test each extracted module independently
- Verify UI layer still calls core functions correctly
- Monitor for missing edge cases
- Gradual rollout (one module at a time)

---

## Phase 5: Analysis Functions

### High-Value Migrations

**Target:** Migrate core analysis functions to standalone library

```
Migrate to teg_analysis/analysis/core.py:
  - format_vs_par()
  - get_net_competition_measure()
  - add_ranks()
  - get_teg_winners()
  - aggregate_data()
  - get_best() / get_worst()
  - ordinal() / safe_ordinal()
```

**Why:** These are pure functions used by many pages
**Impact:** 10+ files need imports updated
**Effort:** 4-5 hours including tests

### Caching Functions

**Option 1: Remove @st.cache_data, add explicit cache layer**
```
def get_complete_teg_data_uncached():
    # Core logic

class TegDataCache:
    def get_complete_teg_data(self):
        # Manage caching without Streamlit
```

**Option 2: Keep as is, document as Streamlit-dependent**
- Less refactoring
- Acceptable if keeping in utils.py

---

## Phase 6: UI Functions (NO MIGRATION)

### Functions That Must Stay in `streamlit/utils.py`

```
Configuration:
  - get_page_layout()
  - clear_all_caches()

Navigation:
  - add_custom_navigation_links()
  - add_section_navigation_links()
  - create_custom_navigation_section()
  - convert_filename_to_streamlit_url()

Display:
  - load_css_file()
  - load_datawrapper_css()
  - load_teg_reports_css()
  - create_stat_section()
  - datawrapper_table()
  - apply_custom_navigation_css()

Setup/Config:
  - get_app_base_url()
  - get_teg_filter_options()
  - filter_data_by_teg()
```

**Reason:** All use Streamlit APIs (st.* functions)
**Migration Impact:** None (by design)
**Maintenance:** Keep in utils.py as convenience layer

---

## Testing Strategy

### Unit Tests

```
For each migrated function:
  1. Input: Use sample data matching production
  2. Output: Verify against original implementation
  3. Edge cases: Empty data, single row, large dataset
  4. Performance: Compare execution time
```

### Integration Tests

```
For each page using migrated code:
  1. Can page import new module?
  2. Page renders without errors?
  3. Data displayed matches original?
  4. Charts work correctly?
  5. Filters/controls work?
```

### Regression Tests

```
Before migration:
  - Capture baseline metrics
  - Record execution times
  - Note any warnings/errors

After migration:
  - Run same metrics
  - Compare execution times (should be identical or faster)
  - Check for new warnings/errors
```

### Environment Testing

```
Local Development:
  - Test all phases locally
  - Verify file I/O works
  - Test caching behavior

Railway Production:
  - Test on actual Railway instance
  - Verify GitHub integration
  - Check volume persistence
  - Monitor performance
```

---

## Rollback Plan

### If Phase Fails at Any Point

#### Immediate Response
```
1. Switch back to old imports
2. Restore original utils.py
3. Document error that occurred
4. Communicate to team
```

#### Recovery Steps
```
1. Create branch: rollback/phase-N
2. Revert all changes: git revert HEAD~N..HEAD
3. Verify system stability
4. Root cause analysis
5. Plan corrected approach
```

#### Prevention
```
1. Keep old code in place for 1-2 versions
2. Add deprecation warnings (don't remove yet)
3. Use feature flags to enable new code
4. Gradual rollout (10% → 50% → 100%)
```

### Backup Strategy

```
Before each phase:
  - Tag git: git tag phase-N-before
  - Save database backups
  - Document current state

During phase:
  - Commit every completed sub-step
  - Test frequently
  - Monitor production (if live)

After phase:
  - Tag git: git tag phase-N-after
  - Document migration results
  - Performance comparison
```

---

## Phase Completion Checklist

Use this for each phase:

```
Phase N: [NAME]

Pre-Migration:
  ☐ All existing tests passing
  ☐ Code review completed
  ☐ Branch created from main
  ☐ Backup taken

Implementation:
  ☐ New module created
  ☐ Functions copied
  ☐ Internal imports updated
  ☐ Tests pass locally

Integration:
  ☐ All 22 files updated with new imports
  ☐ No import errors
  ☐ Pages render correctly
  ☐ Data output verified

Testing:
  ☐ Unit tests pass
  ☐ Integration tests pass
  ☐ Regression tests show no degradation
  ☐ Performance verified
  ☐ Railway environment tested

Documentation:
  ☐ Migration documented
  ☐ Breaking changes noted (if any)
  ☐ Deprecation warnings added
  ☐ Team trained on new imports

Deployment:
  ☐ Code review approved
  ☐ Merged to main
  ☐ Deployed to production
  ☐ Monitoring enabled
  ☐ Rollback plan ready
```

---

## Timeline Estimate

```
Phase 1 (I/O Functions):       5 hours   Week 1
Phase 2 (Data Loading):        9 hours   Week 2-3
Phase 3 (Pure Helpers):        8.5 hours Week 3-4
Phase 4 (Mixed Modules):       13 hours  Week 4-5
Phase 5 (Analysis Functions):  5 hours   Week 5
Phase 6 (UI Functions):        0 hours   (No migration)
                               ─────────
TOTAL:                         40.5 hours (~1 month)

With 2 people: 20 hours each (2-3 weeks)
With 3 people: 13-14 hours each (1.5-2 weeks)
```

---

## Success Metrics

```
Metric: All phases complete
  ✓ 100% of files successfully migrated
  ✓ Zero import errors
  ✓ All tests passing
  ✓ Performance unchanged or improved
  ✓ Code coverage >= 80%

Metric: System stability
  ✓ Zero crashes in production
  ✓ Data integrity maintained
  ✓ Cache behavior correct
  ✓ GitHub integration working

Metric: Team capability
  ✓ Team understands new structure
  ✓ New imports documented
  ✓ Onboarding guide written
  ✓ Common patterns established
```

---

**Document Version:** 1.0
**Last Updated:** October 18, 2025
**Ready for:** Phase 1 implementation
