"""CLI: rebuild the layout prototypes from the current report artefacts.

    python -m scripts.build_newspaper_edition

Two steps, always run together, so this does both:

1. Rebuild `webapp/report_layout_prototypes/editions.json` from whichever TEGs
   have storyline-first artefacts. Tournaments only by default — pass
   `--include-rounds` to also build every round with storyline-first round
   artefacts (`round_storyline.py`), or `--no-tournaments` to build rounds
   ONLY (implies `--include-rounds`). Tournaments and rounds take separate
   quality filters — `--min-*` for tournaments, `--round-min-*` for rounds —
   so each can use different criteria, or one can be filtered while the other
   isn't; neither inherits the other's flags.
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
    available_rounds,
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
                    help="TOURNAMENTS: only print DISCOVERED stories scoring at least this "
                         "(0-10). Trophy, Green Jacket and Wooden Spoon are always printed.")
    ap.add_argument("--min-humour", type=int, default=None,
                    help="TOURNAMENTS: only print stories scoring at least this (0-10).")
    ap.add_argument("--match", choices=("all", "any"), default="all",
                    help="TOURNAMENTS: whether a story must clear BOTH score floors "
                         "(all, default) or EITHER (any).")
    ap.add_argument("--min-combined", type=int, default=None,
                    help="TOURNAMENTS: rescue — print a story whose compelling+humour "
                         "reaches this even if it misses the floors.")
    ap.add_argument("--round-min-compelling", type=int, default=None,
                    help="ROUNDS: same as --min-compelling, applied to round editions "
                         "only. round_story/race_story are always printed.")
    ap.add_argument("--round-min-humour", type=int, default=None,
                    help="ROUNDS: same as --min-humour, applied to round editions only.")
    ap.add_argument("--round-match", choices=("all", "any"), default="all",
                    help="ROUNDS: same as --match, applied to round editions only.")
    ap.add_argument("--round-min-combined", type=int, default=None,
                    help="ROUNDS: same as --min-combined, applied to round editions only.")
    ap.add_argument("--include-rounds", action="store_true",
                    help="Also build editions for every round with storyline-first "
                         "round artefacts (round_storyline.py), alongside tournaments.")
    ap.add_argument("--no-tournaments", action="store_true",
                    help="Skip tournament editions entirely and build rounds only. "
                         "Implies --include-rounds.")
    args = ap.parse_args(argv)

    def _filter_from(compelling, humour, match, combined):
        if all(v is None for v in (compelling, humour, combined)):
            return None      # no flags for this kind: use the module default
        return ArticleFilter(min_compelling=compelling or 0, min_humour=humour or 0,
                             match=match, min_combined=combined or 0)

    tournament_filter = _filter_from(args.min_compelling, args.min_humour,
                                     args.match, args.min_combined)
    round_filter = _filter_from(args.round_min_compelling, args.round_min_humour,
                                args.round_match, args.round_min_combined)
    include_rounds = args.include_rounds or args.no_tournaments or round_filter is not None
    return tournament_filter, round_filter, include_rounds, args.no_tournaments


def _print_edition(edition: dict) -> None:
    label = f"TEG {edition['teg']}" if edition["dateline"].get("round") is None \
        else f"TEG {edition['teg']} R{edition['dateline']['round']}"
    print(f"\n{label}: {edition['title']}")
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


def main(argv=None) -> None:
    # Discovered, not hardcoded: generating a report for a new TEG used to need
    # someone to remember to edit AVAILABLE_TEGS before it showed up here.
    tegs = available_tegs()
    if not tegs:
        raise SystemExit("no TEG has storyline-first artefacts — nothing to build")
    tournament_filter, round_filter, include_rounds, no_tournaments = _parse_args(argv)

    editions = []
    if no_tournaments:
        print("Skipping tournaments (--no-tournaments)")
    else:
        print(f"Building editions for TEG {', '.join(str(t) for t in tegs)}")
        editions = [build_edition(teg, article_filter=tournament_filter) for teg in tegs]
        if tournament_filter is not None:
            print(f"Tournament filter: {tournament_filter.describe()}")

    if include_rounds:
        for teg in tegs:
            for r in available_rounds(teg):
                editions.append(build_edition(teg, round_num=r, article_filter=round_filter))
        n_rounds = sum(1 for teg in tegs for _ in available_rounds(teg))
        print(f"Building {n_rounds} round edition(s)"
              + (f" — filter: {round_filter.describe()}" if round_filter is not None
                 else " (unfiltered — pass --round-min-* for a round-specific filter)"))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps([for_page(e) for e in editions], indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} ({len(editions)} editions)")
    for edition in editions:
        _print_edition(edition)

    # Step 2. Not optional: a rebuilt editions.json that is not inlined leaves
    # the prototype pages showing the previous content, which is worse than not
    # rebuilding at all — it looks done.
    print()
    inline_editions()


if __name__ == "__main__":
    main()
