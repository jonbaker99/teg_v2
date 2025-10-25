# Phase 5 Multi-Agent Execution Prompt

**Copy this prompt to start Phase 5 execution with multiple agents**

---

## 🚀 PROMPT FOR AGENT COORDINATION

```markdown
# Phase 5: Complete UI Independence - Multi-Agent Execution

## Mission
Transform the TEG analysis system to have a pure, framework-agnostic calculation core (teg_analysis) that works with ANY UI framework, while maintaining the existing Streamlit application.

## Current State
- **Location:** c:\Users\jonba\Documents\Projects - not on onedrive\teg_v2
- **Status:** Phase III & IV complete (202 functions migrated)
- **Problem:** teg_analysis still has Streamlit dependencies (23 imports, 42 st.* calls)
- **Goal:** Make teg_analysis completely UI-independent

## Documentation Available
ALL documentation is complete and ready in the `docs/` folder:

1. **PHASE_5_MASTER_PLAN.md** - Overview and coordination (READ FIRST)
2. **PHASE_5_CONTEXT.md** - Background, architecture, patterns (MUST READ)
3. **PHASE_5_TASKS_SUMMARY.md** - Step-by-step execution guide
4. **PHASE_5_AGENT_ASSIGNMENTS.md** - Agent tasks and coordination
5. **PHASE_5_DOCUMENTATION_INDEX.md** - Navigation and quick reference

## Execution Strategy: 4-Wave Parallel Execution

### Wave 1: Foundation (Agents A, B, C, D - Run in Parallel)

**Agent A: Clean Analysis Layer**
- **Task:** Remove all Streamlit dependencies from teg_analysis
- **Document:** docs/PHASE_5_TASKS_SUMMARY.md → Task 1
- **Files:** 5 analysis modules (aggregation.py, pipeline.py, records.py, scoring.py, streaks.py)
- **Actions:**
  - Remove 42 `st.*` calls
  - Remove 23 `import streamlit` statements
  - Extract UI logic to utils.py wrappers
  - Replace st.error() with exceptions
- **Time:** 2-3 hours
- **Deliverable:** Zero Streamlit dependencies in teg_analysis
- **Validation:** `grep -r "import streamlit" teg_analysis/` returns 0 results

**Agent B: Migrate Core Functions**
- **Task:** Migrate 13 functions from utils.py to core/
- **Document:** docs/PHASE_5_TASKS_SUMMARY.md → Task 2 (sections 2.1, 2.2, 2.5)
- **Files:** core/data_loader.py, core/transformations.py, NEW core/metadata.py
- **Actions:**
  - Migrate 5 functions to data_loader.py
  - Migrate 8 functions to transformations.py
  - Create and populate new metadata.py with 3 functions
- **Time:** 1.5-2 hours
- **Deliverable:** 13 functions migrated, all imports work

**Agent C: Migrate Analysis Functions**
- **Task:** Migrate 15 functions from utils.py to analysis/
- **Document:** docs/PHASE_5_TASKS_SUMMARY.md → Task 2 (sections 2.3, 2.4)
- **Files:** analysis/aggregation.py, analysis/pipeline.py
- **Actions:**
  - Migrate 12 functions to aggregation.py
  - Migrate 3 functions to pipeline.py
- **Time:** 1.5-2 hours
- **Deliverable:** 15 functions migrated, all imports work

**Agent D: Migrate Display Functions**
- **Task:** Migrate 8 navigation functions from utils.py
- **Document:** docs/PHASE_5_TASKS_SUMMARY.md → Task 2 (section 2.6)
- **Files:** NEW display/navigation.py
- **Actions:**
  - Create new display/navigation.py
  - Migrate 8 navigation/trophy functions
- **Time:** 1 hour
- **Deliverable:** New module with 8 functions, all imports work

**Wave 1 Completion Gate:**
- [ ] All 4 agents report complete
- [ ] `python -c "import teg_analysis; print('OK')"` works
- [ ] Zero `st.*` calls in teg_analysis
- [ ] All new functions import successfully

---

### Wave 2: Consolidation (Agents E, F - Wait for Wave 1)

**Agent E: Deduplicate Functions**
- **Task:** Remove 20+ duplicate functions between utils.py and teg_analysis
- **Document:** docs/PHASE_5_TASKS_SUMMARY.md → Task 3
- **Depends on:** Agents A, B, C complete
- **Actions:**
  - Identify all duplicates
  - Keep teg_analysis version
  - Replace utils.py duplicates with simple imports/wrappers
- **Time:** 1-2 hours
- **Deliverable:** 20+ duplicates removed, pages still work

**Agent F: Create Wrapper Layer**
- **Task:** Transform streamlit/utils.py into thin Streamlit wrapper
- **Document:** docs/PHASE_5_TASKS_SUMMARY.md → Task 4
- **Depends on:** Agent E complete
- **Actions:**
  - Restructure utils.py (~100 functions → ~50 functions)
  - Add @st.cache_data wrappers
  - Add error display wrappers from Agent A's UI extractions
  - Keep I/O, cache, CSS functions
- **Time:** 2-3 hours
- **Deliverable:** Clean utils.py with ~50 functions, all wrappers work

**Wave 2 Completion Gate:**
- [ ] Agents E and F report complete
- [ ] `grep -c "^def " streamlit/utils.py` returns ~50
- [ ] Test page works: `streamlit run streamlit/101TEG\ History.py`
- [ ] No breaking changes

---

### Wave 3: Page Updates (Agents G, H, I, J - Wait for Wave 2)

**Agent G: Update Pages Batch 1**
- **Task:** Update 14 pages (simple data pages)
- **Document:** docs/PHASE_5_TASKS_SUMMARY.md → Task 5
- **Depends on:** Agent F complete
- **Pages:** ave_by_course.py, ave_by_par.py, ave_by_teg.py, course_details.py, frontback.py, handicap_history.py, handicaps_2.py, hole_by_hole*.py, net_vs_gross.py, player_head2head.py, round_details.py, teg_details.py
- **Time:** 1-1.5 hours

**Agent H: Update Pages Batch 2**
- **Task:** Update 15 pages (analysis pages)
- **Document:** docs/PHASE_5_TASKS_SUMMARY.md → Task 5
- **Depends on:** Agent F complete
- **Pages:** 400scoring.py, bestball.py, best_eclectics.py, biggest_changes.py, comebacks*.py, courses_analysis.py, eagles.py, holes_in_one.py, latest_*.py, par_performance.py, scoring_*.py, streaks.py
- **Time:** 1.5-2 hours

**Agent I: Update Pages Batch 3**
- **Task:** Update 14 pages (records + history)
- **Document:** docs/PHASE_5_TASKS_SUMMARY.md → Task 5
- **Depends on:** Agent F complete
- **Pages:** 300-303 series, personal_*.py, *_rankings.py, 101-102 series, leaderboard.py, scorecard_v2.py
- **Time:** 1.5-2 hours

**Agent J: Update Pages Batch 4**
- **Task:** Update 14 pages (admin + misc)
- **Document:** docs/PHASE_5_TASKS_SUMMARY.md → Task 5
- **Depends on:** Agent F complete
- **Pages:** 1000-1001 series, 9999_generate_caches.py, admin_*.py, delete_data.py, nav.py, 500Handicaps.py, chosen_*.py, remaining pages
- **Time:** 1.5-2 hours

**Per-page actions (all agents):**
1. Update imports (add `_cached` suffix where applicable)
2. Update function calls
3. Test page loads and functions correctly
4. Mark complete in tracking

**Wave 3 Completion Gate:**
- [ ] All 4 agents (G, H, I, J) report complete
- [ ] All 57 pages updated
- [ ] Sample pages tested and working
- [ ] No import errors

---

### Wave 4: Validation (Agents K, L - Wait for Wave 3)

**Agent K: Testing & Validation**
- **Task:** Comprehensive testing and validation
- **Document:** docs/PHASE_5_TASKS_SUMMARY.md → Task 6
- **Depends on:** Agents G, H, I, J complete
- **Actions:**
  - Create and run test_independence.py
  - Create and run test_fastapi.py example
  - Run test_performance.py benchmarks
  - Test all 57 pages (sample testing)
  - Create validation report
- **Time:** 2-3 hours
- **Deliverable:** All tests pass, validation report complete

**Agent L: Documentation**
- **Task:** Create final documentation
- **Document:** docs/PHASE_5_TASKS_SUMMARY.md → Task 7
- **Depends on:** Agent K complete
- **Actions:**
  - Create ARCHITECTURE.md
  - Create PHASE_5_COMPLETION.md
  - Create API_REFERENCE.md
  - Create ALTERNATIVE_UIS.md
- **Time:** 1-2 hours
- **Deliverable:** 4 documentation files complete

---

## Success Criteria

Phase 5 is complete when ALL of these pass:

```bash
# 1. Import test
python -c "import teg_analysis; print('✓ Package imports')"

