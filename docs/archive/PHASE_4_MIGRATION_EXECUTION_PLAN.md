# Phase 4, Task 4.2: Migration Execution Plan & Safety Procedures

**Status:** Planning Document
**Date:** 2025-10-25
**Scope:** Detailed sequence for executing migration from utils.py to teg_analysis/

---

## Executive Summary

This document defines the phased approach to migrating 230+ functions from `utils.py` and helpers/ into the new `teg_analysis/` package structure. The plan minimizes risk through incremental migration with comprehensive testing at each stage.

**Migration Timeline:** ~8-10 weeks (estimated)
**Risk Level:** MEDIUM (high-impact functions like load_all_data)
**Contingency:** Rollback procedures documented for each phase

---

## Part 1: Migration Phases Overview

### High-Level Timeline

```
Week 1:  Phase I   - I/O Layer (3 modules, 26 functions)
Week 2:  Phase II  - Core Layer (2 modules, 19 functions)
Week 3:  Phase III - Analysis Layer (7 modules, 91 functions) [longest]
Week 4:  Phase IV  - Display Layer (3 modules, 44 functions)
Week 5:  Integration & Testing
Week 6+: Cleanup & Optimization
```

---

## Phase I: I/O Layer Migration (Week 1)

### Scope
- 3 modules (volume_operations, file_operations, github_operations)
- 26 functions
- No dependencies on other teg_analysis modules
- External dependencies: os, pathlib, pandas, PyGithub

### Phase I.1: Setup teg_analysis Package

**1.1.1: Create package structure**
```bash
mkdir -p streamlit/../teg_analysis/{core,io,analysis,display,api}
touch streamlit/../teg_analysis/__init__.py
touch streamlit/../teg_analysis/core/__init__.py
touch streamlit/../teg_analysis/io/__init__.py
touch streamlit/../teg_analysis/analysis/__init__.py
touch streamlit/../teg_analysis/display/__init__.py
touch streamlit/../teg_analysis/api/__init__.py
```

**1.1.2: Create volume_operations.py**
```python
# teg_analysis/io/volume_operations.py
"""Railway volume and local environment management."""

def _is_railway() -> bool:
    """Check if running on Railway environment."""
    ...

def _get_volume_path(file_path: str) -> str:
    """Get volume path for Railway."""
    ...

def _get_local_path(file_path: str) -> Path:
    """Get local development path."""
    ...

def _ensure_volume_dir(volume_path: str) -> None:
    """Ensure volume directory exists."""
    ...
```

**1.1.3: Create file_operations.py**
```python
# teg_analysis/io/file_operations.py
"""Environment-aware file I/O operations."""

from . import volume_operations  # Import helper functions

def read_file(file_path: str) -> pd.DataFrame:
    """Read file from Railway volume or local disk."""
    # Implementation from utils.py
    ...

def write_file(file_path: str, data: pd.DataFrame, ...) -> None:
    """Write file to Railway volume or local disk."""
    # Implementation from utils.py
    ...

# ... more functions
```

**1.1.4: Create github_operations.py**
```python
# teg_analysis/io/github_operations.py
"""GitHub API operations for data persistence."""

def read_from_github(file_path: str) -> pd.DataFrame:
    """Read file from GitHub."""
    # Implementation from utils.py
    ...

# ... more functions
```

### Phase I.2: Testing I/O Layer

**Test 1: Independent module tests**
```bash
pytest tests/test_io_volume.py -v
pytest tests/test_io_file.py -v
pytest tests/test_io_github.py -v
```

**Test 2: Integration with existing code**
- Keep both utils.py functions and teg_analysis functions
- Create wrapper in utils.py that calls teg_analysis
- Verify outputs identical

```python
# streamlit/utils.py (temporary wrapper during migration)
from teg_analysis.io.file_operations import read_file as _read_file_new

@st.cache_data
def read_file(file_path: str) -> pd.DataFrame:
    """Cached wrapper for new I/O implementation."""
    return _read_file_new(file_path)
```

**Test 3: Full regression testing**
- Run all 94 existing tests
- Verify no performance degradation
- Check Railway environment behavior

