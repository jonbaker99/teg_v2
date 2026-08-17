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
from collections import Counter
from typing import Optional, Tuple, Union

from teg_analysis.reporting.story_plan import assemble_bundle, StoryPlan
from teg_analysis.reporting import llm, prompts

from teg_analysis.reporting.paths import output_dir


DRY_DRAFT_SYSTEM_DETAILED = """You are producing a DRY STORYLINE DRAFT for a report on a TEG \
(an amateur golf tournament of several rounds). This is a faithful, flat, \
checklist-style fact dump with NO colour, NO jokes, NO narrative hooks, NO \
characterisation, NO stylistic flourish. It is a scaffold and a fact-check, not \
the finished article. If you find yourself reaching for a compelling phrase, that \
phrase belongs in the writer's next pass — leave it out here.

You are given: a STORY PLAN (the agreed structure — theme, per-round angles and \
chosen headlines, the three-competition spine, player arcs, must-include and cut \
beats); the BEATS (each with an `id` and hole-by-hole `holes` evidence); the VENUE; \
and the COMPETITION ARCS (leader-by-round, winner/loser trajectory, lead changes, \
decisive moment).

Write the draft in this structure:
1. OVERVIEW — 2-3 factual sentences: who won the Trophy (Stableford for TEG 8+; \
net-vs-par for TEGs 1–7 — lower is better, signed like +47; see `trophy_metric` \
in the bundle), the Green Jacket (Gross) and the Wooden Spoon (last on the Trophy \
metric), with final scores and margins.
2. One section PER ROUND, in order, using the plan's `chosen_headline` as the heading. \
In plain prose, recount what actually happened that round using the plan's `beat_ids`, \
and RENDER SPECIFIC HOLES from the beat evidence — e.g. "a double bogey at the par-4 10th \
and a 10 at the short 17th", never a vague "a back-nine collapse". This hole-level \
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
- **TEG has NO countback, NO tiebreakers, NO playoff.** Lead changes are caused by \
Stableford / Gross point accumulation, full stop. Never write "countback", "tiebreaker", \
"on countback math", or any similar mechanism. Tied scores are tied — say "drew level" or "tied".
- **Arithmetic must be exact.** When you assert an over-par total across a stretch \
(e.g. "X over par through six"), it must equal the precise sum of per-hole over-par \
(bogey = +1, double = +2, triple = +3, quad = +4, quint = +5, sext = +6). Compute, \
do NOT estimate. If the arithmetic is awkward, list the per-hole values and skip the \
running total.
- **Stroke index (SI).** If a hole's evidence includes `si`, you may note it factually \
when it's genuinely interesting: SI 1 = the hardest hole on the course; SI 18 = the \
easiest; SI 2–3 = one of the hardest; SI 16–17 = one of the easiest. SI 4–15: omit. \
One-word note only — "the easiest hole" — no dramatisation.
- **Days and weeks.** A TEG is a tournament of 4 rounds on 4 consecutive days. Do NOT \
call it "a week". Weekday names (Thursday etc.) come from `venue.rounds[i].weekday` \
and are reliable; use them ONLY in round openers, and use the round number for any \
callback across rounds.
- Plain, clear, British English. Short declarative sentences. **No narrative hooks** \
("The day's defining number was..."), **no characterisation** ("the round of his life"), \
**no dramatisation** ("the wheels came off") — that's the writer's job, not the draft's.
- Markdown headings. Keep it tight."""


DRY_DRAFT_SYSTEM_LIGHT = """You are producing a DRY STORYLINE DRAFT for a report on a TEG \
(an amateur golf tournament of several rounds). This is a faithful, flat, \
checklist-style fact dump with NO colour, NO jokes, NO narrative hooks, NO \
characterisation, NO stylistic flourish. It is a scaffold and a fact-check, not \
the finished article. If you find yourself reaching for a compelling phrase, that \
phrase belongs in the writer's next pass — leave it out here.

You are given: a STORY PLAN (the agreed structure — theme, per-round angles and \
chosen headlines, the three-competition spine, player arcs, must-include and cut \
beats); the BEATS (each with an `id` and hole-by-hole `holes` evidence); the VENUE; \
and the COMPETITION ARCS (leader-by-round, winner/loser trajectory, lead changes, \
decisive moment).

Write the draft in this structure:
1. OVERVIEW — 2-3 factual sentences: who won the Trophy (Stableford for TEG 8+; \
net-vs-par for TEGs 1–7 — lower is better, signed like +47; see `trophy_metric` \
in the bundle), the Green Jacket (Gross) and the Wooden Spoon (last on the Trophy \
metric), with final scores and margins.
2. Follow the plan's `narrative_structure` for the body — chronological round-by-round \
by default, but honour `in_medias_res` / `theme_led` / whatever the plan chose. Use the \
plan's per-round `chosen_headline` as section headings where rounds are the units. \
In plain prose, recount only the **key story notes** for each round using the plan's \
`beat_ids` — the must-include beats, the decisive moments, the genuinely notable holes. \
**Do NOT inventory every blow-up or every round's full sequence**; the entertaining pass \
can draw further colour from the beat data when the narrative needs it. Include \
hole-level evidence for the beats that matter — a "10 at the short 17th" is worth \
rendering, a routine bogey usually isn't.
3. HOW THE COMPETITIONS WERE DECIDED — for the Trophy, then the Green Jacket, then the \
Wooden Spoon: state how each was won (or, for the Spoon, lost) from its competition arc \
— the leader by round, the decisive moment, the final margin.
4. PLAYERS — one factual line per player, from the player arcs.

RULES:
- Use ONLY the supplied facts. Never invent holes, scores, players or events.
- Render hole detail for the beats that matter (must-include + decisive + standout, e.g. \
eagles/HIO/big blow-ups); you don't need to enumerate every blow-up or routine score.
- Honour the data precisely: where a rival "drew level" rather than taking the lead \
outright (see each lead change's `lead_type` / `outright`), say "drew level", not "took the lead".
- Each round is on a specific course (every beat carries its `course`). The same hole \
NUMBER in different rounds is a DIFFERENT hole on a (usually different) course — never \
treat them as "the same hole".
- Early-round lead changes, when the field is bunched, are routine — state them plainly, \
do not treat the opening exchanges as drama.
- **TEG has NO countback, NO tiebreakers, NO playoff.** Lead changes are caused by \
Stableford / Gross point accumulation, full stop. Never write "countback", "tiebreaker", \
"on countback math", or any similar mechanism. Tied scores are tied — say "drew level" or "tied".
- **Arithmetic must be exact.** When you assert an over-par total across a stretch \
(e.g. "X over par through six"), it must equal the precise sum of per-hole over-par \
(bogey = +1, double = +2, triple = +3, quad = +4, quint = +5, sext = +6). Compute, \
do NOT estimate. If the arithmetic is awkward, list the per-hole values and skip the \
running total.
- Plain, clear, British English. Short declarative sentences. **No narrative hooks** \
("The day's defining number was..."), **no characterisation** ("the round of his life"), \
**no dramatisation** ("the wheels came off") — that's the writer's job, not the draft's.
- Markdown headings. Keep it tight."""


# The story-plan fields that carry the STORYTELLING FRAME rather than the
# material: which shape the report takes, what it opens on, what gets planted
# early and paid off later. `plan_scope="arc"` sends these and nothing else —
# the dry draft already carries the facts, so this is the vehicle guidance on
# its own, without the per-round angles and per-player arcs steering the prose.
ARC_PLAN_FIELDS = ("title", "theme", "narrative_structure", "opening_hook",
                   "narrative_vehicles", "prominent_vehicle", "prominent_palette",
                   "foreshadow", "payoffs", "why_the_champion_won")

