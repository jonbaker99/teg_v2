"""Round-report prototype: a single-round version of the tournament pipeline.

Mirrors the tournament pipeline (plan → dry draft → around-draft → lint) but
scoped to one round. Reuses `build_notable_events` filtered to the target round,
uses a smaller `RoundStoryPlan` schema, and has its own ROUND_* prompts because
the tournament framing ("how the three competitions were WON") doesn't apply
mid-tournament — for a round we describe race STATE, not winners.

Decision points exposed in the prompts and bundle so they can be tuned after
reading the first prototype:
- Round-level scoring weights (currently reuses the tournament `mode` weights;
  see `scoring.MODE_WEIGHTS`).
- Standalone readability vs. assumed tournament context.
- Mid-tournament "as it stands" framing of the three competitions.
"""

from __future__ import annotations

import json
from typing import Optional, Tuple, Union

from pydantic import BaseModel

from teg_analysis.reporting.era import trophy_metric
from teg_analysis.reporting.events import build_notable_events
from teg_analysis.reporting.venue import build_venue_context
from teg_analysis.reporting import llm

OUTPUT_DIR = "data/commentary"


# ---------------------------------------------------------------------------
# Output schema (smaller than tournament StoryPlan — no per-round breakdown)
# ---------------------------------------------------------------------------
class RoundCompetitionState(BaseModel):
    name: str               # "Trophy" | "Green Jacket" | "Wooden Spoon"
    leader_or_laggard: str  # who's at the top (or bottom for Spoon) at end of round
    score: float            # their cumulative score
    gap: float              # to the next position
    note: str               # one-line: what happened to this race in the round
                            # (e.g. "Patterson took outright lead at the par-5 7th and never gave it back")


class RoundPlayerArc(BaseModel):
    player: str
    arc: str                # one-line arc FOR THIS ROUND


class RoundStoryPlan(BaseModel):
    title: str
    title_candidates: list[str]
    theme: str              # one-line through-line for the round
    tone: str
    narrative_structure: str  # "chronological" | "in_medias_res" | "theme_led" | free-form
    opening_hook: str       # one-line: what the report opens with
    foreshadow: list[str]   # earlier-round events that pay off later in the round
    competition_state: list[RoundCompetitionState]
    key_beat_ids: list[str]
    players: list[RoundPlayerArc]
    venue_notes: str


# ---------------------------------------------------------------------------
# Round-state helpers (deterministic; no LLM)
# ---------------------------------------------------------------------------
def _competition_state_at_round(teg_num: int, round_num: int) -> list[dict]:
    """End-of-round Trophy/Jacket/Spoon snapshot from cumulative round summary.

    Returns [] if `round_num < 1` (used to represent "before round 1" / no prior state).
    """
    if round_num < 1:
        return []
    from teg_analysis.analysis.commentary import create_round_summary
    rs = create_round_summary()
    rs = rs[(rs["TEGNum"] == teg_num) & (rs["Round"] == round_num)].copy()
    if rs.empty:
        return []

    metric = trophy_metric(teg_num)
    if metric == "net_vs_par":
        trophy_col = "Cumulative_Tournament_Score_NetVP"
        trophy_ascending = True
    else:
        trophy_col = "Cumulative_Tournament_Score_Stableford"
        trophy_ascending = False

    trophy = rs.sort_values(trophy_col, ascending=trophy_ascending)
    jacket = rs.sort_values("Cumulative_Tournament_Score_Gross", ascending=True)
    t_rows = trophy.to_dict("records")
    j_rows = jacket.to_dict("records")

    def _standings(rows, col):
        return [{"pl": r["Pl"], "player": r["Player"], "score": int(r[col])} for r in rows]

    if metric == "net_vs_par":
        # lower is better: leader is t_rows[0] (lowest score); gap = runner_up - leader
        trophy_gap = int(t_rows[1][trophy_col] - t_rows[0][trophy_col])
        spoon_gap = int(t_rows[-1][trophy_col] - t_rows[-2][trophy_col])
    else:
        # higher is better: leader is t_rows[0] (highest score); gap = leader - runner_up
        trophy_gap = int(t_rows[0][trophy_col] - t_rows[1][trophy_col])
        spoon_gap = int(t_rows[-2][trophy_col] - t_rows[-1][trophy_col])

    return [
        {
            "name": "Trophy",
            "leader": t_rows[0]["Player"],
            "leader_pl": t_rows[0]["Pl"],
            "leader_score": int(t_rows[0][trophy_col]),
            "runner_up": t_rows[1]["Player"],
            "gap": trophy_gap,
            "standings": _standings(t_rows, trophy_col),
        },
        {
            "name": "Green Jacket",
            "leader": j_rows[0]["Player"],
            "leader_pl": j_rows[0]["Pl"],
            "leader_score": int(j_rows[0]["Cumulative_Tournament_Score_Gross"]),
            "runner_up": j_rows[1]["Player"],
            "gap": int(j_rows[1]["Cumulative_Tournament_Score_Gross"]
                       - j_rows[0]["Cumulative_Tournament_Score_Gross"]),
            "standings": _standings(j_rows, "Cumulative_Tournament_Score_Gross"),
        },
        {
            "name": "Wooden Spoon",
            "laggard": t_rows[-1]["Player"],
            "laggard_pl": t_rows[-1]["Pl"],
            "laggard_score": int(t_rows[-1][trophy_col]),
            "gap_to_next": spoon_gap,
        },
    ]


