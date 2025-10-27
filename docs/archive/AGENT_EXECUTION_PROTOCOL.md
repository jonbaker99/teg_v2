# Agent Execution Protocol - Pre-Refactoring Cleanup

**Document Purpose:** Define strict compliance requirements for AI agents executing the pre-refactoring plan
**Applies To:** All agents working on [PRE_REFACTORING_PLAN.md](PRE_REFACTORING_PLAN.md)
**Created:** 2025-10-19
**Enforcement Level:** MANDATORY

---

## Overview

This protocol ensures that AI agents executing the pre-refactoring cleanup:
1. Follow the plan completely (no shortcuts)
2. Track progress transparently
3. Verify all changes
4. Flag issues immediately
5. Cannot proceed past failures

**Core Principle:** Trust but verify. Every claim must have evidence.

---

## Pre-Execution Requirements

### Before Starting ANY Task

Agent MUST complete this checklist:

```markdown
## TASK START PROTOCOL

1. ✅ Read FULL task description (not just title)
2. ✅ Identify all subtasks and verification steps
3. ✅ Create TodoWrite checklist with ALL subtasks
4. ✅ Estimate time for each subtask
5. ✅ Report understanding to user
6. ✅ Wait for user confirmation

ONLY AFTER USER CONFIRMS → Proceed with execution
```

### Example Start Message

```
TASK START: Phase 1, Task 1.1.1 - Delete extract_teg_num duplicate

MY UNDERSTANDING:
================
File: streamlit/helpers/history_data_processing.py
Action: Delete lines 639-646 (duplicate function)
Keep: Lines 349-356 (original function)

Verification Steps:
1. grep -n "def extract_teg_num" → Should show ONLY line 349
2. Run tests for history_data_processing.py
3. Run streamlit page: 101TEG History.py

Estimated Time: 5 minutes

SUBTASKS CHECKLIST:
==================
[ ] Open history_data_processing.py
[ ] Locate duplicate at lines 639-646
[ ] Delete lines 639-646
[ ] Save file
[ ] Run grep verification
[ ] Run tests
[ ] Test affected page

Shall I proceed? (Reply 'yes' to confirm)
```

---

## Mandatory TodoWrite Usage

### Every Task MUST Use TodoWrite

**At Task Start:**
```python
TodoWrite([
    {"content": "Locate duplicate function at line 639", "status": "in_progress", "activeForm": "Locating duplicate function at line 639"},
    {"content": "Delete lines 639-646", "status": "pending", "activeForm": "Deleting lines 639-646"},
    {"content": "Verify only one definition remains", "status": "pending", "activeForm": "Verifying only one definition remains"},
    {"content": "Run tests", "status": "pending", "activeForm": "Running tests"},
    {"content": "Test affected pages", "status": "pending", "activeForm": "Testing affected pages"}
])
```

**After EACH Subtask:**
```python
TodoWrite([
    {"content": "Locate duplicate function at line 639", "status": "completed", "activeForm": "Locating duplicate function at line 639"},
    {"content": "Delete lines 639-646", "status": "in_progress", "activeForm": "Deleting lines 639-646"},
    {"content": "Verify only one definition remains", "status": "pending", "activeForm": "Verifying only one definition remains"},
    ...
])
```

### Rules

1. ❌ **NEVER mark task "completed" without showing evidence**
2. ❌ **NEVER have more than ONE task "in_progress" at a time**
3. ❌ **NEVER skip a pending task**
4. ✅ **ALWAYS update after each subtask completion**
5. ✅ **ALWAYS mark completed tasks immediately**

---

## Verification Requirements

### Every Change Must Be Verified

**Rule:** Cannot claim "I did X" without showing proof.

### Verification Types

#### 1. File Changes - Show Git Diff

```bash
# After deleting duplicate function:
git diff streamlit/helpers/history_data_processing.py
```

**Must show:**
- Red lines (deletions) matching expected
- Line numbers correct
- No unintended changes

**Agent must paste git diff output to user**

#### 2. Deletions - Show Grep Verification

```bash
# After claiming "deleted duplicate extract_teg_num":
grep -n "def extract_teg_num" streamlit/helpers/history_data_processing.py
```

