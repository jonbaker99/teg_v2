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
   Storylines that independently cite 2+ of the same beats (they're planned
   against the same pool, so this happens without any special-casing) are
   merged into ONE cross-cut section instead of two separate ones — the
   interweaving A/B (STORYLINE_PLAN.md, "Interweaving A/B result",
   2026-08-19, `scripts/storyline_interweave_experiment.py`) measured this as
   a 3/3-TEG win on every judged axis, driven mostly by eliminating the
   duplicate scene-setting two separate sections about the same round
   otherwise both write. Plain, unstyled prose — this stage's only job is
   structure + facts.
2. **Voice pass** — `authoring.restyle_voice` rewrites that draft in the
   CURRENT house voice (`authoring.WRITER_VOICE` — Herron/Ronay/Armstrong/
   Iannucci, em-dash ban, humour6, faithfulness rules), the same function and
   the same voice constant production would use. D3-verified; `new_findings`
   isolates faults the voice pass introduced vs inherited from the draft.

This is still an experiment, not a pipeline change: nothing in `backfill.py`
calls this, and it never touches `report_final`/`report_styled`.

A default run reuses nothing: the storyline plan is generated fresh via
`build_storyline_plan` (there is no load-from-disk path for it), and the draft
and voice passes follow from it, so it overwrites all four artefacts and re-rolls
every subject, headline and score. The beats and bundle underneath are recomputed
from the parquet data by code, not by the model.

`--from` and `--to` bound which stages run, so you never pay for what you are
not testing — mirroring the legacy chain's `load_story_plan`/`load_dry_draft`
restart points. The three stages are plan -> draft -> voice:

    --from plan   (default)  start by regenerating the storyline plan
    --from draft             reuse the plan on disk, redraft the sections
    --from voice             reuse the draft, run the voice pass alone

    --to plan                stop after the plan — one call, no prose
    --to draft               stop after the structural draft (was --no-voice)
    --to voice    (default)  run through to the finished styled report

`--from voice` is the cheap loop and the right way to try a tone change — the
draft is plain, unvoiced prose, so a voice A/B against it compares like with
like, where restyling an already-styled report compounds rather than compares.
`--from draft` is for iterating on the section-drafting prompt, where the plan
is not the variable.

Usage, from the repo root — either provider:

    # Anthropic API, bills per token. --tegs takes 14, 2-18, 8,9,14 or a mix.
    python scripts/storyline_full_report_experiment.py --tegs 14

    # claude.ai plan usage: prompts hand off through `data/llm_mailbox`, and a
    # Claude Code session answers them with the `teg-report-respond` skill.
    TEG_LLM_PROVIDER=agent python scripts/storyline_full_report_experiment.py --tegs 14

    # Re-run the voice pass alone against the existing structural draft.
    python scripts/storyline_full_report_experiment.py --tegs 14 --from voice

    # Redraft the sections against the plan already on disk.
    python scripts/storyline_full_report_experiment.py --tegs 14 --from draft

    # Just decide what the reports are about, across several TEGs.
    python scripts/storyline_full_report_experiment.py --tegs 2-6 --to plan

This script has no `--plan`/`--paste` flags of its own (unlike `backfill.py`);
the env var is the whole mechanism, since `llm.generate_text` /
`llm.generate_structured` dispatch on the provider for every call.
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
from teg_analysis.reporting.authoring import (WRITER_VOICE, _strip_derived_prose,
                                             load_storyline_plan, restyle_voice)
from teg_analysis.reporting.backfill import parse_teg_spec
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


