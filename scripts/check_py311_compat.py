#!/usr/bin/env python3
"""Verify every deployed .py file parses under Python 3.11 (Railway's runtime).

Local dev commonly runs a newer interpreter (3.12+), which accepts syntax
Railway's 3.11 does not — e.g. PEP 701's relaxed f-string grammar (nested
same-quote strings inside an f-string). Such a file imports fine locally and
passes local tests, then is a hard SyntaxError in production. If the broken
module sits anywhere in webapp.app's import graph, the whole app fails to
start ("Application failed to respond" on Railway, no traceback in the UI —
only in the deploy log). This happened for real 2026-09-12
(teg_analysis/reporting/newspaper_edition.py) — see CLAUDE.md's Python
version invariant.

Run from the repo root:
    python scripts/check_py311_compat.py

Needs a <3.12 interpreter on PATH (checks `python3.11` first, then a few
fallbacks). Install one with: brew install python@3.11
Exits 0 if every file parses clean, 1 if any file fails or no
suitable interpreter is found.
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The packages Railway actually imports to serve the webapp. streamlit/ is
# frozen and never deployed (CLAUDE.md); scripts/ and tests/ aren't imported
# by webapp.app either, though a Python-version mismatch there is lower
# stakes (a CLI script failing is loud and local, not a silent prod outage).
SCAN_DIRS = ["teg_analysis", "webapp"]

CANDIDATE_INTERPRETERS = [
    "python3.11", "python3.10", "python3.9",
    "/opt/homebrew/bin/python3.11", "/usr/local/bin/python3.11",
]


def _find_interpreter() -> str | None:
    for candidate in CANDIDATE_INTERPRETERS:
        path = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
        if path:
            return path
    return None


def main() -> int:
    interpreter = _find_interpreter()
    if interpreter is None:
        print(
            "No Python <3.12 interpreter found (tried: "
            f"{', '.join(CANDIDATE_INTERPRETERS)}).\n"
            "Install one to run this check: brew install python@3.11",
            file=sys.stderr,
        )
        return 1

    files = []
    for d in SCAN_DIRS:
        files.extend(sorted((ROOT / d).rglob("*.py")))

    failures = []
    for f in files:
        result = subprocess.run(
            [interpreter, "-c", "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())",
             str(f)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            failures.append((f, result.stderr.strip().splitlines()[-1] if result.stderr else "unknown error"))

    if failures:
        print(f"{len(failures)} file(s) fail to parse under {interpreter}:\n")
        for f, err in failures:
            print(f"  {f.relative_to(ROOT)}\n    {err}")
        return 1

    print(f"OK — {len(files)} files parse cleanly under {interpreter}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