**Expected output:**
```
349:def extract_teg_num(teg_str):
```

**If output shows 2+ results → Task NOT complete**

**Agent must paste grep output to user**

#### 3. Function Additions - Show Import Test

```bash
# After adding safe_int() to utils.py:
python -c "from streamlit.utils import safe_int; print(safe_int('42'))"
```

**Expected output:**
```
42
```

**Agent must paste test output to user**

#### 4. All Changes - Run Tests

```bash
# After ANY code change:
pytest tests/test_relevant_module.py -v
```

**Expected output:**
```
test_function_name PASSED
...
========== X passed in Y.YYs ==========
```

**If ANY test fails → Task NOT complete**

**Agent must paste full test output to user**

#### 5. Page Functionality - Show Streamlit Test

```bash
# For changes affecting page files:
# Agent must report:
"I have tested streamlit/101TEG History.py and confirm:
✅ Page loads without errors
✅ Data displays correctly
✅ No console warnings
✅ Functionality unchanged"
```

### Verification Matrix

| Change Type | Verification Required | Evidence Format |
|-------------|----------------------|-----------------|
| Delete function | grep shows 0 results | Paste grep output |
| Delete duplicate | grep shows 1 result | Paste grep output |
| Add function | Import test succeeds | Paste test output |
| Modify function | Tests pass | Paste pytest output |
| Update imports | No import errors | Paste test output |
| Archive file | File moved to archive/ | Paste ls output |

**NO verification → NO completion claim**

---

## Checkpoint System

### Mandatory Stop Points

Agent MUST stop and get user approval at these checkpoints:

```markdown
✋ CHECKPOINT 1: After Phase 1.1 (Delete within-file duplicates)
✋ CHECKPOINT 2: After Phase 1.2 (Archive unused code)
✋ CHECKPOINT 3: After Phase 1.3 (Add utility functions)
✋ CHECKPOINT 4: After Phase 1.4 (Create testing infrastructure)
✋ CHECKPOINT 5: After Phase 2 (Resolve naming conflicts)
✋ CHECKPOINT 6: After Phase 3 (Address technical debt)
✋ CHECKPOINT 7: After Phase 4 (Create migration architecture)
```

### Checkpoint Procedure

At each checkpoint, agent MUST:

1. **Summarize Work Done**
```
CHECKPOINT 1 REACHED: Phase 1.1 Complete

Work Summary:
- Deleted 9 duplicate functions across 5 files
- Total lines removed: 370 lines
- Files modified: 5
```

2. **Show Evidence**
```
Evidence:
✅ Git diff shows 370 lines deleted
✅ All tests passing (25/25)
✅ All affected pages tested
✅ No import errors
```

3. **Report Issues (if any)**
```
Issues Encountered:
1. Found 3 duplicates instead of 2 in generate_commentary.py
   - Action taken: Deleted all 3, kept first
   - Updated documentation

2. Test failure in test_history.py
   - Root cause: Import path changed
   - Action taken: Fixed import
   - Status: Now passing
```

4. **Wait for Approval**
```
Status: Phase 1.1 complete and verified.
Ready to proceed to Phase 1.2 (Archive unused code).

Awaiting approval to continue. (Reply 'proceed' to continue)
```

### Checkpoint Cannot Be Skipped

❌ Agent CANNOT say "checkpoint passed" without showing evidence
❌ Agent CANNOT proceed to next phase without user approval
❌ Agent CANNOT batch multiple checkpoints

---

## Issue Flagging Protocol

### When to Flag an Issue

Agent MUST STOP and flag issue if:

| Issue Type | Example | Required Action |
|------------|---------|-----------------|
| **Test Failure** | pytest fails | STOP, report error, await guidance |
| **Unexpected Structure** | File not where docs say | STOP, report discrepancy |
| **Count Mismatch** | Found 3 duplicates, docs say 2 | STOP, report finding |
| **Unable to Verify** | grep doesn't confirm deletion | STOP, report problem |
| **Breaking Change** | Page won't load after change | STOP, rollback, report |
| **Missing Dependency** | Import fails | STOP, report missing item |

