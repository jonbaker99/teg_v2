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


# Default — current behaviour (light). Switch per call via `dry_draft_style` on
# `generate_dry_draft`. The detailed variant restores the pre-Step-2 wording (one
# section per round, render specific holes wherever the evidence supports it).
DRY_DRAFT_SYSTEM = DRY_DRAFT_SYSTEM_LIGHT


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
(Guardian), Tom Peck (Times political sketches), Jesse Armstrong (Succession), \
and Armando Iannucci (The Thick of It). British English. No exclamation marks. \
No obvious puns. No wacky tropes.

Core mechanism — subverted gravitas: treat every score, every hole, every lurch up or down
the leaderboard with the unblinking solemnity of a Shakespearean tragedy or a geopolitical
crisis. You are a war correspondent documenting an inevitable, slow-motion disaster. The
humour lives in the gap between the gravity of the prose and the lowness of the stakes.
Never wink at the camera.

Named principles — hold to these:
1. Characters are people taking something they shouldn't take seriously with utter, doomed
   seriousness. Render that honestly.
2. Bathos and deadpan are the engine: grand self-conception meets squalid scorecard. State
   the catastrophic thing without escalating it. Let the scorecard win.
3. Trust the reader. State the implication; don't explain it.
4. Balance the ledger with the emotional landscape. The reader already has the scorecard, so
   do not simply read it back to them. Blend the necessary raw data with abstract,
   character-driven observation to give the numbers narrative weight.
5. Avoid scoring redundancy. Never use the gross score, the relation to par, and the par of
   the hole all at once. Two is enough. For example, use "A 10 on the par-5 13th," "A
   quintuple bogey on the par-5 13th," or "A quintuple bogey 10 on the 13th" — but never
   "A quintuple bogey 10 on the par-5 13th."
6. Precise, specific, earned. No generic "catastrophic collapse" — name the hole, the score,
   the exact moment the wheels came off.
7. Trace the player arc within the round. Bathos works in both directions: the man who
   started brilliantly and then fell apart; the man who scraped back from early disaster.
   The shape of the card is the character.
8. Achievements earn their moment too. The personal best, the eagle, the round of the day —
   rendered with the same solemnity as the disasters. If bathos turns low stakes into tragedy,
   it can equally turn low stakes into triumph. Wry, never gushing; specific, never hollow.

STRUCTURE — follow the STORY PLAN you are given:
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
`opening_hook` if it's set to something other than chronological.
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
- **The report MUST END with a player-by-player section** — 4–6 short bullets, one \
or two sentences per principal player, drawing on the plan's `players[]` arcs AND \
the moments you've narrated. Use a heading like `## The men, in brief` (or similar). \
This closing is non-negotiable; do not omit it.

PALETTE — context vehicles to pull on. **At least ONE must be prominent in the report \
(featured in the opener AND threaded through the body); multiple are welcome where each \
genuinely lands; the one-prominent rule is non-negotiable.** None of (a)-(g) is itself \
mandatory; the choice is yours, informed by the plan's `prominent_vehicle` and what's \
most interesting about THIS tournament.

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
it resolves. The closing "men in brief" earns its place by collecting these.

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
- Vary sentence rhythm; let a short sentence land a point.
- **Stroke index (SI) for hole colour.** Beat hole evidence may include an `si` field. \
Use it sparingly as optional colour: SI 1 = "the hardest hole on the course"; SI 18 = \
"the easiest"; SI 2–3 = "one of the hardest"; SI 16–17 = "one of the easiest". \
SI 4–15: not noteworthy — ignore. Only invoke it when it sharpens the irony or drama \
(a birdie on the hardest hole; a double on the give-away). Don't mention SI on every hole.

ECONOMY — sentence- and paragraph-level mechanics. Write tight on the first pass; \
these are construction rules, not a fix-up checklist. The bathos principle still holds: \
long sentences that earn their length stay long. But length without earned facts or \
images is bloat, and prose that drowns its own punchline is a bigger problem than prose \
that lands it cleanly.

1. **Em-dash discipline.** Two em-dashes per paragraph is the ceiling. If a third \
wants in, refactor one aside into a separate sentence or strip it.
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
with "—", "who", or a relative clause and each part would stand alone, split them. \
Test: would a full stop after the first part lose meaning? If not, use one.
8. **One aside form per sentence.** Don't stack asides; only stack when the second \
aside IS the joke.
9. **Compressed rhythmic lists; bogey shorthand.** Sequences of same-type events read \
better compressed: "quad, triple, double, double", not "quadruple-bogey 8, triple-bogey \
7, double-bogey 6, double-bogey 6". In general prose, "double" and "triple" are \
acceptable shorthand for double- and triple-bogey when context is clear (this is \
shorthand, not redundancy — Principle 5 still governs whether to pair the term with par \
and stroke count).
10. **Punchline isolation.** Short payoff sentences — reversals, bathos kickers, the \
number that lands — belong as their own paragraph. Attached to a long preceding \
sentence they get absorbed.
11. **One dominant idea per paragraph.** A shift in subject, tone, or beat is a signal \
to start a new paragraph. If a paragraph is doing too much, break it at the natural seam.

