#!/usr/bin/env python3
"""
Comprehensive grep validation of all unused candidates.

Uses ripgrep-style search to find ALL occurrences of each function name.
"""

import json
import subprocess
from pathlib import Path


def search_codebase(pattern: str, root_dir: Path) -> list:
    """
    Search for pattern using rg (ripgrep) if available, otherwise use Python fallback.
    """
    results = []

    # Try using rg (ripgrep)
    try:
        result = subprocess.run(
            ['rg', '--no-heading', '-n', '-i', pattern, str(root_dir / 'streamlit')],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.stdout:
            results = result.stdout.strip().split('\n')
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # Fallback: Simple Python search
        for py_file in (root_dir / 'streamlit').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if pattern.lower() in line.lower():
                            rel_path = py_file.relative_to(root_dir)
                            results.append(f"{rel_path}:{line_num}:{line.rstrip()}")
            except:
                pass

    return results


def main():
    root_dir = Path(__file__).parent

    # Load candidates
    with open(root_dir / 'unused_code_analysis_simple.json', 'r') as f:
        data = json.load(f)

    candidates = data['unused_functions']
    print(f"Validating {len(candidates)} candidates...\n")

    validation_results = []

    for i, candidate in enumerate(candidates, 1):
        func_name = candidate['name']
        func_file = candidate['file']
        func_line = candidate['line']

        print(f"[{i}/{len(candidates)}] Checking: {func_name}")

        # Search for function name
        matches = search_codebase(func_name, root_dir)

        # Filter out the definition itself
        filtered_matches = []
        for match in matches:
            # Skip the definition line
            if f"{func_file}:{func_line}:" in match:
                continue
            # Skip comment-only matches
            if '#' in match:
                parts = match.split('#')
                if len(parts) > 1 and func_name in parts[1]:
                    continue  # It's in a comment
            filtered_matches.append(match)

        # Assign confidence
        if len(filtered_matches) == 0:
            confidence = 'HIGH'
            reason = 'No usage found in codebase'
        elif len(filtered_matches) <= 2:
            confidence = 'MEDIUM'
            reason = f'{len(filtered_matches)} potential usage(s) found - needs review'
        else:
            confidence = 'LOW'
            reason = f'{len(filtered_matches)} usages found - likely actually used'

        result = {
            'name': func_name,
            'file': func_file,
            'line': func_line,
            'confidence': confidence,
            'reason': reason,
            'usage_count': len(filtered_matches),
            'sample_usages': filtered_matches[:3]
        }

        validation_results.append(result)
        print(f"  {confidence}: {reason}")
        if filtered_matches:
            for usage in filtered_matches[:2]:
                print(f"    {usage[:100]}")
        print()

    # Save results
    output = {
        'summary': {
            'total_candidates': len(candidates),
            'high_confidence': len([r for r in validation_results if r['confidence'] == 'HIGH']),
            'medium_confidence': len([r for r in validation_results if r['confidence'] == 'MEDIUM']),
            'low_confidence': len([r for r in validation_results if r['confidence'] == 'LOW'])
        },
        'results': validation_results
    }

    output_file = root_dir / 'validation_results.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print("="*80)
    print("VALIDATION COMPLETE")
    print("="*80)
    print(f"Total candidates: {len(candidates)}")
    print(f"HIGH confidence (safe to archive): {output['summary']['high_confidence']}")
    print(f"MEDIUM confidence (needs review): {output['summary']['medium_confidence']}")
    print(f"LOW confidence (likely used): {output['summary']['low_confidence']}")
    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()