### Issue Report Format

```markdown
🚨 ISSUE DETECTED - EXECUTION HALTED

Phase: 1.1
Task: Delete extract_teg_num duplicate
Step: Verification

EXPECTED:
Find duplicate at line 639

ACTUAL:
Found THREE definitions (lines 349, 639, 892)

ANALYSIS:
Documentation stated 2 duplicates.
Codebase has 3 duplicates.

VERIFICATION:
```bash
$ grep -n "def extract_teg_num" streamlit/helpers/history_data_processing.py
349:def extract_teg_num(teg_str):
639:def extract_teg_num(teg_str):
892:def extract_teg_num(teg_str):
```

QUESTION FOR USER:
Should I:
A) Delete both lines 639 and 892 (keep 349)?
B) Investigate why there's a 3rd copy?
C) Update documentation and delete all but 349?

CURRENT STATUS: Awaiting user decision.
NO CHANGES MADE YET.
```

### What Agent Must NOT Do

❌ **NEVER** "assume it's fine" and skip testing
❌ **NEVER** continue past a test failure
❌ **NEVER** make up missing information
❌ **NEVER** deviate from plan without asking
❌ **NEVER** skip verification because "looks right"
❌ **NEVER** batch fixes without testing each
❌ **NEVER** mark task complete if verification fails

### What Agent MUST Do

✅ **ALWAYS** stop on first issue
✅ **ALWAYS** report exact error messages
✅ **ALWAYS** provide context (what was being done)
✅ **ALWAYS** suggest options for resolution
✅ **ALWAYS** wait for user decision
✅ **ALWAYS** document issue in plan updates

---

## Documentation Update Requirements

### After Every Task

Agent must update documentation:

```markdown
1. PRE_REFACTORING_QUICK_START.md
   - Check off completed task
   - Update progress percentage

2. Task-specific notes
   - Document any deviations
   - Note any new discoveries
   - Update time estimates if different

3. Issue log (if applicable)
   - Record issues encountered
   - Record resolutions applied
```

### After Every Phase

Agent must create phase summary:

```markdown
# Phase 1 Completion Summary

**Planned Duration:** 8 hours
**Actual Duration:** 9.5 hours (+1.5 hours)

**Tasks Completed:**
✅ Task 1.1 - Within-file duplicates (1.5h actual vs 1h planned)
✅ Task 1.2 - Archive unused code (2h actual vs 2h planned)
✅ Task 1.3 - Add utilities (1h actual vs 1h planned)
✅ Task 1.4 - Testing infrastructure (5h actual vs 4h planned)

**Deviations from Plan:**
1. Found 3 extra duplicates not in documentation
   - Added 30 minutes to Task 1.1
2. Testing infrastructure took longer (missing fixtures)
   - Added 1 hour to Task 1.4

**Issues Encountered:**
1. ISSUE-001: Three extract_teg_num instead of two
   - Resolution: Deleted all 3, updated docs
2. ISSUE-002: Missing pytest-cov dependency
   - Resolution: Added to requirements.txt

**Metrics:**
- Lines deleted: 605 (vs 600 planned)
- Functions archived: 22 (vs 20 planned)
- Tests created: 28 (vs 25 planned)
- Test coverage: 65% (target: 50%+)

**Status:** Phase 1 COMPLETE ✅
**Ready for:** Phase 2 (Naming Conflicts)
```

---

## Phase Completion Criteria

### Cannot Mark Phase Complete Unless:

```markdown
✅ All tasks checked off in TodoWrite
✅ All tests passing (100%)
✅ All verifications shown to user
✅ Git commit created
✅ Documentation updated
✅ User has reviewed and approved
✅ No pending issues
```

### Missing ANY Criterion → Phase INCOMPLETE

**Example of INCOMPLETE phase:**

```
Phase 1 Status: INCOMPLETE ❌

Completed:
✅ Tasks 1.1, 1.2, 1.3

Missing:
❌ Task 1.4 (Testing infrastructure)
   - Only 10 tests created (need 25+)
   - No test coverage report

❌ Documentation updates
   - QUICK_START.md not updated

❌ User approval
   - Checkpoint 4 not reached

Cannot proceed to Phase 2 until Phase 1 fully complete.
```

