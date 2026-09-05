"""Stage 3: the story plan (LLM, structured output).

The missing editorial layer. Given the Stage-2 scored beats + competition arcs +
venue context, an LLM produces a STRUCTURED PLAN (not prose): the theme/spine,
foreshadowing hooks, per-round witty headline candidates, must-include beats and
explicit cuts, player arcs, and venue notes. This is the steerable artefact —
archive mode lets a human edit the plan before the writer runs; fast mode passes
it straight through.

`dry_run=True` assembles and writes the exact prompt + input bundle WITHOUT an API
call, so the inputs can be validated with no key.
"""

from __future__ import annotations

import json
from typing import Literal, Optional, Tuple, get_args

from pydantic import BaseModel, Field

from teg_analysis.reporting.era import trophy_metric
from teg_analysis.reporting.events import build_notable_events
from teg_analysis.reporting.venue import build_venue_context
from teg_analysis.reporting import llm, prompts

from teg_analysis.reporting.paths import output_dir

_ARC_KEY = {"trophy_win": "trophy", "jacket_win": "jacket", "wooden_spoon": "spoon"}


# ---------------------------------------------------------------------------
# Shared editor↔writer vocabulary — THE single source of truth
# ---------------------------------------------------------------------------
# These terms were previously spelled out independently in two ~15k-char prose
# prompts with no enforcement, which let `prominent_vehicle` be specified twice
# with two DIFFERENT vocabularies: the field spec said "pick a palette vehicle"
# while the close-finish HARD RULE demanded `counterfactual`/`dual_narrative`
# from the narrative-vehicle menu. The editor resolved that collision in favour
# of the field spec every time, so the hard rule never once fired correctly.
#
# The fix is structural, not editorial: the vocabulary lives here, the prompt
# menus are GENERATED from it, and the schema types below are `Literal`s built
# from the same constants. A collision is now a validation error at generation
# time instead of a silent wrong answer.
#
# Consequence worth knowing: the editor can no longer invent an unlisted vehicle
# name. That freedom is what allowed the drift; adding a vehicle now means adding
# it here, which updates the schema and both prompts at once.

# How the report is sequenced.
#
# `reverse_chronology` ("start at the result, walk backwards through cause") was
# removed 2026-08-13: tested on TEG 18 and read as confusing rather than clever —
# the reader has to hold an unexplained tableau in mind through a full round
# section before the setup pays off, and by the time it does the payoff has
# already been spoiled by the opener. Don't reintroduce without a concrete fix
# for that ordering problem.
NARRATIVE_STRUCTURES: dict[str, str] = {
    "chronological":       "straight tournament timeline; R1 → R4",
    "in_medias_res":       "open mid-action, then loop back",
    "theme_led":           "body organised around an idea, not rounds",
    "three_act":           "setup / confrontation / resolution",
    "player_by_player":    "one section per player rather than per round",
}

# The storytelling FRAME. Grouped for scanning only — the groups carry no
# precedence. `prominent_vehicle` must be one of these.
NARRATIVE_VEHICLES: dict[str, dict[str, str]] = {
    "TOURNAMENT-SHAPE (what happened over the four days)": {
        "counterfactual":  'close / decided late ("but for X, Y would have won")',
        "dual_narrative":  "two players' weeks intertwined",
        "tragic_arc":      "protagonist's collapse drove the tournament (within THIS tournament, not career)",
        "redemption_arc":  "a player recovers from an early disaster — a blow-up hole or a ruinous round — to finish well (within THIS tournament; the career-level equivalent is `comeback` below)",
        "motif":           "a recurring image / hole / number carried as connective tissue",
        "bookends":        "open and close at the same scene / hole / moment",
        "ensemble":        "the field collectively; course as protagonist",
        "catalogue":       "inventory of a recurring failure mode",
        "inevitability":   ("wire-to-wire procession (NOTE: SUPPORTING vehicle only — never "
                            "`prominent_vehicle`; processions come through in the telling, "
                            "not the framing)"),
    },
    "HISTORICAL-CONTEXT (the framing around the result)": {
        "hero_arc":        "protagonist's career trajectory carries the report",
        "comeback":        "long drought / redemption (first win since TEG N, etc.)",
        "inversion":       "reigning holder dethroned / previous-loser elevated",
        "origin":          "first win / debut / breakthrough",
        "underdog":        "unlikely triumph from prior history",
    },
    "STYLISTIC (how to tell, pure judgement)": {
        "theme_led_body":  "body organised around an idea, not rounds",
    },
}

# The CONTEXT MATERIAL the writer foregrounds. A different axis from the frame:
# a report can be framed `counterfactual` while foregrounding `cross_teg_career`.
# Mirrors the PALETTE (a)-(g) block in `authoring.WRITER_SYSTEM`.
PALETTE_VEHICLES: dict[str, str] = {
    "cross_teg_career":  "career storylines across TEGs (Nth win, back-to-back, drought)",
    "course_history":    "per-player history on this specific course",
    "venue_character":   "the course / venue as a character in the telling",
    "decisive_moment":   "the moment the result was effectively decided, + counterfactual",
    "player_thread":     "one player's thread followed through the whole tournament",
    "records":           "records and rare feats woven into the prose",
    "foreshadow_payoff": "a seed planted early and paid off later",
}

_ALL_VEHICLES = tuple(v for group in NARRATIVE_VEHICLES.values() for v in group)

NarrativeStructure = Literal[tuple(NARRATIVE_STRUCTURES)]          # type: ignore[misc]
NarrativeVehicle = Literal[_ALL_VEHICLES]                          # type: ignore[misc]
PaletteVehicle = Literal[tuple(PALETTE_VEHICLES)]                  # type: ignore[misc]

# `inevitability` is explicitly a supporting vehicle only (see its note above).
PROMINENT_VEHICLE_CHOICES = tuple(v for v in _ALL_VEHICLES if v != "inevitability")
ProminentVehicle = Literal[PROMINENT_VEHICLE_CHOICES]              # type: ignore[misc]

# Vehicles that satisfy the close-finish HARD RULE.
CLOSE_FINISH_VEHICLES = ("counterfactual", "dual_narrative")


def _render_structure_menu() -> str:
    return "\n".join(f"    - `{k}`{' ' * max(1, 20 - len(k))}— {v}"
                     for k, v in NARRATIVE_STRUCTURES.items())


def _render_vehicle_menu() -> str:
    blocks = []
    for group, items in NARRATIVE_VEHICLES.items():
        lines = [f"  {group}:"]
        lines += [f"    - `{k}`{' ' * max(1, 20 - len(k))}— {v}" for k, v in items.items()]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _render_palette_menu() -> str:
    return " | ".join(f"`{k}`" for k in PALETTE_VEHICLES)


# ---------------------------------------------------------------------------
# Output schema (what the LLM must return)
# ---------------------------------------------------------------------------
class Competition(BaseModel):
    """Just the name + winner, for the at-a-glance box (`render._build_at_a_glance`
    reads only these two fields). `how`/`key_beat_ids` were dropped 2026-08-18 —
    unused downstream and duplicated by `trophy_storyline`/`jacket_storyline`/
    `spoon_storyline`'s `shape`/`beat_ids`, which is where that detail now lives.
    Also shrinks the schema: the API rejected the plan schema as "too large" once
    the storyline fields were added (see StoryPlan docstring)."""
    name: str                       # "Trophy" | "Green Jacket" | "Wooden Spoon"
    winner_or_loser: str


class RoundPlan(BaseModel):
    round: int
    headline_candidates: list[str]  # ~3 witty options
    chosen_headline: str
    angle: str                      # one line: what this round is about
    beat_ids: list[str]


class PlayerArc(BaseModel):
    player: str
    arc: str


class Payoff(BaseModel):
    """Explicit setup→payoff pair: a foreshadow seed and the section that resolves it.

    Addresses the foreshadow-without-payoff thinness identified in prior reports:
    seeds get planted in the opener but the body never resolves them. Each
    `foreshadow[]` seed should have a corresponding `payoffs[]` entry.
    """
    seed: str           # short reference to the seed planted in foreshadow[]
    resolves_in: str    # which section pays it off (e.g. "Round 3", "Player-by-player summary", "How it was decided")
    payoff: str         # one-line description of how it resolves


class DraftedStoryline(BaseModel):
    """A narrative thread with a real shape, grounded in specific beats.

    Schema proven in `scripts/storyline_experiment.py`'s A/B (2026-08-18,
    STORYLINE_PLAN.md): a cold discovery call (beats + arcs only, no
    `candidate_threads` / `win_anatomy` advisory) using this shape beat a
    hinted one on lead clarity, subplot quality and factual grounding on all
    3 test TEGs. Replaces the unconsumed `competition_storyline_bullets` /
    `player_storyline_bullets` / `decisive_moments` fields (zero downstream
    readers — dead code, found during this replacement).
    """
    subject: str            # who/what this storyline is about
    why_it_matters: str     # one sentence
    shape: str              # setup -> turn -> resolution, 2-3 sentences
    beat_ids: list[str]     # the specific beats this is built from — checked
                            # against the bundle by `check_plan_consistency`
    compelling_score: int = Field(ge=1, le=10)  # your own rating of how GOOD A
                            # STORY this is — not how much it mattered to the standings
    humour_score: int = Field(ge=1, le=10)  # your own rating of how genuinely FUNNY
                            # this storyline is to tell — not how dramatic or important.
                            # See the humour requirement in SYSTEM_PROMPT.


class VehicleFitResponse(BaseModel):
    """The editor's answer to the `vehicle_fit_hints` advisory — accountable,
    not binding.

    The hints are a heuristic over the raw ingredients of a pattern; they
    cannot tell whether that pattern is the most interesting angle, and four
    vehicles have no detector at all (`vehicle_fit.UNSCORED_VEHICLES`). So the
    editor stays free to frame the report however the material demands.

    What this field adds is a record of the decision, not a constraint on it.
    Deliberately NOT phrased as a justification the editor owes when it
    diverges: making divergence costly would push every plan toward whichever
    vehicles happen to be detectable, which is the opposite of the variety the
    scorer exists to serve. Ignoring a strong hint is a legitimate call; making
    it silently is what this prevents.
    """
    top_scored_vehicle: NarrativeVehicle   # highest-ranked entry in vehicle_fit_hints
    taken_up: bool                         # is it in narrative_vehicles?
    note: str                              # one line: why it fits, or what beat it