PLAN_SCOPES = ("full", "arc", "none")

# The bundle keys that carry CONTEXT the dry draft does not: venue character
# (architect, course type, TEG-visit counts), cross-TEG career storylines, and
# per-course player history. Deliberately excludes `beats` and
# `competition_arcs` — the dry draft is built from those and already renders
# them flat, so re-sending them would turn this into `report_single_pass`.
#
# Unlike the story plan, every one of these is STRUCTURED DATA rather than
# editorial prose. That is the whole point: it supplies material without
# supplying phrasing the writer will lift.
# `tournament_shape` joined on 2026-08-17: `ELEVATION_DEVICE` reads `close_finish`
# off it to pick the frame, so a context packet without it leaves one branch of
# the archetype table unanswerable.
BUNDLE_CONTEXT_KEYS = ("venue", "player_history", "player_course_history",
                       "player_relationships", "win_anatomy", "tournament_shape")

# The only fields in those keys whose values are SENTENCES rather than names,
# dates, enums or numbers. Four are code-generated from templates and one
# (`description`) is a human-written course blurb. `bundle_context="data"`
# drops all five, leaving a packet with no readable phrasing in it at all.
#
# Nothing factual is lost: every summary string is derived from numeric fields
# that stay (`visit_n`, `n_prior_visits`, `prior_best_gross`, `prior_best_teg`,
# `strokes_vs_last_visit`, `vs_runner_up`, …). What is lost is the arithmetic
# being done for the model — see the docstring warning on `report_around_draft`.
#
# ONE NON-OBVIOUS CONSEQUENCE. `WRITER_FAITHFULNESS` permits "defending
# champion" / "reigning holder" framing ONLY when a player's
# `notable_milestones` says so explicitly, and forbids inferring it from rank
# history. Stripping the field therefore makes that framing unavailable —
# correctly (it fails closed), but the narrative fact goes with it, even though
# `last_4_positions` still shows the win. If you want the framing, use
# `bundle_context=True`, or drop "notable_milestones" from this tuple.
DERIVED_PROSE_FIELDS = ("summary_facts", "notable_milestones", "description",
                        "visit_str", "area_visit")

CONTEXT_STYLES = ("annotated", "data")


def _strip_derived_prose(obj, fields: tuple = DERIVED_PROSE_FIELDS):
    """Recursively drop the sentence-valued fields, keeping the raw data.

    `fields` is a parameter so a caller can spare one. The Cowork kit spares
    `notable_milestones`, which is template output rather than authorial prose
    and the only licensed source for "defending champion" framing.
    """
    if isinstance(obj, dict):
        return {k: _strip_derived_prose(v, fields) for k, v in obj.items()
                if k not in fields}
    if isinstance(obj, list):
        return [_strip_derived_prose(v, fields) for v in obj]
    return obj


def _bundle_context_text(teg_num: int, style: str = "annotated") -> str:
    """Assemble the structured context block. Deterministic; no LLM call."""
    if style not in CONTEXT_STYLES:
        raise ValueError(f"bundle_context style must be one of {CONTEXT_STYLES}, "
                         f"got {style!r}")
    bundle, _ = assemble_bundle(teg_num)
    payload = {k: bundle[k] for k in BUNDLE_CONTEXT_KEYS if k in bundle}
    if style == "data":
        payload = _strip_derived_prose(payload)
        note = ("CONTEXT (raw data — venue, career and per-course history, and the "
                "anatomy of the win. Numbers and names only: no summary sentences "
                "are provided, deliberately. Derive what you need and phrase all of "
                "it yourself. Any comparison you state must follow exactly from "
                "these figures; if the arithmetic is not clean, leave it out")
    else:
        note = ("CONTEXT (structured data, not prose — venue character, career and "
                "per-course history, and the anatomy of the win. These are FACTS you "
                "may use and colour you may draw on; the phrasing is entirely yours")
    return note + "):\n" + json.dumps(payload, indent=2, ensure_ascii=False) + "\n\n"


def _plan_to_text(plan: Union[StoryPlan, dict], scope: str = "full") -> str:
    """Render the story plan for the writer, optionally narrowed to the arc.

    `scope`: `"full"` (production — the whole plan), `"arc"` (the narrative
    vehicles and story-arc fields only, see `ARC_PLAN_FIELDS`), or `"none"`.
    """
    if scope not in PLAN_SCOPES:
        raise ValueError(f"plan_scope must be one of {PLAN_SCOPES}, got {scope!r}")
    data = plan.model_dump() if isinstance(plan, StoryPlan) else plan
    if scope == "arc":
        data = {k: v for k, v in data.items() if k in ARC_PLAN_FIELDS}
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
                       dry_draft_style: str = "detailed",
                       model: Optional[str] = None,
                       events_cache: Optional[list] = None,
                       venue_cache: Optional[dict] = None) -> dict:
    """4a — produce the faithful, no-colour storyline draft from the plan + evidence.

    `dry_draft_style` picks the prompt: `"detailed"` (default — chronological one-
    section-per-round with full hole-level rendering; floors voice + specificity in
    the entertaining pass that follows) or `"light"` (narrative-structure-aware,
    selective hole detail — leaner read, useful for fast/post-round mode).
    `events_cache` / `venue_cache` enable per-TEG reuse (see `assemble_bundle`).
    """
    if dry_draft_style not in ("light", "detailed"):
        raise ValueError(f"dry_draft_style must be 'light' or 'detailed', got {dry_draft_style!r}")
    system = DRY_DRAFT_SYSTEM_DETAILED if dry_draft_style == "detailed" else DRY_DRAFT_SYSTEM_LIGHT
    bundle, _ = assemble_bundle(teg_num, mode=mode, tone=tone,
                                events_cache=events_cache, venue_cache=venue_cache)
    user = _build_author_input(plan, bundle)
    text, usage = llm.generate_text(system, user,
                                    model=model or llm.DEFAULT_MODEL, max_tokens=8000,
                                    stage="dry_draft", label=f"teg{teg_num}")
    out_path = f"{output_dir()}/teg_{teg_num}_dry_draft.md"
    with open(out_path, "w") as f:
        f.write(text)
    return {"text": text, "usage": usage, "output_path": out_path}


# ===========================================================================
# 4b — the entertaining report (authoring A/B) + repetition lint
# ===========================================================================
# ---------------------------------------------------------------------------
# C2 — voice, craft and economy. Edit this to change how the report READS.
# ---------------------------------------------------------------------------
_WRITER_ROLE = """You are a golf writer producing the finished, entertaining report \
on a TEG (an amateur golf tournament of several rounds), for an audience of THE \
PLAYERS THEMSELVES — insiders who know each other, the courses and the history, who \
want to relive the event and be gently ribbed, and who will instantly spot any \
factual error.
"""

