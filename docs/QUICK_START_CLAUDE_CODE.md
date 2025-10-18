# Quick Start: Using Claude Code for Documentation

**Goal:** Use Claude Code subagents to parallelize the documentation tasks
**Time Savings:** ~2 days instead of ~5 days
**Difficulty:** Easy

---

## Prerequisites

1. ✅ Claude Code installed and configured
2. ✅ Access to your TEG codebase
3. ✅ 5 terminal windows available
4. ✅ This documentation package downloaded

---

## Step-by-Step Instructions

### Phase 1: Preparation (10 minutes)

#### 1. Set up workspace
```bash
cd /path/to/your/teg_v2_project

# Create documentation output directory
mkdir -p docs/inventory

# Copy task files to project root
cp /path/to/docs/TASK_*.md .
```

#### 2. Verify Claude Code access
```bash
# Test that Claude Code can see your files
claude code --help

# Verify it can access your codebase
claude code "list all Python files in streamlit/"
```

#### 3. Open 5 terminal windows
- Terminal 1: Task 1 (utils.py)
- Terminal 2: Task 2 (helpers)
- Terminal 3: Task 3 (pages)
- Terminal 4: Task 4 (dependencies) - Start LATER
- Terminal 5: Task 5 (duplicates) - Start LATER

---

### Phase 2: Start Parallel Tasks (Hour 0)

#### Terminal 1: Document utils.py
```bash
claude code --task "Document all functions in streamlit/utils.py following TASK_1_UTILS_INVENTORY.md. For each function provide: signature, purpose, parameters, returns, dependencies, used by (search codebase), type (PURE/UI/IO/MIXED), migration target, and priority. Output to docs/inventory/UTILS_INVENTORY.md"
```

**Expected Duration:** 4-6 hours
**Output:** `docs/inventory/UTILS_INVENTORY.md`

#### Terminal 2: Document helpers
```bash
claude code --task "Document all helper modules in streamlit/helpers/ following TASK_2_HELPERS_INVENTORY.md. For each module and function provide complete analysis including dependencies, used by, migration target. Output to docs/inventory/HELPERS_INVENTORY.md"
```

**Expected Duration:** 3-4 hours
**Output:** `docs/inventory/HELPERS_INVENTORY.md`

#### Terminal 3: Document pages
```bash
claude code --task "Document all Streamlit page files following TASK_3_PAGES_INVENTORY.md. For each page document purpose, data loading, dependencies, embedded calculations, migration complexity. Output to docs/inventory/PAGES_INVENTORY.md"
```

**Expected Duration:** 4-5 hours
**Output:** `docs/inventory/PAGES_INVENTORY.md`

---

### Phase 3: Monitor Progress (Ongoing)

Check progress every 1-2 hours:

```bash
# Check how much has been documented
wc -l docs/inventory/*.md

# Read partial outputs
less docs/inventory/UTILS_INVENTORY.md

# Check for errors
grep -i "error\|failed\|todo" docs/inventory/*.md
```

---

### Phase 4: Start Dependent Tasks (Hour 3-4)

Once Tasks 1, 2, 3 are about 50% complete:

#### Terminal 4: Map dependencies
```bash
claude code --task "Analyze all imports and function calls in streamlit/ following TASK_4_DEPENDENCY_MAP.md. Create dependency matrix, identify critical paths, calculate migration impact for each function. Output to docs/inventory/DEPENDENCIES.md and docs/inventory/dependency_graph.json"
```

**Expected Duration:** 3-4 hours
**Output:** 
- `docs/inventory/DEPENDENCIES.md`
- `docs/inventory/dependency_graph.json`

---

### Phase 5: Start Final Task (After Tasks 1, 2 complete)

Once Tasks 1 and 2 are 100% complete:

#### Terminal 5: Find duplicates
```bash
claude code --task "Identify all duplicate and similar functions across streamlit/ following TASK_5_DUPLICATION_ANALYSIS.md. Find exact, near, functional, and pattern duplicates. Provide consolidation recommendations. Output to docs/inventory/DUPLICATES.md"
```

**Expected Duration:** 3-4 hours
**Output:**
- `docs/inventory/DUPLICATES.md`
- `docs/inventory/consolidation_roadmap.md`

---

## Alternative: One-Shot Prompt

If Claude Code supports complex multi-part tasks, you can use this single prompt:

```bash
claude code --task "Complete codebase documentation project with 5 parallel tasks:

TASK 1 (Priority: Critical, Start: Now):
Document all functions in streamlit/utils.py per TASK_1_UTILS_INVENTORY.md
Output: docs/inventory/UTILS_INVENTORY.md

TASK 2 (Priority: Critical, Start: Now):
Document all helper modules per TASK_2_HELPERS_INVENTORY.md
Output: docs/inventory/HELPERS_INVENTORY.md

TASK 3 (Priority: High, Start: Now):
Document all page files per TASK_3_PAGES_INVENTORY.md
Output: docs/inventory/PAGES_INVENTORY.md

TASK 4 (Priority: High, Start: After Tasks 1,2,3 reach 50%):
Map all dependencies per TASK_4_DEPENDENCY_MAP.md
Output: docs/inventory/DEPENDENCIES.md, dependency_graph.json

TASK 5 (Priority: Medium, Start: After Tasks 1,2 complete):
Find all duplicates per TASK_5_DUPLICATION_ANALYSIS.md
Output: docs/inventory/DUPLICATES.md

Follow all instructions in respective TASK files. Coordinate timing based on dependencies."
```

