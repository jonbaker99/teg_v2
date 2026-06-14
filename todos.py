#!/usr/bin/env python3
"""Print all outstanding to-do items across the project."""

import re
from pathlib import Path

ROOT = Path(__file__).parent

TODO_FILES = [
    ("Data updates", ROOT / "TODOS.md"),
    ("webapp", ROOT / "webapp" / "TODOS.md"),
    ("streamlit", ROOT / "streamlit" / "TODOS.md"),
    ("teg_analysis", ROOT / "teg_analysis" / "TODOS.md"),
    ("reporting", ROOT / "teg_analysis" / "reporting" / "reporting-to-do.md"),
]

# Reporting STATUS.md uses a different format (phase table), just flag it
EXTRA_NOTES = [
    ("Commentary / reporting", "See teg_analysis/reporting/STATUS.md for active agenda (Phases F–G)"),
]

SECTION_RE = re.compile(r"^##\s+(.+)")
ITEM_RE = re.compile(r"^- \[([ x~])\] (.+)")


def parse_todos(path: Path):
    """Return list of (section, status, text) tuples from a TODOS.md file."""
    items = []
    current_section = "General"
    for line in path.read_text().splitlines():
        m = SECTION_RE.match(line)
        if m:
            current_section = m.group(1).strip()
            continue
        m = ITEM_RE.match(line)
        if m:
            status, text = m.group(1), m.group(2)
            # Strip inline markdown bold markers for cleaner output
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            items.append((current_section, status, text))
    return items


STATUS_LABEL = {" ": "[ ]", "x": "[x]", "~": "[~]"}


def main(show_done: bool = False):
    for label, path in TODO_FILES:
        items = parse_todos(path)
        visible = [i for i in items if show_done or i[1] != "x"]
        if not visible:
            continue
        print(f"\n{'═' * 60}")
        print(f"  {label}")
        print(f"{'═' * 60}")
        current_section = None
        for section, status, text in visible:
            if section != current_section:
                print(f"\n  {section}")
                current_section = section
            marker = STATUS_LABEL.get(status, f"[{status}]")
            # Truncate long lines for readability
            display = text if len(text) <= 80 else text[:77] + "..."
            print(f"    {marker} {display}")

    if EXTRA_NOTES:
        print(f"\n{'═' * 60}")
        print("  Other areas")
        print(f"{'═' * 60}")
        for label, note in EXTRA_NOTES:
            print(f"\n  {label}")
            print(f"    → {note}")

    print()


if __name__ == "__main__":
    import sys
    show_done = "--all" in sys.argv
    main(show_done=show_done)
