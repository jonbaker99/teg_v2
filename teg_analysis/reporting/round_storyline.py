"""Storyline-first ROUND report: the round-level equivalent of
`story_plan.py` + `scripts/storyline_full_report_experiment.py`, scaled down
from a tournament-length newspaper edition to a one-round one.

Mirrors the tournament storyline-first shape exactly:

    assemble_round_storyline_bundle -> build_round_storyline_plan (1 LLM call)
        -> build_round_storyline_draft (per-storyline, fact-isolated, N calls)
        -> authoring.restyle_voice(round_num=...) (1 LLM call, voice pass)
        -> newspaper_edition.build_edition(teg, round_num=...) (free, deterministic)

Two mandatory storylines instead of three: `round_story` (who played the best
round of the day, and how it compares to every round ever played) and
`race_story` (how this round moved the Trophy / Green Jacket / Wooden Spoon —
or, on the final round, who won them). 0-3 discovered storylines fill out the
rest, same quality bar as the tournament pipeline.

WHY A SEPARATE MODULE, not an extension of `round_report.py`. That file's two
prompt constants (`ROUND_PLAN_SYSTEM`, `ROUND_WRITER_SYSTEM`) have their
`DESCRIPTOR_RULE`/`DOUBLE_RULE` exclusions asserted by
`tests/test_reporting_prompts.py`, pinned to the legacy `RoundStoryPlan`
premise ("a round report is a single narrative, not a newspaper of story
cards"). This pipeline makes that premise false — it wires `DESCRIPTOR_RULE`
in, and `DOUBLE_RULE` in on a final round. Sharing a module would put a prompt
that carries a rule next to one that is test-pinned to exclude it, which reads
as an accident. `round_report.py`'s two functions this module DOES reuse —
`_competition_state_at_round` and `_prior_rounds_context`, both correct and
era-aware today — are imported, not reimplemented.

WHY THE CORRECTNESS CONSTRAINT MATTERS. A mid-tournament round report must not
know what happened in later rounds — not for tidiness, but because a live,
clubhouse-generated round report (the future to-do this pipeline is built
towards) is written when later rounds do not exist yet. See
`_assert_no_future_rounds` and the "explicitly excluded" list in
`assemble_round_storyline_bundle`'s docstring.
"""

from __future__ import annotations

import json
from typing import Optional, Tuple, Union

from pydantic import BaseModel, Field

from teg_analysis.reporting.era import trophy_metric
from teg_analysis.reporting.events import build_notable_events
from teg_analysis.reporting.venue import build_venue_context
from teg_analysis.reporting.story_plan import (
    DraftedStoryline, NarrativeVehicle, PaletteVehicle, ProminentVehicle,
    _render_vehicle_menu, _render_palette_menu,
)
from teg_analysis.reporting.round_report import (
    _competition_state_at_round, _prior_rounds_context,
)
from teg_analysis.reporting import llm, prompts

from teg_analysis.reporting.paths import output_dir


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------
class RoundStorylinePlan(BaseModel):
    title: str
    title_candidates: list[str]
    theme: str
    tone: str
    opening_hook: str
    narrative_vehicles: list[NarrativeVehicle] = []
    prominent_vehicle: ProminentVehicle
    prominent_palette: PaletteVehicle
    is_final_round: bool                                   # echoed back from the bundle
    round_story: DraftedStoryline                           # MANDATORY, anchor "round"
    race_story: DraftedStoryline                            # MANDATORY, anchor "race"
    discovered_storylines: list[DraftedStoryline] = Field(default_factory=list, max_length=3)
    race_state_note: str = ""    # one line: what the deterministic standings block cannot say
    storyline_note: str = ""


