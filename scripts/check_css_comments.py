#!/usr/bin/env python3
"""Guard against CSS comments that close early and silently kill a rule.

The failure mode (which once disabled the entire `.section-nav` rule in
`webapp/static/themes/base-vars.css`): a `/* ... */` comment whose prose
contains the sequence ``*/`` — e.g. ``(mb-*/mt-*)``. The browser's CSS parser
closes the comment at that FIRST ``*/``; the remaining prose then parses as a
bad selector and error-recovery swallows the rule that follows. `tinycss2` and
most linters tokenise comments loosely and never flag it, so it goes unnoticed.

This scanner walks each CSS file as a state machine (normal / string / comment)
and flags any ``*/`` that appears while NOT inside a comment — an *orphan close*.
An orphan close is unambiguous: it can only exist because an earlier comment was
terminated prematurely. It also reports comments left unterminated at EOF.

Run from the repo root:
    python scripts/check_css_comments.py

Exits 0 if clean, 1 if any issue is found.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Every place the webapp serves hand-written CSS from.
SCAN_GLOBS = ["webapp/static/themes/*.css", "webapp/static/*.css"]


def scan(text: str):
    """Return a list of (line, col, message) issues for one CSS file."""
    issues = []
    state = "normal"          # normal | string | comment
    quote = ""                # active quote char when state == "string"
    line = col = 1
    i, n = 0, len(text)

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if state == "normal":
            if ch == "/" and nxt == "*":
                state = "comment"
                i += 2; col += 2
                continue
            if ch == "*" and nxt == "/":
                # Closing a comment that isn't open → an earlier comment closed
                # early. This is the bug.
                issues.append((line, col,
                               "orphan '*/' outside any comment — an earlier "
                               "comment almost certainly closed early (a '*/' "
                               "buried in its text, e.g. 'mb-*/mt-*')"))
                i += 2; col += 2
                continue
            if ch in "\"'":
                state, quote = "string", ch
        elif state == "string":
            if ch == "\\":               # escape — skip next char
                i += 2; col += 2
                continue
            if ch == quote:
                state, quote = "normal", ""
        elif state == "comment":
            if ch == "*" and nxt == "/":
                state = "normal"
                i += 2; col += 2
                continue

        if ch == "\n":
            line += 1; col = 1
        else:
            col += 1
        i += 1

    if state == "comment":
        issues.append((line, col, "unterminated comment ('/*' with no closing '*/')"))
    return issues


def main():
    files = sorted({p for g in SCAN_GLOBS for p in ROOT.glob(g)})
    total = 0
    for path in files:
        for ln, cl, msg in scan(path.read_text(encoding="utf-8")):
            total += 1
            rel = path.relative_to(ROOT)
            print(f"ERROR {rel}:{ln}:{cl}: {msg}")

    if total:
        print(f"\n{total} CSS comment issue(s) found. A buried '*/' breaks the "
              f"following rule in the browser — reword the comment (e.g. "
              f"'mb-*/mt-*' → 'mb-, mt-').")
        return 1
    print(f"CSS comments OK ({len(files)} file(s) scanned).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
