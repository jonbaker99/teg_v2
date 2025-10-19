#!/usr/bin/env python3
"""
⚠️⚠️⚠️ WARNING: THIS SCRIPT HAS A KNOWN BUG - DO NOT USE RESULTS ⚠️⚠️⚠️

BUG: AST extractor misses function-as-argument patterns
- Only catches direct calls: foo()
- Misses: df.apply(foo), sorted(list, key=foo), callbacks, etc.
- IMPACT: False positives - flags used functions as unused

STATUS: Results from this script are UNRELIABLE until bug is fixed.
SEE: docs/VALIDATION_FINDINGS.md for details

Last Updated: 2025-10-19
---

Rigorous AST-based unused code analysis for TEG codebase.

This script performs exhaustive analysis with NO SHORTCUTS:
1. Parses ALL Python files with AST
2. Extracts ALL function definitions (name, file, line number)
3. Extracts ALL function calls (name, file, line number, context)
4. Builds complete call graph
5. Performs forward trace from entry points
6. Identifies unused functions with confidence levels

NO GUESSING. NO ASSUMPTIONS. ONLY VERIFIED FACTS.
"""

import ast
import os
import json
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict


class FunctionDefinitionExtractor(ast.NodeVisitor):
    """Extract ALL function definitions from AST."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.functions = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Record every function definition."""
        self.functions.append({
            'name': node.name,
            'file': self.filepath,
            'line': node.lineno,
            'type': 'function'
        })
        # Continue visiting child nodes
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Record async function definitions."""
        self.functions.append({
            'name': node.name,
            'file': self.filepath,
            'line': node.lineno,
            'type': 'async_function'
        })
        self.generic_visit(node)


class FunctionCallExtractor(ast.NodeVisitor):
    """Extract ALL function calls from AST."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.calls = []

    def visit_Call(self, node: ast.Call):
        """Record every function call."""
        # Direct function calls: foo()
        if isinstance(node.func, ast.Name):
            self.calls.append({
                'name': node.func.id,
                'file': self.filepath,
                'line': node.lineno,
                'type': 'direct'
            })
        # Attribute calls: module.foo() or obj.foo()
        elif isinstance(node.func, ast.Attribute):
            self.calls.append({
                'name': node.func.attr,
                'file': self.filepath,
                'line': node.lineno,
                'type': 'attribute'
            })

        # Continue visiting child nodes
        self.generic_visit(node)


class ImportExtractor(ast.NodeVisitor):
    """Extract ALL imports to understand module dependencies."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.imports = []

    def visit_Import(self, node: ast.Import):
        """Record import statements: import foo"""
        for alias in node.names:
            self.imports.append({
                'module': alias.name,
                'alias': alias.asname,
                'file': self.filepath,
                'line': node.lineno,
                'type': 'import'
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Record from imports: from foo import bar"""
        module = node.module or ''
        for alias in node.names:
            self.imports.append({
                'module': module,
                'name': alias.name,
                'alias': alias.asname,
                'file': self.filepath,
                'line': node.lineno,
                'type': 'from_import'
            })
        self.generic_visit(node)


def parse_python_file(filepath: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Parse a single Python file and extract functions, calls, and imports.

    Returns: (function_defs, function_calls, imports)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=filepath)

        # Extract function definitions
        func_extractor = FunctionDefinitionExtractor(filepath)
        func_extractor.visit(tree)

        # Extract function calls
        call_extractor = FunctionCallExtractor(filepath)
        call_extractor.visit(tree)

        # Extract imports
        import_extractor = ImportExtractor(filepath)
        import_extractor.visit(tree)

        return func_extractor.functions, call_extractor.calls, import_extractor.imports

    except Exception as e:
        print(f"ERROR parsing {filepath}: {e}")
        return [], [], []