# ---------------------------------------------------------------------------
# Bundle assembly — leak-safe: nothing here may derive from a round > round_num
# of THIS teg_num. See the module docstring and CLAUDE.md-adjacent reasoning
# in teg_analysis/reporting/STATUS.md under this pipeline's entry.
# ---------------------------------------------------------------------------
def _round_ranks(teg_num: int, round_num: int) -> list[dict]:
    """Per-player as-of-date round comparison: how did THIS round stack up
    against every round this player (and the whole field) has ever played?

    Source is `commentary.create_round_summary()`'s
    `Round_Rank_In_{Player,All}_History_*` columns — computed chronologically
    by date, so "to date" genuinely means up to and including this round, never
    later ones. This is the direct answer to "compared to previous rounds".
    """
    from teg_analysis.analysis.commentary import create_round_summary
    rs = create_round_summary()
    rs = rs[(rs["TEGNum"] == teg_num) & (rs["Round"] == round_num)]
    if rs.empty:
        return []
    metric = trophy_metric(teg_num)
    trophy_rank_col = ("Round_Rank_In_All_History_NetVP" if metric == "net_vs_par"
                       else "Round_Rank_In_All_History_Stableford")
    trophy_player_rank_col = ("Round_Rank_In_Player_History_NetVP" if metric == "net_vs_par"
                              else "Round_Rank_In_Player_History_Stableford")
    out = []
    for _, r in rs.iterrows():
        out.append({
            "player": r["Player"],
            "round_score_trophy": int(r["Round_Score_NetVP" if metric == "net_vs_par"
                                        else "Round_Score_Stableford"]),
            "round_score_gross": int(r["Round_Score_Gross"]),
            "all_time_rank_trophy": r.get(trophy_rank_col),
            "player_history_rank_trophy": r.get(trophy_player_rank_col),
            "all_time_rank_gross": r.get("Round_Rank_In_All_History_Gross"),
            "player_history_rank_gross": r.get("Round_Rank_In_Player_History_Gross"),
            "total_player_rounds_to_date": r.get("Total_Player_Rounds_To_Date"),
            "total_rounds_to_date": r.get("Total_Rounds_To_Date"),
        })
    return out


def _round_of_the_day(round_ranks: list[dict]) -> dict:
    """Deterministic summary of `round_ranks` — guarantees `round_story` has a
    subject even in a dead round, without an LLM call."""
    if not round_ranks:
        return {}
    # Trophy direction varies by era (Stableford: higher is better; net-vs-par:
    # lower is better, signed). Report both extremes and let the prompt/writer
    # pick the right one via `trophy_metric` rather than guessing here.
    return {
        "best_trophy_score": max(r["round_score_trophy"] for r in round_ranks),
        "worst_trophy_score": min(r["round_score_trophy"] for r in round_ranks),
        "best_gross_score": min(r["round_score_gross"] for r in round_ranks),
        "worst_gross_score": max(r["round_score_gross"] for r in round_ranks),
        "field_size": len(round_ranks),
    }


def _race_movement(prior: list[dict], end: list[dict]) -> dict:
    """Deterministic diff of two `_competition_state_at_round` snapshots.

    Per competition: leader before/after, whether the lead changed, gap
    before/after/delta. This is the answer to "how did the round move people
    within the tournament" — computed directly from the two snapshots rather
    than a TEG-wide trajectory helper, so it stays correctly scoped to exactly
    this round's movement.
    """
    if not prior or not end:
        return {"is_round_1": not prior}
    by_name = {c["name"]: c for c in prior}
    out = {}
    for c in end:
        p = by_name.get(c["name"])
        if c["name"] == "Wooden Spoon":
            out[c["name"]] = {
                "laggard_after": c.get("laggard"),
                "laggard_before": p.get("laggard") if p else None,
                "flipped": bool(p) and p.get("laggard") != c.get("laggard"),
                "gap_to_next_after": c.get("gap_to_next"),
                "gap_to_next_before": p.get("gap_to_next") if p else None,
            }
        else:
            out[c["name"]] = {
                "leader_after": c.get("leader"),
                "leader_before": p.get("leader") if p else None,
                "lead_changed": bool(p) and p.get("leader") != c.get("leader"),
                "gap_after": c.get("gap"),
                "gap_before": p.get("gap") if p else None,
            }
    return out


