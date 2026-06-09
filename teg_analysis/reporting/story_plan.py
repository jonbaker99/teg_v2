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

from teg_analysis.reporting.era import trophy_metric
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


class Payoff(BaseModel):
    """Explicit setup→payoff pair: a foreshadow seed and the section that resolves it.

    Addresses the foreshadow-without-payoff thinness identified in prior reports:
    seeds get planted in the opener but the body never resolves them. Each
    `foreshadow[]` seed should have a corresponding `payoffs[]` entry.
    """
    seed: str           # short reference to the seed planted in foreshadow[]
    resolves_in: str    # which section pays it off (e.g. "Round 3", "men in brief", "How it was decided")
    payoff: str         # one-line description of how it resolves


class StoryPlan(BaseModel):
    title: str
    title_candidates: list[str]
    theme: str                      # the one-line through-line / spine
    tone: str                       # resolved register for this report
    narrative_structure: str        # "chronological" | "in_medias_res" | "theme_led" | free-form one-liner
    opening_hook: str               # one-line description of what the report opens with (and why)
    narrative_vehicles: list[str] = []  # 1-3 named storytelling vehicles (see SYSTEM_PROMPT menu)
    foreshadow: list[str]           # hooks to plant early that pay off later
    competitions: list[Competition] # Trophy, Green Jacket, Wooden Spoon (priority order)
    rounds: list[RoundPlan]
    players: list[PlayerArc]
    must_include_beat_ids: list[str]
    cuts: list[str]                 # beat ids (or notes) to deliberately leave out
    venue_notes: str
    # --- Thread-organised storyline content (optional; populated when interesting) ---
    # Each list/dict is empty by default. The editor populates them when the data
    # supports a thread worth feeding to the writer. The writer uses these as
    # additional palette material; none is individually required, but every
    # foreshadow[] seed SHOULD have a matching payoffs[] entry.
    competition_storyline_bullets: dict[str, list[str]] = {}  # {"Trophy": [...], "Green Jacket": [...], "Wooden Spoon": [...]}
    player_storyline_bullets: dict[str, list[str]] = {}        # {player_name: [...bullets...]}
    course_history_notes: list[str] = []                       # per-course-history beats worth foregrounding
    decisive_moments: list[str] = []                           # one line per competition naming THE decisive moment
    prominent_vehicle: str = ""                                # name of the palette vehicle the editor is foregrounding
    payoffs: list[Payoff] = []                                 # setup→payoff pairs; one per foreshadow seed where possible


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

YOUR JOB:
- Choose the story: one clear `theme` that runs through the whole report, and 2-4 \
`foreshadow` hooks to plant early that pay off later.
- Choose a `narrative_structure` and an `opening_hook` for the report. \
`narrative_structure` is one of `chronological` | `in_medias_res` | `theme_led` \
(or a one-line free-form description if none fits). `opening_hook` is a one-line \
description of what the report opens with, and why. **Chronological is a default, \
not a requirement** — favour non-chronological framing when the climax matters more \
than the build-up (open with the decisive moment then flash back to how it came \
about), or when the real story is a theme that cuts across rounds.

- Choose **1–3 `narrative_vehicles`** that frame the report. These are NAMED \
storytelling vehicles drawn from sports / longform conventions. Pick from the menu \
below or invent a vehicle you can name in a phrase. The writer reads these as a \
steer for how to shape the prose. The menu is grouped (structural / character-driven \
/ thematic) for scanning, not by preference — pick whichever genuinely apply, and \
**vary your picks across reports**: if every TEG ends up `hero_arc + bookends`, the \
reports become formulaic.

  TOURNAMENT-SHAPE (what happened over the four days):
    - `counterfactual`      — close / decided late ("but for X, Y would have won")
    - `dual_narrative`      — two players' weeks intertwined
    - `tragic_arc`          — protagonist's collapse drove the tournament
    - `motif`               — a recurring image / hole / number carried as connective tissue
    - `bookends`            — open and close at the same scene / hole / moment
    - `ensemble`            — the field collectively; course as protagonist
    - `catalogue`           — inventory of a recurring failure mode
    - `inevitability`       — wire-to-wire procession  (NOTE: only use as a SUPPORTING \
vehicle, never `prominent_vehicle` — processions come through in the telling, not the \
framing)

  HISTORICAL-CONTEXT (the framing around the result):
    - `hero_arc`            — protagonist's career trajectory carries the report
    - `comeback`            — long drought / redemption (first win since TEG N, etc.)
    - `inversion`           — reigning holder dethroned / previous-loser elevated
    - `origin`              — first win / debut / breakthrough
    - `underdog`            — unlikely triumph from prior history

  STYLISTIC (how to tell, pure judgement):
    - `chronological`       — straight tournament timeline; R1 → R4
    - `in_medias_res`       — open mid-action, then loop back
    - `reverse_chronology`  — start at the result, walk backwards through cause
    - `three_act`           — setup / confrontation / resolution
    - `theme_led_body`      — body organised around an idea, not rounds

  Multiple vehicles can nest: e.g. `["bookends", "hero_arc", "comeback"]` or \
