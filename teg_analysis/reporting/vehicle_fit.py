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

TWO CALIBRATION FIXES (2026-08-13), both born from the same failure: an
early version returned the same top-4 vehicles (tragic_arc, redemption_arc,
catalogue, inversion) for every TEG tested. Root cause was two-fold:

1. The beat types feeding those vehicles (a 3-hole cold stretch, a birdie
   right after bogeys, a lead changing hands) are common in almost any
   multi-round tournament with a spread of handicaps — the raw sum measured
   "how much of this generic texture exists", which is roughly constant
   across TEGs, not "how much does this pattern define THIS one." Fixed by
   `_central_players`: arc-vehicle beats now only count when they belong to
   the Trophy winner, Jacket winner, or Wooden Spoon holder — the three
   names the report is already structured around — not any player in the
   field. A simplification (it misses a genuine runner-up story), but a
   principled one.
2. There was no notion of "typical" to compare against. Fixed by
   `historical_baseline` + `normalize_vehicle_fit`: score a run of past TEGs
   the same way, then report each vehicle as a z-score against that
   population instead of a raw sum. `rank_vehicle_fit` (raw) is kept for
   callers that don't have a baseline handy; `rank_vehicle_fit_normalized`
   is what actually differentiates between TEGs.
"""

from __future__ import annotations

import json
import os
from collections import Counter

# Checked-in cache of `historical_baseline()`'s output — computing it live is
# ~5s/TEG (event detection + history), too slow to redo on every plan call.
# Regenerate with `refresh_baseline_cache()` when beat-detection logic changes
# materially (a new event type, a changed scoring weight); a routine plan
# call should never need to.
BASELINE_CACHE_PATH = os.path.join(os.path.dirname(__file__), "vehicle_fit_baseline.json")

ALL_VEHICLE_NAMES = (
    "counterfactual", "dual_narrative", "tragic_arc", "redemption_arc", "motif",
    "bookends", "ensemble", "catalogue", "inevitability", "hero_arc", "comeback",
    "inversion", "origin", "underdog", "theme_led_body",
)


def _add(scores: dict, vehicle: str, points: float, reason: str) -> None:
    if points <= 0:
        return
    entry = scores.setdefault(vehicle, {"score": 0.0, "reasons": []})
    entry["score"] += points
    entry["reasons"].append(reason)


def _central_players(arcs: dict) -> set:
    """The three names the report is already structured around — Trophy
    winner, Jacket winner, Wooden Spoon holder. Used to keep arc-vehicle
    scoring about who the story is actually about, not any player with a
    stretch of bad holes. Doesn't capture a genuine runner-up story; a
    deliberate simplification, not an oversight."""
    out = set()
    for key in ("trophy", "jacket"):
        w = (arcs.get(key) or {}).get("winner")
        if w:
            out.add(w)
    loser = (arcs.get("spoon") or {}).get("loser")
    if loser:
        out.add(loser)
    return out


def score_vehicle_fit(beats: list, arcs: dict, tournament_shape: dict,
                      player_history: dict) -> dict:
    """Score each narrative vehicle against already-computed bundle signals.

    Returns {vehicle: {"score": float, "reasons": [str, ...]}}, unsorted —
    use `rank_vehicle_fit` (raw) or `rank_vehicle_fit_normalized` (against a
    baseline) to sort. Pure function: takes the pieces `assemble_bundle`
    already builds, so it can be called during bundle assembly without
    recomputing beats/arcs.
    """
    scores: dict = {}
    central = _central_players(arcs)

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

    # --- tragic_arc / inversion / redemption_arc: collapse & recovery beats,
    # restricted to the three central players (see _central_players) ---
    for b in beats:
        t = b["type"]
        players = set(b.get("players") or [])
        if not (players & central):
            continue
        imp = b["scores"]["importance"]
        late = (b.get("round") or 1) >= 3
        if t in ("collapse_after_steady", "cold_stretch"):
            pts = imp * (1.3 if late else 1.0) * 0.6
            _add(scores, "tragic_arc", pts, f"{b['id']} (R{b['round']}): {b['headline']}")
        elif t == "long_lead_lost":
            pts = imp * 0.8
            _add(scores, "tragic_arc", pts, f"{b['id']}: {b['headline']}")
            _add(scores, "inversion", pts * 0.7, f"{b['id']}: {b['headline']}")
            # The player throwing away a long lead is tragic_arc/inversion; the
            # one who overtook it — coming from behind to dethrone a long-held
            # leader — is a redemption/hero beat in its own right, not just the
            # passive beneficiary of someone else's collapse.
            new_leader = (b.get("context") or {}).get("new_leader")
            if new_leader in central:
                _add(scores, "redemption_arc", pts * 0.6, f"{b['id']}: {b['headline']}")
        elif t == "recovery":
            # NOT hot_stretch — a strong run of holes isn't evidence of recovering
            # from anything; `recovery` specifically means birdie-or-better right
            # after a bogey-or-worse run, which is the actual pattern.
            early = (b.get("round") or 4) <= 2
            pts = imp * (1.3 if early else 1.0) * 1.2
            _add(scores, "redemption_arc", pts, f"{b['id']} (R{b['round']}): {b['headline']}")
        elif t == "round_swing":
            # A good round right after a bad one, or vice versa — the same
            # tragic/redemption shape as the hole-level beats above, but at
            # round granularity, per Jon's ask (2026-08-13).
            direction = (b.get("context") or {}).get("direction")
            delta = abs((b.get("context") or {}).get("delta") or 0)
            pts = imp * (1.0 + 0.03 * delta)
            if direction == "up":
                _add(scores, "redemption_arc", pts, f"{b['id']}: {b['headline']}")
            elif direction == "down":
                _add(scores, "tragic_arc", pts, f"{b['id']}: {b['headline']}")

    # --- redemption_arc (tournament-level): eventual Trophy winner's own R1 position,
    # and how large a gap they closed to win ("coming back from a long way back") ---
    trophy = arcs.get("trophy", {})
    traj = trophy.get("winner_trajectory") or []
    if len(traj) >= 2:
        early_pos = traj[0]["pos"]
        if early_pos >= 3:
            _add(scores, "redemption_arc", 2.0 + early_pos,
                 f"eventual Trophy winner was ranked {early_pos} after R1")
        # `gap` is the winner's own deficit to the round leader at that point
        # (None once they ARE the leader). The largest early deficit they
        # actually closed is the "long way back" signal.
        early_gaps = [t["gap"] for t in traj[:-1] if t.get("gap") is not None]
        if early_gaps:
            max_gap = max(early_gaps)
            if max_gap >= 8:
                _add(scores, "redemption_arc", max_gap * 0.5,
                     f"eventual Trophy winner was {max_gap} behind the leader at one point")

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
        # Case-insensitive: arcs['trophy']['winner'] is Proper Case ("Jon
        # Baker", via events.py's _proper()) but player_history keys are
        # surname-uppercase ("Jon BAKER", via build_player_cross_teg_history,
        # which doesn't apply the same normalisation). A plain `==` here
        # silently never matched anyone — found 2026-08-13 by testing the
        # new same-rank-streak milestone and seeing it not fire on TEG 17.
        is_trophy_winner = player.upper() == (winner or "").upper()
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
            # Same-rank streak broken by a win — the "stuck at 4th for three
            # TEGs, then wins" pattern (see history_context.py, added
            # 2026-08-13 specifically because this heuristic missed TEG 17's
            # actual hero_arc pick without it).
            if m.startswith("Trophy rank") and "each of the last" in m and is_trophy_winner:
                _add(scores, "comeback", 5.0, f"{player}: {m}, then wins")
                _add(scores, "hero_arc", 3.5, f"{player}: {m}, then wins")
        if hist.get("trophy_wins", 0) == 0 and is_trophy_winner:
            _add(scores, "origin", 6.0, f"{player}: first-ever Trophy win")

    # --- catalogue: one CENTRAL player racking up repeated blow-up/collapse beats ---
    blowup_types = {"cold_stretch", "collapse_after_steady"}
    per_player = Counter()
    for b in beats:
        if b["type"] in blowup_types:
            for p in b["players"]:
                if p in central:
                    per_player[p] += 1
    for player, n in per_player.items():
        if n >= 3:
            _add(scores, "catalogue", 2.0 + n, f"{player}: {n} separate blow-up/collapse beats")

    return scores


def rank_vehicle_fit(scores: dict, n: int = 5) -> list[dict]:
    """Sort RAW scores desc, trim reasons to the top 3 each, keep the top `n`.

    Prefer `rank_vehicle_fit_normalized` when a baseline is available — raw
    scores don't tell you whether a value is unusual for a TEG, only that
    it's nonzero. Kept for callers (e.g. the live editor prompt) where
    computing a fresh baseline per call isn't worth the ~5s/TEG cost.
    """
    ranked = sorted(
        ({"vehicle": v, "score": round(d["score"], 1), "reasons": d["reasons"][:3]}
         for v, d in scores.items()),
        key=lambda x: -x["score"],
    )
    return ranked[:n]


def historical_baseline(tegs: list, mode: str = "balanced", tone: str = "house") -> dict:
    """Score every vehicle for each TEG in `tegs` and return per-vehicle
    {"mean": float, "std": float} across that population. Missing vehicles
    for a given TEG count as 0 (a vehicle that didn't fire is real signal,
    not missing data) so the baseline reflects true typical/atypical scores.

    Free — no LLM call — but costs ~5s/TEG (event detection + history).
    """
    import statistics

    per_teg = {t: score_vehicle_fit_for_teg(t, mode=mode, tone=tone) for t in tegs}
    baseline: dict = {}
    for vehicle in ALL_VEHICLE_NAMES:
        values = [per_teg[t].get(vehicle, {}).get("score", 0.0) for t in tegs]
        mean = statistics.mean(values)
        std = statistics.pstdev(values)
        baseline[vehicle] = {"mean": round(mean, 2), "std": round(std, 2), "n": len(tegs)}
    return baseline


def load_baseline_cache() -> dict:
    """Load the checked-in baseline, or {} if it hasn't been generated yet
    (callers should fall back to raw `rank_vehicle_fit` in that case)."""
    try:
        with open(BASELINE_CACHE_PATH) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def refresh_baseline_cache(tegs: list = None, mode: str = "balanced",
                           tone: str = "house") -> dict:
    """Recompute the baseline and overwrite the checked-in cache. Defaults to
    every TEG with score data (2-18 as of 2026-08-13). Run this, and commit
    the result, whenever beat-detection logic changes materially."""
    from teg_analysis.core.data_loader import load_all_data

    if tegs is None:
        df = load_all_data()
        tegs = sorted(int(t) for t in df["TEGNum"].unique())
    baseline = historical_baseline(tegs, mode=mode, tone=tone)
    with open(BASELINE_CACHE_PATH, "w") as f:
        json.dump(baseline, f, indent=2)
    return baseline


def normalize_vehicle_fit(scores: dict, baseline: dict) -> list[dict]:
    """Score every vehicle in `ALL_VEHICLE_NAMES` (not just those that fired)
    as a z-score against `baseline`, sorted desc. A vehicle absent from
    `scores` is a real 0, scored against the same baseline as everything
    else — that's what lets "nobody had a collapse this time" outrank a
    collapse that happens every TEG.
    """
    ranked = []
    for vehicle in ALL_VEHICLE_NAMES:
        raw = scores.get(vehicle, {}).get("score", 0.0)
        reasons = scores.get(vehicle, {}).get("reasons", [])[:3]
        b = baseline.get(vehicle, {"mean": 0.0, "std": 0.0})
        mean, std = b["mean"], b["std"]
        if std > 0:
            z = (raw - mean) / std
        else:
            z = 0.0 if raw == mean else (3.0 if raw > mean else -3.0)
        ranked.append({"vehicle": vehicle, "raw": round(raw, 1), "z": round(z, 2),
                       "baseline_mean": mean, "reasons": reasons})
    ranked.sort(key=lambda x: -x["z"])
    return ranked


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