def _assert_no_future_rounds(bundle: dict, teg_num: int, round_num: int) -> None:
    """Leak guard: raise if anything in the bundle derives from a later round
    of this TEG, or from a later TEG. Walks the bundle recursively looking for
    dicts carrying a `"round"` or `"Round"` key."""
    def _walk(obj):
        if isinstance(obj, dict):
            for key in ("round", "Round", "this_teg_best_round"):
                v = obj.get(key)
                if isinstance(v, int) and v > round_num:
                    raise AssertionError(
                        f"round-storyline bundle leak: found round {v} in a bundle "
                        f"scoped to TEG {teg_num} round {round_num} (key={key!r})")
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)
    _walk(bundle.get("course_context") or {})
    _walk(bundle.get("beats") or [])


def assemble_round_storyline_bundle(teg_num: int, round_num: int, *,
                                    mode: str = "balanced", tone: str = "house",
                                    events_cache: Optional[list] = None,
                                    venue_cache: Optional[dict] = None) -> Tuple[dict, list]:
    """Build the LLM input bundle for the round storyline pipeline.

    Superset of `round_report.assemble_round_bundle` — the legacy round
    pipeline keeps using that function unchanged; this is a sibling, not a
    replacement, so the extra tokens here are never paid by the legacy path.

    New keys, grouped by what they answer:
      - `round_ranks` / `round_of_the_day` — comparison to previous rounds
        (§ course context in the tournament sense: as-of-date, leak-safe).
      - `course_context` — round-scoped course history, bounded via
        `through_round=` so a course best set later in THIS TEG cannot surface.
      - `race_movement` — how the round moved the three competitions, a
        deterministic diff of `competition_state_prior` vs `_end_of_round`.
      - `player_history` — prior-TEG-only, therefore round-safe verbatim.
      - `win_anatomy` / `win_counts` / `double` — present ONLY when
        `is_final_round`, because each is a whole-TEG-outcome fact.

    Deliberately NOT included, always: `tournament_shape` (whole-TEG,
    hardcoded to the last round), `vehicle_fit_hints`/`candidate_threads`
    (TEG-scoped detectors with no round-level meaning), `competition_arcs`.

    Raises `AssertionError` (via `_assert_no_future_rounds`) if any enrichment
    leaked a later round's data — this is deliberately loud, not a warning.
    """
    from teg_analysis.reporting.course_history import (
        build_player_course_history, detect_course_records,
    )
    from teg_analysis.reporting.history_context import build_player_cross_teg_history

    all_events = events_cache if events_cache is not None else build_notable_events(teg_num, mode=mode)
    round_events = [e for e in all_events if e.round == round_num]

    venue_full = venue_cache if venue_cache is not None else build_venue_context(teg_num)
    round_venue = next(
        (r for r in venue_full.get("rounds", []) if r.get("round") == round_num), None,
    )
    total_rounds = len(venue_full.get("rounds", []))
    is_final_round = (round_num == total_rounds) and total_rounds > 0

    beats = []
    MANDATORY_TYPES = {"hole_in_one", "eagle"}
    for i, e in enumerate(round_events, 1):
        ctx = dict(e.context)
        ctx.pop("arc", None)
        is_double_figure = bool(e.holes) and (e.holes[0].get("sc", 0) >= 10)
        mandatory = (e.type in MANDATORY_TYPES or e.rarity >= 7 or is_double_figure)
        beats.append({
            "id": f"r{round_num}_b{i:02d}", "total": e.total, "scope": e.scope,
            "type": e.type, "course": e.course, "headline": e.headline,
            "players": e.players,
            "scores": {"importance": e.importance, "rarity": e.rarity, "entertainment": e.entertainment},
            "mandatory": mandatory, "holes": e.holes,
            "context": {k: v for k, v in ctx.items() if v is not None},
        })

    # Round-scoped, leak-safe course records: through_round bounds "prior" to
    # earlier TEGs OR earlier rounds of THIS TEG.
    course_records = detect_course_records(teg_num, through_round=round_num)
    for i, cr in enumerate(course_records, 1):
        beats.append({
            "id": f"cr{i:02d}", "total": 10.0, "scope": "round", "type": cr["type"],
            "course": cr["course"], "headline": cr["summary_fact"], "players": [cr["player"]],
            "scores": {"importance": 10.0, "rarity": 10.0, "entertainment": 8.0},
            "mandatory": True, "holes": [], "context": {"round": cr["round"]},
        })

    prior_state = _competition_state_at_round(teg_num, round_num - 1)
    end_state = _competition_state_at_round(teg_num, round_num)
    round_ranks = _round_ranks(teg_num, round_num)

    bundle = {
        "teg": teg_num, "round": round_num, "is_final_round": is_final_round,
        "total_rounds": total_rounds, "tone": tone, "trophy_metric": trophy_metric(teg_num),
        "round_venue": round_venue,
        "area_context": {
            "area": venue_full.get("area"), "year": venue_full.get("year"),
            "area_visit": venue_full.get("area_visit"),
        },
        "competition_state_end_of_round": end_state,
        "competition_state_prior": prior_state,
        "race_movement": _race_movement(prior_state, end_state),
        "prior_rounds": _prior_rounds_context(teg_num, round_num, all_events),
        "round_ranks": round_ranks,
        "round_of_the_day": _round_of_the_day(round_ranks),
        "course_context": build_player_course_history(teg_num, through_round=round_num),
        "player_history": {
            p: h for p, h in build_player_cross_teg_history(teg_num).items()
            if p in {pl for e in round_events for pl in e.players}
        },
        "beats": beats,
    }

    if is_final_round:
        from teg_analysis.reporting.win_anatomy import build_win_anatomy
        from teg_analysis.reporting.history_context import build_win_counts, build_double_context
        bundle["win_anatomy"] = build_win_anatomy(teg_num)
        bundle["win_counts"] = build_win_counts(teg_num)
        bundle["double"] = build_double_context(teg_num)

    _assert_no_future_rounds(bundle, teg_num, round_num)
    return bundle, round_events


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
def round_storyline_system(is_final_round: bool) -> str:
    """The round editor prompt. `DESCRIPTOR_RULE` always wired in — the output
    IS a newspaper of story cards, unlike the legacy `RoundStoryPlan`.
    `DOUBLE_RULE` only on a final round, when the bundle carries `double`."""
    double_block = ("\n" + prompts.DOUBLE_RULE + "\n") if is_final_round else ""
    return _ROUND_STORYLINE_SYSTEM_BASE.replace("{DOUBLE_RULE}", double_block)