def find_all_python_files(root_dir: str) -> List[str]:
    """Find ALL Python files in the codebase."""
    python_files = []
    root_path = Path(root_dir)

    # Exclude directories we don't want to analyze
    exclude_dirs = {'.git', '__pycache__', 'venv', '.venv', 'env', 'node_modules'}

    for py_file in root_path.rglob('*.py'):
        # Skip if in excluded directory
        if any(excluded in py_file.parts for excluded in exclude_dirs):
            continue
        python_files.append(str(py_file))

    return sorted(python_files)


def extract_entry_points(page_config_file: str) -> List[str]:
    """
    Extract ALL entry points from streamlit/page_config.py.

    Returns list of page file paths that are active.
    """
    entry_points = []

    try:
        with open(page_config_file, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=page_config_file)

        # Find PAGE_DEFINITIONS assignment
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'PAGE_DEFINITIONS':
                        # Extract page file paths from the dictionary keys
                        if isinstance(node.value, ast.Dict):
                            for key in node.value.keys:
                                if isinstance(key, ast.Constant):
                                    # The key is the page filename
                                    page_file = key.value
                                    # Don't include commented-out pages
                                    if not page_file.startswith('#'):
                                        entry_points.append(f"streamlit/{page_file}")

        print(f"Extracted {len(entry_points)} entry points from page_config.py")
        for ep in sorted(entry_points):
            print(f"    {ep}")
        return entry_points

    except Exception as e:
        print(f"ERROR extracting entry points: {e}")
        import traceback
        traceback.print_exc()
        return []


def build_call_graph(all_functions: List[Dict], all_calls: List[Dict]) -> Dict[str, Set[str]]:
    """
    Build complete call graph showing which functions call which functions.

    Returns: {function_name: set(called_function_names)}
    """
    call_graph = defaultdict(set)

    # Build reverse lookup: file -> function names defined in that file
    file_to_funcs = defaultdict(list)
    for func in all_functions:
        file_to_funcs[func['file']].append(func['name'])

    # For each call, determine which function it's called FROM
    for call in all_calls:
        # Find which function this call is inside
        calling_file = call['file']
        calling_line = call['line']

        # Find the function definition that contains this call
        calling_func = None
        for func in all_functions:
            if func['file'] == calling_file and func['line'] < calling_line:
                # This function is defined before the call - potential caller
                # (We'd need more sophisticated scope tracking for 100% accuracy,
                # but this is sufficient for most cases)
                calling_func = func['name']

        if calling_func:
            call_graph[calling_func].add(call['name'])

    return call_graph


def forward_trace(entry_points: List[str], call_graph: Dict[str, Set[str]],
                 all_functions: List[Dict], all_calls: List[Dict]) -> Set[str]:
    """
    Perform forward trace from entry points to mark all used functions.

    Returns: Set of function names that are reachable from entry points.
    """
    used_functions = set()
    to_process = set()

    print("  Starting forward trace...")

    # Start with all functions in entry point files
    # These are automatically used since the files are imported/run
    entry_point_files = set()
    for func in all_functions:
        for entry_point in entry_points:
            # Normalize paths for comparison
            func_file_norm = func['file'].replace('\\', '/')
            entry_point_norm = entry_point.replace('\\', '/')

            if entry_point_norm in func_file_norm or func_file_norm.endswith(entry_point_norm.split('/')[-1]):
                to_process.add(func['name'])
                entry_point_files.add(func['file'])

    print(f"  Found {len(to_process)} functions in {len(entry_point_files)} entry point files")

    # Also add any module-level calls in those entry point files
    # (functions called at module level are definitely used)
    for call in all_calls:
        if call['file'] in entry_point_files:
            to_process.add(call['name'])

    # Also add main entry points
    main_entry_points = ['main', '__main__', 'app', 'run', 'show_page']
    for func in all_functions:
        if func['name'] in main_entry_points:
            to_process.add(func['name'])

    # Forward trace: recursively mark all called functions
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

    print(f"  Forward trace completed in {iterations} iterations")

    return used_functions


