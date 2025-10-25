# Constants & Global Variables Mapping Guide

**Document Purpose:** Track all constants and global variables across the codebase to prevent orphans and duplicates during refactoring
**Created:** 2025-10-19
**Status:** ACTIVE GUIDE
**Part Of:** [PRE_REFACTORING_PLAN.md](PRE_REFACTORING_PLAN.md) Phase 1.5

---

## Why This Matters

### The Problem

During refactoring, functions move between modules. If constants don't move with them:

**Scenario: The Orphan**
```python
# BEFORE (utils.py)
PLAYER_DICT = {'AB': 'Alex BAKER', ...}

def get_player_name(code):
    return PLAYER_DICT.get(code)

# AFTER REFACTOR (teg_analysis/core/players.py)
def get_player_name(code):
    return PLAYER_DICT.get(code)  # ❌ NameError! PLAYER_DICT not here

# utils.py
PLAYER_DICT = {'AB': 'Alex BAKER', ...}  # ❌ Orphaned! Unused, taking up space
```

**Scenario: The Duplicate**
```python
# utils.py
ALL_SCORES_PARQUET = "data/all-scores.parquet"

# page_A.py
ALL_SCORES_FILE = "data/all-scores.parquet"  # ❌ Duplicate! Which is canonical?

# If utils.py constant changes → page_A.py breaks
```

**Scenario: The Hidden Dependency**
```python
# utils.py
BASE_DIR = Path.cwd().parent

# function in module A
def read_file(path):
    full_path = BASE_DIR / path  # Uses BASE_DIR

# If module A migrates without BASE_DIR → NameError
```

### The Solution

**Complete inventory BEFORE migration:**
1. Find all constants
2. Map all usage
3. Plan migration WITH their functions
4. Prevent orphans and duplicates

---

## Constant Types to Track

### 1. Module-Level Constants

```python
# Uppercase variables at module level
GITHUB_REPO = "jonbaker99/teg_v2"
ALL_SCORES_PARQUET = "data/all-scores.parquet"
TOTAL_HOLES = 18
```

**Characteristics:**
- Defined at module level (not in function/class)
- Usually UPPERCASE (Python convention)
- Used by multiple functions
- Changing them affects entire module

### 2. Configuration Dictionaries

```python
PLAYER_DICT = {
    'AB': 'Alex BAKER',
    'JB': 'Jon BAKER',
    ...
}

TEG_ROUNDS = {
    'TEG 1': 1,
    'TEG 2': 3,
    ...
}
```

**Characteristics:**
- Dictionary or list at module level
- Contains reference/lookup data
- Often imported by other modules
- Difficult to reconstruct if lost

### 3. Path/File Constants

```python
BASE_DIR = Path.cwd().parent
DATA_DIR = BASE_DIR / "data"
ALL_DATA_PARQUET = "data/all-data.parquet"
```

**Characteristics:**
- Define file locations
- Used by I/O functions
- CRITICAL: Breaking these breaks data access
- Often have dependencies (BASE_DIR → other paths)

### 4. Environment-Derived Constants

```python
GITHUB_BRANCH = get_current_branch()  # From function
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None
```

**Characteristics:**
- Set from environment or function call
- May behave differently dev vs production
- Must preserve initialization order

### 5. Class-Level Constants

```python
class RateLimiter:
    MAX_REQUESTS = 50
    WINDOW_SECONDS = 60
```

**Characteristics:**
- Defined inside class
- Used by class methods
- Migrate with class

### 6. Imported Constants

```python
from page_config import PAGE_DEFINITIONS
from utils import PLAYER_DICT
```

**Characteristics:**
- Defined elsewhere, imported here
- Creates dependency chain
- Must track both source and usage

---

## Current Constant Inventory

### utils.py Constants (DOCUMENTED)

Based on [inventory/UTILS_INVENTORY_01_CONFIG.md](inventory/UTILS_INVENTORY_01_CONFIG.md):