_ROUND_STORYLINE_SYSTEM_BASE = """You are the editor planning a newspaper-style report on ONE \
ROUND of a TEG (an amateur golf tournament of several rounds). You do NOT write prose here — \
you produce a STRUCTURED PLAN that a writer will follow, one section per storyline, the same \
way a newspaper page carries several articles.

AUDIENCE: the players themselves — insiders who know each other, the courses, and the history. \
They will spot any factual error instantly.

""" + prompts.HOUSE_VOICE_SUMMARY + """
WHAT IS WORTH PUTTING IN THE PLAN:
""" + prompts.RANKING_RULE + """
""" + prompts.NAMING_RULE + """
""" + prompts.DESCRIPTOR_RULE + """
{DOUBLE_RULE}
THIS IS A ROUND REPORT, NOT A TOURNAMENT REPORT.
- The round is ONE day of the tournament: 18 holes, all players.
- If `is_final_round` is FALSE: describe race STATE and MOVEMENT, not winners. Do not declare \
anyone the tournament champion.
- If `is_final_round` is TRUE: this round IS the tournament's resolution. `race_story` becomes \
the coronation — declare Trophy / Green Jacket / Wooden Spoon WINNERS and final margins.

TWO MANDATORY STORYLINES — populate both, regardless of how good you judge them to be:
- `round_story`: the best round of the day. Use `round_of_the_day` and `round_ranks` to ground \
it — `round_ranks` gives every player's round measured against their own history AND the whole \
field's history, TO DATE (never later rounds; the figures are computed chronologically). If the \
round of the day is genuinely dull, say so plainly rather than inflating it.
- `race_story`: what this round did to the Trophy / Green Jacket / Wooden Spoon races. Use \
`race_movement` (a direct before/after diff — leader changes, gap deltas) and \
`competition_state_end_of_round` / `_prior`. On a final round this is the winners-declared story.

**Overlap check.** If the player behind `round_story` is the SAME player who moved the race in \
`race_story` (they are often the same person), write `race_story` from the vantage of whoever \
LOST ground instead — the two sections must not tell the same story twice.

DISCOVERED STORYLINES (0-3): only where the beats genuinely support one distinct from the two \
mandatory stories. A round has far fewer beats than a tournament — do not manufacture a third \
sidebar to fill space. Each discovered storyline needs `compelling_score >= 6` and at least 2 \
`beat_ids`; below that, leave it out. A 2-article round report is a correct outcome.

**Course context.** `course_context` gives each player's history on this round's specific \
course, bounded to visits strictly before this round (earlier TEGs, or earlier rounds of THIS \
TEG on the same course) — never a course best set LATER in this TEG. Use it for `round_story` \
or a discovered storyline when a player's course history is genuinely part of the story.

YOUR JOB:
- `title` + `title_candidates`, `theme` (one line), `opening_hook`.
- 1-3 `narrative_vehicles`, naming the one you foreground as `prominent_vehicle`. Pick ONLY \
from this menu:

{VEHICLE_MENU}

- `prominent_palette` — the context material to foreground, one of: {PALETTE_MENU}.
- For each mandatory storyline and each discovered one: `subject`, `why_it_matters`, `shape` \
(setup -> turn -> resolution, 2-3 sentences), `beat_ids` (must exist in the bundle), \
`headline_candidates` (~3 options, 3-8 words each — no two-clause "X — Y" or "X: Y" \
constructions), `chosen_headline` (3-8 words), `standfirst` (one sentence, adds context, never \
restates the headline), `compelling_score` (1-10), `humour_score` (1-10), and `descriptor` per \
DESCRIPTOR_RULE above.
- `race_state_note`: one line covering anything about the race state the deterministic \
standings block (auto-appended by the renderer) cannot say — leave it empty if nothing needs \
saying beyond the numbers.
- `is_final_round`: echo the bundle's value back exactly.
- `storyline_note`: only if departing from round_story-leads-unless-final-round-then-race_story.

MANDATORY BEAT COVERAGE: every beat marked `"mandatory": true` (course records, holes-in-one, \
eagles, double-figure gross scores) MUST appear in some storyline's `beat_ids`.

RULES:
- Use ONLY the supplied data. Never invent.
- **Stableford and Gross measure DIFFERENT things.** A player leading one and trailing the \
other is normal handicapping, not paradox — never frame the split as a head-scratcher.
- The Trophy metric is `trophy_metric` in the bundle: Stableford (higher is better) for TEG 8+; \
net-vs-par (lower is better, signed like +47) for TEGs 1-7.
- **TEG has NO countback, NO tiebreakers, NO playoff.** Never invoke any of those mechanisms.
- Output only the structured plan."""

