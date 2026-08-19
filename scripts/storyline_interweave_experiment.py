"""Interweaving A/B — should two storylines that share a scene ever be told as
ONE cross-cut section, instead of the current strict one-storyline-per-section
layout?

Background (STORYLINE_PLAN.md, "Full-report proof + user's 3-point punch
list", point 3): flagged by Jon as worth trying, deferred to its own
fresh-context chat because it's a narrative-ordering question, not a
fact-grounding or discovery one — the risk is losing the fact-isolation
guarantee that's been load-bearing for grounding throughout this workstream
(an interwoven writer needs evidence from BOTH storylines at once).

**Candidate selection is deterministic, not LLM-judged.** Beat citation
already overlaps across storylines in real plan output — the same round-3
collapse beats get cited independently by e.g. a Jacket-race storyline AND a
Wooden-Spoon storyline, because nothing dedupes citations across storylines
(each is planned independently against the full beat pool). That overlap
*is* the candidate signal: no new clustering code, just count shared
beat_ids between every storyline pair in an already-generated
`StorylinePlan` and pick the pair with the most overlap, excluding near-
identical pairs (>60% of the smaller set) since a pair that similar is one
storyline's content leaking into another's citations, not two independent
threads sharing a scene.

Two arms per candidate pair:

1. **separate** (current production) — each storyline drafted independently
   via the same fact-isolated writer as `storyline_full_report_experiment.py`
   (`subject` + own `evidence` + own scoped `context`), concatenated with a
   `##` heading each, same as the real pipeline output.
2. **interwoven** — ONE writer call, given BOTH storylines' `subject`s and
   evidence side by side (each beat still tagged with which storyline it
   belongs to) plus the union of their scoped context, instructed to cut
   between the two threads by round/moment rather than resolving one fully
   before starting the other. Still fact-isolated in the sense that matters:
   the writer sees only these two storylines' own cited beats, never the
   whole bundle — the isolation boundary just moves from "one storyline" to
   "this pair," it doesn't disappear.

A blind judge (order randomised) scores compellingness, factual_grounding,
clarity (can the reader tell which fact belongs to which player — the risk
specific to interweaving that the other A/Bs in this workstream didn't need
to test), redundancy (does interweaving avoid restating shared scene-setting
twice, e.g. "Round 3 at Penha Longa" once instead of twice), and
reads_as_story_not_list.

Usage, from the repo root (needs an already-generated `StorylinePlan` for
--teg via `build_storyline_plan`, and ANTHROPIC_API_KEY /
TEG_ANTHROPIC_API_KEY):

    python scripts/storyline_interweave_experiment.py --teg 14

Cost: 1 pair per TEG (skips TEGs with no qualifying overlap) — 2 writer
calls (1 for each of 2 sections in the separate arm, 1 for interwoven — so 3
writer calls) + 1 judge call per TEG tested.
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
from teg_analysis.reporting.authoring import _strip_derived_prose
from teg_analysis.reporting.paths import output_dir
from teg_analysis.reporting.story_plan import assemble_bundle

MIN_OVERLAP = 2       # need >=2 shared beats to count as "sharing a scene"
MAX_OVERLAP_RATIO = 0.6  # >60% of the smaller set = same content, not a pair


def _evidence_for(storyline: dict, all_beats: list) -> list:
    by_id = {b["id"]: b for b in all_beats}
    return [by_id[bid] for bid in storyline["beat_ids"] if bid in by_id]


def _context_for(storyline_players: set, bundle: dict) -> dict:
    ctx = {
        "venue": bundle.get("venue"),
        "player_history": {p: h for p, h in (bundle.get("player_history") or {}).items()
                           if p in storyline_players},
        "player_course_history": {p: h for p, h in (bundle.get("player_course_history") or {}).items()
                                  if p in storyline_players},
    }
    return _strip_derived_prose(ctx)


def find_overlapping_pairs(stories: list) -> list[tuple]:
    """Deterministic candidate selection — see module docstring. Greedily picks
    non-overlapping pairs (by list index) with the most shared beat_ids,
    clearing MIN_OVERLAP and under MAX_OVERLAP_RATIO. Returns a list of
    (story_a, story_b, index_a, index_b) tuples, index_a < index_b, sorted by
    index_a — the caller uses index_a as the pair's position in the section
    order. A story index appears in at most one pair; leftover stories are
    the caller's job to draft singly."""
    candidates = []
    for i in range(len(stories)):
        for j in range(i + 1, len(stories)):
            a, b = stories[i], stories[j]
            set_a, set_b = set(a["beat_ids"]), set(b["beat_ids"])
            shared = set_a & set_b
            smaller = min(len(set_a), len(set_b))
            if not smaller or len(shared) / smaller > MAX_OVERLAP_RATIO:
                continue
            if len(shared) >= MIN_OVERLAP:
                candidates.append((len(shared), i, j))
    candidates.sort(key=lambda c: -c[0])

    used, pairs = set(), []
    for _, i, j in candidates:
        if i in used or j in used:
            continue
        used.add(i)
        used.add(j)
        pairs.append((stories[i], stories[j], i, j))
    pairs.sort(key=lambda p: p[2])
    return pairs