| Constant | Type | Line | Value | Used By | Migration Target |
|----------|------|------|-------|---------|------------------|
| `GITHUB_REPO` | str | 82 | "jonbaker99/teg_v2" | GitHub I/O functions (5) | `teg_analysis/config/constants.py` |
| `BASE_DIR` | Path | 86 | Path.cwd().parent... | All I/O functions | `teg_analysis/config/paths.py` |
| `ALL_DATA_PARQUET` | str | 91 | "data/all-data.parquet" | load_all_data, etc. | `teg_analysis/config/paths.py` |
| `ALL_SCORES_PARQUET` | str | 92 | "data/all-scores.parquet" | 16+ files | `teg_analysis/config/paths.py` |
| `STREAKS_PARQUET` | str | 93 | "data/streaks.parquet" | Streak functions | `teg_analysis/config/paths.py` |
| `BESTBALL_PARQUET` | str | 94 | "data/bestball.parquet" | Bestball functions | `teg_analysis/config/paths.py` |
| `HANDICAPS_CSV` | str | 95 | "data/handicaps.csv" | Handicap functions | `teg_analysis/config/paths.py` |
| `ROUND_INFO_CSV` | str | 96 | "data/round_info.csv" | Round info functions | `teg_analysis/config/paths.py` |
| `COMMENTARY_*_PARQUET` | str | 99-103 | "data/commentary_*.parquet" | Commentary functions | `teg_analysis/config/paths.py` |
| `ALL_DATA_CSV_MIRROR` | str | 106 | "data/all-data.csv" | Data update | `teg_analysis/config/paths.py` |
| `GITHUB_BRANCH` | str | 135 | get_current_branch() | GitHub I/O | `teg_analysis/config/constants.py` |
| `FILE_PATH_ALL_DATA` | str | 733 | ALL_DATA_PARQUET | load_all_data | ❌ DUPLICATE - Remove |
| `TOTAL_HOLES` | int | 735 | 18 | Various calculations | `teg_analysis/config/constants.py` |
| `PLAYER_DICT` | dict | 737-747 | Player mappings | get_player_name (3 files) | `teg_analysis/config/players.py` |
| `TEG_ROUNDS` | dict | 749-754 | TEG → round count | get_teg_rounds (4 files) | `teg_analysis/config/tournaments.py` |
| `TEGNUM_ROUNDS` | dict | 756-759 | int → round count | get_tegnum_rounds (4 files) | `teg_analysis/config/tournaments.py` |
| `TEG_OVERRIDES` | dict | 761-766 | Winner overrides | get_teg_winners | `teg_analysis/config/tournaments.py` |

**Total: 17 constant groups in utils.py**

### Other Files (TO BE INVENTORIED)

Research shows 119 constant definitions across 30 files. Need to inventory:

| File | Constants Found | Status |
|------|----------------|--------|
| `page_config.py` | PAGE_DEFINITIONS | ✅ Keep in streamlit/ |
| `helpers/display_helpers.py` | Unknown | ❌ Not inventoried |
| `commentary/*.py` | Unknown | ❌ Not inventoried |
| All other files | Unknown | ❌ Not inventoried |

**Action Required:** Run inventory script (see below)

---

## Inventory Process

### Step 1: Automated Discovery

**Create/Run:** `analyze_constants.py` (see template below)

```python
# This script finds all module-level constants
python analyze_constants.py > docs/CONSTANTS_INVENTORY.md
```

**Output:** Complete list of constants with:
- Constant name
- File location
- Line number
- Inferred type
- Assigned value (if simple)

### Step 2: Usage Analysis

For each constant found, determine:

```bash
# Find all usages
grep -r "CONSTANT_NAME" streamlit/**/*.py

# Example:
grep -r "PLAYER_DICT" streamlit/**/*.py
```

**Document:**
- How many files import it
- How many files use it directly
- What functions depend on it

### Step 3: Categorization

Classify each constant:

| Category | Migration Plan |
|----------|----------------|
| **Config - Paths** | → `teg_analysis/config/paths.py` |
| **Config - Settings** | → `teg_analysis/config/constants.py` |
| **Domain Data** | → Domain-specific module (e.g., `players.py`) |
| **UI Config** | → Keep in `streamlit/` |
| **Duplicates** | → Consolidate to ONE canonical location |
| **Orphans** | → Delete (unused) |

### Step 4: Dependency Mapping

Create dependency graph:

```
BASE_DIR (Line 86)
    ↓ Used by
    _get_local_path()
    ↓ Used by
    read_file(), write_file()
    ↓ Used by
    load_all_data(), 20+ other functions

Migration: BASE_DIR MUST move WITH or BEFORE I/O functions
```

### Step 5: Migration Planning

For each constant, document:

```markdown
### PLAYER_DICT

**Current Location:** utils.py:737-747
**Type:** Dict[str, str]
**Used By:**
- utils.get_player_name() (line 2350)
- helpers/display_helpers.py:167 (imported)
- commentary/generate_commentary.py:25 (imported)

**Dependencies:** None (self-contained)

**Migration Plan:**
1. Create teg_analysis/config/players.py
2. Move PLAYER_DICT to new file
3. Add to teg_analysis/__init__.py exports
4. Update imports in 3 files
5. Keep re-export in utils.py (backwards compat)
6. Gradually migrate streamlit/ imports
7. Remove re-export in final cleanup

**Risk Level:** LOW (well-defined, no dependencies)
**Priority:** MEDIUM (move with player-related functions)
```

---

## Migration Strategies

### Strategy 1: Move with Function

**When:** Constant used by single function/module

```python
# BEFORE
# utils.py
PLAYER_DICT = {...}

def get_player_name(code):
    return PLAYER_DICT.get(code)

# AFTER
# teg_analysis/config/players.py
PLAYER_DICT = {...}

def get_player_name(code):
    return PLAYER_DICT.get(code)
```

**Steps:**
1. Copy constant to new module
2. Copy function to new module
3. Test new module
4. Update imports
5. Delete from utils.py

### Strategy 2: Centralize in Config Module

**When:** Constant used by multiple modules

```python
# BEFORE
# utils.py
ALL_SCORES_PARQUET = "data/all-scores.parquet"

# Multiple functions use it

# AFTER
# teg_analysis/config/paths.py
ALL_SCORES_PARQUET = "data/all-scores.parquet"

# teg_analysis/io/file_operations.py
from teg_analysis.config.paths import ALL_SCORES_PARQUET

# teg_analysis/core/data_loader.py
from teg_analysis.config.paths import ALL_SCORES_PARQUET
```

**Steps:**
1. Create central config module
2. Move constant to config
3. Update ALL modules to import from config
4. Keep re-export in utils.py temporarily
5. Remove re-export later

### Strategy 3: Re-Export for Compatibility

**When:** Breaking many imports undesirable

```python
# teg_analysis/config/paths.py (NEW)
ALL_SCORES_PARQUET = "data/all-scores.parquet"

# streamlit/utils.py (BACKWARD COMPAT)
from teg_analysis.config.paths import ALL_SCORES_PARQUET  # Re-export

# Old imports still work:
from utils import ALL_SCORES_PARQUET  # Still works!

# New imports also work:
from teg_analysis.config.paths import ALL_SCORES_PARQUET  # Better!
```

**Steps:**
1. Move to new location
2. Add re-export in utils.py
3. Gradually update imports
4. Remove re-export in final cleanup

### Strategy 4: Consolidate Duplicates

**When:** Multiple files define same constant

```python
# BEFORE
# utils.py
ALL_SCORES_FILE = "data/all-scores.parquet"

# page_A.py
ALL_SCORES_PARQUET = "data/all-scores.parquet"

# AFTER
# teg_analysis/config/paths.py
ALL_SCORES_PARQUET = "data/all-scores.parquet"  # Single canonical version

# Both files import from here
```

**Steps:**
1. Identify all duplicates
2. Choose canonical name/value
3. Create in config module
4. Update ALL files to import
5. Delete duplicates

---

## Orphan Prevention Checklist

Before moving ANY function:

- [ ] List all constants it uses
- [ ] Check if constants used elsewhere
- [ ] Plan constant migration
- [ ] Move constants WITH or BEFORE function
- [ ] Verify no NameError
- [ ] Update all imports
- [ ] Test thoroughly

### Example Checklist: Moving read_file()