class StoryPlan(BaseModel):
    title: str
    title_candidates: list[str]
    theme: str                      # the one-line through-line / spine
    tone: str                       # resolved register for this report
    narrative_structure: NarrativeStructure   # enum — see NARRATIVE_STRUCTURES
    opening_hook: str               # one-line description of what the report opens with (and why)
    narrative_vehicles: list[NarrativeVehicle] = []  # 1-3 frames — see NARRATIVE_VEHICLES
    foreshadow: list[str]           # hooks to plant early that pay off later
    competitions: list[Competition] # Trophy, Green Jacket, Wooden Spoon (priority order)
    rounds: list[RoundPlan]
    players: list[PlayerArc]
    must_include_beat_ids: list[str]
    cuts: list[str]                 # beat ids (or notes) to deliberately leave out
    venue_notes: str
    course_history_notes: list[str] = []                       # per-course-history beats worth foregrounding
    # --- Storyline discovery (2026-08-18) ---
    # Mandatory Trophy/Jacket/Spoon storylines (baseline material for "how the
    # trophies were won", and a bar to judge discovered_storylines against —
    # Jon's framing, STORYLINE_PLAN.md) plus 1-3 independently-discovered ones.
    # Replaces `competition_storyline_bullets` / `player_storyline_bullets` /
    # `decisive_moments` — same job, but grounded (every beat_id checked
    # against the bundle) rather than free-text bullets nothing verified.
    trophy_storyline: DraftedStoryline
    jacket_storyline: DraftedStoryline
    spoon_storyline: DraftedStoryline
    discovered_storylines: list[DraftedStoryline] = Field(default_factory=list, max_length=3)
    # Fallback ladder (2026-08-19): what fills the body when nothing clears the
    # `discovered_storylines` bar. "none" (the common case) means the trophy/
    # jacket/spoon anatomy stories stand alone. "player_by_player" and
    # "round_by_round" sit at the SAME tier as each other, never above the
    # storylines approach — they exist only for when discovered_storylines is
    # empty or thin. See the fallback-ladder guidance in SYSTEM_PROMPT.
    body_fallback: Literal["none", "player_by_player", "round_by_round"] = "none"
    # Two DIFFERENT axes, previously collapsed into one free-string field — which
    # is what let the close-finish hard rule silently never fire. See the
    # vocabulary block at the top of this module. Both are REQUIRED: the prompt
    # always said "ALWAYS populated", and a required enum is how that is actually
    # enforced rather than merely requested.
    prominent_vehicle: ProminentVehicle        # the FRAME being foregrounded
    prominent_palette: PaletteVehicle          # the CONTEXT MATERIAL being foregrounded
    payoffs: list[Payoff] = []                                 # setup→payoff pairs; one per foreshadow seed where possible
    # Required, like the two prominence fields above and for the same reason:
    # a prose instruction to "record your reasoning" is a request, a required
    # field is enforcement. Checked against the bundle by
    # `check_plan_consistency`, so it cannot be filled in with a vehicle that
    # was not actually the top hint.
    vehicle_fit_response: VehicleFitResponse
    # Why the champion won, in one line, drawn from `win_anatomy` — the thing
    # Jon named as the single most important job of the report (2026-08-14).
    # Required because a report that never makes this clear has failed however
    # entertaining it is, and a required field is the only way to know the
    # editor actually decided rather than left it to emerge from the beats.
    why_the_champion_won: str
    # Only when departing from the Trophy-leads default; empty otherwise.
    storyline_note: str = ""


# ---------------------------------------------------------------------------
# System prompt (stable / cacheable)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are the editor planning a newspaper-style report on a TEG \
(an amateur golf tournament of several rounds). You do NOT write prose here — you \
produce a STRUCTURED PLAN that a writer will follow.

AUDIENCE: the players themselves — insiders who know each other, the courses, and \
the history. They will spot any factual error instantly, and they enjoy reliving \
the tournament and being gently ribbed.

""" + prompts.HOUSE_VOICE_SUMMARY + """
THE SPINE — the report is built around the three competitions, in this priority order:
1. The Trophy — the main event. The scoring metric varies by era: **Stableford** \
(higher is better) from TEG 8 onwards; **total net-vs-par** (lower is better, \
signed format like +47) for TEGs 1–7. Use the `trophy_metric` field in the bundle \
(`"stableford"` or `"net_vs_par"`) to choose the right framing and language.
2. The Green Jacket (Gross).
3. The Wooden Spoon (last place on the Trophy metric — Stableford for TEG 8+, \
net-vs-par for TEGs 1–7).
For each you MUST explain HOW it was won (or, for the Spoon, lost): the decisive \
moments, lead changes, and trajectory. Draw on the competition_arcs provided.