# ---------------------------------------------------------------------------
# Bundle assembly
# ---------------------------------------------------------------------------
def _prior_rounds_context(teg_num: int, round_num: int, all_events: list) -> list[dict]:
    """For rounds R≥2, summarise each completed prior round.

    Returns a list of dicts, one per prior round (oldest first):
        {round, standings_end_of_round, top_beats: [{id, headline, type, players}]}

    The top beats are the 6 highest-scored events from that round (no hole detail —
    just enough for the planner and writer to reference by player and event type).
    """
    if round_num <= 1:
        return []
    prior = []
    for r in range(1, round_num):
        r_events = sorted(
            [e for e in all_events if e.round == r],
            key=lambda e: e.total, reverse=True,
        )
        top_beats = [
            {
                "id": f"r{r}_prior_{i+1:02d}",
                "headline": e.headline,
                "type": e.type,
                "players": e.players,
                "scores": {"importance": e.importance, "rarity": e.rarity,
                           "entertainment": e.entertainment},
            }
            for i, e in enumerate(r_events[:6])
        ]
        prior.append({
            "round": r,
            "standings_end_of_round": _competition_state_at_round(teg_num, r),
            "top_beats": top_beats,
        })
    return prior


def assemble_round_bundle(teg_num: int, round_num: int, mode: str = "balanced",
                          tone: str = "house",
                          events_cache: Optional[list] = None,
                          venue_cache: Optional[dict] = None) -> Tuple[dict, list]:
    """Build the LLM input bundle for round-report stages.

    `events_cache` / `venue_cache` allow per-TEG reuse — when an orchestrator
    runs the tournament + 4 round reports for the same TEG, recomputing
    `build_notable_events` 5 times is wasteful.
    """
    all_events = events_cache if events_cache is not None else build_notable_events(teg_num, mode=mode)
    round_events = [e for e in all_events if e.round == round_num]

    venue_full = venue_cache if venue_cache is not None else build_venue_context(teg_num)
    round_venue = next(
        (r for r in venue_full.get("rounds", []) if r.get("round") == round_num),
        None,
    )
    total_rounds = len(venue_full.get("rounds", []))
    is_final_round = (round_num == total_rounds) and total_rounds > 0

    beats = []
    MANDATORY_TYPES = {"hole_in_one", "eagle"}
    for i, e in enumerate(round_events, 1):
        ctx = dict(e.context)
        ctx.pop("arc", None)
        is_double_figure = bool(e.holes) and (e.holes[0].get("sc", 0) >= 10)
        mandatory = (e.type in MANDATORY_TYPES
                     or e.rarity >= 7
                     or is_double_figure)
        beats.append({
            "id": f"r{round_num}_b{i:02d}",
            "total": e.total,
            "scope": e.scope,
            "type": e.type,
            "course": e.course,
            "headline": e.headline,
            "players": e.players,
            "scores": {"importance": e.importance, "rarity": e.rarity,
                       "entertainment": e.entertainment},
            "mandatory": mandatory,
            "holes": e.holes,
            "context": {k: v for k, v in ctx.items() if v is not None},
        })

    bundle = {
        "teg": teg_num,
        "round": round_num,
        "is_final_round": is_final_round,
        "total_rounds": total_rounds,
        "tone": tone,
        "trophy_metric": trophy_metric(teg_num),
        "round_venue": round_venue,
        "area_context": {
            "area": venue_full.get("area"),
            "year": venue_full.get("year"),
            "area_visit": venue_full.get("area_visit"),
        },
        "competition_state_end_of_round": _competition_state_at_round(teg_num, round_num),
        "competition_state_prior": _competition_state_at_round(teg_num, round_num - 1),
        "prior_rounds": _prior_rounds_context(teg_num, round_num, all_events),
        "beats": beats,
    }
    return bundle, round_events


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
ROUND_PLAN_SYSTEM = """You are the editor planning a newspaper-style report on ONE \
ROUND of a TEG (an amateur golf tournament of several rounds). You do NOT write \
prose here — you produce a STRUCTURED PLAN that a writer will follow.

AUDIENCE: the players themselves — insiders who know each other, the courses, and \
the history. They will spot any factual error instantly.

HOUSE VOICE (for the writer who follows your plan): faithful, entertaining, \
tongue-in-cheek — in the spirit of Barney Ronay (Guardian) and Tom Peck (Times \
political sketches). Witty and characterful, but always anchored in the facts; \
never zany or over the top.

THIS IS A ROUND REPORT, NOT A TOURNAMENT REPORT.
- The round is ONE day of the tournament: 18 holes, all players.
- If `is_final_round` is FALSE: the three competitions (Trophy / Green Jacket / \
Wooden Spoon) have STATE here, not winners. Describe how each race shifted in \
the round, drawing on `competition_state_prior` vs `competition_state_end_of_round`. \
Do not declare anyone the tournament champion.
- If `is_final_round` is TRUE: this round IS the tournament's resolution. The plan \
should declare Trophy / Green Jacket / Wooden Spoon WINNERS and final margins. \
Foreshadow hooks become payoff hooks. A single dominant story arc (the winning \
shot, the decisive collapse) is more defensible here than in a mid-tournament round.
- The round IS the unit. There is no per-round breakdown — the report covers one \
round.

INPUT (JSON in the user turn):
- is_final_round: boolean — whether this round is the tournament's final round
- total_rounds: the total round count for this TEG
- competition_state_end_of_round: per-competition leader/laggard, score, gap, \
plus full standings list
- competition_state_prior: same shape, for end of previous round (empty if R1)
- prior_rounds (R≥2 only): for each completed prior round — end-of-round standings \
and the top 6 beats from that round. Use this for callbacks and trajectory colour.
- beats: ranked notable events FROM THIS ROUND ONLY. ALWAYS refer by `id`.
- round_venue: course, date, visit count
- area_context: location and area visit count
- tone: requested register

YOUR JOB:
- Choose the round's STORY: a clear one-line `theme`, and 2-3 `foreshadow` hooks \
(events earlier in the round that pay off later — e.g. "early blow-up at the 4th \
that came back to haunt him at the 18th").
- Choose a `narrative_structure`. **The default for a round report is \
`chronological` or `player_by_player`** — these two reliably cover every notable \
player and read cleanly. `in_medias_res` and `theme_led` are reserved for rounds \
with a SINGLE dominant story arc (one player's record round, one decisive \
collapse, one moment that defines the day). If you choose either of those, the \
`opening_hook` must clearly justify the choice. For final rounds, theme-led / \
in_medias_res becomes more defensible (the round often has a natural coronation \
shape).
- Set `opening_hook` to a one-line description of what to open with and why.
- Select 5-8 `key_beat_ids` the report MUST cover. **NON-NEGOTIABLE: every beat \
marked `"mandatory": true` MUST appear in `key_beat_ids`.** Mandatory beats are \
TEG records, personal bests, rare feats (holes-in-one, eagles), and any \
double-figure gross score. The players will notice any omission of these.
- For each principal player, a one-sentence `arc` FOR THIS ROUND (what they did, \
what it meant). EVERY notable player must have an entry — the writer needs to \
cover them all.
- Build a `competition_state` array — for Trophy / Green Jacket / Wooden Spoon: \
the leader_or_laggard, their cumulative score, the gap to the next position, AND \
a `note` describing what happened to that race in the round (lead taken, lead \
held, gap widened, lead changes mid-round, etc.). Draw on prior state to describe \
what changed. For final rounds, the `note` describes how the race was WON (or \
lost, for the Spoon).
- `venue_notes`: any course/area context to weave in.
- `title` + a few `title_candidates`; record the resolved `tone`.
- Use `prior_rounds` (when present) to set foreshadow hooks and player arcs in \
context: e.g. "Baker recovering from a disastrous R1", "Mullin extending his \
overnight lead". Only reference prior events when they add genuine trajectory \
or contrast — don't pad.

SELECTION PRINCIPLES:
- Favour high-importance beats for the spine; high-rarity for one-line callouts; \
high-entertainment for colour.
- Early-round lead changes within a single round, when the field is bunched, are \
routine; late-round shifts matter more.
- **Stableford and Gross measure DIFFERENT things** — Stableford is \
handicap-adjusted, Gross is raw shots. A player leading one and trailing the \
other is normal handicapping, NOT paradox. Don't plan a theme or player arc that \
frames the split as schizophrenic, contradictory, a "unique double", or any kind \
of head-scratcher.
- The Trophy metric is `trophy_metric` in the bundle: Stableford (higher is better) \
for TEG 8+; net-vs-par (lower is better, signed like +47) for TEGs 1–7.

RULES:
- Use ONLY the supplied data. Never invent.
- For non-final rounds: describe race STATE, not WINNERS.
- For final rounds: declare race WINNERS and final margins.
- **TEG has NO countback, NO tiebreakers, NO playoff.** Lead changes are caused \
by accumulated points (Stableford/net-vs-par for the Trophy, Gross for the Jacket). \
Never plan a theme or note that invokes "countback", "tiebreaker", or "playoff" \
— those mechanisms do not exist.
- Output only the structured plan."""


