#!/usr/bin/env python3
"""Verify every deployed .py file parses under the pinned deploy Python version.

Local dev commonly runs a newer interpreter than Railway does, which accepts
syntax the older pinned version does not — e.g. PEP 701's relaxed f-string
grammar (nested same-quote strings inside an f-string, valid from 3.12).
Such a file imports fine locally and passes local tests, then is a hard
SyntaxError in production. If the broken module sits anywhere in
webapp.app's import graph, the whole app fails to start ("Application
failed to respond" on Railway, no traceback in the UI — only in the deploy
log). This happened for real 2026-09-12
(teg_analysis/reporting/newspaper_edition.py), which is why the repo root
now carries a `.python-version` file (3.12 as of this writing) and Railway's
mise-based build reads it — see CLAUDE.md's Python version invariant.

Run from the repo root:
    python scripts/check_python_compat.py

Reads the target version from `.python-version` at the repo root, so it
always checks against whatever's actually pinned rather than a hardcoded
number. Needs a matching interpreter on PATH (checks `python3.<minor>`
first, then a few common install locations). Install one with, e.g.:
    brew install python@3.12
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


def _target_version() -> str:
    version_file = ROOT / ".python-version"
    if not version_file.exists():
        print(
            f"No .python-version at repo root ({version_file}) — nothing to check against.",
            file=sys.stderr,
        )
        sys.exit(1)
    return version_file.read_text().strip()


def _find_interpreter(version: str) -> str | None:
    # version may be a full pin ("3.12.4") or just "3.12" — only major.minor
    # matters for syntax support, so match on that.
    major_minor = ".".join(version.split(".")[:2])
    candidates = [
        f"python{major_minor}",
        f"/opt/homebrew/bin/python{major_minor}",
        f"/opt/homebrew/opt/python@{major_minor}/bin/python{major_minor}",
        f"/usr/local/bin/python{major_minor}",
    ]
    for candidate in candidates:
        path = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
        if path:
            return path
    return None


def main() -> int:
    version = _target_version()
    interpreter = _find_interpreter(version)
    if interpreter is None:
        print(
            f".python-version pins {version}, but no matching interpreter was found on PATH.\n"
            f"Install one: brew install python@{'.'.join(version.split('.')[:2])}",
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
        print(f"{len(failures)} file(s) fail to parse under {interpreter} (pinned {version}):\n")
        for f, err in failures:
            print(f"  {f.relative_to(ROOT)}\n    {err}")
        return 1

    print(f"OK — {len(files)} files parse cleanly under {interpreter} (pinned {version}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
