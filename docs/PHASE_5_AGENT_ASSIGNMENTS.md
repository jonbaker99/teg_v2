# Phase 5: Agent Task Assignments

**For Parallel Execution by Multiple Agents**

---

## 🎯 EXECUTION WAVES

### Wave 1: Foundation (Parallel Execution)

**Agent A: Clean Analysis Layer**
- **Task:** Remove UI from teg_analysis
- **Files:** 5 analysis modules
- **Time:** 2-3 hours
- **Document:** [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md#task-1)
- **Dependencies:** None
- **Deliverables:**
  - [ ] Zero `st.*` calls in teg_analysis
  - [ ] Zero `import streamlit` in teg_analysis
  - [ ] All UI extracted to utils.py wrappers
  - [ ] Package imports successfully

**Agent B: Migrate Core Functions**
- **Task:** Migrate 13 functions to core/
- **Files:** core/data_loader.py, core/transformations.py, new core/metadata.py
- **Time:** 1.5-2 hours
- **Document:** [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md#task-2)
- **Dependencies:** None (different files than Agent A)
- **Deliverables:**
  - [ ] 5 functions in core/data_loader.py
  - [ ] 8 functions in core/transformations.py
  - [ ] 3 functions in new core/metadata.py
  - [ ] All imports work

**Agent C: Migrate Analysis Functions**
- **Task:** Migrate 15 functions to analysis/
- **Files:** analysis/aggregation.py, analysis/pipeline.py
- **Time:** 1.5-2 hours
- **Document:** [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md#task-2)
- **Dependencies:** None (different files than Agent A)
- **Deliverables:**
  - [ ] 12 functions in aggregation.py
  - [ ] 3 functions in pipeline.py
  - [ ] All imports work

**Agent D: Migrate Display Functions**
- **Task:** Migrate 8 navigation functions
- **Files:** New display/navigation.py
- **Time:** 1 hour
- **Document:** [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md#task-2)
- **Dependencies:** None
- **Deliverables:**
  - [ ] Create display/navigation.py
  - [ ] 8 navigation functions migrated
  - [ ] All imports work

---

### Wave 2: Consolidation (Wait for Wave 1)

**Agent E: Deduplicate Functions**
- **Task:** Remove 20+ duplicate functions
- **Files:** utils.py, all teg_analysis modules
- **Time:** 1-2 hours
- **Document:** [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md#task-3)
- **Dependencies:** Agents A, B, C complete
- **Deliverables:**
  - [ ] 20+ duplicates removed from utils.py
  - [ ] Simple imports/wrappers in utils.py
  - [ ] All pages still work

**Agent F: Create Wrapper Layer**
- **Task:** Transform utils.py into wrapper layer
- **Files:** streamlit/utils.py
- **Time:** 2-3 hours
- **Document:** [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md#task-4)
- **Dependencies:** Agent E complete
- **Deliverables:**
  - [ ] utils.py down to ~50 functions
  - [ ] Cached wrappers created
  - [ ] UI wrappers from Agent A integrated
  - [ ] All imports work

---

### Wave 3: Page Updates (Wait for Wave 2)

**Agent G: Update Pages Batch 1**
- **Task:** Update 14 pages (simple data pages)
- **Files:** ave_by_*.py, course_details.py, etc.
- **Time:** 1-1.5 hours
- **Document:** [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md#task-5)
- **Dependencies:** Agent F complete
- **Page List:**
  1. ave_by_course.py
  2. ave_by_par.py
  3. ave_by_teg.py
  4. course_details.py
  5. frontback.py
  6. handicap_history.py
  7. handicaps_2.py
  8. hole_by_hole.py
  9. hole_by_hole_data.py
  10. holes_per_score.py
  11. net_vs_gross.py
  12. player_head2head.py
  13. round_details.py
  14. teg_details.py

**Agent H: Update Pages Batch 2**
- **Task:** Update 15 pages (analysis pages)
- **Files:** scoring.py, bestball.py, etc.
- **Time:** 1.5-2 hours
- **Document:** [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md#task-5)
- **Dependencies:** Agent F complete
- **Page List:**
  1. 400scoring.py
  2. bestball.py
  3. best_eclectics.py
  4. biggest_changes.py
  5. comebacks.py
  6. comebacks_full_teg.py
  7. courses_analysis.py
  8. eagles.py
  9. holes_in_one.py
  10. latest_round.py
  11. latest_teg.py
  12. par_performance.py
  13. scoring_achievements.py
  14. scoring_counts.py
  15. streaks.py

**Agent I: Update Pages Batch 3**
- **Task:** Update 14 pages (records + history)
- **Files:** Records pages, history pages
- **Time:** 1.5-2 hours
- **Document:** [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md#task-5)
- **Dependencies:** Agent F complete
- **Page List:**
  1. 300TEG Records.py
  2. 301Best_TEGs_and_Rounds.py
  3. 302Personal Best Rounds & TEGs.py
  4. 303Final Round Comebacks.py
  5. personal_bests.py
  6. personal_worsts.py
  7. rounds_rankings.py
  8. teg_rankings.py
  9. 101TEG History.py
  10. 101TEG Honours Board.py
  11. 102TEG Results.py
  12. leaderboard.py
  13. latest_teg_2.py
  14. scorecard_v2.py

**Agent J: Update Pages Batch 4**
- **Task:** Update 14 pages (admin + misc)
- **Files:** Data update, admin, misc
- **Time:** 1.5-2 hours
- **Document:** [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md#task-5)
- **Dependencies:** Agent F complete
- **Page List:**
  1. 1000Data update.py
  2. 1001Report Generation.py
  3. 9999_generate_caches.py
  4. admin_volume_management.py
  5. delete_data.py
  6. nav.py
  7. 500Handicaps.py
  8. chosen_rd.py
  9. chosen_teg.py
  10. graph_testing.py
  11. multi_rounds.py
  12. summary.py
  13. winners.py
  14. (any remaining pages)

---

### Wave 4: Validation (Wait for Wave 3)

**Agent K: Testing & Validation**
- **Task:** Comprehensive testing
- **Files:** Test scripts
- **Time:** 2-3 hours
- **Document:** [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md#task-6)
- **Dependencies:** Agents G, H, I, J complete
- **Deliverables:**
  - [ ] test_independence.py passes
  - [ ] test_fastapi.py works
  - [ ] test_performance.py results
  - [ ] All 57 pages tested
  - [ ] Validation report

**Agent L: Documentation**
- **Task:** Create final documentation
- **Files:** docs/
- **Time:** 1-2 hours
- **Document:** [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md#task-7)
- **Dependencies:** Agent K complete
- **Deliverables:**
  - [ ] ARCHITECTURE.md
  - [ ] PHASE_5_COMPLETION.md
  - [ ] API_REFERENCE.md
  - [ ] ALTERNATIVE_UIS.md

---

## 📊 PROGRESS TRACKING

### Before Starting
```bash
# Baseline measurements
import_test=$(python -c "import teg_analysis; print('OK')" 2>&1)
st_imports=$(grep -r "import streamlit" teg_analysis/ | wc -l)
st_calls=$(grep -r "st\." teg_analysis/analysis/ | wc -l)
utils_funcs=$(grep -c "^def " streamlit/utils.py)

echo "Baseline:"
echo "- teg_analysis imports: $import_test"
echo "- Streamlit imports: $st_imports (target: 0)"
echo "- st.* calls: $st_calls (target: 0)"
echo "- utils.py functions: $utils_funcs (target: ~50)"
```

### Agent Status Table

| Agent | Wave | Task | Status | Progress | Complete |
|-------|------|------|--------|----------|----------|
| A | 1 | Clean Analysis | 📋 Ready | 0/5 files | ❌ |
| B | 1 | Migrate Core | 📋 Ready | 0/13 funcs | ❌ |
| C | 1 | Migrate Analysis | 📋 Ready | 0/15 funcs | ❌ |
| D | 1 | Migrate Display | 📋 Ready | 0/8 funcs | ❌ |
| E | 2 | Deduplicate | ⏸️ Wait | 0/20 funcs | ❌ |
| F | 2 | Wrapper Layer | ⏸️ Wait | 0/1 files | ❌ |
| G | 3 | Update Batch 1 | ⏸️ Wait | 0/14 pages | ❌ |
| H | 3 | Update Batch 2 | ⏸️ Wait | 0/15 pages | ❌ |
| I | 3 | Update Batch 3 | ⏸️ Wait | 0/14 pages | ❌ |
| J | 3 | Update Batch 4 | ⏸️ Wait | 0/14 pages | ❌ |
| K | 4 | Testing | ⏸️ Wait | 0/5 tests | ❌ |
| L | 4 | Documentation | ⏸️ Wait | 0/4 docs | ❌ |

### Wave Completion Gates

**Wave 1 → Wave 2:**
- [ ] Agent A complete (Analysis cleaned)
- [ ] Agent B complete (Core migrated)
- [ ] Agent C complete (Analysis migrated)
- [ ] Agent D complete (Display migrated)
- [ ] All imports work
- [ ] No st.* in teg_analysis

**Wave 2 → Wave 3:**
- [ ] Agent E complete (Deduplicated)
- [ ] Agent F complete (Wrapper layer)
- [ ] utils.py has ~50 functions
- [ ] Test page works

**Wave 3 → Wave 4:**
- [ ] Agent G complete (Batch 1)
- [ ] Agent H complete (Batch 2)
- [ ] Agent I complete (Batch 3)
- [ ] Agent J complete (Batch 4)
- [ ] All 57 pages tested

---

## 🔄 COORDINATION PROTOCOL

### Communication

**Start of Each Wave:**
1. Wave leader announces wave start
2. Each agent confirms task received
3. Agents begin work in parallel

**During Work:**
1. Agents post updates every 30-60 minutes
2. Report blockers immediately
3. Mark files as "in progress" to avoid conflicts

**End of Task:**
1. Agent marks task complete
2. Agent posts completion checklist
3. Agent commits code with clear message

### Conflict Resolution

**If File Conflicts:**
1. Agent with higher priority (earlier wave) wins
2. Losing agent merges and retests
3. Report to coordinator

**If Blockers:**
1. Post blocker with details
2. Check [PHASE_5_CONTEXT.md](PHASE_5_CONTEXT.md) for answers
3. Ask coordinator if unclear

### Git Strategy

```bash
# Each agent creates feature branch
git checkout -b phase-5-task-{agent-letter}

# Work and commit frequently
git add .
git commit -m "Phase 5 Task {X}: {description}"

# When complete, push
git push origin phase-5-task-{agent-letter}

# Coordinator merges in order
```

---

## ✅ FINAL VALIDATION CHECKLIST

After ALL agents complete:

```bash
# Run comprehensive validation
./scripts/validate_phase_5.sh

# Manual checks:
# 1. Import test
python -c "import teg_analysis; print('✓')"

# 2. No Streamlit dependencies
grep -r "import streamlit" teg_analysis/ | wc -l  # = 0

# 3. Function count
grep -c "^def " streamlit/utils.py  # ≈ 50

# 4. All pages work
for page in streamlit/*.py; do
    echo "Testing $page..."
    timeout 5 streamlit run "$page" --server.headless true
done

# 5. Alternative UI works
python test_independence.py  # SUCCESS

# 6. Performance OK
python test_performance.py  # < 10s
```

---

## 🎉 SUCCESS CRITERIA

Phase 5 is complete when:

- [ ] **teg_analysis is UI-independent** (no Streamlit imports)
- [ ] **All 57 pages work** (manual testing passes)
- [ ] **Alternative UI example works** (FastAPI or Jupyter)
- [ ] **Performance maintained** (< 10% regression)
- [ ] **Documentation complete** (4 docs created)
- [ ] **Tests pass** (all validation tests green)
- [ ] **User can use teg_analysis with any framework**

---

## 📞 SUPPORT

**Questions?**
1. Check [PHASE_5_CONTEXT.md](PHASE_5_CONTEXT.md) first
2. Review [PHASE_5_TASKS_SUMMARY.md](PHASE_5_TASKS_SUMMARY.md)
3. Search existing code for patterns
4. Ask coordinator with specific details

**Common Issues:**
- Import errors → Check Python path
- Function not found → Check it was migrated
- Page breaks → Check utils.py has wrapper
- Test fails → Check test expectations updated

---

**STATUS:** 📋 **READY FOR AGENT ASSIGNMENT**
**NEXT:** Assign agents and begin Wave 1
