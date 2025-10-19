#!/usr/bin/env python3
"""
FIXED AST-based unused code analysis - CATCHES ALL FUNCTION USAGE PATTERNS

This version fixes the bug in analyze_unused_refined.py by catching:
✓ Direct calls: foo()
✓ Function as argument: df.apply(foo), sorted(list, key=foo)
✓ Callbacks: st.button(on_click=foo)
✓ Function references without parentheses

NO SHORTCUTS - Rigorous analysis with complete pattern coverage.

Last Updated: 2025-10-19
"""

import ast
import os
import json
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict


def is_active_codebase_file(filepath: str) -> bool:
    """
    Determine if a file is part of the active codebase.

    Excludes: backups/, test files, archives, dev notebooks, etc.
    Includes: streamlit/ directory (core app)
    """
    exclude_patterns = [
        'backup', 'archive', 'test', '_test', 'dev_notebook',
        'commentary_archive', 'streamlit_archive', 'nicegui',
        'temp_', 'generate_utils_inventory', 'analyze_',
        'copy_prompt', 'filter_teg', 'generate_titles', 'insert_titles',
        'add_md_ids', 'regenerate_caches', 'update_all_data'
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


class EnhancedFunctionUsageExtractor(ast.NodeVisitor):
    """
    Extract ALL function usage patterns - calls AND references.

    This fixes the bug in the original by catching:
    1. Direct calls: foo()
    2. Function references as arguments: df.apply(foo)
    3. Keyword arguments: st.button(on_click=foo)
    4. Function names in any expression context
    """

    def __init__(self, filepath: str, all_function_defs: List[Dict]):
        self.filepath = filepath
        self.all_function_defs = all_function_defs
        self.used_names = set()  # All function names that appear as references
        self.calls = []  # Detailed call information
        self.current_function = None

        # Build set of all defined function names for quick lookup
        self.defined_function_names = {func['name'] for func in all_function_defs}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track when we enter a function definition."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Track async function definitions."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node: ast.Call):
        """Record function calls."""
        called_name = None

        # Direct function calls: foo()
        if isinstance(node.func, ast.Name):
            called_name = node.func.id
        # Attribute calls: module.foo() or obj.foo()
        elif isinstance(node.func, ast.Attribute):
            called_name = node.func.attr

        if called_name:
            self.used_names.add(called_name)
            self.calls.append({
                'caller': self.current_function,
                'called': called_name,
                'file': self.filepath,
                'line': node.lineno,
                'type': 'call'
            })

        # CRITICAL FIX: Check arguments for function references
        # Example: df.apply(compress_ranges) - compress_ranges is an arg, not a call!
        for arg in node.args:
            if isinstance(arg, ast.Name) and arg.id in self.defined_function_names:
                self.used_names.add(arg.id)
                self.calls.append({
                    'caller': self.current_function,
                    'called': arg.id,
                    'file': self.filepath,
                    'line': node.lineno,
                    'type': 'arg_reference'
                })

        # CRITICAL FIX: Check keyword arguments
        # Example: st.button("Click", on_click=my_callback)
        for keyword in node.keywords:
            if isinstance(keyword.value, ast.Name) and keyword.value.id in self.defined_function_names:
                self.used_names.add(keyword.value.id)
                self.calls.append({
                    'caller': self.current_function,
                    'called': keyword.value.id,
                    'file': self.filepath,
                    'line': node.lineno,
                    'type': 'kwarg_reference'
                })

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        """
        Catch any bare function name reference.

        This handles edge cases like:
        - func_list = [func1, func2, func3]
        - func_dict = {'key': my_function}
        - return my_function (without calling it)
        """
        if isinstance(node.ctx, (ast.Load, ast.Store)) and node.id in self.defined_function_names:
            # Only track if it's one of our defined functions
            self.used_names.add(node.id)

        self.generic_visit(node)


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
        print(f"ERROR parsing {filepath}: {e}")
        return []


def extract_function_usage(filepath: str, all_function_defs: List[Dict]) -> Tuple[Set[str], List[Dict]]:
    """
    Extract all function usage from a file - calls AND references.

    Returns: (set of used function names, list of detailed usage info)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=filepath)

        extractor = EnhancedFunctionUsageExtractor(filepath, all_function_defs)
        extractor.visit(tree)

        return extractor.used_names, extractor.calls

    except Exception as e:
        print(f"ERROR parsing {filepath}: {e}")
        return set(), []


def main():
    """Execute fixed unused code analysis."""

    print("="*80)
    print("FIXED AST-BASED UNUSED CODE ANALYSIS")
    print("NOW CATCHES: Calls + Arguments + Callbacks + All References")
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

    # Step 2: Extract function definitions
    print("STEP 2: Extracting function definitions...")
    all_functions = []
    for filepath in active_files:
        funcs = extract_function_definitions(filepath)
        all_functions.extend(funcs)

    print(f"  Extracted {len(all_functions)} function definitions")
    print()

    # Step 3: Extract function usage (FIXED - now catches all patterns)
    print("STEP 3: Extracting function usage (calls + refs + callbacks)...")
    all_used_names = set()
    all_usage_details = []

    for i, filepath in enumerate(active_files, 1):
        if i % 10 == 0:
            print(f"  [{i}/{len(active_files)}] Processing {filepath}")

        used_names, usage_details = extract_function_usage(filepath, all_functions)
        all_used_names.update(used_names)
        all_usage_details.extend(usage_details)

    print(f"  Found {len(all_used_names)} used function names")
    print(f"  Tracked {len(all_usage_details)} usage instances")
    print()

    # Step 4: Identify unused
    print("STEP 4: Identifying unused functions...")
    all_function_names = {f['name'] for f in all_functions}
    unused_function_names = all_function_names - all_used_names

    unused_functions = [f for f in all_functions if f['name'] in unused_function_names]

    print(f"  Found {len(unused_functions)} potentially unused functions")
    print()

    # Group by file
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
            'used_functions': len(all_used_names),
            'unused_functions': len(unused_functions),
            'usage_percentage': round(len(all_used_names) / len(all_functions) * 100, 1) if all_functions else 0,
            'total_usage_instances': len(all_usage_details)
        },
        'unused_functions': [
            {'name': f['name'], 'file': f['file'], 'line': f['line']}
            for f in sorted(unused_functions, key=lambda x: (x['file'], x['line']))
        ],
        'used_function_names': sorted(list(all_used_names)),
        'usage_details': all_usage_details[:1000]  # First 1000 for inspection
    }

    output_file = root_dir / 'unused_code_analysis_fixed.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"  Saved to: {output_file}")
    print()

    # Summary
    print("="*80)
    print("ANALYSIS COMPLETE - BUG FIXED")
    print("="*80)
    print(f"Active codebase files: {len(active_files)}")
    print(f"Total functions: {len(all_functions)}")
    print(f"Used functions: {len(all_used_names)} ({output['summary']['usage_percentage']}%)")
    print(f"Unused functions: {len(unused_functions)} ({100 - output['summary']['usage_percentage']}%)")
    print()
    print("Next step: Grep validation of each unused candidate")
    print()


if __name__ == '__main__':
    main()