```markdown
Function: read_file()
Constants Used:
- BASE_DIR ✓
- ALL_SCORES_PARQUET ✓
- GITHUB_BRANCH ✓

Plan:
1. Create teg_analysis/config/paths.py
2. Move BASE_DIR, ALL_SCORES_PARQUET
3. Create teg_analysis/config/constants.py
4. Move GITHUB_BRANCH
5. Update read_file() imports
6. Test read_file() in new location
7. Move read_file()
8. Update calling code

Status: Constants migrated FIRST ✓
```

---

## Constant Inventory Template

### CONSTANTS_INVENTORY.md Structure

```markdown
# Complete Constants Inventory

**Generated:** 2025-10-19
**Files Scanned:** 79
**Constants Found:** TBD

---

## Summary Statistics

| Category | Count | Migration Target |
|----------|-------|------------------|
| Path Constants | TBD | teg_analysis/config/paths.py |
| Settings | TBD | teg_analysis/config/constants.py |
| Domain Data | TBD | Domain-specific modules |
| UI Config | TBD | Keep in streamlit/ |
| Duplicates | TBD | Consolidate |
| Orphans | TBD | Delete |

---

## By Module

### utils.py (17 constants)

[See detailed inventory above]

### page_config.py

#### PAGE_DEFINITIONS
- **Type:** Dict
- **Line:** 3
- **Used By:** get_page_layout() (utils.py), 24+ page files
- **Migration:** KEEP in streamlit/page_config.py (UI-specific)
- **Risk:** LOW

### helpers/display_helpers.py

[To be completed after inventory script run]

### [Continue for all files...]

---

## Dependencies

### Dependency Chains

```
BASE_DIR (Line 86)
    ↓
_get_local_path() (uses BASE_DIR)
    ↓
read_file() (uses _get_local_path)
    ↓
load_all_data() (uses read_file)
    ↓
40+ page files (use load_all_data)

Migration order: BASE_DIR → helpers → I/O → data loading
```

---

## Migration Priority

### Phase 1: Critical Infrastructure
Move with Phase 1 of refactoring:
- BASE_DIR
- GITHUB_REPO
- GITHUB_BRANCH
- All path constants

### Phase 2: Domain Data
Move with Phase 2:
- PLAYER_DICT
- TEG_ROUNDS
- TEG_OVERRIDES

### Phase 3: Everything Else
Clean up remaining constants

---

## Verification

After migration, verify:

```bash
# 1. No undefined name errors
python -m py_compile streamlit/**/*.py

# 2. All imports resolve
python -c "from teg_analysis.config.paths import ALL_SCORES_PARQUET"

# 3. No orphaned constants (defined but never imported)
# Run orphan detection script

# 4. No duplicate constants (same value, different names)
# Run duplicate detection script
```
```

---

## Constant Analysis Script

### analyze_constants.py