ROUND_DRY_DRAFT_SYSTEM = """You are producing a DRY STORYLINE DRAFT for a \
single-round TEG report. This is a faithful, flat, checklist-style fact dump \
with NO colour, NO jokes, NO narrative hooks, NO characterisation, NO stylistic \
flourish. It is a scaffold and a fact-check, not the finished article. If you \
find yourself reaching for a compelling phrase, that phrase belongs in the \
writer's next pass — leave it out here.

You are given: a ROUND STORY PLAN (theme, opening hook, narrative structure, key \
beat ids, player arcs, competition state); the BEATS for this round (with \
hole-by-hole `holes` evidence); the COMPETITION STATE (end of round and prior); \
and the round VENUE.

Write the draft in this structure:
1. OVERVIEW — 2-3 factual sentences: best round of the day, worst round of the \
day, key result/movement in the three races.
2. THE ROUND — in plain prose, recount what happened, in chronological order \
unless the plan's `narrative_structure` chose otherwise. RENDER SPECIFIC HOLES \
from the beat evidence — e.g. "a quadruple-bogey 8 at the par-4 6th and an 11 at \
the par-5 18th", never a vague "a back-nine collapse". This hole-level \
specificity is the whole point of the draft. **Cover every notable player's round** \
— each principal must appear substantively in the prose.
3. RACE SHIFTS (only if material movement happened) — a short factual paragraph \
on how Trophy / Green Jacket / Wooden Spoon SHIFTED this round (leads taken, \
gaps halved or stretched, a race effectively settled, a player flipping into the \
Spoon). The standings BLOCK is appended deterministically later; do NOT restate \
the leader/score/gap (the block carries that). Skip this section entirely when \
nothing material happened in any of the three races.

RULES:
- Use ONLY the supplied facts. Never invent holes, scores, players, or events.
- Render real hole detail wherever the evidence supports it.
- Honour the data precisely: where a rival "drew level" rather than taking the \
lead outright, say "drew level", not "took the lead".
- For non-final rounds: describe race STATE/SHIFTS, not WINNERS.
- For final rounds (`is_final_round=true`): the race-shifts section becomes the \
race-results section — declare winners and final margins.
- No closing "Players" / "men, in brief" bullet list — coverage lives in section 2.
- **Prior rounds (R≥2).** Use `prior_rounds` for factual callbacks only: one-line \
references like "recovering from yesterday's 9-over R2" or "he held the overnight \
lead". No extended retelling of prior rounds.
- **Stroke index (SI).** If hole evidence includes `si`, note it factually where \
interesting: SI 1 = hardest hole on the course; SI 18 = easiest; SI 2–3 = one of \
the hardest; SI 16–17 = one of the easiest. SI 4–15: omit. One-word note only.
- **TEG has NO countback, NO tiebreakers, NO playoff.** Lead changes are caused by \
point accumulation: Stableford (TEG 8+) or net-vs-par (TEGs 1–7) for the Trophy; \
Gross for the Jacket. The bundle's `trophy_metric` identifies which era. Never \
write "countback", "tiebreaker", "on countback math" — those mechanisms do not \
exist. Tied scores: say "drew level" / "tied".
- **Arithmetic must be exact.** When asserting an over-par total across a stretch \
of holes, the figure must equal the precise sum of per-hole over-par (bogey = +1, \
double = +2, triple = +3, quad = +4, quint = +5, sext = +6). Compute, do NOT \
estimate. When awkward, list per-hole values without the running total.
- Plain, clear, British English. Short declarative sentences. **No narrative \
hooks** ("The day's defining number was..."), **no characterisation** ("the \
round of his life"), **no dramatisation** — that's the writer's job.
- Markdown headings. Keep it tight."""


