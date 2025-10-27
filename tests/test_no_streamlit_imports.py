"""Test that teg_analysis has no direct Streamlit imports.

This test verifies that teg_analysis modules don't directly import
Streamlit, ensuring UI independence. Conditional imports in try/except
blocks are allowed.

Run with: python tests/test_no_streamlit_imports.py
"""
import sys
import os
import re
from pathlib import Path

def find_streamlit_imports(directory):
    """Find all direct Streamlit imports in Python files.

    Excludes:
    - Imports within try/except blocks (conditional imports are OK)
    - Comments

    Args:
        directory: Directory to search

    Returns:
        List of (file_path, line_number, line_content) tuples
    """
    imports_found = []
    teg_analysis_dir = Path(directory) / 'teg_analysis'

    if not teg_analysis_dir.exists():
        raise FileNotFoundError(f"Directory not found: {teg_analysis_dir}")

    # Pattern for Streamlit imports
    import_pattern = re.compile(r'^\s*(import streamlit|from streamlit)')

    for py_file in teg_analysis_dir.rglob('*.py'):
        with open(py_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        in_try_block = False
        indent_level = 0

        for line_num, line in enumerate(lines, 1):
            # Track try/except blocks
            if re.match(r'^\s*try\s*:', line):
                in_try_block = True
                indent_level = len(line) - len(line.lstrip())
            elif in_try_block and re.match(r'^\s*except', line):
                # Still in try/except handling
                pass
            elif in_try_block:
                # Check if we've exited the try/except block
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and line.strip():
                    in_try_block = False

            # Check for Streamlit imports
            if import_pattern.match(line):
                # Skip if in try/except block (conditional imports are OK)
                if not in_try_block:
                    rel_path = py_file.relative_to(Path(directory))
                    imports_found.append((str(rel_path), line_num, line.strip()))

    return imports_found

def test_no_direct_streamlit_imports():
    """Test that teg_analysis has no direct Streamlit imports."""
    print("=" * 60)
    print("TEST: No Direct Streamlit Imports in teg_analysis")
    print("=" * 60)

    # Get project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    print(f"\nScanning directory: {project_root}/teg_analysis")
    print("Looking for direct 'import streamlit' or 'from streamlit'...")
    print("(Conditional imports in try/except blocks are allowed)\n")

    # Find all Streamlit imports
    imports = find_streamlit_imports(project_root)

    if imports:
        print(f"FAIL: Found {len(imports)} direct Streamlit import(s):\n")
        for file_path, line_num, line_content in imports:
            print(f"  {file_path}:{line_num}")
            print(f"    {line_content}\n")
        print("=" * 60)
        print("TEST FAILED")
        print("=" * 60)
        print("\nAction Required:")
        print("Move Streamlit imports inside try/except blocks like this:")
        print("""
    try:
        import streamlit as st
        HAS_STREAMLIT = True
    except ImportError:
        st = None
        HAS_STREAMLIT = False
""")
        return False
    else:
        print("OK: No direct Streamlit imports found")
        print("\n" + "=" * 60)
        print("TEST PASSED")
        print("=" * 60)
        print("\nConclusion: teg_analysis is free of direct Streamlit dependencies")
        print("(Conditional imports in try/except blocks are allowed and working)")
        return True

if __name__ == "__main__":
    try:
        success = test_no_direct_streamlit_imports()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
