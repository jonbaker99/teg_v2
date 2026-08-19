"""Generate a full report from the storyline-first method, then apply the
CURRENT production house voice as a final language layer.

Three-stage, mirroring `authoring.restyle_voice`'s own split (structure/facts
first, voice second) plus the writer-richness fix from the context A/B:

1. **Structural draft** — one section per storyline (trophy_storyline lead,
   then discovered_storylines, then jacket_storyline, spoon_storyline), each
   written fact-isolated (STORYLINE_PLAN.md's validated fix: the writer sees
   only `subject` + raw beat evidence, never the discovery step's own
   why_it_matters/shape prose — 2b's telling call is skipped, per the
   documented 3-TEG verdict that it doesn't earn its cost) PLUS scoped,
   structured `context` (venue + this storyline's own players' career/course
   history, numbers-only) — the writer-richness A/B (STORYLINE_PLAN.md,
   2026-08-19, `scripts/storyline_context_experiment.py`) measured this as a
   clean win on 10/10 storylines across 2 TEGs: richness +2.4, compellingness
   +1.7, reads-as-story +1.4, AND factual_grounding +0.5 (no regression —
   unlike 2b, this is raw structured data, not a competing prose channel).
   Plain, unstyled prose — this stage's only job is structure + facts.
2. **Voice pass** — `authoring.restyle_voice` rewrites that draft in the
   CURRENT house voice (`authoring.WRITER_VOICE` — Herron/Ronay/Armstrong/
   Iannucci, em-dash ban, humour6, faithfulness rules), the same function and
   the same voice constant production would use. D3-verified; `new_findings`
   isolates faults the voice pass introduced vs inherited from the draft.

This is still an experiment, not a pipeline change: nothing in `backfill.py`
calls this, and it never touches `report_final`/`report_styled`.

Usage, from the repo root (needs ANTHROPIC_API_KEY / TEG_ANTHROPIC_API_KEY —
the story plan is generated fresh on each run via `build_storyline_plan`):

    python scripts/storyline_full_report_experiment.py --teg 14
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Optional

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from teg_analysis.reporting import llm
from teg_analysis.reporting.authoring import WRITER_VOICE, _strip_derived_prose, restyle_voice
from teg_analysis.reporting.paths import output_dir
from teg_analysis.reporting.story_plan import assemble_bundle, build_storyline_plan

import storyline_interweave_experiment as interweave


def _evidence_for(storyline: dict, all_beats: list) -> list:
    by_id = {b["id"]: b for b in all_beats}
    return [by_id[bid] for bid in storyline["beat_ids"] if bid in by_id]


def _context_for(storyline_players: set, bundle: dict) -> dict:
    """Structured, numbers-only context scoped to this storyline's own
    players. Validated in `scripts/storyline_context_experiment.py`'s A/B —
    see the module docstring above for the result. Scoping to the storyline's
    own players (rather than the whole tournament) keeps the writer's
    attention on who this section is actually about, same reasoning as
    `evidence` being scoped to the storyline's own cited beat_ids.
    """
    ctx = {
        "venue": bundle.get("venue"),
        "player_history": {p: h for p, h in (bundle.get("player_history") or {}).items()
                           if p in storyline_players},
        "player_course_history": {p: h for p, h in (bundle.get("player_course_history") or {}).items()
                                  if p in storyline_players},
    }
    return _strip_derived_prose(ctx)


def _fallback_sections(plan: dict, all_beats: list) -> list:
    """Deterministic body_fallback sections (2026-08-19): used ONLY when the
    editor set body_fallback != "none" because discovered_storylines came back
    empty or thin. Content is grouped from raw beats, same fact-isolation
    principle as everywhere else in this pipeline — the fallback is a
    structural decision, not a second LLM-authored "shape".
    """
    fallback = plan.get("body_fallback", "none")
    if fallback == "none":
        return []

    spine_players = {plan["trophy_storyline"]["subject"], plan["jacket_storyline"]["subject"],
                     plan["spoon_storyline"]["subject"]}

    if fallback == "player_by_player":
        by_player: dict[str, list] = {}
        for b in all_beats:
            for p in b.get("players", []):
                by_player.setdefault(p, []).append(b)
        sections = []
        for player, beats in sorted(by_player.items(), key=lambda kv: -len(kv[1])):
            if len(beats) < 3 or player in spine_players:
                continue
            sections.append({"subject": f"{player}'s tournament", "beat_ids": [b["id"] for b in beats]})
        return sections

    if fallback == "round_by_round":
        by_round: dict[int, list] = {}
        for b in all_beats:
            if b.get("round"):
                by_round.setdefault(b["round"], []).append(b)
        return [{"subject": f"Round {rnd}", "beat_ids": [b["id"] for b in beats]}
                for rnd, beats in sorted(by_round.items())]

    return []


DRAFT_WRITER_SYSTEM = """You are writing one section of a golf tournament report — a \
single storyline, not the whole report. Plain, clear, factual prose — this is a \
structural draft, not the final voice; do not try to be funny or stylish. 150-250 \
words. `subject` is a label only, NOT a source of facts — do not copy any score, \
margin, comparison, or claim from it unless it also appears in `evidence` or \
`context`. `context` is RAW DATA — venue character and per-player career/course \
history, numbers and names only, no summary sentences. You may draw on it for \
colour (a player's history on this course, a career milestone) but any comparison \
you state must follow exactly from its figures; if the arithmetic is not clean, \
leave it out. Do not let it crowd out `evidence` — this storyline's own beats are \
still the spine. Every fact you write must trace to `evidence` or `context`. Never \
invent scores, margins, or comparisons not present in your input."""


def draft_section(storyline: dict, evidence: list, context: dict, model: Optional[str] = None) -> str:
    payload = {"subject": storyline["subject"], "evidence": evidence, "context": context}
    user = "Write this storyline as a prose section:\n\n" + json.dumps(payload, indent=2, ensure_ascii=False)
    text, usage = llm.generate_text(user=user, system=DRAFT_WRITER_SYSTEM,
                                    model=model or llm.DEFAULT_MODEL,
                                    stage="storyline_full_report", label=storyline["subject"][:30])
    return text.strip()


def build_storyline_draft(teg_num: int, model: Optional[str] = None) -> tuple[str, dict]:
    """Runs Call A only (`build_storyline_plan`) — this prototype never calls
    the legacy full `StoryPlan` (Call B); see story_plan.py's module comment
    above `StorylinePlan` for the split.
    """
    plan_result = build_storyline_plan(teg_num, model=model)
    for w in plan_result["warnings"]:
        print(f"[storyline_full_report] WARNING: {w}")
    plan = plan_result["plan"].model_dump()

    bundle, _ = assemble_bundle(teg_num, top_n=None)
    all_beats = bundle["beats"]

    fallback_sections = _fallback_sections(plan, all_beats)
    if fallback_sections:
        print(f"[storyline_full_report] body_fallback={plan.get('body_fallback')!r}: "
              f"{len(fallback_sections)} fallback section(s)")

    order = ([plan["trophy_storyline"]] + plan["discovered_storylines"] + fallback_sections
            + [plan["jacket_storyline"], plan["spoon_storyline"]])

    # Interweaving A/B (STORYLINE_PLAN.md, "Interweaving A/B result", 2026-08-19):
    # interwoven won 3/3 TEGs on every judged axis (compellingness, factual_grounding,
    # clarity, redundancy, reads_as_story_not_list) against today's always-separate
    # sections. Candidate pairs need no LLM call — storylines already cite overlapping
    # beat_ids independently (planned against the same beat pool), so shared citation
    # IS the candidate signal. Multiple non-overlapping pairs can exist in one plan;
    # `find_overlapping_pairs` greedily picks the highest-overlap set.
    pairs = interweave.find_overlapping_pairs(order)
    merge_at = {i: (a, b) for a, b, i, j in pairs}       # position -> pair to merge in
    skip = {j for _, _, i, j in pairs}                    # position already covered by its pair

    sections = []
    for idx, s in enumerate(order):
        if idx in skip:
            continue
        if idx in merge_at:
            a, b = merge_at[idx]
            print(f"[storyline_full_report] interweaving: {a['subject'][:40]} / {b['subject'][:40]}")
            evidence_a, evidence_b = _evidence_for(a, all_beats), _evidence_for(b, all_beats)
            players = {p for beat in evidence_a + evidence_b for p in beat.get("players", [])}
            context = _context_for(players, bundle)
            text = interweave.draft_interwoven(a, evidence_a, b, evidence_b, context, model=model)
            sections.append(f"## {a['subject']} / {b['subject']}\n\n{text}")
            continue
        print(f"[storyline_full_report] drafting: {s['subject'][:60]}")
        evidence = _evidence_for(s, all_beats)
        storyline_players = {p for b in evidence for p in b.get("players", [])}
        context = _context_for(storyline_players, bundle)
        text = draft_section(s, evidence, context, model=model)
        sections.append(f"## {s['subject']}\n\n{text}")

    body = f"# {plan['title']}\n\n" + "\n\n".join(sections) + "\n"
    return body, plan


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--teg", type=int, required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--no-voice", action="store_true",
                    help="Write only the structural draft; skip the restyle_voice pass.")
    args = ap.parse_args()

    if not llm.has_api_key():
        print("No API key found. Aborting.")
        sys.exit(1)

    draft_text, plan = build_storyline_draft(args.teg, model=args.model)
    draft_path = f"{output_dir()}/teg_{args.teg}_report_storylinedraft.md"
    with open(draft_path, "w") as f:
        f.write(draft_text)
    print(f"[storyline_full_report] wrote structural draft: {draft_path} ({len(draft_text.split())} words)")

    if args.no_voice:
        print("[storyline_full_report] --no-voice: skipping the restyle_voice pass.")
        return

    print("[storyline_full_report] applying house voice (restyle_voice)...")
    result = restyle_voice(args.teg, WRITER_VOICE, label="storylinefirst",
                           source_label="storylinedraft", model=args.model)
    print(f"[storyline_full_report] wrote voiced report: {result['output_path']}")
    print(f"[storyline_full_report] wrote styled report: {result['styled_path']}")
    print(f"[storyline_full_report] D3 new findings introduced by voice pass: {len(result['new_findings'])}")
    for f in result["new_findings"]:
        print(f"  - {f}")


if __name__ == "__main__":
    main()