ROUND_WRITER_SYSTEM = """You are a golf writer producing the finished, \
entertaining report on ONE ROUND of a TEG (an amateur golf tournament of several \
rounds), for an audience of THE PLAYERS THEMSELVES — insiders who know each \
other, the courses and the history, who want to relive the round and be gently \
ribbed, and who will instantly spot any factual error.

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

STRUCTURE — follow the ROUND STORY PLAN you are given:
- Open with the title and a paragraph that lands the theme — drawing on the \
plan's `opening_hook`.
- **Default narrative shape: `chronological` or `player_by_player` coverage.** \
These are the two acceptable defaults — both reliably cover every notable player \
and read cleanly. `in_medias_res` and `theme_led` are reserved for rounds with a \
SINGLE dominant story arc; only use one of those structures if the plan's \
`narrative_structure` calls for it AND the `opening_hook` justifies the choice.
- **Every notable player's round MUST be covered in the prose itself** — \
substantively, not as a passing mention. The core of the report is comprehensive \
player coverage, not editorial flourish. There is no closing player-bullet \
section (no "men, in brief"); coverage lives in the body.
- The round IS the unit. Don't break into sub-sections by nines or phases unless \
the story genuinely calls for it. Carry the theme; pay off the foreshadow hooks.
- Render specific holes drawn from the dry draft's hole evidence — concrete hole \
detail (par, score, hole number) is the point.
- **End-of-round standings are appended automatically by the renderer** (Trophy \
+ Green Jacket paragraphs). Do NOT write a "Where the races stand" / "State of \
play" section — it would duplicate the auto-injected block. The deterministic \
block carries the STATE.
- **Race-shift commentary (optional, encouraged when warranted).** Immediately \
before the auto-injected standings block, you SHOULD add a short paragraph on \
how the three races *shifted* this round when there is meaningful movement to \
describe — leads changing hands, gaps halving or stretching, a race effectively \
settled, the Spoon flipping at a specific hole, Jacket lead changed for the \
first time. This is about shifts, not state. Keep it tight; skip entirely when \
all three races held station.

FINAL ROUND (when `is_final_round` is true):
- Declare Trophy / Green Jacket / Wooden Spoon WINNERS explicitly, with final \
margins. Frame the round as a coronation (or capitulation) — the foreshadow \
hooks become payoff hooks. The race-shift paragraph (above) becomes a how-the- \
race-was-won paragraph.

RULES:
- Use ONLY the supplied facts. Never invent holes, scores, players, or events.
- **Every beat id in the plan's `key_beat_ids` MUST be covered in the prose** \
— not just hinted at. These include TEG records, personal bests, and rare feats \
(holes-in-one, eagles, all-time top-3 rounds, big blow-ups). A deterministic \
"PBs and TEG records" appendix is also auto-appended to the styled output, but \
the prose must still cover them.
- Each beat carries a `course`. The same hole NUMBER on different courses is a \
DIFFERENT hole — never treat them as "the same hole".
- For non-final rounds: describe race STATE at day's end, NOT tournament winners.
- For final rounds: declare race WINNERS and final margins.
- British English. Use proper-cased player names (not all-caps surnames).
- Honour the data precisely: where a rival "drew level" rather than taking the \
lead outright, say "drew level".
- **Stableford and Gross measure DIFFERENT things** — Stableford is \
handicap-adjusted, Gross is raw shots. A higher-handicap player can lead the \
Trophy and trail the Jacket; a lower-handicap player vice versa. This is \
**normal handicapping, not paradox**. NEVER frame a player's split between the \
two competitions as schizophrenic, contradictory, a "unique double", impossibly \
strange, or any kind of head-scratcher. State both facts plainly.
- The Trophy metric is `trophy_metric` in the bundle: Stableford (higher is better) \
for TEG 8+; net-vs-par (lower is better, signed like +47) for TEGs 1–7.
- **TEG has NO countback, NO tiebreakers, NO playoff.** Lead changes are caused \
by accumulated points (Stableford/net-vs-par for the Trophy, Gross for the Jacket). \
Never invent "countback", "countback math", "tiebreaker", "playoff" — those \
mechanisms do not exist in TEG.
- **Arithmetic must be exact.** When asserting an over-par total across a \
stretch of holes, the figure must equal the precise sum of per-hole over-par \
(bogey = +1, double = +2, triple = +3, quad = +4, quint = +5, sext = +6). If \
echoing a total from the dry draft, check it against the per-hole evidence — \
wrong arithmetic is the most obvious fabrication players will catch.
- **Stroke index (SI) for hole colour.** Beat hole evidence may include an `si` \
field. Use sparingly: SI 1 = "the hardest hole on the course"; SI 18 = "the \
easiest"; SI 2–3 = "one of the hardest"; SI 16–17 = "one of the easiest". \
SI 4–15: not noteworthy — ignore. Don't force it on every hole.
- **Prior-round callbacks (R≥2).** The dry draft and `prior_rounds` data allow \
brief colour references to earlier rounds — "recovering from a disastrous R1", \
"extending his overnight lead", "a player transformed since R2's struggles". \
Keep callbacks brief and earned; this is still a round report, not a tournament recap.
- Markdown only; the renderer applies styling."""


