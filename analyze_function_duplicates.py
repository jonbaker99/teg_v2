"""
Comprehensive Function Duplication and Similarity Analysis for TEG Codebase

This script:
1. Extracts all function definitions from the codebase using AST
2. Analyzes similarity between functions (exact, near, and fuzzy matches)
3. Identifies duplicate and similar code patterns
4. Generates a detailed report for refactoring purposes
"""

import ast
import os
import json
import difflib
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict
import hashlib


class FunctionExtractor(ast.NodeVisitor):
    """Extract function definitions with their metadata using AST"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.functions = []
        self.source_lines = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition nodes and extract metadata"""
        # Get the source code for this function
        try:
            source = ast.get_source_segment(
                '\n'.join(self.source_lines),
                node
            )
        except:
            source = f"# Source extraction failed for {node.name}"

        # Extract parameter information
        args = []
        for arg in node.args.args:
            arg_name = arg.arg
            # Try to get type annotation if present
            annotation = ast.unparse(arg.annotation) if arg.annotation else None
            args.append({
                'name': arg_name,
                'annotation': annotation
            })

        # Extract return type annotation
        return_annotation = ast.unparse(node.returns) if node.returns else None

        # Count lines
        line_count = (node.end_lineno - node.lineno + 1) if node.end_lineno else 1

        # Extract decorators
        decorators = [ast.unparse(dec) for dec in node.decorator_list]

        function_info = {
            'name': node.name,
            'file': self.file_path,
            'line_start': node.lineno,
            'line_end': node.end_lineno if node.end_lineno else node.lineno,
            'line_count': line_count,
            'args': args,
            'return_annotation': return_annotation,
            'decorators': decorators,
            'source': source,
            'source_hash': hashlib.md5(source.encode()).hexdigest() if source else None
        }

        self.functions.append(function_info)
        self.generic_visit(node)


