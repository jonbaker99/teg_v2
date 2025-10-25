#!/usr/bin/env python3
"""Fix file concatenation issues in migrated modules."""

import re
from pathlib import Path

def fix_file(filepath):
    """Fix concatenation issues in a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern: return statement directly followed by triple-quoted docstring
    # This happens when files were concatenated without proper spacing
    pattern = r'(\n    return [^\n]+)("""[^"]+""")'
    replacement = r'\1\n\n\n# === SECTION DIVIDER ===\n\n\2'

    content = re.sub(pattern, replacement, content)

    # Also fix cases where imports follow docstrings too closely
    pattern2 = r'("""[^"]+""")\n\nimport '
    replacement2 = r'\1\n\n\nimport '

    content = re.sub(pattern2, replacement2, content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Fixed {filepath}")

# Fix all analysis modules
analysis_dir = Path('teg_analysis/analysis')
for py_file in analysis_dir.glob('*.py'):
    if py_file.name != '__init__.py':
        fix_file(py_file)

print("\nAll files fixed!")
