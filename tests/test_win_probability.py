"""Tests for teg_analysis.analysis.win_probability."""

import numpy as np
import pandas as pd
import pytest

from teg_analysis.analysis import win_probability as wp


def _rounds(rows):
    """rows: (TEGNum, Round, Pl, GrossVP, HC). Holes spread the GrossVP evenly over SI 1..18."""
    out = []
    for t, r, pl, g, hc in rows:
        holes = wp.spread_to_total(np.zeros((1, 18), dtype=np.int64), np.array([g]))[0]
        pts = int(np.maximum(0, 2 + wp.hole_strokes(hc) - holes).sum())
        rec = {"TEGNum": t, "Round": r, "Pl": pl, "GrossVP": float(g), "NetVP": float(g - hc),
               "Stableford": float(pts), "HC": float(hc), "Holes": 18}
        rec.update({c: int(v) for c, v in zip(wp._SI_COLS, holes)})
        out.append(rec)
    return pd.DataFrame(out)


# ---- weighting

def test_prior_weights_full_history():
    assert wp.prior_teg_weights([18, 17, 16], [16, 17, 18]) == pytest.approx(
        {18: 0.5, 17: 0.3, 16: 0.2})


def test_prior_weights_renormalise_missed_teg():
    w = wp.prior_teg_weights([18, 17, 16], [18, 16])
    assert w == pytest.approx({18: 0.5 / 0.7, 16: 0.2 / 0.7})
    assert sum(w.values()) == pytest.approx(1.0)


def test_prior_weights_only_first_three_count():
    assert wp.prior_teg_weights([18, 17, 16, 15], [15]) == {}


def test_prior_weights_none_played():
    assert wp.prior_teg_weights([18, 17, 16], []) == {}


def test_prior_weights_custom():
    assert wp.prior_teg_weights([5, 4], [4, 5], (1, 3)) == pytest.approx({5: 0.25, 4: 0.75})


def test_blend_weight_formula():
    assert wp.blend_weight(0) == 0.0
    assert wp.blend_weight(1) == pytest.approx(3 / 9)
    assert wp.blend_weight(2) == pytest.approx(6 / 12)
    assert wp.blend_weight(3, k=2, P=4) == pytest.approx(6 / 10)
    with pytest.raises(ValueError):
        wp.blend_weight(1, P=0)


def test_blend_form_round_zero_is_prior():
    assert wp.blend_form(20.0, 5.0, []) == (20.0, 5.0, 0.0)


def test_blend_form_one_round_keeps_prior_sd():
    mean, sd, w = wp.blend_form(20.0, 5.0, [29.0])
    assert w == pytest.approx(1 / 3)
    assert mean == pytest.approx(23.0)
    assert sd == pytest.approx(5.0)


def test_blend_form_sd_uses_half_weight():
    mean, sd, w = wp.blend_form(20.0, 5.0, [10.0, 14.0])  # sample SD 2.83
    assert w == pytest.approx(0.5)
    assert mean == pytest.approx(16.0)
    assert sd == pytest.approx(0.25 * np.sqrt(8) + 0.75 * 5.0)


def test_prior_form_weighted_renormalised_and_field_fallback():
    rows = []
    for t, g in ((1, 10), (2, 20), (3, 30)):
        rows += [(t, r, "AA", g, 10) for r in (1, 2)]
    rows += [(3, r, "BB", 40 + 2 * r, 10) for r in (1, 2)]   # BB only played TEG 3
    rows += [(4, 1, "AA", 0, 10)]                              # current TEG ignored
    pf = wp.prior_form(_rounds(rows), 4, ["AA", "BB", "CC"]).set_index("Pl")
    assert pf.loc["AA", "PriorMean"] == pytest.approx(0.5 * 30 + 0.3 * 20 + 0.2 * 10)
    assert pf.loc["AA", "PriorTEGs"] == "3,2,1"
    assert pf.loc["BB", "PriorMean"] == pytest.approx(43.0)
    assert pf.loc["BB", "PriorSD"] == pytest.approx(np.sqrt(2))
    assert pf.loc["CC", "PriorSource"] == "field"
    assert pf.loc["AA", "PriorSource"] == "player"


# ---- simulation pieces

def test_hole_strokes():
    assert wp.hole_strokes(0).sum() == 0
    assert list(wp.hole_strokes(20)[:3]) == [2, 2, 1]
    assert wp.hole_strokes(20).sum() == 20
    assert wp.hole_strokes(-2).sum() == -2


def test_spread_to_total_hits_total():
    tmpl = np.array([[0, 1, 2] * 6, [3] * 18])
    out = wp.spread_to_total(tmpl, np.array([5, 40]))
    assert list(out.sum(axis=1)) == [5, 40]
    assert list(out[0, :6]) == [0, 1, 2, 0, 1, 1]  # -13: -1 each, +1 back on SI 1-5
    assert list(wp.spread_to_total(np.zeros((1, 18), int), np.array([2]))[0, :3]) == [1, 1, 0]