### Phase I.3: Rollback Procedure

**If issues occur:**
1. Delete teg_analysis/io/ directory
2. Keep utils.py functions unchanged
3. Restart: Phase I.1

**Time estimate:** 5 minutes

---

## Phase II: Core Data Layer Migration (Week 2)

### Scope
- 2 modules (data_loader, data_transforms)
- 19 functions (including critical load_all_data)
- Depends on: I/O layer only
- External: pandas, numpy, streamlit

### Phase II.1: Create Core Modules

**2.1.1: Create core/data_loader.py**
```python
# teg_analysis/core/data_loader.py
"""Primary data loading functions."""

import streamlit as st
from teg_analysis.io.file_operations import read_file

@st.cache_data
def load_all_data(exclude_teg_50: bool = True, exclude_incomplete_tegs: bool = False) -> pd.DataFrame:
    """Load all tournament data with caching."""
    # Implementation from utils.py
    ...

# ... 5 more data loading functions
```

**2.1.2: Create core/data_transforms.py**
```python
# teg_analysis/core/data_transforms.py
"""Data transformation and enrichment functions."""

from .data_loader import load_all_data

def add_cumulative_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Add cumulative score columns."""
    # Implementation from utils.py
    ...

# ... 5 more transformation functions
```

### Phase II.2: Testing Core Layer

**Test 1: Unit tests**
```bash
pytest tests/test_core_data_loader.py -v
pytest tests/test_core_transforms.py -v
```

**Test 2: Critical function validation**
- Verify load_all_data() output identical to utils.py version
- Check caching behavior
- Validate data integrity

**Test 3: Integration with I/O**
- Test read_file() calls from data_loader
- Verify path handling (Railway vs local)

**Test 4: Full regression suite**
- All 94 existing tests must pass
- Performance benchmarks (should be same or better)

### Phase II.3: Gradual Import Cutover

Once Phase II tests pass:

```python
# Step 1: Update streamlit/utils.py to import from teg_analysis
from teg_analysis.core.data_loader import load_all_data as _load_all_data

@st.cache_data
def load_all_data(...):
    """Cached wrapper for new implementation."""
    return _load_all_data(...)

# Step 2: Update page imports one at a time
# Before: from utils import load_all_data
# After:  from teg_analysis.core import load_all_data
```

### Phase II.4: Rollback Procedure

**If issues occur:**
1. Delete teg_analysis/core/ directory
2. Revert utils.py to direct implementations
3. Restart: Phase II.1

**Time estimate:** 10 minutes

---

## Phase III: Analysis Layer Migration (Week 3)

### Scope
- 7 modules (scoring, rankings, aggregation, streaks, records, commentary, pipeline)
- 91 functions (most complex)
- Depends on: Core + I/O layers
- Dependencies between analysis modules: scoring → rankings → aggregation

### Phase III.1: Migration Order (Critical!)

```
1. analysis/scoring.py         (depends on: core)
2. analysis/rankings.py        (depends on: core, scoring)
3. analysis/aggregation.py     (depends on: core, scoring, rankings)
4. analysis/streaks.py         (depends on: core)
5. analysis/records.py         (depends on: core, aggregation)
6. analysis/commentary.py      (depends on: all of above)
7. analysis/pipeline.py        (depends on: all modules)
```

**Rationale:** Must follow dependency order to avoid import errors

### Phase III.2: Migrate Scoring Module

```python
# teg_analysis/analysis/scoring.py
"""Scoring calculations and utilities."""

from teg_analysis.core import load_all_data

def format_vs_par(value: int) -> str:
    """Format value as vs-par score."""
    # Implementation from utils.py
    ...

@st.cache_data
def get_net_competition_measure(teg_num: int) -> str:
    """Get scoring measure for TEG."""
    # Implementation from utils.py
    ...

# ... 12 functions from scoring_data_processing.py
```

### Phase III.3: Migrate Remaining Analysis Modules

**Rankings → Aggregation → Streaks → Records** (in parallel after scoring)

Once scoring is stable:
- Migrate rankings (depends on scoring)
- Migrate aggregation (depends on rankings)
- Migrate streaks, records (independent of above 2)

