"""Storyline-discovery A/B — can an LLM find compelling subplots, hinted or cold?

STORYLINE_PLAN.md Phase 1 built `threads.py`, a free deterministic beat-clustering
pass, and found it surfaces real signal (repeated-course, recurring-failure
clusters) but also a lot of noise (a cluster for nearly every player). Jon's
question (2026-08-18): can an LLM actually spot the compelling 2-4 storylines
at all, and does giving it `candidate_threads` + `win_anatomy` as hints help,
or does the hint list mostly just add noise the model has to see through?

Three arms, same TEG, same underlying beats:

- **cold**    — raw beats + competition_arcs only. No computed advisories.
- **hinted**  — cold + `win_anatomy` (why the Trophy was won) + `candidate_threads`
                (threads.py's clustering), framed as advisory, not verdict.
- **fallback**— hinted + an explicit instruction that returning zero/one
                discovered storylines is correct when nothing clears the bar.

Every arm always drafts a trophy/jacket/spoon storyline (guaranteed material for
the "how the trophies were won" section, and a baseline to score discovered
storylines against) plus 1-3 independently-discovered ones. A fourth call judges
all three arms blind against a rubric.

Usage, from the repo root (needs ANTHROPIC_API_KEY / TEG_ANTHROPIC_API_KEY):

    python scripts/storyline_experiment.py --teg 14

Cost: ~4 calls (3 drafts + 1 judge) on DEFAULT_MODEL, roughly $0.20-0.40 for one TEG.
Writes results to data/commentary/storyline_experiment_teg_{N}.json — nothing in
the production pipeline reads this file; it's for reading by a human.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Literal, Optional

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from pydantic import BaseModel, Field

from teg_analysis.reporting import llm
from teg_analysis.reporting.paths import output_dir
from teg_analysis.reporting.story_plan import assemble_bundle
from teg_analysis.reporting.threads import detect_threads


# ---------------------------------------------------------------------------
# Schema — standalone, deliberately NOT StoryPlan. This is an experiment to
# decide whether Phase 2 (schema change) is worth doing at all.
# ---------------------------------------------------------------------------
class DraftedStoryline(BaseModel):
    subject: str = Field(description="Who or what this storyline is about")
    why_it_matters: str = Field(description="One sentence: why a reader would care")
    shape: str = Field(description="Setup -> turn -> resolution, 2-3 sentences")
    beat_ids: list[str] = Field(description="The specific beat IDs this is built from")
    compelling_score: int = Field(ge=1, le=10,
        description="Your own rating of how GOOD A STORY this is (not how "
                    "important the outcome was to the standings)")


class StorylineDraft(BaseModel):
    trophy_storyline: DraftedStoryline
    jacket_storyline: DraftedStoryline
    spoon_storyline: DraftedStoryline
    discovered_storylines: list[DraftedStoryline] = Field(
        max_length=3,
        description="1-3 ADDITIONAL storylines found independently in the beats. "
                    "Can be about anything, not just who won a competition. "
                    "Return fewer (even zero) if nothing else clears the bar.")


SYSTEM_PROMPT = """You are a golf tournament story editor. You are given event data \
("beats") for one TEG — an annual amateur golf tournament with three competitions \
decided over the same rounds: the Trophy (the main event), the Green Jacket (gross \
scoring), and the Wooden Spoon (last place, played for laughs).

Your job: identify the storylines a report should be built around — not \
round-by-round summaries, but narrative threads with a real shape (setup, turn, \
resolution) that a reader would call a story, not a stats recap.

Always produce, regardless of how good you judge them to be:
1. trophy_storyline — the MOST COMPELLING way to tell how the Trophy was won. \
This is the report's lead. Find the best version of this story, not a flat \
recitation of who led each round.
2. jacket_storyline — how the Green Jacket was won, told as well as the data allows.
3. spoon_storyline — how the Wooden Spoon was "won", told as well as the data allows.

These three are mandatory whether or not they turn out to be the best story in the \
tournament. They are guaranteed material for a "how the trophies were won" section, \
and a baseline to judge the next group against.

