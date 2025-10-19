#!/usr/bin/env python3
"""
REFINED AST-based unused code analysis - ACTIVE CODEBASE ONLY.

Focus exclusively on streamlit/ directory (exclude backups, tests, archives).
NO SHORTCUTS - Rigorous analysis with proper scope tracking.
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


class ScopedFunctionCallExtractor(ast.NodeVisitor):
    """
    Extract function calls AND track which function they're called FROM.

    This provides proper scope tracking for building accurate call graphs.
    """

    def __init__(self, filepath: str, all_function_defs: List[Dict]):
        self.filepath = filepath
        self.all_function_defs = all_function_defs
        self.calls = []
        self.current_function = None  # Track which function we're currently inside

        # Build lookup: line number -> function name for this file
        self.line_to_func = {}
        for func in all_function_defs:
            if func['file'] == filepath:
                self.line_to_func[func['line']] = func['name']

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track when we enter a function definition."""
        old_function = self.current_function
        self.current_function = node.name

        # Visit child nodes
        self.generic_visit(node)

        # Restore previous function when we exit
        self.current_function = old_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Track async function definitions."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node: ast.Call):
        """Record function call with proper caller context."""
        called_name = None

        # Direct function calls: foo()
        if isinstance(node.func, ast.Name):
            called_name = node.func.id
        # Attribute calls: module.foo() or obj.foo()
        elif isinstance(node.func, ast.Attribute):
            called_name = node.func.attr

        if called_name:
            self.calls.append({
                'caller': self.current_function,  # Function this call is inside (or None for module-level)
                'called': called_name,
                'file': self.filepath,
                'line': node.lineno
            })

        # Continue visiting child nodes
        self.generic_visit(node)


