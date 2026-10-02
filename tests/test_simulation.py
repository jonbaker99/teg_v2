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
    d = sim.build_distributions(h, ["AA", "BB"], {1: 1, 2: 1, 3: 1}, method="bands")
    assert len(d.cells) == 2 * 3 * 4
    sums = d.probs.groupby(["Pl", "Par", "Band"])["Prob"].sum()
    assert len(sums) == 24
    assert np.allclose(sums, 1.0)


def test_k0_equals_raw_cell():
    h = _hist([(1, "A", 4, 1, 0), (1, "A", 4, 2, 1), (1, "A", 4, 3, 1), (1, "A", 4, 10, 2)])
    d = sim.build_distributions(h, ["A"], {1: 1.0}, boundaries=(4, 9, 14), shrinkage=0, method="bands")
    c = d.probs[(d.probs.Par == 4) & (d.probs.Band == 0)].set_index("GrossVP")["Prob"]
    assert c[0] == pytest.approx(1 / 3) and c[1] == pytest.approx(2 / 3)


def test_large_k_approaches_par_level():
    h = _hist([(1, "A", 4, 1, 0)] * 5 + [(1, "A", 4, 10, 2)] * 5)
    d = sim.build_distributions(h, ["A"], {1: 1.0}, shrinkage=1e9, method="bands", field_alpha=0)
    c = d.probs[(d.probs.Par == 4) & (d.probs.Band == 0)].set_index("GrossVP")["Prob"]
    assert c[0] == pytest.approx(0.5, abs=1e-6) and c[2] == pytest.approx(0.5, abs=1e-6)


def test_zero_weight_teg_ignored():
    h = _hist([(1, "A", 4, 1, 0), (2, "A", 4, 1, 3)])
    d = sim.build_distributions(h, ["A"], {1: 0.0, 2: 10.0}, shrinkage=0, method="bands", field_alpha=0)
    c = d.probs[(d.probs.Par == 4) & (d.probs.Band == 0)]
    assert list(c.GrossVP) == [3]
    row = d.cells[(d.cells.Par == 4) & (d.cells.Band == 0)].iloc[0]
    assert row.N == 1 and row.Source == "cell"


def test_par_fallback_source():
    h = _hist([(1, "A", 4, 10, 1)])
    d = sim.build_distributions(h, ["A"], {1: 1.0}, method="bands")
    row = d.cells[(d.cells.Par == 4) & (d.cells.Band == 0)].iloc[0]
    assert row.Source == "par fallback" and row.N == 0 and row.MeanVP == pytest.approx(1.0)


def test_history_and_field_fallback():
    h = _hist([(1, "A", 4, 1, 0), (1, "B", 4, 1, 2), (2, "A", 3, 1, 1)])
    d = sim.build_distributions(h, ["A", "C"], {2: 1.0}, method="bands")
    a4 = d.cells[(d.cells.Pl == "A") & (d.cells.Par == 4)]
    assert (a4.Source == "history fallback").all()
    c4 = d.cells[(d.cells.Pl == "C") & (d.cells.Par == 4)]
    assert (c4.Source == "field fallback").all()
    assert len(d.warnings) >= 2
    assert np.allclose(d.probs.groupby(["Pl", "Par", "Band"])["Prob"].sum(), 1.0)


# ---- rolling window

def _cell(d, pl, par, band):
    return d.cells[(d.cells.Pl == pl) & (d.cells.Par == par) & (d.cells.Band == band)].iloc[0]


def test_window_default_and_structure():
    h = _synthetic()
    d = sim.build_distributions(h, ["AA", "BB"], {1: 1, 2: 1, 3: 1})
    assert d.boundaries == (2, 4, 6, 8, 10, 12, 14, 16)
    assert len(d.cells) == 2 * 3 * 9
    assert set(d.cells.Source) == {"window"}
    assert np.allclose(d.probs.groupby(["Pl", "Par", "Band"])["Prob"].sum(), 1.0)
    assert list(d.cells.BandLabel[:2]) == ["SI 1-2", "SI 3-4"]


def test_window_expands_until_min_holes():
    # 3 holes in each of pairs 0..8 (par 4): min_holes 7 from pair 4 -> radius 1 gives 9
    rows = [(1, "A", 4, 2 * q + 1, 0) for q in range(9) for _ in range(3)]
    d = sim.build_distributions(_hist(rows), ["A"], {1: 1.0}, min_holes=7)
    c = _cell(d, "A", 4, 4)
    assert c.N == 9 and c.Window == "SI 7-12"
    d1 = sim.build_distributions(_hist(rows), ["A"], {1: 1.0}, min_holes=3)
    assert _cell(d1, "A", 4, 4).Window == "SI 9-10"


