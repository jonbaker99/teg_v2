"""CLI: regenerate `webapp/report_layout_prototypes/editions.json`.

The parser (`build_edition`) and its private helpers live in
`teg_analysis.reporting.newspaper_edition` — UI-agnostic, and shared with
`webapp/routes/report_preview.py`, which is why it moved out of `scripts/`.
This file is now just the local dev-tool entry point:

    python -m scripts.build_newspaper_edition

Also re-exports `build_edition` for anything still importing it from here.
"""

from __future__ import annotations

import json
from pathlib import Path

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


if __name__ == "__main__":
    main()
