"""
Analyze all constants in the codebase.

Finds:
- Module-level constant assignments
- Usage locations
- Potential duplicates
- Orphaned constants

Usage:
    python analyze_constants.py > docs/CONSTANTS_INVENTORY.md
    python analyze_constants.py streamlit > docs/CONSTANTS_INVENTORY.md
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any

def is_constant(name: str) -> bool:
    """Check if variable name follows constant convention."""
    return name.isupper() and not name.startswith('_')

def find_constants_in_file(file_path: str) -> List[Tuple[str, int, Any]]:
    """
    Find all module-level constants in a Python file.

    Returns:
        List of (constant_name, line_number, value) tuples
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=file_path)
    except Exception as e:
        print(f"<!-- Error parsing {file_path}: {e} -->")
        return []

    constants = []

    # Only look at module-level assignments
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if is_constant(name):
                        # Try to get value
                        value = None
                        if isinstance(node.value, ast.Constant):
                            value = repr(node.value.value)
                        elif isinstance(node.value, ast.Dict):
                            # Count dict items
                            n_items = len(node.value.keys)
                            value = f"{{...}} ({n_items} items)"
                        elif isinstance(node.value, ast.List):
                            n_items = len(node.value.elts)
                            value = f"[...] ({n_items} items)"
                        elif isinstance(node.value, ast.Call):
                            # Function call
                            if isinstance(node.value.func, ast.Name):
                                value = f"{node.value.func.id}()"
                            elif isinstance(node.value.func, ast.Attribute):
                                value = f"<function call>"
                        elif isinstance(node.value, ast.BinOp):
                            value = "<binary operation>"
                        else:
                            value = f"<{type(node.value).__name__}>"

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
        # Skip __pycache__ and other generated files
        if '__pycache__' in str(py_file):
            continue

        file_path = str(py_file)
        constants = find_constants_in_file(file_path)
        if constants:
            constants_by_file[file_path] = constants

    return constants_by_file

def find_constant_usage(constant_name: str, root_dir: str = "streamlit") -> List[str]:
    """
    Find all files that use a constant (via simple text search).

    Note: This is a simple search and may have false positives
    (e.g., constant name in comments or strings).
    """
    usage_files = []

    for py_file in Path(root_dir).rglob("*.py"):
        if '__pycache__' in str(py_file):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if constant_name in content:
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

def categorize_constants(constants_by_file: Dict) -> Dict[str, List]:
    """
    Categorize constants by type/purpose.
    """
    categories = {
        'paths': [],
        'config': [],
        'data': [],
        'other': []
    }

    path_keywords = ['PATH', 'DIR', 'FILE', 'CSV', 'PARQUET', 'URL']
    config_keywords = ['REPO', 'BRANCH', 'TOTAL', 'MAX', 'MIN']
    data_keywords = ['DICT', 'ROUNDS', 'OVERRIDE', 'PLAYER']

    for file_path, constants in constants_by_file.items():
        for name, line, value in constants:
            categorized = False

            if any(kw in name for kw in path_keywords):
                categories['paths'].append((name, file_path, line))
                categorized = True
            elif any(kw in name for kw in data_keywords):
                categories['data'].append((name, file_path, line))
                categorized = True
            elif any(kw in name for kw in config_keywords):
                categories['config'].append((name, file_path, line))
                categorized = True

            if not categorized:
                categories['other'].append((name, file_path, line))

    return categories