`["inversion", "dual_narrative"]`. Pick what's MOST INTERESTING about THIS \
tournament; don't reach for the same pattern by reflex.

  **HARD RULE — close finish overrides everything.** The bundle's \
`tournament_shape.close_finish` is computed deterministically from the Trophy \
arc (small margin and/or a contested R4). When it is `true`, the close finish \
IS the story: `prominent_vehicle` MUST be `counterfactual` (or `dual_narrative` \
if two players carried the finish), and the close-finish framing leads the \
report. Historical-context vehicles (`comeback`, `origin`, `inversion`, \
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

THREAD-ORGANISED STORYLINE FIELDS — **DEFAULT IS TO POPULATE THESE, NOT LEAVE EMPTY.** \
The writer relies on them to thread context through the prose; empty fields mean a \
thinner report. Populate every one for which the data offers any material; the \
specific per-field guidance below names the narrow cases where empty is acceptable:

- `decisive_moments`: **ALWAYS 3 entries** (Trophy, Green Jacket, Wooden Spoon — in \
that order). Each is one line naming THE moment the result was effectively decided. \
Draw from `competition_arcs[*].decisive_moment` plus your editorial judgement. \
Example: "R1 H16 par at Royal Cinque Ports — Mullin's outright Trophy lead, never \
headed across the next 56 holes". Leaving any of these empty is wrong — every \
competition has a decisive moment, even a wire-to-wire procession (where the \
decisive moment is the round / hole the cushion became unrecoverable).

- `prominent_vehicle`: **ALWAYS populated.** Pick the palette vehicle the writer \
should foreground: one of `cross_teg_career` | `course_history` | `venue_character` \
| `decisive_moment` | `player_thread` | `records` | `foreshadow_payoff`. The writer \
is required to make at least one vehicle prominent; you tell them which. Choose \
whichever is most interesting about THIS tournament — if multiple feel equal, pick \
the one most likely to vary the framing across reports.

- `payoffs`: **one entry per `foreshadow[]` seed.** If you have 4 foreshadows you \
should have ~4 payoffs. Each entry: `seed` (short ref to the seed), `resolves_in` \
(which section pays it off — e.g. "Round 4", "How the three were decided", "the men \
in brief"), `payoff` (one-line description). This addresses the biggest thinness in \
past reports: seeds planted in the opener that the body never resolved. An \
unresolved foreshadow is a bug.

- `competition_storyline_bullets`: **typically 3–6 factual bullets per competition** \
("Trophy", "Green Jacket", "Wooden Spoon"). Each bullet is a fact + a connection — \
not a round-by-round chronicle but the causal arc. "Mullin's R1 +4 opened a 14-shot \
Jacket cushion that he was never asked to defend" beats "Mullin shot +4 in R1". \
Empty is only acceptable for a competition whose arc is literally "X led wire-to-wire \
and won; nothing else happened" — almost no TEG has all three competitions that flat.

- `player_storyline_bullets`: **2–4 factual bullets per principal player** \
(certainly the three competition winners and the Spoon holder; usually the runners-up \
too; mid-pack players who carry a recurring thread, like a habitual blow-up artist, \
also). Different role from the one-line `arc`: the bullets carry the connective \
tissue the writer riffs off. Empty only when this TEG is genuinely a two-man story \
(very rare).

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
    # "men in brief" (observed: Henry Meller added to TEG 10 closing list).
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

    bundle = {
        "teg": teg_num,
        "tone": tone,
        "trophy_metric": trophy_metric(teg_num),
        "venue": venue,
        "competition_arcs": arcs,
        "player_history": player_history,
        "player_course_history": player_course_history,
        "player_relationships": player_relationships,
        "tournament_shape": tournament_shape_signals,
        "recent_vehicle_choices": recent_vehicles,
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
