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
from typing import Optional, Tuple

from pydantic import BaseModel

from teg_analysis.reporting.events import build_notable_events
from teg_analysis.reporting.venue import build_venue_context
from teg_analysis.reporting import llm

OUTPUT_DIR = "data/commentary"

_ARC_KEY = {"trophy_win": "trophy", "jacket_win": "jacket", "wooden_spoon": "spoon"}


# ---------------------------------------------------------------------------
# Output schema (what the LLM must return)
# ---------------------------------------------------------------------------
class Competition(BaseModel):
    name: str                       # "Trophy" | "Green Jacket" | "Wooden Spoon"
    winner_or_loser: str
    how: str                        # how it was won (or lost, for the Spoon)
    key_beat_ids: list[str]


class RoundPlan(BaseModel):
    round: int
    headline_candidates: list[str]  # ~3 witty options
    chosen_headline: str
    angle: str                      # one line: what this round is about
    beat_ids: list[str]


class PlayerArc(BaseModel):
    player: str
    arc: str


class StoryPlan(BaseModel):
    title: str
    title_candidates: list[str]
    theme: str                      # the one-line through-line / spine
    tone: str                       # resolved register for this report
    narrative_structure: str        # "chronological" | "in_medias_res" | "theme_led" | free-form one-liner
    opening_hook: str               # one-line description of what the report opens with (and why)
    foreshadow: list[str]           # hooks to plant early that pay off later
    competitions: list[Competition] # Trophy, Green Jacket, Wooden Spoon (priority order)
    rounds: list[RoundPlan]
    players: list[PlayerArc]
    must_include_beat_ids: list[str]
    cuts: list[str]                 # beat ids (or notes) to deliberately leave out
    venue_notes: str


# ---------------------------------------------------------------------------
# System prompt (stable / cacheable)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are the editor planning a newspaper-style report on a TEG \
(an amateur golf tournament of several rounds). You do NOT write prose here — you \
produce a STRUCTURED PLAN that a writer will follow.

AUDIENCE: the players themselves — insiders who know each other, the courses, and \
the history. They will spot any factual error instantly, and they enjoy reliving \
the tournament and being gently ribbed.

HOUSE VOICE (for the writer who follows your plan): faithful, entertaining, \
tongue-in-cheek — in the spirit of Barney Ronay (Guardian) and Tom Peck (Times \
political sketches). Witty and characterful, but always anchored in the facts; \
never zany or over the top.

THE SPINE — the report is built around the three competitions, in this priority order:
1. The Trophy (Stableford) — the main event.
2. The Green Jacket (Gross).
3. The Wooden Spoon (last place on Stableford).
For each you MUST explain HOW it was won (or, for the Spoon, lost): the decisive \
moments, lead changes, and trajectory. Draw on the competition_arcs provided.

INPUT (JSON in the user turn):
- competition_arcs: leader-by-round, winner/loser trajectory, lead changes and the \
decisive moment for each competition.
- beats: a ranked list of notable events. Each has an `id`, three scores \
(importance = contribution to the result; rarity = how noteworthy in TEG history; \
entertainment = colour independent of the result), and hole-by-hole `holes` \
evidence. ALWAYS refer to beats by their `id`.
- venue: course one-liners and whether TEG has played here before.
- tone: a requested register; default to the house voice unless this overrides it.

YOUR JOB:
- Choose the story: one clear `theme` that runs through the whole report, and 2-4 \
`foreshadow` hooks to plant early that pay off later.
- Choose a `narrative_structure` and an `opening_hook` for the report. \
`narrative_structure` is one of `chronological` | `in_medias_res` | `theme_led` \
(or a one-line free-form description if none fits). `opening_hook` is a one-line \
description of what the report opens with, and why. **Chronological is a default, \
not a requirement** — favour non-chronological framing when the climax matters more \
than the build-up (open with the decisive moment then flash back to how it came \
about), or when the real story is a theme that cuts across rounds. The writer will \
follow whatever you choose.
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
- `title` + a few `title_candidates`; record the resolved `tone`.

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
- Output only the structured plan."""


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

    bundle = {
        "teg": teg_num,
        "tone": tone,
        "venue": venue,
        "competition_arcs": arcs,
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
        path = f"{OUTPUT_DIR}/teg_{teg_num}_story_plan_prompt.md"
        with open(path, "w") as f:
            f.write("# SYSTEM PROMPT (cached)\n\n" + SYSTEM_PROMPT
                    + "\n\n---\n\n# USER MESSAGE\n\n" + user_message + "\n")
        return {"dry_run": True, "prompt_path": path,
                "n_beats": len(bundle["beats"]),
                "user_chars": len(user_message),
                "competitions_in_arcs": sorted(bundle["competition_arcs"].keys())}

    plan, usage = llm.generate_structured(SYSTEM_PROMPT, user_message, StoryPlan,
                                          model=model or llm.DEFAULT_MODEL)
    out_path = f"{OUTPUT_DIR}/teg_{teg_num}_story_plan.json"
    with open(out_path, "w") as f:
        json.dump(plan.model_dump(), f, indent=2, ensure_ascii=False)
    return {"dry_run": False, "plan": plan, "usage": usage, "output_path": out_path}