# ---------------------------------------------------------------------------
# Editorial stance — CONTRACT, not voice. What the report is FOR and what it
# owes the champion. Holds whatever register the prose is written in.
#
# Split out of the old `_WRITER_AIM` on 2026-08-16. That block interleaved two
# separable things: the duty the report owes the winner (voice-independent) and
# where the comedy points (voice-specific). Since a custom voice now replaces
# the voice block wholesale, anything that must survive the swap had to come out
# of it. The prose is the original prose, sorted into the two halves; the only
# rewritten sentence is NARRATIVE PULL's opener, which used to cross-refer to
# the comic devices sitting below it.
# ---------------------------------------------------------------------------
_WRITER_EDITORIAL = """WHO THE REPORT IS FOR, AND WHO IT IS ABOUT. Read this first. It governs everything below.

**This is the winner's story.** Its first duty is to make clear WHY the champion won. \
The plan's `why_the_champion_won` and the bundle's `win_anatomy` give you the answer \
already worked out. Were they good in one round or all four? Were their rivals bad? \
Did somebody blow a lead? Land that, or the report has failed however good the prose is.

**Proportion matters.** A report whose THROUGH-LINE is how poor the champion was has \
failed, however well written. Their failings are punctuation in a story about a win, \
never the story itself.

The one thing that is banned outright is WITHHOLDING THE CREDIT: writing the champion \
as a passive accident of arithmetic, or implying the win was undeserved, or letting a \
catalogue of their failings stand in place of any account of how they won.

**A bad gross score is not a bad tournament.** The Trophy and the Spoon are decided on \
NET (Stableford from TEG 8, net-vs-par before). A high-handicap player can post \
horrifying gross numbers and win the thing. That contrast is a genuinely good story \
when the gross really is dreadful, and it must never be written as though the champion \
were secretly undeserving. The Green Jacket is the gross competition; keep the two \
straight and never treat a gross figure as evidence about the Trophy.

NARRATIVE PULL. The report is a magazine feature, not a results record. The piece as a \
whole must make the reader want to keep reading. Raise a question, a stake, or an \
apparent claim early, and let the reader work towards its resolution or contradiction \
rather than stating the answer upfront and walking through it in order. Vary pace. Let \
some passages breathe and others land fast. If a stretch reads like a faithful account \
of what happened rather than something someone would choose to read, it needs more shape.
"""

# Tournament-specific, and VOICE: aims the comedy at the right targets. The round
# writer has no champion to protect, so this block is deliberately NOT shared.
_WRITER_COMIC_AIM = """THESE RULES AIM THE COMEDY; THEY DO NOT REDUCE IT. Everything above stays fully in force. The mechanisms, the escalation, the deadpan. What follows only decides WHERE the comedy points.

**Praise the achievement, and be merciless about the golf.** These are not in tension. \
Holding both at once is the single best register available to you. The champion EARNED \
the win and the report should say so without hedging. It should simultaneously be \
hyper-aware of how ragged the winning golf actually was, and of how comprehensively the \
rest of the field disgraced themselves. "He won it with a 10 on his card and a shrug, \
which is roughly what winning looks like round here" is the target. So is "the winner \
didn't avoid the wreckage; he was simply the one whose wreckage cost him least."

  Do NOT go easy on the champion's golf. Their blow-ups, their ruinous stretches, the \
holes that would embarrass a beginner. All of it is fair comic material and the report \
is worse without it. Winning by being the least catastrophic man in a catastrophic field \
is a genuinely funny way to win, and saying so is a compliment in this company.

  **But the DELIVERY has to carry it, and this is the part that goes wrong.** A flat \
recitation of the champion's failings reads as a charge sheet, however accurate. The \
same facts delivered with theatrical, slightly camp overstatement read as affection. \
Elevate: mock-epic, grandiose, absurdly solemn. That is the subverted gravitas above, pointed \
directly at the winner. The facts do not change; the register does.

    FLAT (wrong):  "He took 10 at the 14th and 8 at the 17th. His R4 was the \
worst of the four."
    ELEVATED (right): "He arrived at the 14th with the tournament in his \
pocket. He took a 10. It was an act of magnificent indifference to his own \
self-interest. One can only assume he was making a point about the futility of \
ambition. The trophy did not seem to mind."

  Note the shape of that example as well as its register. Five short sentences, no \
em-dashes, one idea each. That is the target on BOTH counts. The same content as one \
long sentence would read as hard work and the joke would not land.

**Mockery, by target.** Calibrate. This is a group of friends who know each other:
  - **Wooden Spoon holder: hard.** The Spoon is the joke prize. Its holder expects, and \
has earned, a proper going-over. Be specific and merciless.
  - **The rest of the field: moderate.** Blow-ups, ruinous rounds and general \
humiliation from players who were never contending are exactly the colour the report \
wants. Enjoy them.
  - **The runner-up: moderate.** A player who threw it away is a legitimate tragic \
figure and can be needled for it. That is often the real story.
  - **The champion: hard on the golf, never on the achievement.** Same intensity as \
anyone else when describing what they actually did with a golf club. The difference is \
that the win stands, unqualified, alongside it.
"""

