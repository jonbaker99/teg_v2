"""Voice-of-tone A/B — tests specific refinements to the house voice (`WRITER_VOICE`)
against the settled baseline, on the SAME fixed unvoiced draft (stage 2 of the
storyline-first pipeline: `teg_N_report_storylinedraft.md`). See
`teg_analysis/reporting/STORYLINE_PLAN.md` under this experiment's dated section for
the design conversation these variants came out of.

Six arms, all built as amendments to the CURRENT `WRITER_VOICE` (not designed from
scratch — the point is to test deltas against the settled voice):

1. **baseline** — `WRITER_VOICE` unchanged.
2. **overstatement** — a delivery refinement of the existing `ELEVATION_DEVICE`
   contract block (which already does hyperbole, for every arm including baseline):
   one move per joke (big claim, immediate scoping qualifier, stop — no stacking a
   second flourish on top), and stay inside golf/tournament vocabulary for the
   qualifier rather than reaching for an invented external comparison.
3. **interiority** — a new register: report the player's internal psychological
   state at its most extreme, as flat verified fact, no editorialising.
4. **combined** — both of the above together.
5. **crueller** — raises the field/runner-up mockery to Wooden-Spoon-holder
   intensity; the champion's "hard on the golf, never on the achievement" carve-out
   is explicitly UNCHANGED (confirmed: don't extend cruelty to a deserving winner).
6. **cjmh** — replaces the four-writer rotation (Herron/Ronay/Armstrong/Iannucci)
   with a single consistent Clive James / Marina Hyde register. Everything else in
   `WRITER_VOICE` (comic density, clarity, mockery calibration, named principles)
   stands.

Judge is BLIND, multi-arm (not pairwise — 6 arms would be 15 pairs), order
randomised per TEG, scored on named axes, run across TEG 14/16/18 (all three
already have a `storylinedraft.md` on disk). Results tallied + averaged and written
into STORYLINE_PLAN.md by hand after this script runs.

Usage, from the repo root (ANTHROPIC_API_KEY / TEG_ANTHROPIC_API_KEY required):

    python scripts/storyline_voice_tone_experiment.py --tegs 14,16,18

Cost: 6 restyle_voice calls per TEG (one per arm) + 1 multi-arm judge call per TEG.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
from typing import Dict, List, Optional

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from pydantic import BaseModel, Field

from teg_analysis.reporting import llm, prompts
from teg_analysis.reporting.authoring import (
    WRITER_VOICE, _WRITER_COMIC_AIM, restyle_voice,
)
from teg_analysis.reporting.paths import output_dir

# ---------------------------------------------------------------------------
# Variant voice text
# ---------------------------------------------------------------------------
OVERSTATEMENT_DELIVERY = """OVERSTATEMENT DELIVERY — a refinement to how you execute THE OCCASION contract \
requirement (hamming the achievement/drama/defeat), and to any other place hyperbole is \
the right tool.

One move per joke: state the big claim, then immediately scope it down with a plain \
qualifier, and stop. Do not add a further flourish, image or punchline on top of an \
already-complete overstatement — the qualifier IS the joke, and a second beat dilutes it \
rather than amplifying it.

  RIGHT: "the greatest round of golf he has ever played — on this course, in this competition"
  WRONG (stacked): "...on this course, in this competition, by this specific 54-year-old with a bad knee"

Stay inside golf and tournament vocabulary for the scoping qualifier wherever possible \
("in the history of the tournament", "on this course", "in his golfing history") rather \
than reaching into an unrelated external domain (medical history, humanitarian crises, \
restaurant bookings) for contrast — those constructed comparisons read as try-hard. When \
you do reach outside golf, reach for something universally recognisable and stated \
plainly (a sporting montage, a diary entry) — never an invented, elaborate contraption.

  RIGHT: "unquestionably the finest 94 ever shot in the history of the tournament"
  RIGHT (external, simple): "the kind of turnaround that would be central to a thousand post-match montages"
  WRONG (constructed): "the kind of turnaround that, on a channel with a budget for strings, comes with its own closing credits"

This applies wherever the voice reaches for overstatement, not only in the opening occasion."""

EMOTIONAL_INTERIORITY = """EMOTIONAL INTERIORITY — a fifth register available alongside the four humour \
mechanisms above. Where a moment carries real emotional weight, report the player's \
internal psychological state at its most extreme — not the event, the FEELING — as flat, \
verified fact. No "he must have felt", no exclamation, no editorialising. State the \
specific psychological content plainly, as though it had been observed and confirmed.

  "for four hours, doubt did not so much subside as cease to exist as a concept"
  "somewhere between the third and fourth shot he stopped being a man having a bad hole and became a man reconsidering every decision that had led him to that fairway"
  "eleven years of quietly rehearsed excuses became, in one afternoon, unnecessary"
  "he looked, briefly, like a man who had forgotten he was bad at this"