_ROUND_STORYLINE_SYSTEM_BASE = (_ROUND_STORYLINE_SYSTEM_BASE
                               .replace("{VEHICLE_MENU}", _render_vehicle_menu())
                               .replace("{PALETTE_MENU}", _render_palette_menu()))
assert "{VEHICLE_MENU}" not in _ROUND_STORYLINE_SYSTEM_BASE
assert "{PALETTE_MENU}" not in _ROUND_STORYLINE_SYSTEM_BASE

#: Kept as a module attribute purely so `tests/test_reporting_prompts.py`'s
#: constant sweep (`_named_prompt_constants`, which looks for module-level
#: UPPERCASE strings) can find and check the base editor prompt without a
#: model argument. `round_storyline_system(False)` is what production calls.
ROUND_STORYLINE_SYSTEM_PROMPT = round_storyline_system(False)


def round_draft_writer_system(is_final_round: bool) -> str:
    """Per-storyline fact-isolated draft writer. Deliberately voiceless — the
    voice pass (`authoring.restyle_voice`) owns register, exactly like the
    tournament pipeline's `DRAFT_WRITER_SYSTEM`. Never carries `DESCRIPTOR_RULE`
    (editor-only, print-only field). `DOUBLE_RULE` only on a final round."""
    double_block = ("\n" + prompts.DOUBLE_RULE + "\n") if is_final_round else ""
    return _ROUND_DRAFT_WRITER_SYSTEM_BASE.replace("{DOUBLE_RULE}", double_block)


