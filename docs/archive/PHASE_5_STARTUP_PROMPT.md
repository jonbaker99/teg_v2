# Phase 5: Full Refactoring Implementation - Startup Prompt

**Created:** 2025-10-25
**Purpose:** Comprehensive prompt to start Phase 5 refactoring implementation
**Status:** Ready to use

---

## How to Use This Document

When you're ready to begin Phase 5 refactoring:

1. **Copy the appropriate prompt** from the sections below
2. **Paste it into Claude Code** as your starting message
3. **Wait for Claude to confirm understanding** before proceeding
4. **Approve to begin Phase I** when ready

---

## Full Version (Recommended for Fresh Start)

Copy and paste this entire prompt when starting Phase 5:

```
I'm ready to begin Phase 5: Full Refactoring Implementation for the TEG codebase.

PHASE 5 OBJECTIVE:
Execute the complete migration of 254+ functions from the monolithic structure into the new teg_analysis/ package (5 packages, 17 modules) following the phased approach documented in docs/PHASE_4_MIGRATION_EXECUTION_PLAN.md.

EXECUTION REQUIREMENTS:
- Follow STRICT COMPLIANCE with docs/AGENT_EXECUTION_PROTOCOL.md
- Use TodoWrite to track ALL tasks and progress
- Show verification (grep/test output) for EVERY change
- Run tests after EACH phase completion (target: 94/94 passing)
- Commit to git after EACH phase with detailed messages
- Create completion summary after EACH phase
- STOP at all 5 phase checkpoints for review before proceeding

PHASE 5 STRUCTURE (4 Sequential Phases):

PHASE I: I/O Layer Migration (Week 1)
- Migrate 3 modules: volume_operations, file_operations, github_operations
- Migrate 26 functions with no internal dependencies
- Risk Level: LOW
- Rollback Time: 5 minutes

PHASE II: Core Layer Migration (Week 2)
- Migrate 2 modules: data_loader, data_transforms
- Migrate 19 functions (including critical load_all_data)
- Risk Level: MEDIUM (high-impact functions)
- Rollback Time: 10 minutes
- Extra attention to load_all_data() which affects 40+ pages

PHASE III: Analysis Layer Migration (Week 3)
- Migrate 7 modules in order: scoring → rankings → aggregation → streaks → records → commentary → pipeline
- Migrate 91 functions (most complex, interdependent)
- Risk Level: MEDIUM-HIGH
- Rollback Time: 15-30 minutes per module
- CRITICAL: Follow dependency order to avoid import errors

PHASE IV: Display Layer Migration (Week 4)
- Migrate 3 modules: formatters, tables, charts
- Migrate 44 functions (leaf modules, safe to migrate)
- Risk Level: LOW
- Rollback Time: 5-10 minutes

REFERENCE DOCUMENTS:
- Architecture Design: docs/PHASE_4_PACKAGE_STRUCTURE.md
- Function Mapping: docs/PHASE_4_FUNCTION_MAP.md
- Dependencies: docs/PHASE_4_DEPENDENCY_MAP.md
- Execution Plan: docs/PHASE_4_MIGRATION_EXECUTION_PLAN.md
- Complete Summary: docs/COMPLETE_CLEANUP_SUMMARY.md

TESTING REQUIREMENTS:
After each phase:
- [ ] Unit tests for new modules (pass 100%)
- [ ] Integration tests with previous phases (pass 100%)
- [ ] Full regression suite (94 tests, pass 100%)
- [ ] Performance validation (no degradation)
- [ ] Manual smoke test (load pages in streamlit)

SAFETY CHECKLIST (Before Starting):
- [ ] Current branch is 'refactor'
- [ ] All 94 tests passing before starting
- [ ] Git status is clean (no uncommitted changes)
- [ ] Latest docs/PHASE_4_MIGRATION_EXECUTION_PLAN.md reviewed
- [ ] Understanding of phased approach and rollback procedures

EXECUTION PATTERN (For Each Phase):
1. Create teg_analysis/[package]/ directory structure
2. Create new module files with implementations
3. Create/update __init__.py files for public API exports
4. Create temporary wrappers in streamlit/utils.py (for backward compatibility during transition)
5. Update imports in affected pages (gradual cutover)
6. Run all tests (unit → integration → regression → smoke)
7. Verify performance (same or better)
8. Commit with detailed message
9. Create phase completion summary
10. STOP for review before next phase

START WITH PHASE I:
Begin by creating the teg_analysis/ package structure and migrating the I/O layer (volume_operations, file_operations, github_operations).

BEFORE PROCEEDING:
1. Show me your understanding of Phase I scope
2. List all subtasks you'll complete
3. Estimated time for Phase I
4. Success criteria for Phase I

Wait for my approval before beginning Phase I implementation.
```

---

## Quick Reference Version (Resume After Break)

Use this shorter version if you're resuming work and don't need all the background:

