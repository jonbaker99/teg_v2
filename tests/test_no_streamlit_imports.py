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
    # Get project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    imports = find_streamlit_imports(project_root)

    formatted = "\n".join(
        f"  {file_path}:{line_num}\n    {line_content}"
        for file_path, line_num, line_content in imports
    )
    assert not imports, (
        f"Found {len(imports)} direct Streamlit import(s) in teg_analysis "
        f"(move them inside a try/except block):\n{formatted}"
    )

if __name__ == "__main__":
    try:
        test_no_direct_streamlit_imports()
        print("OK: No direct Streamlit imports found")
        sys.exit(0)
    except AssertionError as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
