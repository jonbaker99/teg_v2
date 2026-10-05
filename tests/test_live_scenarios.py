"""Tests for live_scenarios.what_it_takes on hand-built snapshots (all par-4 card, SI 1..18)."""
import json

import pandas as pd
import pytest

from teg_analysis.analysis import live_scenarios as ls
from teg_analysis.analysis import win_probability as wp

CARD = pd.DataFrame({"Hole": range(1, 19), "Par": 4, "SI": range(1, 19)})


def _rem(rnd=2):
    return CARD.assign(Round=rnd)[["Round", "Hole", "Par", "SI"]]


def _empty():
    return pd.DataFrame(columns=["Round", "Hole", "Par", "SI"], dtype=int)


def snap(stableford=True, random_rounds=0, finished=False, net=None):
    """A (hc 9) shot +9 gross, B (hc 0) +10 gross, over round 1 of 2."""
    rem = (lambda: _empty()) if (finished or random_rounds) else _rem
    return wp.Snapshot(
        teg_num=20 if stableford else 5, stableford=stableford, rounds_done=1, n_rounds=2,
        live_round=None, thru={"A": 0, "B": 0}, holes_played={"A": 18, "B": 18},
        gross={"A": 9, "B": 10},
        net=net or ({"A": 36, "B": 26} if stableford else {"A": 0, "B": 10}),
        handicaps={"A": 9, "B": 0}, names={"A": "Alf ONE", "B": "Bob TWO"},
        remaining={"A": rem(), "B": rem()}, random_rounds=random_rounds)


def test_same_pace_projection():
    r = ls.what_it_takes(snap(), "A", "trophy")
    proj = {p["player"]: p["projected"] for p in r["projections"]}
    assert proj["B"] == 52.0  # 26 + (36 + 0 strokes - 10)
    assert proj["A"] == 72.0  # 36 + (36 + 9 strokes - 9)
    assert r["best_rival"] == {"player": "B", "name": "Bob TWO", "projected": 52.0}
    assert [p["player"] for p in r["projections"]] == ["A", "B"]
    assert r["measure"] == "Stableford" and r["holes_left"] == 18


def test_outright_vs_tie_and_gross_conversion():
    r = ls.what_it_takes(snap(), "A", "trophy")
    out, tie = r["need"]["outright"], r["need"]["tie"]
    assert (tie["target_total"], out["target_total"]) == (52, 53)
    assert out["points"] == 17 and tie["points"] == 16
    # gross vs par = 9 strokes + 2*18 - 17 = 28 -> 100 strokes on par 72
    assert out["gross_vp"] == 28 and out["gross"] == 100 and out["per_round_gross"] == 100.0
    assert out["per_round_points"] == 17.0
    assert tie["gross"] == 101 and out["net_vs_par"] is None


