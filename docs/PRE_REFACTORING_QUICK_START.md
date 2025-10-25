# Pre-Refactoring Quick Start Checklist

**Use This For:** Day-to-day tracking during pre-refactoring cleanup
**Full Details:** [PRE_REFACTORING_PLAN.md](PRE_REFACTORING_PLAN.md)
**Status:** 0% Complete (0 of 4 phases)

---

## 🚀 Quick Reference

**Total Time:** 30 hours over 4 weeks (updated with Phase 1.5)
**Current Phase:** Not Started
**Priority:** Complete Phase 1 (especially testing) before proceeding

**New Since Plan Created:**
- Phase 1.5: Constants mapping (2 hours) - prevents orphaned variables
- Agent compliance protocol - ensures quality execution
- 7 mandatory checkpoints - requires user approval

**Key Documents:**
- [AGENT_EXECUTION_PROTOCOL.md](AGENT_EXECUTION_PROTOCOL.md) - HOW to execute safely
- [CONSTANTS_MAPPING_GUIDE.md](CONSTANTS_MAPPING_GUIDE.md) - Constants inventory strategy
- [PRE_REFACTORING_PLAN.md](PRE_REFACTORING_PLAN.md) - WHAT to execute

---

## Week 1: Phase 1 - Quick Wins (~10 hours, updated)

### ⚠️ CRITICAL: Testing Infrastructure (4 hours) - DO THIS FIRST
**Why:** Cannot safely refactor without tests

- [ ] Install pytest: `pip install pytest pytest-cov`
- [ ] Create tests/ directory structure
- [ ] Create conftest.py with fixtures
- [ ] Write data loading tests (test_data_loading.py)
- [ ] Write helper module tests (test_helpers.py)
- [ ] Write page smoke tests (test_pages_smoke.py)
- [ ] Create pytest.ini configuration
- [ ] Run tests: `pytest tests/ -v`
- [ ] Target: ≥25 tests, ≥50% passing initially

**Success:** Test suite runs, catches basic errors

---

### Delete Within-File Duplicates (1 hour)
**Impact:** Remove 370 lines of waste

#### `history_data_processing.py` (30 min)
- [ ] Delete `extract_teg_num` duplicate (line 639)
- [ ] Delete `check_winner_completeness` duplicate (line 658)
- [ ] Delete `display_completeness_status` duplicate (line 694)
- [ ] Delete `calculate_and_save_missing_winners` duplicate (lines 714-793)
- [ ] Test: Run `101TEG History.py`, `1000Data update.py`

#### Commentary Files (20 min)
- [ ] Fix `generate_tournament_commentary_v2.py` (2 duplicates)
- [ ] Fix `generate_round_report.py` (1 duplicate)
- [ ] Test: Run `1001Report Generation.py`

#### Quick Fixes (10 min)
- [ ] Fix `player_history.py` (`teg_sort_key` duplicate)
- [ ] Fix `generate_commentary.py` (`read_file` duplicate)

---

### Archive Unused Code (2 hours)
**Impact:** 20 functions archived (6% reduction)

- [ ] Create archive directory: `streamlit/archive/unused_2025_10_19/`
- [ ] Archive 20 HIGH-confidence unused functions (see list in plan)
- [ ] Test after each batch: `streamlit run streamlit/nav.py`
- [ ] Document archived functions