**Commentary & Pipeline** (last - depend on all others)

### Phase III.4: Testing Analysis Layer

**Test at each module level:**
```bash
pytest tests/test_analysis_scoring.py -v
pytest tests/test_analysis_rankings.py -v
pytest tests/test_analysis_aggregation.py -v
# ... etc
```

**Integration tests:**
- Test cross-module dependencies
- Verify caching behavior
- Check data consistency across modules

**Critical function validation:**
- create_round_summary() correctness
- aggregate_data() output verification
- Ranking calculations accuracy

**Full regression:**
- All 94 tests pass
- Performance benchmarks acceptable
- No cache collisions

### Phase III.5: Rollback Procedure

**If issues occur at any module:**
1. Restore that module's functions to utils.py
2. Keep already-migrated modules in place
3. Fix and retry

**Time estimate:** 15-30 minutes per module

---

## Phase IV: Display Layer Migration (Week 4)

### Scope
- 3 modules (formatters, tables, charts)
- 44 functions
- Depends on: Core + Analysis layers
- No internal dependencies between display modules

### Phase IV.1: Migrate Display Modules

```python
# teg_analysis/display/formatters.py
"""Value formatting utilities."""

from teg_analysis.analysis.scoring import format_vs_par
from teg_analysis.analysis.rankings import ordinal

def format_leaderboard_value(value, value_type: str) -> str:
    """Format leaderboard score values."""
    # Implementation from leaderboard_utils.py
    ...

# ... 20 formatting functions
```

### Phase IV.2: Testing Display Layer

**Unit tests:**
```bash
pytest tests/test_display_formatters.py -v
pytest tests/test_display_tables.py -v
pytest tests/test_display_charts.py -v
```

**Output validation:**
- Compare formatted values with original
- Check table generation
- Verify chart helper functions

**Integration:**
- Test with analysis layer
- Verify data flow from analysis → display

### Phase IV.3: Update Streamlit Pages

Once display modules pass tests:
```python
# Before: from utils import format_leaderboard_value
# After:  from teg_analysis.display import format_leaderboard_value
```

---

## Part 2: Testing Strategy

### Test Pyramid

```
Level 1: Unit Tests (Module-specific)
- Each module tested independently
- Mock external dependencies
- Fast execution (~30s per module)

Level 2: Integration Tests (Between modules)
- Test cross-module dependencies
- Verify data consistency
- Moderate execution (~2 min per phase)

Level 3: Regression Tests (Full suite)
- All 94 existing tests
- Performance benchmarks
- Slow but comprehensive (~10 min)

Level 4: Smoke Tests (Production paths)
- Load streamlit pages
- Verify no import errors
- Check data consistency
```

### Test Execution Checklist

**For each phase:**
- [ ] Create/update unit tests for new modules
- [ ] Run unit tests (all pass)
- [ ] Run integration tests (all pass)
- [ ] Run full regression suite (94 tests, all pass)
- [ ] Performance benchmark (same or better)
- [ ] Manual smoke test (load pages in streamlit)
- [ ] Verify Railway environment behavior
- [ ] Sign off on phase completion

---

## Part 3: Safety Procedures

### Pre-Migration Checklist

- [ ] All current tests passing (100%)
- [ ] Current git branch clean (no uncommitted changes)
- [ ] Create git branch: `refactor/phase-migration-[phase-num]`
- [ ] Backup utils.py to archive/
- [ ] Document baseline performance metrics
- [ ] Notify team of planned migration

### During Migration

**For each function moved:**
1. Copy function to new module
2. Test new module independently
3. Create wrapper in utils.py (temporary)
4. Run regression tests
5. Commit to git with clear message
6. Only then delete from original location

**Commit message example:**
```
refactor(phase-4): Migrate I/O functions to teg_analysis

Moved 5 file operations to teg_analysis/io/file_operations.py:
- read_file()
- write_file()
- backup_file()
- (2 more)

Created temporary wrappers in utils.py for backward compatibility.
All 94 tests passing, performance verified.

Phase I.1 complete.
```

### Rollback Procedures