# 2. No Streamlit in core
grep -r "import streamlit" teg_analysis/ | wc -l  # Must equal 0

# 3. No st.* calls
grep -r "st\." teg_analysis/analysis/ | wc -l  # Must equal 0

# 4. Function count reduced
grep -c "^def " streamlit/utils.py  # Should be ~50 (down from 100)

# 5. Streamlit app works
streamlit run streamlit/nav.py  # Manual test - should work

# 6. Independence test passes
python test_independence.py  # Should print "SUCCESS"

# 7. Performance acceptable
python test_performance.py  # Should be < 10s
```

---

## Coordination Protocol

### Before Starting
1. Each agent confirms receipt of assignment
2. Read assigned task document section
3. Read PHASE_5_CONTEXT.md for patterns
4. Create feature branch: `git checkout -b phase-5-task-{agent-letter}`

### During Work
1. Post updates every 30-60 minutes
2. Mark files "in progress" to avoid conflicts
3. Report blockers immediately
4. Commit frequently with clear messages

### After Completion
1. Mark task complete with checklist
2. Push branch: `git push origin phase-5-task-{agent-letter}`
3. Notify dependent agents
4. Stand by for validation

### Wave Gates
- **Wave 1 → Wave 2:** All Wave 1 agents complete + validation passes
- **Wave 2 → Wave 3:** All Wave 2 agents complete + test page works
- **Wave 3 → Wave 4:** All Wave 3 agents complete + sample tests pass
- **Wave 4 → Done:** All tests pass + documentation complete

---

## Quick Reference

**Timeline:**
- Wave 1: 2-3 hours
- Wave 2: 2-3 hours
- Wave 3: 1.5-2 hours
- Wave 4: 2-3 hours
- **Total: 8-12 hours (wall time)**

**Key Files:**
- `teg_analysis/` - Pure calculations (no UI)
- `streamlit/utils.py` - Streamlit wrappers
- `streamlit/*.py` - UI pages (57 files)

**Validation Commands:**
```bash
# Check imports
python -c "import teg_analysis; print('OK')"

# Check no Streamlit
grep -r "import streamlit" teg_analysis/

# Check function count
grep -c "^def " streamlit/utils.py

# Test app
streamlit run streamlit/nav.py
```

---

## Start Execution

**Coordinator:** Assign agents A-D to Wave 1 tasks and begin execution.

**All Agents:**
1. Read your assignment above
2. Read docs/PHASE_5_CONTEXT.md for patterns
3. Read your specific task section in docs/PHASE_5_TASKS_SUMMARY.md
4. Create your feature branch
5. Begin work
6. Report progress regularly

**Ready to execute Phase 5!** 🚀
```

---

## 📋 USAGE INSTRUCTIONS

### How to Use This Prompt

1. **Copy the entire prompt** from the code block above
2. **Start a new agent session** or multi-agent coordination tool
3. **Paste the prompt** to initiate execution
4. **Agents automatically coordinate** through the wave system

### Alternative: Use as Template

You can also:
- Send to individual agents (extract their specific section)
- Use for sequential execution (follow agent order A→B→C...)
- Adapt for your specific agent coordination system

---

## ✅ What This Prompt Provides

- **Complete context** - No additional explanation needed
- **Clear assignments** - Each agent knows their task
- **Coordination built-in** - Wave gates prevent conflicts
- **Validation steps** - Success criteria at every stage
- **Time estimates** - Realistic planning
- **Dependencies mapped** - Agents know when they can start
- **Success criteria** - Clear definition of done

---

## 🎯 Expected Outcome

After executing with this prompt:
- ✅ teg_analysis is completely UI-independent
- ✅ All 57 Streamlit pages work correctly
- ✅ Can use teg_analysis with ANY framework
- ✅ Complete documentation delivered
- ✅ All tests pass

**Total time: 8-12 hours (wall time) with parallel execution**

---

**Status:** ✅ **READY TO EXECUTE**
**Next:** Copy prompt and start multi-agent execution
