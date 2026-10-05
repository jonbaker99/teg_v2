"""What does a player need over their remaining holes to win the Trophy or the Jacket?

Works from a ``win_probability.Snapshot`` (completed rounds plus the live round's
entered holes). Every other player is projected to a final total, the best of
those is the bar, and the answer is what the player must score on their own
remaining holes to clear it. Users think in gross, so each target comes back in
gross strokes as well as in the competition's own measure.

Rival projection (``rivals``):
  ``same_pace``  total so far + per-hole average so far x holes left. A player
                 with no holes played yet falls back to ``expected`` if given,
                 else their handicap (net par: handicap / 18 gross vs par a hole).
  ``expected``   total so far + expected gross vs par per 18 remaining holes
                 (``expected``: {player: mean}, the ``mean`` column of the gross
                 rows of ``win_probs_live``) x holes left / 18. Missing players
                 fall back to their handicap.
The same rule projects the player too, so the list shows where they are heading.

Measures: Trophy is Stableford points from TEG ``STABLEFORD_ERA_TEG``, net vs par
before; Jacket is gross vs par. Stableford and gross are linked by
``gross_vp = strokes received + 2 x holes - points``, exact unless a hole scores 0
points, so callers say "about". Ties are shared wins, so both the target to win
outright and the target to tie are returned. A round with no scorecard yet is
par 72 with strokes = handicap.

UI-agnostic: pandas/numpy only; returns plain JSON-serialisable dicts.
"""

from __future__ import annotations

import math

import pandas as pd

from teg_analysis.analysis import win_probability as wp

COMPETITIONS = ("trophy", "jacket")
RIVAL_MODES = ("same_pace", "expected")
_HOLES = 18
_RANDOM_PAR = 72
_RECENT_TEGS = 3


def _left(snap: wp.Snapshot, p: str) -> tuple[int, int, int]:
    """(holes left, strokes received on them, par of them) for p."""
    rem = snap.remaining[p]
    hc = int(snap.handicaps[p])
    k = int(snap.random_rounds)
    holes = len(rem) + _HOLES * k
    strokes = wp._strokes(rem["SI"].to_numpy(int), hc) + k * hc if len(rem) else k * hc
    par = int(rem["Par"].sum()) + _RANDOM_PAR * k if len(rem) else _RANDOM_PAR * k
    return holes, int(strokes), par


def _rem_gross_vp(snap: wp.Snapshot, p: str, holes: int, rivals: str,
                  expected: dict[str, float] | None) -> float:
    """Projected gross vs par over p's remaining holes."""
    if holes == 0:
        return 0.0
    if rivals == "same_pace" and snap.holes_played[p] > 0:
        return snap.gross[p] / snap.holes_played[p] * holes
    if expected is not None and p in expected and expected[p] is not None \
            and not (isinstance(expected[p], float) and math.isnan(expected[p])):
        return float(expected[p]) * holes / _HOLES
    return snap.handicaps[p] / _HOLES * holes  # net par


def _measure(snap: wp.Snapshot, competition: str) -> str:
    if competition == "jacket":
        return "gross vs par"
    return "Stableford" if snap.stableford else "net vs par"


def _now(snap: wp.Snapshot, p: str, competition: str) -> int:
    return int(snap.gross[p] if competition == "jacket" else snap.net[p])


def _project(snap: wp.Snapshot, p: str, competition: str, rivals: str,
             expected: dict[str, float] | None) -> float:
    """Projected final total in the competition's measure."""
    holes, strokes, _ = _left(snap, p)
    g = _rem_gross_vp(snap, p, holes, rivals, expected)
    now = _now(snap, p, competition)
    if competition == "jacket":
        return now + g
    if snap.stableford:
        return now + strokes + 2 * holes - g
    return now + g - strokes


def _higher_better(snap: wp.Snapshot, competition: str) -> bool:
    return competition == "trophy" and snap.stableford


def _targets(best: float, higher: bool) -> dict[str, int]:
    """Whole-number totals that tie and that win outright against a projected ``best``."""
    b = round(best, 9)
    if higher:
        return {"tie": math.ceil(b), "outright": math.floor(b) + 1}
    return {"tie": math.floor(b), "outright": math.ceil(b) - 1}


def _need(snap: wp.Snapshot, p: str, competition: str, target: int,
          holes: int, strokes: int, par: int) -> dict:
    """Translate a target total into what p must score on their remaining holes."""
    now = _now(snap, p, competition)
    need = target - now
    if competition == "jacket":
        gvp, points, nvp = need, None, None
    elif snap.stableford:
        gvp, points, nvp = strokes + 2 * holes - need, need, None
    else:
        gvp, points, nvp = need + strokes, None, need
    per = _HOLES / holes
    return {
        "target_total": int(target),
        "points": None if points is None else int(points),
        "net_vs_par": None if nvp is None else int(nvp),
        "gross_vp": int(gvp),
        "gross": int(gvp + par),
        "per_round_gross": round((gvp + par) * per, 1),
        "per_round_points": None if points is None else round(points * per, 1),
    }


