"""Stage 4: authoring.

4a — the DRY STORYLINE DRAFT: a faithful, plainly-written account with no colour,
built from the story plan + the beats' hole evidence. Two jobs: a sense-check that
the selection/structure tell the right story before any prose effort, and a scaffold
the entertaining report can be built around. If the story is wrong here, the fault
is upstream (scoring/plan), not the writing.

4b (next) — the entertaining report, with the authoring A/B.
"""

from __future__ import annotations

import json
from typing import Optional, Tuple, Union

from teg_analysis.reporting.story_plan import assemble_bundle, StoryPlan
from teg_analysis.reporting import llm

OUTPUT_DIR = "data/commentary"


DRY_DRAFT_SYSTEM = """You are producing a DRY STORYLINE DRAFT for a report on a TEG \
(an amateur golf tournament of several rounds). This is a faithful, plainly-written \
account with NO colour, NO jokes, NO stylistic flourish. It is a scaffold and a \
fact-check, not the finished article.

You are given: a STORY PLAN (the agreed structure — theme, per-round angles and \
chosen headlines, the three-competition spine, player arcs, must-include and cut \
beats); the BEATS (each with an `id` and hole-by-hole `holes` evidence); the VENUE; \
and the COMPETITION ARCS (leader-by-round, winner/loser trajectory, lead changes, \
decisive moment).

Write the draft in this structure:
1. OVERVIEW — 2-3 factual sentences: who won the Trophy (Stableford), the Green \
Jacket (Gross) and the Wooden Spoon (last on Stableford), with final scores and margins.
2. One section PER ROUND, in order, using the plan's `chosen_headline` as the heading. \
In plain prose, recount what actually happened that round using the plan's `beat_ids`, \
and RENDER SPECIFIC HOLES from the beat evidence — e.g. "a double bogey at the par-4 \
10th and a 10 at the short 17th", never a vague "a back-nine collapse". This hole-level \
specificity is the whole point of the draft.
3. HOW THE COMPETITIONS WERE DECIDED — for the Trophy, then the Green Jacket, then the \
Wooden Spoon: state how each was won (or, for the Spoon, lost) from its competition arc \
— the leader by round, the decisive moment, the final margin.
4. PLAYERS — one factual line per player, from the player arcs.

RULES:
- Use ONLY the supplied facts. Never invent holes, scores, players or events.
- Render real hole detail wherever the evidence supports it.
- Honour the data precisely: where a rival "drew level" rather than taking the lead \
outright (see each lead change's `lead_type` / `outright`), say "drew level", not "took the lead".
- Each round is on a specific course (every beat carries its `course`). The same hole \
NUMBER in different rounds is a DIFFERENT hole on a (usually different) course — never \
treat them as "the same hole".
- Early-round lead changes, when the field is bunched, are routine — state them plainly, \
do not treat the opening exchanges as drama.
- Plain, clear, British English. Short declarative sentences. No similes, no jokes, no \
purple language — that comes in the next pass.
- Markdown headings. Keep it tight."""


def _plan_to_text(plan: Union[StoryPlan, dict]) -> str:
    data = plan.model_dump() if isinstance(plan, StoryPlan) else plan
    return json.dumps(data, indent=2, ensure_ascii=False)


def _build_author_input(plan: Union[StoryPlan, dict], bundle: dict) -> str:
    return (
        "STORY PLAN:\n" + _plan_to_text(plan)
        + "\n\nBEATS (facts + hole evidence; reference by id):\n"
        + json.dumps(bundle["beats"], indent=2, ensure_ascii=False)
        + "\n\nCOMPETITION ARCS:\n"
        + json.dumps(bundle["competition_arcs"], indent=2, ensure_ascii=False)
        + "\n\nVENUE:\n"
        + json.dumps(bundle["venue"], indent=2, ensure_ascii=False)
    )