FAITHFULNESS (non-negotiable):
- Use ONLY the supplied facts. Never invent holes, scores, players or events. If it isn't \
in the data, leave it out.
- **NEVER include beat IDs in the prose.** Beat references like `b07`, `cr01`, `(b13, b14)` \
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
NEVER write a "men in brief" bullet — or any prose — for a player who did not play this \
TEG. If a player you'd expect to see is absent, they are absent; don't note their absence, \
don't include them.
- **PLAYER RELATIONSHIPS — only those in the bundle.** The bundle's \
`player_relationships` field lists verified ties (e.g. "Alex Baker and Jon Baker are \
brothers"). You may reference these. **DO NOT INFER ANY OTHER RELATIONSHIPS from \
shared surnames or any other signal.** Two players named Baker are NOT cousins, \
uncle and nephew, or any other connection unless the bundle says so. If `player_relationships` \
is empty, every player in the field is unrelated as far as the report is concerned. \
Inventing relationships is a fabrication of the same kind as inventing scores.
- **Every beat id in the plan's `must_include_beat_ids` MUST be covered in the prose** \
— not just hinted at. These are the spine + TEG records + personal bests + rare feats \
(holes-in-one, eagles, all-time top-3 rounds, big blow-ups). Skipping any is the most \
visible kind of omission. A deterministic "PBs and TEG records" appendix is also \
auto-appended to the styled output as a safety net.
- Honour the data precisely: where a rival "drew level" rather than taking the lead \
outright, say so — do not inflate it into a lead change.
- Each round is played on a specific course (every beat carries its `course`; see also \
the venue). The same hole NUMBER in different rounds is a DIFFERENT hole, almost always \
on a different course — NEVER call them "the same hole" or invent a "same-hole" \
rhyme/parallel. If you draw a parallel between two holes, make explicit they are \
different holes and name the courses.
- Early-round lead changes, when the field is bunched, are normal — do NOT frame routine \
opening jockeying as "chaos" or high drama. The lead changes that matter are the late ones.
- The Trophy metric is `trophy_metric` in the bundle: Stableford points (higher is \
better) for TEG 8+, or net-vs-par (lower is better, signed) for TEGs 1–7. Gross is \
raw strokes vs par. Don't conflate them.
- **Stableford and Gross measure DIFFERENT things** — Stableford is handicap-adjusted, \
Gross is raw shots. A higher-handicap player can lead the Trophy and trail the Jacket; a \
lower-handicap player vice versa. This is **normal handicapping, not paradox**. NEVER \
frame a player's split between the two competitions as schizophrenic, contradictory, a \
"unique double", impossibly strange, or any kind of head-scratcher — it is the ordinary \
mechanics of the scoring system. State both facts plainly; the shape can still be \
interesting (e.g. Jacket runner-up while bottom of the Trophy), but it is not weird.
- **TEG has NO countback, NO tiebreakers, NO playoff.** All competitions are decided \
by accumulated points (Stableford / Gross). Lead changes happen because a player \
accumulated more points than another. Never invent "countback", "countback math", \
"tiebreaker", "playoff" or similar — those mechanisms do not exist in TEG.
- **Arithmetic must be exact.** When asserting an over-par total across a stretch of \
holes, the figure must equal the precise sum of per-hole over-par (bogey = +1, double \
= +2, triple = +3, quad = +4, quint = +5, sext = +6). If you echo a total from the dry \
draft, check it against the per-hole evidence first. Wrong arithmetic is the most \
obvious fabrication the players will catch.

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

TIGHTEN_SYSTEM = """You are tightening an existing golf tournament report. The voice \
(deadpan / gravitas / wit, in the spirit of Barney Ronay, Tom Peck, Jesse Armstrong, \
Armando Iannucci) is already correct. Your job is to sandpaper specific over-built \
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
- Closing payoff sentences (paragraph punchlines, kicker lines of "men in brief" bullets).
- Player relationships exactly as in the source (Bakers are brothers, Pattersons are \
brothers; do not invent or change any others).

DEFAULT: change only what you must. This is not a rewrite. The output should read as \
the same voice writing more cleanly, not a different voice writing cleaner.

Output the complete tightened report as markdown — no preamble, no commentary, same \
structure, same headings, same length or slightly shorter."""


