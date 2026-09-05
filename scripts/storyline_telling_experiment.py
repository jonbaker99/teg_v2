"""2b A/B — does a separate, narrow-context "telling" call improve the prose a
writer produces from a storyline, versus writing straight from 2a's output?

STORYLINE_PLAN.md's Phase 2 design (2026-08-18) scoped 2b as a SEPARATE call per
storyline, seeing ONLY that storyline's own cited beat evidence — not the whole
bundle — specifically because the first A/B (storyline_experiment.py) measured
hallucination scaling with context breadth. This script tests whether that bet
pays off: does an explicit bullet-point "telling" outline, grounded in narrow
evidence, produce better final prose than handing a minimal writer the same
storyline (subject/why_it_matters/shape/beat evidence) directly?

For each storyline in an already-generated story plan (trophy/jacket/spoon +
up to 2 discovered, to bound cost):

1. **with_telling**  — run 2b (telling call, narrow evidence-only context) to get
   `telling: list[str]` bullets, then a minimal writer call using them.
2. **without_telling** — the same minimal writer call, straight from
   subject/why_it_matters/shape/beat_ids + the same evidence, no telling step.

A blind judge (order randomised per storyline) scores each pair on compellingness,
clarity, factual grounding, and "reads as a story, not a list".

Usage, from the repo root (needs a story plan already generated for --teg, and
ANTHROPIC_API_KEY / TEG_ANTHROPIC_API_KEY):

    python scripts/storyline_telling_experiment.py --teg 14

Cost: ~3 calls per storyline (telling + 2 writer) + 1 judge call — for the default
5 storylines (3 mandatory + 2 discovered), ~20 calls, roughly $1-2.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
from typing import Optional

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from pydantic import BaseModel, Field

from teg_analysis.reporting import llm
from teg_analysis.reporting.paths import output_dir
from teg_analysis.reporting.story_plan import assemble_bundle


# ---------------------------------------------------------------------------
# 2b — telling call. Narrow context: ONLY this storyline's own beat evidence.
# ---------------------------------------------------------------------------
class Telling(BaseModel):
    bullets: list[str] = Field(min_length=3, max_length=8,
        description="Ordered setup -> turn -> resolution bullets, each a "
                    "specific, vivid beat, anchored in the evidence given")


TELLING_SYSTEM = """You are given ONE storyline for a golf tournament report, \
already identified by an editor (subject, why it matters, its shape), plus the \
FULL hole-by-hole evidence for every beat it cites. You see nothing else about \
this tournament — no other storylines, no standings, no other players' data.

Your job: write the compelling BULLET-POINT telling of this story — the outline \
a writer will follow to draft the actual prose. 4-7 bullets, ordered setup -> \
turn(s) -> resolution. Each bullet should be a specific, vivid beat (a score, a \
hole, a moment), not a vague summary sentence.

RULE: every fact must come from the evidence given to you. Do not invent scores, \
margins, comparisons to other players/rounds, or any context not present in this \
evidence. If the editor's `why_it_matters`/`shape` mentions something not backed \
by the evidence you were given, do not repeat it as fact — describe only what the \
evidence supports."""


def _evidence_for(storyline: dict, all_beats: list) -> list:
    by_id = {b["id"]: b for b in all_beats}
    return [by_id[bid] for bid in storyline["beat_ids"] if bid in by_id]


def run_telling(storyline: dict, evidence: list, model: Optional[str] = None) -> list:
    user = ("Storyline:\n" + json.dumps({
                "subject": storyline["subject"],
                "why_it_matters": storyline["why_it_matters"],
                "shape": storyline["shape"],
            }, indent=2)
           + "\n\nFull evidence for the cited beats:\n"
           + json.dumps(evidence, indent=2, ensure_ascii=False))
    telling, usage = llm.generate_structured(TELLING_SYSTEM, user, Telling,
                                             model=model or llm.DEFAULT_MODEL,
                                             stage="telling_experiment",
                                             label=storyline["subject"][:30])
    return telling.bullets


# ---------------------------------------------------------------------------
# Minimal writer — same prompt shape for both arms, only the input differs.
# ---------------------------------------------------------------------------
WRITER_SYSTEM = """You are writing one section of a golf tournament report — a \
single storyline, not the whole report. British sports-journalism register: \
engaging, a little wry, no exclamation marks, no em-dashes. 150-220 words. \
`subject` and `telling` (if given) are STRUCTURAL GUIDANCE ONLY — which beats to \
use and what order to tell them in. They are NOT a source of facts: do not copy \
any score, margin, comparison, or claim from them unless it also appears in \
`evidence`. Every fact you write must trace to `evidence`. Ground every fact in \
what you are given; never invent scores, margins, or comparisons not present in \
your input."""


