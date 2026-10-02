"""Tests for teg_analysis.analysis.simulation."""

import os

import numpy as np
import pandas as pd
import pytest

from teg_analysis.analysis import simulation as sim


def _hist(rows):
    """rows: (TEGNum, Pl, PAR, SI, GrossVP)."""
    return pd.DataFrame(rows, columns=["TEGNum", "Pl", "PAR", "SI", "GrossVP"])


def _synthetic(seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for t in (1, 2, 3):
        for pl in ("AA", "BB"):
            for _ in range(60):
                par = int(rng.choice([3, 4, 5]))
                rows.append((t, pl, par, int(rng.integers(1, 19)), int(rng.integers(-1, 4))))
    return _hist(rows)


def _target(players=("AA",), hcs=None, pars=(4,) * 18, sis=None):
    sis = sis or list(range(1, 19))
    holes = pd.DataFrame({"Round": 1, "Hole": range(1, len(pars) + 1), "Par": pars, "SI": sis})
    return sim.TargetTournament(99, holes, list(players),
                                hcs or {p: 0 for p in players}, {p: p + " X" for p in players})


def _det_dists(players, vp_by_player, boundaries=(4, 9, 14)):
    """Deterministic distributions: player always scores a fixed GrossVP."""
    rows = []
    for pl in players:
        for par in (3, 4, 5):
            for b in range(len(boundaries) + 1):
                rows.append((pl, par, b, vp_by_player[pl], 1.0))
    probs = pd.DataFrame(rows, columns=["Pl", "Par", "Band", "GrossVP", "Prob"])
    return sim.ScoreDistributions(tuple(boundaries), probs, pd.DataFrame(), [])


# ---- bands

def test_parse_valid():
    assert sim.parse_si_boundaries("4,9,14") == (4, 9, 14)
    assert sim.parse_si_boundaries(" 6 , 12 ") == (6, 12)
    assert sim.parse_si_boundaries("") == ()
    assert sim.parse_si_boundaries([4, 9]) == (4, 9)


@pytest.mark.parametrize("bad", ["a,b", "9,4", "4,4", "0,5", "5,18", "4.5", "-1"])
def test_parse_invalid(bad):
    with pytest.raises(ValueError):
        sim.parse_si_boundaries(bad)


def test_labels():
    assert sim.si_band_labels((4, 9, 14)) == ["SI 1-4", "SI 5-9", "SI 10-14", "SI 15-18"]
    assert sim.si_band_labels(()) == ["All SI"]
    assert sim.si_band_labels((1, 8)) == ["SI 1", "SI 2-8", "SI 9-18"]


def test_assign_band_edges():
    b = sim.assign_si_band([1, 4, 5, 9, 10, 14, 15, 18], (4, 9, 14))
    assert list(b) == [0, 0, 1, 1, 2, 2, 3, 3]
    assert list(sim.assign_si_band([1, 18], ())) == [0, 0]


def test_default_weights():
    w = sim.default_teg_weights([5, 4, 3, 2, 1])
    assert w == {5: 50.0, 4: 35.0, 3: 15.0, 2: 0.0, 1: 0.0}
    assert sim.completed_teg_numbers(_hist([(1, "A", 4, 1, 0), (3, "A", 4, 1, 0)])) == [3, 1]


# ---- distributions

def test_probs_sum_and_all_cells():
    h = _synthetic()
    d = sim.build_distributions(h, ["AA", "BB"], {1: 1, 2: 1, 3: 1})
    assert len(d.cells) == 2 * 3 * 4
    sums = d.probs.groupby(["Pl", "Par", "Band"])["Prob"].sum()
    assert len(sums) == 24
    assert np.allclose(sums, 1.0)


def test_k0_equals_raw_cell():
    h = _hist([(1, "A", 4, 1, 0), (1, "A", 4, 2, 1), (1, "A", 4, 3, 1), (1, "A", 4, 10, 2)])
    d = sim.build_distributions(h, ["A"], {1: 1.0}, boundaries=(4, 9, 14), shrinkage=0)
    c = d.probs[(d.probs.Par == 4) & (d.probs.Band == 0)].set_index("GrossVP")["Prob"]
    assert c[0] == pytest.approx(1 / 3) and c[1] == pytest.approx(2 / 3)


def test_large_k_approaches_par_level():
    h = _hist([(1, "A", 4, 1, 0)] * 5 + [(1, "A", 4, 10, 2)] * 5)
    d = sim.build_distributions(h, ["A"], {1: 1.0}, shrinkage=1e9)
    c = d.probs[(d.probs.Par == 4) & (d.probs.Band == 0)].set_index("GrossVP")["Prob"]
    assert c[0] == pytest.approx(0.5, abs=1e-6) and c[2] == pytest.approx(0.5, abs=1e-6)


def test_zero_weight_teg_ignored():
    h = _hist([(1, "A", 4, 1, 0), (2, "A", 4, 1, 3)])
    d = sim.build_distributions(h, ["A"], {1: 0.0, 2: 10.0}, shrinkage=0)
    c = d.probs[(d.probs.Par == 4) & (d.probs.Band == 0)]
    assert list(c.GrossVP) == [3]
    row = d.cells[(d.cells.Par == 4) & (d.cells.Band == 0)].iloc[0]
    assert row.N == 1 and row.Source == "cell"


def test_par_fallback_source():
    h = _hist([(1, "A", 4, 10, 1)])
    d = sim.build_distributions(h, ["A"], {1: 1.0})
    row = d.cells[(d.cells.Par == 4) & (d.cells.Band == 0)].iloc[0]
    assert row.Source == "par fallback" and row.N == 0 and row.MeanVP == pytest.approx(1.0)


def test_history_and_field_fallback():
    h = _hist([(1, "A", 4, 1, 0), (1, "B", 4, 1, 2), (2, "A", 3, 1, 1)])
    d = sim.build_distributions(h, ["A", "C"], {2: 1.0})
    a4 = d.cells[(d.cells.Pl == "A") & (d.cells.Par == 4)]
    assert (a4.Source == "history fallback").all()
    c4 = d.cells[(d.cells.Pl == "C") & (d.cells.Par == 4)]
    assert (c4.Source == "field fallback").all()
    assert len(d.warnings) >= 2
    assert np.allclose(d.probs.groupby(["Pl", "Par", "Band"])["Prob"].sum(), 1.0)


# ---- simulation

def test_deterministic_with_seed_and_shapes():
    h = _synthetic()
    d = sim.build_distributions(h, ["AA", "BB"], {1: 1, 2: 1, 3: 1})
    t = _target(("AA", "BB"), pars=(3, 4, 5) * 6, hcs={"AA": 10, "BB": 20})
    r1 = sim.run_simulation(d, t, 200, seed=7)
    r2 = sim.run_simulation(d, t, 200, seed=7)
    assert r1.gross.shape == (200, 2) and r1.stableford_pos.shape == (200, 2)
    assert np.array_equal(r1.gross, r2.gross) and np.array_equal(r1.gross_pos, r2.gross_pos)
    assert r1.par_total == 72


def test_par_player_exact_totals():
    d = _det_dists(["AA"], {"AA": 0})
    t = _target(("AA",), hcs={"AA": 20}, pars=(4,) * 18)
    r = sim.run_simulation(d, t, 10, seed=1)
    assert (r.gross == 72).all()
    strokes = 20 // 18 + (20 % 18 >= np.arange(1, 19))
    assert (r.stableford == (2 + strokes).sum()).all()


def test_stableford_floor_zero():
    d = _det_dists(["AA"], {"AA": 5})
    r = sim.run_simulation(d, _target(("AA",)), 3, seed=1)
    assert (r.stableford == 0).all()


def test_position_grid_and_tie_split():
    d = _det_dists(["AA", "BB"], {"AA": 1, "BB": 1})
    t = _target(("AA", "BB"))
    r = sim.run_simulation(d, t, 4000, seed=3)
    g = sim.position_grid(r, "gross")
    assert np.allclose(g.sum(axis=1), 1.0)
    assert g.loc["AA X", 1] == pytest.approx(0.5, abs=0.05)
    assert sim.position_grid(r, "stableford").shape == (2, 2)
    s = sim.summary_table(r)
    assert abs(s["WinGross"].sum() - 1.0) < 1e-9
    td = sim.total_distribution(r, "gross")
    assert td.groupby("Pl")["Fraction"].sum().round(9).eq(1.0).all()
    with pytest.raises(ValueError):
        sim.position_grid(r, "bogus")


def test_clamp_and_bad_par():
    d = _det_dists(["AA"], {"AA": 0})
    t = _target(("AA",), pars=(4,) * 2, sis=[1, 2])
    assert sim.run_simulation(d, t, 0).n_sims == 1
    assert sim.run_simulation(d, t, 10**9).n_sims == sim.MAX_SIMS
    bad = _target(("AA",), pars=(6, 4), sis=[1, 2])
    with pytest.raises(ValueError):
        sim.run_simulation(d, bad, 5)


# ---- real data smoke

@pytest.mark.skipif(not os.path.exists("data/round_pars.csv"), reason="no round pars")
def test_real_data_smoke():
    target = sim.load_target_tournament()
    hist = sim.load_history([target.teg_num])
    w = sim.default_teg_weights(sim.completed_teg_numbers(hist))
    d = sim.build_distributions(hist, target.players, w)
    r = sim.run_simulation(d, target, 500, seed=1)
    assert r.gross.shape == (500, len(target.players))
    assert np.allclose(sim.position_grid(r, "gross").sum(axis=1), 1.0)
