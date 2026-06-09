"""Tournament-shape signals for the report bundle.

Currently surfaces a single signal — `close_finish` — read from the Trophy
arc. A close finish is the only tournament-shape pattern important enough
to override the editor's vehicle selection: when the Trophy was decided
late and by a small margin, the report's prominent vehicle must reflect
that, regardless of any historical-context framing.

Other tournament-shape patterns (procession, wire-to-wire, blowup) are
deliberately NOT surfaced as signals — they should come through in the
telling, not the framing. See plan §6.
"""

from __future__ import annotations

from typing import Optional


def detect_close_finish(arcs: dict, trophy_metric: str) -> dict:
    """Return whether the Trophy finish was close, with the firing signals.

    Reads `arcs['trophy']`. Returns:
        {
            "close_finish": bool,
            "signals": [str, ...],     # human-readable reasons it fired
            "final_margin": int,
            "trophy_metric": str,
        }

    Trophy is Stableford for TEG 8+ (lead = points clear; higher = wider gap)
    or net-vs-par for TEGs 1-7 (lead = strokes clear; same direction). Both
    are reported as positive integers in `leader_by_round[*].lead`, so the
    same thresholds apply.

    A close finish fires if EITHER of:
      A. final_margin ≤ 4  (definitively close on the scoreboard)
      B. final_margin ≤ 8 AND (decisive moment is in R4 OR an outright
         lead change happened in R4)  (margin slightly bigger but the
         finish itself was contested in R4)

    A "lead ≤ 4 at end of R3" alone is NOT enough — TEG 9 had lead 3 at
    end of R3 and Patterson put R4 to bed; the storyline is "by a
    distance", not "close finish". The detector must see R4 itself being
    contested, not just R4 starting close.
    """
    trophy = arcs.get("trophy")
    if not trophy:
        return {"close_finish": False, "signals": [], "final_margin": None, "trophy_metric": trophy_metric}

    leader_by_round = trophy.get("leader_by_round") or []
    if not leader_by_round:
        return {"close_finish": False, "signals": [], "final_margin": None, "trophy_metric": trophy_metric}

    final_margin = int(leader_by_round[-1].get("lead", 0))
    decisive = trophy.get("decisive_takeover") or {}
    decisive_in_r4 = decisive.get("round") == 4
    lead_changes = trophy.get("lead_changes") or []
    outright_r4_change = any(
        (c.get("round") == 4 and c.get("outright", False)) for c in lead_changes
    )

    signals: list[str] = []

    # Rule A — small margin alone
    if final_margin <= 4:
        signals.append(f"final margin {final_margin} ≤ 4 (decisive finish was close)")

    # Rule B — moderate margin but contested late
    if final_margin <= 8 and (decisive_in_r4 or outright_r4_change):
        contest = []
        if decisive_in_r4:
            contest.append("decisive moment in R4")
        if outright_r4_change:
            contest.append("outright lead change in R4")
        signals.append(
            f"final margin {final_margin} ≤ 8 with " + " + ".join(contest)
        )

    return {
        "close_finish": bool(signals),
        "signals": signals,
        "final_margin": final_margin,
        "trophy_metric": trophy_metric,
    }


def recent_vehicle_choices(teg_num: int, n: int = 3, output_dir: str = "data/commentary") -> list[dict]:
    """Read the last `n` TEG story-plan JSON files (TEGs before this one) and
    return their `narrative_vehicles` picks. Surfaces "what got picked recently"
    so the editor has a deliberate variation signal.

    Returns a list (oldest first) of:
        {"teg": int, "vehicles": list[str], "structure": str, "title": str}
    """
    import json
    import os

    out: list[dict] = []
    candidates = sorted(
        t for t in range(max(1, teg_num - 8), teg_num)
        if os.path.exists(os.path.join(output_dir, f"teg_{t}_story_plan.json"))
    )
    # Take the most recent `n`
    for t in candidates[-n:]:
        path = os.path.join(output_dir, f"teg_{t}_story_plan.json")
        try:
            with open(path) as f:
                d = json.load(f)
            out.append({
                "teg": t,
                "vehicles": d.get("narrative_vehicles", []),
                "structure": d.get("narrative_structure", ""),
                "title": d.get("title", ""),
            })
        except (OSError, json.JSONDecodeError):
            continue
    return out
