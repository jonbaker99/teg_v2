"""CLI: rebuild the layout prototypes from the current report artefacts.

    python -m scripts.build_newspaper_edition

Two steps, always run together, so this does both:

1. Rebuild `webapp/report_layout_prototypes/editions.json` from whichever TEGs
   have storyline-first artefacts.
2. Inline it into the prototype pages, which carry the data as a JS literal
   because a published Artifact cannot fetch a sibling file.

Step 2 used to be a separate `python -m scripts.inline_editions`, and every doc
wrote the pair with `&&`. Forgetting it left the pages showing older content
than the artefacts on disk -- which happened three times in a week (PR #95's
headlines, the 14/16/18 re-sync, PR #100's rule pass). `inline_editions` still
runs standalone for re-inlining without a rebuild.

The parser (`build_edition`) and its helpers live in
`teg_analysis.reporting.newspaper_edition` — UI-agnostic, and shared with
`webapp/routes/report_preview.py`, which is why it is not in `scripts/`. Note
that route builds its edition per request and never reads `editions.json`, so
none of this affects the live page.

Also re-exports `build_edition` for anything still importing it from here.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.inline_editions import main as inline_editions
from teg_analysis.reporting.newspaper_edition import available_tegs, build_edition

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "webapp" / "report_layout_prototypes" / "editions.json"


def main() -> None:
    # Discovered, not hardcoded: generating a report for a new TEG used to need
    # someone to remember to edit AVAILABLE_TEGS before it showed up here.
    tegs = available_tegs()
    if not tegs:
        raise SystemExit("no TEG has storyline-first artefacts — nothing to build")
    print(f"Building editions for TEG {', '.join(str(t) for t in tegs)}")
    editions = [build_edition(teg) for teg in tegs]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(editions, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} ({len(editions)} editions)")
    for edition in editions:
        print(f"\nTEG {edition['teg']}: {edition['title']}")
        print(f"  dateline: {edition['dateline']}")
        print(f"  results: {[r['label'] for r in edition['results']]}")
        for a in edition["articles"]:
            print(
                f"  [{a['kicker']}] {a['headline']!r} "
                f"(lead={a['is_lead']}, words={a['words']}, "
                f"compelling={a['compelling']}, humour={a['humour']})"
            )
        print(f"  standings rounds: {[s['round'] for s in edition['standings']]}")
        print(f"  records: {len(edition['records'])}")

    # Step 2. Not optional: a rebuilt editions.json that is not inlined leaves
    # the prototype pages showing the previous content, which is worse than not
    # rebuilding at all — it looks done.
    print()
    inline_editions()


if __name__ == "__main__":
    main()