def test_window_edge_expands_one_way():
    rows = [(1, "A", 4, 2 * q + 1, 0) for q in range(9) for _ in range(3)]
    d = sim.build_distributions(_hist(rows), ["A"], {1: 1.0}, min_holes=7)
    c = _cell(d, "A", 4, 0)
    assert c.Window == "SI 1-6" and c.N == 9
    c = _cell(d, "A", 4, 8)
    assert c.Window == "SI 13-18" and c.N == 9


def test_window_exact_pair_outweighs_neighbour():
    # pair 4 holes score 0, pair 5 holes score 2, equal counts; target pair 4 leans to 0
    rows = [(1, "A", 4, 9, 0)] * 5 + [(1, "A", 4, 11, 2)] * 5
    d = sim.build_distributions(_hist(rows), ["A"], {1: 1.0}, min_holes=10, field_alpha=0)
    pr = d.probs[(d.probs.Par == 4) & (d.probs.Band == 4)].set_index("GrossVP")["Prob"]
    assert pr[0] == pytest.approx(2 / 3) and pr[2] == pytest.approx(1 / 3)
    assert _cell(d, "A", 4, 4).EffN > 0


def test_window_min_holes_larger_than_data_uses_all_pairs():
    rows = [(1, "A", 4, 1, 0), (1, "A", 4, 18, 1)]
    d = sim.build_distributions(_hist(rows), ["A"], {1: 1.0}, min_holes=500)
    for b in range(9):
        c = _cell(d, "A", 4, b)
        assert c.Window == "SI 1-18" and c.N == 2


def test_window_fallbacks_still_work():
    h = _hist([(1, "A", 4, 1, 0), (1, "B", 4, 1, 2), (2, "A", 3, 1, 1)])
    d = sim.build_distributions(h, ["A", "C"], {2: 1.0})
    assert (d.cells[(d.cells.Pl == "A") & (d.cells.Par == 4)].Source == "history fallback").all()
    assert (d.cells[(d.cells.Pl == "C") & (d.cells.Par == 4)].Source == "field fallback").all()


def test_bands_cells_have_window_column():
    h = _synthetic()
    d = sim.build_distributions(h, ["AA"], {1: 1, 2: 1, 3: 1}, method="bands")
    assert list(d.cells.Window) == list(d.cells.BandLabel)


def test_unknown_method_rejected():
    with pytest.raises(ValueError):
        sim.build_distributions(_synthetic(), ["AA"], {1: 1}, method="x")


@pytest.mark.parametrize("method", ["window", "bands"])
def test_player_weights_override_only_that_player(method):
    rows = []
    for pl in ("A", "B"):
        rows += [(1, pl, 4, 5, 0)] * 5 + [(2, pl, 4, 5, 3)] * 5
    h = _hist(rows)
    g = {1: 1.0, 2: 1.0}
    base = sim.build_distributions(h, ["A", "B"], g, method=method, field_alpha=0)
    ov = sim.build_distributions(h, ["A", "B"], g, method=method, field_alpha=0,
                                player_weights={"A": {1: 0.0, 2: 1.0}})
    assert ov.cells[ov.cells.Pl == "A"].MeanVP.round(6).tolist() != base.cells[base.cells.Pl == "A"].MeanVP.round(6).tolist()
    pa = ov.probs[(ov.probs.Pl == "A") & (ov.probs.Par == 4)]
    assert set(pa.GrossVP) == {3}
    pd.testing.assert_frame_equal(ov.probs[ov.probs.Pl == "B"].reset_index(drop=True),
                                  base.probs[base.probs.Pl == "B"].reset_index(drop=True))


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


# ---- field blend

def _field_hist():
    # A always scores 0 on par 4; B scores 0..3 (so the field has a +3 / -2 that A never had)
    rows = [(1, "A", 4, 5, 0)] * 30
    rows += [(1, "B", 4, 5, v) for v in (0, 1, 2, 3, -2) for _ in range(6)]
    return _hist(rows)


