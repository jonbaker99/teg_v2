"""Deterministic, free heuristic scoring of narrative-vehicle fit.

Given the same signals `assemble_bundle` already computes (beats, competition
arcs, tournament shape, player history), score how well each `narrative_vehicle`
fits THIS TEG's actual facts. No LLM call — pure arithmetic over data already
in memory, so it costs nothing to run on every plan.

This is a heuristic, not a verdict: it detects the PRESENCE of a pattern (a
collapse beat exists, a milestone string says "defending champion"), not
whether that pattern is genuinely the most interesting angle on the
tournament — that judgement call still belongs to the editor prompt. Treat
the output as a ranked candidate list to weigh, the same way
`recent_vehicle_choices` is advisory rather than a hard rule.
"""

from __future__ import annotations

from collections import Counter


def _add(scores: dict, vehicle: str, points: float, reason: str) -> None:
    if points <= 0:
        return
    entry = scores.setdefault(vehicle, {"score": 0.0, "reasons": []})
    entry["score"] += points
    entry["reasons"].append(reason)


def score_vehicle_fit(beats: list, arcs: dict, tournament_shape: dict,
                      player_history: dict) -> dict:
    """Score each narrative vehicle against already-computed bundle signals.

    Returns {vehicle: {"score": float, "reasons": [str, ...]}}, unsorted —
    use `rank_vehicle_fit` to sort. Pure function: takes the pieces
    `assemble_bundle` already builds, so it can be called during bundle
    assembly without recomputing beats/arcs.
    """
    scores: dict = {}

    # --- counterfactual / dual_narrative: close finish ---
    if tournament_shape.get("close_finish"):
        _add(scores, "counterfactual", 6.0,
             "close finish: " + "; ".join(tournament_shape.get("signals", [])))
        trophy = arcs.get("trophy", {})
        outright_leaders = {c["player"] for c in trophy.get("lead_changes", [])
                            if c.get("outright")}
        if len(outright_leaders) >= 2:
            _add(scores, "dual_narrative", 4.0,
                 f"{len(outright_leaders)} different outright Trophy leaders in a close finish")

    # --- tragic_arc / inversion / redemption_arc: collapse & recovery beats ---
    for b in beats:
        t = b["type"]
        imp = b["scores"]["importance"]
        late = (b.get("round") or 1) >= 3
        if t in ("collapse_after_steady", "cold_stretch"):
            pts = imp * (1.3 if late else 1.0) * 0.6
            _add(scores, "tragic_arc", pts, f"{b['id']} (R{b['round']}): {b['headline']}")
        elif t == "long_lead_lost":
            pts = imp * 0.8
            _add(scores, "tragic_arc", pts, f"{b['id']}: {b['headline']}")
            _add(scores, "inversion", pts * 0.7, f"{b['id']}: {b['headline']}")
        elif t == "recovery":
            # NOT hot_stretch — a strong run of holes isn't evidence of recovering
            # from anything; `recovery` specifically means birdie-or-better right
            # after a bogey-or-worse run, which is the actual pattern.
            early = (b.get("round") or 4) <= 2
            pts = imp * (1.3 if early else 1.0) * 1.2
            _add(scores, "redemption_arc", pts, f"{b['id']} (R{b['round']}): {b['headline']}")

    # --- redemption_arc (tournament-level): eventual Trophy winner's own R1 position ---
    trophy = arcs.get("trophy", {})
    traj = trophy.get("winner_trajectory") or []
    if len(traj) >= 2:
        early_pos = traj[0]["pos"]
        if early_pos >= 3:
            _add(scores, "redemption_arc", 2.0 + early_pos,
                 f"eventual Trophy winner was ranked {early_pos} after R1")

    # --- inevitability (supporting only): wire-to-wire, no lead changes after R1 ---
    for label, key in (("Trophy", "trophy"), ("Green Jacket", "jacket")):
        arc = arcs.get(key, {})
        arc_traj = arc.get("winner_trajectory") or []
        if arc_traj and all(p["pos"] == 1 for p in arc_traj):
            summary = arc.get("lead_change_summary", {})
            if summary.get("total", 0) <= summary.get("early_round1", 0):
                _add(scores, "inevitability", 5.0,
                     f"{label} led wire-to-wire, no lead changes after R1")

    # --- hero_arc / comeback / inversion / underdog / origin: career milestones ---
    winner = trophy.get("winner")
    for player, hist in player_history.items():
        milestones = hist.get("notable_milestones", [])
        is_trophy_winner = player == winner
        for m in milestones:
            if "defending" in m:
                if is_trophy_winner:
                    _add(scores, "hero_arc", 3.0, f"{player}: {m} — won again")
                else:
                    _add(scores, "inversion", 4.0, f"{player}: {m} but did not repeat")
            if "back-to-back" in m and "Trophy" in m and is_trophy_winner:
                _add(scores, "hero_arc", 3.5, f"{player}: {m}")
            if "runner-up" in m and "without a win" in m and is_trophy_winner:
                _add(scores, "comeback", 5.0, f"{player}: {m}, now wins")
                _add(scores, "underdog", 3.0, f"{player}: {m}, now wins")
            if "Wooden Spoon" in m and is_trophy_winner:
                _add(scores, "underdog", 4.0, f"{player}: {m} — now the Trophy winner")
        if hist.get("trophy_wins", 0) == 0 and is_trophy_winner:
            _add(scores, "origin", 6.0, f"{player}: first-ever Trophy win")

    # --- catalogue: one player racking up repeated blow-up/collapse beats ---
    blowup_types = {"cold_stretch", "collapse_after_steady"}
    per_player = Counter()
    for b in beats:
        if b["type"] in blowup_types:
            for p in b["players"]:
                per_player[p] += 1
    for player, n in per_player.items():
        if n >= 3:
            _add(scores, "catalogue", 2.0 + n, f"{player}: {n} separate blow-up/collapse beats")

    return scores


def rank_vehicle_fit(scores: dict, n: int = 5) -> list[dict]:
    """Sort scores desc, trim reasons to the top 3 each, keep the top `n` vehicles."""
    ranked = sorted(
        ({"vehicle": v, "score": round(d["score"], 1), "reasons": d["reasons"][:3]}
         for v, d in scores.items()),
        key=lambda x: -x["score"],
    )
    return ranked[:n]


def score_vehicle_fit_for_teg(teg_num: int, mode: str = "balanced", tone: str = "house",
                              events_cache=None, venue_cache=None) -> dict:
    """Standalone convenience for scripting/inspection: assembles the bundle
    itself. `assemble_bundle` calls the pure `score_vehicle_fit` directly
    instead, using pieces it has already built, to avoid recomputing beats
    and arcs twice per plan call."""
    from teg_analysis.reporting.story_plan import assemble_bundle

    bundle, _ = assemble_bundle(teg_num, mode=mode, tone=tone, top_n=None,
                                events_cache=events_cache, venue_cache=venue_cache)
    return score_vehicle_fit(bundle["beats"], bundle["competition_arcs"],
                             bundle.get("tournament_shape") or {},
                             bundle.get("player_history") or {})