_ROUND_DRAFT_WRITER_SYSTEM_BASE = """You are writing ONE SECTION of a round-of-golf report — a \
single storyline, not the whole report. Plain, clear, factual prose. NOT the final voice: do \
not try to be funny, do not reach for a compelling turn of phrase. 150-250 words.

You are given `subject` (a label — a starting point, not a fact source), `evidence` (the \
specific beats this storyline is built from — the ONLY source of facts), and `context` (venue, \
course history, race movement, round-rank data — background material; any comparison you make \
from it must follow exactly from its own figures, never estimated). Do not let `context` crowd \
out `evidence` — the beats are still the spine.

Every fact you state must trace to `evidence` or `context`. If it is in neither, it does not \
exist.

WHAT IS WORTH SAYING, and how to name it:
""" + prompts.RANKING_RULE + """
""" + prompts.NAMING_RULE + """
""" + prompts.STROKE_INDEX_RULE + """
""" + prompts.SCORING_REDUNDANCY_RULE + """
{DOUBLE_RULE}"""

ROUND_DRAFT_WRITER_SYSTEM_PROMPT = round_draft_writer_system(False)


# ---------------------------------------------------------------------------
# Consistency checks — no LLM, warnings only
# ---------------------------------------------------------------------------
def check_round_storyline_plan_consistency(plan: RoundStorylinePlan, bundle: dict) -> list[str]:
    warnings: list[str] = []
    beat_ids = {b["id"] for b in bundle["beats"]}
    storylines = [("round_story", plan.round_story), ("race_story", plan.race_story)]
    storylines += [(f"discovered[{i}]", s) for i, s in enumerate(plan.discovered_storylines)]

    for name, s in storylines:
        bad = set(s.beat_ids) - beat_ids
        if bad:
            warnings.append(f"{name} cites unknown beat_ids: {sorted(bad)}")
        if not s.chosen_headline:
            warnings.append(f"{name} has no chosen_headline")
        elif not (3 <= len(s.chosen_headline.split()) <= 8):
            warnings.append(f"{name} chosen_headline is not 3-8 words: {s.chosen_headline!r}")
        if not s.standfirst:
            warnings.append(f"{name} has no standfirst")
        if not s.descriptor:
            warnings.append(f"{name} has no descriptor")

    mandatory_ids = {b["id"] for b in bundle["beats"] if b.get("mandatory")}
    cited_ids = {bid for _, s in storylines for bid in s.beat_ids}
    missing = mandatory_ids - cited_ids
    if missing:
        warnings.append(f"mandatory beats not cited by any storyline: {sorted(missing)}")

    overlap = set(plan.round_story.beat_ids) & set(plan.race_story.beat_ids)
    if len(overlap) > max(len(plan.round_story.beat_ids), len(plan.race_story.beat_ids)) * 0.5:
        warnings.append(
            f"round_story and race_story share {len(overlap)} beat_ids — likely the same "
            f"story told twice; race_story should pivot to whoever lost ground")

    for name, s in storylines[2:]:
        if len(s.beat_ids) < 2 or s.compelling_score < 6:
            warnings.append(f"{name} is thin (beat_ids={len(s.beat_ids)}, "
                             f"compelling={s.compelling_score}) — should have been left out")

    if plan.is_final_round != bundle["is_final_round"]:
        warnings.append("plan.is_final_round does not match the bundle")

    return warnings


# ---------------------------------------------------------------------------
# Pipeline functions
# ---------------------------------------------------------------------------
def _json_default(o):
    import numpy as np
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not JSON serialisable: {type(o)}")


