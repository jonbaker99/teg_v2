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

    trophy = rs.sort_values("Cumulative_Tournament_Score_Stableford", ascending=False)
    jacket = rs.sort_values("Cumulative_Tournament_Score_Gross", ascending=True)
    t_rows = trophy.to_dict("records")
    j_rows = jacket.to_dict("records")

    def _standings(rows, col):
        return [{"pl": r["Pl"], "player": r["Player"], "score": int(r[col])} for r in rows]

    return [
        {
            "name": "Trophy",
            "leader": t_rows[0]["Player"],
            "leader_pl": t_rows[0]["Pl"],
            "leader_score": int(t_rows[0]["Cumulative_Tournament_Score_Stableford"]),
            "runner_up": t_rows[1]["Player"],
            "gap": int(t_rows[0]["Cumulative_Tournament_Score_Stableford"]
                       - t_rows[1]["Cumulative_Tournament_Score_Stableford"]),
            "standings": _standings(t_rows, "Cumulative_Tournament_Score_Stableford"),
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
            "laggard_score": int(t_rows[-1]["Cumulative_Tournament_Score_Stableford"]),
            "gap_to_next": int(t_rows[-2]["Cumulative_Tournament_Score_Stableford"]
                               - t_rows[-1]["Cumulative_Tournament_Score_Stableford"]),
        },
    ]