# Tournament-specific structure, palette and construction rules.
_WRITER_STRUCTURE = """STRUCTURE — follow the STORY PLAN you are given:
- The plan's `narrative_structure` and `opening_hook` set the shape of the report. \
**Chronology is a scaffold, not a constraint** — you may (and should) reorder, open \
*in medias res*, flash back, or thread a theme across rounds when the story calls \
for it. The dry draft is a fact anchor, not a structural template.
- The plan's `narrative_vehicles` name 1–3 storytelling frames the editor picked — \
e.g. `bookends + hero_arc`, `inversion + motif`, `comeback + theme_led_body`. \
**Honour them in the prose**: if the editor picked `bookends`, the opener and the \
close should rhyme; if `motif`, the recurring image should be set up early and \
called back where it lands; if `hero_arc`, the protagonist's trajectory should \
carry the report; if `inversion`, the before-and-after contrast should be \
explicit; if `theme_led_body`, the round headings can be dropped or replaced with \
thematic ones. The vocabulary is shared between the editor and you.
- Open with the title and an overview that lands the theme — drawing on the plan's \
`opening_hook` if it's set to something other than chronological. Where it doesn't \
break the narrative, the opener should give the reader a sense of what happened in \
more than one of the three competitions — even a single clause is enough (e.g. \
"...while at the bottom, X was already assembling the Spoon"). Don't force it if the \
chosen frame only supports one competition up front; the closing section below \
covers all three regardless.
- Round-by-round and theme-led are BOTH valid structures. If you take the \
round-by-round route, each round should have its own `## Round N — …` heading \
(themed titles after the number are fine, e.g. `## Round 1 — 46 and Out of \
Sight`); the deterministic per-round standings renderer keys off those markers \
and will inject standings under each. If you take a theme-led route and don't \
use `## Round N` markers, a consolidated "Standings by round" appendix will be \
inserted before the player closing — so the data still ships either way. Carry \
the theme through and pay off the foreshadowing hooks.
- The report is built around the THREE COMPETITIONS in priority order — the Trophy \
(Stableford for TEG 8+; net-vs-par for TEGs 1–7 — lower is better, signed like +47; \
see `trophy_metric` in the bundle) first, then the Green Jacket (Gross), then the \
Wooden Spoon — and you must make clear HOW each was won (or, for the Spoon, lost).
- Weave in the venue/course colour and the player arcs where they earn their place.
- **Before the player closing, include a short "how it was decided" section** — one \
paragraph or a few bullets, one per competition, naming plainly how the Trophy, the \
Green Jacket and the Wooden Spoon were each won or lost (the decisive moment, who \
beat whom, the margin). Use a heading like `## How it was decided` (or similar). \
This is the one place a reader can check what happened in each competition without \
re-reading the whole narrative — it must not be buried inside prose elsewhere and \
skipped here. Keep it compact and factual; it should read as a clean summary, not a \
second telling of the story. This section is non-negotiable; do not omit it, and do \
not let it substitute for covering the competitions in the narrative body too — it's \
a floor, not the only place the competitions are covered. It sits ALONGSIDE (not \
instead of) any TEG-record or personal-best fact that belongs in this section's \
competition — e.g. if the Green Jacket winner's total is a top-3 all-time Gross \
total, say so here even if the narrative body didn't have room for it.
- **The report MUST END with a player-by-player section** — 4–6 short bullets, one \
or two sentences per principal player, drawing on the plan's `players[]` arcs AND \
the moments you've narrated. The heading MUST be exactly `## Player-by-player summary` \
— not a variant, not a witty substitute. This closing is non-negotiable; do not omit it.

PALETTE — context vehicles to pull on. **At least ONE must be prominent in the report \
(featured in the opener AND threaded through the body); multiple are welcome where each \
genuinely lands; the one-prominent rule is non-negotiable.** None of (a)-(g) is itself \
mandatory; the choice is yours, informed by the plan's **`prominent_palette`** and what's \
most interesting about THIS tournament. (Note `prominent_palette` — NOT `prominent_vehicle`, \
which is the structural FRAME and is covered under STRUCTURE above. They are different \
fields with different vocabularies; do not read one for the other.)

a) **Cross-TEG career storylines.** The bundle's `player_history` and the plan's \
`players[]` carry factual storyline phrases (Nth Trophy / Jacket / Spoon; back-to-back; \
first win in N years; defending champion; "first Trophy after 2 prior runner-up finishes"; \
etc.). Use them as factual anchors; **flourish the colour yourself in voice — \
the pre-computed phrases are deliberately neutral so you can vary the framing.** For \
example, "first Trophy after 2 prior Trophy runner-up finishes" can become "bridesmaid \
no more", "the nearly-man finally arrives", "second twice and now first", "two near-misses \
made good", or whatever fits the voice in the moment. Reuse of the same framing across \
players or reports is a tell — vary it. Do NOT invent any win counts, streaks, or \
historical claims not present in the bundle.

b) **Per-course player history.** When the bundle includes `player_course_history` items \
(first visit to this course; Nth visit; personal best on this course; strokes vs last \
visit here; course record), use them. **New course records (good or bad), on courses \
played more than twice previously, MUST be included** — they appear in \
`must_include_beat_ids`.

c) **Course / venue character.** The venue context carries architect, type, TEG-visit count. \
Use these when the venue's character earns it — debut routings, sentimental returns, \
courses with reputation. Skip when "another round on familiar ground".

d) **Decisive-moment framing + counterfactual.** Each competition arc carries a \
`decisive_moment`. Name THE moment when the result was effectively decided. Occasional \
counterfactuals — "but for the quintuple at the 8th, the gap would have been one" — work \
when the data supports them precisely. Don't speculate beyond the evidence.

e) **Player-thread continuity within the tournament.** When a player's round-by-round \
shape forms a recurring pattern (serial Spoon blow-ups; Jacket-without-Trophy parlay; \
parallel collapses across the field), name the pattern. Set it up early; pay it off when \
it resolves. The closing player-by-player summary earns its place by collecting these.

f) **Records and rare feats woven into prose.** The deterministic appendix at report end \
already inventories every PB, TEG record and rare feat. In prose, selectively pull forward \
the ones that anchor THIS story ("the 51 was the highest single round TEG has ever \
recorded, full stop"). Don't double up on the appendix; pick the ones that earn their \
narrative place.

g) **Foreshadow / payoff threads.** The plan's `foreshadow[]` hooks plant questions early; \
the plan's `payoffs[]` name which round/section resolves each one. **Every foreshadow \
seed MUST be paid off explicitly in the named section** — don't plant a seed and forget \
it. This is the single most common thinness in past reports.

CRAFT:
- Render SPECIFIC holes ("a double at the par-4 10th, a 10 at the short 17th"), not vague \
abstractions — the detail is what makes it sing.
- VARY your language. Never lean on the same dramatic word twice — do not repeat \
"disaster", "meltdown", "catastrophe" and the like; reach for fresh, precise phrasing.
- Vary sentence rhythm, and let a short sentence land a point. **Sentence-length \
discipline:** average around 15 words, and no sentence past roughly 25. Where a thought \
needs room, split it into two sentences rather than let one run on. The wit lands in \
something short and flat, never in an unfurling clause.
"""

_WRITER_ECONOMY = """ECONOMY. Sentence- and paragraph-level mechanics. Write tight on the first pass; \
these are construction rules, not a fix-up checklist. There is no exception for a long \
sentence that "earns its length". Prose that drowns its own punchline is the single most \
common failure in past reports.

1. **Em-dashes are banned outright.** Zero, in the entire report. This repeats the rule \
from the voice section because it is the one most often broken. Every aside you would \
have set off with an em-dash becomes its own sentence, or is cut.
2. **Subordinate-clause budget.** Three+ subordinate clauses in one sentence are fine \
ONLY when every clause carries a fact, image or beat. Otherwise split or trim.
3. **No "particular kind of X / one of them" preambles.** Skip the wind-up and state \
the thing. The preamble carries no fact.
4. **No subject-burying preambles.** "The detail that elevates X to Y is that Z…" / \
"If there is a quiet hero, it is X, who…" describe the fact before stating it. Lead \
with the actor or the fact; cut the wrapper.
5. **Plain word over inflated phrasing.** "That hole" not "the very hole at which." \
"Probably" not "something approaching." Gravitas comes from what happens, not from the \
vocabulary describing it.
6. **Split run-on factual lists.** A sentence of 20+ words whose bulk is comma-separated \
facts breaks at a sensible seam.
7. **Two equal facts = two sentences.** When one sentence joins two equal-weight beats \
with "who" or a relative clause and each part would stand alone, split them. \
Test: would a full stop after the first part lose meaning? If not, use one.
8. **One aside form per sentence.** Don't stack asides; only stack when the second \
aside IS the joke.
9. **Compressed rhythmic lists; bogey shorthand.** Sequences of same-type events read \
better compressed: "quad, triple, double, double", not "quadruple-bogey 8, triple-bogey \
7, double-bogey 6, double-bogey 6". In general prose, "double" and "triple" are \
acceptable shorthand for double- and triple-bogey when context is clear (this is \
shorthand, not redundancy. Principle 5 still governs whether to pair the term with par \
and stroke count).
10. **Punchline isolation.** Short payoff sentences belong as their own paragraph. \
Reversals, bathos kickers, the number that lands. Attached to a long preceding \
sentence they get absorbed.
11. **One dominant idea per paragraph.** A shift in subject, tone, or beat is a signal \
to start a new paragraph. If a paragraph is doing too much, break it at the natural seam.
"""

# ---------------------------------------------------------------------------
# The writer prompt has THREE slots, not two, since 2026-08-16:
#
#   WRITER_CONTRACT   what the report must be, whatever register it is in
#   <voice>           how it reads               <- the swappable slot
#   WRITER_FAITHFULNESS + WRITER_OUTPUT_RULE     the guardrails
#
# `WRITER_VOICE` is the HOUSE occupant of the middle slot. It is not privileged
# in the assembly: `build_writer_system(voice=...)` drops any complete voice
# description into the same position, and production simply passes none.
#
# The line between contract and voice is "would this still be true if the report
# were written flat and straight?" — the winner's-story duty, the structure, the
# scoring-redundancy notation and the SI guidance all survive that test; the
# comic mechanisms, the mockery calibration and the sentence economy do not.
#
# ORDER NOTE: STRUCTURE and STROKE_INDEX now sit BEFORE the voice rather than
# inside it. Same content, one block moved, so that the contract is contiguous
# and a voice swap is a single substitution. `_WRITER_ECONOMY`'s back-reference
# to the voice section still resolves — VOICE_CORE is directly above it.
# ---------------------------------------------------------------------------
WRITER_CONTRACT = "\n".join((
    _WRITER_ROLE,
    _WRITER_EDITORIAL,
    prompts.ELEVATION_DEVICE,
    _WRITER_STRUCTURE,
    prompts.SCORING_REDUNDANCY_RULE,
    prompts.STROKE_INDEX_RULE,
))