def build_storyline_draft(teg_num: int, model: Optional[str] = None,
                          interweave_sections: bool = False,
                          plan: Optional[dict] = None) -> tuple[str, dict]:
    """Runs Call A only (`build_storyline_plan`) — this prototype never calls
    the legacy full `StoryPlan` (Call B); see story_plan.py's module comment
    above `StorylinePlan` for the split.

    `interweave_sections` merges storylines that share beats into one cross-cut
    section. Off by default — see the comment at the call site below.

    `plan` skips Call A and drafts against a plan you already have — pass
    `authoring.load_storyline_plan(teg)` to redraft against the plan on disk
    without re-rolling it. It must be in `StorylinePlan.model_dump()` shape,
    which is what that loader returns.
    """
    if plan is None:
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

    # Interweaving — OFF by default since 2026-09-05, opt in with --interweave.
    #
    # The A/B still stands on its own terms (STORYLINE_PLAN.md, "Interweaving A/B
    # result", 2026-08-19): interwoven won 3/3 TEGs on every judged axis —
    # compellingness, factual_grounding, clarity, redundancy,
    # reads_as_story_not_list — against always-separate sections. Candidate pairs
    # need no LLM call: storylines already cite overlapping beat_ids independently
    # (planned against the same beat pool), so shared citation IS the candidate
    # signal, and `find_overlapping_pairs` greedily picks the highest-overlap set.
    #
    # What changed is the destination, not the judgement. That A/B scored reports
    # read as one flowing document, where merging two threads into a cross-cut
    # section genuinely reads better. Reports are now presented as a newspaper
    # edition — a lead story plus separate articles in a grid
    # (webapp/report_layout_prototypes/) — and there a merged section is one
    # double-length article carrying two subjects and a ' / '-joined heading that
    # is no longer a headline. Separate storylines are what that layout wants.
    #
    # Kept behind a flag rather than deleted: the mechanism is sound and the
    # evidence is real, so if the presentation changes again this is a flag flip,
    # not a rebuild.
    pairs = interweave.find_overlapping_pairs(order) if interweave_sections else []
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


def run_voice_pass(teg_num: int, model: Optional[str] = None) -> dict:
    """Stage 3 alone: rewrite the frozen structural draft in the house voice.

    Reads `teg_N_report_storylinedraft.md` and writes `teg_N_report_storylinefirst.md`
    (+ `_styled.md`). One LLM call, against whatever draft is already on disk —
    it does not regenerate the plan or the sections. `restyle_voice` raises with
    the available `source_label`s if the draft is missing.
    """
    print("[storyline_full_report] applying house voice (restyle_voice)...")
    result = restyle_voice(teg_num, WRITER_VOICE, label="storylinefirst",
                           source_label="storylinedraft", model=model)
    print(f"[storyline_full_report] wrote voiced report: {result['output_path']}")
    print(f"[storyline_full_report] wrote styled report: {result['styled_path']}")
    print(f"[storyline_full_report] D3 new findings introduced by voice pass: "
          f"{len(result['new_findings'])}")
    for f in result["new_findings"]:
        print(f"  - {f}")
    return result