def _reality(history: pd.DataFrame, snap: wp.Snapshot, p: str, per_round_vp: float) -> dict:
    """The player's own record over full 18-hole rounds, against the needed per-round gross vs par."""
    h = history[(history["Pl"] == p) & (history["TEGNum"] < snap.teg_num)]
    full = (h.groupby(["TEGNum", "Round"]).agg(vp=("GrossVP", "sum"), n=("GrossVP", "size"))
            .reset_index())
    full = full[full["n"] == _HOLES]
    if full.empty:
        return {"best_round_vp": None, "best_round_gross": None, "rounds_recent": 0,
                "rounds_recent_at_or_better": 0, "recent_tegs": []}
    tegs = sorted(full["TEGNum"].unique())[-_RECENT_TEGS:]
    recent = full[full["TEGNum"].isin(tegs)]
    best = int(full["vp"].min())
    return {"best_round_vp": best, "best_round_gross": _RANDOM_PAR + best,
            "rounds_recent": int(len(recent)),
            "rounds_recent_at_or_better": int((recent["vp"] <= per_round_vp + 1e-9).sum()),
            "recent_tegs": [int(t) for t in tegs]}


def what_it_takes(snap: wp.Snapshot, player: str, competition: str, rivals: str = "same_pace",
                  expected: dict[str, float] | None = None,
                  history: pd.DataFrame | None = None) -> dict:
    """What ``player`` must score over their remaining holes to win ``competition``.

    ``competition``: "trophy" or "jacket". See the module docstring for ``rivals``,
    ``expected`` and the conversion. ``history``: hole-level frame (TEGNum, Round,
    Pl, GrossVP) for the reality check; skipped when None. Returns a plain dict:
    ``need`` holds the totals to win ``outright`` and to ``tie`` (points are over
    the remaining holes; ``target_total`` is the final total in the measure),
    ``reality`` the player's own rounds, ``out_of_reach`` whether the needed round
    beats their best ever, ``no_holes_left`` (then ``need`` is None and
    ``leading``/``tied`` come from the totals).
    """
    if competition not in COMPETITIONS:
        raise ValueError(f"competition must be 'trophy' or 'jacket', not {competition!r}")
    if rivals not in RIVAL_MODES:
        raise ValueError(f"rivals must be 'same_pace' or 'expected', not {rivals!r}")
    if player not in snap.handicaps:
        raise ValueError(f"Unknown player {player!r}; players are {sorted(snap.handicaps)}")
    others = [p for p in snap.handicaps if p != player]
    if not others:
        raise ValueError("No rivals to compare against")

    higher = _higher_better(snap, competition)
    measure = _measure(snap, competition)
    name = lambda q: snap.names.get(q, q)  # noqa: E731
    proj = {q: _project(snap, q, competition, rivals, expected) for q in snap.handicaps}
    order = sorted(proj, key=lambda q: -proj[q] if higher else proj[q])
    best_pl = max(others, key=lambda q: proj[q]) if higher else min(others, key=lambda q: proj[q])
    holes, strokes, par = _left(snap, player)
    live = snap.live_round
    out = {
        "teg": int(snap.teg_num), "player": player, "name": name(player),
        "competition": competition, "measure": measure, "rivals": rivals,
        "rounds_done": int(snap.rounds_done), "live_round": None if live is None else int(live),
        "holes_left": int(holes),
        "now": {"total": _now(snap, player, competition), "gross_vp_now": int(snap.gross[player])},
        "projections": [{"player": q, "name": name(q), "now": _now(snap, q, competition),
                         "projected": round(float(proj[q]), 2)} for q in order],
        "best_rival": {"player": best_pl, "name": name(best_pl),
                       "projected": round(float(proj[best_pl]), 2)},
        "need": None, "reality": None, "out_of_reach": False,
        "no_holes_left": holes == 0, "notes": [],
    }
    notes = out["notes"]
    if rivals == "same_pace":
        notes.append("Rivals keep their pace so far: total so far plus their average per hole times holes left.")
    else:
        notes.append("Rivals score what the model expects over their remaining holes.")
    if snap.stableford and competition == "trophy":
        notes.append("Points and gross are linked by gross vs par = strokes received + 2 per hole - points; "
                     "about right (exact unless a hole scores 0 points).")
    if snap.random_rounds:
        notes.append(f"{snap.random_rounds} later round(s) have no scorecard yet: taken as par 72 "
                     "with strokes equal to handicap.")

    if holes == 0:
        mine = _now(snap, player, competition)
        theirs = [_now(snap, q, competition) for q in others]
        top = max(theirs) if higher else min(theirs)
        out["leading"] = bool(mine > top if higher else mine < top)
        out["tied"] = bool(mine == top)
        return out

    tg = _targets(proj[best_pl], higher)
    out["need"] = {k: _need(snap, player, competition, t, holes, strokes, par) for k, t in tg.items()}
    pts = out["need"]["outright"]["points"]
    if pts is not None and pts <= 0:
        # Already past the bar: any finish wins on this projection; a gross figure means nothing.
        out["already_enough"] = True
        notes.append("Already ahead of every rival's projected total: finishing the holes is enough "
                     "on this projection.")
        return out
    out["already_enough"] = False
    if pts is not None and pts < holes:
        # Under a point a hole means several 0-point holes, which the conversion ignores.
        notes.append("Under a point a hole on average: several holes could score 0, so the gross "
                     "figure is a rough ceiling rather than a target.")
    per_vp = out["need"]["outright"]["gross_vp"] * _HOLES / holes
    if history is not None:
        out["reality"] = _reality(history, snap, player, per_vp)
        best = out["reality"]["best_round_vp"]
        out["out_of_reach"] = bool(best is not None and per_vp < best - 1e-9)
    return out


def what_it_takes_all(snap: wp.Snapshot, competition: str, rivals: str = "same_pace",
                      expected: dict[str, float] | None = None,
                      history: pd.DataFrame | None = None) -> list[dict]:
    """``what_it_takes`` for every player, in snapshot order."""
    return [what_it_takes(snap, p, competition, rivals, expected, history) for p in snap.handicaps]