def run_writer(storyline: dict, evidence: list, telling: Optional[list],
               model: Optional[str] = None) -> str:
    # Deliberately NOT `why_it_matters`/`shape` — round 1 of this experiment
    # (2026-08-18) found both arms fabricating claims that lived only in that
    # free text (generated by 2a from the full bundle), which defeated 2b's
    # narrow-context isolation. `subject` is kept as a short label; `evidence`
    # is the only fact source either arm gets.
    payload = {"subject": storyline["subject"], "evidence": evidence}
    if telling is not None:
        payload["telling"] = telling
    user = "Write this storyline as a prose section:\n\n" + json.dumps(payload, indent=2, ensure_ascii=False)
    text, usage = llm.generate_text(user=user, system=WRITER_SYSTEM,
                                    model=model or llm.DEFAULT_MODEL,
                                    stage="telling_experiment_writer",
                                    label=storyline["subject"][:30])
    return text.strip()


# ---------------------------------------------------------------------------
# Judge — blind, order randomised per storyline.
# ---------------------------------------------------------------------------
class ABScore(BaseModel):
    A: int = Field(ge=1, le=10)
    B: int = Field(ge=1, le=10)


class PairScore(BaseModel):
    winner: str = Field(description="'A', 'B', or 'tie'")
    compellingness: ABScore
    clarity: ABScore
    factual_grounding: ABScore = Field(description="check against the evidence provided")
    reads_as_story_not_list: ABScore
    notes: str


JUDGE_SYSTEM = """You are comparing two prose drafts of the same golf storyline, \
written by different methods (not told which). Score BLIND against: \
compellingness, clarity, factual_grounding (check every claim against the raw \
evidence provided — penalise anything not supported), reads_as_story_not_list \
(does it flow, or does it read like a bullet list turned into sentences). Pick an \
overall winner, or 'tie' if genuinely close."""


def run_judge(storyline: dict, evidence: list, text_a: str, text_b: str,
             model: Optional[str] = None) -> dict:
    user = (f"Storyline: {storyline['subject']}\n\nRaw evidence:\n"
           + json.dumps(evidence, indent=2, ensure_ascii=False)
           + f"\n\n--- Draft A ---\n{text_a}\n\n--- Draft B ---\n{text_b}")
    verdict, usage = llm.generate_structured(JUDGE_SYSTEM, user, PairScore,
                                             model=model or llm.DEFAULT_MODEL,
                                             stage="telling_experiment_judge",
                                             label=storyline["subject"][:30])
    return verdict.model_dump()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--teg", type=int, required=True)
    ap.add_argument("--max-discovered", type=int, default=2)
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    if not llm.has_api_key():
        print("No API key found. Aborting.")
        sys.exit(1)

    plan_path = f"{output_dir()}/teg_{args.teg}_story_plan.json"
    with open(plan_path) as f:
        plan = json.load(f)

    bundle, _ = assemble_bundle(args.teg, top_n=None)
    all_beats = bundle["beats"]

    storylines = ([plan["trophy_storyline"], plan["jacket_storyline"], plan["spoon_storyline"]]
                 + plan["discovered_storylines"][:args.max_discovered])

    results = []
    for s in storylines:
        print(f"[telling_experiment] TEG {args.teg}: {s['subject'][:60]}")
        evidence = _evidence_for(s, all_beats)

        telling = run_telling(s, evidence, model=args.model)
        text_with = run_writer(s, evidence, telling, model=args.model)
        text_without = run_writer(s, evidence, None, model=args.model)

        # Randomise A/B order so the judge can't learn a positional bias.
        if random.random() < 0.5:
            label_map = {"A": "with_telling", "B": "without_telling"}
            text_a, text_b = text_with, text_without
        else:
            label_map = {"A": "without_telling", "B": "with_telling"}
            text_a, text_b = text_without, text_with

        verdict = run_judge(s, evidence, text_a, text_b, model=args.model)
        winner_arm = label_map.get(verdict["winner"], "tie")

        results.append({
            "subject": s["subject"], "telling": telling,
            "text_with_telling": text_with, "text_without_telling": text_without,
            "label_map": label_map, "verdict": verdict, "winner_arm": winner_arm,
        })
        print(f"    winner: {winner_arm}")

    out_path = f"{output_dir()}/telling_experiment_teg_{args.teg}.json"
    with open(out_path, "w") as f:
        json.dump({"teg": args.teg, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"[telling_experiment] wrote {out_path}")

    tally = {}
    for r in results:
        tally[r["winner_arm"]] = tally.get(r["winner_arm"], 0) + 1
    print("\n=== Tally ===")
    for arm, n in tally.items():
        print(f"  {arm}: {n}")


if __name__ == "__main__":
    main()