# The house voice. Edit this to change how the standard report READS; pass a
# `voice=` argument instead to try one without touching the file.
WRITER_VOICE = "\n".join((
    prompts.VOICE_CORE,
    _WRITER_COMIC_AIM,
    prompts.NAMED_PRINCIPLES,
    _WRITER_ECONOMY,
))


# ---------------------------------------------------------------------------
# D1 — preventive faithfulness rules. Deliberately a SEPARATE constant from the
# voice block above, even though they are concatenated into one prompt.
#
# They are different components with different failure modes and different
# tests: a flat sentence versus a factual error the players catch; taste versus
# mechanical verification. Keeping them in one 16k literal meant every voice
# experiment edited the same string as the guardrails, which is how you lose a
# faithfulness rule by accident while tuning humour.
#
# Every rule here traces to an observed failure. Six of them are now ALSO checked
# mechanically by `verify.py` (D3) — see the table in reporting/README.md. Do not
# delete a rule just because D3 covers it: prevention and detection are cheap
# together, and D3 only sees the finished text.
# ---------------------------------------------------------------------------
_WRITER_FAITHFULNESS_TOURNAMENT = """- **NEVER include beat IDs in the prose.** Beat references like `b07`, `cr01`, `(b13, b14)` \
are internal identifiers for your tracking; they must NOT appear in the finished report. \
The reader sees only prose. If you find yourself tempted to write "(b07)" as a citation, \
delete it — the sentence should stand on its own factual content.
- **DAYS AND WEEKS — strict rules.** A TEG is a tournament of 4 rounds played on 4 \
consecutive days. **Do NOT call it "a week"** — use "the tournament", "the trip", \
"the four days", "the visit", or the area name. Weekday names (Thursday, Sunday, etc.) \
appear in the bundle as `venue.rounds[i].weekday` and are VERIFIED — use them ONLY in \
the opener of the relevant round section (e.g. "The Sunday round at Boavista…"), and \
ONLY taken verbatim from `weekday`. **Anywhere else — callbacks, lookforwards, \
references across rounds — use the round number ("R2", "Round 2", "the second round", \
"two rounds later"), NOT a weekday.** Inventing weekday names (e.g. calling R1 \
"Tuesday" when the bundle says "Saturday") is a faithfulness failure the players will \
spot.
- **PLAYERS WHO PLAYED THIS TEG ONLY.** Only players who actually appear in the bundle's \
`competition_arcs`, `beats`, or `player_history` for THIS TEG are participants. The bundle \
may include cross-TEG career context but the player list for THIS tournament is fixed. \
NEVER write a player-by-player summary bullet — or any prose — for a player who did not play this \
TEG. If a player you'd expect to see is absent, they are absent; don't note their absence, \
don't include them.
- **PLAYER RELATIONSHIPS — only those in the bundle.** The bundle's \
`player_relationships` field lists verified ties (e.g. "Alex Baker and Jon Baker are \
brothers"). You may reference these. **DO NOT INFER ANY OTHER RELATIONSHIPS from \
shared surnames or any other signal.** Two players named Baker are NOT cousins, \
uncle and nephew, or any other connection unless the bundle says so. If `player_relationships` \
is empty, every player in the field is unrelated as far as the report is concerned. \
Inventing relationships is a fabrication of the same kind as inventing scores.
- **"DEFENDING CHAMPION" / "REIGNING [X]" / "LAST TO WIN" framing — only from an explicit \
milestone string.** Only claim a player is the defending Trophy/Jacket champion, the reigning \
titleholder, or "the last man to win" a competition if the bundle's `notable_milestones` for \
that player explicitly says so (e.g. "defending Trophy champion (TEG N)"). **Do NOT infer this \
from win counts, past rank history, or general reputation** — a player who won a competition \
two TEGs ago, or who finished runner-up last time, is NOT "the last to win it": the actual \
most recent winner may be a player who isn't even in THIS TEG's field, since not every player \
plays every TEG. If no milestone string says "defending champion" or equivalent for a given \
competition, don't claim it, imply it, or use "reigning" for that competition — describe their \
past wins by count and TEG number instead ("N prior Jacket wins") without asserting recency.
- **Every beat id in the plan's `must_include_beat_ids` MUST be covered in the prose** \
— not just hinted at. These are the spine + TEG records + personal bests + rare feats \
(holes-in-one, eagles, all-time top-3 rounds, big blow-ups). Skipping any is the most \
visible kind of omission. A deterministic "PBs and TEG records" appendix is also \
auto-appended to the styled output as a safety net.
- Early-round lead changes, when the field is bunched, are normal — do NOT frame routine \
opening jockeying as "chaos" or high drama. The lead changes that matter are the late ones. \
**This is now given to you as data, not left to judgement:** each arc carries a \
`lead_change_summary` (and `bottom_change_summary`) with `early_round1`, `final_round`, \
`outright` and `all_routine`, and every individual change carries a `significance` of \
`routine` / `notable` / `decisive`. When `all_routine` is true, the headline count is \
opening jockeying and nothing more — report it plainly or not at all. Never build drama \
on a raw `n_lead_changes` total without checking what it is made of.
"""

# Shared rules first, then the tournament-only ones. `startswith` on the header is
# asserted in tests, so the header stays attached here rather than in prompts.py.
WRITER_FAITHFULNESS = ("FAITHFULNESS (non-negotiable):\n"
                       + prompts.SHARED_FAITHFULNESS
                       + _WRITER_FAITHFULNESS_TOURNAMENT)

WRITER_OUTPUT_RULE = prompts.OUTPUT_RULE


def build_writer_system(voice: Optional[str] = None) -> str:
    """Assemble the tournament writer's system prompt around a voice description.

    `voice` is a COMPLETE description of the register to write in, not a delta
    from the house voice — it REPLACES `WRITER_VOICE` rather than appending to
    it. "Drier than usual" is the wrong shape of input here and will read as an
    instruction with no baseline; describe the voice you want from scratch.

    Everything else is fixed: the contract above it (who the report is for, the
    winner's-story duty, structure, the palette, scoring-redundancy notation, SI)
    and the guardrails below it (faithfulness, output format). A voice cannot
    shed either, which is the point of the split.

    Pass nothing for the house voice. `WRITER_SYSTEM` is exactly that.
    """
    return "\n".join((WRITER_CONTRACT, voice.strip() if voice else WRITER_VOICE,
                      WRITER_FAITHFULNESS, WRITER_OUTPUT_RULE))


WRITER_SYSTEM = build_writer_system()

REVISE_SYSTEM = WRITER_SYSTEM + """

YOU ARE NOW REVISING YOUR OWN FIRST DRAFT. Critique it internally against: faithfulness; \
whether the theme lands and the foreshadowing pays off; anything important buried or \
any filler that should go; repeated words or phrasings; whether each round has a clear \
angle; and whether the three competitions are each clearly resolved. Then output ONLY \
the improved report — tighter, fresher, no repetition — same facts."""

LINT_SYSTEM = """You are a copy-editor making ONE kind of change only: eliminate repeated \
or over-used words and phrasings, replacing them with fresh, precise alternatives so no \
striking word is reused close to itself. Do NOT change any facts, names, numbers, \
structure, or headings, and do not alter meaning or length materially.

**PROTECTED TERMS — never substitute these.** They are fixed nomenclature, not stylistic \
choices:
- Competition names: "Trophy", "Green Jacket", "Jacket", "Wooden Spoon", "Spoon".
- Player names: any full name or surname appearing in the report.
- Scoring terms: "Stableford", "Gross", "par", "bogey", "double bogey", "triple bogey", \
"quadruple bogey", "quintuple bogey", "sextuple bogey", "birdie", "eagle", "hole-in-one".
- Course / venue names.

Repetition of any protected term is acceptable; do NOT swap "Jacket" for "award" / \
"accolade" / "blazer", "Trophy" for "title" / "cup", or "Spoon" for "wooden spoon" / \
"prize". Use the term as given.

Return the edited markdown only."""