# ---------------------------------------------------------------------------
# Pipeline functions
# ---------------------------------------------------------------------------
def _plan_to_text(plan: Union[RoundStoryPlan, dict]) -> str:
    d = plan.model_dump() if isinstance(plan, RoundStoryPlan) else plan
    return json.dumps(d, indent=2, ensure_ascii=False)


def build_round_story_plan(teg_num: int, round_num: int, mode: str = "balanced",
                           tone: str = "house", dry_run: bool = False,
                           model: Optional[str] = None,
                           events_cache: Optional[list] = None,
                           venue_cache: Optional[dict] = None) -> dict:
    """Stage 3 for a round: LLM produces a structured RoundStoryPlan."""
    bundle, _ = assemble_round_bundle(teg_num, round_num, mode=mode, tone=tone,
                                      events_cache=events_cache, venue_cache=venue_cache)
    user = ("Plan the report for the following round. Use ONLY this data.\n\n"
            + json.dumps(bundle, indent=2, ensure_ascii=False))

    if dry_run:
        path = f"{OUTPUT_DIR}/teg_{teg_num}_round_{round_num}_plan_prompt.md"
        with open(path, "w") as f:
            f.write("# SYSTEM PROMPT\n\n" + ROUND_PLAN_SYSTEM
                    + "\n\n---\n\n# USER MESSAGE\n\n" + user + "\n")
        return {"dry_run": True, "prompt_path": path, "n_beats": len(bundle["beats"])}

    plan, usage = llm.generate_structured(ROUND_PLAN_SYSTEM, user, RoundStoryPlan,
                                          model=model or llm.DEFAULT_MODEL)
    out_path = f"{OUTPUT_DIR}/teg_{teg_num}_round_{round_num}_story_plan.json"
    with open(out_path, "w") as f:
        json.dump(plan.model_dump(), f, indent=2, ensure_ascii=False)
    return {"plan": plan, "usage": usage, "output_path": out_path}


