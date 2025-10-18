# TEG Codebase Documentation - Master Coordination Guide

**Project:** Golf Tournament Analysis App Refactoring
**Phase:** Complete Codebase Documentation
**Status:** 🚧 READY TO START
**Last Updated:** 2025-10-17

---

## Purpose

This guide coordinates the complete, exhaustive documentation of the TEG codebase before any refactoring begins. It organizes 5 parallel documentation tasks that can be completed independently by Claude Code subagents or manually.

---

## Documentation Philosophy

> **"We don't know what we don't know until we document everything."**

Before moving a single line of code:
1. ✅ Document what exists
2. ✅ Understand dependencies  
3. ✅ Identify duplicates
4. ✅ Plan the migration
5. ❌ **DO NOT** start refactoring yet

---

## Task Overview

### Task 1: Utils.py Function Inventory 🔴 CRITICAL
**File:** `TASK_1_UTILS_INVENTORY.md`
**Owner:** Subagent 1
**Time:** 4-6 hours
**Output:** `UTILS_INVENTORY.md`

**What:** Document every function in utils.py (~2000 lines, 50-100+ functions)
**Why:** Utils.py is the heart of the current mess - must understand it completely
**Priority:** Start FIRST - other tasks depend on this

### Task 2: Helper Modules Inventory 🔴 CRITICAL
**File:** `TASK_2_HELPERS_INVENTORY.md`
**Owner:** Subagent 2
**Time:** 3-4 hours
**Output:** `HELPERS_INVENTORY.md`

**What:** Document all helper modules (~10 files)
**Why:** Helpers contain domain-specific logic that's migration-ready
**Priority:** Can start IN PARALLEL with Task 1

### Task 3: Streamlit Pages Inventory 🟡 HIGH
**File:** `TASK_3_PAGES_INVENTORY.md`
**Owner:** Subagent 3
**Time:** 4-5 hours
**Output:** `PAGES_INVENTORY.md`

**What:** Document all 30+ page files
**Why:** Need to understand what pages use and what they embed
**Priority:** Can start IN PARALLEL with Tasks 1 & 2

### Task 4: Dependency Map 🟡 HIGH
**File:** `TASK_4_DEPENDENCY_MAP.md`
**Owner:** Subagent 4
**Time:** 3-4 hours
**Output:** `DEPENDENCIES.md`, `dependency_graph.json`

**What:** Map all imports, function calls, and dependencies
**Why:** Must understand ripple effects before changing anything
**Priority:** Start AFTER Tasks 1, 2, 3 are ~50% complete

### Task 5: Duplication Analysis 🟢 MEDIUM
**File:** `TASK_5_DUPLICATION_ANALYSIS.md`
**Owner:** Subagent 5
**Time:** 3-4 hours
**Output:** `DUPLICATES.md`, `consolidation_roadmap.md`

**What:** Find all duplicate and similar functions
**Why:** Eliminate duplication during migration
**Priority:** Start AFTER Tasks 1 & 2 are complete

---

## Task Dependencies

```
Timeline:

Day 1:
├─ Task 1: Utils.py [Start Hour 0] ═════════════════════════════> [6 hours]
├─ Task 2: Helpers  [Start Hour 0] ════════════════════> [4 hours]
└─ Task 3: Pages    [Start Hour 0] ═════════════════════════> [5 hours]

Day 2:
├─ Task 4: Dependencies [Start after T1,T2,T3 at 50%] ═════════> [4 hours]
└─ Task 5: Duplicates   [Start after T1,T2 complete] ══════════> [4 hours]

Total: 2 days with parallel work
```

**Critical Path:** Task 1 → Task 4 → Task 5
**Parallelizable:** Tasks 1, 2, 3 can run simultaneously

---

## How to Execute with Claude Code Subagents

### Option A: Full Automation (Claude Code)