@pytest.mark.parametrize("method", ["window", "bands"])
def test_field_blend_gives_unseen_outcomes_and_mean_preserved(method):
    h = _field_hist()
    off = sim.build_distributions(h, ["A"], {1: 1.0}, method=method, field_alpha=0)
    on = sim.build_distributions(h, ["A"], {1: 1.0}, method=method, field_alpha=5)
    b = 2 if method == "window" else 1  # SI 5 -> window pair 2 / band "SI 5-9"
    sel = lambda d: d.probs[(d.probs.Par == 4) & (d.probs.Band == b)].set_index("GrossVP")["Prob"]
    assert set(sel(off).index) == {0}
    assert sel(on).get(3, 0) > 0 and sel(on).get(-2, 0) > 0
    assert sel(on).sum() == pytest.approx(1.0)
    assert (sum(sel(on).index * sel(on).values)) == pytest.approx(0.0, abs=1e-9)  # A's mean kept


def test_field_alpha_zero_equals_old_behaviour():
    h = _synthetic()
    a = sim.build_distributions(h, ["AA", "BB"], {1: 1, 2: 1, 3: 1}, field_alpha=0)
    # support must not be extended and probabilities only come from own data
    assert a.probs.GrossVP.between(-1, 3).all()
    pd.testing.assert_frame_equal(
        a.probs, sim.build_distributions(h, ["AA", "BB"], {1: 1, 2: 1, 3: 1}, field_alpha=-5).probs)


def test_tilt_dist_matches_mean_and_keeps_zeros():
    sup = np.arange(-3, 9)
    p = np.zeros(len(sup)); p[3:7] = [0.3, 0.4, 0.2, 0.1]  # 0..3, mean 1.1
    p[1] = 0.0  # -2 never seen: must stay impossible
    out = sim._tilt_dist(p, sup, 0.6)
    assert out.sum() == pytest.approx(1.0)
    assert (out * sup).sum() == pytest.approx(0.6, abs=1e-6)
    assert out[1] == 0.0
    # tilting toward a better mean raises the low outcome less than a sideways shift would
    assert out[3] > p[3]


def test_tilt_keeps_eagles_rare():
    sup = np.arange(-3, 9)
    p = np.zeros(len(sup)); p[1:6] = [0.003, 0.04, 0.35, 0.4, 0.207]  # -2..2
    out = sim._tilt_dist(p, sup, (p * sup).sum() - 0.5)
    assert out[1] < 0.02  # a 0.5-stroke better player: eagle still under 2%


def test_blended_support_clamped():
    h = _hist([(1, "A", 4, 5, 0)] * 20 + [(1, "B", 4, 5, 9)] * 20)  # field has a +9
    d = sim.build_distributions(h, ["A"], {1: 1.0}, field_alpha=10)
    assert d.probs.GrossVP.max() <= sim.FIELD_VP_MAX
    assert d.probs.GrossVP.min() >= sim.FIELD_VP_MIN


def test_backtest_returns_finite_rows():
    rng = np.random.default_rng(1)
    rows = [(t, pl, int(rng.choice([3, 4, 5])), int(rng.integers(1, 19)), int(rng.integers(-1, 4)))
            for t in range(1, 7) for pl in ("A", "B", "C") for _ in range(36)]
    bt = sim.backtest_field_alpha(_hist(rows), alphas=(0, 2), min_holes=5)
    assert list(bt.columns) == ["Alpha", "MeanLogLik", "Holes", "ZeroProbHoles"]
    assert len(bt) == 2 and np.isfinite(bt.MeanLogLik).all()
    assert (bt.Holes == 3 * 36 * 3).all()  # TEGs 4, 5, 6 as targets
    assert bt.ZeroProbHoles[1] <= bt.ZeroProbHoles[0]


# ---- target selection / random courses

def test_default_target_teg(monkeypatch):
    data = {sim.IN_PROGRESS_TEGS_CSV: pd.DataFrame({"TEGNum": [20]}),
            sim.COMPLETED_TEGS_CSV: pd.DataFrame({"TEGNum": [3, 18, 19]})}
    monkeypatch.setattr(sim, "_read_csv", lambda p: data[p])
    assert sim.default_target_teg() == 20
    data[sim.IN_PROGRESS_TEGS_CSV] = pd.DataFrame({"TEGNum": []})
    assert sim.default_target_teg() == 20  # 19 + 1
    data[sim.COMPLETED_TEGS_CSV] = pd.DataFrame({"TEGNum": [3, 18]})
    monkeypatch.setattr(sim, "_read_round_pars",
                        lambda: pd.DataFrame({"TEGNum": [17, 19, 19, 21]}))
    assert sim.default_target_teg() == 19
    assert sim.available_target_tegs() == [21, 19]  # 17 is finished, not offered