def build_round_storyline_plan(teg_num: int, round_num: int, mode: str = "balanced",
                               tone: str = "house", dry_run: bool = False,
                               model: Optional[str] = None,
                               events_cache: Optional[list] = None,
                               venue_cache: Optional[dict] = None) -> dict:
    """Stage 1: LLM produces a structured `RoundStorylinePlan`."""
    bundle, _ = assemble_round_storyline_bundle(
        teg_num, round_num, mode=mode, tone=tone,
        events_cache=events_cache, venue_cache=venue_cache)
    user = ("Plan the report for the following round. Use ONLY this data.\n\n"
            + json.dumps(bundle, indent=2, ensure_ascii=False, default=_json_default))
    system = round_storyline_system(bundle["is_final_round"])

    if dry_run:
        path = f"{output_dir()}/teg_{teg_num}_round_{round_num}_storyline_plan_prompt.md"
        with open(path, "w") as f:
            f.write("# SYSTEM PROMPT\n\n" + system + "\n\n---\n\n# USER MESSAGE\n\n" + user + "\n")
        return {"dry_run": True, "prompt_path": path, "n_beats": len(bundle["beats"]),
                "is_final_round": bundle["is_final_round"]}

    plan, usage = llm.generate_structured(system, user, RoundStorylinePlan, max_tokens=20000,
                                          model=model or llm.DEFAULT_MODEL,
                                          stage="round_storyline_plan",
                                          label=f"teg{teg_num}r{round_num}")
    out_path = f"{output_dir()}/teg_{teg_num}_round_{round_num}_storyline_plan.json"
    with open(out_path, "w") as f:
        json.dump(plan.model_dump(), f, indent=2, ensure_ascii=False)

    warnings = check_round_storyline_plan_consistency(plan, bundle)
    for w in warnings:
        print(f"[round_storyline_plan] WARNING TEG {teg_num} R{round_num}: {w}")

    return {"plan": plan, "usage": usage, "output_path": out_path, "warnings": warnings}


def load_round_storyline_plan(teg_num: int, round_num: int) -> dict:
    """Load `teg_N_round_R_storyline_plan.json`, validated. Mirrors
    `authoring.load_storyline_plan`."""
    path = f"{output_dir()}/teg_{teg_num}_round_{round_num}_storyline_plan.json"
    try:
        with open(path) as f:
            raw = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"{path} not found — TEG {teg_num} round {round_num} has no storyline "
            f"plan to reuse. Run `build_round_storyline_plan` for it first.") from None
    try:
        return RoundStorylinePlan(**raw).model_dump()
    except Exception as e:
        raise ValueError(f"{path} is not a valid RoundStorylinePlan: {e}") from None


def build_round_results_for_glance(teg_num: int, round_num: int) -> Tuple[list, bool]:
    """The round edition's at-a-glance box content, computed DETERMINISTICALLY
    from `_competition_state_at_round` / `_round_of_the_day` — never from the
    LLM plan's prose — the same "deterministic blocks are the safety net"
    principle as `render._build_at_a_glance` (which reads `plan["competitions"]`,
    itself deterministic data, not free text).

    Returns `(round_results, is_final_round)` where `round_results` is exactly
    3 `{"label", "value"}` dicts — `render.build_round_at_a_glance` and
    `newspaper_edition._parse_results` both require exactly 3.

    Mid-tournament: round of the day, Trophy lead, Green Jacket lead. Final
    round: the real Trophy / Green Jacket / Wooden Spoon winners, in that
    order (matching the tournament at-a-glance box's order).
    """
    end_state = _competition_state_at_round(teg_num, round_num)
    from teg_analysis.reporting.venue import build_venue_context
    total_rounds = len(build_venue_context(teg_num).get("rounds", []))
    is_final_round = (round_num == total_rounds) and total_rounds > 0
    by_name = {c["name"]: c for c in end_state}

    if is_final_round:
        return [
            {"label": "Trophy Winner", "value": by_name["Trophy"]["leader"]},
            {"label": "Green Jacket", "value": by_name["Green Jacket"]["leader"]},
            {"label": "Wooden Spoon", "value": by_name["Wooden Spoon"]["laggard"]},
        ], True

    round_ranks = _round_ranks(teg_num, round_num)
    metric = trophy_metric(teg_num)
    score_key = "round_score_trophy"
    best = max(round_ranks, key=lambda r: r[score_key]) if metric != "net_vs_par" else \
        min(round_ranks, key=lambda r: r[score_key])
    unit = "" if metric == "net_vs_par" else " pts"
    sign = "+" if metric == "net_vs_par" and best[score_key] >= 0 else ""
    round_of_day_value = f'{best["player"]} ({sign}{best[score_key]}{unit})'

    return [
        {"label": "Round of the day", "value": round_of_day_value},
        {"label": "Trophy lead", "value": f'{by_name["Trophy"]["leader"]}, '
                                          f'{by_name["Trophy"]["gap"]} ahead'},
        {"label": "Green Jacket lead", "value": f'{by_name["Green Jacket"]["leader"]}, '
                                                f'{by_name["Green Jacket"]["gap"]} ahead'},
    ], False


