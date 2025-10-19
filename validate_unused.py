#!/usr/bin/env python3
"""
GREP VALIDATION of unused function candidates.

For each unused function, search entire codebase to verify it's truly unused.
NO SHORTCUTS - check EVERY candidate.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import List, Dict


def grep_search(pattern: str, root_dir: str) -> List[str]:
    """
    Search for pattern in all Python files using grep.

    Returns list of matches (file:line:content).
    """
    try:
        # Use findstr on Windows (like grep)
        result = subprocess.run(
            ['findstr', '/S', '/N', '/I', pattern, '*.py'],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        lines = result.stdout.strip().split('\n') if result.stdout else []
        return [line for line in lines if line.strip()]
    except Exception as e:
        print(f"  ERROR searching for {pattern}: {e}")
        return []


def validate_unused_function(func_info: Dict, root_dir: str) -> Dict:
    """
    Validate if a function is truly unused by searching for it.

    Returns validation result with confidence level.
    """
    func_name = func_info['name']
    func_file = func_info['file']
    func_line = func_info['line']

    print(f"\n  Validating: {func_name} in {func_file}:{func_line}")

    # Search for function name in codebase
    matches = grep_search(func_name, root_dir)

    # Filter matches
    definition_matches = []
    call_matches = []
    comment_matches = []

    for match in matches:
        match_lower = match.lower()

        # Skip if it's the function definition itself
        if f"{func_file}:{func_line}:" in match or f"{func_file.replace(os.sep, '/')}:{func_line}:" in match:
            definition_matches.append(match)
            continue

        # Check if it's a comment
        if '#' in match and match.split('#')[1].strip().startswith(func_name):
            comment_matches.append(match)
            continue

        # Check if it's a function call pattern
        if f"{func_name}(" in match or f".{func_name}(" in match:
            call_matches.append(match)
        elif f" {func_name} " in match or f"'{func_name}'" in match or f'"{func_name}"' in match:
            # Could be string reference or other usage
            call_matches.append(match)

    # Determine confidence
    if len(call_matches) == 0:
        confidence = 'HIGH'  # No calls found - safe to archive
        reason = f"No calls found in codebase (checked {len(matches)} total matches)"
    elif len(call_matches) <= 2:
        confidence = 'MEDIUM'  # Very few calls - needs review
        reason = f"Found {len(call_matches)} potential calls - needs manual review"
    else:
        confidence = 'LOW'  # Many calls - likely false positive
        reason = f"Found {len(call_matches)} potential calls - likely used"

    result = {
        'function': func_name,
        'file': func_file,
        'line': func_line,
        'confidence': confidence,
        'reason': reason,
        'total_matches': len(matches),
        'definition_matches': len(definition_matches),
        'call_matches': len(call_matches),
        'comment_matches': len(comment_matches),
        'sample_calls': call_matches[:5]  # First 5 for review
    }

    print(f"    Confidence: {confidence} - {reason}")
    if call_matches:
        print(f"    Sample calls:")
        for call in call_matches[:3]:
            print(f"      {call[:120]}")

    return result


def main():
    """Validate all unused function candidates."""

    print("="*80)
    print("GREP VALIDATION OF UNUSED FUNCTION CANDIDATES")
    print("NO SHORTCUTS - CHECKING EVERY CANDIDATE")
    print("="*80)
    print()

    root_dir = Path(__file__).parent

    # Load refined analysis results
    analysis_file = root_dir / 'unused_code_analysis_refined.json'
    with open(analysis_file, 'r') as f:
        data = json.load(f)

    unused_functions = data['unused_functions']
    print(f"Loaded {len(unused_functions)} unused function candidates")
    print()

    # Validate each one
    print("Starting grep validation...")
    validation_results = []

    for i, func_info in enumerate(unused_functions, 1):
        print(f"\n[{i}/{len(unused_functions)}]", end='')
        result = validate_unused_function(func_info, str(root_dir))
        validation_results.append(result)

    print("\n\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)
    print()

    # Summarize results by confidence
    by_confidence = {'HIGH': [], 'MEDIUM': [], 'LOW': []}
    for result in validation_results:
        by_confidence[result['confidence']].append(result)

    print(f"HIGH confidence (safe to archive): {len(by_confidence['HIGH'])}")
    print(f"MEDIUM confidence (needs review): {len(by_confidence['MEDIUM'])}")
    print(f"LOW confidence (likely used): {len(by_confidence['LOW'])}")
    print()

    # Save validation results
    output = {
        'summary': {
            'total_candidates': len(unused_functions),
            'high_confidence': len(by_confidence['HIGH']),
            'medium_confidence': len(by_confidence['MEDIUM']),
            'low_confidence': len(by_confidence['LOW'])
        },
        'by_confidence': {
            'HIGH': by_confidence['HIGH'],
            'MEDIUM': by_confidence['MEDIUM'],
            'LOW': by_confidence['LOW']
        },
        'all_results': validation_results
    }

    output_file = root_dir / 'unused_code_validation.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"Results saved to: {output_file}")
    print()
    print("Next step: Review validation results and create unused code report")
    print()


if __name__ == '__main__':
    main()