```
I'm ready to begin Phase 5: Full Refactoring Implementation.

SCOPE: Migrate 254+ functions into teg_analysis/ package (5 packages, 17 modules) following the 4-phase plan in docs/PHASE_4_MIGRATION_EXECUTION_PLAN.md.

PHASES:
1. Phase I (Week 1): I/O Layer - 3 modules, 26 functions, LOW risk
2. Phase II (Week 2): Core Layer - 2 modules, 19 functions, MEDIUM risk
3. Phase III (Week 3): Analysis Layer - 7 modules, 91 functions, MEDIUM-HIGH risk
4. Phase IV (Week 4): Display Layer - 3 modules, 44 functions, LOW risk

REQUIREMENTS:
- Use TodoWrite for task tracking
- Show verification for each change
- Run full test suite after each phase (target: 94/94 passing)
- Create phase completion summary after each phase
- STOP at each phase checkpoint for review

DOCUMENTS:
- Architecture: docs/PHASE_4_PACKAGE_STRUCTURE.md
- Functions: docs/PHASE_4_FUNCTION_MAP.md
- Plan: docs/PHASE_4_MIGRATION_EXECUTION_PLAN.md

START: Begin with Phase I (I/O Layer). Show me:
1. Your understanding of Phase I scope
2. All subtasks to complete
3. Estimated time
4. Success criteria

Wait for approval before starting.
```

---

## Minimal Version (Very Familiar with Plan)

Use this if you're already very familiar with the plan and just need to trigger the start:

```
Start Phase 5: Full Refactoring Implementation. Execute the 4-phase migration plan from docs/PHASE_4_MIGRATION_EXECUTION_PLAN.md. Begin with Phase I (I/O Layer: 3 modules, 26 functions). Use TodoWrite, run full tests after each phase, create summaries, and stop at checkpoints. Before starting: show Phase I scope, subtasks, estimated time, and success criteria. Wait for approval.
```

---

## Phase-Specific Prompts

Use these if resuming in the middle of Phase 5:

### Resume Phase II (Core Layer)

```
Resuming Phase 5: Full Refactoring Implementation at Phase II.

PHASE II SCOPE:
Migrate 2 modules from Core layer: data_loader, data_transforms
- 19 functions total
- Critical function: load_all_data() affects 40+ pages
- Risk Level: MEDIUM
- Depends on: Phase I (I/O Layer) already migrated

REQUIREMENTS:
- Extra testing for load_all_data() before gradual cutover
- Update imports in pages one at a time
- Keep temporary wrapper in utils.py during transition
- All 94 tests must pass after Phase II

REFERENCE:
- Architecture: docs/PHASE_4_PACKAGE_STRUCTURE.md
- Function Map: docs/PHASE_4_FUNCTION_MAP.md
- Execution Plan: docs/PHASE_4_MIGRATION_EXECUTION_PLAN.md (Phase II section)

START: Show Phase II scope, subtasks, estimated time, and success criteria. Wait for approval.
```

### Resume Phase III (Analysis Layer)

```
Resuming Phase 5: Full Refactoring Implementation at Phase III.

PHASE III SCOPE:
Migrate 7 modules from Analysis layer: scoring → rankings → aggregation → streaks → records → commentary → pipeline
- 91 functions total (most complex)
- Heavy interdependencies between modules
- CRITICAL: Must migrate in order (scoring → rankings → aggregation first)
- Risk Level: MEDIUM-HIGH
- Depends on: Phase I (I/O) and Phase II (Core) already migrated

MIGRATION ORDER (NON-NEGOTIABLE):
1. analysis/scoring.py (depends on: core)
2. analysis/rankings.py (depends on: core, scoring)
3. analysis/aggregation.py (depends on: core, scoring, rankings)
4. analysis/streaks.py (depends on: core only - can do in parallel with above)
5. analysis/records.py (depends on: core, aggregation)
6. analysis/commentary.py (depends on: all of above)
7. analysis/pipeline.py (depends on: all modules - last)

REQUIREMENTS:
- Test each module independently before proceeding
- Test cross-module dependencies (scoring → rankings → aggregation chain)
- Verify all 94 tests passing after each module
- Keep temporary wrappers in utils.py for gradual cutover

REFERENCE:
- Architecture: docs/PHASE_4_PACKAGE_STRUCTURE.md
- Function Map: docs/PHASE_4_FUNCTION_MAP.md
- Dependencies: docs/PHASE_4_DEPENDENCY_MAP.md
- Execution Plan: docs/PHASE_4_MIGRATION_EXECUTION_PLAN.md (Phase III section)

START: Show Phase III scope, subtasks, estimated time, and success criteria. Wait for approval.
```

### Resume Phase IV (Display Layer)