TIGHTEN_SYSTEM = ("""You are tightening an existing golf tournament report. The voice \
(deadpan / gravitas / wit, in the spirit of """ + prompts.VOICE_WRITERS_PHRASE + """) \
is already correct. Your job is to sandpaper specific over-built \
constructions WITHOUT changing the voice, the facts, or the structure.

CUT THESE PATTERNS when they don't earn their length:
1. Three+ em-dashes in a single paragraph — refactor at least one into a separate \
sentence or strip the aside. Two per paragraph is the ceiling.
2. Three+ subordinate clauses in a single sentence — if every clause carries a fact, \
image or beat, leave it. Otherwise split or trim.
3. The "There is a particular kind of X... This was one of them" preamble — replace \
with the direct statement; the preamble carries no fact.
4. Run-on factual lists — when a sentence is 20+ words and the bulk is comma-separated \
facts, split at a sensible break.
5. Stacked-aside paragraphs — pick one aside form per sentence; only stack when the \
second aside is the joke.
6. Subject-burying preambles — "The detail that elevates X to Y is that Z…" / \
"If there is a quiet hero, it is X, who…" describes the fact before stating it. Start \
with the actor or the fact. Cut the wrapper.
7. Pompous or inflated phrasing — use the plain word. "That hole" not "the very hole \
at which." "Probably" not "something approaching." Gravitas comes from what happens, not \
from the language describing it.
8. Two-fact sentences that belong as two sentences — when a long sentence contains two \
equal-weight beats joined by "—", "who", or a relative clause, and each part would stand \
alone, split them. If you could put a full stop after the first part without losing \
meaning, do it.
9. Compressed rhythmic lists; shortened bogey terms — in sequences of same-type events, \
use compressed forms: "quad, triple, double, double" not "quadruple-bogey 8, triple-bogey \
7." In general prose, "double" and "triple" are acceptable shorthand for "double-bogey" \
and "triple-bogey" when context is clear.
10. Punchline isolation — short payoff sentences (reversals, bathos kickers, the number \
that lands) belong as their own paragraph. Attached to a long preceding sentence they get \
absorbed.
11. Paragraph length — if a paragraph is doing too much, break it at the natural seam. \
One dominant idea per paragraph. A shift in subject, tone, or beat is a signal to start \
a new paragraph.

PRESERVE ALWAYS:
- The deadpan / gravitas register.
- Bathos: long sentences that are funny BECAUSE they are long stay long.
- All facts: holes, scores, par values, SI references, cross-tournament context, course \
records, weekday names, player names exactly as written.
- Section headings and the report's structural shape.
- Closing payoff sentences (paragraph punchlines, kicker lines of player-by-player summary bullets).
- Player relationships exactly as in the source (Bakers are brothers, Pattersons are \
brothers; do not invent or change any others).

DEFAULT: change only what you must. This is not a rewrite. The output should read as \
the same voice writing more cleanly, not a different voice writing cleaner.

Output the complete tightened report as markdown — no preamble, no commentary, same \
structure, same headings, same length or slightly shorter.""")


def load_story_plan(teg_num: int) -> dict:
    with open(f"{output_dir()}/teg_{teg_num}_story_plan.json") as f:
        return json.load(f)


def load_dry_draft(teg_num: int) -> str:
    with open(f"{output_dir()}/teg_{teg_num}_dry_draft.md") as f:
        return f.read()


def _variant_label(label: str) -> str:
    """Normalise an experiment label and refuse ones that clobber the chain.

    `report_final` / `report_styled` are what the site reads; `A_around_draft`
    is the production chain's own intermediate. An experiment writing to any of
    them stops being an experiment.
    """
    label = label.strip().strip("_")
    if not label:
        raise ValueError("label must be a non-empty variant name")
    if label in {"final", "styled", "A_around_draft"}:
        raise ValueError(
            f"label {label!r} would overwrite a canonical artefact; "
            "name the voice instead, e.g. 'broadsheet' or 'plainspoken'")
    return label


def _write(teg_num: int, label: str, text: str) -> str:
    path = f"{output_dir()}/teg_{teg_num}_report_{label}.md"
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
                                    model=model or llm.DEFAULT_MODEL, max_tokens=16000,
                                    stage="report_single_pass", label=f"teg{teg_num}")
    return {"text": text, "usage": usage, "output_path": _write(teg_num, "B_single_pass", text)}


def report_around_draft(teg_num: int, plan: Union[StoryPlan, dict], dry_text: str,
                        model: Optional[str] = None, *,
                        voice: Optional[str] = None,
                        label: str = "A_around_draft",
                        plan_scope: str = "full",
                        bundle_context: Union[bool, str] = False) -> dict:
    """Approach A: build the entertaining report around the dry factual draft.

    This is stage 4b of the production chain AND the voice-experiment path.
    Deliberately one function: a voice tried here is tried on the real writer,
    through the real prompt assembly, so nothing can be true of the experiment
    and false of the pipeline. The defaults ARE production — every experiment
    knob below is opt-in.

    Args:
        voice: a COMPLETE description of the register to write in, replacing
            `WRITER_VOICE` (see `build_writer_system`). None = house voice,
            which is what `backfill` passes.
        label: output filename stem. Leave it alone in production; a voice
            experiment should name its own so it doesn't clobber the chain's
            intermediate. `write_from_dry` handles that for you.
        plan_scope: how much of the story plan the writer sees. `"full"`
            (production), `"arc"` (narrative vehicles and story-arc fields only
            — the dry draft supplies the facts), or `"none"` (dry draft alone,
            which isolates the voice from any structural steer).
        bundle_context: append the structured venue / career-history /
            win-anatomy block from the bundle (see `BUNDLE_CONTEXT_KEYS`). This
            is how you give a variant the full material WITHOUT the plan's
            pre-written phrasing: every plan field is editorial prose the writer
            can lift, whereas these are data. Deterministic, no extra LLM call.

            `True` (or `"annotated"`) sends the block as the bundle builds it,
            including the code-generated summary sentences. `"data"` strips
            every sentence-valued field (`DERIVED_PROSE_FIELDS`), leaving names,
            dates, enums and numbers only.

            **`"data"` moves arithmetic onto the model.** The stripped summaries
            are where "11 shots worse than his last visit" is computed for it;
            without them it derives comparisons itself, against a faithfulness
            rule that demands exact arithmetic. Check `findings` on the output.
    """
    plan_block = ("STORY PLAN:\n" + _plan_to_text(plan, plan_scope) + "\n\n"
                  if plan_scope != "none" else "")
    context_block = (_bundle_context_text(
        teg_num, "annotated" if bundle_context is True else bundle_context)
        if bundle_context else "")
    facts_source = ("here or in the plan" if plan_scope == "full"
                    else "in the draft below or the context above" if context_block
                    else "in the draft below")
    user = (plan_block + context_block
            + "DRY FACTUAL DRAFT (accurate — every fact you may use is "
            + facts_source + "; add no others):\n" + dry_text
            + "\n\nRewrite this into the finished, entertaining report. Reshape structure "
              "and wording freely for engagement, but add NO new facts.")
    if plan_scope != "full":
        # The contract block references plan fields (`players[]`,
        # `must_include_beat_ids`, the per-round angles) that a narrowed scope
        # does not supply. Say so, or the writer hunts for them and improvises.
        supplied = (", ".join(f"`{f}`" for f in ARC_PLAN_FIELDS)
                    if plan_scope == "arc" else "none")
        user += ("\n\nNOTE ON THE PLAN: the only story-plan fields supplied to you are: "
                 + supplied + ". Where your instructions refer to a plan field you have "
                 "not been given, disregard that reference and work from the dry draft "
                 "instead. Every structural requirement still stands.")
    text, usage = llm.generate_text(build_writer_system(voice), user,
                                    model=model or llm.DEFAULT_MODEL, max_tokens=16000,
                                    stage="report", label=f"teg{teg_num}")
    return {"text": text, "usage": usage, "output_path": _write(teg_num, label, text)}


