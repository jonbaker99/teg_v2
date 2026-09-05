"""Writer-richness A/B — does giving the storyline-first writer read-only,
structured (non-prose) context improve richness without reintroducing the
fabrication risk the 2b experiment found?

Background (STORYLINE_PLAN.md, "Call A / Call B split, and the writer-richness
gap", 2026-08-19): the LEGACY writer (`authoring.py`) re-injects raw bundle
context (`venue`, `player_history`, `player_course_history`) into the prose
prompt via `BUNDLE_CONTEXT_KEYS`/`bundle_context_text(style="data")`. The
storyline-first writer (`draft_section()` in
`scripts/storyline_full_report_experiment.py`) gets none of that — only the
beats a storyline's `beat_ids` cite. Deliberate (2b found that a SECOND
UNVERIFIED PROSE channel — an editor's own why_it_matters/shape summary —
caused fabrication when handed alongside evidence), but this is a different
kind of context: raw structured data (numbers/names/dates), not another LLM's
free-text summary. Untested whether the same risk applies.

For each storyline in an already-generated `StorylinePlan`
(`teg_{n}_storyline_plan.json`):

1. **without_context** — the current production behaviour: `subject` +
   `evidence` (the storyline's own cited beats) only.
2. **with_context**    — the same, plus `context`: `venue` +
   `player_history`/`player_course_history` SCOPED to the players in this
   storyline's evidence, stripped of derived prose (numbers/names only,
   mirroring `authoring._strip_derived_prose`) so nothing arrives as a
   ready-made sentence to lift.

A blind judge (order randomised per storyline) scores each pair on
compellingness, factual_grounding, richness (genuine colour beyond the bare
evidence — not padding), and reads_as_story_not_list.

Usage, from the repo root (needs a StorylinePlan already generated for --teg
via `build_storyline_plan`, and ANTHROPIC_API_KEY / TEG_ANTHROPIC_API_KEY):

    python scripts/storyline_context_experiment.py --teg 14

Cost: ~2 writer calls + 1 judge call per storyline — for the default 5
storylines (3 mandatory + 2 discovered), ~15 calls.
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


def _evidence_for(storyline: dict, all_beats: list) -> list:
    by_id = {b["id"]: b for b in all_beats}
    return [by_id[bid] for bid in storyline["beat_ids"] if bid in by_id]


def _context_for(storyline_players: set, bundle: dict) -> dict:
    """Structured, numbers-only context scoped to this storyline's own
    players — NOT the whole tournament. Scoping (rather than reusing
    `authoring._bundle_context_text` verbatim, which sends every player)
    keeps the writer's attention on the players actually in this section,
    the same reasoning that keeps `evidence` scoped to cited beat_ids.
    """
    ctx = {
        "venue": bundle.get("venue"),
        "player_history": {p: h for p, h in (bundle.get("player_history") or {}).items()
                           if p in storyline_players},
        "player_course_history": {p: h for p, h in (bundle.get("player_course_history") or {}).items()
                                  if p in storyline_players},
    }
    return _strip_derived_prose(ctx)


# ---------------------------------------------------------------------------
# Writer — same prompt shape for both arms; the test arm gets an extra
# `context` key and one extra paragraph of instruction.
# ---------------------------------------------------------------------------
WRITER_SYSTEM_BASE = """You are writing one section of a golf tournament report — a \
single storyline, not the whole report. Plain, clear, factual prose — this is a \
structural draft, not the final voice; do not try to be funny or stylish. 150-250 \
words. `subject` is a label only, NOT a source of facts — do not copy any score, \
margin, comparison, or claim from it unless it also appears in `evidence`. Every \
fact you write must trace to `evidence`{context_clause}. Never invent scores, \
margins, or comparisons not present in your input."""

CONTEXT_CLAUSE = (" or `context`. `context` is RAW DATA — venue character and "
                  "per-player career/course history, numbers and names only, no "
                  "summary sentences. You may draw on it for colour (a player's "
                  "history on this course, a career milestone) but any comparison "
                  "you state must follow exactly from its figures; if the "
                  "arithmetic is not clean, leave it out. Do not let it crowd out "
                  "`evidence` — this storyline's own beats are still the spine")

WRITER_SYSTEM_WITHOUT = WRITER_SYSTEM_BASE.format(context_clause="")
WRITER_SYSTEM_WITH = WRITER_SYSTEM_BASE.format(context_clause=CONTEXT_CLAUSE)


def run_writer(storyline: dict, evidence: list, context: Optional[dict],
               model: Optional[str] = None) -> str:
    payload = {"subject": storyline["subject"], "evidence": evidence}
    system = WRITER_SYSTEM_WITHOUT
    if context is not None:
        payload["context"] = context
        system = WRITER_SYSTEM_WITH
    user = "Write this storyline as a prose section:\n\n" + json.dumps(payload, indent=2, ensure_ascii=False)
    text, usage = llm.generate_text(user=user, system=system,
                                    model=model or llm.DEFAULT_MODEL,
                                    stage="context_experiment_writer",
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
    factual_grounding: ABScore = Field(description="check against the evidence AND context provided")
    richness: ABScore = Field(description="genuine colour beyond the bare evidence (career/course "
                                          "history, texture) — NOT padding or filler")
    reads_as_story_not_list: ABScore
    notes: str


JUDGE_SYSTEM = """You are comparing two prose drafts of the same golf storyline, \
written by different methods (not told which). One method had access to extra \
structured context (career history, course history, venue detail); the other did \
not. Score BLIND against: compellingness, factual_grounding (check every claim \
against the raw evidence AND context provided — penalise anything not supported, \
including any claim that reads as a real fact but isn't backed by either), richness \
(does it draw in genuine colour beyond the bare scorecard evidence, or does it read \
thinner — reward real texture, not verbosity for its own sake), and \
reads_as_story_not_list. Pick an overall winner, or 'tie' if genuinely close."""


def run_judge(storyline: dict, evidence: list, context: Optional[dict],
             text_a: str, text_b: str, model: Optional[str] = None) -> dict:
    user = (f"Storyline: {storyline['subject']}\n\nRaw evidence:\n"
           + json.dumps(evidence, indent=2, ensure_ascii=False)
           + "\n\nAvailable context (may or may not have been used by either draft):\n"
           + json.dumps(context, indent=2, ensure_ascii=False)
           + f"\n\n--- Draft A ---\n{text_a}\n\n--- Draft B ---\n{text_b}")
    verdict, usage = llm.generate_structured(JUDGE_SYSTEM, user, PairScore,
                                             model=model or llm.DEFAULT_MODEL,
                                             stage="context_experiment_judge",
                                             label=storyline["subject"][:30])
    return verdict.model_dump()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--teg", type=int, required=True)
    ap.add_argument("--max-discovered", type=int, default=3)
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    if not llm.has_api_key():
        print("No API key found. Aborting.")
        sys.exit(1)

    plan_path = f"{output_dir()}/teg_{args.teg}_storyline_plan.json"
    with open(plan_path) as f:
        plan = json.load(f)

    bundle, _ = assemble_bundle(args.teg, top_n=None)
    all_beats = bundle["beats"]

    storylines = ([plan["trophy_storyline"], plan["jacket_storyline"], plan["spoon_storyline"]]
                 + plan["discovered_storylines"][:args.max_discovered])

    results = []
    for s in storylines:
        print(f"[context_experiment] TEG {args.teg}: {s['subject'][:60]}")
        evidence = _evidence_for(s, all_beats)
        storyline_players = {p for b in evidence for p in b.get("players", [])}
        context = _context_for(storyline_players, bundle)

        text_without = run_writer(s, evidence, None, model=args.model)
        text_with = run_writer(s, evidence, context, model=args.model)

        if random.random() < 0.5:
            label_map = {"A": "with_context", "B": "without_context"}
            text_a, text_b = text_with, text_without
        else:
            label_map = {"A": "without_context", "B": "with_context"}
            text_a, text_b = text_without, text_with

        verdict = run_judge(s, evidence, context, text_a, text_b, model=args.model)
        winner_arm = label_map.get(verdict["winner"], "tie")

        results.append({
            "subject": s["subject"], "context": context,
            "text_with_context": text_with, "text_without_context": text_without,
            "label_map": label_map, "verdict": verdict, "winner_arm": winner_arm,
        })
        print(f"    winner: {winner_arm}")

    out_path = f"{output_dir()}/context_experiment_teg_{args.teg}.json"
    with open(out_path, "w") as f:
        json.dump({"teg": args.teg, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"[context_experiment] wrote {out_path}")

    tally = {}
    for r in results:
        tally[r["winner_arm"]] = tally.get(r["winner_arm"], 0) + 1
    print("\n=== Tally ===")
    for arm, n in tally.items():
        print(f"  {arm}: {n}")


if __name__ == "__main__":
    main()
