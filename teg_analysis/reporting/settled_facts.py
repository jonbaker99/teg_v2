"""Settled facts for the report writer — derived, not new data.

Both draft writers previously saw only per-storyline evidence plus venue and
career/course history — no standings, no lead timeline, no final totals, and
only the current round's weekday. That gap is what let a "comfortably the
better player" claim stand on the Trophy alone while trailing on the Jacket
(no final totals to check against), and a Sunday score get quoted inside an
R1 paragraph (no round→day map beyond the single round in view).

Nothing here is new data: a hole-by-hole leaderboard is effectively already
materialised in `all-data.parquet` via `Rank_Stableford_TEG` /
`Rank_GrossVP_TEG` / `Rank_NetVP_TEG` (per-hole, tie-aware ranks), and
`venue.build_venue_context` already carries every round's weekday — the
writer just never saw more than its own storyline's slice of it.

    from teg_analysis.reporting.settled_facts import build_settled_facts
    facts = build_settled_facts(18)                    # tournament writer
    facts = build_settled_facts(18, through_round=2)    # round 2 writer — leak-safe
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from teg_analysis.core.data_loader import load_all_data
from teg_analysis.reporting.era import trophy_metric
from teg_analysis.reporting.events import (
    JACKET,
    _proper,
    _trophy_cols,
    _trophy_label,
    leader_timeline,
)
from teg_analysis.reporting.venue import build_venue_context


def _safe_num(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return int(v) if float(v).is_integer() else float(v)


def build_hole_timeline(teg_num: int, all_data: Optional[pd.DataFrame] = None,
                        through_round: Optional[int] = None) -> dict:
    """The per-hole DataFrame plus a tie-aware leader timeline per competition.

    `through_round` bounds the walk to rounds `<= through_round` — the same
    leak-safety contract `course_history.build_player_course_history` uses,
    so a round report never sees a later round's standings.

    Internal building block for `build_settled_facts` and for the WP4 claim
    checker (`claims.py`), which needs the same per-hole rank data to verify
    `lead_event` / `rank_change` claims. Returns a DataFrame (`teg_df`), so
    this is NOT what goes in a writer's JSON context — see
    `build_settled_facts` for that.
    """
    if all_data is None:
        all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    all_data = all_data.copy()
    all_data["Player"] = all_data["Player"].map(_proper)
    teg_df = all_data[all_data["TEGNum"] == teg_num].copy()
    if teg_df.empty:
        raise ValueError(f"No data for TEG {teg_num}")
    if through_round is not None:
        teg_df = teg_df[teg_df["Round"] <= through_round]

    from teg_analysis.analysis.commentary import _add_rank_netvp_teg
    teg_df = _add_rank_netvp_teg(teg_df)

    metric = trophy_metric(teg_num)
    cols = _trophy_cols(metric)
    trophy_label = _trophy_label(metric)
    player_names = (teg_df[["Pl", "Player"]].drop_duplicates()
                    .set_index("Pl")["Player"].to_dict())

    # Spoon "rank 1" (worst) as the mirror of whichever Trophy rank this era
    # uses — same construction as events.py's _turning_points, kept in sync
    # deliberately rather than imported, since it's a one-line transform and
    # importing a private helper across modules would be the wrong coupling.
    spoon_rank_col = cols["rank_hole"]
    spoon_df = teg_df.assign(
        _SpoonRank=(teg_df.groupby(["Round", "Hole"])[spoon_rank_col].transform("max")
                   + 1 - teg_df[spoon_rank_col]))

    timelines = {
        trophy_label: leader_timeline(teg_df, cols["rank_hole"]),
        JACKET: leader_timeline(teg_df, "Rank_GrossVP_TEG"),
        "Wooden Spoon": leader_timeline(spoon_df, "_SpoonRank"),
    }
    return {
        "teg_df": teg_df, "spoon_df": spoon_df, "player_names": player_names,
        "metric": metric, "trophy_label": trophy_label,
        "cols": cols, "timelines": timelines,
    }


def build_settled_facts(teg_num: int, all_data: Optional[pd.DataFrame] = None,
                        through_round: Optional[int] = None) -> dict:
    """JSON-safe facts the writer can be TOLD instead of asked to infer.

    Returns:
        round_days: {round: weekday} for rounds `<= through_round` only —
            answers "which round was Sunday" without exposing later rounds.
        lead_timeline: {competition: [{round, hole, new_leader,
            previous_leader}, ...]} — every OUTRIGHT change, tie-aware (a
            tied hole is not a "change"; drawing level then re-taking it
            outright is two changes, matching `long_lead_lost`'s semantics).
        final_totals: {competition: [{player, total}, ...]} sorted best
            first, plus `decisive_metric` naming which one actually decides
            the Trophy this era — the fact "comfortably the better player"
            needed and didn't have.
        rank_snapshots: {"R{r}H{h}": {competition: [{player, rank}, ...]}}
            for just the holes referenced in `lead_timeline` (not every hole
            — that would be ~72 holes of noise for a handful of relevant
            moments).
    """
    tl = build_hole_timeline(teg_num, all_data=all_data, through_round=through_round)
    teg_df, spoon_df = tl["teg_df"], tl["spoon_df"]
    player_names, metric, cols = tl["player_names"], tl["metric"], tl["cols"]
    trophy_label = tl["trophy_label"]
    max_round = int(teg_df["Round"].max())

    venue = build_venue_context(teg_num)
    round_days = {int(r["round"]): r["weekday"] for r in venue.get("rounds", [])
                 if r.get("weekday") and int(r["round"]) <= max_round}

    lead_timeline_out: dict = {}
    notable_holes: set = set()
    for comp, timeline in tl["timelines"].items():
        changes = []
        prev_leader = None
        for key in timeline["ordered"]:
            leader = timeline["leader_at"].get(key)
            if leader is None:
                continue  # tied — not a settled leader at this hole
            if leader != prev_leader:
                rnd, hole = key
                changes.append({
                    "round": rnd, "hole": hole,
                    "new_leader": player_names.get(leader, leader),
                    "previous_leader": (player_names.get(prev_leader, prev_leader)
                                       if prev_leader else None),
                })
                notable_holes.add(key)
                prev_leader = leader
        lead_timeline_out[comp] = changes

    # Final hole of the final round in scope, per player — "{Metric} Cum TEG"
    # is the running total already in the parquet, so the last hole's value
    # IS the tournament total (or the total through `through_round`).
    max_hole = int(teg_df[teg_df["Round"] == max_round]["Hole"].max())
    final_rows = teg_df[(teg_df["Round"] == max_round) & (teg_df["Hole"] == max_hole)]
    trophy_score_col = "NetVP Cum TEG" if metric == "net_vs_par" else "Stableford Cum TEG"
    final_totals: dict = {}
    score_specs = {
        trophy_label: (trophy_score_col, cols.get("score_ascending", False)),
        # Raw gross strokes, not vs-par — the Jacket total players actually
        # recognise (matches the plan's own worked example: "JP 383 vs AB
        # 412"). Ranking order is identical to GrossVP either way (they're a
        # constant offset apart), but strokes read as an actual score.
        JACKET: ("Sc Cum TEG", True),
    }
    for comp, (score_col, ascending) in score_specs.items():
        totals = (final_rows[["Player", score_col]].drop_duplicates()
                 .sort_values(score_col, ascending=ascending))
        final_totals[comp] = [
            {"player": row["Player"], "total": _safe_num(row[score_col])}
            for _, row in totals.iterrows()
        ]
    # The Jacket is reported both ways in real prose — raw strokes ("412
    # gross") and gross-vs-par ("+66") — and a checker matching only the
    # first flags the second as a false error (real case: "won the TEG 18
    # Green Jacket at +66 gross" checked as if 66 were a stroke total).
    # `total_vs_par` gives the claim checker the other valid representation.
    if JACKET in final_totals:
        vp_by_player = dict(zip(final_rows["Player"], final_rows["GrossVP Cum TEG"]))
        for row in final_totals[JACKET]:
            row["total_vs_par"] = _safe_num(vp_by_player.get(row["player"]))
    final_totals["decisive_metric"] = trophy_label

    def _snapshot(rank_col: str, source: pd.DataFrame, rnd: int, hole: int) -> list:
        snap = source[(source["Round"] == rnd) & (source["Hole"] == hole)]
        rows = sorted(
            ({"player": player_names.get(r["Pl"], r["Player"]), "rank": _safe_num(r[rank_col])}
             for _, r in snap.iterrows()),
            key=lambda d: (d["rank"] is None, d["rank"]))
        return rows

    rank_snapshots: dict = {}
    for rnd, hole in sorted(notable_holes):
        rank_snapshots[f"R{rnd}H{hole}"] = {
            trophy_label: _snapshot(cols["rank_hole"], teg_df, rnd, hole),
            JACKET: _snapshot("Rank_GrossVP_TEG", teg_df, rnd, hole),
            "Wooden Spoon": _snapshot("_SpoonRank", spoon_df, rnd, hole),
        }

    return {
        "round_days": round_days,
        "lead_timeline": lead_timeline_out,
        "final_totals": final_totals,
        "rank_snapshots": rank_snapshots,
    }
