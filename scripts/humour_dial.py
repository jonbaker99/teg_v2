"""Humour-dial experiment — produce voice variants of a finished report.

Thin wrapper over `authoring.restyle_voice()`. This file's real content is the
VOICE PROMPTS below: the registers that were A/B'd on TEGs 14 and 18 and never
settled. See EXPERIMENTS.md -> H8.

Was previously a one-off script with the TEG list hardcoded (stuck at
`TEGS = [18]` mid-retry after a connection reset) and the faithfulness rules
restated inline. It now takes arguments, and the guardrails come from the shared
`WRITER_FAITHFULNESS` constant, so a variant cannot drift out of step with the
main writer's rules.

Usage, from the repo root:

    python scripts/humour_dial.py --teg 14 --variant humour8b
    python scripts/humour_dial.py --teg 14 --variant humour6 --variant humour8
    python scripts/humour_dial.py --list

Each run writes `data/commentary/teg_N_report_{variant}.md` and a `_styled.md`
alongside it, so a variant is directly comparable line-for-line with
`teg_N_report_styled.md`. The canonical `report_final.md` is never touched.

Cost: ~$0.10 per variant. Verification runs automatically and reports any fault
the rewrite *introduced* (as opposed to inherited from the source).
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from teg_analysis.reporting.authoring import restyle_voice


# ---------------------------------------------------------------------------
# The voice registers. Each is layered ON TOP of the baseline house voice
# (Ronay / Peck / Armstrong / Iannucci), which stays the floor.
# ---------------------------------------------------------------------------
HUMOUR_6 = """VOICE TARGET: the same deadpan gravitas, dialled from roughly 3/10 to 6/10.

Keep the baseline register — Barney Ronay, Tom Peck, Jesse Armstrong, Armando \
Iannucci. British English, no exclamation marks, no obvious puns.

What changes at 6/10:
- More frequent comic landings: 5-7 across the report rather than 2-3.
- Slightly more licence with comparison and overstatement, still anchored to \
the facts of the round.
- The core mechanism is unchanged: subverted gravitas. Trivial stakes treated \
with the solemnity of a geopolitical crisis. Never wink at the camera."""

HUMOUR_8 = """VOICE TARGET: the same deadpan gravitas, dialled from roughly 3/10 to 8/10.

Keep the baseline register as the floor — Ronay, Peck, Armstrong, Iannucci — \
and add Charlie Brooker and Clive James: bigger swings, sustained comic images, \
a willingness to let a comparison run.

What changes at 8/10:
- 7-10 landed comic moments across the report.
- Big swings permitted: a genuinely funny sustained image is worth a sentence \
or two of build.
- Still no exclamation marks, no puns, no winking. The cruelty stays deadpan."""

HUMOUR_8B = """VOICE TARGET: 8/10, BROOKER-ONLY. Drops Clive James and the literary-comparison \
register that came with him; adds Marina Hyde for matched contemporary punch.

You are ADDING TWO INFLUENCES to the baseline (Ronay / Peck / Armstrong / \
Iannucci), both modern Guardian-column voice, both punch-not-flourish:

- **Charlie Brooker** (Screen Burn / TV Go Home era): contemporary, vicious, \
specific, physical. Speaking-voice prose, not essay-voice. Comparisons are \
PHYSICAL and CONTEMPORARY (broken household objects, malfunctioning tech, \
mundane horrors, bodily indignity), never literary or classical. Escalation \
through specificity. Sentences usually short. He never reaches for Shakespeare \
where a phrase about a stuck pixel or a faulty kettle will do.
- **Marina Hyde**: same register, applied to public absurdity. Running jokes \
that accumulate across the piece. Sharp specific cruelty about behaviour and \
pattern. State the absurd thing, follow with the deadpan correction, move on.

WHAT TO AIM FOR:
- PHYSICAL, CONTEMPORARY comparisons drawn from present-day ordinary life.
- STACCATO escalation, not sustained metaphor. One short sharp image, then move.
- SPEAKING VOICE. The reader should hear it said, not written. Contractions fine.
- 7-10 landed comic moments: 3-4 sharp images, the rest wry asides and cruel \
restatements built into existing sentences.

EXPLICIT FAILURE MODES — DO NOT REPEAT:
- No literary/classical register. "In the manner of", "the kind of stretch that" \
— all out. This is Brooker-on-deadline, not Ronay-on-Sunday-supplement.
- No sustained metaphor across clauses or paragraphs. Start an image, finish it \
inside the sentence.
- No generic kicker formulas. The kicker must be specific to THIS player, THIS \
round, THIS card.
- No setup-punchline structures. No "It was as if...", no "What can you say \
about...", no "you have to admire...".
- No surface wit. Say the cruel thing as if it were the only honest description \
of what happened. Never advertise the joke.
- No flourish bolted onto a sentence that already works. The dial is about WHICH \
sentences get the swing, not adding wit to every sentence.
- Do not loosen the deadpan. No exclamation marks, no puns, no wacky tropes, no \
jokes ABOUT golf as a sport.
- No clever-for-clever's-sake numerical games ("the seventeenth-from-last hole" \
— twee, and wrong). If the cleverness needs mental arithmetic to land, cut it."""

VARIANTS = {"humour6": HUMOUR_6, "humour8": HUMOUR_8, "humour8b": HUMOUR_8B}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--teg", type=int, help="TEG number")
    ap.add_argument("--variant", action="append", default=[],
                    help=f"one of {sorted(VARIANTS)} (repeatable)")
    ap.add_argument("--list", action="store_true", help="list available variants")
    args = ap.parse_args(argv)

    if args.list or not args.teg:
        print("Available variants:")
        for name in sorted(VARIANTS):
            first = VARIANTS[name].split("\n")[0]
            print(f"  {name:10s} {first}")
        print("\nUsage: python scripts/humour_dial.py --teg 14 --variant humour8b")
        return 0

    variants = args.variant or sorted(VARIANTS)
    unknown = [v for v in variants if v not in VARIANTS]
    if unknown:
        ap.error(f"unknown variant(s) {unknown}; choose from {sorted(VARIANTS)}")

    for name in variants:
        print(f"\n=== TEG {args.teg}: {name} ===", flush=True)
        t0 = time.time()
        out = restyle_voice(args.teg, VARIANTS[name], name)
        print(f"  -> {out['output_path']}")
        print(f"  -> {out['styled_path']}")
        print(f"  {time.time() - t0:.1f}s"
              + ("  ✓ no new faults" if not out["new_findings"] else ""))
    print("\nCompare each against data/commentary/teg_"
          f"{args.teg}_report_styled.md, then record the verdict in "
          "teg_analysis/reporting/EXPERIMENTS.md -> H8.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