def generate_report(constants_by_file: Dict, root_dir: str):
    """Generate markdown report."""
    from datetime import datetime

    print("# Complete Constants Inventory")
    print()
    print(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"**Directory Scanned:** `{root_dir}/`")
    print(f"**Files with Constants:** {len(constants_by_file)}")

    total_constants = sum(len(consts) for consts in constants_by_file.values())
    print(f"**Total Constants Found:** {total_constants}")
    print()

    # Find duplicates
    duplicates = find_duplicates(constants_by_file)

    # Categorize
    categories = categorize_constants(constants_by_file)

    print("---")
    print()
    print("## Summary Statistics")
    print()
    print(f"- **Total constant definitions:** {total_constants}")

    unique_names = set(name for consts in constants_by_file.values() for name, _, _ in consts)
    print(f"- **Unique constant names:** {len(unique_names)}")
    print(f"- **Duplicate names:** {len(duplicates)}")
    print()

    print("### By Category")
    print()
    print("| Category | Count | Migration Target |")
    print("|----------|-------|------------------|")
    print(f"| Path Constants | {len(categories['paths'])} | `teg_analysis/config/paths.py` |")
    print(f"| Configuration | {len(categories['config'])} | `teg_analysis/config/constants.py` |")
    print(f"| Domain Data | {len(categories['data'])} | Domain-specific modules |")
    print(f"| Other | {len(categories['other'])} | TBD |")
    print()

    # Show duplicates
    if duplicates:
        print("---")
        print()
        print("## ⚠️ Duplicate Constants (Same Name, Multiple Definitions)")
        print()
        print(f"Found **{len(duplicates)}** constant names defined in multiple locations.")
        print()

        for name, locations in sorted(duplicates.items()):
            print(f"### `{name}` ({len(locations)} definitions)")
            print()
            print("| File | Line | Value |")
            print("|------|------|-------|")

            for file_path, line, value in locations:
                value_str = str(value)[:80] if value is not None else "N/A"
                print(f"| `{file_path}` | {line} | `{value_str}` |")

            print()
            print("**Action:** Consolidate to single canonical definition.")
            print()

    # Constants by category
    print("---")
    print()
    print("## Constants by Category")
    print()

    for category_name, category_display in [
        ('paths', 'Path Constants'),
        ('config', 'Configuration Constants'),
        ('data', 'Domain Data Constants'),
        ('other', 'Other Constants')
    ]:
        items = categories[category_name]
        if items:
            print(f"### {category_display} ({len(items)})")
            print()
            print("| Constant | File | Line |")
            print("|----------|------|------|")

            for name, file_path, line in sorted(items):
                print(f"| `{name}` | `{file_path}` | {line} |")

            print()

    # Detailed inventory
    print("---")
    print()
    print("## Detailed Inventory by File")
    print()

    for file_path in sorted(constants_by_file.keys()):
        constants = constants_by_file[file_path]
        rel_path = file_path.replace('\\', '/')

        print(f"### `{rel_path}` ({len(constants)} constants)")
        print()
        print("| Constant | Line | Value | Type |")
        print("|----------|------|-------|------|")

        for name, line, value in sorted(constants, key=lambda x: x[1]):
            value_str = str(value)[:60] if value is not None else "N/A"

            # Determine type
            const_type = "other"
            if 'PATH' in name or 'DIR' in name or 'FILE' in name:
                const_type = "path"
            elif 'DICT' in name or 'ROUNDS' in name:
                const_type = "data"
            elif 'REPO' in name or 'BRANCH' in name:
                const_type = "config"

            print(f"| `{name}` | {line} | `{value_str}` | {const_type} |")

        print()

    # Migration recommendations
    print("---")
    print()
    print("## Migration Recommendations")
    print()
    print("### Priority 1: Path Constants (CRITICAL)")
    print()
    print("**Target:** `teg_analysis/config/paths.py`")
    print()
    print("These must move WITH I/O functions:")
    for name, file_path, line in sorted(categories['paths'])[:10]:
        print(f"- `{name}` from `{file_path}:{line}`")
    if len(categories['paths']) > 10:
        print(f"- ... and {len(categories['paths']) - 10} more")
    print()

    print("### Priority 2: Configuration Constants")
    print()
    print("**Target:** `teg_analysis/config/constants.py`")
    print()
    for name, file_path, line in sorted(categories['config'])[:10]:
        print(f"- `{name}` from `{file_path}:{line}`")
    if len(categories['config']) > 10:
        print(f"- ... and {len(categories['config']) - 10} more")
    print()

    print("### Priority 3: Domain Data")
    print()
    print("**Target:** Domain-specific modules (e.g., `players.py`, `tournaments.py`)")
    print()
    for name, file_path, line in sorted(categories['data'])[:10]:
        print(f"- `{name}` from `{file_path}:{line}`")
    if len(categories['data']) > 10:
        print(f"- ... and {len(categories['data']) - 10} more")
    print()

    print("---")
    print()
    print("## Next Steps")
    print()
    print("1. **Review duplicates** - Consolidate to single definitions")
    print("2. **Plan migration** - Use [CONSTANTS_MAPPING_GUIDE.md](CONSTANTS_MAPPING_GUIDE.md)")
    print("3. **Update PRE_REFACTORING_PLAN.md** - Add Phase 1.5 (Constants Mapping)")
    print("4. **Prevent orphans** - Ensure constants move WITH functions that use them")
    print()
    print("---")
    print()
    print(f"**Report generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"**For details, see:** [CONSTANTS_MAPPING_GUIDE.md](CONSTANTS_MAPPING_GUIDE.md)")

if __name__ == "__main__":
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else "streamlit"

    print(f"<!-- Analyzing constants in {root}/ -->", file=sys.stderr)
    constants_by_file = find_all_constants(root)
    print(f"<!-- Found {len(constants_by_file)} files with constants -->", file=sys.stderr)

    generate_report(constants_by_file, root)