INPUT (JSON in the user turn):
- competition_arcs: leader-by-round, winner/loser trajectory, lead changes and the \
decisive moment for each competition.
- **win_anatomy: WHY each competition was won or lost.** Computed from the data, not \
inferred. Per competition: `attribution` (`built` = the winner outscored the runner-up \
and earned the margin; `inherited` = the runner-up shed more than the winner gained), \
`shape` (`consistent` vs `volatile` against the field's own spread), \
`best_in_field_rounds`, `below_median_rounds`, per-round standing vs the field, and \
whether the runner-up could have flipped it by merely playing their own average. \
`summary_facts` states all of this in neutral phrasing. **This is the single most \
important input for the primary storyline** — it answers "was the champion good, were \
the others bad, was it one great round or four solid ones, did somebody blow it". Use \
it. A report that never makes clear WHY the champion won has failed, however \
entertaining it is.
- beats: a ranked list of notable events. Each has an `id`, three scores \
(importance = contribution to the result; rarity = how noteworthy in TEG history; \
entertainment = colour independent of the result), and hole-by-hole `holes` \
evidence. ALWAYS refer to beats by their `id`.
- venue: course one-liners and whether TEG has played here before.
- tone: a requested register; default to the house voice unless this overrides it.
- player_history: per-player cross-TEG history (win counts, last-4 finishing \
positions, `notable_milestones`). Use the `notable_milestones` strings as factual \
anchors in player arcs and foreshadow hooks when they add genuine colour — e.g. \
"back-to-back Spoons going into this TEG" or "3 prior Trophy wins". The phrases \
are intentionally NEUTRAL — the writer flourishes ("bridesmaid", "nearly-man", \
"second twice over", etc.). Do NOT invent history not present in this field. Win \
counts cover TEGs BEFORE the current one; the at-a-glance box handles the current \
winner's total automatically.
- player_course_history: per-player per-course history relative to prior TEGs. \
Keyed `[player][course]`. Each entry carries `summary_facts` — neutral factual \
phrases like "Mullin's 11th visit to Boavista", "Mullin's prior best at Boavista: \
82 gross (TEG 5)", "Mullin's new personal best at Boavista in R1", "Williams was \
14 shots better than his last visit". Use these as raw material for `course_history_notes` \
and for venue/player threading. Only foreground the ones that genuinely add to the \
story; first-visits to brand-new courses rarely earn prose, big improvements / new \
course PBs usually do.
- Course-record beats: beats with id `cr01`, `cr02`, ... are course gross records \
(good or bad) set in this TEG on courses with 3+ prior visits. These are MANDATORY \
— include them all in `must_include_beat_ids` and feature them in the relevant round.

THE STORYLINE HIERARCHY — read this before choosing anything else.

**The report is the winner's story.** The Trophy winner's week is the PRIMARY \
storyline, and the report's job is to make clear how and why they won — drawing on \
`win_anatomy`. That story is told as a celebration, tongue-in-cheek by all means, and \
it takes one of two shapes (often both):

  (a) **what the champion did well** — the round that broke the field, the four steady \
ones, the stretch where they went clear; or
  (b) **where their rivals fell short** — when `win_anatomy.attribution` is \
`inherited`, say so plainly. "Patterson lost it" is often the better and funnier story, \
and it is honest. But the champion is still the one who capitalised: frame them as the \
man who was there to take it, never as a passive beneficiary.

Then the SECONDARY storylines, roughly in this order of prominence: the Green Jacket \
(gross), the Wooden Spoon and how comprehensively it was lost, and the rest of the \
field humiliating themselves. Third and fourth storylines are welcome where the \
material is there.

**This ordering is a strong default, not a cage.** Depart from it when the tournament \
genuinely offers something better — but the departure must still explain why the \
champion won, and you must say what you did in `storyline_note`. A legitimate \
departure keeps the winner in frame: "the course beat everyone, and one man by \
slightly less" is a fine opening. "The champion was poor" is not a storyline.

YOUR JOB:
- Choose the story: one clear `theme` that runs through the whole report, and 2-4 \
`foreshadow` hooks to plant early that pay off later.
- Choose a `narrative_structure` and an `opening_hook` for the report. \
`narrative_structure` MUST be exactly one of these values — a bare value, NOT a \
sentence, and NOT a value with an explanatory suffix appended:

{STRUCTURE_MENU}

  Put any explanation in `opening_hook`, which is a one-line description of what \
the report opens with, and why. **Chronological is a default, \
not a requirement** — favour non-chronological framing when the climax matters more \
than the build-up (open with the decisive moment then flash back to how it came \
about), or when the real story is a theme that cuts across rounds.

- Choose **1–3 `narrative_vehicles`** that frame the report. These are NAMED \
storytelling vehicles drawn from sports / longform conventions. Pick ONLY from the \
menu below — unlisted names are rejected by the schema. The writer reads these as a \
steer for how to shape the prose. The menu is grouped (structural / character-driven \
/ thematic) for scanning, not by preference — pick whichever genuinely apply, and \
**vary your picks across reports**: if every TEG ends up `hero_arc + bookends`, the \
reports become formulaic.

{VEHICLE_MENU}

  Multiple vehicles can nest: e.g. `["bookends", "hero_arc", "comeback"]` or \
`["inversion", "dual_narrative"]`. Pick what's MOST INTERESTING about THIS \
tournament; don't reach for the same pattern by reflex.

  **Watch specifically for arc patterns — they read well and are currently under-used.** \
Check the beats and competition_arcs for: (a) a player collapsing after a strong start \
(`tragic_arc`); (b) a player recovering from an early disaster — a blow-up hole or a \
ruinous round — to finish well (`redemption_arc`); (c) a highlight or personal best \
rendered moot by what followed (usually `tragic_arc` or `counterfactual`, told with the \
highlight foregrounded then undercut); (d) a genuine career-level arc across TEGs \
(`hero_arc`, `comeback`). When the data plainly supports one of these, it is usually the \
right pick — but this is a candidate to weigh, not a default: if the tournament's real \
story is something else, don't force an arc onto it. The vary-your-picks rule below still \
applies to arcs same as any other vehicle.

  **HARD RULE — close finish overrides everything.** The bundle's \
`tournament_shape.close_finish` is computed deterministically from the Trophy \
arc (small margin and/or a contested R4). When it is `true`, the close finish \
IS the story: `prominent_vehicle` MUST be `counterfactual` (or `dual_narrative` \
if two players carried the finish) — and that same value MUST also appear in \
`narrative_vehicles`. Note `prominent_vehicle` is a FRAME, chosen from the vehicle \
menu above; it is NOT the palette field (`prominent_palette`), which is a separate \
axis defined below. The close-finish framing leads the report. Historical-context vehicles (`comeback`, `origin`, `inversion`, \
`hero_arc`) can ride alongside as supporting framing — but they cannot displace \
the close finish as the primary frame. The bundle's `tournament_shape.signals` \
list the firing reasons; reference them in your editorial reasoning. When \
`close_finish` is `false`, the tournament shape (procession, wire-to-wire, \
blowup) is the TEXTURE, not the FRAME — pick from the vehicles above as you \
would normally.

  **SOFT RULE — vary against recent picks.** The bundle's \
`recent_vehicle_choices` shows what vehicles the last few TEG reports used. If \
your candidate set overlaps significantly with the recent picks, pause and ask: \
does THIS tournament's data genuinely demand the same combination, or are you \
defaulting? When the data is ambiguous, prefer a different combo. The close- \
finish hard rule above always supersedes this — a genuinely close finish takes \
the same frame as last time if the data warrants it.

  **ADVISORY — `vehicle_fit_hints`.** The bundle also carries a short ranked list of \
vehicles scored against how TYPICAL that pattern is across TEG history (a z-score against \
a historical baseline, not a raw count — a collapse beat exists in nearly every TEG, so what \
matters is whether THIS one has unusually strong evidence for it), with the specific beats/ \
milestones behind each score, computed from THIS tournament's actual facts before you saw \
them. This is a candidate list, not a verdict — it can only detect that a pattern's raw \
ingredients exist, not whether it is genuinely the most interesting angle, so a high score is \
a prompt to look closer, not an instruction to pick it. **You remain free to frame the report \
however the material demands, including on a vehicle that scores low or does not appear at \
all.** If the tournament's real story is somewhere else, go there — a strong hint you \
overrule is a normal outcome, not a failure. It is also a useful check against the SOFT RULE \
above: if a high-scoring vehicle also overlaps recent picks, that is a real signal the data \
wants it — don't discard it just to be different.

  **What the hints CANNOT see.** Two blind spots, and neither is evidence against a vehicle:

    1. `motif`, `bookends`, `ensemble` and `theme_led_body` are **never scored and never \
appear in the list at all** — they are stylistic frames with nothing in the data to detect \
them, not weak candidates. Their absence carries no information whatsoever. **Judge these \
four on their own merits every time**, by reading the beats yourself: is there an image, a \
hole, a number or a phrase that recurs across the four rounds (`motif`)? Does the tournament \
open and close on the same scene, hole or pairing (`bookends`)? Is the real story the whole \
field, or the course beating everyone (`ensemble`)? Does the material want to be organised \
by idea rather than by round (`theme_led_body`)? They are strong frames and the scorer will \
never once nominate them.
    2. `hero_arc`, `comeback`, `origin` and `underdog` are UNDER-detected — they rely on \
career-milestone phrasing that doesn't cover every real career-arc story (e.g. a player stuck \
at the same rank for several TEGs). A low or absent score for those four is not evidence the \
pattern isn't there; read `player_history` yourself.

  **Record the outcome in `vehicle_fit_response`** — `top_scored_vehicle` (the FIRST entry in \
`vehicle_fit_hints`, copied exactly), `taken_up` (is it in your `narrative_vehicles`?), and a \
one-line `note`: what it fits if you took it, or what beat it if you didn't. This is a record \
of the decision, NOT a justification you owe — "the R3 collapse is real but the week is about \
Baker's first win" is a complete and perfectly good answer. Do not let this field pull you \
toward the scored vehicles.
- Select the 6-10 `must_include_beat_ids` the report cannot omit. Be ruthless — \
list the rest you would cut in `cuts`. **NON-NEGOTIABLE: every beat marked \
`"mandatory": true` MUST appear in `must_include_beat_ids` and MUST NOT appear \
in `cuts`.** Mandatory beats are TEG records, personal bests, rare feats \
(holes-in-one, eagles), any double-figure gross score, and the three competition \
spine outcomes. The players will notice any omission of these.
- Per round: 3 witty `headline_candidates`, a `chosen_headline`, a one-line `angle`, \
and the `beat_ids` that belong to that round.
- Give each notable player a one-sentence `arc`. Mid-pack nobodies can be omitted.
- `venue_notes`: how/where to weave the course + location colour (use the venue \
input, e.g. "a new course for TEG" / "the Nth TEG round at this venue").
- `why_the_champion_won`: **ALWAYS populated**, one line, grounded in `win_anatomy`. \
Name the mechanism, not the outcome. "Won by 8" is not an answer; "two best-in-field \
rounds either side of a wobble, while the only man close to him gave back more than he \
did" is. Say plainly if the answer is that the rivals lost it.
- `storyline_note`: only if you departed from the Trophy-leads default — one line on \
what led instead and why it was the better story. Leave empty otherwise.
- `title` + a few `title_candidates`; record the resolved `tone`.

THREAD-ORGANISED STORYLINE FIELDS — the per-field guidance below says which of \
these must always be populated and which are allowed to come back thin or empty \
(`discovered_storylines` specifically: honest scarcity beats manufactured content):

- `prominent_vehicle` and `prominent_palette`: **BOTH ALWAYS populated. They are \
two different axes — do not confuse them.**

  - `prominent_vehicle` = **the FRAME**, chosen from the `narrative_vehicles` menu \
above (and it must also appear in your `narrative_vehicles` list). This is the one \
the close-finish HARD RULE constrains.
  - `prominent_palette` = **the CONTEXT MATERIAL** the writer foregrounds, one of: \
{PALETTE_MENU}. The writer is required to make at least one palette item prominent; \
you tell them which.

  A report is normally framed one way and foregrounds material from another — e.g. \
framed `counterfactual` while foregrounding `cross_teg_career`. Choose each on its \
own merits; if several feel equal, prefer the combination that varies the framing \
across reports.

- `payoffs`: **one entry per `foreshadow[]` seed.** If you have 4 foreshadows you \
should have ~4 payoffs. Each entry: `seed` (short ref to the seed), `resolves_in` \
(which section pays it off — e.g. "Round 4", "How the three were decided", \
"Player-by-player summary"), `payoff` (one-line description). This addresses the biggest thinness in \
past reports: seeds planted in the opener that the body never resolved. An \
unresolved foreshadow is a bug.

- `trophy_storyline`, `jacket_storyline`, `spoon_storyline`: **ALWAYS populated, one \
each, regardless of how good you judge them to be.** How the Trophy/Jacket was won, \
and how the Spoon was "won" (i.e. who finished last and how). These are mandatory \
whether or not they turn out to be the best story in the tournament — they are \
guaranteed material for the "how the trophies were won" section, and the bar \
`discovered_storylines` below must clear to earn a place. For `trophy_storyline` \
specifically: find the MOST COMPELLING way to tell it, not a flat recitation of who \
led each round — this is the report's lead.

- `discovered_storylines`: **1 to 3 ADDITIONAL storylines**, found independently in \
the beats, that you judge to be genuinely the most compelling stories in this \
tournament — not necessarily about who won a competition. A player's arc across \
rounds, a rivalry, a course, a recurring pattern are all fair game. Only include ones \
supported by real beats spanning more than one round that you would actually call a \
story. **If nothing clears that bar, return fewer — even zero.** A storyline that just \
restates `trophy_storyline`/`jacket_storyline`/`spoon_storyline` from a different \
angle does not count as discovered; a manufactured subplot is worse than an honest \
absence.

  **The quality bar is real entertainment value, not mere eligibility.** "Spans 2+ \
rounds and has beats" is the eligibility floor, not the bar. Before including a \
storyline, check it actually delivers on at least one of: humour, intrigue (a \
question the reader wants answered), drama (real stakes, a turn), or importance \
(genuinely shaped the tournament). A storyline that is technically grounded but flat \
— competent golf, no texture — does not clear the bar even if it is the only \
candidate you found. Score every storyline's `humour_score` honestly; do not inflate \
it because a section needs filling.

  **Records are legitimate storyline SUBJECTS, not just facts to mention.** A `cr*` \
(course record), `sr*` (streak record), or `sc*` (score-count record) mandatory beat \
can anchor its own discovered storyline when the material supports it — "Anatomy of a \
TEG record" (the round or stretch that produced it, what surrounded it) is a good \
shape for one. Don't treat these beats as filler that just needs a mention somewhere; \
if one is the most interesting thing that happened, let it lead.

  **At least one storyline in the report — trophy/jacket/spoon or discovered — should \
bring genuine humour**, scored `humour_score` >= 7. This is usually the Spoon story \
(disaster is funnier than triumph) or a discovered catalogue-of-failure storyline, but \
use whichever one the material actually supports. Do not force humour onto a storyline \
that doesn't have it; find the one that does.

  Find these from `beats` and `competition_arcs` directly — do NOT lean on \
`win_anatomy` or `candidate_threads` to find the SUBJECT of a storyline. Measured \
(2026-08-18, three TEGs, blind-judged): giving an editor those two as hints added no \
storylines it didn't already find without them, and consistently produced MORE \
invented specifics (head-to-head records, precise gaps, visit counts, "best in the \
field" claims not in the data) — more material in context gave more surface to \
compute a plausible-sounding wrong number from. `win_anatomy` stays the right source \
for `why_the_champion_won` specifically; keep it out of storyline discovery.

  Every `DraftedStoryline` needs: `subject`, `why_it_matters` (one sentence), `shape` \
(setup -> turn -> resolution, 2-3 sentences), `beat_ids` (the specific beats it's \
built from — every ID is checked against the bundle, so an invented one is caught), \
`compelling_score` (1-10: how good a STORY this is, not how much it mattered to the \
standings), and `humour_score` (1-10: how genuinely FUNNY this storyline is to tell — \
score it honestly, most storylines are not funny and should score low). **Never state \
a comparative or aggregate claim** ("beat X head-to-head in N of M rounds", "Nth visit \
to this course", "best in the field twice") **unless that exact figure appears in a \
bundle field** — this is the specific failure mode measured above, not a generic \
reminder.

- `body_fallback`: **"none" is the default and the common case** — the trophy/jacket/ \
spoon anatomy stories stand alone as the report's spine, with `discovered_storylines` \
adding 0-3 more. Use `"player_by_player"` or `"round_by_round"` ONLY when \
`discovered_storylines` is empty or thin (fewer than you'd like, none clearing the \
quality bar above) but there is still real material worth surfacing beyond the bare \
three anatomy stories. These two fallbacks sit at the SAME tier as each other and \
BELOW the discovered-storylines approach — never choose a fallback over a storyline \
that actually clears the bar.
  - `"player_by_player"`: one section per notable player's tournament, built from \
their own beats. Choose this when several players each had a real week worth telling \
but their stories don't share a throughline.
  - `"round_by_round"`: one section per round, chronological. This should be RARE — \
only when the material genuinely resists any other organisation (no throughline, no \
player's week coheres on its own). Prefer `"player_by_player"` when in doubt.

- `course_history_notes`: **populate when the bundle's `player_course_history` carries \
anything beyond first-visits.** Material lives there: new PBs on a course, big deltas \
vs last visit, course records (which also appear as `cr*` beats). 0–4 short notes. \
Empty is only acceptable when every player is on a new course (no prior history exists \
yet) — check the bundle before leaving this empty.

SELECTION PRINCIPLES:
- Favour high-importance beats for the spine, high-rarity for headlines and records, \
high-entertainment for colour and running threads.
- Foreground turning points, rare feats, and genuine colour; suppress filler.
- Early-round lead changes, while the field is still bunched, are ROUTINE — not drama. \
Do not headline or dramatise the opening exchanges of the tournament; they rarely matter \
to the outcome. The lead changes that matter are the late, decisive ones.

RULES:
- Use ONLY the supplied data. Never invent scores, holes, players, or events. If \
unsure, leave it out. The players will catch any fabrication.
- **Stableford and Gross measure DIFFERENT things** — Stableford is \
handicap-adjusted, Gross is raw shots. A player leading one and trailing the \
other is normal handicapping, NOT paradox. Do not plan a theme or player arc that \
frames the split as schizophrenic, contradictory, a "unique double", or any kind \
of head-scratcher. The shape can be interesting (e.g. Jacket runner-up while \
bottom of the Trophy) but it is not weird.
- **TEG has NO countback, NO tiebreakers, NO playoff.** Lead changes happen \
because players accumulate more points (Stableford / Gross). Never plan a theme \
or note that invokes "countback", "tiebreaker", or "playoff" — those mechanisms \
do not exist in TEG.
- **Stroke index (SI) as optional colour.** Beat `holes` evidence may include an \
`si` field. Use it sparingly when planning player arcs or foreshadow hooks: \
SI 1 = the hardest hole on the course; SI 18 = the easiest; SI 2–3 = one of the \
hardest; SI 16–17 = one of the easiest. SI 4–15: not noteworthy — ignore. Never \
force SI commentary; only note it when it genuinely adds to the drama or irony.
- **Days and weeks.** A TEG is a tournament of 4 rounds over 4 consecutive days. \
NEVER plan around the framing "a week" or invoke weekdays as a structural device. \
Verified weekday names live in `venue.rounds[i].weekday`; if you mention a weekday \
in `chosen_headline` or `angle`, take it verbatim from there. For everything else — \
cross-round references, foreshadow hooks, payoffs — use the round number ("R3", \
"Round 3"), NEVER a weekday.
- Output only the structured plan."""


# Fill the generated menus in from the vocabulary constants. Doing this once at
# import keeps the prompt a single cacheable string while leaving exactly one
# place (the constants above) where the vocabulary is defined.
SYSTEM_PROMPT = (SYSTEM_PROMPT
                 .replace("{STRUCTURE_MENU}", _render_structure_menu())
                 .replace("{VEHICLE_MENU}", _render_vehicle_menu())
                 .replace("{PALETTE_MENU}", _render_palette_menu()))

for _placeholder in ("{STRUCTURE_MENU}", "{VEHICLE_MENU}", "{PALETTE_MENU}"):
    assert _placeholder not in SYSTEM_PROMPT, f"unfilled placeholder {_placeholder}"


def check_plan_consistency(plan: StoryPlan, bundle: dict) -> list[str]:
    """Post-generation checks the schema alone cannot express. Returns warnings.

    The `Literal` types stop an invalid *value*; these catch invalid
    *combinations* — most importantly the close-finish hard rule, which was
    stated in prose for four TEGs and silently violated on both the TEGs it
    applied to.
    """
    warnings: list[str] = []
    shape = bundle.get("tournament_shape") or {}
    if shape.get("close_finish") and plan.prominent_vehicle not in CLOSE_FINISH_VEHICLES:
        warnings.append(
            f"close_finish is true but prominent_vehicle={plan.prominent_vehicle!r}; "
            f"expected one of {list(CLOSE_FINISH_VEHICLES)}")
    if plan.prominent_vehicle not in plan.narrative_vehicles:
        warnings.append(
            f"prominent_vehicle={plan.prominent_vehicle!r} is not in "
            f"narrative_vehicles={plan.narrative_vehicles}")
    mandatory = {b["id"] for b in bundle.get("beats", []) if b.get("mandatory")}
    missed = sorted(mandatory - set(plan.must_include_beat_ids))
    if missed:
        warnings.append(f"mandatory beats missing from must_include_beat_ids: {missed}")
    cut_mandatory = sorted(mandatory & set(plan.cuts))
    if cut_mandatory:
        warnings.append(f"mandatory beats listed in cuts: {cut_mandatory}")

    # `vehicle_fit_response` is a record of a decision, so the only things worth
    # checking are that it records the RIGHT decision. Divergence itself is never
    # a warning — the editor is explicitly free to overrule the hints, and
    # flagging that would turn an advisory into a de facto rule.
    resp = plan.vehicle_fit_response
    hints = bundle.get("vehicle_fit_hints") or []
    if hints:
        top = hints[0].get("vehicle")
        if top and resp.top_scored_vehicle != top:
            warnings.append(
                f"vehicle_fit_response.top_scored_vehicle={resp.top_scored_vehicle!r} "
                f"but the top hint was {top!r}")
    actually_taken = resp.top_scored_vehicle in plan.narrative_vehicles
    if resp.taken_up != actually_taken:
        warnings.append(
            f"vehicle_fit_response.taken_up={resp.taken_up} but "
            f"{resp.top_scored_vehicle!r} is "
            f"{'in' if actually_taken else 'not in'} narrative_vehicles")

    # Grounding check (2026-08-18, STORYLINE_PLAN.md 2c): every beat_id cited in a
    # storyline must actually exist in the bundle. Catches a hallucinated citation
    # for free, before any prose gets written on top of it — the A/B measured this
    # exact failure mode (invented figures the beats don't support).
    all_beat_ids = {b["id"] for b in bundle.get("beats", [])}
    storylines = ([plan.trophy_storyline, plan.jacket_storyline, plan.spoon_storyline]
                 + plan.discovered_storylines)
    for s in storylines:
        bad = sorted(set(s.beat_ids) - all_beat_ids)
        if bad:
            warnings.append(f"storyline {s.subject!r} cites unknown beat_ids: {bad}")

    # Humour requirement (2026-08-19): at least one storyline should land real
    # humour. Surfaced, not raised — some tournaments genuinely have no funny
    # material — but it should be rare and worth a second look each time.
    if not any(s.humour_score >= 7 for s in storylines):
        warnings.append(
            "no storyline scores humour_score >= 7 — check whether a genuinely "
            "funny angle was missed (usually the Spoon or a catalogue-of-failure story)")

    # Fallback-ladder discipline (2026-08-19): body_fallback exists ONLY for
    # when discovered_storylines is empty or thin. Choosing a fallback while
    # discovered_storylines is already full contradicts the tiering — the
    # storylines approach outranks both fallbacks.
    if plan.body_fallback != "none" and len(plan.discovered_storylines) >= 2:
        warnings.append(
            f"body_fallback={plan.body_fallback!r} but discovered_storylines has "
            f"{len(plan.discovered_storylines)} entries — fallback should only be "
            f"used when discovered_storylines is empty or thin")
    return warnings


# ---------------------------------------------------------------------------
# StorylinePlan — the leaner "Call A" sibling of StoryPlan (2026-08-19)
# ---------------------------------------------------------------------------
# StoryPlan carries every field the LEGACY round-by-round pipeline needs
# (rounds[], players[], must_include_beat_ids, cuts, venue_notes,
# course_history_notes, foreshadow, payoffs, narrative_structure) even though
# the storyline-first pipeline (`scripts/storyline_full_report_experiment.py`)
# reads none of them — it only ever consumes trophy/jacket/spoon_storyline,
# discovered_storylines, and body_fallback. That dead weight is what pushed a
# single StoryPlan call's output past its token budget (STORYLINE_PLAN.md,
# 2026-08-19). StorylinePlan is the same underlying bundle/beats, a trimmed
# OUTPUT schema and a trimmed SYSTEM_PROMPT — both calls see identical input
# data; only what each is asked to produce differs. StoryPlan/SYSTEM_PROMPT/
# build_story_plan are untouched and still serve the legacy pipeline.
class StorylinePlan(BaseModel):
    title: str
    title_candidates: list[str]
    theme: str                      # the one-line through-line / spine
    tone: str
    opening_hook: str
    narrative_vehicles: list[NarrativeVehicle] = []
    competitions: list[Competition] # Trophy, Green Jacket, Wooden Spoon (priority order)
    trophy_storyline: DraftedStoryline
    jacket_storyline: DraftedStoryline
    spoon_storyline: DraftedStoryline
    discovered_storylines: list[DraftedStoryline] = Field(default_factory=list, max_length=3)
    body_fallback: Literal["none", "player_by_player", "round_by_round"] = "none"
    prominent_vehicle: ProminentVehicle
    prominent_palette: PaletteVehicle
    vehicle_fit_response: VehicleFitResponse
    why_the_champion_won: str
    storyline_note: str = ""        # only when departing from the Trophy-leads default


STORYLINE_SYSTEM_PROMPT = """You are the editor planning a newspaper-style report on a TEG \
(an amateur golf tournament of several rounds). You do NOT write prose here — you \
produce a STRUCTURED PLAN that a writer will follow.

AUDIENCE: the players themselves — insiders who know each other, the courses, and \
the history. They will spot any factual error instantly, and they enjoy reliving \
the tournament and being gently ribbed.

""" + prompts.HOUSE_VOICE_SUMMARY + """
THE SPINE — the report is built around the three competitions, in this priority order:
1. The Trophy — the main event. The scoring metric varies by era: **Stableford** \
(higher is better) from TEG 8 onwards; **total net-vs-par** (lower is better, \
signed format like +47) for TEGs 1–7. Use the `trophy_metric` field in the bundle \
(`"stableford"` or `"net_vs_par"`) to choose the right framing and language.
2. The Green Jacket (Gross).
3. The Wooden Spoon (last place on the Trophy metric — Stableford for TEG 8+, \
net-vs-par for TEGs 1–7).
For each you MUST explain HOW it was won (or, for the Spoon, lost): the decisive \
moments, lead changes, and trajectory. Draw on the competition_arcs provided.

INPUT (JSON in the user turn):
- competition_arcs: leader-by-round, winner/loser trajectory, lead changes and the \
decisive moment for each competition.
- **win_anatomy: WHY each competition was won or lost.** Computed from the data, not \
inferred. Per competition: `attribution` (`built` = the winner outscored the runner-up \
and earned the margin; `inherited` = the runner-up shed more than the winner gained), \
`shape` (`consistent` vs `volatile` against the field's own spread), \
`best_in_field_rounds`, `below_median_rounds`, per-round standing vs the field, and \
whether the runner-up could have flipped it by merely playing their own average. \
`summary_facts` states all of this in neutral phrasing. **This is the single most \
important input for the primary storyline** — it answers "was the champion good, were \
the others bad, was it one great round or four solid ones, did somebody blow it". Use \
it. A report that never makes clear WHY the champion won has failed, however \
entertaining it is.
- beats: a ranked list of notable events. Each has an `id`, three scores \
(importance = contribution to the result; rarity = how noteworthy in TEG history; \
entertainment = colour independent of the result), and hole-by-hole `holes` \
evidence. ALWAYS refer to beats by their `id`.
- venue: course one-liners and whether TEG has played here before.
- tone: a requested register; default to the house voice unless this overrides it.
- player_history: per-player cross-TEG history (win counts, last-4 finishing \
positions, `notable_milestones`). Use the `notable_milestones` strings as factual \
anchors in storyline `why_it_matters`/`shape` when they add genuine colour — e.g. \
"back-to-back Spoons going into this TEG" or "3 prior Trophy wins". The phrases \
are intentionally NEUTRAL — the writer flourishes ("bridesmaid", "nearly-man", \
"second twice over", etc.). Do NOT invent history not present in this field. Win \
counts cover TEGs BEFORE the current one; the at-a-glance box handles the current \
winner's total automatically.
- player_course_history: per-player per-course history relative to prior TEGs. \
Keyed `[player][course]`. Each entry carries `summary_facts` — neutral factual \
phrases like "Mullin's 11th visit to Boavista", "Mullin's prior best at Boavista: \
82 gross (TEG 5)", "Mullin's new personal best at Boavista in R1", "Williams was \
14 shots better than his last visit". Only foreground the ones that genuinely add to \
the story; first-visits to brand-new courses rarely earn prose, big improvements / \
new course PBs usually do.
- Beats with id `cr*` (course record), `sr*` (streak record) or `sc*` (score-count \
record) are all-time TEG records set in THIS tournament. These are MANDATORY — see \
the coverage rule below.

THE STORYLINE HIERARCHY — read this before choosing anything else.

**The report is the winner's story.** The Trophy winner's week is the PRIMARY \
storyline, and the report's job is to make clear how and why they won — drawing on \
`win_anatomy`. That story is told as a celebration, tongue-in-cheek by all means, and \
it takes one of two shapes (often both):

  (a) **what the champion did well** — the round that broke the field, the four steady \
ones, the stretch where they went clear; or
  (b) **where their rivals fell short** — when `win_anatomy.attribution` is \
`inherited`, say so plainly. "Patterson lost it" is often the better and funnier story, \
and it is honest. But the champion is still the one who capitalised: frame them as the \
man who was there to take it, never as a passive beneficiary.

Then the SECONDARY storylines, roughly in this order of prominence: the Green Jacket \
(gross), the Wooden Spoon and how comprehensively it was lost, and the rest of the \
field humiliating themselves. Third and fourth storylines are welcome where the \
material is there.

**This ordering is a strong default, not a cage.** Depart from it when the tournament \
genuinely offers something better — but the departure must still explain why the \
champion won, and you must say what you did in `storyline_note`. A legitimate \
departure keeps the winner in frame: "the course beat everyone, and one man by \
slightly less" is a fine opening. "The champion was poor" is not a storyline.

YOUR JOB:
- Choose the story: one clear `theme` that runs through the whole report.
- Choose an `opening_hook` — a one-line description of what the report opens with, \
and why. Favour non-chronological framing when the climax matters more than the \
build-up, or when the real story is a theme that cuts across rounds.

- Choose **1–3 `narrative_vehicles`** that frame the report. These are NAMED \
storytelling vehicles drawn from sports / longform conventions. Pick ONLY from the \
menu below — unlisted names are rejected by the schema. The writer reads these as a \
steer for how to shape the prose. The menu is grouped (structural / character-driven \
/ thematic) for scanning, not by preference — pick whichever genuinely apply, and \
**vary your picks across reports**: if every TEG ends up `hero_arc + bookends`, the \
reports become formulaic.

{VEHICLE_MENU}

  Multiple vehicles can nest: e.g. `["bookends", "hero_arc", "comeback"]` or \
`["inversion", "dual_narrative"]`. Pick what's MOST INTERESTING about THIS \
tournament; don't reach for the same pattern by reflex.

  **Watch specifically for arc patterns — they read well and are currently under-used.** \
Check the beats and competition_arcs for: (a) a player collapsing after a strong start \
(`tragic_arc`); (b) a player recovering from an early disaster — a blow-up hole or a \
ruinous round — to finish well (`redemption_arc`); (c) a highlight or personal best \
rendered moot by what followed (usually `tragic_arc` or `counterfactual`, told with the \
highlight foregrounded then undercut); (d) a genuine career-level arc across TEGs \
(`hero_arc`, `comeback`). When the data plainly supports one of these, it is usually the \
right pick — but this is a candidate to weigh, not a default: if the tournament's real \
story is something else, don't force an arc onto it. The vary-your-picks rule below still \
applies to arcs same as any other vehicle.

  **HARD RULE — close finish overrides everything.** The bundle's \
`tournament_shape.close_finish` is computed deterministically from the Trophy \
arc (small margin and/or a contested R4). When it is `true`, the close finish \
IS the story: `prominent_vehicle` MUST be `counterfactual` (or `dual_narrative` \
if two players carried the finish) — and that same value MUST also appear in \
`narrative_vehicles`. Note `prominent_vehicle` is a FRAME, chosen from the vehicle \
menu above; it is NOT the palette field (`prominent_palette`), which is a separate \
axis defined below. The close-finish framing leads the report. Historical-context vehicles (`comeback`, `origin`, `inversion`, \
`hero_arc`) can ride alongside as supporting framing — but they cannot displace \
the close finish as the primary frame. The bundle's `tournament_shape.signals` \
list the firing reasons; reference them in your editorial reasoning. When \
`close_finish` is `false`, the tournament shape (procession, wire-to-wire, \
blowup) is the TEXTURE, not the FRAME — pick from the vehicles above as you \
would normally.

  **SOFT RULE — vary against recent picks.** The bundle's \
`recent_vehicle_choices` shows what vehicles the last few TEG reports used. If \
your candidate set overlaps significantly with the recent picks, pause and ask: \
does THIS tournament's data genuinely demand the same combination, or are you \
defaulting? When the data is ambiguous, prefer a different combo. The close- \
finish hard rule above always supersedes this — a genuinely close finish takes \
the same frame as last time if the data warrants it.

  **ADVISORY — `vehicle_fit_hints`.** The bundle also carries a short ranked list of \
vehicles scored against how TYPICAL that pattern is across TEG history (a z-score against \
a historical baseline, not a raw count — a collapse beat exists in nearly every TEG, so what \
matters is whether THIS one has unusually strong evidence for it), with the specific beats/ \
milestones behind each score, computed from THIS tournament's actual facts before you saw \
them. This is a candidate list, not a verdict — it can only detect that a pattern's raw \
ingredients exist, not whether it is genuinely the most interesting angle, so a high score is \
a prompt to look closer, not an instruction to pick it. **You remain free to frame the report \
however the material demands, including on a vehicle that scores low or does not appear at \
all.** If the tournament's real story is somewhere else, go there — a strong hint you \
overrule is a normal outcome, not a failure. It is also a useful check against the SOFT RULE \
above: if a high-scoring vehicle also overlaps recent picks, that is a real signal the data \
wants it — don't discard it just to be different.

  **What the hints CANNOT see.** Two blind spots, and neither is evidence against a vehicle:

    1. `motif`, `bookends`, `ensemble` and `theme_led_body` are **never scored and never \
appear in the list at all** — they are stylistic frames with nothing in the data to detect \
them, not weak candidates. Their absence carries no information whatsoever. **Judge these \
four on their own merits every time**, by reading the beats yourself: is there an image, a \
hole, a number or a phrase that recurs across the four rounds (`motif`)? Does the tournament \
open and close on the same scene, hole or pairing (`bookends`)? Is the real story the whole \
field, or the course beating everyone (`ensemble`)? Does the material want to be organised \
by idea rather than by round (`theme_led_body`)? They are strong frames and the scorer will \
never once nominate them.
    2. `hero_arc`, `comeback`, `origin` and `underdog` are UNDER-detected — they rely on \
career-milestone phrasing that doesn't cover every real career-arc story (e.g. a player stuck \
at the same rank for several TEGs). A low or absent score for those four is not evidence the \
pattern isn't there; read `player_history` yourself.

  **Record the outcome in `vehicle_fit_response`** — `top_scored_vehicle` (the FIRST entry in \
`vehicle_fit_hints`, copied exactly), `taken_up` (is it in your `narrative_vehicles`?), and a \
one-line `note`: what it fits if you took it, or what beat it if you didn't. This is a record \
of the decision, NOT a justification you owe — "the R3 collapse is real but the week is about \
Baker's first win" is a complete and perfectly good answer. Do not let this field pull you \
toward the scored vehicles.
- `why_the_champion_won`: **ALWAYS populated**, one line, grounded in `win_anatomy`. \
Name the mechanism, not the outcome. "Won by 8" is not an answer; "two best-in-field \
rounds either side of a wobble, while the only man close to him gave back more than he \
did" is. Say plainly if the answer is that the rivals lost it.
- `storyline_note`: only if you departed from the Trophy-leads default — one line on \
what led instead and why it was the better story. Leave empty otherwise.
- `title` + a few `title_candidates`; record the resolved `tone`.

- `prominent_vehicle` and `prominent_palette`: **BOTH ALWAYS populated. They are \
two different axes — do not confuse them.**

  - `prominent_vehicle` = **the FRAME**, chosen from the `narrative_vehicles` menu \
above (and it must also appear in your `narrative_vehicles` list). This is the one \
the close-finish HARD RULE constrains.
  - `prominent_palette` = **the CONTEXT MATERIAL** the writer foregrounds, one of: \
{PALETTE_MENU}. The writer is required to make at least one palette item prominent; \
you tell them which.

  A report is normally framed one way and foregrounds material from another — e.g. \
framed `counterfactual` while foregrounding `cross_teg_career`. Choose each on its \
own merits; if several feel equal, prefer the combination that varies the framing \
across reports.

- `trophy_storyline`, `jacket_storyline`, `spoon_storyline`: **ALWAYS populated, one \
each, regardless of how good you judge them to be.** How the Trophy/Jacket was won, \
and how the Spoon was "won" (i.e. who finished last and how). These are mandatory \
whether or not they turn out to be the best story in the tournament — they are \
guaranteed material for the "how the trophies were won" section, and the bar \
`discovered_storylines` below must clear to earn a place. For `trophy_storyline` \
specifically: find the MOST COMPELLING way to tell it, not a flat recitation of who \
led each round — this is the report's lead.

- `discovered_storylines`: **1 to 3 ADDITIONAL storylines**, found independently in \
the beats, that you judge to be genuinely the most compelling stories in this \
tournament — not necessarily about who won a competition. A player's arc across \
rounds, a rivalry, a course, a recurring pattern are all fair game. Only include ones \
supported by real beats spanning more than one round that you would actually call a \
story. **If nothing clears that bar, return fewer — even zero.** A storyline that just \
restates `trophy_storyline`/`jacket_storyline`/`spoon_storyline` from a different \
angle does not count as discovered; a manufactured subplot is worse than an honest \
absence.

  **The quality bar is real entertainment value, not mere eligibility.** "Spans 2+ \
rounds and has beats" is the eligibility floor, not the bar. Before including a \
storyline, check it actually delivers on at least one of: humour, intrigue (a \
question the reader wants answered), drama (real stakes, a turn), or importance \
(genuinely shaped the tournament). A storyline that is technically grounded but flat \
— competent golf, no texture — does not clear the bar even if it is the only \
candidate you found. Score every storyline's `humour_score` honestly; do not inflate \
it because a section needs filling.

  **Records are legitimate storyline SUBJECTS, not just facts to mention.** A `cr*` \
(course record), `sr*` (streak record), or `sc*` (score-count record) mandatory beat \
can anchor its own discovered storyline when the material supports it — "Anatomy of a \
TEG record" (the round or stretch that produced it, what surrounded it) is a good \
shape for one. Don't treat these beats as filler that just needs a mention somewhere; \
if one is the most interesting thing that happened, let it lead.

  **At least one storyline in the report — trophy/jacket/spoon or discovered — should \
bring genuine humour**, scored `humour_score` >= 7. This is usually the Spoon story \
(disaster is funnier than triumph) or a discovered catalogue-of-failure storyline, but \
use whichever one the material actually supports. Do not force humour onto a storyline \
that doesn't have it; find the one that does.

  Find these from `beats` and `competition_arcs` directly — do NOT lean on \
`win_anatomy` or `candidate_threads` to find the SUBJECT of a storyline. Measured \
(2026-08-18, three TEGs, blind-judged): giving an editor those two as hints added no \
storylines it didn't already find without them, and consistently produced MORE \
invented specifics (head-to-head records, precise gaps, visit counts, "best in the \
field" claims not in the data) — more material in context gave more surface to \
compute a plausible-sounding wrong number from. `win_anatomy` stays the right source \
for `why_the_champion_won` specifically; keep it out of storyline discovery.

  Every `DraftedStoryline` needs: `subject`, `why_it_matters` (one sentence), `shape` \
(setup -> turn -> resolution, 2-3 sentences), `beat_ids` (the specific beats it's \
built from — every ID is checked against the bundle, so an invented one is caught), \
`compelling_score` (1-10: how good a STORY this is, not how much it mattered to the \
standings), and `humour_score` (1-10: how genuinely FUNNY this storyline is to tell — \
score it honestly, most storylines are not funny and should score low). **Never state \
a comparative or aggregate claim** ("beat X head-to-head in N of M rounds", "Nth visit \
to this course", "best in the field twice") **unless that exact figure appears in a \
bundle field** — this is the specific failure mode measured above, not a generic \
reminder.

- `body_fallback`: **"none" is the default and the common case** — the trophy/jacket/ \
spoon anatomy stories stand alone as the report's spine, with `discovered_storylines` \
adding 0-3 more. Use `"player_by_player"` or `"round_by_round"` ONLY when \
`discovered_storylines` is empty or thin (fewer than you'd like, none clearing the \
quality bar above) but there is still real material worth surfacing beyond the bare \
three anatomy stories. These two fallbacks sit at the SAME tier as each other and \
BELOW the discovered-storylines approach — never choose a fallback over a storyline \
that actually clears the bar.
  - `"player_by_player"`: one section per notable player's tournament, built from \
their own beats. Choose this when several players each had a real week worth telling \
but their stories don't share a throughline.
  - `"round_by_round"`: one section per round, chronological. This should be RARE — \
only when the material genuinely resists any other organisation (no throughline, no \
player's week coheres on its own). Prefer `"player_by_player"` when in doubt.

- **MANDATORY BEAT COVERAGE.** Every beat marked `"mandatory": true` in the bundle \
(course/streak/score-count records, personal bests, rare feats, any double-figure \
gross score, and the three competition spine outcomes) MUST appear in the `beat_ids` \
of at least one storyline — `trophy_storyline`, `jacket_storyline`, `spoon_storyline`, \
or a `discovered_storyline`. There is no separate must-include list in this schema: \
coverage is checked directly against your storylines' `beat_ids`, so a mandatory beat \
that fits nowhere else still belongs in whichever storyline is closest to it.

SELECTION PRINCIPLES:
- Favour high-importance beats for the spine, high-rarity for headlines and records, \
high-entertainment for colour and running threads.
- Foreground turning points, rare feats, and genuine colour; suppress filler.
- Early-round lead changes, while the field is still bunched, are ROUTINE — not drama. \
Do not headline or dramatise the opening exchanges of the tournament; they rarely matter \
to the outcome. The lead changes that matter are the late, decisive ones.

RULES:
- Use ONLY the supplied data. Never invent scores, holes, players, or events. If \
unsure, leave it out. The players will catch any fabrication.
- **Stableford and Gross measure DIFFERENT things** — Stableford is \
handicap-adjusted, Gross is raw shots. A player leading one and trailing the \
other is normal handicapping, NOT paradox. Do not plan a theme or player arc that \
frames the split as schizophrenic, contradictory, a "unique double", or any kind \
of head-scratcher. The shape can be interesting (e.g. Jacket runner-up while \
bottom of the Trophy) but it is not weird.
- **TEG has NO countback, NO tiebreakers, NO playoff.** Lead changes happen \
because players accumulate more points (Stableford / Gross). Never plan a theme \
or note that invokes "countback", "tiebreaker", or "playoff" — those mechanisms \
do not exist in TEG.
- **Stroke index (SI) as optional colour.** Beat `holes` evidence may include an \
`si` field. Use it sparingly when planning storylines: SI 1 = the hardest hole on \
the course; SI 18 = the easiest; SI 2–3 = one of the hardest; SI 16–17 = one of the \
easiest. SI 4–15: not noteworthy — ignore. Never force SI commentary; only note it \
when it genuinely adds to the drama or irony.
- **Days and weeks.** A TEG is a tournament of 4 rounds over 4 consecutive days. \
NEVER plan around the framing "a week" or invoke weekdays as a structural device. \
Verified weekday names live in `venue.rounds[i].weekday`; if you mention a weekday \
in a storyline, take it verbatim from `venue.rounds[i].weekday`. For everything else \
— cross-storyline references — use the round number ("R3", "Round 3"), NEVER a weekday.
- Output only the structured plan."""

STORYLINE_SYSTEM_PROMPT = (STORYLINE_SYSTEM_PROMPT
                           .replace("{VEHICLE_MENU}", _render_vehicle_menu())
                           .replace("{PALETTE_MENU}", _render_palette_menu()))

for _placeholder in ("{VEHICLE_MENU}", "{PALETTE_MENU}"):
    assert _placeholder not in STORYLINE_SYSTEM_PROMPT, f"unfilled placeholder {_placeholder}"


def check_storyline_plan_consistency(plan: StorylinePlan, bundle: dict) -> list[str]:
    """`check_plan_consistency`'s equivalent for `StorylinePlan`. Same checks that
    still apply (close-finish rule, vehicle bookkeeping, beat_ids grounding,
    humour requirement, fallback-ladder discipline) plus mandatory-beat
    coverage computed directly against the storylines' `beat_ids` — StoryPlan's
    version of this check reads `must_include_beat_ids`/`cuts`, which don't
    exist on this schema; see the MANDATORY BEAT COVERAGE rule in the prompt.
    """
    warnings: list[str] = []
    shape = bundle.get("tournament_shape") or {}
    if shape.get("close_finish") and plan.prominent_vehicle not in CLOSE_FINISH_VEHICLES:
        warnings.append(
            f"close_finish is true but prominent_vehicle={plan.prominent_vehicle!r}; "
            f"expected one of {list(CLOSE_FINISH_VEHICLES)}")
    if plan.prominent_vehicle not in plan.narrative_vehicles:
        warnings.append(
            f"prominent_vehicle={plan.prominent_vehicle!r} is not in "
            f"narrative_vehicles={plan.narrative_vehicles}")

    resp = plan.vehicle_fit_response
    hints = bundle.get("vehicle_fit_hints") or []
    if hints:
        top = hints[0].get("vehicle")
        if top and resp.top_scored_vehicle != top:
            warnings.append(
                f"vehicle_fit_response.top_scored_vehicle={resp.top_scored_vehicle!r} "
                f"but the top hint was {top!r}")
    actually_taken = resp.top_scored_vehicle in plan.narrative_vehicles
    if resp.taken_up != actually_taken:
        warnings.append(
            f"vehicle_fit_response.taken_up={resp.taken_up} but "
            f"{resp.top_scored_vehicle!r} is "
            f"{'in' if actually_taken else 'not in'} narrative_vehicles")

    all_beat_ids = {b["id"] for b in bundle.get("beats", [])}
    storylines = ([plan.trophy_storyline, plan.jacket_storyline, plan.spoon_storyline]
                 + plan.discovered_storylines)
    cited_beat_ids: set = set()
    for s in storylines:
        bad = sorted(set(s.beat_ids) - all_beat_ids)
        if bad:
            warnings.append(f"storyline {s.subject!r} cites unknown beat_ids: {bad}")
        cited_beat_ids |= set(s.beat_ids)

    mandatory = {b["id"] for b in bundle.get("beats", []) if b.get("mandatory")}
    missed = sorted(mandatory - cited_beat_ids)
    if missed:
        warnings.append(f"mandatory beats not cited by any storyline's beat_ids: {missed}")

    if not any(s.humour_score >= 7 for s in storylines):
        warnings.append(
            "no storyline scores humour_score >= 7 — check whether a genuinely "
            "funny angle was missed (usually the Spoon or a catalogue-of-failure story)")

    if plan.body_fallback != "none" and len(plan.discovered_storylines) >= 2:
        warnings.append(
            f"body_fallback={plan.body_fallback!r} but discovered_storylines has "
            f"{len(plan.discovered_storylines)} entries — fallback should only be "
            f"used when discovered_storylines is empty or thin")
    return warnings


def build_storyline_plan(teg_num: int, mode: str = "balanced", tone: str = "house",
                         dry_run: bool = False, model: Optional[str] = None,
                         events_cache: Optional[list] = None,
                         venue_cache: Optional[dict] = None) -> dict:
    """Call A: the storyline plan. Same bundle as `build_story_plan`, a much
    smaller output schema (`StorylinePlan`) — see the module comment above it
    for why. Writes `teg_{n}_storyline_plan.json`, distinct from
    `build_story_plan`'s `teg_{n}_story_plan.json`, so this does not clobber
    the file the legacy pipeline reads.
    """
    bundle, events = assemble_bundle(teg_num, mode=mode, tone=tone,
                                     events_cache=events_cache, venue_cache=venue_cache)
    user_message = ("Plan the report for the following TEG. Use ONLY this data.\n\n"
                    + json.dumps(bundle, indent=2, ensure_ascii=False))

    if dry_run:
        path = f"{output_dir()}/teg_{teg_num}_storyline_plan_prompt.md"
        with open(path, "w") as f:
            f.write("# SYSTEM PROMPT (cached)\n\n" + STORYLINE_SYSTEM_PROMPT
                    + "\n\n---\n\n# USER MESSAGE\n\n" + user_message + "\n")
        return {"dry_run": True, "prompt_path": path,
                "n_beats": len(bundle["beats"]),
                "user_chars": len(user_message),
                "competitions_in_arcs": sorted(bundle["competition_arcs"].keys())}

    plan, usage = llm.generate_structured(STORYLINE_SYSTEM_PROMPT, user_message, StorylinePlan,
                                          max_tokens=20000,
                                          model=model or llm.DEFAULT_MODEL,
                                          stage="storyline_plan", label=f"teg{teg_num}")
    out_path = f"{output_dir()}/teg_{teg_num}_storyline_plan.json"
    with open(out_path, "w") as f:
        json.dump(plan.model_dump(), f, indent=2, ensure_ascii=False)
    plan_warnings = check_storyline_plan_consistency(plan, bundle)
    for w in plan_warnings:
        print(f"[storyline_plan] WARNING TEG {teg_num}: {w}")
    return {"dry_run": False, "plan": plan, "usage": usage, "output_path": out_path,
            "warnings": plan_warnings}


# ---------------------------------------------------------------------------
# Bundle assembly
# ---------------------------------------------------------------------------
def assemble_bundle(teg_num: int, mode: str = "balanced", tone: str = "house",
                    top_n: Optional[int] = 50,
                    events_cache: Optional[list] = None,
                    venue_cache: Optional[dict] = None) -> Tuple[dict, list]:
    """Build the token-lean input bundle (beats + arcs + venue) for the LLM.

    `top_n` (default 50) trims the `beats` array to the highest-scoring N events,
    saving input tokens on the story-plan and dry-draft calls. `competition_arcs`
    are always preserved in full regardless — they're extracted by event type
    (trophy_win / jacket_win / wooden_spoon), so trimming beats never loses them.
    Pass `top_n=None` to disable trimming.

    `events_cache` / `venue_cache` allow a caller to compute the (expensive)
    `build_notable_events` + `build_venue_context` once per TEG and reuse them
    across multiple bundle calls (used by the backfill orchestrator).
    """
    events = events_cache if events_cache is not None else build_notable_events(teg_num, mode=mode)
    venue = venue_cache if venue_cache is not None else build_venue_context(teg_num)

    arcs: dict = {}
    all_beats = []
    MANDATORY_TYPES = {"hole_in_one", "eagle", "feat_hole_in_one", "feat_eagles",
                       "trophy_win", "jacket_win", "wooden_spoon"}
    for i, e in enumerate(events, 1):
        beat_id = f"b{i:02d}"
        ctx = dict(e.context)
        arc = ctx.pop("arc", None)
        if arc and e.type in _ARC_KEY:
            arcs[_ARC_KEY[e.type]] = arc
        # Mandatory = HIO / eagle / spine / rarity-7+ / any double-figure score
        is_double_figure = bool(e.holes) and (e.holes[0].get("sc", 0) >= 10)
        mandatory = (e.type in MANDATORY_TYPES
                     or e.rarity >= 7
                     or is_double_figure)
        all_beats.append({
            "id": beat_id,
            "total": e.total,
            "scope": e.scope,
            "type": e.type,
            "round": e.round,
            "course": e.course,
            "headline": e.headline,
            "players": e.players,
            "scores": {"importance": e.importance, "rarity": e.rarity,
                       "entertainment": e.entertainment},
            "mandatory": mandatory,
            "holes": e.holes,
            "context": {k: v for k, v in ctx.items() if v is not None},
        })

    # Trim beats to top-N by score; events are already sorted desc by `total`.
    # ALWAYS preserve mandatory beats (HIO, eagle, double-figure scores, all-time
    # top-3 rounds, PBs, spine wins) — they must not be trimmed even if other
    # beats outscore them on the combined `total`. Arcs are unaffected.
    if top_n is not None:
        keep_ids = {b["id"] for b in all_beats[:top_n]}
        for b in all_beats:
            if b["mandatory"]:
                keep_ids.add(b["id"])
        beats = [b for b in all_beats if b["id"] in keep_ids]
    else:
        beats = all_beats

    from teg_analysis.reporting.history_context import build_player_cross_teg_history
    from teg_analysis.reporting.course_history import (
        build_player_course_history, detect_course_records,
    )
    from teg_analysis.core.data_loader import load_all_data
    # Restrict player_history to players who actually played in THIS TEG.
    # Without this, the bundle carries career context for every historical
    # player, which can lead the writer to confabulate non-participants into
    # player-by-player summary (observed: Henry Meller added to TEG 10 closing list).
    _df = load_all_data()
    _current_players = set(_df[_df["TEGNum"] == teg_num]["Player"].unique())
    _full_history = build_player_cross_teg_history(teg_num, df=_df)
    player_history = {p: h for p, h in _full_history.items() if p in _current_players}

    # Per-player per-course history (P2b): first visits, PBs on course, deltas
    player_course_history = build_player_course_history(teg_num, df=_df)

    # Course records (P2c): wired into the beats list as mandatory beats so
    # they cannot be skipped. Course records only count on courses with >=3
    # prior visits across all TEGs.
    course_record_events = detect_course_records(teg_num, df=_df)
    for cr_idx, ev in enumerate(course_record_events, 1):
        beat_id = f"cr{cr_idx:02d}"
        beats.append({
            "id": beat_id,
            "total": 10.0,            # max salience — these are mandatory
            "scope": "round",
            "type": ev["type"],       # 'course_record_low' or 'course_record_high'
            "round": ev["round"],
            "course": ev["course"],
            "headline": ev["summary_fact"],
            "players": [ev["player"]],
            "scores": {"importance": 10.0, "rarity": 10.0, "entertainment": 7.0},
            "mandatory": True,
            "holes": [],
            "context": {
                "gross": ev["gross"],
                "prior_record": ev["prior_record"],
                "n_prior_visits": ev["n_prior_visits"],
                "summary_fact": ev["summary_fact"],
            },
        })

    # All-time streak and score-count records (P3): the TEG-level analogue of
    # course records above, same reasoning — wired into `beats` as mandatory so
    # the LLM has a grounded beat to hang "this ties the all-time record" on,
    # rather than being left to infer it. See milestone_records.py docstring.
    from teg_analysis.reporting.milestone_records import (
        detect_streak_records, detect_score_count_records,
    )
    streak_record_events = detect_streak_records(teg_num, df=_df)
    for sr_idx, ev in enumerate(streak_record_events, 1):
        beat_id = f"sr{sr_idx:02d}"
        beats.append({
            "id": beat_id,
            "total": 10.0,
            "scope": "tournament",
            "type": ev["type"],
            "round": ev["round"],
            "course": None,
            "headline": ev["summary_fact"],
            "players": [ev["player"]],
            "scores": {"importance": 8.0, "rarity": 9.0, "entertainment": 6.0},
            "mandatory": True,
            "holes": [],
            "context": {
                "streak_type": ev["streak_type"],
                "value": ev["value"],
                "prior_record": ev["prior_record"],
                "location": ev["location"],
                "summary_fact": ev["summary_fact"],
            },
        })

    score_count_record_events = detect_score_count_records(teg_num, df=_df)
    for sc_idx, ev in enumerate(score_count_record_events, 1):
        beat_id = f"sc{sc_idx:02d}"
        beats.append({
            "id": beat_id,
            "total": 10.0,
            "scope": "tournament",
            "type": ev["type"],
            "round": None,
            "course": None,
            "headline": ev["summary_fact"],
            "players": [ev["player"]],
            "scores": {"importance": 6.0, "rarity": 8.0, "entertainment": 6.0},
            "mandatory": True,
            "holes": [],
            "context": {
                "score_type": ev["score_type"],
                "count": ev["count"],
                "summary_fact": ev["summary_fact"],
            },
        })

    # Tournament-shape signals: today only `close_finish`. When true the editor
    # must lead with the close-finish framing (see SYSTEM_PROMPT). Other shape
    # patterns (procession, wire-to-wire) come through in the telling, not the
    # framing — they are NOT surfaced as signals.
    from teg_analysis.reporting.tournament_shape import (
        detect_close_finish, recent_vehicle_choices,
    )
    tournament_shape_signals = detect_close_finish(arcs, trophy_metric(teg_num))

    # Anti-context: what the most recent reports' vehicles looked like, so the
    # editor has a deliberate variation signal (soft rule).
    recent_vehicles = recent_vehicle_choices(teg_num)

    # Free, deterministic candidate signal: how well each vehicle fits THIS
    # TEG's actual facts, scored from beats/arcs/shape/history already built
    # above. Normalized against the checked-in historical baseline (z-score)
    # when it's present — a raw score alone doesn't say whether a pattern is
    # unusual for a TEG or present in almost every one (see vehicle_fit.py's
    # module docstring: an early version returned the same top-4 vehicles for
    # every TEG tested until this normalization was added). Falls back to the
    # raw ranking if the cache is somehow missing. Advisory either way — see
    # the module docstring for why this doesn't replace editorial judgement.
    from teg_analysis.reporting.vehicle_fit import (
        score_vehicle_fit, rank_vehicle_fit, normalize_vehicle_fit, load_baseline_cache,
    )
    # NOTE: `all_beats`, NOT the trimmed `beats`. The `top_n` trim is a token
    # budget for the LLM call — it says nothing about what happened in the
    # tournament — but several vehicles (tragic_arc, redemption_arc, catalogue)
    # score as a SUM over beats, so trimming silently deflated them. Worse, the
    # checked-in baseline is generated via `score_vehicle_fit_for_teg`, which
    # passes `top_n=None`, so live z-scores were comparing a trimmed raw score
    # against an untrimmed population mean.
    #
    # Measured on TEG 6 (2026-08-13): tragic_arc raw 79.5 untrimmed vs 32.7 at
    # top_n=50, i.e. z +2.70 vs +0.06 — enough to drop it from rank 1 to rank 5
    # and hand the top hint to hero_arc. Every hint list generated before this
    # fix was skewed against the beat-sum vehicles.
    _raw_vehicle_scores = score_vehicle_fit(all_beats, arcs, tournament_shape_signals,
                                            player_history)
    _baseline = load_baseline_cache()
    if _baseline:
        vehicle_fit_hints = normalize_vehicle_fit(_raw_vehicle_scores, _baseline)[:5]
    else:
        vehicle_fit_hints = rank_vehicle_fit(_raw_vehicle_scores, n=5)

    # Free, deterministic candidate signal: beats clustered by shared subject
    # (player, repeated course, recurring failure motif) spanning 2+ rounds —
    # a candidate subplot list, same advisory shape as `vehicle_fit_hints`.
    # Same reasoning applies for using `all_beats` over the trimmed `beats`:
    # a cluster scores as a sum over its member beats, so trimming would
    # silently deflate it. See threads.py and STORYLINE_PLAN.md Phase 1.
    from teg_analysis.reporting.threads import detect_threads
    candidate_threads = detect_threads(all_beats, arcs)
    # Threads are SCORED from all_beats (see comment above — trimming would
    # deflate the sum), but their `beat_ids` must be filtered to the actual
    # bundle `beats` sent to the model. Found live (2026-08-19, TEG 14): the
    # editor cited beat_ids straight out of candidate_threads that were never
    # in `beats` at all — `check_plan_consistency`'s grounding check correctly
    # caught it as "cites unknown beat_ids", but the bundle handed the model
    # phantom IDs to begin with. A thread that loses all its members this way
    # is dropped; one still worth surfacing keeps only its in-bundle beats.
    _in_bundle_ids = {b["id"] for b in beats}
    candidate_threads = [
        {**t, "beat_ids": [bid for bid in t["beat_ids"] if bid in _in_bundle_ids]}
        for t in candidate_threads
    ]
    candidate_threads = [t for t in candidate_threads if t["beat_ids"]]

    # Verified player relationships. Only ties listed here are facts; the
    # writer is forbidden from inferring any others from shared surnames.
    from teg_analysis.constants import PLAYER_RELATIONSHIPS
    # Filter to relationships where BOTH players were in this TEG.
    _current_players_proper = {" ".join(w.capitalize() for w in p.split())
                               for p in _current_players}
    player_relationships = [
        r for r in PLAYER_RELATIONSHIPS
        if all(p in _current_players_proper for p in r["players"])
    ]

    # WHY each competition was won, computed deterministically — see
    # win_anatomy.py. `competition_arcs` carries the what (leader by round, lead
    # changes); this carries the causation the editor was previously left to
    # infer from a pile of beats.
    from teg_analysis.reporting.win_anatomy import build_win_anatomy
    win_anatomy = build_win_anatomy(teg_num)

    bundle = {
        "teg": teg_num,
        "tone": tone,
        "trophy_metric": trophy_metric(teg_num),
        "venue": venue,
        "competition_arcs": arcs,
        "win_anatomy": win_anatomy,
        "player_history": player_history,
        "player_course_history": player_course_history,
        "player_relationships": player_relationships,
        "tournament_shape": tournament_shape_signals,
        "recent_vehicle_choices": recent_vehicles,
        "vehicle_fit_hints": vehicle_fit_hints,
        "candidate_threads": candidate_threads,
        "beats": beats,
    }
    return bundle, events


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def build_story_plan(teg_num: int, mode: str = "balanced", tone: str = "house",
                     dry_run: bool = False, model: Optional[str] = None,
                     events_cache: Optional[list] = None,
                     venue_cache: Optional[dict] = None) -> dict:
    """Produce the story plan for a TEG.

    dry_run=True writes the exact prompt + bundle to disk and skips the API call.
    Otherwise calls the LLM, returns the validated StoryPlan, and writes the JSON.
    `events_cache` / `venue_cache` enable per-TEG reuse (see `assemble_bundle`).
    """
    bundle, events = assemble_bundle(teg_num, mode=mode, tone=tone,
                                     events_cache=events_cache, venue_cache=venue_cache)
    user_message = ("Plan the report for the following TEG. Use ONLY this data.\n\n"
                    + json.dumps(bundle, indent=2, ensure_ascii=False))

    if dry_run:
        path = f"{output_dir()}/teg_{teg_num}_story_plan_prompt.md"
        with open(path, "w") as f:
            f.write("# SYSTEM PROMPT (cached)\n\n" + SYSTEM_PROMPT
                    + "\n\n---\n\n# USER MESSAGE\n\n" + user_message + "\n")
        return {"dry_run": True, "prompt_path": path,
                "n_beats": len(bundle["beats"]),
                "user_chars": len(user_message),
                "competitions_in_arcs": sorted(bundle["competition_arcs"].keys())}

    plan, usage = llm.generate_structured(SYSTEM_PROMPT, user_message, StoryPlan,
                                          max_tokens=20000,
                                          model=model or llm.DEFAULT_MODEL,
                                          stage="story_plan", label=f"teg{teg_num}")
    out_path = f"{output_dir()}/teg_{teg_num}_story_plan.json"
    with open(out_path, "w") as f:
        json.dump(plan.model_dump(), f, indent=2, ensure_ascii=False)
    # Combination-level checks the schema can't express (close-finish rule,
    # mandatory-beat coverage). Surfaced, not raised: a plan that trips one is
    # still usable, but it must not pass silently the way it did for four TEGs.
    plan_warnings = check_plan_consistency(plan, bundle)
    for w in plan_warnings:
        print(f"[story_plan] WARNING TEG {teg_num}: {w}")
    return {"dry_run": False, "plan": plan, "usage": usage, "output_path": out_path,
            "warnings": plan_warnings}
