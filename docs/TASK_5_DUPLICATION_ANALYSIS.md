# TASK 5: Duplication & Similarity Analysis

**Assigned To:** Subagent 5 / Manual Documentation
**Priority:** 🟡 MEDIUM
**Estimated Time:** 3-4 hours
**Status:** ⏳ NOT STARTED
**Prerequisites:** Tasks 1, 2 completed (need function inventory)

---

## Objective

Identify all duplicate and similar functions across the codebase:
- Exact duplicates (same code, different locations)
- Near duplicates (minor variations)
- Similar functionality (different implementations, same purpose)
- Consolidation opportunities

---

## Categories of Duplication

### 1. Exact Duplicates
Functions with identical or near-identical code in multiple locations.

**Example:**
```python
# utils.py
def format_vs_par(value):
    if value > 0:
        return f"+{value:.0f}"
    elif value < 0:
        return f"{value:.0f}"
    else:
        return "E"

# helpers/display.py
def format_vs_par(value):  # EXACT DUPLICATE
    if value > 0:
        return f"+{value:.0f}"
    elif value < 0:
        return f"{value:.0f}"
    else:
        return "E"
```

### 2. Near Duplicates
Functions with 80%+ code similarity but minor variations.

**Example:**
```python
# File A
def format_score(value, precision=0):
    if value > 0:
        return f"+{value:.{precision}f}"
    else:
        return f"{value:.{precision}f}"

# File B  
def format_score_value(value):  # NEAR DUPLICATE
    if value > 0:
        return f"+{value:.2f}"  # Different default precision
    else:
        return f"{value:.2f}"
```

### 3. Functional Duplicates
Different implementations of the same logical operation.

**Example:**
```python
# File A
def get_player_average(data, player):
    player_data = data[data['Player'] == player]
    return player_data['Score'].mean()

# File B
def calculate_player_avg(df, player_name):  # FUNCTIONAL DUPLICATE
    return df.loc[df['Player'] == player_name, 'Score'].mean()
```

### 4. Pattern Duplicates
Repeated code patterns that should be abstracted.

**Example:**
```python
# Multiple files have variations of:
teg_data = data[data['TEGNum'] == selected_teg]
round_data = teg_data[teg_data['Round'] == selected_round]
player_data = round_data[round_data['Player'] == selected_player]
# This filtering pattern appears 10+ times
```

---

## Documentation Template

For each duplicate group:

```markdown
## Duplicate Group: [Function Name/Pattern]

### Classification
**Type:** Exact | Near | Functional | Pattern
**Severity:** 🔴 Critical | 🟡 Moderate | 🟢 Minor

### Instances Found: X

#### Instance 1
- **File:** utils.py
- **Lines:** 145-160
- **Function Name:** format_vs_par()
- **Signature:** `def format_vs_par(value: float) -> str`
- **Used By:** 18 files

#### Instance 2  
- **File:** helpers/display_helpers.py
- **Lines:** 23-38
- **Function Name:** format_vs_par()
- **Signature:** `def format_vs_par(value: float) -> str`
- **Used By:** 5 files

#### Instance 3
- **File:** helpers/scoring_data_processing.py
- **Lines:** 12-27
- **Function Name:** format_vs_par_value()
- **Signature:** `def format_vs_par_value(value: float) -> str`
- **Used By:** 3 files

### Similarity Analysis
- Code similarity: 100% | 95% | 80%
- Logic similarity: 100%
- Same parameters: Yes/No
- Same return type: Yes/No
- Different edge cases: [List any differences]

### Impact Analysis
- Total usage count: 26 files
- If consolidated, affects: 26 import statements

### Consolidation Recommendation

**Canonical Location:** `teg_analysis/formatters/display.py`
**Canonical Name:** `format_vs_par()`
**Rationale:** Most used, clearest name, pure function

**Consolidation Steps:**
1. Move canonical version to new location
2. Update 26 files to import from new location
3. Remove duplicate implementations
4. Add tests to prevent future duplication

**Estimated Effort:** 1 hour

**Priority:** 🔴 HIGH - High usage, exact duplicates

### Notes
- This duplication likely arose from copy-paste during refactoring
- Should add linting rule to detect duplicates in future
```

---

## Detection Methods

### 1. Manual Code Review
- Read through utils.py and helpers
- Note similar function names
- Compare implementations

### 2. Automated Similarity Detection

**Using `diff`:**
```bash
# Extract function from multiple files
sed -n '/^def format_vs_par/,/^def /p' utils.py > func1.txt
sed -n '/^def format_vs_par/,/^def /p' helpers/display.py > func2.txt
diff -u func1.txt func2.txt
```

**Using Python AST:**
```python
import ast
import difflib

def extract_function_ast(filepath, function_name):
    """Extract AST for a specific function."""
    with open(filepath) as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return ast.unparse(node)
    return None

def compare_functions(file1, func1, file2, func2):
    """Compare two functions for similarity."""
    code1 = extract_function_ast(file1, func1)
    code2 = extract_function_ast(file2, func2)
    
    if code1 and code2:
        similarity = difflib.SequenceMatcher(None, code1, code2).ratio()
        return similarity * 100
    return 0
```