def generate_round_dry_draft(teg_num: int, round_num: int,
                              plan: Union[RoundStoryPlan, dict],
                              mode: str = "balanced", tone: str = "house",
                              model: Optional[str] = None,
                              events_cache: Optional[list] = None,
                              venue_cache: Optional[dict] = None) -> dict:
    """Stage 4a for a round — dry storyline draft (chronological, hole-by-hole detail)."""
    bundle, _ = assemble_round_bundle(teg_num, round_num, mode=mode, tone=tone,
                                      events_cache=events_cache, venue_cache=venue_cache)
    user = (
        "ROUND STORY PLAN:\n" + _plan_to_text(plan)
        + "\n\nBEATS (facts + hole evidence; reference by id):\n"
        + json.dumps(bundle["beats"], indent=2, ensure_ascii=False)
        + "\n\nCOMPETITION STATE (end of this round):\n"
        + json.dumps(bundle["competition_state_end_of_round"], indent=2, ensure_ascii=False)
        + "\n\nCOMPETITION STATE (end of prior round):\n"
        + json.dumps(bundle["competition_state_prior"], indent=2, ensure_ascii=False)
        + "\n\nROUND VENUE:\n"
        + json.dumps(bundle["round_venue"] or {}, indent=2, ensure_ascii=False)
    )
    text, usage = llm.generate_text(ROUND_DRY_DRAFT_SYSTEM, user,
                                    model=model or llm.DEFAULT_MODEL, max_tokens=6000)
    out_path = f"{OUTPUT_DIR}/teg_{teg_num}_round_{round_num}_dry_draft.md"
    with open(out_path, "w") as f:
        f.write(text)
    return {"text": text, "usage": usage, "output_path": out_path}