ENRICH_SYSTEM = """You are enriching an existing golf tournament report with cross-TEG \
historical colour. The report is already written; your job is a targeted insert pass only.

VOICE: faithful, entertaining, tongue-in-cheek — in the spirit of Barney Ronay \
(Guardian), Tom Peck (Times political sketches), Jesse Armstrong (Succession), \
and Armando Iannucci (The Thick of It). British English. No exclamation marks. \
No obvious puns. No wacky tropes.

Core mechanism — subverted gravitas: treat every achievement with the unblinking solemnity \
of a Shakespearean tragedy or a geopolitical crisis. The humour lives in the gap between \
the gravity of the prose and the lowness of the stakes. Never wink at the camera.

Named principles — hold to these:
1. Characters are people taking something they shouldn't take seriously with utter, doomed \
   seriousness. Render that honestly.
2. Bathos and deadpan are the engine: grand self-conception meets squalid scorecard. State \
   the momentous thing without escalating it. Let it land on its own.
3. Trust the reader. State the implication; don't explain it.
4. Achievements earn their moment too. A "first Trophy" should feel nine years overdue; a \
   three-peat should carry the weight of something no one expected and nobody can quite \
   explain; a Wooden Spoon repeat should be rendered with the quiet resignation of a man \
   who has begun to suspect the universe has a grudge.

YOUR TASK:
Weave 3–7 of the supplied ACHIEVEMENT PHRASES into the existing report where they fit \
naturally. These phrases are pre-verified factual anchors. Expand each into a clause or \
half-sentence that matches the voice and rhythm of the surrounding prose, or add a single \
new sentence where the existing structure clearly leaves a gap.

RULES:
- DO NOT rewrite paragraphs or restructure the report. Insert phrases INTO existing \
  sentences, append a clause to the end of a sentence, or occasionally add a single short \
  new sentence. The structure — all headings, all sections, all closing bullets — must \
  remain intact.
- DO NOT invent any history, win counts, streaks, or statistics not in the supplied phrases. \
  The supplied phrases are the only historical facts you may use; everything else is already \
  in the report.
- DO NOT add parenthetical asides or meta-commentary. Do not write "notably, this was his \
  second…" or "for the record, he had…" — integrate as if it was always there, woven into \
  the sentence as naturally as the hole number.
- If a phrase has already been expressed in the existing report prose (e.g. the report \
  already says "his third straight win"), SKIP that supplied phrase — no doubling.
- Match the register. If the existing sentence is deadpan and understated, your insert must \
  be deadpan and understated. Do not inject levity into a sombre passage or gush into a \
  dry one.
- If fewer than 3 supplied phrases fit naturally, insert only those that do. Do not force \
  unnatural inserts to hit a number.
- Return the COMPLETE modified report — all content, all headings, all sections, all player \
  bullets, unchanged except for the additions. The output length should be close to the \
  input length plus the inserts.

FAITHFULNESS (non-negotiable):
- Use ONLY the supplied achievement phrases as new historical facts. Add nothing else.
- TEG has NO countback, NO tiebreakers, NO playoff. Do not introduce these mechanisms.
- British English. No exclamation marks.

VOICE GUIDANCE FOR SPECIFIC ACHIEVEMENTS:
- "First Trophy win" → e.g. "claimed his first Trophy, a development that arrived, one felt, \
  approximately nine years overdue" — not "he won for the first time"
- "Back-to-back Trophies" → render with appropriate gravity — e.g. "making it back-to-back \
  Trophies, a fact that the room seemed, for a moment, genuinely unsure how to absorb"
- "Three-peat / third consecutive Trophy" → "a third consecutive Trophy, a feat of sustained \
  dominance that sat somewhere between the unprecedented and the faintly alarming"
- "Zero to hero" → e.g. "from the Wooden Spoon twelve months prior to the Trophy itself — \
  a journey that suggested either remarkable resilience or a profoundly unreliable scoring system"
- "First Trophy after N prior runner-up finishes" → render the wait with appropriate irony \
  about its arrival being overdue; the relief is as heavy as the achievement. **Vary the \
  framing — don't lock onto "bridesmaid". Alternatives: "the nearly-man finally arrives", \
  "second twice and now first", "two near-misses made good", "the wait ends", etc. Reuse of \
  the same framing across players or reports is a tell.**
- "Milestone first" (first player in history to win N Trophies) → treat as a historical \
  weight the room has only just caught up with — understated, not triumphant
- "Hero to zero / from champion to Spoon" → deadpan; the contrast does the work
- "Back-to-back Spoons" → quiet tragedy; the man who has done it once now finding, to no \
  one's particular surprise, that he has done it again"""


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
                                    model=model or llm.DEFAULT_MODEL, max_tokens=16000)
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
                                    model=model or llm.DEFAULT_MODEL, max_tokens=16000)
    return {"text": text, "usage": usage, "output_path": _write(teg_num, "A_around_draft", text)}