**If Phase Fails:**
1. git reset --hard [pre-phase-commit]
2. Restore utils.py from archive
3. Investigate issues
4. Fix and restart phase

**If Single Function Breaks:**
1. git revert [commit-that-broke-it]
2. Restore function to utils.py
3. Fix issue in new module
4. Commit fix and retry

**Rollback Time Estimates:**
- Full phase: 5-30 minutes (depends on how far in we got)
- Single function: 5 minutes

### Communication Protocol

- Notify team before starting each phase
- Daily progress updates during Phase III (most complex)
- Notify when phase complete and tests passing
- Document any issues and resolutions
- Review at end of each phase before proceeding

---

## Part 4: Performance Validation

### Baseline Metrics (Pre-Migration)

**Capture before starting Phase I:**
```bash
# Function execution times
pytest tests/test_performance.py::test_create_round_summary_performance -v -s

# Page load times
streamlit run streamlit/nav.py &
# Manually time page loads in browser

# Memory usage
# Monitor during tests

# Cache hit rates
# Log cache statistics
```

### Continuous Validation

**After each phase completion:**
```bash
# Re-run performance tests
pytest tests/test_performance.py -v

# Check for regressions
pytest tests/ -v

# Profile memory usage
python -m memory_profiler tests/test_performance.py
```

### Success Criteria

- [ ] Execution time: Same or faster than baseline
- [ ] Memory usage: No increase
- [ ] Cache hit rates: No degradation
- [ ] All tests: Passing (100%)
- [ ] No new warnings or errors

---

## Part 5: Migration Timeline

### Week 1: Phase I (I/O Layer)
- Mon-Tue: Create package structure, volume_operations module
- Wed: Create file_operations, github_operations modules
- Thu: Testing and integration
- Fri: Finalization and rollback procedure verification

### Week 2: Phase II (Core Layer)
- Mon-Tue: Create data_loader module
- Wed: Create data_transforms module
- Thu-Fri: Testing, cutover, finalization

### Week 3: Phase III (Analysis Layer)
- Mon-Tue: scoring, rankings modules
- Wed: aggregation module
- Thu: streaks, records modules
- Fri: commentary, pipeline modules (might spill into next week)

### Week 4: Phase IV (Display Layer)
- Mon-Tue: formatters module
- Wed: tables, charts modules
- Thu-Fri: Integration, testing, finalization

### Week 5: Integration & Cleanup
- Remove temporary wrappers from utils.py
- Final regression testing
- Document complete migration

---

## Part 6: Risk Mitigation

### Risk 1: Breaking load_all_data()
**Impact:** HIGH (40+ pages depend)
**Mitigation:**
- Create comprehensive tests for this function
- Use temporary wrapper pattern during migration
- Test each dependent page after migration
- Have rollback plan ready

### Risk 2: Import Errors After Migration
**Impact:** HIGH (pages won't load)
**Mitigation:**
- Test imports at each module level
- Create __init__.py with public API
- Verify all import paths before committing
- Use linter to catch missing imports

### Risk 3: Caching Issues
**Impact:** MEDIUM (performance)
**Mitigation:**
- Keep @st.cache_data decorators in place
- Test cache behavior explicitly
- Monitor cache hit rates
- Compare performance before/after

### Risk 4: Circular Dependency Missed
**Impact:** HIGH (import failures)
**Mitigation:**
- Already checked for circular dependencies (0 found)
- Verify during migration
- Follow dependency order strictly
- Fail fast if circular detected

### Risk 5: Data Consistency Issues
**Impact:** HIGH (wrong results)
**Mitigation:**
- Compare outputs with original functions
- Use data validation tests
- Check numerical precision
- Validate against known test cases

---

## Summary

**Migration Scope:** 230+ functions, 4 phases, ~8-10 weeks

**Risk Level:** MEDIUM (high-impact functions)

**Testing:** Comprehensive at each phase with regression testing

**Rollback:** Clear procedures at each step

**Status:** Ready for Phase 5 (Full Refactoring)

---

**Prepared by:** Claude Code (Phase 4 Executor)
**Date:** 2025-10-25
**Status:** Migration Plan Complete - Ready for Execution