def report_critique_revise(teg_num: int, plan: Union[StoryPlan, dict],
                           mode: str = "balanced", tone: str = "house",
                           model: Optional[str] = None) -> dict:
    """Approach C: single-pass draft, then a self-critique-and-revise pass."""
    bundle, _ = assemble_bundle(teg_num, mode=mode, tone=tone)
    draft_user = _build_author_input(plan, bundle) + "\n\nWrite the finished report now."
    draft, u1 = llm.generate_text(WRITER_SYSTEM, draft_user,
                                  model=model or llm.DEFAULT_MODEL, max_tokens=16000,
                                  stage="report_draft", label=f"teg{teg_num}")
    revise_user = ("STORY PLAN:\n" + _plan_to_text(plan)
                   + "\n\nYOUR FIRST DRAFT:\n" + draft
                   + "\n\nRevise it per your instructions. Output only the improved report.")
    final, u2 = llm.generate_text(REVISE_SYSTEM, revise_user,
                                  model=model or llm.DEFAULT_MODEL, max_tokens=16000,
                                  stage="report_revise", label=f"teg{teg_num}")
    return {"text": final, "draft": draft, "usage": (u1, u2),
            "output_path": _write(teg_num, "C_critique_revise", final)}


def _strip_beat_ids(text: str) -> str:
    """Remove leaked beat-ID references like `(b07)`, `(cr01, b13)` from prose.

    Belt-and-braces over the writer prompt rule: even with the prompt instruction,
    a beat ID occasionally slips through. This is mechanical and deterministic.
    Handles parenthetical groups and stray bare references; preserves a clean
    sentence (collapses double spaces).
    """
    import re
    # Parenthetical groups containing only beat IDs (with optional commas/spaces)
    text = re.sub(r"\s*\(\s*(?:b|cr)\d+(?:\s*,\s*(?:b|cr)\d+)*\s*\)", "", text)
    # Bare references like "b13" or "cr01" left dangling (rare)
    text = re.sub(r"\b(?:b|cr)\d{2,}\b", "", text)
    # Collapse the resulting double spaces
    text = re.sub(r"  +", " ", text)
    # Tidy up space-before-period / comma artefacts
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    return text


def repetition_lint(text: str, model: str = "claude-haiku-4-5",
                    label: str = "") -> Tuple[str, object]:
    """Narrow final pass: kill repeated/over-used words only. Returns (text, usage).

    Defaults to Haiku 4.5 — the lint is a mechanical copy-edit (no reasoning), so the
    cheap model is appropriate. `thinking=False` because Haiku doesn't support
    adaptive thinking. Pass `model=` to override.

    Under the `agent` provider the model choice is advisory: the responding session
    answers with whatever model it is running, so the lint costs nothing but is
    done by a heavier model than it needs. `label` names the call in the mailbox.

    Also runs `_strip_beat_ids` after the LLM lint to mechanically remove any
    leaked beat-ID references (`b07`, `(cr01)`, etc.) that slipped through the
    writer prompt rule.
    """
    linted, usage = llm.generate_text(LINT_SYSTEM, text, model=model, max_tokens=16000,
                                      thinking=False, stage="lint", label=label)
    return _strip_beat_ids(linted), usage


def tighten_prose(text: str, model: str = "claude-sonnet-4-6") -> Tuple[str, object]:
    """One-off prose density pass: trim em-dash stacks, run-ons, content-free preambles.

    Returns (text, usage). Does not touch facts, voice, or structure.
    Defaults to Sonnet 4.6 — needs judgement to distinguish bathos from bloat.
    """
    tightened, usage = llm.generate_text(TIGHTEN_SYSTEM, text, model=model, max_tokens=16000,
                                         thinking=False, stage="tighten")
    return tightened, usage


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


# ===========================================================================
# Voice restyling — an EXPERIMENT LEVER, deliberately not in the default chain
# ===========================================================================
# A ONE-OFF EXPERIMENT TOOL. Nothing in the pipeline calls this — `backfill.py`
# runs plan -> dry -> around -> lint -> style -> verify and stops. It exists to
# find a target voice; once found, that voice is folded into `WRITER_VOICE` and
# this function goes back to being unused until the next voice question.
#
# Takes an already-finished report and rewrites ONLY its voice. Everything else
# — facts, structure, headings, standings, records — is held literally constant,
# because the input is the finished text rather than the bundle. That makes it
# the tightest possible A/B for voice: one variable, one API call.
#
# WHY THIS IS NOT A PIPELINE STAGE. The original authoring A/B tested exactly
# this shape as a default (variant C, critique-revise) and rejected it: the extra
# pass over finished prose fabricated a "countback" detail. Every pass over prose
# is a fabrication opportunity, so this stays an opt-in tool for experiments.
#
# What has changed since that verdict is that D3 now exists, so a rewrite can be
# *checked* rather than merely trusted — `verify=True` (the default) runs the
# mechanical checks over the output and returns the findings.
#
# WHAT IT DOES NOT PROVE. It shows a target voice is reachable *by rewriting*,
# not that the writer will hit it first time from the bundle. Whatever wins here
# must be folded into `WRITER_VOICE` and validated with a from-scratch
# generation before it is trusted for a backfill.

RESTYLE_CONTRACT = """You are rewriting an existing, finished golf tournament report to change \
its VOICE ONLY.

NON-NEGOTIABLE — this is a restyle, not a rewrite:
- DO NOT change any fact: holes, scores, players, par values, weekdays, stroke indexes, course \
names, records, margins, totals. Every number stays exactly as written.
- DO NOT change the structure: same sections, same headings, same order, same length or slightly \
shorter.
- DO NOT add or remove events. If it is not in the text you were given, it does not exist.
- DO NOT add weekday names anywhere they do not already appear.

Everything below describes the voice you are writing IN. Apply it to the existing sentences."""