def parse_file_with_scope(filepath: str, all_function_defs: List[Dict]) -> List[Dict]:
    """
    Parse a file and extract function calls WITH scope information.

    Returns list of calls with caller/called information.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=filepath)

        extractor = ScopedFunctionCallExtractor(filepath, all_function_defs)
        extractor.visit(tree)

        return extractor.calls

    except Exception as e:
        print(f"ERROR parsing {filepath}: {e}")
        return []


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


def build_scoped_call_graph(scoped_calls: List[Dict]) -> Dict[str, Set[str]]:
    """
    Build call graph from scoped calls.

    Returns: {function_name: set(called_function_names)}
    """
    call_graph = defaultdict(set)

    for call in scoped_calls:
        caller = call['caller']
        called = call['called']

        if caller:  # Inside a function
            call_graph[caller].add(called)
        else:  # Module-level call (treat as entry point)
            call_graph['__module_level__'].add(called)

    return call_graph


def forward_trace_refined(entry_points: List[str], call_graph: Dict[str, Set[str]],
                         all_functions: List[Dict], scoped_calls: List[Dict]) -> Set[str]:
    """
    Perform forward trace with proper scope tracking.

    Returns set of used function names.
    """
    used_functions = set()
    to_process = set()

    print("  Starting refined forward trace...")

    # 1. Add all functions in entry point files (these are automatically used)
    entry_point_files = set()
    for func in all_functions:
        for entry_point in entry_points:
            func_file_norm = func['file'].replace('\\', '/')
            entry_point_norm = entry_point.replace('\\', '/')

            if entry_point_norm in func_file_norm or func_file_norm.endswith(entry_point_norm.split('/')[-1]):
                to_process.add(func['name'])
                entry_point_files.add(func['file'])

    print(f"  Found {len(to_process)} functions in {len(entry_point_files)} entry point files")

    # 2. Add module-level calls in entry point files
    for call in scoped_calls:
        if call['file'] in entry_point_files and call['caller'] is None:
            to_process.add(call['called'])

    # 3. Add utils.py functions (imported everywhere - treat as entry points)
    for func in all_functions:
        if 'utils.py' in func['file']:
            to_process.add(func['name'])

    print(f"  Total seed functions: {len(to_process)}")

    # 4. Forward trace
    iterations = 0
    while to_process:
        iterations += 1
        func_name = to_process.pop()

        if func_name in used_functions:
            continue

        used_functions.add(func_name)

        # Add all functions called by this function
        if func_name in call_graph:
            for called_func in call_graph[func_name]:
                if called_func not in used_functions:
                    to_process.add(called_func)

        # Also check module-level calls
        if '__module_level__' in call_graph:
            for called_func in call_graph['__module_level__']:
                if called_func not in used_functions:
                    to_process.add(called_func)

    print(f"  Forward trace completed in {iterations} iterations")

    return used_functions


def main():
    """Execute refined unused code analysis."""

    print("="*80)
    print("REFINED AST-BASED UNUSED CODE ANALYSIS")
    print("ACTIVE CODEBASE ONLY (streamlit/ directory)")
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

    print(f"  Found {len(active_files)} active codebase files (filtered from {len(all_python_files)} total)")
    print()

    # Step 2: Extract function definitions
    print("STEP 2: Extracting function definitions...")
    all_functions = []
    for filepath in active_files:
        funcs = extract_function_definitions(filepath)
        all_functions.extend(funcs)

    print(f"  Extracted {len(all_functions)} function definitions")
    print()

    # Step 3: Extract scoped function calls
    print("STEP 3: Extracting function calls with scope tracking...")
    scoped_calls = []
    for i, filepath in enumerate(active_files, 1):
        if i % 10 == 0:
            print(f"  [{i}/{len(active_files)}] Processing {filepath}")
        calls = parse_file_with_scope(filepath, all_functions)
        scoped_calls.extend(calls)

    print(f"  Extracted {len(scoped_calls)} function calls")
    print()

    # Step 4: Extract entry points
    print("STEP 4: Extracting entry points...")
    page_config = str(root_dir / 'streamlit' / 'page_config.py')

    # Read PAGE_DEFINITIONS
    with open(page_config, 'r', encoding='utf-8') as f:
        content = f.read()
    tree = ast.parse(content)

    entry_points = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'PAGE_DEFINITIONS':
                    if isinstance(node.value, ast.Dict):
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant):
                                page_file = key.value
                                entry_points.append(f"streamlit/{page_file}")

    # Add nav.py as main entry point
    entry_points.append('streamlit/nav.py')

    print(f"  Found {len(entry_points)} entry points")
    print()

    # Step 5: Build call graph
    print("STEP 5: Building scoped call graph...")
    call_graph = build_scoped_call_graph(scoped_calls)
    print(f"  Call graph has {len(call_graph)} nodes")
    print()

    # Step 6: Forward trace
    print("STEP 6: Performing forward trace...")
    used_functions = forward_trace_refined(entry_points, call_graph, all_functions, scoped_calls)
    print(f"  Found {len(used_functions)} used functions")
    print()

    # Step 7: Identify unused
    print("STEP 7: Identifying unused functions...")
    all_function_names = {f['name'] for f in all_functions}
    unused_function_names = all_function_names - used_functions

    # Get full details for unused functions
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

    # Step 8: Save results
    print("STEP 8: Saving results...")
    output = {
        'summary': {
            'active_files': len(active_files),
            'total_functions': len(all_functions),
            'total_calls': len(scoped_calls),
            'used_functions': len(used_functions),
            'unused_functions': len(unused_functions),
            'usage_percentage': round(len(used_functions) / len(all_functions) * 100, 1) if all_functions else 0
        },
        'unused_functions': [
            {'name': f['name'], 'file': f['file'], 'line': f['line']}
            for f in sorted(unused_functions, key=lambda x: (x['file'], x['line']))
        ],
        'used_function_names': sorted(list(used_functions)),
        'all_function_names': sorted(list(all_function_names))
    }

    output_file = root_dir / 'unused_code_analysis_refined.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"  Saved to: {output_file}")
    print()

    # Summary
    print("="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"Active codebase files: {len(active_files)}")
    print(f"Total functions: {len(all_functions)}")
    print(f"Used functions: {len(used_functions)} ({output['summary']['usage_percentage']}%)")
    print(f"Unused functions: {len(unused_functions)} ({100 - output['summary']['usage_percentage']}%)")
    print()
    print("Next step: Manual grep validation of each unused candidate")
    print()


if __name__ == '__main__':
    main()
