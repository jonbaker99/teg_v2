"""Generate a round report from the storyline-first method, then apply the
CURRENT production house voice as a final language layer.

The round-level twin of `storyline_full_report_experiment.py`. Same three
stages, same `--from`/`--to` slicing, same anchors, same voice pass — see that
script's module docstring for the general shape; only what differs is
documented here.

    storylines  ->  draft  ->  voice

    storylines  the editor picks `round_story` + `race_story` + 0-3 discovered
    draft       each storyline written plain, fact-isolated, unvoiced
    voice       `authoring.restyle_voice(round_num=...)` rewrites it in the house voice

WHAT DIFFERS FROM THE TOURNAMENT SCRIPT
- Two mandatory storylines, not three (`round_storyline.RoundStorylinePlan`):
  `round_story` (the best round of the day) and `race_story` (how the round
  moved the three competitions — or, on the final round, who won them).
- No interweaving flag. A round's beat pool is small enough that the overlap
  the tournament pipeline interweaves is instead handled in the editor prompt
  (the "overlap check" in `round_storyline.ROUND_STORYLINE_SYSTEM_BASE`):
  `race_story` is told to pivot to whoever LOST ground when it would otherwise
  duplicate `round_story`.
- `--tegs` and `--rounds` both required and run as a cross-product IN ORDER
  (TEG outer, round inner) — `--tegs 16 --rounds 1-4` runs all four rounds of
  TEG 16; `--tegs 14,16 --rounds 4` runs both TEGs' final rounds only.
- The correctness constraint this pipeline exists to hold: a mid-tournament
  round's bundle must not know later rounds happened. See
  `round_storyline.assemble_round_storyline_bundle`'s docstring and
  `_assert_no_future_rounds`, which raises loudly rather than silently leaking.

Usage, from the repo root:

    # One round, full pipeline, Anthropic API (bills per token).
    python scripts/storyline_round_report_experiment.py --tegs 16 --rounds 2

    # A cross-product: TEG 16's four rounds.
    python scripts/storyline_round_report_experiment.py --tegs 16 --rounds 1-4

    # claude.ai plan usage.
    TEG_LLM_PROVIDER=agent python scripts/storyline_round_report_experiment.py --tegs 16 --rounds 2

    # Just the editorial plan, no prose — read it before paying for a word.
    python scripts/storyline_round_report_experiment.py --tegs 16 --rounds 2 --to storylines

    # Dry run: write the composed prompt to disk, no LLM call at all.
    python scripts/storyline_round_report_experiment.py --tegs 16 --rounds 2 --dry-run

    # Redraft sections against the plan already on disk.
    python scripts/storyline_round_report_experiment.py --tegs 16 --rounds 2 --from draft

    # Re-run the voice pass alone.
    python scripts/storyline_round_report_experiment.py --tegs 16 --rounds 2 --from voice
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Optional

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from teg_analysis.reporting import llm
from teg_analysis.reporting.authoring import WRITER_VOICE, restyle_voice
from teg_analysis.reporting.backfill import parse_teg_spec
from teg_analysis.reporting.paths import output_dir
from teg_analysis.reporting.round_storyline import (
    build_round_storyline_draft,
    build_round_storyline_plan,
    load_round_storyline_plan,
)


def run_voice_pass(teg_num: int, round_num: int, model: Optional[str] = None) -> dict:
    """Stage 3 alone: rewrite the frozen structural draft in the house voice."""
    print(f"[storyline_round_report] TEG {teg_num} R{round_num}: applying house voice...")
    result = restyle_voice(teg_num, WRITER_VOICE, label="storylinefirst",
                           source_label="storylinedraft", model=model, round_num=round_num)
    print(f"[storyline_round_report] wrote voiced report: {result['output_path']}")
    print(f"[storyline_round_report] wrote styled report: {result['styled_path']}")
    print(f"[storyline_round_report] D3 new findings introduced by voice pass: "
          f"{len(result['new_findings'])}")
    for f in result["new_findings"]:
        print(f"  - {f}")
    return result


def run_one(teg_num: int, round_num: int, *, start_from: str = "storylines",
           stop_after: str = "voice", model: Optional[str] = None,
           dry_run: bool = False) -> None:
    """Run the stages between `start_from` and `stop_after` for one round."""
    if dry_run:
        result = build_round_storyline_plan(teg_num, round_num, dry_run=True)
        print(f"[storyline_round_report] TEG {teg_num} R{round_num}: wrote prompt "
              f"to {result['prompt_path']} ({result['n_beats']} beats, "
              f"is_final_round={result['is_final_round']}). No LLM call made.")
        return

    if start_from == "voice":
        draft_path = f"{output_dir()}/teg_{teg_num}_round_{round_num}_report_storylinedraft.md"
        print(f"[storyline_round_report] --from voice: reusing {draft_path}, "
              f"regenerating nothing above it.")
        run_voice_pass(teg_num, round_num, model=model)
        return

    reused_plan = None
    if start_from == "draft":
        reused_plan = load_round_storyline_plan(teg_num, round_num)
        print(f"[storyline_round_report] --from draft: reusing "
              f"{output_dir()}/teg_{teg_num}_round_{round_num}_storyline_plan.json, "
              f"redrafting sections.")

    if stop_after == "storylines":
        result = build_round_storyline_plan(teg_num, round_num, model=model)
        plan = result["plan"].model_dump()
        print(f"[storyline_round_report] wrote storyline plan: {result['output_path']}")
        storylines = [plan["round_story"], plan["race_story"]] + plan["discovered_storylines"]
        for s in storylines:
            print(f"  [{s.get('chosen_headline') or s['subject'][:60]}] "
                  f"compelling={s.get('compelling_score')} humour={s.get('humour_score')}")
        if result["warnings"]:
            print(f"  {len(result['warnings'])} consistency warning(s) — see above.")
        return

    draft_text, plan = build_round_storyline_draft(teg_num, round_num, model=model,
                                                    plan=reused_plan)
    print(f"[storyline_round_report] wrote structural draft "
          f"({len(draft_text.split())} words)")

    if stop_after == "draft":
        print("[storyline_round_report] --to draft: stopping before the voice pass.")
        return

    run_voice_pass(teg_num, round_num, model=model)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tegs", required=True,
                    help="Which TEGs: 14, 2-18, 8,9,14, or a mix.")
    ap.add_argument("--rounds", required=True,
                    help="Which rounds, same syntax as --tegs: 2, 1-4, 1,4. Runs "
                         "the TEG x round cross-product, TEG outer, round inner.")
    ap.add_argument("--model", default=None)
    ap.add_argument("--from", dest="start_from",
                    choices=("storylines", "draft", "voice"), default="storylines",
                    help="Which stage to START at. Everything before it is reused "
                         "from disk.")
    ap.add_argument("--to", dest="stop_after",
                    choices=("storylines", "draft", "voice"), default="voice",
                    help="Which stage to STOP after.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Write the composed editor prompt to disk and stop — no "
                         "LLM call at all. Ignores --from/--to.")
    args = ap.parse_args()

    _ORDER = {"storylines": 0, "draft": 1, "voice": 2}
    if _ORDER[args.stop_after] < _ORDER[args.start_from]:
        ap.error(f"--to {args.stop_after} is before --from {args.start_from}: "
                 f"that range has no stages in it.")

    if not args.dry_run and llm.get_provider() == llm.PROVIDER_API and not llm.has_api_key():
        print(f"No API key found, and the provider is {llm.PROVIDER_API}. "
              f"Set one, or run on plan usage with {llm.ENV_PROVIDER}={llm.PROVIDER_AGENT}.")
        sys.exit(1)

    tegs = parse_teg_spec(args.tegs)
    rounds = parse_teg_spec(args.rounds)
    jobs = [(t, r) for t in tegs for r in rounds]
    if len(jobs) > 1:
        print(f"[storyline_round_report] {len(jobs)} TEG/round pairs: {jobs} "
              f"(--from {args.start_from} --to {args.stop_after})")

    failed = []
    for teg, rnd in jobs:
        if len(jobs) > 1:
            print(f"\n{'=' * 70}\n[storyline_round_report] TEG {teg} R{rnd}\n{'=' * 70}")
        try:
            run_one(teg, rnd, start_from=args.start_from, stop_after=args.stop_after,
                    model=args.model, dry_run=args.dry_run)
        except Exception as e:
            failed.append((teg, rnd, e))
            print(f"[storyline_round_report] TEG {teg} R{rnd} FAILED: "
                  f"{type(e).__name__}: {e}")

    if failed:
        print(f"\n[storyline_round_report] {len(failed)} of {len(jobs)} failed:")
        for teg, rnd, e in failed:
            print(f"  TEG {teg} R{rnd}: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