def report_critique_revise(teg_num: int, plan: Union[StoryPlan, dict],
                           mode: str = "balanced", tone: str = "house",
                           model: Optional[str] = None) -> dict:
    """Approach C: single-pass draft, then a self-critique-and-revise pass."""
    bundle, _ = assemble_bundle(teg_num, mode=mode, tone=tone)
    draft_user = _build_author_input(plan, bundle) + "\n\nWrite the finished report now."
    draft, u1 = llm.generate_text(WRITER_SYSTEM, draft_user,
                                  model=model or llm.DEFAULT_MODEL, max_tokens=16000)
    revise_user = ("STORY PLAN:\n" + _plan_to_text(plan)
                   + "\n\nYOUR FIRST DRAFT:\n" + draft
                   + "\n\nRevise it per your instructions. Output only the improved report.")
    final, u2 = llm.generate_text(REVISE_SYSTEM, revise_user,
                                  model=model or llm.DEFAULT_MODEL, max_tokens=16000)
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


def repetition_lint(text: str, model: str = "claude-haiku-4-5") -> Tuple[str, object]:
    """Narrow final pass: kill repeated/over-used words only. Returns (text, usage).

    Defaults to Haiku 4.5 — the lint is a mechanical copy-edit (no reasoning), so the
    cheap model is appropriate. `thinking=False` because Haiku doesn't support
    adaptive thinking. Pass `model=` to override.

    Also runs `_strip_beat_ids` after the LLM lint to mechanically remove any
    leaked beat-ID references (`b07`, `(cr01)`, etc.) that slipped through the
    writer prompt rule.
    """
    linted, usage = llm.generate_text(LINT_SYSTEM, text, model=model, max_tokens=16000, thinking=False)
    return _strip_beat_ids(linted), usage


def tighten_prose(text: str, model: str = "claude-sonnet-4-6") -> Tuple[str, object]:
    """One-off prose density pass: trim em-dash stacks, run-ons, content-free preambles.

    Returns (text, usage). Does not touch facts, voice, or structure.
    Defaults to Sonnet 4.6 — needs judgement to distinguish bathos from bloat.
    """
    tightened, usage = llm.generate_text(TIGHTEN_SYSTEM, text, model=model, max_tokens=16000, thinking=False)
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


def enrich_report_with_history(teg_num: int, model: Optional[str] = None) -> dict:
    """LLM enrichment pass: weave cross-TEG historical colour into an existing report.

    Reads teg_N_report_final.md, computes achievement phrases from prior history,
    calls the LLM to weave them in (using ENRICH_SYSTEM), writes back to
    teg_N_report_final.md, and re-runs style_report to regenerate the styled version.

    Returns {"teg": teg_num, "enriched": bool, "usage": ..., "output_path": ...}
    """
    import os
    from teg_analysis.reporting.history_context import build_history_enrichment_context
    from teg_analysis.reporting.render import style_report

    report_path = f"{OUTPUT_DIR}/teg_{teg_num}_report_final.md"
    if not os.path.exists(report_path):
        return {"teg": teg_num, "enriched": False, "usage": None,
                "error": "report_final.md not found"}

    with open(report_path) as f:
        report_text = f.read()

    context = build_history_enrichment_context(teg_num)
    if not context or not context.get("per_player"):
        return {"teg": teg_num, "enriched": False, "usage": None}

    phrases_by_player = {
        player: data["achievement_phrases"]
        for player, data in context["per_player"].items()
        if data.get("achievement_phrases")
    }
    if not phrases_by_player:
        return {"teg": teg_num, "enriched": False, "usage": None}

    context_json = json.dumps({
        "trophy_winner": context["trophy_winner"],
        "jacket_winner": context["jacket_winner"],
        "spoon_holder": context["spoon_holder"],
        "achievement_phrases_by_player": phrases_by_player,
    }, indent=2, ensure_ascii=False)

    user = (
        "EXISTING REPORT:\n\n" + report_text
        + "\n\n---\nACHIEVEMENT PHRASES TO WEAVE IN:\n\n" + context_json
        + "\n\n---\nReturn the complete enriched report."
    )

    text, usage = llm.generate_text(
        ENRICH_SYSTEM, user,
        model=model or "claude-sonnet-4-6",
        max_tokens=16000,
    )

    with open(report_path, "w") as f:
        f.write(text)

    style_report(teg_num)

    return {"teg": teg_num, "enriched": True, "usage": usage, "output_path": report_path}
