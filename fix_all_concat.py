#!/usr/bin/env python3
"""Comprehensively fix all file concatenation issues."""

import re
from pathlib import Path

def fix_file_comprehensive(filepath):
    """Fix all concatenation patterns in a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this line contains a docstring starting pattern right after code
        if '"""' in line and not line.strip().startswith('"""'):
            # Split the line at the docstring
            parts = line.split('"""', 1)
            if len(parts) == 2:
                # Add the code part with newline
                fixed_lines.append(parts[0].rstrip() + '\n')
                # Add blank lines and section marker
                fixed_lines.append('\n')
                fixed_lines.append('\n')
                fixed_lines.append('# === MIGRATED SECTION ===\n')
                fixed_lines.append('\n')
                # Add the docstring on its own line
                fixed_lines.append('"""' + parts[1])
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

        i += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f"Fixed: {filepath.name}")

# Fix all analysis modules
analysis_dir = Path('teg_analysis/analysis')
for py_file in analysis_dir.glob('*.py'):
    if py_file.name != '__init__.py':
        print(f"Processing {py_file.name}...")
        fix_file_comprehensive(py_file)

print("\nAll concatenation issues fixed!")