def test_win_shares_split_ties():
    totals = np.array([[30, 30, 40], [35, 31, 31]])
    assert wp.win_shares(totals, higher_better=False) == pytest.approx([0.25, 0.5, 0.25])
    assert wp.win_shares(totals, higher_better=True) == pytest.approx([0.5, 0, 0.5])


# ---- banked scores

def test_no_remaining_rounds_is_banked_result():
    p = wp.simulate_win_probs(np.array([20, 18]), np.array([70, 72]), np.zeros(2), np.ones(2),
                              [np.zeros((1, 18), int)] * 2, [10, 10], 0, True)
    assert p["gross"] == pytest.approx([0, 1])
    assert p["net"] == pytest.approx([0, 1])


def test_banked_lead_carries_through_simulation():
    tm = [np.zeros((1, 18), int)] * 2
    p = wp.simulate_win_probs(np.array([0, 30]), np.array([0, 30]), np.array([20.0, 20.0]),
                              np.array([0.0, 0.0]), tm, [0, 0], 2, False, 500,
                              np.random.default_rng(0))
    assert p["gross"] == pytest.approx([1, 0])
    assert p["net"] == pytest.approx([1, 0])  # pre-Stableford era: net vs par


def test_stableford_scored_from_simulated_gross():
    # Same gross, AA gets 18 more strokes: AA wins net every time, gross is shared.
    tm = [np.zeros((1, 18), int)] * 2
    p = wp.simulate_win_probs(np.zeros(2), np.zeros(2), np.array([18.0, 18.0]), np.zeros(2),
                              tm, [36, 18], 1, True, 200, np.random.default_rng(0))
    assert p["net"] == pytest.approx([1, 0])
    assert p["gross"] == pytest.approx([0.5, 0.5])


def _two_player_teg():
    rows = [(t, r, pl, g, 18) for t in (1, 2, 3) for r in (1, 2)
            for pl, g in (("AA", 20), ("BB", 22))]
    rows += [(4, 1, "AA", 10, 18), (4, 1, "BB", 30, 18), (4, 2, "AA", 12, 18)]  # R2 incomplete
    return _rounds(rows)


def test_win_probs_by_round_banks_completed_rounds_only():
    df = wp.win_probs_by_round(4, _two_player_teg(), n_sims=2000, seed=1,
                               players=["AA", "BB"], handicaps={"AA": 18, "BB": 18}, n_rounds=3)
    assert list(df.columns) == ["teg", "after_round", "measure", "player", "win_prob",
                                "mean", "sd", "w", "banked"]
    assert sorted(df["after_round"].unique()) == [0, 1]
    assert list(df["measure"].unique()) == ["net", "gross"]
    r1 = df[(df["after_round"] == 1) & (df["measure"] == "gross")].set_index("player")
    assert r1.loc["AA", "banked"] == 10 and r1.loc["BB", "banked"] == 30
    assert r1.loc["AA", "w"] == pytest.approx(1 / 3)
    assert r1.loc["AA", "mean"] == pytest.approx(20 * 2 / 3 + 10 / 3)
    assert r1.loc["AA", "win_prob"] > 0.95
    assert df.groupby(["after_round", "measure"])["win_prob"].sum().to_numpy() == pytest.approx(1)


def test_win_probs_seed_reproducible():
    kw = dict(n_sims=500, seed=3, players=["AA", "BB"], handicaps={"AA": 18, "BB": 18}, n_rounds=3)
    a = wp.win_probs_by_round(4, _two_player_teg(), **kw)
    b = wp.win_probs_by_round(4, _two_player_teg(), **kw)
    pd.testing.assert_frame_equal(a, b)


def test_completed_rounds_requires_all_players_and_order():
    r = _two_player_teg()
    assert wp.completed_rounds(r, 4, ["AA", "BB"]) == [1]
    assert wp.completed_rounds(r, 4, ["AA"]) == [1, 2]


# ---- backtest

def _complete_teg():
    rows = [(t, r, pl, g + t, 18) for t in (1, 2, 3, 4) for r in (1, 2, 3)
            for pl, g in (("AA", 20), ("BB", 22), ("CC", 25))]
    return _rounds(rows)


def test_backtest_shape_and_ratio_only_matters():
    b = wp.backtest_blend(ks=(1.0, 2.0), Ps=(2.0, 4.0), target_tegs=[4], rounds=_complete_teg(),
                          n_sims=300)
    assert set(b["after_round"]) == {1, 2}
    assert (b["tegs"] == 1).all() and b["brier"].notna().all()
    v = b.set_index(["k", "P", "measure", "after_round"])["brier"]
    assert v.loc[(1.0, 2.0)].to_numpy() == pytest.approx(v.loc[(2.0, 4.0)].to_numpy())


def test_backtest_rejects_incomplete_teg():
    with pytest.raises(ValueError, match="not complete"):
        wp.backtest_blend(ks=(1.0,), Ps=(2.0,), target_tegs=[4], rounds=_two_player_teg(),
                          n_sims=100)