def extract_functions_from_file(file_path: str) -> List[Dict]:
    """Extract all functions from a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source)
        extractor = FunctionExtractor(file_path)
        extractor.source_lines = source.split('\n')
        extractor.visit(tree)

        return extractor.functions
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []


def find_python_files(base_dir: str) -> List[str]:
    """Find all Python files in the codebase"""
    python_files = []
    streamlit_dir = os.path.join(base_dir, 'streamlit')

    # Get all .py files in streamlit directory and subdirectories
    for root, dirs, files in os.walk(streamlit_dir):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    return python_files


def calculate_similarity(source1: str, source2: str) -> float:
    """Calculate similarity percentage between two code snippets"""
    # Normalize whitespace for comparison
    lines1 = [line.strip() for line in source1.split('\n') if line.strip()]
    lines2 = [line.strip() for line in source2.split('\n') if line.strip()]

    # Use SequenceMatcher for similarity
    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    return matcher.ratio() * 100


def normalize_function_name(name: str) -> str:
    """Normalize function name for fuzzy matching"""
    return name.lower().replace('_', '')


def analyze_duplicates(all_functions: List[Dict]) -> Dict:
    """Analyze functions to find duplicates and similarities"""

    # Group by function name
    by_name = defaultdict(list)
    for func in all_functions:
        by_name[func['name']].append(func)

    # Group by normalized name (for fuzzy matching)
    by_normalized_name = defaultdict(list)
    for func in all_functions:
        normalized = normalize_function_name(func['name'])
        by_normalized_name[normalized].append(func)

    # Group by source hash (exact duplicates)
    by_hash = defaultdict(list)
    for func in all_functions:
        if func['source_hash']:
            by_hash[func['source_hash']].append(func)

    results = {
        'exact_duplicates': [],  # 100% match, different files
        'near_duplicates': [],   # 80-99% match
        'same_name_different_impl': [],  # Same name, different implementation
        'similar_names': [],     # Similar names (fuzzy match)
        'pattern_duplicates': [], # Common patterns
    }

    # Find exact duplicates (same hash, different locations)
    for hash_key, funcs in by_hash.items():
        if len(funcs) > 1:
            # Group by unique file paths
            unique_files = set(f['file'] for f in funcs)
            if len(unique_files) > 1:  # Only if in different files
                results['exact_duplicates'].append({
                    'functions': funcs,
                    'count': len(funcs),
                    'unique_files': len(unique_files)
                })

    # Find same-name functions with different implementations
    for name, funcs in by_name.items():
        if len(funcs) > 1:
            # Check if they have different hashes
            hashes = set(f['source_hash'] for f in funcs if f['source_hash'])
            if len(hashes) > 1:
                # Compare all pairs
                comparisons = []
                for i, func1 in enumerate(funcs):
                    for func2 in funcs[i+1:]:
                        if func1['source'] and func2['source']:
                            similarity = calculate_similarity(
                                func1['source'],
                                func2['source']
                            )
                            comparisons.append({
                                'func1': func1,
                                'func2': func2,
                                'similarity': similarity
                            })

                            # Categorize based on similarity
                            if 80 <= similarity < 100:
                                results['near_duplicates'].append({
                                    'name': name,
                                    'func1': func1,
                                    'func2': func2,
                                    'similarity': similarity
                                })
                            elif similarity < 80:
                                results['same_name_different_impl'].append({
                                    'name': name,
                                    'func1': func1,
                                    'func2': func2,
                                    'similarity': similarity
                                })

    # Find similar names (fuzzy matching)
    processed_pairs = set()
    for normalized, funcs in by_normalized_name.items():
        if len(funcs) > 1:
            # Get actual names
            names = set(f['name'] for f in funcs)
            if len(names) > 1:  # Different actual names
                for i, func1 in enumerate(funcs):
                    for func2 in funcs[i+1:]:
                        if func1['name'] != func2['name']:
                            pair_key = tuple(sorted([func1['name'], func2['name']]))
                            if pair_key not in processed_pairs:
                                processed_pairs.add(pair_key)

                                # Calculate name similarity
                                name_sim = difflib.SequenceMatcher(
                                    None,
                                    func1['name'],
                                    func2['name']
                                ).ratio() * 100

                                # Calculate code similarity
                                code_sim = 0
                                if func1['source'] and func2['source']:
                                    code_sim = calculate_similarity(
                                        func1['source'],
                                        func2['source']
                                    )

                                results['similar_names'].append({
                                    'func1': func1,
                                    'func2': func2,
                                    'name_similarity': name_sim,
                                    'code_similarity': code_sim
                                })

    return results


def generate_report(all_functions: List[Dict], analysis: Dict) -> str:
    """Generate a comprehensive analysis report"""

    report = []
    report.append("=" * 80)
    report.append("TEG CODEBASE - FUNCTION DUPLICATION & SIMILARITY ANALYSIS")
    report.append("=" * 80)
    report.append("")

    # Summary statistics
    report.append("SUMMARY STATISTICS")
    report.append("-" * 80)
    report.append(f"Total functions analyzed: {len(all_functions)}")

    # Count unique files
    unique_files = set(f['file'] for f in all_functions)
    report.append(f"Files analyzed: {len(unique_files)}")

    # Count by file type
    utils_funcs = [f for f in all_functions if 'utils.py' in f['file']]
    helper_funcs = [f for f in all_functions if 'helpers' in f['file']]
    page_funcs = [f for f in all_functions if f not in utils_funcs + helper_funcs]

    report.append(f"Functions in utils.py: {len(utils_funcs)}")
    report.append(f"Functions in helpers/: {len(helper_funcs)}")
    report.append(f"Functions in page files: {len(page_funcs)}")
    report.append("")

    # Exact duplicates
    report.append("1. EXACT DUPLICATES (100% identical code, different locations)")
    report.append("-" * 80)
    if analysis['exact_duplicates']:
        for idx, dup in enumerate(analysis['exact_duplicates'], 1):
            funcs = dup['functions']
            report.append(f"\nDuplicate Set #{idx}: {funcs[0]['name']}")
            report.append(f"  Occurrences: {dup['count']} times in {dup['unique_files']} files")
            report.append(f"  Line count: {funcs[0]['line_count']} lines")
            report.append(f"  Locations:")
            for func in funcs:
                rel_path = func['file'].replace(os.getcwd(), '').lstrip(os.sep)
                report.append(f"    - {rel_path}:{func['line_start']}")
            report.append(f"  Decorators: {', '.join(funcs[0]['decorators']) if funcs[0]['decorators'] else 'None'}")
    else:
        report.append("  No exact duplicates found.")
    report.append("")

    # Near duplicates
    report.append("2. NEAR DUPLICATES (80-99% similar)")
    report.append("-" * 80)
    if analysis['near_duplicates']:
        # Sort by similarity descending
        sorted_near = sorted(
            analysis['near_duplicates'],
            key=lambda x: x['similarity'],
            reverse=True
        )
        for idx, dup in enumerate(sorted_near, 1):
            report.append(f"\nNear Duplicate #{idx}: {dup['name']}")
            report.append(f"  Similarity: {dup['similarity']:.1f}%")

            rel_path1 = dup['func1']['file'].replace(os.getcwd(), '').lstrip(os.sep)
            rel_path2 = dup['func2']['file'].replace(os.getcwd(), '').lstrip(os.sep)

            report.append(f"  Location 1: {rel_path1}:{dup['func1']['line_start']}")
            report.append(f"  Location 2: {rel_path2}:{dup['func2']['line_start']}")
            report.append(f"  Lines: {dup['func1']['line_count']} vs {dup['func2']['line_count']}")
    else:
        report.append("  No near duplicates found.")
    report.append("")

    # Same name, different implementation
    report.append("3. SAME NAME, DIFFERENT IMPLEMENTATION")
    report.append("-" * 80)
    if analysis['same_name_different_impl']:
        # Group by function name
        by_name = defaultdict(list)
        for item in analysis['same_name_different_impl']:
            by_name[item['name']].append(item)

        for name, items in sorted(by_name.items()):
            report.append(f"\nFunction: {name}")
            report.append(f"  Implementations: {len(items) + 1}")

            # Get all unique functions with this name
            all_funcs = []
            seen = set()
            for item in items:
                for key in ['func1', 'func2']:
                    func = item[key]
                    file_line = f"{func['file']}:{func['line_start']}"
                    if file_line not in seen:
                        seen.add(file_line)
                        all_funcs.append(func)

            report.append(f"  Locations:")
            for func in all_funcs:
                rel_path = func['file'].replace(os.getcwd(), '').lstrip(os.sep)
                report.append(f"    - {rel_path}:{func['line_start']} ({func['line_count']} lines)")

            # Show similarity between versions
            if items:
                report.append(f"  Similarity range: {min(i['similarity'] for i in items):.1f}% - {max(i['similarity'] for i in items):.1f}%")
    else:
        report.append("  No functions with same name but different implementations.")
    report.append("")

    # Similar names
    report.append("4. SIMILAR FUNCTION NAMES (Potential naming inconsistencies)")
    report.append("-" * 80)
    if analysis['similar_names']:
        # Filter to only show high similarity and reasonable code similarity
        filtered = [
            s for s in analysis['similar_names']
            if s['name_similarity'] > 70 and s['code_similarity'] > 20
        ]

        if filtered:
            # Sort by code similarity
            sorted_similar = sorted(
                filtered,
                key=lambda x: x['code_similarity'],
                reverse=True
            )

            for idx, sim in enumerate(sorted_similar[:20], 1):  # Limit to top 20
                report.append(f"\nSimilar #{idx}:")
                report.append(f"  Names: '{sim['func1']['name']}' vs '{sim['func2']['name']}'")
                report.append(f"  Name similarity: {sim['name_similarity']:.1f}%")
                report.append(f"  Code similarity: {sim['code_similarity']:.1f}%")

                rel_path1 = sim['func1']['file'].replace(os.getcwd(), '').lstrip(os.sep)
                rel_path2 = sim['func2']['file'].replace(os.getcwd(), '').lstrip(os.sep)

                report.append(f"  Location 1: {rel_path1}:{sim['func1']['line_start']}")
                report.append(f"  Location 2: {rel_path2}:{sim['func2']['line_start']}")
        else:
            report.append("  No significant similar names found.")
    else:
        report.append("  No similar names found.")
    report.append("")

    # Most common function names
    report.append("5. MOST COMMON FUNCTION NAMES (Potential for consolidation)")
    report.append("-" * 80)
    name_counts = defaultdict(int)
    for func in all_functions:
        name_counts[func['name']] += 1

    common = sorted(name_counts.items(), key=lambda x: x[1], reverse=True)
    for name, count in common[:20]:
        if count > 1:
            report.append(f"  {name}: {count} occurrences")
    report.append("")

    return '\n'.join(report)


def save_detailed_json(all_functions: List[Dict], analysis: Dict, output_file: str):
    """Save detailed analysis to JSON for further processing"""

    # Convert to serializable format
    output = {
        'total_functions': len(all_functions),
        'functions': all_functions,
        'analysis': {
            'exact_duplicates_count': len(analysis['exact_duplicates']),
            'exact_duplicates': analysis['exact_duplicates'],
            'near_duplicates_count': len(analysis['near_duplicates']),
            'near_duplicates': analysis['near_duplicates'],
            'same_name_different_impl_count': len(analysis['same_name_different_impl']),
            'same_name_different_impl': analysis['same_name_different_impl'],
            'similar_names_count': len(analysis['similar_names']),
            'similar_names': analysis['similar_names'][:50]  # Limit to top 50
        }
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)


def main():
    """Main analysis workflow"""
    print("Starting TEG Function Duplication Analysis...")
    print("=" * 80)

    # Get base directory
    base_dir = os.getcwd()
    print(f"Base directory: {base_dir}")

    # Find all Python files
    print("\n1. Finding Python files...")
    python_files = find_python_files(base_dir)
    print(f"   Found {len(python_files)} Python files")

    # Extract functions
    print("\n2. Extracting functions from files...")
    all_functions = []
    for file_path in python_files:
        rel_path = file_path.replace(base_dir, '').lstrip(os.sep)
        print(f"   Processing: {rel_path}")
        functions = extract_functions_from_file(file_path)
        all_functions.extend(functions)

    print(f"\n   Total functions extracted: {len(all_functions)}")

    # Analyze duplicates
    print("\n3. Analyzing duplicates and similarities...")
    analysis = analyze_duplicates(all_functions)

    print(f"   Exact duplicates: {len(analysis['exact_duplicates'])}")
    print(f"   Near duplicates: {len(analysis['near_duplicates'])}")
    print(f"   Same name, different impl: {len(analysis['same_name_different_impl'])}")
    print(f"   Similar names: {len(analysis['similar_names'])}")

    # Generate report
    print("\n4. Generating report...")
    report = generate_report(all_functions, analysis)

    # Save report
    report_file = os.path.join(base_dir, 'docs', 'FUNCTION_DUPLICATION_ANALYSIS.md')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"   Report saved to: {report_file}")

    # Save detailed JSON
    json_file = os.path.join(base_dir, 'function_analysis.json')
    save_detailed_json(all_functions, analysis, json_file)
    print(f"   Detailed JSON saved to: {json_file}")

    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)

    # Print summary
    print("\n" + report.split("SUMMARY STATISTICS")[1].split("\n\n")[0])


if __name__ == "__main__":
    main()
