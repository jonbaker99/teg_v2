#!/usr/bin/env python3
"""
SIMPLIFIED AST-based unused code analysis - MOST RELIABLE APPROACH

This version uses the simplest possible logic:
- If a function name appears ANYWHERE in active codebase → USED
- No complex call graphs, no entry point tracing
- Just: defined_functions - used_names = unused

This eliminates import tracking bugs and edge cases.

Last Updated: 2025-10-19
Version: 3 (Simplified)
"""

import ast
import os
import json
from pathlib import Path
from typing import Dict, Set, List
from collections import defaultdict


def is_active_codebase_file(filepath: str) -> bool:
    """
    Determine if a file is part of the active codebase.

    Excludes: backups/, test files, archives, dev notebooks, etc.
    Includes: streamlit/ directory (core app)
    """
    exclude_patterns = [
        'backup', 'archive', '_test', 'dev_notebook',
        'commentary_archive', 'streamlit_archive', 'nicegui',
        'temp_', 'generate_utils_inventory', 'analyze_',
        'copy_prompt', 'filter_teg', 'generate_titles', 'insert_titles',
        'add_md_ids', 'regenerate_caches', 'update_all_data',
        '\\test_', '\\test.'  # Only exclude files starting with test_
    ]

    # Only include files in streamlit/ directory
    if not filepath.startswith('streamlit' + os.sep):
        return False

    # Exclude files matching patterns
    filepath_lower = filepath.lower()
    for pattern in exclude_patterns:
        if pattern in filepath_lower:
            return False

    return True


def extract_all_function_names_in_code(filepath: str, defined_function_names: Set[str]) -> Set[str]:
    """
    Extract ALL occurrences of function names in a file.

    SIMPLIFIED: Just find all Name nodes that match our defined functions.
    No complex tracking - if the name appears, the function is used.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=filepath)

        used_names = set()

        # Walk ALL nodes in the tree
        for node in ast.walk(tree):
            # Check any Name node (variable, function call, argument, etc.)
            if isinstance(node, ast.Name):
                if node.id in defined_function_names:
                    used_names.add(node.id)

            # Also check attribute access (obj.function_name)
            elif isinstance(node, ast.Attribute):
                if node.attr in defined_function_names:
                    used_names.add(node.attr)

        return used_names

    except Exception as e:
        print(f"  ERROR parsing {filepath}: {e}")
        return set()


def extract_function_definitions(filepath: str) -> List[Dict]:
    """Extract all function definitions from a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=filepath)

        functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({
                    'name': node.name,
                    'file': filepath,
                    'line': node.lineno
                })

        return functions

    except Exception as e:
        print(f"  ERROR parsing {filepath}: {e}")
        return []


def main():
    """Execute simplified unused code analysis."""

    print("="*80)
    print("SIMPLIFIED AST-BASED UNUSED CODE ANALYSIS")
    print("Logic: If name appears ANYWHERE in active code -> USED")
    print("="*80)
    print()

    root_dir = Path(__file__).parent

    # Step 1: Find active codebase files
    print("STEP 1: Finding active codebase files...")
    all_python_files = list(root_dir.rglob('*.py'))
    active_files = []

    for py_file in all_python_files:
        rel_path = os.path.relpath(py_file, root_dir)
        if is_active_codebase_file(rel_path):
            active_files.append(rel_path)

    print(f"  Found {len(active_files)} active codebase files")
    print()

    # Step 2: Extract ALL function definitions
    print("STEP 2: Extracting all function definitions...")
    all_functions = []
    for filepath in active_files:
        funcs = extract_function_definitions(filepath)
        all_functions.extend(funcs)

    all_function_names = {f['name'] for f in all_functions}
    print(f"  Extracted {len(all_functions)} function definitions")
    print(f"  Unique function names: {len(all_function_names)}")
    print()

    # Step 3: Find ALL occurrences of those function names in code
    print("STEP 3: Finding all occurrences of function names in code...")
    all_used_names = set()

    for i, filepath in enumerate(active_files, 1):
        if i % 10 == 0:
            print(f"  [{i}/{len(active_files)}] Processing {filepath}")

        used_in_file = extract_all_function_names_in_code(filepath, all_function_names)
        all_used_names.update(used_in_file)

    print(f"  Found {len(all_used_names)} function names used in code")
    print()

    # Step 4: Calculate unused (SIMPLE!)
    print("STEP 4: Calculating unused functions...")
    unused_function_names = all_function_names - all_used_names

    # Get full details
    unused_functions = [f for f in all_functions if f['name'] in unused_function_names]

    print(f"  Found {len(unused_functions)} potentially unused functions")
    print()

    # Group by file for display
    unused_by_file = defaultdict(list)
    for func in unused_functions:
        unused_by_file[func['file']].append(func)

    print("  Unused functions by file:")
    for file in sorted(unused_by_file.keys()):
        funcs = unused_by_file[file]
        print(f"    {file}: {len(funcs)} functions")
        for func in sorted(funcs, key=lambda x: x['line']):
            print(f"      - {func['name']} (line {func['line']})")
    print()

    # Step 5: Save results
    print("STEP 5: Saving results...")
    output = {
        'summary': {
            'active_files': len(active_files),
            'total_functions': len(all_functions),
            'unique_function_names': len(all_function_names),
            'used_functions': len(all_used_names),
            'unused_functions': len(unused_functions),
            'usage_percentage': round(len(all_used_names) / len(all_function_names) * 100, 1) if all_function_names else 0
        },
        'unused_functions': [
            {'name': f['name'], 'file': f['file'], 'line': f['line']}
            for f in sorted(unused_functions, key=lambda x: (x['file'], x['line']))
        ],
        'used_function_names': sorted(list(all_used_names)),
        'all_function_names': sorted(list(all_function_names))
    }

    output_file = root_dir / 'unused_code_analysis_simple.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"  Saved to: {output_file}")
    print()

    # Summary
    print("="*80)
    print("ANALYSIS COMPLETE - SIMPLIFIED LOGIC")
    print("="*80)
    print(f"Active codebase files: {len(active_files)}")
    print(f"Total functions: {len(all_functions)}")
    print(f"Unique function names: {len(all_function_names)}")
    print(f"Used functions: {len(all_used_names)} ({output['summary']['usage_percentage']}%)")
    print(f"Unused functions: {len(unused_functions)} ({100 - output['summary']['usage_percentage']}%)")
    print()
    print("Next step: Grep validation of ALL unused candidates")
    print()


if __name__ == '__main__':
    main()
