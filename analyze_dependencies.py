#!/usr/bin/env python3
"""
Analyze Python imports and function calls to create dependency graph.
Generates JSON output for dependency mapping documentation.
"""

import ast
import json
import os
from pathlib import Path
from collections import defaultdict
import re

class ImportAnalyzer(ast.NodeVisitor):
    """Extract imports from a Python file."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.imports = []
        self.internal_imports = []  # imports from streamlit/
        self.external_imports = []
        self.functions_defined = []
        self.function_calls = defaultdict(set)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
            if 'streamlit' in alias.name or 'helpers' in alias.name:
                self.internal_imports.append(alias.name)
            else:
                self.external_imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ''
        for alias in node.names:
            full_import = f"{module}.{alias.name}" if module else alias.name
            self.imports.append(full_import)
            if 'streamlit' in module or 'helpers' in module or module == 'utils':
                self.internal_imports.append(full_import)
            else:
                self.external_imports.append(full_import)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.functions_defined.append(node.name)
        self.generic_visit(node)

    def visit_Call(self, node):
        # Track function calls
        if isinstance(node.func, ast.Name):
            self.function_calls[node.func.id].add('local')
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                self.function_calls[node.func.attr].add(f"{node.func.value.id}.")
        self.generic_visit(node)


def analyze_file(filepath):
    """Extract dependencies from a Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                print(f"Syntax error in {filepath}: {e}")
                return None

        analyzer = ImportAnalyzer(filepath)
        analyzer.visit(tree)

        rel_path = str(filepath).replace('\\', '/')

        return {
            'filepath': rel_path,
            'imports': list(set(analyzer.imports)),
            'internal_imports': list(set(analyzer.internal_imports)),
            'external_imports': list(set(analyzer.external_imports)),
            'functions_defined': analyzer.functions_defined,
            'functions_called': {k: list(v) for k, v in analyzer.function_calls.items()}
        }
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return None


def find_function_calls_with_grep(pattern, directory):
    """Use regex to find function calls in files."""
    results = defaultdict(list)

    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ and .git
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', '.venv', 'venv')]

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_no, line in enumerate(f, 1):
                            if re.search(pattern, line):
                                rel_path = filepath.replace('\\', '/')
                                results[rel_path].append((line_no, line.strip()))
                except:
                    pass

    return results


def build_complete_graph(root_dir):
    """Build complete dependency graph for the codebase."""
    graph = {
        'files': {},
        'imports': defaultdict(list),  # import_name -> [files that import it]
        'functions': defaultdict(list)  # function_name -> [files that define it]
    }

    # Analyze all Python files
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', '.venv', 'venv', 'commentary')]

        for file in files:
            if file.endswith('.py') and not file.startswith('.'):
                filepath = os.path.join(root, file)
                result = analyze_file(filepath)

                if result:
                    rel_path = result['filepath']
                    graph['files'][rel_path] = result

                    # Track which files import what
                    for imp in result['internal_imports']:
                        graph['imports'][imp].append(rel_path)

                    # Track which files define functions
                    for func in result['functions_defined']:
                        graph['functions'][f"{rel_path}::{func}"].append(rel_path)

    return graph


def analyze_critical_functions(graph):
    """Identify most-used functions from utils and helpers."""
    critical_functions = {
        'utils.load_all_data': 0,
        'utils.format_vs_par': 0,
        'utils.add_cumulative_scores': 0,
        'utils.add_rankings_and_gaps': 0,
        'utils.get_teg_winners': 0,
        'utils.aggregate_data': 0,
        'utils.read_file': 0,
        'utils.write_file': 0,
    }

    # Find usage of these functions
    usage = defaultdict(int)

    streamlit_dir = os.path.join(os.path.dirname(graph['files'].get(list(graph['files'].keys())[0], {}).get('filepath', '')), '..')
    if streamlit_dir.endswith('..'):
        streamlit_dir = 'streamlit'

    for filepath in graph['files']:
        for func_name in critical_functions.keys():
            # Count occurrences in imports
            if func_name in graph['files'][filepath].get('internal_imports', []):
                usage[func_name] += 1

    return dict(sorted(usage.items(), key=lambda x: x[1], reverse=True))


def detect_circular_dependencies(graph):
    """Detect circular import dependencies."""
    circular = []
    visited = set()
    rec_stack = set()

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        # Get files that import this module
        if node in graph['imports']:
            for imported_by in graph['imports'][node]:
                if imported_by not in visited:
                    dfs(imported_by, path.copy())
                elif imported_by in rec_stack:
                    # Circular dependency found
                    cycle = path[path.index(imported_by):] + [imported_by]
                    circular.append(cycle)

        rec_stack.remove(node)

    for node in graph['imports']:
        if node not in visited:
            dfs(node, [])

    return circular


if __name__ == "__main__":
    print("Analyzing dependencies...")

    # Analyze streamlit directory
    streamlit_dir = Path("streamlit")
    if not streamlit_dir.exists():
        streamlit_dir = Path("./streamlit")

    graph = build_complete_graph(str(streamlit_dir))

    # Calculate statistics
    stats = {
        'total_files': len(graph['files']),
        'total_imports': len(set(imp for imports in graph['imports'].values() for imp in imports)),
        'critical_functions': analyze_critical_functions(graph),
    }

    # Save graph
    output = {
        'stats': stats,
        'files': {k: {
            'imports': v['imports'],
            'internal_imports': v['internal_imports'],
            'functions_defined': v['functions_defined']
        } for k, v in graph['files'].items()}
    }

    with open('dependency_graph.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("Analysis complete!")
    print(f"   - Files analyzed: {stats['total_files']}")
    print(f"   - Unique imports tracked: {stats['total_imports']}")
    print("\nCritical Functions Usage:")
    for func, count in sorted(stats['critical_functions'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   - {func}: {count} files")

    print("\nOutput saved to dependency_graph.json")