def _pool(n=3):
    out = []
    for i in range(n):
        par = np.array([3, 4, 5, 4, 4, 4] * 3)
        par[0] = 3 + (i % 2)   # vary par layout but keep total 72
        par[1] = 4 - (i % 2)
        out.append((f"C{i}", par, np.arange(1, 19) if i % 2 == 0 else np.arange(18, 0, -1)))
    return out


def test_random_course_target_runs():
    d = sim.build_distributions(_synthetic(), ["AA", "BB"], {1: 1, 2: 1, 3: 1})
    t = _target(("AA", "BB"), hcs={"AA": 10, "BB": 20}, pars=(4,) * 18)
    t.random_rounds, t.course_pool = 3, _pool(4)
    assert all(int(p.sum()) == 72 for _, p, _ in t.course_pool)
    r1 = sim.run_simulation(d, t, 300, seed=5)
    r2 = sim.run_simulation(d, t, 300, seed=5)
    assert r1.par_total == 18 * 4 + 3 * 72
    assert np.array_equal(r1.gross, r2.gross) and np.array_equal(r1.courses_used, r2.courses_used)
    assert r1.courses_used.shape == (300, 3) and len(np.unique(r1.courses_used)) > 1
    assert len({tuple(row) for row in r1.courses_used.tolist()}) > 1
    assert r1.random_rounds == 3


def test_all_random_target_empty_holes():
    d = _det_dists(["AA"], {"AA": 0})
    t = sim.TargetTournament(99, pd.DataFrame(columns=["Round", "Hole", "Par", "SI"], dtype=int),
                             ["AA"], {"AA": 0}, {"AA": "A"}, random_rounds=4, course_pool=_pool(2))
    r = sim.run_simulation(d, t, 20, seed=2)
    assert r.par_total == 288 and (r.gross == 288).all()
    t.course_pool = []
    with pytest.raises(ValueError):
        sim.run_simulation(d, t, 5)


def test_load_target_random_and_draft_handicaps(monkeypatch):
    csvs = {sim.IN_PROGRESS_TEGS_CSV: pd.DataFrame({"TEGNum": [20]}),
            sim.COMPLETED_TEGS_CSV: pd.DataFrame({"TEGNum": [19]}),
            sim.ROUND_INFO_CSV: pd.DataFrame({"TEGNum": [20, 20, 20], "Round": [1, 2, 3]}),
            sim.COURSE_PARS_CSV: pd.concat([
                pd.DataFrame({"Course": n, "Hole": range(1, 19), "Par": p, "SI": s})
                for n, p, s in _pool(1)] + [
                pd.DataFrame({"Course": "Bad", "Hole": range(1, 10), "Par": 4, "SI": range(1, 10)})])}
    monkeypatch.setattr(sim, "_read_csv", lambda p: csvs[p])
    monkeypatch.setattr(sim, "_read_round_pars", lambda: pd.DataFrame(columns=["TEGNum"]))
    monkeypatch.setattr(sim, "_playing_codes", lambda t: {"AA", "BB"})
    monkeypatch.setattr(sim, "_player_dict", lambda: {"AA": "A A", "BB": "B B", "CC": "C C"})
    monkeypatch.setattr(sim, "_read_handicaps_raw",
                        lambda: pd.DataFrame({"TEG": ["TEG 20"], "AA": [12.0], "BB": [np.nan]}))
    monkeypatch.setattr(sim, "_draft_handicaps", lambda t: {"BB": 22, "CC": 30})
    t = sim.load_target_tournament()
    assert t.teg_num == 20 and t.n_rounds == 3 and t.random_rounds == 3 and t.holes.empty
    assert [c[0] for c in t.course_pool] == ["C0"]  # invalid 9-hole course dropped
    assert t.handicaps == {"AA": 12, "BB": 22} and t.handicaps_draft
    assert t.candidates == ["AA", "BB", "CC"]
    with pytest.raises(ValueError, match="DD"):
        sim.load_target_tournament(players=["AA", "DD"])
    monkeypatch.setattr(sim, "_draft_handicaps", lambda t: {})
    with pytest.raises(ValueError, match="BB"):
        sim.load_target_tournament()
    t = sim.load_target_tournament(players=["AA"])
    assert t.handicaps_draft is False


# ---- eagles / blobs / smoothing