**Functions List:** See [PRE_REFACTORING_PLAN.md Task 1.2](PRE_REFACTORING_PLAN.md#task-12-archive-high-confidence-unused-code-2-hours)

---

### Add Utility Functions (1 hour)

- [ ] Add `safe_int()` to utils.py (line ~50)
- [ ] Update 3 files to import from utils
- [ ] Test commentary generation

---

### Map Constants & Global Variables (2 hours) - NEW PHASE 1.5

**CRITICAL:** Prevents orphaned constants during refactoring

- [ ] Run constants inventory script: `python analyze_constants.py > docs/CONSTANTS_INVENTORY.md`
- [ ] Review constants report (119+ constants expected)
- [ ] For each major constant, document usage with grep
- [ ] Create CONSTANT_MIGRATION_PLAN.md
- [ ] Update migration_impact.md with constant moves
- [ ] Test: Verify constants can be imported

**Why:** Functions use constants. If constants don't move WITH functions → NameError

**Reference:** [CONSTANTS_MAPPING_GUIDE.md](CONSTANTS_MAPPING_GUIDE.md)

---

### Week 1 Success Criteria
- [ ] Test suite running (≥25 tests)
- [ ] 370 lines of duplicates removed
- [ ] 20 unused functions archived
- [ ] Utility functions consolidated
- [ ] Constants inventory complete (Phase 1.5)
- [ ] All tests passing
- [ ] **Checkpoint 1 passed** (see Agent Protocol)
- [ ] Git commit: "Phase 1: Quick wins complete"

---

## Week 2: Phase 2 - Naming Conflicts (~6 hours)

### Rename `render_report` (2 hours)
**Target:** 5 functions, all with same name

- [ ] Rename in `102TEG Results.py` → `render_teg_results_report`
- [ ] Rename in `latest_teg_context.py` → `render_latest_teg_report`
- [ ] Rename in `teg_reports.py` → `render_tournament_report`
- [ ] Rename in `teg_reports_17brief.py` → `render_brief_tournament_report`
- [ ] Rename in `teg_reports_17full.py` → `render_full_tournament_report`
- [ ] Test each page after rename

---

### Rename `format_value` (1 hour)
**Target:** 4 functions, all with same name

- [ ] Rename in `500Handicaps.py` → `format_handicap_value`
- [ ] Rename in `leaderboard_utils.py` → `format_leaderboard_value`
- [ ] Rename in `make_charts.py` → `format_chart_value`
- [ ] Rename in `records_identification.py` → `format_record_value`
- [ ] Test each affected page

---

### Review MEDIUM-Confidence Unused (3 hours)

- [ ] Review 11 "imported but not called" functions
- [ ] For each: grep for usage, decide keep/archive
- [ ] Document decisions in ANALYSIS_SUMMARY_FINAL.md
- [ ] Archive or mark as kept

---

### Week 2 Success Criteria
- [ ] Zero naming conflicts (9 functions renamed)
- [ ] All MEDIUM-confidence unused reviewed
- [ ] Decisions documented
- [ ] All tests passing
- [ ] **Checkpoint 2 passed** (see Agent Protocol)
- [ ] Git commit: "Phase 2: Naming conflicts resolved"

---

## Week 3: Phase 3 - Technical Debt (~8 hours)

### Consolidate Data Loaders (4 hours)

- [ ] Find all uses of `round_data_loader` (old version)
- [ ] Update imports to `unified_round_data_loader`
- [ ] Test after each file update
- [ ] Archive old `round_data_loader.py`
- [ ] Comprehensive commentary testing

---

### Document utils.py (2 hours)

- [ ] Add 16 section headers to utils.py
- [ ] Add table of contents at top
- [ ] Update function docstrings (missing/incomplete)
- [ ] Verify no syntax errors: `python -c "import streamlit.utils"`

**Sections:**
1. Configuration & Setup
2. GitHub I/O
3. Railway Volume Management
4. Core Data Loading
5. Data Transforms
6. Cache Updates
7-16. (see plan for full list)

---

### Fix Performance Issues (2 hours)

- [ ] Create performance benchmark test
- [ ] Profile `create_round_summary()` (baseline)
- [ ] Optimize algorithm (target: 10x speedup)
- [ ] Verify correctness (compare outputs)
- [ ] Re-run performance test
- [ ] Regression test all pages

---

### Week 3 Success Criteria
- [ ] Single data loader (unified version only)
- [ ] utils.py organized with section headers
- [ ] create_round_summary() optimized (≥10x faster)
- [ ] All tests passing
- [ ] **Checkpoint 3 passed** (see Agent Protocol)
- [ ] Git commit: "Phase 3: Technical debt addressed"

---

## Week 4: Phase 4 - Migration Architecture (~6 hours)

### Design Package Structure (3 hours)

- [ ] Define `teg_analysis/` directory structure
- [ ] Map all 102 utils.py functions to destinations
- [ ] Map all 20 helper modules
- [ ] Decide Streamlit caching strategy
- [ ] Create REFACTORING_FUNCTION_MAP.md

**Structure:**
```
teg_analysis/
├── core/          # Data loading
├── io/            # File operations
├── analysis/      # Calculations
├── display/       # Formatting
└── api/           # Public API
```

---

### Create Migration Plan (2 hours)

- [ ] Update migration_impact.md with cleaned codebase
- [ ] Create REFACTORING_MIGRATION_SEQUENCE.md
- [ ] Create REFACTORING_CHECKLIST.md
- [ ] Sequence migrations (dependency order)

---

### Define API Surface (1 hour)

- [ ] Identify 20-30 core API functions
- [ ] Document expected inputs/outputs
- [ ] Create API_DESIGN.md
- [ ] Define API modules (data, analysis, display)

---

### Week 4 Success Criteria
- [ ] Package structure defined
- [ ] All functions mapped to destinations
- [ ] Migration sequence documented
- [ ] API surface defined
- [ ] Ready to begin refactoring
- [ ] **Checkpoint 4 passed** (see Agent Protocol)
- [ ] Git commit: "Phase 4: Migration architecture complete"

---

## Overall Progress Tracker

### Phases Complete
- [ ] Phase 1: Quick Wins (Week 1) - includes Phase 1.5 (Constants)
- [ ] Phase 2: Naming Conflicts (Week 2)
- [ ] Phase 3: Technical Debt (Week 3)
- [ ] Phase 4: Migration Architecture (Week 4)

### Checkpoints Passed
- [ ] Checkpoint 1: After Phase 1.1 (Delete duplicates)
- [ ] Checkpoint 2: After Phase 1.2 (Archive unused)
- [ ] Checkpoint 3: After Phase 1.3 (Add utilities)
- [ ] Checkpoint 4: After Phase 1.4 (Testing infrastructure)
- [ ] Checkpoint 5: After Phase 1.5 (Constants mapping)
- [ ] Checkpoint 6: After Phase 2 (Naming conflicts)
- [ ] Checkpoint 7: After Phase 3 (Technical debt)

**Note:** Agent MUST stop at each checkpoint for user approval. See [AGENT_EXECUTION_PROTOCOL.md](AGENT_EXECUTION_PROTOCOL.md)

### Success Metrics
- [ ] Test coverage: ___% (target: ≥50%)
- [ ] Lines removed: _____ (target: ~600)
- [ ] Functions archived: _____ (target: 20)
- [ ] Naming conflicts: _____ (target: 0)
- [ ] Data loaders: _____ (target: 1)
- [ ] Constants inventoried: _____ (target: 119+)
- [ ] utils.py sections: _____ (target: 16)
- [ ] Performance improvements: _____x (target: ≥10x)

### Ready for Refactoring?
Answer YES to all before proceeding:
- [ ] All 4 phases complete (including Phase 1.5)
- [ ] All 7 checkpoints passed with user approval
- [ ] Test suite at 100% passing
- [ ] Zero import errors
- [ ] All pages functional
- [ ] Constants inventory complete
- [ ] Documentation updated
- [ ] Agent compliance verified
- [ ] Team aligned on approach

---

## Priority Order (If Time Limited)

### Must Do (Non-Negotiable)
1. **Testing Infrastructure** (Phase 1.4) - 4 hours
   - Cannot refactor safely without tests
2. **Constants Mapping** (Phase 1.5) - 2 hours
   - Prevents orphaned variables during migration
3. **Delete Within-File Duplicates** (Phase 1.1) - 1 hour
   - Obvious waste, zero risk
4. **Design Package Structure** (Phase 4.1) - 3 hours
   - Need target architecture

**Minimum:** 10 hours → Ready for basic refactoring

### Should Do (High Value)
5. Archive Unused Code (Phase 1.2) - 2 hours
6. Rename Conflicts (Phase 2.1-2.2) - 3 hours
7. Consolidate Data Loaders (Phase 3.1) - 4 hours

**Recommended:** 19 hours → Well-prepared for refactoring

### Nice to Have (Optimization)
8. Add Utilities (Phase 1.3) - 1 hour
9. Document utils.py (Phase 3.2) - 2 hours
10. Fix Performance (Phase 3.3) - 2 hours
11. Define API (Phase 4.3) - 1 hour

**Complete:** 30 hours → Optimal refactoring readiness

---

## Daily Task Suggestions

### Week 1, Day 1 (2-3 hours)
- Set up testing infrastructure
- Create first 10 tests
- Run test suite
- **Checkpoint 4** (user approval required)

### Week 1, Day 2 (2-3 hours)
- Delete within-file duplicates
- Archive first batch of unused code
- Run tests
- **Checkpoint 1** (user approval required)

### Week 1, Day 3 (2-3 hours)
- Archive remaining unused code
- Add utility functions
- Run constants inventory script
- **Checkpoints 2, 3, 5** (user approvals required)
- Full testing

### Week 2, Day 1 (3 hours)
- Rename all `render_report` functions
- Test each page

### Week 2, Day 2 (3 hours)
- Rename `format_value` functions
- Review MEDIUM-confidence unused

### Week 3, Day 1 (2 hours)
- Find all data loader usages
- Start migrating to unified version

### Week 3, Day 2 (2 hours)
- Complete data loader migration
- Test thoroughly

### Week 3, Day 3 (2 hours)
- Document utils.py structure
- Optimize performance issues

### Week 3, Day 4 (2 hours)
- Test performance improvements
- Final regression testing

### Week 4, Day 1 (3 hours)
- Design package structure
- Map functions to destinations

### Week 4, Day 2 (2 hours)
- Create migration sequence
- Write execution checklist

### Week 4, Day 3 (1 hour)
- Define API surface
- Final documentation review

---

## Testing Checklist

Run after EACH task completion:

### Quick Tests (1-2 minutes)
- [ ] No Python syntax errors
- [ ] Module imports successfully
- [ ] Streamlit app starts

### Standard Tests (5 minutes)
- [ ] pytest suite passes: `pytest tests/ -v`
- [ ] Affected pages load
- [ ] No console errors

### Full Tests (15 minutes)
- [ ] All 7 page categories load
- [ ] Data operations work
- [ ] Commentary generation works
- [ ] No performance regressions

---

## Rollback Procedure

If anything breaks:
1. **Stop immediately** - don't make more changes
2. **Identify last working state** - check git log
3. **Rollback:** `git checkout <last-good-commit>`
4. **Test:** Verify working
5. **Review what broke:** Understand the issue
6. **Try again:** With better understanding

---

## Getting Help

**Stuck on a task?**
- Check full details: [PRE_REFACTORING_PLAN.md](PRE_REFACTORING_PLAN.md)
- Review relevant docs: [README.md](README.md), [MASTER_DOCUMENTATION_GUIDE.md](MASTER_DOCUMENTATION_GUIDE.md)
- Check analysis files: [TASK_5_QUICK_REFERENCE.md](TASK_5_QUICK_REFERENCE.md), [analysis/ANALYSIS_SUMMARY_FINAL.md](analysis/ANALYSIS_SUMMARY_FINAL.md)
- Review constants guide: [CONSTANTS_MAPPING_GUIDE.md](CONSTANTS_MAPPING_GUIDE.md)

**Tests failing?**
- Check test output for specific error
- Verify imports are correct
- Check if function signatures changed
- Review git diff for unintended changes

**Agent not following protocol?**
- Review [AGENT_EXECUTION_PROTOCOL.md](AGENT_EXECUTION_PROTOCOL.md)
- Demand verification for every claim
- Stop at checkpoints, require approval
- Challenge unverified work

**Don't know how to proceed?**
- Review documentation thoroughly
- Start with smallest possible change
- Test frequently (after every change)
- Document what you're doing

---

## Important Reminders for Agent Execution

**Before starting ANY task, agent must:**
1. Read full task description
2. Create TodoWrite checklist
3. Show understanding to user
4. Wait for approval

**After EVERY change, agent must:**
1. Show verification (grep/test output)
2. Update TodoWrite progress
3. Run tests

**At EVERY checkpoint, agent must:**
1. Stop and summarize work
2. Show evidence
3. Wait for user approval

**See:** [AGENT_EXECUTION_PROTOCOL.md](AGENT_EXECUTION_PROTOCOL.md) for complete requirements

---

**Last Updated:** 2025-10-19 (Evening)
**Status:** Enhanced with Phase 1.5 and checkpoints
**Ready to Begin:** Phase 1, Task 1.4 (Testing Infrastructure)