**Using code similarity tools:**
```bash
# Install duplication detection tool
pip install pylint

# Run duplication detection
pylint --disable=all --enable=duplicate-code streamlit/
```

### 3. Function Signature Analysis

Look for functions with:
- Same name (or very similar names)
- Same parameter types
- Same return types
- Similar line counts

```bash
# Extract all function signatures
grep -r "^def " streamlit/ | sort | uniq -c | sort -rn
```

---

## Common Duplication Patterns to Check

### Pattern 1: Data Loading Variations
```python
# Check for multiple implementations of:
- load_data()
- read_data()
- get_data()
- fetch_data()
```

### Pattern 2: Formatting Functions
```python
# Check for multiple implementations of:
- format_score()
- format_value()
- display_value()
- render_score()
```

### Pattern 3: Data Filtering
```python
# Check for repeated patterns:
data[data['TEGNum'] == teg]
data[data['Round'] == round]
data[data['Player'] == player]
```

### Pattern 4: Statistical Calculations
```python
# Check for multiple implementations of:
- calculate_average()
- get_mean()
- compute_avg()
```

### Pattern 5: DataFrame Operations
```python
# Check for repeated groupby/agg patterns:
df.groupby('Player').agg({'Score': 'mean'})
```

---

## Duplication Categories

### By Severity

#### 🔴 Critical (Must Fix)
- Exact duplicates with high usage (10+ files)
- Core business logic duplicated
- Data loading duplicates

#### 🟡 Moderate (Should Fix)
- Near duplicates with medium usage (5-10 files)
- Formatting function duplicates
- Helper function duplicates

#### 🟢 Minor (Nice to Fix)
- Low usage duplicates (< 5 files)
- One-off implementations
- Page-specific variations

### By Type

#### Code Duplicates
Functions with duplicate code

#### Logic Duplicates  
Functions with same logic, different code

#### Pattern Duplicates
Repeated code patterns that should be functions

---

## Consolidation Priority Matrix

| Duplicate | Usage | Similarity | Priority | Effort |
|-----------|-------|------------|----------|--------|
| format_vs_par | 26 files | 100% | 🔴 | 1 hour |
| load_data variations | 15 files | 80% | 🔴 | 2 hours |
| calculate_average | 8 files | 90% | 🟡 | 1 hour |
| filter_by_player | 6 files | 70% | 🟡 | 30 min |
| [Continue for all] | | | | |

---

## Consolidation Strategy

For each duplicate group, decide:

### Option 1: Consolidate to Single Function
- Choose canonical location
- Update all imports
- Remove duplicates
- **Best for:** Exact duplicates with same signature

### Option 2: Create Wrapper Functions
- Keep variations for backward compatibility
- Have them call a single implementation
- **Best for:** Near duplicates with different signatures

### Option 3: Create Base Function with Parameters
- Parameterize differences
- Update calls to include parameters
- **Best for:** Functional duplicates with variations

### Option 4: Accept Duplication (Document Why)
- Some duplication is intentional
- Different domains need different implementations
- **Best for:** Superficially similar but genuinely different logic

---

## Output Structure

```markdown
# Duplication Analysis Report

## Executive Summary
- Total duplicate groups found: XX
- Critical duplicates: XX
- Moderate duplicates: XX
- Minor duplicates: XX
- Total estimated consolidation effort: XX hours

## Critical Duplicates (Must Fix)
[Detailed analysis of each]

## Moderate Duplicates (Should Fix)
[Detailed analysis of each]

## Minor Duplicates (Nice to Fix)
[Detailed analysis of each]

## Consolidation Roadmap
1. Phase 1: Critical duplicates (X hours)
2. Phase 2: Moderate duplicates (X hours)
3. Phase 3: Minor duplicates (X hours)

## Prevention Recommendations
- Add linting rules
- Code review checklist
- Shared function guidelines
```

---

## Tools & Commands

### Find duplicate function names
```bash
# Extract all function names and find duplicates
grep -rh "^def " streamlit/ | cut -d'(' -f1 | sort | uniq -c | sort -rn
```

### Find similar function names
```bash
# Use fuzzy matching to find similar names
# (requires custom script or tool like fzf)
```

### Code similarity tools
```bash
# Various tools for detecting duplicate code
pip install radon  # Code metrics
pip install pycodestyle  # Style checker
pip install prospector  # Static analysis with duplication detection
```

---

## Success Criteria

- ✅ All duplicate groups identified
- ✅ Similarity percentages calculated
- ✅ Usage impact assessed
- ✅ Consolidation recommendations made
- ✅ Priority and effort estimated
- ✅ Consolidation roadmap created
- ✅ Prevention strategies recommended

---

## Output Files

- `DUPLICATES.md` - Complete duplication analysis
- `consolidation_roadmap.md` - Step-by-step consolidation plan
- `duplicate_matrix.csv` - Spreadsheet of all duplicates
