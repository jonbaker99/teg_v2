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
from teg_analysis.reporting.newspaper_edition import (
    ArticleFilter,
    available_tegs,
    build_edition,
    for_page,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "webapp" / "report_layout_prototypes" / "editions.json"


def _parse_args(argv=None):
    import argparse

    ap = argparse.ArgumentParser(
        prog="python -m scripts.build_newspaper_edition",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--min-compelling", type=int, default=None,
                    help="Only print stories scoring at least this (0-10).")
    ap.add_argument("--min-humour", type=int, default=None,
                    help="Only print stories scoring at least this (0-10).")
    ap.add_argument("--match", choices=("all", "any"), default="all",
                    help="Whether a story must clear BOTH score floors (all, default) "
                         "or EITHER (any).")
    ap.add_argument("--min-combined", type=int, default=None,
                    help="Rescue: print a story whose compelling+humour reaches this "
                         "even if it misses the floors. Lets a very funny but less "
                         "compelling piece through.")
    args = ap.parse_args(argv)
    if all(v is None for v in (args.min_compelling, args.min_humour, args.min_combined)):
        return None      # no flags: use the module default
    return ArticleFilter(min_compelling=args.min_compelling or 0,
                         min_humour=args.min_humour or 0,
                         match=args.match,
                         min_combined=args.min_combined or 0)


def main(argv=None) -> None:
    # Discovered, not hardcoded: generating a report for a new TEG used to need
    # someone to remember to edit AVAILABLE_TEGS before it showed up here.
    tegs = available_tegs()
    if not tegs:
        raise SystemExit("no TEG has storyline-first artefacts — nothing to build")
    print(f"Building editions for TEG {', '.join(str(t) for t in tegs)}")
    article_filter = _parse_args(argv)
    editions = [build_edition(teg, article_filter) for teg in tegs]
    if article_filter is not None:
        print(f"Filter: {article_filter.describe()}")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps([for_page(e) for e in editions], indent=2) + "\n", encoding="utf-8")
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
        for a in edition["dropped_articles"]:
            # Named, not silently gone: the story is still in the plan, the draft
            # and the styled markdown — it just did not make the paper.
            print(f"  NOT PRINTED [{a['kicker']}] {a['headline']!r} "
                  f"(compelling={a['compelling']}, humour={a['humour']})")
        print(f"  standings rounds: {[s['round'] for s in edition['standings']]}")
        print(f"  records: {len(edition['records'])}")

    # Step 2. Not optional: a rebuilt editions.json that is not inlined leaves
    # the prototype pages showing the previous content, which is worse than not
    # rebuilding at all — it looks done.
    print()
    inline_editions()


if __name__ == "__main__":
    main()