```bash
# Open 5 terminal windows with Claude Code

# Terminal 1
claude code --file TASK_1_UTILS_INVENTORY.md

# Terminal 2  
claude code --file TASK_2_HELPERS_INVENTORY.md

# Terminal 3
claude code --file TASK_3_PAGES_INVENTORY.md

# Terminal 4 (wait for 1,2,3 to be 50% complete)
claude code --file TASK_4_DEPENDENCY_MAP.md

# Terminal 5 (wait for 1,2 to complete)
claude code --file TASK_5_DUPLICATION_ANALYSIS.md
```

### Option B: Semi-Automated (Mix)

Assign tasks based on capability:
- **Automated:** Tasks 4 & 5 (code analysis)
- **Manual:** Tasks 1, 2, 3 (need human judgment)

### Option C: Fully Manual

Follow each TASK file as a checklist and document manually.

---

## Progress Tracking

### Task 1: Utils.py Inventory
- [ ] Functions 1-20 documented
- [ ] Functions 21-40 documented
- [ ] Functions 41-60 documented
- [ ] Functions 61-80 documented
- [ ] All remaining functions documented
- [ ] Constants documented
- [ ] Dependencies analyzed
- [ ] Migration targets assigned
- [ ] COMPLETE ✅

### Task 2: Helpers Inventory
- [ ] scoring_data_processing.py
- [ ] scoring_achievements_processing.py
- [ ] streak_analysis_processing.py
- [ ] score_count_processing.py
- [ ] display_helpers.py
- [ ] latest_round_processing.py
- [ ] data_update_processing.py
- [ ] data_deletion_processing.py
- [ ] commentary_generator.py
- [ ] All other helpers
- [ ] COMPLETE ✅

### Task 3: Pages Inventory
- [ ] History section pages
- [ ] Records section pages
- [ ] Analysis section pages
- [ ] Latest section pages
- [ ] Data section pages
- [ ] Special pages
- [ ] COMPLETE ✅

### Task 4: Dependencies
- [ ] File-level dependencies
- [ ] Function-level dependencies
- [ ] Dependency matrix
- [ ] Critical path analysis
- [ ] Circular dependency check
- [ ] Migration impact analysis
- [ ] COMPLETE ✅

### Task 5: Duplicates
- [ ] Exact duplicates found
- [ ] Near duplicates found
- [ ] Functional duplicates found
- [ ] Pattern duplicates found
- [ ] Consolidation recommendations
- [ ] Priority matrix created
- [ ] COMPLETE ✅

---

## Output Files Expected

After all tasks complete, you should have:

### Core Documentation
1. `CODEBASE_INVENTORY.md` - Master overview (this file)
2. `UTILS_INVENTORY.md` - Complete utils.py documentation
3. `HELPERS_INVENTORY.md` - All helper modules
4. `PAGES_INVENTORY.md` - All page files
5. `DEPENDENCIES.md` - Complete dependency map
6. `DUPLICATES.md` - Duplication analysis

### Supporting Files
7. `dependency_graph.json` - Machine-readable dependencies
8. `consolidation_roadmap.md` - Duplicate consolidation plan
9. `migration_matrix.csv` - Migration planning spreadsheet
10. `duplicate_matrix.csv` - Duplicate tracking spreadsheet

### Optional Visuals
11. `dependency_graph.png` - Visual dependency diagram
12. `data_flow.png` - Data flow diagram

---

## Quality Checks

Before considering documentation "complete":

### Completeness Check
- ✅ Every Python file documented
- ✅ Every function documented
- ✅ Every import tracked
- ✅ Every dependency mapped
- ✅ Every duplicate identified

### Accuracy Check
- ✅ Function signatures correct
- ✅ Dependencies verified (not assumed)
- ✅ Line numbers accurate
- ✅ Usage counts validated

### Usefulness Check
- ✅ Migration targets recommended
- ✅ Priorities assigned
- ✅ Effort estimates included
- ✅ Blockers identified

---

## What Happens After Documentation?

Once all 5 tasks are complete:

### Phase 1: Review & Analysis
1. Review all documentation
2. Hold planning session
3. Identify any gaps
4. Validate recommendations

### Phase 2: Strategic Planning
1. Design final module structure
2. Create migration order
3. Plan breaking changes
4. Set up tests

### Phase 3: Migration Execution
1. Start with data loaders (core)
2. Move domain logic (analysis)
3. Update all imports
4. Test continuously