def restyle_voice(teg_num: int, voice_prompt: str, label: str, *,
                  source_label: Optional[str] = None,
                  model: Optional[str] = None,
                  verify: bool = True,
                  style: bool = True) -> dict:
    """Rewrite a finished report's voice and save it under a variant name.

    Args:
        teg_num: which TEG.
        voice_prompt: the voice instructions for this variant. Composed with the
            restyle contract and the shared `WRITER_FAITHFULNESS` block, so the
            guardrails are the *same constant* the main writer uses and cannot
            drift out of step with it.
        label: variant name, e.g. `"drier"`. Writes
            `teg_N_report_{label}.md` (+ `_styled.md`). Refuses labels that would
            overwrite the canonical files.
        source_label: read from `teg_N_report_{source_label}.md` instead of
            `report_final.md` — for chaining or for re-styling another variant.
        verify: run D3 over both the source and the output, and report which
            findings are NEW (default True). A restyle inherits whatever faults
            the source already had, so the raw finding list is misleading — the
            question that matters for an extra prose pass is whether *this* pass
            introduced anything. That is `new_findings`.
        style: also write the styled variant, so it is directly comparable
            line-for-line with `report_styled.md` (default True).

    Returns {teg, label, source_path, output_path, styled_path, usage,
    findings, new_findings}.
    """
    import os

    from teg_analysis.reporting.render import style_text
    from teg_analysis.reporting.verify import verify_report

    label = _variant_label(label)

    src_name = f"report_{source_label}" if source_label else "report_final"
    source_path = f"{output_dir()}/teg_{teg_num}_{src_name}.md"
    if not os.path.exists(source_path):
        # Several TEGs have had their report_final.md consumed into variant
        # filenames by past experiments (TEGs 10, 11, 13, 14, 18 as of
        # 2026-08-11) — including 14 and 18, the usual anchors for a voice A/B.
        # Listing the real alternatives is more useful than "not found".
        import glob
        import re as _re
        prefix = f"{output_dir()}/teg_{teg_num}_report_"
        available = sorted(
            _re.sub(r"\.md$", "", os.path.basename(p)[len(os.path.basename(prefix)):])
            for p in glob.glob(f"{prefix}*.md")
            if not p.endswith("_styled.md"))
        raise FileNotFoundError(
            f"{source_path} not found — TEG {teg_num} has no finished report to "
            f"rewrite.\nPass source_label= one of: {available}\n"
            f"'A_around_draft' is usually the right choice (the pre-lint text).")

    with open(source_path) as f:
        source_text = f.read()

    system = (RESTYLE_CONTRACT + "\n\n" + voice_prompt.strip() + "\n\n"
              + WRITER_FAITHFULNESS + "\n" + WRITER_OUTPUT_RULE)
    text, usage = llm.generate_text(system, source_text,
                                    model=model or llm.DEFAULT_MODEL,
                                    max_tokens=16000,
                                    stage="restyle", label=f"teg{teg_num}")
    text = _strip_beat_ids(text)

    output_path = f"{output_dir()}/teg_{teg_num}_report_{label}.md"
    with open(output_path, "w") as f:
        f.write(text)

    styled_path = None
    if style:
        styled_path = f"{output_dir()}/teg_{teg_num}_report_{label}_styled.md"
        with open(styled_path, "w") as f:
            f.write(style_text(teg_num, text))

    findings: list = []
    new_findings: list = []
    if verify:
        found = verify_report(teg_num, text=text)
        findings = [str(f) for f in found]
        # Faults the source already had are not this pass's doing. What matters
        # is whether rewriting introduced one — that is the exact failure that
        # got the critique-revise variant rejected.
        #
        # Match on (rule, detail), NOT str(f): str() embeds the excerpt, and a
        # restyle rewrites the prose around a fault by definition, so the
        # excerpt shifts and an inherited fault was being blamed on the pass.
        # `Finding` documents rule as stable and detail as human-facing; both
        # survive a rewrite of the surrounding sentence. Counter, not set, so
        # that a fault the source had once and the output has twice still
        # reports one new instance.
        def _key(f):
            return (f.rule, f.detail)

        before = Counter(_key(f) for f in verify_report(teg_num, text=source_text))
        new_findings = []
        for f in found:
            k = _key(f)
            if before[k]:
                before[k] -= 1          # accounted for by the source
            else:
                new_findings.append(str(f))
        if new_findings:
            print(f"[restyle_voice] WARNING TEG {teg_num} ({label}): "
                  f"{len(new_findings)} NEW fault(s) introduced by this pass:")
            for s in new_findings:
                print(f"  {s}")
    return {"teg": teg_num, "label": label, "source_path": source_path,
            "output_path": output_path, "styled_path": styled_path,
            "usage": usage, "findings": findings, "new_findings": new_findings}


# ===========================================================================
# Writing a variant FROM THE DRY DRAFT — the other half of the voice loop
# ===========================================================================
# `restyle_voice` above rewrites a FINISHED report. That holds facts and
# structure literally constant, which makes it the tightest A/B, but it only
# proves a voice is reachable by rewriting. This one runs the REAL writer over
# the frozen dry draft — the same call production makes — so it proves the
# pipeline can reach the voice cold.
#
# It is a thin wrapper over `report_around_draft`, not a parallel path. The
# prompt assembly, the user message and the model call are production's. What
# this adds is the ergonomics: load the frozen inputs, refuse a label that
# would clobber the chain, then style and verify the result.
#
# STILL AN EXPERIMENT LEVER. Nothing in the default chain calls it, and it
# cannot write `report_final.md`, `report_styled.md` or the chain's own
# `A_around_draft` intermediate. Promotion is a deliberate, separate act:
# fold the winning voice into `WRITER_VOICE` and re-run the backfill.
def write_from_dry(teg_num: int, voice: Optional[str], label: str, *,
                   plan_scope: str = "arc",
                   bundle_context: Union[bool, str] = False,
                   model: Optional[str] = None,
                   lint: bool = True,
                   style: bool = True,
                   verify: bool = True) -> dict:
    """Write a variant report from TEG `teg_num`'s frozen dry draft in `voice`.

    Args:
        voice: a COMPLETE description of the register to write in. It REPLACES
            the house voice rather than modifying it, so write it as a
            standalone brief ("VOICE: plain broadsheet match report. …"), not
            as a delta ("drier than usual"). Pass None to run the house voice
            through the same path — the control case for any comparison.
        label: variant name. Writes `teg_N_report_{label}.md` (+ `_styled`).
        plan_scope: how much story plan goes in with the draft. `"arc"`
            (default) adds the narrative vehicles and story-arc fields, so the
            report has a shape to follow; `"none"` sends the dry draft alone,
            isolating the voice completely; `"full"` matches production.
        bundle_context: add the structured venue / career-history / win-anatomy
            block. Pair with `plan_scope="none"` when you want the full material
            with none of the plan's pre-written phrasing. Pass `"data"` instead
            of `True` for a packet with no sentences in it at all — see the
            arithmetic warning on `report_around_draft`.
        lint: run the repetition lint, as the production chain does (default
            True, so the output is comparable with `report_styled.md`). Turn it
            off to see the writer's unmediated prose.

    Returns {teg, label, voice_is_house, plan_scope, output_path, styled_path,
    usage, findings}.
    """
    from teg_analysis.reporting.render import style_text
    from teg_analysis.reporting.verify import verify_report

    label = _variant_label(label)
    plan = load_story_plan(teg_num)
    dry = load_dry_draft(teg_num)

    rpt = report_around_draft(teg_num, plan, dry, model=model,
                              voice=voice, label=label, plan_scope=plan_scope,
                              bundle_context=bundle_context)
    text, usage = rpt["text"], [rpt["usage"]]

    if lint:
        text, lint_usage = repetition_lint(text, label=f"teg{teg_num}_{label}")
        usage.append(lint_usage)
        _write(teg_num, label, text)

    styled_path = None
    if style:
        styled_path = f"{output_dir()}/teg_{teg_num}_report_{label}_styled.md"
        with open(styled_path, "w") as f:
            f.write(style_text(teg_num, text))

    findings: list = []
    if verify:
        findings = [str(f) for f in verify_report(teg_num, text=text)]
        if findings:
            # A fault here usually means the voice pulled the writer into
            # fabrication, not that it is a stylistic near-miss. Worth seeing
            # before you form a view on the prose.
            print(f"[write_from_dry] TEG {teg_num} ({label}): "
                  f"{len(findings)} finding(s):")
            for s in findings:
                print(f"  {s}")

    return {"teg": teg_num, "label": label, "voice_is_house": voice is None,
            "plan_scope": plan_scope, "bundle_context": bundle_context,
            "output_path": rpt["output_path"],
            "styled_path": styled_path, "usage": usage, "findings": findings}