def generate_dry_draft(teg_num: int, plan: Union[StoryPlan, dict],
                       mode: str = "balanced", tone: str = "house",
                       model: Optional[str] = None) -> dict:
    """4a — produce the faithful, no-colour storyline draft from the plan + evidence."""
    bundle, _ = assemble_bundle(teg_num, mode=mode, tone=tone)
    user = _build_author_input(plan, bundle)
    text, usage = llm.generate_text(DRY_DRAFT_SYSTEM, user,
                                    model=model or llm.DEFAULT_MODEL, max_tokens=8000)
    out_path = f"{OUTPUT_DIR}/teg_{teg_num}_dry_draft.md"
    with open(out_path, "w") as f:
        f.write(text)
    return {"text": text, "usage": usage, "output_path": out_path}


# ===========================================================================
# 4b — the entertaining report (authoring A/B) + repetition lint
# ===========================================================================
WRITER_SYSTEM = """You are a golf writer producing the finished, entertaining report \
on a TEG (an amateur golf tournament of several rounds), for an audience of THE \
PLAYERS THEMSELVES — insiders who know each other, the courses and the history, who \
want to relive the event and be gently ribbed, and who will instantly spot any \
factual error.

VOICE: faithful, entertaining, tongue-in-cheek — in the spirit of Barney Ronay \
(Guardian) and Tom Peck (Times political sketches). Witty, characterful, a clear \
point of view; but anchored in the facts and never zany or over the top. British English.

STRUCTURE — follow the STORY PLAN you are given:
- Open with the title and a punchy overview that lands the theme.
- A section per round, using the plan's chosen headline; carry the theme through and \
pay off the foreshadowing hooks.
- The report is built around the THREE COMPETITIONS in priority order — the Trophy \
(Stableford) first, then the Green Jacket (Gross), then the Wooden Spoon — and you must \
make clear HOW each was won (or, for the Spoon, lost).
- Weave in the venue/course colour and the player arcs where they earn their place.

CRAFT:
- Render SPECIFIC holes ("a double at the par-4 10th, a 10 at the short 17th"), not vague \
abstractions — the detail is what makes it sing.
- VARY your language. Never lean on the same dramatic word twice — do not repeat \
"disaster", "meltdown", "catastrophe" and the like; reach for fresh, precise phrasing.
- Vary sentence rhythm; let a short sentence land a point.

FAITHFULNESS (non-negotiable):
- Use ONLY the supplied facts. Never invent holes, scores, players or events. If it isn't \
in the data, leave it out.
- Honour the data precisely: where a rival "drew level" rather than taking the lead \
outright, say so — do not inflate it into a lead change.
- Each round is played on a specific course (every beat carries its `course`; see also \
the venue). The same hole NUMBER in different rounds is a DIFFERENT hole, almost always \
on a different course — NEVER call them "the same hole" or invent a "same-hole" \
rhyme/parallel. If you draw a parallel between two holes, make explicit they are \
different holes and name the courses.
- Early-round lead changes, when the field is bunched, are normal — do NOT frame routine \
opening jockeying as "chaos" or high drama. The lead changes that matter are the late ones.
- Net scoring is Stableford points; gross is strokes vs par. Don't conflate them.

Output GitHub-flavoured markdown. No preamble, no sign-off — just the report."""

REVISE_SYSTEM = WRITER_SYSTEM + """

YOU ARE NOW REVISING YOUR OWN FIRST DRAFT. Critique it internally against: faithfulness; \
whether the theme lands and the foreshadowing pays off; anything important buried or \
any filler that should go; repeated words or phrasings; whether each round has a clear \
angle; and whether the three competitions are each clearly resolved. Then output ONLY \
the improved report — tighter, fresher, no repetition — same facts."""

LINT_SYSTEM = """You are a copy-editor making ONE kind of change only: eliminate repeated \
or over-used words and phrasings, replacing them with fresh, precise alternatives so no \
striking word is reused close to itself. Do NOT change any facts, names, numbers, \
structure, or headings, and do not alter meaning or length materially. Return the edited \
markdown only."""


def load_story_plan(teg_num: int) -> dict:
    with open(f"{OUTPUT_DIR}/teg_{teg_num}_story_plan.json") as f:
        return json.load(f)