def _evidence_for(storyline: dict, all_beats: list) -> list:
    by_id = {b["id"]: b for b in all_beats}
    return [by_id[bid] for bid in storyline["beat_ids"] if bid in by_id]


def _context_for(storyline_players: set, bundle: dict) -> dict:
    """Scoped, numbers-only context for one storyline's draft call — mirrors
    `scripts/storyline_full_report_experiment.py`'s `_context_for`, extended
    with the round-specific keys. `race_movement` and `round_of_the_day` are
    whole-round summaries (not per-player), so they are always included
    un-scoped; everything else is filtered to this storyline's players."""
    from teg_analysis.reporting.authoring import _strip_derived_prose

    ctx = {
        "venue": bundle.get("round_venue"),
        "area_context": bundle.get("area_context"),
        "race_movement": bundle.get("race_movement"),
        "round_of_the_day": bundle.get("round_of_the_day"),
        "round_ranks": [r for r in (bundle.get("round_ranks") or [])
                        if r["player"] in storyline_players],
        "course_context": {p: h for p, h in (bundle.get("course_context") or {}).items()
                           if p in storyline_players},
        "player_history": {p: h for p, h in (bundle.get("player_history") or {}).items()
                           if p in storyline_players},
    }
    if bundle.get("is_final_round"):
        ctx["double"] = bundle.get("double")
    return _strip_derived_prose(ctx)


def draft_section(storyline: dict, evidence: list, context: dict,
                  is_final_round: bool, model: Optional[str] = None) -> str:
    payload = {"subject": storyline["subject"], "evidence": evidence, "context": context}
    user = "Write this storyline as a prose section:\n\n" + json.dumps(payload, indent=2,
                                                                        ensure_ascii=False,
                                                                        default=_json_default)
    system = round_draft_writer_system(is_final_round)
    text, _usage = llm.generate_text(user=user, system=system,
                                     model=model or llm.DEFAULT_MODEL,
                                     stage="round_storyline_draft",
                                     label=storyline["subject"][:30])
    return text


def build_round_storyline_draft(teg_num: int, round_num: int, model: Optional[str] = None,
                                plan: Optional[dict] = None) -> Tuple[str, dict]:
    """Stage 2: fact-isolated per-storyline draft. Returns (markdown, plan dict).

    Order: `round_story`, then discovered, then `race_story` — mirrors the
    tournament draft's trophy-first-then-discovered-then-jacket/spoon order,
    except on a final round, where `race_story` (the coronation) leads.
    """
    if plan is None:
        result = build_round_storyline_plan(teg_num, round_num, model=model)
        for w in result["warnings"]:
            print(f"  {w}")
        plan = result["plan"].model_dump()

    bundle, _ = assemble_round_storyline_bundle(teg_num, round_num)
    all_beats = bundle["beats"]
    is_final_round = bundle["is_final_round"]

    if is_final_round:
        order = [("race", plan["race_story"])] + [
            (f"d{i}", s) for i, s in enumerate(plan["discovered_storylines"])
        ] + [("round", plan["round_story"])]
    else:
        order = [("round", plan["round_story"])] + [
            (f"d{i}", s) for i, s in enumerate(plan["discovered_storylines"])
        ] + [("race", plan["race_story"])]

    sections = []
    for key, storyline in order:
        evidence = _evidence_for(storyline, all_beats)
        storyline_players = {p for b in evidence for p in b["players"]}
        context = _context_for(storyline_players, bundle)
        text = draft_section(storyline, evidence, context, is_final_round, model=model)
        anchor = f"<!-- storyline: {key} -->"
        sections.append(f"## {storyline['subject']}\n{anchor}\n\n{text}")

    body = f"# {plan['title']}\n\n" + "\n\n".join(sections) + "\n"
    out_path = f"{output_dir()}/teg_{teg_num}_round_{round_num}_report_storylinedraft.md"
    with open(out_path, "w") as f:
        f.write(body)
    return body, plan