# ---------------------------------------------------------------------------
# Bundle assembly
# ---------------------------------------------------------------------------
def assemble_round_bundle(teg_num: int, round_num: int, mode: str = "balanced",
                          tone: str = "house") -> Tuple[dict, list]:
    """Build the LLM input bundle for round-report stages."""
    all_events = build_notable_events(teg_num, mode=mode)
    round_events = [e for e in all_events if e.round == round_num]

    venue_full = build_venue_context(teg_num)
    round_venue = next(
        (r for r in venue_full.get("rounds", []) if r.get("round") == round_num),
        None,
    )

    beats = []
    for i, e in enumerate(round_events, 1):
        ctx = dict(e.context)
        ctx.pop("arc", None)
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
            "holes": e.holes,
            "context": {k: v for k, v in ctx.items() if v is not None},
        })

    bundle = {
        "teg": teg_num,
        "round": round_num,
        "tone": tone,
        "round_venue": round_venue,
        "area_context": {
            "area": venue_full.get("area"),
            "year": venue_full.get("year"),
            "area_visit": venue_full.get("area_visit"),
        },
        "competition_state_end_of_round": _competition_state_at_round(teg_num, round_num),
        "competition_state_prior": _competition_state_at_round(teg_num, round_num - 1),
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
- The three competitions (Trophy / Green Jacket / Wooden Spoon) have STATE here, \
not winners. Use `competition_state_end_of_round` for where each race stands at \
day's end, and `competition_state_prior` for where it stood going in. Describe \
what changed in the round.
- The round IS the unit. There is no per-round breakdown — the report covers one \
round.

INPUT (JSON in the user turn):
- competition_state_end_of_round: per-competition leader/laggard, score, gap, \
plus full standings list
- competition_state_prior: same shape, for end of previous round (empty if R1)
- beats: ranked notable events FROM THIS ROUND ONLY. ALWAYS refer by `id`.
- round_venue: course, date, visit count
- area_context: location and area visit count
- tone: requested register

YOUR JOB:
- Choose the round's STORY: a clear one-line `theme`, and 2-3 `foreshadow` hooks \
(events earlier in the round that pay off later — e.g. "early blow-up at the 4th \
that came back to haunt him at the 18th").
- Choose a `narrative_structure` (`chronological` | `in_medias_res` | `theme_led` \
| free-form one-liner) and an `opening_hook` (one-line description of what to \
open with and why). Don't default to "front nine then back nine" if the story has \
a different shape.
- Select 5-8 `key_beat_ids` the report MUST cover.
- For each principal player, a one-sentence `arc` FOR THIS ROUND (what they did, \
what it meant).
- Build a `competition_state` array — for Trophy / Green Jacket / Wooden Spoon: \
the leader_or_laggard, their cumulative score, the gap to the next position, AND \
a `note` describing what happened to that race in the round (lead taken, lead \
held, gap widened, lead changes mid-round, etc.). Draw on prior state to describe \
what changed.
- `venue_notes`: any course/area context to weave in.
- `title` + a few `title_candidates`; record the resolved `tone`.

SELECTION PRINCIPLES:
- Favour high-importance beats for the spine; high-rarity for one-line callouts; \
high-entertainment for colour.
- Early-round lead changes within a single round, when the field is bunched, are \
routine; late-round shifts matter more.

RULES:
- Use ONLY the supplied data. Never invent.
- Round reports describe race STATE, not WINNERS. Do not declare anyone the \
tournament champion.
- Output only the structured plan."""


ROUND_DRY_DRAFT_SYSTEM = """You are producing a DRY STORYLINE DRAFT for a \
single-round TEG report. This is a faithful, plainly-written account with NO \
colour, NO jokes, NO stylistic flourish. It is a scaffold and a fact-check, not \
the finished article.

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
specificity is the whole point of the draft.
3. WHERE THE RACES STAND — for the Trophy, then the Green Jacket, then the Wooden \
Spoon: leader-or-laggard, cumulative score, gap to next position, what changed \
this round (drawing on the competition_state data).
4. PLAYERS — one factual line per player, from the player arcs.

RULES:
- Use ONLY the supplied facts. Never invent holes, scores, players, or events.
- Render real hole detail wherever the evidence supports it.
- Honour the data precisely: where a rival "drew level" rather than taking the \
lead outright, say "drew level", not "took the lead".
- Round reports describe race STATE, not WINNERS — do not declare anyone the \
tournament champion.
- Plain, clear, British English. Short declarative sentences. No similes, no \
jokes, no purple language — that comes in the next pass.
- Markdown headings. Keep it tight."""


ROUND_WRITER_SYSTEM = """You are a golf writer producing the finished, \
entertaining report on ONE ROUND of a TEG (an amateur golf tournament of several \
rounds), for an audience of THE PLAYERS THEMSELVES — insiders who know each \
other, the courses and the history, who want to relive the round and be gently \
ribbed, and who will instantly spot any factual error.

VOICE: faithful, entertaining, tongue-in-cheek — in the spirit of Barney Ronay \
(Guardian) and Tom Peck (Times political sketches). Witty, characterful, a clear \
point of view; but anchored in the facts and never zany or over the top. \
British English.

STRUCTURE — follow the ROUND STORY PLAN you are given:
- Open with the title and a paragraph that lands the theme — drawing on the \
plan's `opening_hook`. The plan's `narrative_structure` sets the shape; you may \
(and should) open *in medias res*, flash back, or lead with the biggest moment \
when the story calls for it.
- The round IS the unit. Don't break into sub-sections by nines or phases unless \
the story genuinely calls for it. Carry the theme; pay off the foreshadow hooks.
- Render specific holes drawn from the dry draft's hole evidence — concrete hole \
detail (par, score, hole number) is the point.
- Close with the state of the three races (Trophy / Green Jacket / Wooden Spoon \
at end of round) — leader/laggard, cumulative score, gap, what changed today. \
**State, not winners**.
- **The report MUST END with a player-by-player section** — 3-5 short bullets, \
one or two sentences per principal player, anchored in this round's moments and \
the plan's `players[]` arcs. Use a heading like `## The men, in brief` (or \
similar). Non-negotiable.

RULES:
- Use ONLY the supplied facts. Never invent holes, scores, players, or events.
- Each beat carries a `course`. The same hole NUMBER on different courses is a \
DIFFERENT hole — never treat them as "the same hole".
- This is a round report. Describe race STATE at day's end, NOT tournament \
winners.
- British English. Use proper-cased player names (not all-caps surnames).
- Honour the data precisely: where a rival "drew level" rather than taking the \
lead outright, say "drew level".
- **Stableford and Gross measure DIFFERENT things** — Stableford is \
handicap-adjusted, Gross is raw shots. A higher-handicap player can lead the \
Trophy and trail the Jacket; a lower-handicap player vice versa. This is \
**normal handicapping, not paradox**. NEVER frame a player's split between the \
two competitions as schizophrenic, contradictory, a "unique double", impossibly \
strange, or any kind of head-scratcher. State both facts plainly.
- Markdown only; the renderer applies styling."""


# ---------------------------------------------------------------------------
# Pipeline functions
# ---------------------------------------------------------------------------
def _plan_to_text(plan: Union[RoundStoryPlan, dict]) -> str:
    d = plan.model_dump() if isinstance(plan, RoundStoryPlan) else plan
    return json.dumps(d, indent=2, ensure_ascii=False)


def build_round_story_plan(teg_num: int, round_num: int, mode: str = "balanced",
                           tone: str = "house", dry_run: bool = False,
                           model: Optional[str] = None) -> dict:
    """Stage 3 for a round: LLM produces a structured RoundStoryPlan."""
    bundle, _ = assemble_round_bundle(teg_num, round_num, mode=mode, tone=tone)
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
                              model: Optional[str] = None) -> dict:
    """Stage 4a for a round — dry storyline draft (chronological, hole-by-hole detail)."""
    bundle, _ = assemble_round_bundle(teg_num, round_num, mode=mode, tone=tone)
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
                          tone: str = "house") -> dict:
    """Full round-report pipeline. Writes the final markdown and returns its path."""
    from teg_analysis.reporting.authoring import repetition_lint
    plan_out = build_round_story_plan(teg_num, round_num, mode=mode, tone=tone)
    plan = plan_out["plan"]
    dry = generate_round_dry_draft(teg_num, round_num, plan, mode=mode, tone=tone)
    around = report_round_around_draft(teg_num, round_num, plan, dry["text"])
    linted, _ = repetition_lint(around["text"])
    out_path = f"{OUTPUT_DIR}/teg_{teg_num}_round_{round_num}_report_final.md"
    with open(out_path, "w") as f:
        f.write(linted)
    return {"plan_path": plan_out["output_path"],
            "dry_path": dry["output_path"],
            "around_path": around["output_path"],
            "final_path": out_path,
            "n_chars": len(linted)}
