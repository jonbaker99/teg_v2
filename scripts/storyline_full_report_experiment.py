"""Generate a full report from the storyline-first method, then apply the
CURRENT production house voice as a final language layer.

Two-stage, mirroring `authoring.restyle_voice`'s own split (structure/facts
first, voice second):

1. **Structural draft** — one section per storyline (trophy_storyline lead,
   then discovered_storylines, then jacket_storyline, spoon_storyline), each
   written fact-isolated (STORYLINE_PLAN.md's validated fix: the writer sees
   only `subject` + raw beat evidence, never the discovery step's own
   why_it_matters/shape prose — 2b's telling call is skipped, per the
   documented 3-TEG verdict that it doesn't earn its cost). Plain, unstyled
   prose — this stage's only job is structure + facts.
2. **Voice pass** — `authoring.restyle_voice` rewrites that draft in the
   CURRENT house voice (`authoring.WRITER_VOICE` — Herron/Ronay/Armstrong/
   Iannucci, em-dash ban, humour6, faithfulness rules), the same function and
   the same voice constant production would use. D3-verified; `new_findings`
   isolates faults the voice pass introduced vs inherited from the draft.

This is still an experiment, not a pipeline change: nothing in `backfill.py`
calls this, and it never touches `report_final`/`report_styled`.

Usage, from the repo root (needs a story plan already generated for --teg, and
ANTHROPIC_API_KEY / TEG_ANTHROPIC_API_KEY):

    python scripts/storyline_full_report_experiment.py --teg 14
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Optional

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from teg_analysis.reporting import llm
from teg_analysis.reporting.authoring import WRITER_VOICE, restyle_voice
from teg_analysis.reporting.paths import output_dir
from teg_analysis.reporting.story_plan import assemble_bundle


def _evidence_for(storyline: dict, all_beats: list) -> list:
    by_id = {b["id"]: b for b in all_beats}
    return [by_id[bid] for bid in storyline["beat_ids"] if bid in by_id]


DRAFT_WRITER_SYSTEM = """You are writing one section of a golf tournament report — a \
single storyline, not the whole report. Plain, clear, factual prose — this is a \
structural draft, not the final voice; do not try to be funny or stylish. 150-250 \
words. `subject` is a label only, NOT a source of facts — do not copy any score, \
margin, comparison, or claim from it unless it also appears in `evidence`. Every \
fact you write must trace to `evidence`. Never invent scores, margins, or \
comparisons not present in your input."""


def draft_section(storyline: dict, evidence: list, model: Optional[str] = None) -> str:
    payload = {"subject": storyline["subject"], "evidence": evidence}
    user = "Write this storyline as a prose section:\n\n" + json.dumps(payload, indent=2, ensure_ascii=False)
    text, usage = llm.generate_text(user=user, system=DRAFT_WRITER_SYSTEM,
                                    model=model or llm.DEFAULT_MODEL,
                                    stage="storyline_full_report", label=storyline["subject"][:30])
    return text.strip()


def build_storyline_draft(teg_num: int, model: Optional[str] = None) -> tuple[str, dict]:
    plan_path = f"{output_dir()}/teg_{teg_num}_story_plan.json"
    with open(plan_path) as f:
        plan = json.load(f)

    bundle, _ = assemble_bundle(teg_num, top_n=None)
    all_beats = bundle["beats"]

    order = ([plan["trophy_storyline"]] + plan["discovered_storylines"]
            + [plan["jacket_storyline"], plan["spoon_storyline"]])

    sections = []
    for s in order:
        print(f"[storyline_full_report] drafting: {s['subject'][:60]}")
        evidence = _evidence_for(s, all_beats)
        text = draft_section(s, evidence, model=model)
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