Then:
4. discovered_storylines — 1 to 3 ADDITIONAL storylines, found independently in the \
beats, that you judge to be genuinely the most compelling stories in this \
tournament. They do NOT have to be about who won a competition — a player's arc \
across rounds, a rivalry, a course, a recurring pattern are all fair game. Only \
include ones supported by real beats spanning more than one round that you would \
actually call a story. If nothing clears that bar, return fewer — even zero. A \
manufactured subplot is worse than an honest absence.

For every storyline (all four fields), give subject, why_it_matters (one \
sentence), shape (setup -> turn -> resolution, 2-3 sentences), beat_ids (the \
specific IDs it's built from), and compelling_score (1-10: how good a STORY this \
is, not how much it mattered to the result).

Ground every claim in the beat data you are given. Do not invent facts, players, \
or outcomes not present in the data."""

ARM_ADDENDA = {
    "cold": (
        "\n\nYou are given raw event beats and the basic competition arcs (who led "
        "each round, by how much). No editorial hints are provided — find "
        "everything yourself from the raw data."
    ),
    "hinted": (
        "\n\nYou are also given `win_anatomy` (a deterministic breakdown of why the "
        "Trophy was actually won) and `candidate_threads` (a deterministic "
        "clustering of beats that MIGHT be subplots). Both are ADVISORY, not a "
        "verdict — candidate_threads in particular is known to include a lot of "
        "noise (it clusters every player's beats, most of which aren't a real "
        "story). Use your own judgement about what's actually compelling."
    ),
    "fallback": (
        "\n\nYou are also given `win_anatomy` (a deterministic breakdown of why the "
        "Trophy was actually won) and `candidate_threads` (a deterministic "
        "clustering of beats that MIGHT be subplots). Both are ADVISORY, not a "
        "verdict — candidate_threads in particular is known to include a lot of "
        "noise (it clusters every player's beats, most of which aren't a real "
        "story). Use your own judgement about what's actually compelling.\n\n"
        "Remember: if nothing beyond the three guaranteed storylines is genuinely "
        "compelling, it is correct and expected to return zero or one "
        "discovered_storylines. Do not force a subplot to fill a quota."
    ),
}


def _build_arm_bundle(teg_num: int, arm: str) -> dict:
    bundle, _ = assemble_bundle(teg_num, top_n=None)
    out = {
        "teg": bundle["teg"],
        "trophy_metric": bundle["trophy_metric"],
        "venue": bundle["venue"],
        "competition_arcs": bundle["competition_arcs"],
        "player_relationships": bundle["player_relationships"],
        "beats": bundle["beats"],
    }
    if arm in ("hinted", "fallback"):
        out["win_anatomy"] = bundle["win_anatomy"]
        out["candidate_threads"] = detect_threads(bundle["beats"], bundle["competition_arcs"])
    return out


def run_arm(teg_num: int, arm: str, model: Optional[str] = None) -> dict:
    bundle = _build_arm_bundle(teg_num, arm)
    system = SYSTEM_PROMPT + ARM_ADDENDA[arm]
    user = ("Draft the storylines for the following TEG. Use ONLY this data.\n\n"
           + json.dumps(bundle, indent=2, ensure_ascii=False))
    draft, usage = llm.generate_structured(system, user, StorylineDraft,
                                           model=model or llm.DEFAULT_MODEL,
                                           stage="storyline_experiment",
                                           label=f"teg{teg_num}_{arm}")
    return {"arm": arm, "draft": draft.model_dump(), "usage": _usage_dict(usage)}


def _usage_dict(usage) -> dict:
    try:
        return {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}
    except AttributeError:
        return {}


# ---------------------------------------------------------------------------
# Judge — blind, sees all three arms' output (labeled A/B/C, not by arm name)
# plus the raw beats, and scores each against a rubric.
# ---------------------------------------------------------------------------
class ArmScore(BaseModel):
    label: str = Field(description="A, B, or C — matches the input labeling")
    lead_clarity: int = Field(ge=1, le=10, description="Is the Trophy storyline genuinely the best version of that story?")
    subplot_quality: int = Field(ge=1, le=10, description="Are the discovered storylines real stories, not beat dumps?")
    chosen_not_defaulted: int = Field(ge=1, le=10, description="Does the overall set feel like a deliberate editorial choice, not a formula?")
    factual_integrity: int = Field(ge=1, le=10, description="Are all claims actually grounded in the beat_ids cited? Check against the raw data provided.")
    notes: str = Field(description="1-3 sentences: what worked, what didn't")


class JudgeVerdict(BaseModel):
    scores: list[ArmScore]
    overall_ranking: list[str] = Field(description="Labels best to worst, e.g. ['B', 'C', 'A']")
    summary: str = Field(description="2-4 sentences: what this comparison shows")


def run_judge(teg_num: int, arm_results: list[dict], model: Optional[str] = None) -> dict:
    bundle, _ = assemble_bundle(teg_num, top_n=None)
    labels = ["A", "B", "C"]
    labeled = {lab: r["draft"] for lab, r in zip(labels, arm_results)}
    mapping = {lab: r["arm"] for lab, r in zip(labels, arm_results)}

    system = """You are judging three storyline drafts for the same golf tournament \
report, produced by different methods (which you are not told). Score each \
BLIND against this rubric, 1-10 per axis:

- lead_clarity: is the Trophy storyline genuinely the best version of that story?
- subplot_quality: are the discovered storylines real stories with a shape \
(setup/turn/resolution), not just a list of beats that happened to the same player?
- chosen_not_defaulted: does the set feel like a deliberate editorial choice, or \
like a formula applied mechanically?
- factual_integrity: check every beat_id cited against the raw beat data provided \
below. Penalize invented facts or beat_ids that don't support the claim.

You are also given the raw beats for the tournament so you can verify factual \
claims independently. Do not assume any draft is correct just because it's \
confident."""
    user = (f"Raw beats and arcs for TEG {teg_num}:\n\n"
           + json.dumps({"competition_arcs": bundle["competition_arcs"],
                        "beats": bundle["beats"]}, indent=2, ensure_ascii=False)
           + "\n\n---\n\nThree drafts to judge (A, B, C):\n\n"
           + json.dumps(labeled, indent=2, ensure_ascii=False))
    verdict, usage = llm.generate_structured(system, user, JudgeVerdict,
                                             model=model or llm.DEFAULT_MODEL,
                                             stage="storyline_experiment_judge",
                                             label=f"teg{teg_num}_judge")
    return {"verdict": verdict.model_dump(), "label_to_arm": mapping,
            "usage": _usage_dict(usage)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--teg", type=int, required=True)
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    if not llm.has_api_key():
        print("No API key found (ANTHROPIC_API_KEY / TEG_ANTHROPIC_API_KEY). Aborting.")
        sys.exit(1)

    results = []
    for arm in ("cold", "hinted", "fallback"):
        print(f"[storyline_experiment] TEG {args.teg}: running arm '{arm}'...")
        results.append(run_arm(args.teg, arm, model=args.model))

    print(f"[storyline_experiment] TEG {args.teg}: running blind judge...")
    judge = run_judge(args.teg, results, model=args.model)

    out = {"teg": args.teg, "arms": results, "judge": judge}
    path = f"{output_dir()}/storyline_experiment_teg_{args.teg}.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"[storyline_experiment] wrote {path}")

    print("\n=== Judge verdict ===")
    print(judge["verdict"]["summary"])
    print("Ranking:", judge["verdict"]["overall_ranking"], "->",
         {lab: judge["label_to_arm"][lab] for lab in judge["verdict"]["overall_ranking"]})
    for s in judge["verdict"]["scores"]:
        arm = judge["label_to_arm"][s["label"]]
        print(f"  {s['label']} ({arm}): lead={s['lead_clarity']} subplot={s['subplot_quality']} "
             f"chosen={s['chosen_not_defaulted']} factual={s['factual_integrity']} — {s['notes']}")


if __name__ == "__main__":
    main()
