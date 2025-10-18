"""
Additional Pattern Analysis for TEG Codebase

This script performs deeper analysis on the extracted functions to identify:
1. Code patterns that repeat across files
2. Utility function candidates (functions that should be centralized)
3. Impact analysis (which duplicates affect the most files)
"""

import json
import os
from collections import defaultdict, Counter
import re


def load_analysis_data():
    """Load the JSON analysis data"""
    with open('function_analysis.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def find_import_patterns(all_functions):
    """Analyze import patterns to understand dependencies"""
    import_patterns = defaultdict(list)

    for func in all_functions:
        source = func.get('source', '')
        # Extract import statements
        import_lines = [
            line.strip()
            for line in source.split('\n')
            if line.strip().startswith(('import ', 'from '))
        ]

        if import_lines:
            import_patterns[func['name']].append({
                'file': func['file'],
                'imports': import_lines
            })

    return import_patterns


def analyze_decorator_usage(all_functions):
    """Analyze decorator patterns"""
    decorator_usage = defaultdict(list)

    for func in all_functions:
        if func['decorators']:
            for dec in func['decorators']:
                decorator_usage[dec].append({
                    'name': func['name'],
                    'file': func['file'],
                    'line': func['line_start']
                })

    return decorator_usage


def find_utility_function_candidates(all_functions):
    """Identify functions that could be utility functions"""
    candidates = []

    # Criteria for utility functions:
    # 1. Short functions (< 30 lines)
    # 2. No streamlit imports
    # 3. Pure computation/formatting
    # 4. Used in multiple places (same name)

    name_counts = Counter(f['name'] for f in all_functions)

    for func in all_functions:
        # Check if used multiple times
        if name_counts[func['name']] > 1:
            source = func.get('source', '').lower()

            # Check criteria
            if (func['line_count'] <= 30 and
                'streamlit' not in source and
                'st.' not in source):
                candidates.append(func)

    return candidates


def analyze_within_file_duplicates(all_functions):
    """Find duplicate functions within the same file"""
    by_file = defaultdict(list)

    for func in all_functions:
        by_file[func['file']].append(func)

    within_file_dups = []

    for file_path, funcs in by_file.items():
        name_counts = Counter(f['name'] for f in funcs)

        for name, count in name_counts.items():
            if count > 1:
                matching_funcs = [f for f in funcs if f['name'] == name]
                within_file_dups.append({
                    'file': file_path,
                    'function_name': name,
                    'count': count,
                    'functions': matching_funcs
                })

    return within_file_dups


def identify_code_patterns(all_functions):
    """Identify common code patterns that appear across files"""
    patterns = {
        'vs_par_formatting': [],
        'player_filtering': [],
        'teg_filtering': [],
        'dataframe_styling': [],
        'cache_clearing': [],
        'github_operations': [],
        'chart_creation': [],
    }

    pattern_keywords = {
        'vs_par_formatting': [r'vs[\s_]par', r'\+\s*str\(', r'format.*par'],
        'player_filtering': [r'player.*==', r'player.*filter', r'player.*select'],
        'teg_filtering': [r'teg.*==', r'teg.*filter', r'tegnum'],
        'dataframe_styling': [r'\.style\.', r'background.*gradient', r'\.applymap'],
        'cache_clearing': [r'cache.*clear', r'st\.cache'],
        'github_operations': [r'github', r'commit', r'push'],
        'chart_creation': [r'alt\.Chart', r'plotly', r'\.mark_'],
    }

    for func in all_functions:
        source = func.get('source', '').lower()

        for pattern_name, keywords in pattern_keywords.items():
            for keyword in keywords:
                if re.search(keyword, source, re.IGNORECASE):
                    patterns[pattern_name].append({
                        'name': func['name'],
                        'file': func['file'],
                        'line_count': func['line_count']
                    })
                    break  # Only count once per pattern

    return patterns


def generate_enhanced_report(data):
    """Generate enhanced analysis report"""
    all_functions = data['functions']
    analysis = data['analysis']

    report = []
    report.append("=" * 80)
    report.append("ENHANCED DUPLICATION ANALYSIS - ADDITIONAL INSIGHTS")
    report.append("=" * 80)
    report.append("")

    # Within-file duplicates
    report.append("1. WITHIN-FILE DUPLICATES (Same function name, same file)")
    report.append("-" * 80)
    within_file = analyze_within_file_duplicates(all_functions)

    if within_file:
        for dup in within_file:
            rel_path = dup['file'].replace(os.getcwd(), '').lstrip(os.sep)
            report.append(f"\n  File: {rel_path}")
            report.append(f"  Function: {dup['function_name']}")
            report.append(f"  Occurrences: {dup['count']} times in the same file")
            report.append(f"  Line numbers:")
            for func in dup['functions']:
                report.append(f"    - Line {func['line_start']} ({func['line_count']} lines)")
    else:
        report.append("  No within-file duplicates found.")
    report.append("")

    # Decorator analysis
    report.append("2. DECORATOR USAGE ANALYSIS")
    report.append("-" * 80)
    decorator_usage = analyze_decorator_usage(all_functions)

    report.append(f"\n  Total unique decorators: {len(decorator_usage)}")
    report.append("\n  Most common decorators:")

    sorted_decs = sorted(
        decorator_usage.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:10]

    for dec, usages in sorted_decs:
        report.append(f"    {dec}: {len(usages)} functions")

    # Show st.cache_data usage in detail
    if 'st.cache_data' in decorator_usage:
        report.append(f"\n  Functions with @st.cache_data: {len(decorator_usage['st.cache_data'])}")

    report.append("")

    # Utility function candidates
    report.append("3. UTILITY FUNCTION CONSOLIDATION CANDIDATES")
    report.append("-" * 80)
    report.append("Functions that appear multiple times and could be centralized in utils.py")
    report.append("")

    candidates = find_utility_function_candidates(all_functions)

    # Group by name
    by_name = defaultdict(list)
    for cand in candidates:
        by_name[cand['name']].append(cand)

    # Filter to only show those not in utils.py
    non_utils = {
        name: funcs
        for name, funcs in by_name.items()
        if not any('utils.py' in f['file'] for f in funcs)
    }

    if non_utils:
        for name, funcs in sorted(non_utils.items()):
            report.append(f"\n  Function: {name}")
            report.append(f"  Occurrences: {len(funcs)}")
            report.append(f"  Average size: {sum(f['line_count'] for f in funcs) / len(funcs):.1f} lines")
            report.append(f"  Locations:")
            for func in funcs:
                rel_path = func['file'].replace(os.getcwd(), '').lstrip(os.sep)
                report.append(f"    - {rel_path}:{func['line_start']}")
    else:
        report.append("  All multi-use utility functions are already in utils.py")
    report.append("")

    # Code pattern analysis
    report.append("4. COMMON CODE PATTERNS")
    report.append("-" * 80)
    patterns = identify_code_patterns(all_functions)

    for pattern_name, occurrences in patterns.items():
        if occurrences:
            unique_files = set(o['file'] for o in occurrences)
            report.append(f"\n  Pattern: {pattern_name}")
            report.append(f"  Occurrences: {len(occurrences)} functions")
            report.append(f"  Files affected: {len(unique_files)}")

            # Show top functions
            sorted_occs = sorted(occurrences, key=lambda x: x['line_count'], reverse=True)[:3]
            if sorted_occs:
                report.append(f"  Example functions:")
                for occ in sorted_occs:
                    rel_path = occ['file'].replace(os.getcwd(), '').lstrip(os.sep)
                    report.append(f"    - {occ['name']} ({rel_path}, {occ['line_count']} lines)")

    report.append("")

    # High-impact duplicates
    report.append("5. HIGH-IMPACT DUPLICATES (Prioritize for refactoring)")
    report.append("-" * 80)
    report.append("Duplicates sorted by potential impact (number of occurrences × line count)")
    report.append("")

    # Calculate impact scores
    impact_items = []

    # Exact duplicates
    for dup_set in analysis['exact_duplicates']:
        funcs = dup_set['functions']
        impact = dup_set['count'] * funcs[0]['line_count']
        impact_items.append({
            'type': 'EXACT',
            'name': funcs[0]['name'],
            'count': dup_set['count'],
            'lines': funcs[0]['line_count'],
            'impact': impact,
            'files': [f['file'] for f in funcs]
        })

    # Near duplicates
    for dup in analysis['near_duplicates']:
        impact = 2 * dup['func1']['line_count']  # 2 occurrences
        impact_items.append({
            'type': 'NEAR',
            'name': dup['name'],
            'count': 2,
            'lines': dup['func1']['line_count'],
            'similarity': dup['similarity'],
            'impact': impact,
            'files': [dup['func1']['file'], dup['func2']['file']]
        })

    # Sort by impact
    sorted_impact = sorted(impact_items, key=lambda x: x['impact'], reverse=True)

    for idx, item in enumerate(sorted_impact[:15], 1):
        report.append(f"\n  #{idx}: {item['name']}")
        report.append(f"  Type: {item['type']} duplicate")
        report.append(f"  Occurrences: {item['count']}")
        report.append(f"  Line count: {item['lines']}")
        if 'similarity' in item:
            report.append(f"  Similarity: {item['similarity']:.1f}%")
        report.append(f"  Impact score: {item['impact']} (count × lines)")
        report.append(f"  Affected files:")
        for file_path in item['files']:
            rel_path = file_path.replace(os.getcwd(), '').lstrip(os.sep)
            report.append(f"    - {rel_path}")

    report.append("")

    # File complexity analysis
    report.append("6. FILE COMPLEXITY ANALYSIS")
    report.append("-" * 80)
    report.append("Files with the most functions (candidates for splitting)")
    report.append("")

    by_file = defaultdict(list)
    for func in all_functions:
        by_file[func['file']].append(func)

    file_stats = []
    for file_path, funcs in by_file.items():
        total_lines = sum(f['line_count'] for f in funcs)
        file_stats.append({
            'file': file_path,
            'function_count': len(funcs),
            'total_lines': total_lines,
            'avg_lines': total_lines / len(funcs) if funcs else 0
        })

    sorted_files = sorted(file_stats, key=lambda x: x['function_count'], reverse=True)

    for idx, stat in enumerate(sorted_files[:15], 1):
        rel_path = stat['file'].replace(os.getcwd(), '').lstrip(os.sep)
        report.append(f"\n  #{idx}: {rel_path}")
        report.append(f"  Functions: {stat['function_count']}")
        report.append(f"  Total function lines: {stat['total_lines']}")
        report.append(f"  Average function size: {stat['avg_lines']:.1f} lines")

    report.append("")

    return '\n'.join(report)


def main():
    """Main analysis workflow"""
    print("Loading analysis data...")
    data = load_analysis_data()

    print("Generating enhanced report...")
    report = generate_enhanced_report(data)

    # Save report
    output_file = os.path.join('docs', 'FUNCTION_DUPLICATION_ENHANCED.md')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Enhanced report saved to: {output_file}")
    print("\nReport preview:")
    print("=" * 80)
    # Print first part of report
    lines = report.split('\n')
    for line in lines[:50]:
        print(line)


if __name__ == "__main__":
    main()