---

## Testing Compliance

### Every Code Change Requires Tests

| Change Type | Test Requirement | Evidence |
|-------------|------------------|----------|
| Delete function | Tests still pass | pytest output |
| Add function | New test created | pytest output |
| Modify function | Tests updated | pytest output |
| Rename function | Imports updated, tests pass | pytest output |
| Archive file | No test failures | pytest output |

### Test Execution Timing

```markdown
1. BEFORE any changes:
   - Run full test suite
   - Confirm all passing (baseline)

2. AFTER each file change:
   - Run tests for affected module
   - Confirm still passing

3. AFTER each task:
   - Run full test suite
   - Confirm all passing

4. BEFORE checkpoint:
   - Run full test suite
   - Run smoke tests
   - Confirm 100% passing
```

### Test Failure Protocol

```markdown
IF test fails:

1. STOP immediately (do not continue)

2. Report failure:
   - Which test failed
   - Error message
   - Stack trace

3. Analyze cause:
   - What change caused it?
   - Is it real bug or test issue?

4. Propose fix:
   - Option A: Rollback change
   - Option B: Fix code
   - Option C: Update test

5. Wait for user decision

6. Apply fix

7. Re-run tests

8. Only continue when ALL passing
```

---

## Git Commit Requirements

### Commit Frequency

```markdown
Commit AFTER:
- Each completed task
- Each checkpoint
- Each phase completion

DO NOT commit:
- Mid-task (incomplete work)
- Broken code (tests failing)
- Unverified changes
```

### Commit Message Format

```
<type>(<scope>): <description>

<body>

Pre-refactoring Phase X.Y
Generated with Claude Code
```

**Example:**
```
refactor(duplicates): Delete within-file duplicate functions

Removed 9 duplicate function definitions across 5 files:
- history_data_processing.py: 4 duplicates (180 lines)
- generate_tournament_commentary_v2.py: 2 duplicates (16 lines)
- generate_round_report.py: 1 duplicate (3 lines)
- player_history.py: 1 duplicate (5 lines)
- generate_commentary.py: 1 duplicate (5 lines)

Total: 370 lines deleted

All tests passing (25/25)
All affected pages tested

Pre-refactoring Phase 1.1
Generated with Claude Code
```

---

## Rollback Procedure

### When to Rollback

If agent encounters:
- Failing tests that can't be immediately fixed
- Breaking changes
- Unexpected cascading errors
- Unable to verify changes

### Rollback Steps

```bash
# 1. Identify last good commit
git log --oneline

# 2. Rollback to last good state
git checkout <last-good-commit>

# 3. Verify rollback successful
pytest tests/ -v

# 4. Report to user
"Rolled back to commit <hash> due to <reason>.
All tests now passing.
Ready to retry with different approach."
```

---

## Summary: Agent Compliance Checklist

For EVERY task, agent must:

- [ ] Show understanding before starting
- [ ] Create TodoWrite checklist
- [ ] Update todos after each step
- [ ] Show verification for every change
- [ ] Run tests after every change
- [ ] Stop at checkpoints
- [ ] Flag issues immediately
- [ ] Update documentation
- [ ] Create git commits
- [ ] Wait for approval before proceeding

**Violation of ANY rule → Non-compliant execution**

---

## Enforcement

User should:

1. **Challenge unverified claims**
   - "You say you deleted the duplicate. Show me the grep output."

2. **Require evidence**
   - "I don't see test output. Run tests and show results."

3. **Block checkpoint passage**
   - "Checkpoint 1 incomplete. Task 1.4 not verified."

4. **Request rollback if needed**
   - "Tests are failing. Roll back and explain what broke."

5. **Demand compliance**
   - "You skipped the TodoWrite step. Restart task with proper tracking."

**Remember:** Agent works for you. Demand evidence. Verify claims. Enforce protocol.

---

**Last Updated:** 2025-10-19
**Status:** ACTIVE PROTOCOL
**Enforcement:** MANDATORY for all pre-refactoring work