---

## Tips for Success

### 1. Let it run
- Don't interrupt Claude Code mid-task
- These are long-running tasks (hours)
- Check progress but don't micromanage

### 2. Review incrementally
- Check partial outputs every 1-2 hours
- Validate quality early
- Correct course if needed

### 3. Handle errors gracefully
- If a task fails, check the error
- Restart that specific task only
- Don't restart all tasks

### 4. Save intermediate results
```bash
# Backup partial results every few hours
cp -r docs/inventory docs/inventory_backup_$(date +%Y%m%d_%H%M)
```

---

## What If It Doesn't Work?

### Claude Code doesn't support long tasks?
→ Break each task into smaller chunks:

```bash
# Instead of all of utils.py at once:
claude code "Document functions 1-20 in utils.py per TASK_1"
claude code "Document functions 21-40 in utils.py per TASK_1"
# etc.
```

### Claude Code output is incomplete?
→ Review and fill gaps manually

### Claude Code is too slow?
→ Hybrid approach:
- Use Claude Code for mechanical tasks (4, 5)
- Do tasks 1, 2, 3 manually with task files as checklists

### Claude Code makes mistakes?
→ Validate and correct:
- Check function signatures against actual code
- Verify dependencies with grep
- Test import paths

---

## Quality Checks

After each task completes, verify:

```bash
# Check file size (should be substantial)
ls -lh docs/inventory/*.md

# Check completeness (no TODOs left)
grep -i "todo\|tbd\|fix\|check" docs/inventory/*.md

# Check structure (follows template)
head -100 docs/inventory/UTILS_INVENTORY.md

# Validate specific entries
grep "def load_all_data" docs/inventory/UTILS_INVENTORY.md -A 20
```

---

## Timeline Expectations

### Hour 0-2: Setup & Start
- Tasks 1, 2, 3 started
- First progress checks
- Any immediate issues resolved

### Hour 3-6: Main Work
- Tasks 1, 2, 3 in progress
- Task 4 started (after 50% milestone)
- Regular progress monitoring

### Hour 7-10: Completion
- Tasks 1, 2, 3 complete
- Task 4 in progress
- Task 5 started

### Hour 11-14: Final Tasks
- Task 4 complete
- Task 5 complete
- Quality validation

### Hour 15-16: Review
- Read all outputs
- Validate completeness
- Identify any gaps

---

## Success Metrics

When done, you should have:

- ✅ UTILS_INVENTORY.md: 50-100 functions documented
- ✅ HELPERS_INVENTORY.md: 10+ modules, all functions
- ✅ PAGES_INVENTORY.md: 30+ pages analyzed
- ✅ DEPENDENCIES.md: Complete dependency graph
- ✅ DUPLICATES.md: All duplicates identified

**Total Documentation:** Likely 500-1000 pages of detailed analysis

---

## What's Next?

After Claude Code completes:

1. **Review all outputs** (2-4 hours)
2. **Fill any gaps** manually (1-2 hours)
3. **Validate findings** (1 hour)
4. **Hold planning session** (2-4 hours)
5. **Begin refactoring** (following the plan)

---

## Example Output Check

After Task 1 completes, verify quality:

```markdown
# Should look like this:

### `load_all_data()`

**Line Numbers:** 145-180
**Function Type:** IO + PURE
**Complexity:** Medium

**Purpose:**
Main data loading function that fetches tournament data from either
GitHub (production) or local files (development), with optional
filtering for incomplete TEGs and TEG 50.

**Full Signature:**
\`\`\`python
def load_all_data(
    exclude_incomplete_tegs: bool = True,
    exclude_teg_50: bool = False
) -> pd.DataFrame:
    """Load all tournament data with optional filters."""
\`\`\`

**Parameters:**
- exclude_incomplete_tegs (bool): Remove tournaments not yet complete
- exclude_teg_50 (bool): Remove TEG 50 (special case tournament)

**Returns:**
- pd.DataFrame: Tournament data with columns: TEGNum, Round, Player, Hole, Sc, PAR, etc.

**Dependencies:**
- External: pandas, os
- Internal: read_from_github(), get_current_branch()
- Streamlit: st.cache_data (for caching)

**Used By:**
- streamlit/400scoring.py (line 35)
- streamlit/streaks.py (line 28)
[... 28 more files]

**Migration Target:** teg_analysis/core/data_loader.py
**Priority:** 🔴 CRITICAL (32 usages)
```

If output looks like this ✅ → Quality is good
If output is sparse ❌ → Need to refine prompt or do manually

---

## Ready to Start?

1. Open 3-5 terminals
2. Navigate to your project directory
3. Copy the commands above
4. Let Claude Code work
5. Monitor progress
6. Review outputs

**Estimated Time:** Start now, complete in 12-16 hours of wall time

Good luck! 🚀