```
Resuming Phase 5: Full Refactoring Implementation at Phase IV.

PHASE IV SCOPE:
Migrate 3 modules from Display layer: formatters, tables, charts
- 44 functions total (leaf modules - safest to migrate)
- Risk Level: LOW
- Depends on: Phase I (I/O), Phase II (Core), Phase III (Analysis) already migrated
- No internal dependencies between display modules

MIGRATION STRUCTURE:
1. display/formatters.py (depends on: core, analysis)
2. display/tables.py (depends on: core, analysis, formatters)
3. display/charts.py (depends on: core, analysis, formatters)

REQUIREMENTS:
- Update page imports to use new display modules
- Test table and chart generation after each module
- Verify all 94 tests passing after Phase IV
- Keep temporary wrappers in utils.py

REFERENCE:
- Architecture: docs/PHASE_4_PACKAGE_STRUCTURE.md
- Function Map: docs/PHASE_4_FUNCTION_MAP.md
- Execution Plan: docs/PHASE_4_MIGRATION_EXECUTION_PLAN.md (Phase IV section)

START: Show Phase IV scope, subtasks, estimated time, and success criteria. Wait for approval.
```

---

## Post-Implementation Prompts

### Phase 5 Completion & Cleanup

Use this after all 4 phases are complete:

```
Phase 5: Full Refactoring Implementation - All 4 phases complete.

FINAL TASKS:
1. Remove all temporary wrappers from streamlit/utils.py
2. Update all page imports to use new teg_analysis package directly
3. Clean up old function definitions from utils.py
4. Run full regression test suite (all 94 tests)
5. Performance validation (same or better than baseline)
6. Create final Phase 5 completion summary
7. Commit with final message
8. Update documentation

REQUIREMENTS:
- All 94 tests passing (100%)
- No performance degradation
- All pages loading correctly
- No import errors or warnings

REFERENCE:
- Migration Plan: docs/PHASE_4_MIGRATION_EXECUTION_PLAN.md (Week 5 section)
- Pre-cleanup Docs: docs/COMPLETE_CLEANUP_SUMMARY.md

START: Show cleanup plan, all tasks, estimated time, and success criteria. Wait for approval.
```

---

## Tips for Using These Prompts

### Best Practices

1. **Copy the entire prompt** - Don't paraphrase; copy/paste ensures consistency
2. **Include all sections** - The requirements and structure matter
3. **Wait for confirmation** - Let Claude show understanding before approving
4. **Keep reference docs nearby** - You may need to reference them
5. **Review phase scope** - Understand what each phase accomplishes

### When to Use Each Version

| Version | Use When |
|---------|----------|
| **Full** | Starting Phase 5 from scratch |
| **Quick Reference** | Resuming after a break, familiar with plan |
| **Minimal** | Very familiar with plan, just need to trigger start |
| **Phase-Specific** | Resuming in middle of Phase 5 (Phase II, III, or IV) |
| **Post-Implementation** | All 4 phases complete, need cleanup guidance |

### Common Scenarios

**Scenario 1: Starting Phase 5 fresh**
- Use: Full Version
- Copy entire prompt
- Claude will confirm understanding of all 4 phases and requirements

**Scenario 2: Resuming after 1 week break**
- Use: Quick Reference Version
- Shorter, faster to process
- Claude still has context from previous work

**Scenario 3: Midway through Phase 5 (at Phase II)**
- Use: Phase II Resume Prompt
- Provides context of what's already done
- Focuses on current phase requirements

**Scenario 4: Completed all migration, need cleanup**
- Use: Post-Implementation Prompt
- Focuses on final cleanup tasks
- Verification and completion steps

---

## Quick Copy/Paste Commands

If you want to load this document into Claude without manual copying:

```bash
# View full version
cat docs/PHASE_5_STARTUP_PROMPT.md | head -150

# View quick reference
sed -n '140,180p' docs/PHASE_5_STARTUP_PROMPT.md

# View phase-specific prompts
sed -n '200,280p' docs/PHASE_5_STARTUP_PROMPT.md
```

---

## Related Documentation

These documents provide detailed reference information:

- **Architecture:** `docs/PHASE_4_PACKAGE_STRUCTURE.md` - Complete teg_analysis/ design
- **Function Mapping:** `docs/PHASE_4_FUNCTION_MAP.md` - All 254+ functions mapped
- **Dependencies:** `docs/PHASE_4_DEPENDENCY_MAP.md` - Dependency analysis (0 circular)
- **Execution Plan:** `docs/PHASE_4_MIGRATION_EXECUTION_PLAN.md` - Detailed 4-phase plan
- **Cleanup Summary:** `docs/COMPLETE_CLEANUP_SUMMARY.md` - Phases 1-4 completion

---

## Notes

**Version History:**
- Created: 2025-10-25
- Status: Ready for use
- Last Updated: 2025-10-25

**Maintenance:**
If you make changes to the Phase 5 plan, update this file to keep prompts synchronized with actual implementation plans.

---

**How to use:** Copy one of the prompts above and paste it into Claude Code when you're ready to begin Phase 5 refactoring.