def test_eagles_blobs_zero_for_par_player_and_counted_otherwise():
    d = _det_dists(["AA"], {"AA": 0})
    r = sim.run_simulation(d, _target(("AA",), hcs={"AA": 0}), 10, seed=1)
    assert r.eagles.dtype == np.int16 and r.eagles.shape == (10, 1)
    assert (r.eagles == 0).all() and (r.blobs == 0).all()
    s = sim.summary_table(r)
    assert s.EagleChance.iloc[0] == 0 and s.ExpBlobs.iloc[0] == 0
    d = _det_dists(["AA"], {"AA": -2})
    r = sim.run_simulation(d, _target(("AA",)), 5, seed=1)
    assert (r.eagles == 18).all()
    assert sim.summary_table(r).EagleChance.iloc[0] == 1.0
    d = _det_dists(["AA"], {"AA": 2})  # net par with HC 0 -> 0 points on every hole
    r = sim.run_simulation(d, _target(("AA",)), 5, seed=1)
    assert (r.blobs == 18).all() and (r.stableford == 0).all()


def test_smooth_total_distribution():
    rng = np.random.default_rng(0)
    n = 2000
    vals = np.round(rng.normal(80, 6, size=(n, 1))).astype(np.int32)
    r = sim.SimulationResult(["AA"], {"AA": "A"}, n, 1, 72, vals, vals,
                             np.ones((n, 1), dtype=np.int8), np.ones((n, 1), dtype=np.int8))
    sm = sim.total_distribution(r, "gross", smooth=True)
    assert sm.Fraction.sum() == pytest.approx(1.0)
    f = sm.Fraction.to_numpy()
    peak = int(f.argmax())
    assert (np.diff(f[:peak + 1]) >= -1e-12).all() and (np.diff(f[peak:]) <= 1e-12).all()
    assert abs(sm.Total.iloc[peak] - 80) <= 2
    assert sm.Total.min() < vals.min() and sm.Total.max() > vals.max()
    raw = sim.total_distribution(r, "gross")
    assert len(raw) < len(sm) and raw.Fraction.sum() == pytest.approx(1.0)


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


def test_smoothed_distribution_with_one_sim():
    h = _synthetic()
    d = sim.build_distributions(h, ["AA", "BB"], {1: 1, 2: 1, 3: 1})
    holes = pd.DataFrame({"Round": [1] * 18, "Hole": range(1, 19), "Par": [4] * 18, "SI": range(1, 19)})
    t = sim.TargetTournament(99, holes, ["AA", "BB"], {"AA": 10, "BB": 20}, {"AA": "A", "BB": "B"})
    r = sim.run_simulation(d, t, n_sims=1, seed=1)
    out = sim.total_distribution(r, "gross", smooth=True)
    assert out.groupby("Pl").Fraction.sum().round(6).eq(1).all()


def test_stale_in_progress_teg_ignored(monkeypatch):
    def fake(path):
        if path == sim.COMPLETED_TEGS_CSV:
            return pd.DataFrame({"TEGNum": [17, 18]})
        return pd.DataFrame({"TEGNum": [18]})
    monkeypatch.setattr(sim, "_read_csv", fake)
    assert sim.default_target_teg() == 19


@pytest.mark.parametrize("p,expected", [
    (0.5, "Evens"), (0.25, "3/1"), (0.2, "4/1"), (0.75, "1/3"), (0.1, "9/1"),
    (0.0, "1000/1+"), (1.0, "1/1000"), (0.0001, "1000/1"),
])
def test_fractional_odds(p, expected):
    assert sim.fractional_odds(p) == expected


def test_odds_table_prizes():
    h = _synthetic()
    d = sim.build_distributions(h, ["AA", "BB"], {1: 1, 2: 1, 3: 1})
    holes = pd.DataFrame({"Round": [1] * 18, "Hole": range(1, 19), "Par": [4] * 18, "SI": range(1, 19)})
    t = sim.TargetTournament(99, holes, ["AA", "BB"], {"AA": 10, "BB": 20}, {"AA": "A", "BB": "B"})
    r = sim.run_simulation(d, t, n_sims=2000, seed=3)
    o = sim.odds_table(r)
    assert o.Trophy.sum() == pytest.approx(1.0)
    assert o.Jacket.sum() == pytest.approx(1.0)
    assert o.Spoon.sum() == pytest.approx(1.0)
    # with two players, the Spoon is whoever did not win the Trophy
    assert (o.Trophy + o.Spoon).round(9).eq(1.0).all()