def test_fractional_projection_rounds_target_up():
    s = snap()
    s.gross["B"], s.net["B"] = 9, 27
    s.holes_played["B"] = 12  # 9/12 per hole x 18 left... pace gives non-integer
    r = ls.what_it_takes(s, "A", "trophy")
    assert r["best_rival"]["projected"] != int(r["best_rival"]["projected"])
    b = r["best_rival"]["projected"]
    assert r["need"]["tie"]["target_total"] == -(-b // 1)
    assert r["need"]["outright"]["target_total"] == int(b // 1) + 1


def test_random_round_without_scorecard():
    r = ls.what_it_takes(snap(random_rounds=1), "A", "trophy")
    assert r["holes_left"] == 18
    assert r["need"]["outright"]["gross"] == 100  # par 72, strokes = handicap 9
    assert any("no scorecard" in n for n in r["notes"])


def test_net_vs_par_era():
    r = ls.what_it_takes(snap(stableford=False), "A", "trophy")
    assert r["measure"] == "net vs par"
    assert r["best_rival"]["projected"] == 20.0
    out = r["need"]["outright"]
    assert out["net_vs_par"] == 19 and out["points"] is None and out["per_round_points"] is None
    assert out["gross_vp"] == 28  # 19 net + 9 strokes
    assert r["need"]["tie"]["net_vs_par"] == 20


def test_jacket():
    r = ls.what_it_takes(snap(), "B", "jacket")
    assert r["measure"] == "gross vs par"
    assert r["best_rival"]["projected"] == 18.0
    assert r["need"]["outright"]["gross_vp"] == 7 and r["need"]["outright"]["gross"] == 79
    assert r["need"]["tie"]["gross_vp"] == 8
    assert r["now"] == {"total": 10, "gross_vp_now": 10}


def test_expected_rivals_and_fallback():
    r = ls.what_it_takes(snap(), "A", "jacket", rivals="expected", expected={"B": 4.0})
    proj = {p["player"]: p["projected"] for p in r["projections"]}
    assert proj["B"] == 14.0  # 10 + 4 per 18 holes
    assert proj["A"] == 9 + 9.0  # no expected for A: handicap 9 over 18 holes


def test_out_of_reach_and_reality():
    rows = []
    for tg, rnd, pl, vp in [(1, 1, "B", 2), (1, 2, "B", 6), (2, 1, "B", 3),
                            (1, 1, "A", 4), (2, 1, "A", 30), (3, 1, "A", 0)]:
        rows += [{"TEGNum": tg, "Round": rnd, "Pl": pl, "GrossVP": vp if h == 1 else 0,
                  "PAR": 4, "Hole": h} for h in range(1, 19)]
    rows += [{"TEGNum": 3, "Round": 2, "Pl": "A", "GrossVP": -9, "PAR": 4, "Hole": 1}]  # partial: ignored
    rows += [{"TEGNum": 20, "Round": 1, "Pl": "A", "GrossVP": -9, "PAR": 4, "Hole": 1}]  # this TEG: ignored
    hist = pd.DataFrame(rows)
    b = ls.what_it_takes(snap(), "B", "trophy", history=hist)
    assert b["need"]["outright"]["gross_vp"] == -11  # 0 + 36 - 47
    assert b["out_of_reach"] is True
    assert b["reality"]["best_round_vp"] == 2 and b["reality"]["best_round_gross"] == 74
    a = ls.what_it_takes(snap(), "A", "trophy", history=hist)  # needs +28 a round
    assert a["out_of_reach"] is False
    assert a["reality"]["rounds_recent"] == 3 and a["reality"]["rounds_recent_at_or_better"] == 2
    assert ls.what_it_takes(snap(), "A", "trophy")["reality"] is None


def test_no_holes_left():
    r = ls.what_it_takes(snap(finished=True), "A", "trophy")
    assert r["no_holes_left"] is True and r["need"] is None
    assert r["leading"] is True and r["tied"] is False
    b = ls.what_it_takes(snap(finished=True), "B", "trophy")
    assert b["leading"] is False


def test_errors():
    with pytest.raises(ValueError, match="competition"):
        ls.what_it_takes(snap(), "A", "wooden spoon")
    with pytest.raises(ValueError, match="Unknown player"):
        ls.what_it_takes(snap(), "Z", "trophy")
    with pytest.raises(ValueError, match="rivals"):
        ls.what_it_takes(snap(), "A", "trophy", rivals="vibes")


def test_all_and_json():
    res = ls.what_it_takes_all(snap(), "trophy")
    assert [r["player"] for r in res] == ["A", "B"]
    json.dumps(res)
    json.dumps(ls.what_it_takes(snap(finished=True), "A", "jacket"))


def test_already_enough_when_points_target_is_met():
    from teg_analysis.analysis import win_probability as wp
    card = pd.DataFrame({"Round": 2, "Hole": range(1, 19), "Par": 4, "SI": range(1, 19)})
    snap = wp.Snapshot(9, True, 1, 2, None, {"AA": 0, "BB": 0}, {"AA": 18, "BB": 18},
                       {"AA": 0, "BB": 36}, {"AA": 80, "BB": 10}, {"AA": 18, "BB": 18},
                       {"AA": "AA", "BB": "BB"}, {"AA": card, "BB": card}, 0)
    r = ls.what_it_takes(snap, "AA", "trophy")
    assert r["already_enough"] is True and r["reality"] is None


def _two(thru_a, thru_b, gross, net, rounds=2):
    card = pd.DataFrame({"Round": rounds, "Hole": range(1, 19), "Par": 4, "SI": range(1, 19)})
    rem = lambda n: card[card["Hole"] > n].reset_index(drop=True)  # noqa: E731
    return wp.Snapshot(9, True, 1, rounds, rounds, {"AA": thru_a, "BB": thru_b},
                       {"AA": 18 + thru_a, "BB": 18 + thru_b}, gross, net,
                       {"AA": 18, "BB": 18}, {"AA": "AA", "BB": "BB"},
                       {"AA": rem(thru_a), "BB": rem(thru_b)}, 0)


def test_finished_player_is_not_called_leader_while_rivals_play_on():
    # AA done on 70 points; BB thru 9 on 54 at 2 points a hole: projects to 72.
    snap = _two(18, 9, {"AA": 36, "BB": 27}, {"AA": 70, "BB": 54})
    r = ls.what_it_takes(snap, "AA", "trophy")
    assert r["no_holes_left"] and r["rivals_finished"] is False
    assert r["leading"] is False and r["tied"] is False


def test_trophy_rivals_projected_on_points_pace_not_gross():
    # BB's gross pace (+3 a hole, many blobs) would convert to negative points;
    # their actual points pace (1 a hole) is what counts.
    snap = _two(9, 9, {"AA": 27, "BB": 81}, {"AA": 54, "BB": 27 + 9})
    r = ls.what_it_takes(snap, "AA", "trophy")
    bb = next(p for p in r["projections"] if p["player"] == "BB")
    assert bb["projected"] == pytest.approx(36 + 9 * 36 / 27)


def test_expected_mode_uses_expected_points_for_trophy():
    snap = _two(9, 9, {"AA": 27, "BB": 27}, {"AA": 54, "BB": 54})
    r = ls.what_it_takes(snap, "AA", "trophy", rivals="expected", expected={"AA": 18, "BB": 18},
                         expected_net={"AA": 36, "BB": 30})
    bb = next(p for p in r["projections"] if p["player"] == "BB")
    assert bb["projected"] == pytest.approx(54 + 30 * 9 / 18)