def pick_overlapping_pair(plan: dict) -> Optional[tuple]:
    """Single-pair convenience wrapper used by this script's own A/B run —
    see `find_overlapping_pairs` for the general (multi-pair) version used by
    the production pipeline."""
    stories = ([plan["trophy_storyline"], plan["jacket_storyline"], plan["spoon_storyline"]]
              + plan["discovered_storylines"])
    pairs = find_overlapping_pairs(stories)
    if not pairs:
        return None
    a, b, _, _ = pairs[0]
    return (a, b)


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------
SEPARATE_WRITER_SYSTEM = """You are writing one section of a golf tournament report — a \
single storyline, not the whole report. Plain, clear, factual prose — this is a \
structural draft, not the final voice; do not try to be funny or stylish. 150-250 \
words. `subject` is a label only, NOT a source of facts — do not copy any score, \
margin, comparison, or claim from it unless it also appears in `evidence` or \
`context`. Every fact you write must trace to `evidence` or `context`. Never invent \
scores, margins, or comparisons not present in your input."""

INTERWOVEN_WRITER_SYSTEM = """You are writing ONE section of a golf tournament report \
that cuts between TWO storylines sharing a scene — plain, clear, factual prose, not \
the final voice; do not try to be funny or stylish. 250-400 words. You are given \
`storyline_a` and `storyline_b`, each with its own `subject` (a label only, not a \
source of facts) and own `evidence`, plus shared `context`. Cut between the two \
threads by round or moment — do not fully resolve one storyline before starting the \
other; the point of this section is showing them unfold in parallel. Never attribute \
a fact from storyline_a's evidence to a player in storyline_b or vice versa. Only \
state a connection between the two threads (shared round, same course, same hole) \
when both storylines' evidence actually places them there — do not invent causality \
or thematic linkage beyond what the evidence supports. Every fact must trace to its \
own storyline's evidence or to `context`."""


def draft_separate(storyline: dict, evidence: list, context: dict, model: Optional[str] = None) -> str:
    payload = {"subject": storyline["subject"], "evidence": evidence, "context": context}
    user = "Write this storyline as a prose section:\n\n" + json.dumps(payload, indent=2, ensure_ascii=False)
    text, _ = llm.generate_text(user=user, system=SEPARATE_WRITER_SYSTEM,
                                model=model or llm.DEFAULT_MODEL,
                                stage="interweave_experiment_separate", label=storyline["subject"][:30])
    return text.strip()


def draft_interwoven(a: dict, evidence_a: list, b: dict, evidence_b: list,
                     context: dict, model: Optional[str] = None) -> str:
    payload = {
        "storyline_a": {"subject": a["subject"], "evidence": evidence_a},
        "storyline_b": {"subject": b["subject"], "evidence": evidence_b},
        "context": context,
    }
    user = "Write this cross-cut section:\n\n" + json.dumps(payload, indent=2, ensure_ascii=False)
    text, _ = llm.generate_text(user=user, system=INTERWOVEN_WRITER_SYSTEM,
                                model=model or llm.DEFAULT_MODEL,
                                stage="interweave_experiment_interwoven",
                                label=f"{a['subject'][:15]}+{b['subject'][:15]}")
    return text.strip()


# ---------------------------------------------------------------------------
# Judge — blind, order randomised.
# ---------------------------------------------------------------------------
class ABScore(BaseModel):
    A: int = Field(ge=1, le=10)
    B: int = Field(ge=1, le=10)


class PairScore(BaseModel):
    winner: str = Field(description="'A', 'B', or 'tie'")
    compellingness: ABScore
    factual_grounding: ABScore = Field(description="check against the evidence AND context provided")
    clarity: ABScore = Field(description="can the reader always tell which fact belongs to which "
                                         "player/storyline — penalise any confusion or blurred attribution")
    redundancy: ABScore = Field(description="higher score = LESS wasted repetition of shared scene-setting "
                                            "(e.g. restating the same round/course twice)")
    reads_as_story_not_list: ABScore
    notes: str