def report_round_around_draft(teg_num: int, round_num: int,
                               plan: Union[RoundStoryPlan, dict], dry_text: str,
                               model: Optional[str] = None) -> dict:
    """Stage 4b for a round — entertaining report built around the dry draft."""
    user = (
        "ROUND STORY PLAN:\n" + _plan_to_text(plan)
        + "\n\nDRY STORYLINE DRAFT (your fact anchor — do not contradict; you may \
add voice, colour, foreshadowing, and reorder for narrative effect):\n"
        + dry_text
    )
    text, usage = llm.generate_text(ROUND_WRITER_SYSTEM, user,
                                    model=model or llm.DEFAULT_MODEL, max_tokens=8000)
    out_path = f"{OUTPUT_DIR}/teg_{teg_num}_round_{round_num}_report_A_around_draft.md"
    with open(out_path, "w") as f:
        f.write(text)
    return {"text": text, "usage": usage, "output_path": out_path}


def generate_round_report(teg_num: int, round_num: int, mode: str = "balanced",
                          tone: str = "house",
                          events_cache: Optional[list] = None,
                          venue_cache: Optional[dict] = None) -> dict:
    """Full round-report pipeline. Writes final + styled markdown, returns paths.

    `events_cache` / `venue_cache` enable per-TEG reuse across tournament + 4
    round reports (used by the backfill orchestrator).
    """
    from teg_analysis.reporting.authoring import repetition_lint
    from teg_analysis.reporting.render import style_round_report
    plan_out = build_round_story_plan(teg_num, round_num, mode=mode, tone=tone,
                                      events_cache=events_cache, venue_cache=venue_cache)
    plan = plan_out["plan"]
    dry = generate_round_dry_draft(teg_num, round_num, plan, mode=mode, tone=tone,
                                   events_cache=events_cache, venue_cache=venue_cache)
    around = report_round_around_draft(teg_num, round_num, plan, dry["text"])
    linted, _ = repetition_lint(around["text"])
    out_path = f"{OUTPUT_DIR}/teg_{teg_num}_round_{round_num}_report_final.md"
    with open(out_path, "w") as f:
        f.write(linted)
    styled_path = style_round_report(teg_num, round_num)
    return {"plan_path": plan_out["output_path"],
            "dry_path": dry["output_path"],
            "around_path": around["output_path"],
            "final_path": out_path,
            "styled_path": styled_path,
            "n_chars": len(linted)}
