#!/usr/bin/env python3
"""One-off: run tighten_prose() on TEG 14 and TEG 18 final reports.

Usage:
    venv/bin/python scripts/tighten_reports.py

Writes tightened versions to data/commentary/teg_{N}_report_tightened.md.
Skips if output already exists.
"""
import difflib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from teg_analysis.reporting.authoring import tighten_prose

DATA = pathlib.Path("data/commentary")

PAIRS = [
    ("teg_14_report_final.md", "teg_14_report_tightened.md"),
    ("teg_18_report_final.md", "teg_18_report_tightened.md"),
]

for src_name, dst_name in PAIRS:
    src = DATA / src_name
    dst = DATA / dst_name

    if dst.exists():
        print(f"SKIP {dst_name} — already exists")
        continue

    original = src.read_text()
    orig_lines = original.splitlines()
    print(f"Tightening {src_name} ({len(orig_lines)} lines)...")

    tightened, usage = tighten_prose(original)
    dst.write_text(tightened)

    new_lines = tightened.splitlines()
    delta = len(new_lines) - len(orig_lines)
    print(f"  Done → {dst_name}: {len(orig_lines)} → {len(new_lines)} lines ({delta:+d})")
    print(f"  Usage: {usage}")

    # Show up to 4 changed paragraph pairs (before/after)
    diff = list(difflib.unified_diff(orig_lines, new_lines, lineterm="", n=0))
    removed = [l[1:] for l in diff if l.startswith("-") and not l.startswith("---")]
    added   = [l[1:] for l in diff if l.startswith("+") and not l.startswith("+++")]
    pairs = list(zip(removed, added))[:4]
    if pairs:
        print(f"\n  Sample rewrites ({len(pairs)} shown):")
        for i, (before, after) in enumerate(pairs, 1):
            print(f"\n  [{i}] BEFORE: {before.strip()}")
            print(f"      AFTER:  {after.strip()}")
    print()