def load_dry_draft(teg_num: int) -> str:
    with open(f"{OUTPUT_DIR}/teg_{teg_num}_dry_draft.md") as f:
        return f.read()


def _write(teg_num: int, label: str, text: str) -> str:
    path = f"{OUTPUT_DIR}/teg_{teg_num}_report_{label}.md"
    with open(path, "w") as f:
        f.write(text)
    return path


def report_single_pass(teg_num: int, plan: Union[StoryPlan, dict],
                       mode: str = "balanced", tone: str = "house",
                       model: Optional[str] = None) -> dict:
    """Approach B: write the entertaining report fresh from the plan + evidence."""
    bundle, _ = assemble_bundle(teg_num, mode=mode, tone=tone)
    user = _build_author_input(plan, bundle) + "\n\nWrite the finished report now."
    text, usage = llm.generate_text(WRITER_SYSTEM, user,
                                    model=model or llm.DEFAULT_MODEL, max_tokens=10000)
    return {"text": text, "usage": usage, "output_path": _write(teg_num, "B_single_pass", text)}


def report_around_draft(teg_num: int, plan: Union[StoryPlan, dict], dry_text: str,
                        model: Optional[str] = None) -> dict:
    """Approach A: build the entertaining report around the dry factual draft."""
    user = ("STORY PLAN:\n" + _plan_to_text(plan)
            + "\n\nDRY FACTUAL DRAFT (accurate — every fact you may use is here or in the "
              "plan; add no others):\n" + dry_text
            + "\n\nRewrite this into the finished, entertaining report. Reshape structure "
              "and wording freely for engagement, but add NO new facts.")
    text, usage = llm.generate_text(WRITER_SYSTEM, user,
                                    model=model or llm.DEFAULT_MODEL, max_tokens=10000)
    return {"text": text, "usage": usage, "output_path": _write(teg_num, "A_around_draft", text)}


def report_critique_revise(teg_num: int, plan: Union[StoryPlan, dict],
                           mode: str = "balanced", tone: str = "house",
                           model: Optional[str] = None) -> dict:
    """Approach C: single-pass draft, then a self-critique-and-revise pass."""
    bundle, _ = assemble_bundle(teg_num, mode=mode, tone=tone)
    draft_user = _build_author_input(plan, bundle) + "\n\nWrite the finished report now."
    draft, u1 = llm.generate_text(WRITER_SYSTEM, draft_user,
                                  model=model or llm.DEFAULT_MODEL, max_tokens=10000)
    revise_user = ("STORY PLAN:\n" + _plan_to_text(plan)
                   + "\n\nYOUR FIRST DRAFT:\n" + draft
                   + "\n\nRevise it per your instructions. Output only the improved report.")
    final, u2 = llm.generate_text(REVISE_SYSTEM, revise_user,
                                  model=model or llm.DEFAULT_MODEL, max_tokens=10000)
    return {"text": final, "draft": draft, "usage": (u1, u2),
            "output_path": _write(teg_num, "C_critique_revise", final)}


def repetition_lint(text: str, model: Optional[str] = None) -> Tuple[str, object]:
    """Narrow final pass: kill repeated/over-used words only. Returns (text, usage)."""
    return llm.generate_text(LINT_SYSTEM, text, model=model or llm.DEFAULT_MODEL, max_tokens=10000)


def run_authoring_ab(teg_num: int, mode: str = "balanced", tone: str = "house",
                     model: Optional[str] = None) -> dict:
    """Generate all three authoring approaches for comparison, reusing the saved
    story plan + dry draft (no extra plan/draft calls)."""
    plan = load_story_plan(teg_num)
    dry_text = load_dry_draft(teg_num)
    a = report_around_draft(teg_num, plan, dry_text, model=model)
    b = report_single_pass(teg_num, plan, mode=mode, tone=tone, model=model)
    c = report_critique_revise(teg_num, plan, mode=mode, tone=tone, model=model)
    return {"A_around_draft": a["output_path"],
            "B_single_pass": b["output_path"],
            "C_critique_revise": c["output_path"]}