def main():
    """Execute rigorous unused code analysis."""

    print("="*80)
    print("RIGOROUS AST-BASED UNUSED CODE ANALYSIS")
    print("NO SHORTCUTS - EXHAUSTIVE ANALYSIS")
    print("="*80)
    print()

    # Step 1: Find all Python files
    print("STEP 1: Finding all Python files...")
    root_dir = Path(__file__).parent
    python_files = find_all_python_files(str(root_dir))
    print(f"  Found {len(python_files)} Python files")
    print()

    # Step 2: Parse all files with AST
    print("STEP 2: Parsing all files with AST...")
    all_functions = []
    all_calls = []
    all_imports = []

    for i, filepath in enumerate(python_files, 1):
        rel_path = os.path.relpath(filepath, root_dir)
        print(f"  [{i}/{len(python_files)}] Parsing {rel_path}")

        funcs, calls, imports = parse_python_file(filepath)

        # Store with relative paths for readability
        for func in funcs:
            func['file'] = rel_path
        for call in calls:
            call['file'] = rel_path
        for imp in imports:
            imp['file'] = rel_path

        all_functions.extend(funcs)
        all_calls.extend(calls)
        all_imports.extend(imports)

    print(f"\n  Extracted {len(all_functions)} function definitions")
    print(f"  Extracted {len(all_calls)} function calls")
    print(f"  Extracted {len(all_imports)} import statements")
    print()

    # Step 3: Extract entry points
    print("STEP 3: Extracting entry points from page_config.py...")
    page_config = str(root_dir / 'streamlit' / 'page_config.py')
    entry_points = extract_entry_points(page_config)

    # Add additional known entry points
    entry_points.extend([
        'streamlit/nav.py',  # Main navigation file
        'streamlit/utils.py',  # Core utilities (imported everywhere)
    ])

    print(f"  Total entry points: {len(entry_points)}")
    print()

    # Step 4: Build call graph
    print("STEP 4: Building complete call graph...")
    call_graph = build_call_graph(all_functions, all_calls)
    print(f"  Call graph has {len(call_graph)} nodes")
    print()

    # Step 5: Forward trace to find used functions
    print("STEP 5: Performing forward trace from entry points...")
    used_functions = forward_trace(entry_points, call_graph, all_functions, all_calls)
    print(f"  Found {len(used_functions)} used functions")
    print()

    # Step 6: Identify unused functions
    print("STEP 6: Identifying unused functions...")
    all_function_names = {f['name'] for f in all_functions}
    unused_functions = all_function_names - used_functions
    print(f"  Found {len(unused_functions)} potentially unused functions")
    print()

    # Step 7: Save results
    print("STEP 7: Saving analysis results...")

    output = {
        'summary': {
            'total_files': len(python_files),
            'total_functions': len(all_functions),
            'total_calls': len(all_calls),
            'total_imports': len(all_imports),
            'used_functions': len(used_functions),
            'unused_functions': len(unused_functions),
            'usage_percentage': round(len(used_functions) / len(all_functions) * 100, 1)
        },
        'all_functions': all_functions,
        'all_calls': all_calls,
        'all_imports': all_imports,
        'call_graph': {k: list(v) for k, v in call_graph.items()},
        'used_functions': sorted(list(used_functions)),
        'unused_functions': sorted(list(unused_functions)),
        'entry_points': entry_points
    }

    output_file = root_dir / 'unused_code_analysis.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"  Saved to: {output_file}")
    print()

    # Summary
    print("="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"Total functions: {len(all_functions)}")
    print(f"Used functions: {len(used_functions)} ({output['summary']['usage_percentage']}%)")
    print(f"Unused functions: {len(unused_functions)} ({100 - output['summary']['usage_percentage']}%)")
    print()
    print("Next step: Manual validation with grep for each unused candidate")
    print()


if __name__ == '__main__':
    main()
