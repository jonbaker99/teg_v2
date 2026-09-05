"""Re-inline editions.json into the layout prototypes.

The prototype pages are self-contained on purpose (a published Artifact cannot
fetch a sibling file — CSP blocks it), so the edition data lives inside each
page as a JS literal. Run this after `python -m scripts.build_newspaper_edition`
to push the regenerated data back into the pages:

    python -m scripts.inline_editions

Replaces everything between the `var EDITIONS = ` marker and its closing `];`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROTO_DIR = REPO_ROOT / "webapp" / "report_layout_prototypes"
EDITIONS_PATH = PROTO_DIR / "editions.json"
TARGETS = ("newspaper.html", "mobile.html", "composite.html")

_BLOCK_RE = re.compile(r"(  var EDITIONS = )\[.*?\n  \];\n", re.DOTALL)


def inline_into(path: Path, editions_js: str) -> bool:
    text = path.read_text(encoding="utf-8")
    new_text, n = _BLOCK_RE.subn(lambda m: m.group(1) + editions_js, text, count=1)
    if not n:
        return False
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    editions = json.loads(EDITIONS_PATH.read_text(encoding="utf-8"))
    # 2-space base indent so the literal sits correctly inside the IIFE.
    body = json.dumps(editions, indent=2)
    body = "\n".join(("  " + line) if line else line for line in body.split("\n"))
    editions_js = body.strip() + ";\n"

    for name in TARGETS:
        path = PROTO_DIR / name
        if not path.exists():
            continue
        ok = inline_into(path, editions_js)
        print(f"{'inlined' if ok else 'NO MARKER in'} {name}"
              f" ({len(editions)} editions)")


if __name__ == "__main__":
    main()