**DO NOT PROCEED TO PHASE 3 UNTIL DOCUMENTATION IS 100% COMPLETE**

---

## Critical Success Factors

### ✅ DO:
- Document EVERYTHING (no exceptions)
- Be thorough over fast
- Validate all claims (don't assume)
- Note uncertainties
- Ask questions when unclear

### ❌ DON'T:
- Skip "obvious" functions
- Assume similar functions are identical
- Guess at dependencies
- Start refactoring yet
- Miss edge cases

---

## Communication Protocol

### Daily Standup Questions
1. What task(s) are you working on?
2. What percentage complete?
3. Any blockers or questions?
4. Any unexpected findings?
5. ETA for completion?

### Reporting Template

```markdown
## Daily Update: [Date]

**Task:** [Task number and name]
**Progress:** XX% complete
**Completed Today:**
- [Item 1]
- [Item 2]

**In Progress:**
- [Item 1]

**Blockers:**
- [None / List blockers]

**Findings:**
- [Any interesting discoveries]

**ETA:** [Date/Time]
```

---

## Risk Management

### Known Risks

#### Risk 1: Incomplete Documentation
**Impact:** High - Bad decisions based on incomplete info
**Mitigation:** Triple-check completeness, peer review

#### Risk 2: Incorrect Dependencies
**Impact:** High - Break things during migration
**Mitigation:** Test imports, validate with actual code execution

#### Risk 3: Missed Duplicates
**Impact:** Medium - Consolidate less than possible
**Mitigation:** Use automated tools, manual review

#### Risk 4: Time Overrun
**Impact:** Low - Documentation takes longer than estimated
**Mitigation:** Acceptable - thoroughness > speed

#### Risk 5: Scope Creep
**Impact:** Medium - Start refactoring before documentation done
**Mitigation:** Strict discipline - documentation ONLY

---

## Next Steps

### Immediate (Now)
1. ✅ Read this coordination guide
2. ✅ Read all 5 task files
3. ✅ Decide on execution approach (automated/manual/mixed)
4. ✅ Assign ownership to tasks
5. ✅ Set up communication protocol

### Short-term (Today)
1. 🚀 Start Tasks 1, 2, 3 in parallel
2. 📝 First progress update in 2 hours
3. 📝 Daily standup scheduled

### Medium-term (This Week)
1. Complete Tasks 1, 2, 3
2. Start Tasks 4, 5
3. Complete all tasks
4. Review documentation
5. Plan Phase 2

---

## Questions & Clarifications

Before starting, clarify:

1. **Who is doing what?**
   - Claude Code subagents?
   - Manual documentation?
   - Mixed approach?

2. **What's the timeline?**
   - How quickly do we need this?
   - Any deadlines?

3. **What level of detail?**
   - Every function? (Yes)
   - Every line? (No, but function-level)
   - Every parameter? (Yes)

4. **Where to document?**
   - GitHub repo?
   - Shared drive?
   - Local files?

---

## Resources

### Task Files
- `TASK_1_UTILS_INVENTORY.md`
- `TASK_2_HELPERS_INVENTORY.md`
- `TASK_3_PAGES_INVENTORY.md`
- `TASK_4_DEPENDENCY_MAP.md`
- `TASK_5_DUPLICATION_ANALYSIS.md`

### Current Project Files
- `streamlit/REFACTORING_TEMPLATE.md` - Refactoring guide (for reference)
- `streamlit/utils.py` - The beast we're documenting
- `streamlit/helpers/` - Helper modules
- `streamlit/pages/` - All page files

### Tools
- grep, sed, awk - Text processing
- Python AST - Code analysis
- pylint, radon - Code metrics
- Claude Code - Automation

---

## Conclusion

**This documentation phase is the foundation for successful refactoring.**

Take the time to do it right. No shortcuts. Every function, every dependency, every duplicate.

Once complete, we'll have a perfect map of the codebase and can refactor with confidence.

**Ready to begin? Pick a task and start documenting!**

---

**Last Updated:** 2025-10-17
**Next Review:** After Task 1, 2, 3 complete