```python
"""
Analyze all constants in the codebase.

Finds:
- Module-level constant assignments
- Usage locations
- Potential duplicates
- Orphaned constants
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

def is_constant(name: str) -> bool:
    """Check if variable name follows constant convention."""
    return name.isupper() and not name.startswith('_')

def find_constants_in_file(file_path: str) -> List[Tuple[str, int, any]]:
    """
    Find all module-level constants in a Python file.

    Returns:
        List of (constant_name, line_number, value) tuples
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=file_path)
    except:
        return []

    constants = []

    for node in ast.walk(tree):
        # Only top-level assignments
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if is_constant(name):
                        # Try to get value
                        value = None
                        if isinstance(node.value, ast.Constant):
                            value = node.value.value
                        elif isinstance(node.value, ast.Dict):
                            value = "{...}"  # Dict, don't show full value
                        elif isinstance(node.value, ast.List):
                            value = "[...]"

                        constants.append((name, node.lineno, value))

    return constants

def find_all_constants(root_dir: str = "streamlit") -> Dict[str, List]:
    """
    Find all constants in all Python files.

    Returns:
        Dict mapping file_path -> [(name, line, value), ...]
    """
    constants_by_file = {}

    for py_file in Path(root_dir).rglob("*.py"):
        file_path = str(py_file)
        constants = find_constants_in_file(file_path)
        if constants:
            constants_by_file[file_path] = constants

    return constants_by_file

def find_constant_usage(constant_name: str, root_dir: str = "streamlit") -> List[str]:
    """
    Find all files that use a constant (via grep simulation).
    """
    usage_files = []

    for py_file in Path(root_dir).rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if constant_name in content:
                    # Crude check - could be in comment, string, etc.
                    # More sophisticated: parse and check for Name nodes
                    usage_files.append(str(py_file))
        except:
            pass

    return usage_files

def find_duplicates(constants_by_file: Dict) -> Dict[str, List[Tuple]]:
    """
    Find constants with same name defined in multiple files.

    Returns:
        Dict mapping constant_name -> [(file, line, value), ...]
    """
    name_to_locations = defaultdict(list)

    for file_path, constants in constants_by_file.items():
        for name, line, value in constants:
            name_to_locations[name].append((file_path, line, value))

    # Only keep names with >1 location
    duplicates = {
        name: locations
        for name, locations in name_to_locations.items()
        if len(locations) > 1
    }

    return duplicates

def generate_report(constants_by_file: Dict):
    """Generate markdown report."""

    print("# Complete Constants Inventory")
    print()
    print("**Generated:** 2025-10-19")
    print(f"**Files Scanned:** {len(constants_by_file)}")

    total_constants = sum(len(consts) for consts in constants_by_file.values())
    print(f"**Constants Found:** {total_constants}")
    print()

    # Find duplicates
    duplicates = find_duplicates(constants_by_file)

    print("## Summary Statistics")
    print()
    print(f"- Total constant definitions: {total_constants}")
    print(f"- Unique constant names: {len(set(name for consts in constants_by_file.values() for name, _, _ in consts))}")
    print(f"- Duplicate names: {len(duplicates)}")
    print()

    # Show duplicates
    if duplicates:
        print("## ⚠️ Duplicate Constants")
        print()
        for name, locations in sorted(duplicates.items()):
            print(f"### `{name}` (defined in {len(locations)} places)")
            print()
            for file_path, line, value in locations:
                value_str = f" = {value}" if value is not None else ""
                print(f"- `{file_path}:{line}`{value_str}")
            print()

    # Detailed inventory
    print("## Detailed Inventory by File")
    print()

    for file_path in sorted(constants_by_file.keys()):
        constants = constants_by_file[file_path]
        print(f"### {file_path} ({len(constants)} constants)")
        print()
        print("| Constant | Line | Value |")
        print("|----------|------|-------|")

        for name, line, value in sorted(constants, key=lambda x: x[1]):
            value_str = str(value)[:50] if value is not None else "N/A"
            print(f"| `{name}` | {line} | `{value_str}` |")

        print()

if __name__ == "__main__":
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else "streamlit"
    constants_by_file = find_all_constants(root)
    generate_report(constants_by_file)
```

### Running the Script

```bash
# Analyze all constants
python analyze_constants.py > docs/CONSTANTS_INVENTORY.md

# Review output
cat docs/CONSTANTS_INVENTORY.md
```

---

## Integration with Refactoring Plan

### Updated Migration Phases

**Phase 1: I/O Functions + Constants**
- Move I/O functions to `teg_analysis/io/`
- Move path constants to `teg_analysis/config/paths.py`
- Move BASE_DIR, GITHUB_REPO, GITHUB_BRANCH

**Phase 2: Data Loading + Domain Constants**
- Move data loading to `teg_analysis/core/`
- Move PLAYER_DICT to `teg_analysis/config/players.py`
- Move TEG_ROUNDS, etc. to `teg_analysis/config/tournaments.py`

**Phase 3: Analysis Functions**
- Check for constants in analysis modules
- Move with functions or import from config

**Phase 4: Final Cleanup**
- Remove all re-exports from utils.py
- Delete orphaned constants
- Consolidate final duplicates

---

## Success Criteria

Constants mapping considered complete when:

- [ ] All 119+ constants inventoried
- [ ] All usage locations documented
- [ ] All duplicates identified
- [ ] Migration plan for each constant
- [ ] No orphans (all defined constants are used)
- [ ] No hidden duplicates (same value, different names)
- [ ] Constants inventory integrated into refactoring plan

---

**Last Updated:** 2025-10-19
**Status:** GUIDE ACTIVE
**Part Of:** Pre-Refactoring Phase 1.5