def run_one(teg_num: int, *, start_from: str = "plan", stop_after: str = "voice",
            model: Optional[str] = None, interweave: bool = False) -> None:
    """Run the stages between `start_from` and `stop_after` for one TEG.

    Split out of `main` so the multi-TEG loop can keep going past a TEG that
    fails — a bad plan on TEG 7 should not discard the six already paid for.
    """
    if start_from == "voice":
        draft_path = f"{output_dir()}/teg_{teg_num}_report_storylinedraft.md"
        print(f"[storyline_full_report] --from voice: reusing {draft_path}, "
              f"regenerating nothing above it.")
        run_voice_pass(teg_num, model=model)
        return

    reused_plan = None
    if start_from == "draft":
        reused_plan = load_storyline_plan(teg_num)
        print(f"[storyline_full_report] --from draft: reusing "
              f"{output_dir()}/teg_{teg_num}_storyline_plan.json "
              f"({1 + len(reused_plan['discovered_storylines']) + 2} storylines), "
              f"redrafting sections.")

    if stop_after == "plan":
        # Stop at the editorial decision: what is this report about? One LLM
        # call, before anything is spent on prose.
        result = build_storyline_plan(teg_num, model=model)
        plan = result["plan"].model_dump()
        print(f"[storyline_full_report] wrote storyline plan: {result['output_path']}")
        for s in ([plan["trophy_storyline"]] + plan["discovered_storylines"]
                  + [plan["jacket_storyline"], plan["spoon_storyline"]]):
            print(f"  [{s.get('chosen_headline') or s['subject'][:60]}] "
                  f"compelling={s.get('compelling_score')} humour={s.get('humour_score')}")
        return

    draft_text, plan = build_storyline_draft(teg_num, model=model,
                                             interweave_sections=interweave,
                                             plan=reused_plan)
    draft_path = f"{output_dir()}/teg_{teg_num}_report_storylinedraft.md"
    with open(draft_path, "w") as f:
        f.write(draft_text)
    print(f"[storyline_full_report] wrote structural draft: {draft_path} "
          f"({len(draft_text.split())} words)")

    if stop_after == "draft":
        print("[storyline_full_report] --to draft: stopping before the voice pass.")
        return

    run_voice_pass(teg_num, model=model)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tegs", required=True,
                    help="Which TEGs: 14, 2-18, 8,9,14, or a mix. Parsed by "
                         "`backfill.parse_teg_spec`, the same syntax backfill takes. "
                         "Runs them in order and keeps going if one fails.")
    ap.add_argument("--model", default=None)
    ap.add_argument("--from", dest="start_from", choices=("plan", "draft", "voice"),
                    default="plan",
                    help="Which stage to start from, reusing everything above it. "
                         "'plan' (default) runs the lot: storyline plan, one draft call "
                         "per storyline, then the voice pass. 'draft' reuses the plan on "
                         "disk and redrafts the sections — for iterating on the drafting "
                         "prompt, where the plan is not what you are testing. 'voice' "
                         "reuses the structural draft and re-runs the voice pass alone: "
                         "one LLM call, and the right way to try a tone change.")
    ap.add_argument("--to", dest="stop_after", choices=("plan", "draft", "voice"),
                    default="voice",
                    help="Which stage to stop after. 'voice' (default) runs to the "
                         "finished styled report. 'draft' stops at the structural "
                         "draft. 'plan' stops at the storyline plan — one LLM call, "
                         "for deciding what the report is about before spending "
                         "anything on prose.")
    ap.add_argument("--no-voice", action="store_true",
                    help="Deprecated alias for --to draft. Kept because it appears in "
                         "existing notes and docs.")
    ap.add_argument("--interweave", action="store_true",
                    help="Merge storylines that share beats into one cross-cut section. "
                         "Off by default: the newspaper layout wants separate articles.")
    args = ap.parse_args()

    if args.no_voice:
        if args.stop_after != "voice":
            ap.error("--no-voice is a deprecated alias for --to draft; don't pass both.")
        args.stop_after = "draft"

    # Reject combinations that ask for nothing to happen, or for a flag that only
    # applies to a stage this run skips, rather than running and silently
    # ignoring half the command line.
    _ORDER = {"plan": 0, "draft": 1, "voice": 2}
    if _ORDER[args.stop_after] < _ORDER[args.start_from]:
        ap.error(f"--to {args.stop_after} is before --from {args.start_from}: "
                 f"that range has no stages in it.")
    if args.start_from == "voice" and args.interweave:
        ap.error("--interweave affects section drafting, which --from voice skips. "
                 "Re-run from plan or draft to redraft.")
    if args.stop_after == "plan" and args.interweave:
        ap.error("--interweave affects section drafting, which --to plan stops before.")

    # Only the `api` provider needs a key — under `agent` the prompts hand off
    # through the mailbox and there is no key at all (see `llm.has_api_key`).
    # Guarding unconditionally used to abort a perfectly valid
    # `TEG_LLM_PROVIDER=agent` run before it made a single call.
    if llm.get_provider() == llm.PROVIDER_API and not llm.has_api_key():
        print(f"No API key found, and the provider is {llm.PROVIDER_API}. "
              f"Set one, or run on plan usage with {llm.ENV_PROVIDER}={llm.PROVIDER_AGENT}.")
        sys.exit(1)

    tegs = parse_teg_spec(args.tegs)
    if len(tegs) > 1:
        print(f"[storyline_full_report] {len(tegs)} TEGs: {tegs} "
              f"(--from {args.start_from} --to {args.stop_after})")

    failed = []
    for teg in tegs:
        if len(tegs) > 1:
            print(f"\n{'=' * 70}\n[storyline_full_report] TEG {teg}\n{'=' * 70}")
        try:
            run_one(teg, start_from=args.start_from, stop_after=args.stop_after,
                    model=args.model, interweave=args.interweave)
        except Exception as e:
            # One bad TEG should not throw away the ones already paid for.
            failed.append((teg, e))
            print(f"[storyline_full_report] TEG {teg} FAILED: {type(e).__name__}: {e}")

    if failed:
        print(f"\n[storyline_full_report] {len(failed)} of {len(tegs)} failed:")
        for teg, e in failed:
            print(f"  TEG {teg}: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
