#!/usr/bin/env python3
"""Scan for known pandas 2.x compatibility issues.

Run from the repo root:
    python scripts/check_pandas_compat.py

Exits 0 if clean, 1 if issues found.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ["streamlit", "teg_analysis", "webapp"]

# ---------------------------------------------------------------------------
# Known-bad patterns
# ---------------------------------------------------------------------------
CHECKS = [
    {
        "id": "applymap",
        "level": "error",
        "description": "DataFrame.applymap() was removed in pandas 2.1+ — replace with .map()",
        "pattern": re.compile(r"\.applymap\("),
    },
    {
        "id": "rank-int-unprotected",
        "level": "warning",
        "description": (
            ".rank().astype(int) not immediately chained to .astype(object) or .astype(str). "
            "If string values (e.g. tied-rank '1=') are later assigned to the same column, "
            "pandas 2.x will raise TypeError. Safe if the column never receives strings."
        ),
        "pattern": re.compile(r"\.rank\([^)]*\)\.astype\(int\)(?!\.astype\((object|str)\))"),
    },
    {
        "id": "loc-string-assign",
        "level": "warning",
        "description": (
            ".loc[] assignment where the right-hand side produces strings "
            "(.astype(str) or string concatenation). Raises TypeError in pandas 2.x "
            "if the target column is int64 or float64."
        ),
        "pattern": re.compile(r"\.loc\[.+\]\s*=\s*.+(\+\s*['\"]|\.astype\(str\))"),
    },
    {
        "id": "iloc-col-assign",
        "level": "warning",
        "description": (
            ".iloc[..., col] = ... positional column assignment. Pandas 2.x enforces "
            "the existing column dtype on iloc setitem — assigning strings into a "
            "float64/int64 column raises TypeError. Use named-column assignment "
            "(df[col_name] = ...) instead."
        ),
        "pattern": re.compile(r"\.iloc\[[^\]]*,[^\]]*\]\s*="),
    },
]

LEVEL_ICON = {"error": "✖", "warning": "⚠"}


def scan_file(path: Path) -> list[dict]:
    issues = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return issues
    for lineno, line in enumerate(lines, start=1):
        if line.strip().startswith("#"):
            continue
        for check in CHECKS:
            if check["pattern"].search(line):
                issues.append(
                    {
                        "file": path.relative_to(ROOT),
                        "line": lineno,
                        "text": line.rstrip(),
                        "check": check,
                    }
                )
    return issues


def main() -> int:
    all_issues: list[dict] = []
    for dir_name in SCAN_DIRS:
        scan_root = ROOT / dir_name
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*.py")):
            all_issues.extend(scan_file(path))

    if not all_issues:
        print("✅  No pandas 2.x compatibility issues found.")
        return 0

    errors = [i for i in all_issues if i["check"]["level"] == "error"]
    warnings = [i for i in all_issues if i["check"]["level"] == "warning"]

    print(
        f"Found {len(errors)} error(s) and {len(warnings)} warning(s) "
        f"across {len(all_issues)} location(s).\n"
    )

    # Group by check id for readable output
    by_check: dict[str, list[dict]] = {}
    for issue in all_issues:
        by_check.setdefault(issue["check"]["id"], []).append(issue)

    for check_id, issues in by_check.items():
        check = issues[0]["check"]
        icon = LEVEL_ICON[check["level"]]
        print(f"{icon}  [{check_id}]  {check['description']}")
        for i in issues:
            print(f"   {i['file']}:{i['line']}")
            print(f"     {i['text'].strip()}")
        print()

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