Use this sparingly, on moments that genuinely carry weight — a drought broken, a \
collapse, a personal-best round, a comeback — not on routine holes. Same discipline as \
the overstatement device: one move, no stacking, stop once the state is named."""

CRUELLER_CALIBRATION = """MOCKERY CALIBRATION — SUPERSEDES the "Mockery, by target" list above for this \
variant only. The field and the runner-up move up to the SAME intensity currently \
reserved for the Wooden Spoon holder: hard, specific, merciless — no more "moderate". \
The Wooden Spoon holder's calibration is unchanged (already hard). **The champion's \
calibration is UNCHANGED**: hard on the golf, never on the achievement. The increased \
intensity given to the field and the runner-up does NOT extend to the champion beyond \
what their golf actually earns — do not manufacture extra cruelty for a deserving winner."""

_CJMH_MECHANISM_BLOCK = """A SINGLE CONSISTENT REGISTER, not the four-device rotation: elegant excess paired \
with precise, absurd comparison (Clive James) and deadpan, savage overstatement landing \
on bathos (Marina Hyde). Commit to this one register throughout the whole report — do \
not switch devices paragraph to paragraph. The comic density and clarity requirements \
above still apply in full."""


SELECTIVITY_NOTE = """SELECTIVITY — this variant layers three additional devices (overstatement \
discipline, emotional interiority, and raised cruelty on weak performances) on top of the base \
register below. NONE of the three is mandatory in any given passage, and none should appear in \
every paragraph or every storyline. Reach for a device only where the specific moment earns it — a \
drought broken, a career round, a genuine collapse, a performance that really was poor — and let \
most of the report sit in the plain base register otherwise. A report that hams, ups the emotional \
volume, or turns cruel on every passage reads as try-hard and breaks the "never zany" rule; the \
discipline is knowing when NOT to reach for these, as much as knowing how to land them when you do."""


def _cjmh_voice() -> str:
    """VOICE_CORE with its four-writer rotation section replaced by a single CJ/MH
    register; everything else in WRITER_VOICE (comic aim, named principles) stands."""
    core = prompts.VOICE_CORE
    start = core.index("HUMOUR MECHANISMS")
    end = core.index("CLARITY, non-negotiable")
    replaced_core = core[:start] + _CJMH_MECHANISM_BLOCK + "\n\n" + core[end:]
    return "\n".join((replaced_core, _WRITER_COMIC_AIM, prompts.NAMED_PRINCIPLES))


VARIANTS: Dict[str, str] = {
    "baseline": WRITER_VOICE,
    "overstatement": WRITER_VOICE + "\n\n" + OVERSTATEMENT_DELIVERY,
    "interiority": WRITER_VOICE + "\n\n" + EMOTIONAL_INTERIORITY,
    "combined": WRITER_VOICE + "\n\n" + OVERSTATEMENT_DELIVERY + "\n\n" + EMOTIONAL_INTERIORITY,
    "crueller": WRITER_VOICE + "\n\n" + CRUELLER_CALIBRATION,
    "cjmh": _cjmh_voice(),
    "kitchen_sink": (_cjmh_voice() + "\n\n" + SELECTIVITY_NOTE + "\n\n" + OVERSTATEMENT_DELIVERY
                     + "\n\n" + EMOTIONAL_INTERIORITY + "\n\n" + CRUELLER_CALIBRATION),
}

ARM_NAMES = list(VARIANTS.keys())


# ---------------------------------------------------------------------------
# Judge — blind, multi-arm, order randomised per TEG.
# ---------------------------------------------------------------------------
class SlotScore(BaseModel):
    slot: str = Field(description="the slot letter this score is for, e.g. 'A'")
    compellingness: int = Field(ge=1, le=10)
    humor_landing: int = Field(ge=1, le=10, description="do the jokes land, or feel overworked/stacked")
    emotional_resonance: int = Field(ge=1, le=10)
    factual_grounding: int = Field(ge=1, le=10, description="every claim traceable to the source draft; "
                                                              "penalise anything invented or over-claimed")
    tone_fit: int = Field(ge=1, le=10, description="matches TEG house style: subverted gravitas, dry, "
                                                    "never zany, never sincere hyperbole taken straight")
    notes: str


class JudgeVerdict(BaseModel):
    scores: List[SlotScore] = Field(description="one entry per slot letter shown above — ALL of them, "
                                                  "e.g. if slots A through F were shown, return 6 entries")
    ranking_best_to_worst: List[str] = Field(description="slot letters, best first")
    overall_notes: str


JUDGE_SYSTEM = """You are comparing several voice/tone treatments of the SAME golf tournament \
report, rewritten from the same plain factual draft by different methods (not told which). \
Score each BLIND against: compellingness, humor_landing (do the jokes land, or read as \
overworked/stacked — a joke with a second flourish tacked onto an already-complete line \
should be marked down here), emotional_resonance, factual_grounding (every claim must trace to \
the source draft; penalise invention or over-claiming), and tone_fit (deadpan, subverted \
gravitas, dry British understatement — never zany, never earnest/sincere hyperbole played \
straight). Then give an overall best-to-worst ranking of the slot letters."""


def run_judge(draft_text: str, texts_by_arm: Dict[str, str], model: Optional[str] = None) -> dict:
    arms = list(texts_by_arm.keys())
    random.shuffle(arms)
    letters = [chr(ord("A") + i) for i in range(len(arms))]
    slot_to_arm = dict(zip(letters, arms))

    sections = "\n\n".join(
        f"--- Draft {letter} ---\n{texts_by_arm[arm]}" for letter, arm in zip(letters, arms)
    )
    user = (f"SOURCE (plain factual draft, for grounding checks only):\n{draft_text}\n\n"
            f"{sections}")
    verdict, _ = llm.generate_structured(JUDGE_SYSTEM, user, JudgeVerdict,
                                         model=model or llm.DEFAULT_MODEL,
                                         stage="voice_tone_experiment_judge", label="judge")
    verdict_dict = verdict.model_dump()
    verdict_dict["scores_by_slot"] = {s["slot"]: s for s in verdict_dict.pop("scores")}
    verdict_dict["slot_to_arm"] = slot_to_arm
    return verdict_dict


# ---------------------------------------------------------------------------
def run_one_teg(teg_num: int, model: Optional[str] = None, judge_only: bool = False,
                force: bool = False) -> dict:
    draft_path = f"{output_dir()}/teg_{teg_num}_report_storylinedraft.md"
    with open(draft_path) as f:
        draft_text = f.read()

    texts_by_arm = {}
    for arm, voice_prompt in VARIANTS.items():
        label = f"voicetest_{arm}"
        arm_path = f"{output_dir()}/teg_{teg_num}_report_{label}.md"
        import os
        exists = os.path.exists(arm_path)
        if judge_only and not exists:
            raise FileNotFoundError(f"--judge-only but {arm_path} does not exist")
        if not force and exists:
            print(f"[voice_tone_experiment] TEG {teg_num}: reusing arm {arm!r} from disk")
            with open(arm_path) as f:
                texts_by_arm[arm] = f.read()
            continue
        print(f"[voice_tone_experiment] TEG {teg_num}: writing arm {arm!r}...")
        result = restyle_voice(teg_num, voice_prompt, label=label,
                               source_label="storylinedraft", model=model, style=False)
        with open(result["output_path"]) as f:
            texts_by_arm[arm] = f.read()
        if result.get("new_findings"):
            print(f"    new_findings: {result['new_findings']}")

    verdict = run_judge(draft_text, texts_by_arm, model=model)
    slot_to_arm = verdict["slot_to_arm"]
    ranking_arms = [slot_to_arm[s] for s in verdict["ranking_best_to_worst"]]
    print(f"    ranking: {ranking_arms}")

    return {
        "teg": teg_num,
        "slot_to_arm": slot_to_arm,
        "scores_by_slot": verdict["scores_by_slot"],
        "ranking_arms_best_to_worst": ranking_arms,
        "overall_notes": verdict["overall_notes"],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tegs", default="14,16,18", help="comma-separated TEG numbers to test")
    ap.add_argument("--model", default=None)
    ap.add_argument("--judge-only", action="store_true",
                    help="skip regenerating restyles; re-judge existing teg_N_report_voicetest_*.md files")
    args = ap.parse_args()

    if not llm.has_api_key():
        print("No API key found. Aborting.")
        sys.exit(1)

    tegs = [int(t) for t in args.tegs.split(",")]
    results = [run_one_teg(t, model=args.model, judge_only=args.judge_only) for t in tegs]

    out_path = f"{output_dir()}/voice_tone_experiment.json"
    with open(out_path, "w") as f:
        json.dump({"tegs": tegs, "arms": ARM_NAMES, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"[voice_tone_experiment] wrote {out_path}")

    # Tally: average each axis per arm across all TEGs + count of #1 rankings.
    axis_names = ["compellingness", "humor_landing", "emotional_resonance",
                  "factual_grounding", "tone_fit"]
    sums = {arm: {ax: 0.0 for ax in axis_names} for arm in ARM_NAMES}
    counts = {arm: 0 for arm in ARM_NAMES}
    first_place = {arm: 0 for arm in ARM_NAMES}

    for r in results:
        for slot, arm in r["slot_to_arm"].items():
            score = r["scores_by_slot"][slot]
            for ax in axis_names:
                sums[arm][ax] += score[ax]
            counts[arm] += 1
        if r["ranking_arms_best_to_worst"]:
            first_place[r["ranking_arms_best_to_worst"][0]] += 1

    print("\n=== Averages (per axis, across TEGs judged) ===")
    for arm in ARM_NAMES:
        n = counts[arm] or 1
        avgs = {ax: round(sums[arm][ax] / n, 2) for ax in axis_names}
        overall = round(sum(avgs.values()) / len(axis_names), 2)
        print(f"  {arm:15s} overall={overall:5.2f}  {avgs}  (#1 finishes: {first_place[arm]})")


if __name__ == "__main__":
    main()
