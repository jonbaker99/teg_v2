"""Retrofit the current content rules onto reports that are already written.

Two rules reached the writers and the editors on 2026-09-10 —
`prompts.RANKING_RULE` (a rank is only cited if it is top 3) and
`prompts.NAMING_RULE` (no ambiguous surname; name the edition on a
competition's first mention) — after the storyline-first reports for TEGs 14,
16 and 18 were already on disk. Regenerating those reports would apply the
rules, but it also re-rolls every subject, headline and section, so it changes
far more than the rules do and costs a full run per TEG.

This script is the narrow alternative. Two things happen, and they have very
different costs:

1. **Re-style (free, no LLM).** The standings block and the newspaper rail are
   deterministic — `render.style_text` rebuilds them from the parquet data. The
   2026-09-10 presentation changes (round scores in brackets beside the
   cumulative total; the rail's runner-up line without its score) need nothing
   more than re-styling the unstyled report. Note it must run from the UNSTYLED
   file: `render._inject_standings` is idempotent and skips a text that already
   has a standings block.

2. **Corrections pass (one LLM call per TEG).** `authoring.apply_corrections`
   sends the finished prose back through the model with the two rules and a
   contract permitting exactly two edits: delete a rank claim the rule does not
   allow, and expand an ambiguous name or first competition mention. Everything
   else is frozen. D3 runs over the result and reports anything the pass
   introduced.

This is NOT `restyle_voice`, deliberately. That function's contract holds facts
constant so a voice A/B has one variable; a pass that deletes a claim would
break the property that makes it useful.

Usage, from the repo root:

    # Free: re-style only, no model call. Picks up standings + rail changes.
    python scripts/apply_report_rules.py --tegs 14,16,18 --restyle-only

    # Full: corrections pass then re-style. Anthropic API, bills per token.
    python scripts/apply_report_rules.py --tegs 14,16,18

    # Same, on claude.ai plan usage — prompts hand off through data/llm_mailbox
    # and a Claude Code session answers them with the `teg-report-respond` skill.
    TEG_LLM_PROVIDER=agent python scripts/apply_report_rules.py --tegs 14,16,18

`--tegs` takes `14`, `2-18`, `8,9,14` or a mix. The corrected report is written
back over its source, with the original preserved as
`teg_N_report_{label}_precorrections.md` the first time — a second run will not
clobber that backup with already-corrected text.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from teg_analysis.reporting.authoring import apply_corrections
from teg_analysis.reporting.backfill import parse_teg_spec
from teg_analysis.reporting.paths import output_dir
from teg_analysis.reporting.render import style_text


def restyle_only(teg_num: int, source_label: str) -> str:
    """Re-run Stage 5 over the unstyled report. No LLM call.

    Reads `teg_N_report_{source_label}.md` and rewrites its `_styled.md`, so the
    standings block and the records appendix are regenerated in the current
    format from the current data.
    """
    src = f"{output_dir()}/teg_{teg_num}_report_{source_label}.md"
    if not os.path.exists(src):
        raise FileNotFoundError(
            f"{src} not found — TEG {teg_num} has no {source_label!r} report to style.")
    with open(src) as f:
        text = f.read()
    out = f"{output_dir()}/teg_{teg_num}_report_{source_label}_styled.md"
    with open(out, "w") as f:
        f.write(style_text(teg_num, text))
    return out


def run_one(teg_num: int, *, source_label: str, restyle_only_mode: bool,
            model: str | None = None) -> None:
    if restyle_only_mode:
        out = restyle_only(teg_num, source_label)
        print(f"[apply_report_rules] TEG {teg_num}: re-styled -> {out}")
        return

    print(f"[apply_report_rules] TEG {teg_num}: corrections pass...")
    result = apply_corrections(teg_num, source_label=source_label, model=model)
    if result["backup_path"]:
        print(f"[apply_report_rules]   original preserved: {result['backup_path']}")
    print(f"[apply_report_rules]   wrote {result['output_path']}")
    print(f"[apply_report_rules]   wrote {result['styled_path']}")
    if not result["changed"]:
        print("[apply_report_rules]   no change — the report already complied.")
    print(f"[apply_report_rules]   D3 new findings introduced: {len(result['new_findings'])}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Apply the current ranking and naming rules to existing reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    ap.add_argument("--tegs", required=True,
                    help="TEGs to process: 14, 2-18, 8,9,14, or a mix.")
    ap.add_argument("--source-label", default="storylinefirst",
                    help="Which report variant to correct (default: storylinefirst). "
                         "Reads teg_N_report_{label}.md, the UNSTYLED file.")
    ap.add_argument("--restyle-only", action="store_true",
                    help="Skip the model call. Re-styles only, which picks up the "
                         "deterministic standings and rail changes and nothing else.")
    ap.add_argument("--model", default=None,
                    help="Override the model for the corrections pass.")
    args = ap.parse_args()

    tegs = parse_teg_spec(args.tegs)
    mode = "re-style only" if args.restyle_only else "corrections + re-style"
    print(f"[apply_report_rules] TEGs {tegs} ({mode})")

    failed = []
    for teg in tegs:
        try:
            run_one(teg, source_label=args.source_label,
                    restyle_only_mode=args.restyle_only, model=args.model)
        except Exception as exc:  # one bad TEG must not abort the rest
            print(f"[apply_report_rules] TEG {teg} FAILED: {exc}")
            failed.append(teg)
    if failed:
        print(f"[apply_report_rules] failed: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