JUDGE_SYSTEM = """You are comparing two prose treatments of the same pair of golf \
storylines that share a scene, written by different methods (not told which). One \
method told them as two separate sections; the other cross-cut them into one. Score \
BLIND against: compellingness, factual_grounding (check every claim against the raw \
evidence AND context provided for BOTH storylines — penalise anything not supported, \
including any claim that attributes one storyline's fact to the other's subject), \
clarity (can you always tell which fact belongs to which player without re-reading), \
redundancy (higher = less wasted repetition of shared scene-setting), and \
reads_as_story_not_list. Pick an overall winner, or 'tie' if genuinely close."""


def run_judge(a: dict, b: dict, evidence_a: list, evidence_b: list, context: dict,
             text_a: str, text_b: str, model: Optional[str] = None) -> dict:
    user = (f"Storyline A: {a['subject']}\nStoryline B: {b['subject']}\n\n"
           f"Evidence for storyline A:\n{json.dumps(evidence_a, indent=2, ensure_ascii=False)}\n\n"
           f"Evidence for storyline B:\n{json.dumps(evidence_b, indent=2, ensure_ascii=False)}\n\n"
           f"Shared context:\n{json.dumps(context, indent=2, ensure_ascii=False)}\n\n"
           f"--- Draft A ---\n{text_a}\n\n--- Draft B ---\n{text_b}")
    verdict, _ = llm.generate_structured(JUDGE_SYSTEM, user, PairScore,
                                         model=model or llm.DEFAULT_MODEL,
                                         stage="interweave_experiment_judge",
                                         label=f"{a['subject'][:15]}+{b['subject'][:15]}")
    return verdict.model_dump()


def run_one_teg(teg_num: int, model: Optional[str] = None) -> Optional[dict]:
    plan_path = f"{output_dir()}/teg_{teg_num}_storyline_plan.json"
    with open(plan_path) as f:
        plan = json.load(f)

    pair = pick_overlapping_pair(plan)
    if pair is None:
        print(f"[interweave_experiment] TEG {teg_num}: no qualifying overlapping pair, skipping")
        return None
    a, b = pair
    print(f"[interweave_experiment] TEG {teg_num}: pair = {a['subject'][:50]!r} / {b['subject'][:50]!r}")

    bundle, _ = assemble_bundle(teg_num, top_n=None)
    all_beats = bundle["beats"]
    evidence_a, evidence_b = _evidence_for(a, all_beats), _evidence_for(b, all_beats)
    players = {p for beat in evidence_a + evidence_b for p in beat.get("players", [])}
    context = _context_for(players, bundle)

    text_a_sep = draft_separate(a, evidence_a, context, model=model)
    text_b_sep = draft_separate(b, evidence_b, context, model=model)
    text_separate = f"## {a['subject']}\n\n{text_a_sep}\n\n## {b['subject']}\n\n{text_b_sep}"
    text_interwoven = draft_interwoven(a, evidence_a, b, evidence_b, context, model=model)

    if random.random() < 0.5:
        label_map = {"A": "interwoven", "B": "separate"}
        judge_a, judge_b = text_interwoven, text_separate
    else:
        label_map = {"A": "separate", "B": "interwoven"}
        judge_a, judge_b = text_separate, text_interwoven

    verdict = run_judge(a, b, evidence_a, evidence_b, context, judge_a, judge_b, model=model)
    winner_arm = label_map.get(verdict["winner"], "tie")
    print(f"    winner: {winner_arm}")

    return {
        "teg": teg_num, "pair": [a["subject"], b["subject"]],
        "text_separate": text_separate, "text_interwoven": text_interwoven,
        "label_map": label_map, "verdict": verdict, "winner_arm": winner_arm,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tegs", default="14,16,18", help="comma-separated TEG numbers to test")
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    if not llm.has_api_key():
        print("No API key found. Aborting.")
        sys.exit(1)

    tegs = [int(t) for t in args.tegs.split(",")]
    results = [r for r in (run_one_teg(t, model=args.model) for t in tegs) if r]

    out_path = f"{output_dir()}/interweave_experiment.json"
    with open(out_path, "w") as f:
        json.dump({"tegs": tegs, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"[interweave_experiment] wrote {out_path}")

    tally = {}
    for r in results:
        tally[r["winner_arm"]] = tally.get(r["winner_arm"], 0) + 1
    print("\n=== Tally ===")
    for arm, n in tally.items():
        print(f"  {arm}: {n}")


if __name__ == "__main__":
    main()
