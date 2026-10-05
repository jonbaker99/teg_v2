"""Tests for teg_analysis.analysis.win_probability."""

import numpy as np
import pandas as pd
import pytest

from teg_analysis.analysis import win_probability as wp

_SI = np.arange(1, 19)


def _holes(teg, rnd, pl, vp, hc, n_holes=18):
    """Hole rows (``load_history`` format) on an all-par-4 course, SI 1..18, GrossVP ``vp`` each hole."""
    vp = np.broadcast_to(np.asarray(vp), (18,))[:n_holes]
    si = _SI[:n_holes]
    strokes = hc // 18 + ((hc % 18) >= si)
    return pd.DataFrame({
        "TEGNum": teg, "Round": rnd, "Hole": np.arange(1, n_holes + 1), "Pl": pl,
        "PAR": 4, "SI": si, "Sc": 4 + vp, "GrossVP": vp, "HC": float(hc),
        "NetVP": vp - strokes, "Stableford": np.maximum(0, 2 + strokes - vp)})


def _history(current, prior_vp=None, hc=None, rounds=(1, 2), tegs=(1, 2, 3)):
    """Prior TEGs where each player scores ``prior_vp[pl]`` on every hole, plus ``current`` rows."""
    prior_vp = prior_vp or {"AA": 1, "BB": 1}
    hc = hc or {pl: 18 for pl in prior_vp}
    rows = [_holes(t, r, pl, v, hc[pl]) for t in tegs for r in rounds for pl, v in prior_vp.items()]
    return pd.concat(rows + list(current), ignore_index=True)


def _state(history, teg=4):
    return wp.load_teg_state(teg, history, from_scores=True, field_alpha=0)


# ---- weighting

def test_prior_weights_full_history():
    assert wp.prior_teg_weights([18, 17, 16], [16, 17, 18]) == pytest.approx(
        {18: 0.5, 17: 0.35, 16: 0.15})


def test_prior_weights_renormalise_missed_teg():
    w = wp.prior_teg_weights([18, 17, 16], [18, 16])
    assert w == pytest.approx({18: 0.5 / 0.65, 16: 0.15 / 0.65})
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


def test_form_shift_grows_with_holes_played():
    assert wp.form_shift(5.0, 0) == (0.0, 0.0)
    shift, w = wp.form_shift(4.5, 9)  # +4.5 over 9 holes = +9 a round
    assert w == pytest.approx(wp.blend_weight(0.5))
    assert shift == pytest.approx(w * 9.0)
    ws = [wp.form_shift(1.0, h)[1] for h in (1, 9, 18, 27, 36, 72)]
    assert ws == sorted(ws) and ws[2] == pytest.approx(1 / 3) and ws[4] == pytest.approx(0.5)


def test_prior_uses_weighted_tegs_and_field_for_newcomer():
    hist = _history([], prior_vp={"AA": 1, "BB": 3})
    hist = pd.concat([hist, _holes(0, 1, "AA", 9, 18)], ignore_index=True)  # older than 3 TEGs back
    d = wp.prior_distributions(hist, 4, ["AA", "CC"], field_alpha=0)
    means = d.cells[d.cells["Par"] == 4].groupby("Pl")["MeanVP"].mean()
    assert means["AA"] == pytest.approx(1.0)  # TEG 0 is outside the 3 prior TEGs
    assert means["CC"] == pytest.approx(2.0)  # no history: field (AA and BB equally)
    assert (d.cells.loc[d.cells["Pl"] == "CC", "Source"] == "field fallback").all()


# ---- distribution adjustment

def _spread_cells():
    support = np.arange(-1, 4)
    p = np.array([[0.1, 0.3, 0.4, 0.2, 0.0], [0.0, 0.2, 0.5, 0.2, 0.1]])
    ref = [np.array([0] * 9 + [1] * 9)]
    return support, p, ref


def test_shift_cells_moves_mean_and_keeps_zeros():
    support, p, _ = _spread_cells()
    q = wp.shift_cells(p, support, 0.25)
    assert ((q * support).sum(axis=1) - (p * support).sum(axis=1)) == pytest.approx([0.25, 0.25])
    assert (q[p == 0] == 0).all()
    assert q.sum(axis=1) == pytest.approx([1, 1])


def test_win_shares_split_ties():
    totals = np.array([[30, 30, 40], [35, 31, 31]])
    assert wp.win_shares(totals, higher_better=False) == pytest.approx([0.25, 0.5, 0.25])
    assert wp.win_shares(totals, higher_better=True) == pytest.approx([0.5, 0, 0.5])


# ---- banked scores

def _current_teg():
    """TEG 4, 3 rounds: R1 AA -18 / BB +18, R2 AA complete but BB only 9 holes."""
    return [_holes(4, 1, "AA", -1, 18), _holes(4, 1, "BB", 1, 18),
            _holes(4, 2, "AA", 1, 18), _holes(4, 2, "BB", 1, 18, n_holes=9),
            _holes(4, 3, "AA", 1, 18).iloc[:0]]


def test_completed_rounds_requires_all_players_and_order():
    h = _history(_current_teg())
    assert wp.completed_rounds(h, 4, ["AA", "BB"]) == [1]
    assert wp.completed_rounds(h, 4, ["AA"]) == [1, 2]


def test_banked_rounds_and_tidy_output():
    st = _state(_history(_current_teg()))
    st.n_rounds = 3  # round 3 not started: simulated on round 1's card
    st.cards[3] = st.cards[1]
    df = wp.win_probs_by_round(st, n_sims=300, seed=1, form_var=0, day_var=0)
    assert list(df.columns) == ["teg", "after_round", "measure", "player", "win_prob",
                                "mean", "sd", "w", "banked"]
    assert sorted(df["after_round"].unique()) == [0, 1]
    assert list(df["measure"].unique()) == ["net", "gross"]
    g = df[df["measure"] == "gross"].set_index(["after_round", "player"])
    # same deterministic prior: a shared win before the TEG, AA's banked lead after R1
    assert g.loc[(0, "AA"), "win_prob"] == pytest.approx(0.5)
    assert g.loc[(1, "AA"), "banked"] == -18 and g.loc[(1, "BB"), "banked"] == 18
    assert g.loc[(1, "AA"), "win_prob"] == pytest.approx(1.0)
    assert g.loc[(1, "AA"), "w"] == pytest.approx(1 / 3)
    assert g.loc[(0, "AA"), "mean"] == pytest.approx(18.0)
    n = df[df["measure"] == "net"].set_index(["after_round", "player"])
    assert n.loc[(1, "AA"), "banked"] == -36 and n.loc[(1, "BB"), "banked"] == 0  # NetVP era


def test_completed_teg_final_row_is_actual_result():
    cur = [_holes(4, r, pl, v, 18) for r in (1, 2) for pl, v in (("AA", 0), ("BB", 1))]
    df = wp.win_probs_by_round(_state(_history(cur)), n_sims=200, seed=1)
    final = df[df["after_round"] == 2].set_index(["measure", "player"])["win_prob"]
    assert final[("gross", "AA")] == 1.0 and final[("net", "AA")] == 1.0
    assert df.loc[df["after_round"] == 2, "mean"].isna().all()


def test_stableford_from_simulated_gross_and_handicap():
    # Same gross; AA gets 18 more strokes, so AA wins net every time and gross is shared.
    cur = [_holes(4, 1, "AA", 1, 36), _holes(4, 1, "BB", 1, 18)]
    st = _state(_history(cur, hc={"AA": 36, "BB": 18}))
    st.n_rounds, st.cards[2] = 2, st.cards[1]
    df = wp.win_probs_by_round(st, n_sims=200, seed=1, form_var=0, day_var=0)
    r0 = df[df["after_round"] == 0].set_index(["measure", "player"])["win_prob"]
    assert r0[("net", "AA")] == pytest.approx(1.0)
    assert r0[("gross", "AA")] == pytest.approx(0.5)


def test_pre_stableford_era_net_is_net_vs_par():
    cur = [_holes(4, 1, "AA", 1, 36), _holes(4, 1, "BB", 1, 18)]
    st = _state(_history(cur, hc={"AA": 36, "BB": 18}))
    assert not st.stableford  # TEG 4 < STABLEFORD_ERA_TEG
    df = wp.win_probs_by_round(st, n_sims=200, seed=1)
    r1 = df[(df["after_round"] == 1) & (df["measure"] == "net")].set_index("player")
    assert r1.loc["AA", "banked"] == -18 and r1.loc["BB", "banked"] == 0
    assert r1.loc["AA", "win_prob"] == 1.0


def test_live_round_in_progress_keeps_full_scorecard(monkeypatch):
    from teg_analysis.analysis import simulation as sim

    cur = [_holes(4, 1, pl, 1, 18) for pl in ("AA", "BB")]
    cur += [_holes(4, 2, pl, 1, 18, n_holes=5) for pl in ("AA", "BB")]
    card = pd.DataFrame({"Round": np.repeat([1, 2], 18), "Hole": np.tile(range(1, 19), 2),
                         "Par": 4, "SI": np.tile(_SI, 2)})
    target = sim.TargetTournament(4, card, ["AA", "BB"], {"AA": 18, "BB": 18},
                                  {"AA": "AA", "BB": "BB"}, n_rounds=2)
    monkeypatch.setattr(sim, "load_target_tournament", lambda teg: target)
    st = wp.load_teg_state(4, _history(cur), field_alpha=0)
    assert st.done == [1] and len(st.cards[2]) == 18
    df = wp.win_probs_by_round(st, n_sims=100, seed=1)
    assert df.loc[df["after_round"] == 1, "mean"].to_numpy() == pytest.approx(18.0)


def test_seed_reproducible():
    st = _state(_history(_current_teg()))
    st.n_rounds, st.cards[3] = 3, st.cards[1]
    pd.testing.assert_frame_equal(wp.win_probs_by_round(st, n_sims=200, seed=3),
                                  wp.win_probs_by_round(st, n_sims=200, seed=3))


# ---- backtest

def _noisy_history(seed=0):
    rng = np.random.default_rng(seed)
    rows = [_holes(t, r, pl, rng.integers(-1, 3 + i, size=18), 18)
            for t in (1, 2, 3, 4) for r in (1, 2, 3) for i, pl in enumerate(("AA", "BB", "CC"))]
    return pd.concat(rows, ignore_index=True)


def test_backtest_shape_and_ratio_only_matters():
    b = wp.backtest_blend(ks=(1.0, 2.0), Ps=(2.0, 4.0), target_tegs=[4],
                          history=_noisy_history(), n_sims=200)
    assert set(b["after_round"]) == {1, 2}
    assert (b["tegs"] == 1).all() and b["brier"].notna().all()
    v = b.set_index(["k", "P", "measure", "after_round"])["brier"]
    assert v.loc[(1.0, 2.0)].to_numpy() == pytest.approx(v.loc[(2.0, 4.0)].to_numpy())


def test_backtest_rejects_incomplete_teg():
    with pytest.raises(ValueError, match="not complete"):
        wp.backtest_blend(ks=(1.0,), Ps=(2.0,), target_tegs=[4],
                          history=_history(_current_teg()), n_sims=100)


# ---- hole checkpoints

def _two_round_teg(vp=None, hc=None):
    vp = vp or {"AA": 0, "BB": 1}
    hc = hc or {"AA": 18, "BB": 18}
    cur = [_holes(4, r, pl, v, hc[pl]) for r in (1, 2) for pl, v in vp.items()]
    return _state(_history(cur, prior_vp=vp, hc=hc))


def test_checkpoints_cover_every_hole_of_completed_rounds():
    cps = wp.checkpoints(_two_round_teg())
    assert cps[0] == (0, 0) and len(cps) == 1 + 36
    assert cps[1] == (1, 1) and cps[-1] == (2, 18)


def test_mid_round_banks_played_holes_and_counts_fraction_of_round():
    df = wp.win_probs_at(_two_round_teg(), 1, 9, n_sims=200, seed=1)
    g = df[df["measure"] == "gross"].set_index("player")
    assert g.loc["AA", "banked"] == 0 and g.loc["BB", "banked"] == 9
    assert g.loc["AA", "w"] == pytest.approx(wp.blend_weight(0.5))
    assert g.loc["AA", "win_prob"] == 1.0


def test_hole_18_matches_round_checkpoint():
    st = _two_round_teg()
    a = wp.win_probs_at(st, 1, 18, n_sims=200, seed=2)
    b = wp.win_probs_by_round(st, n_sims=200, seed=2)
    b = b[b["after_round"] == 1]
    assert a["win_prob"].to_numpy() == pytest.approx(b["win_prob"].to_numpy())
    assert a["banked"].tolist() == b["banked"].tolist()


def test_mid_round_net_vs_par_subtracts_strokes_on_remaining_holes():
    # AA: +2 a hole off 36 (net level); BB: +1 a hole off 18 (net level): net always tied.
    st = _two_round_teg(vp={"AA": 2, "BB": 1}, hc={"AA": 36, "BB": 18})
    df = wp.win_probs_at(st, 1, 9, n_sims=200, seed=1, form_var=0, day_var=0)
    n = df[df["measure"] == "net"].set_index("player")
    assert n.loc["AA", "banked"] == 0 and n.loc["BB", "banked"] == 0
    assert n["win_prob"].to_numpy() == pytest.approx([0.5, 0.5])


def test_win_probs_at_rejects_unplayed_hole():
    with pytest.raises(ValueError):
        wp.win_probs_at(_two_round_teg(), 3, 1)


def test_round_offsets_spread_exactly_over_each_rounds_holes():
    from types import SimpleNamespace

    holes = pd.DataFrame({"Round": [2] * 6, "Hole": range(13, 19), "Par": 4, "SI": range(1, 7)})
    tgt = SimpleNamespace(holes=holes, random_rounds=1)
    out = SimpleNamespace(hole_vp=np.zeros((400, 2, 24), dtype=np.int8))
    rng = np.random.default_rng(0)
    hv = wp._add_round_offsets(out, tgt, form_sd=6.0, day_sd=0.0, rng=rng)
    part, full = hv[:, :, :6].sum(axis=2), hv[:, :, 6:].sum(axis=2)
    # same form offset in both: the partial round gets 6/18 of it (rounded), the full round all of it
    assert np.abs(part - np.rint(full * 6 / 18)).max() <= 1
    assert full.std() == pytest.approx(6.0, rel=0.15)
    small = np.abs(full) <= 18  # an offset of up to 18 strokes moves each hole by at most one
    assert (np.abs(hv[:, :, 6:])[small] <= 1).all()
    assert (out.hole_vp == hv).all()


def test_day_and_form_offsets_spread_outcomes():
    # Two identical deterministic players: without offsets every sim ties; with them, a real race.
    st = _two_round_teg(vp={"AA": 1, "BB": 1})
    st.n_rounds, st.cards[3] = 3, st.cards[1]
    off = wp.win_probs_at(st, 0, 0, n_sims=400, seed=1, form_var=0, day_var=0)
    on = wp.win_probs_at(st, 0, 0, n_sims=400, seed=1)
    g_off = off[off["measure"] == "gross"].set_index("player")
    g_on = on[on["measure"] == "gross"].set_index("player")
    assert g_off["win_prob"].tolist() == [0.5, 0.5] and g_off["sd"].tolist() == [0.0, 0.0]
    assert g_on["sd"].iloc[0] == pytest.approx(np.sqrt(wp.DEFAULT_FORM_VAR + wp.DEFAULT_DAY_VAR))
    assert 0.35 < g_on.loc["AA", "win_prob"] < 0.65


def test_newcomer_centred_on_handicap():
    # AA (off 18) shoots +15 a round, 3 under handicap. Debutant CC (off 36) should be
    # centred on 36 - 3 = +33 a round, not on the field's +15.
    spread = np.tile([-1, 0, 1, 2, 3], 4)[:18]
    rows = [_holes(t, r, "AA", spread, 18) for t in (1, 2, 3) for r in (1, 2)]
    rows += [_holes(4, 1, "AA", spread, 18), _holes(4, 1, "CC", spread, 36)]
    st = _state(pd.concat(rows, ignore_index=True))
    sup, arr = st.cells()
    cc = (arr["CC"][1] * sup).sum(axis=1)
    assert cc == pytest.approx(33 / 18, abs=0.01)
    assert any(w.startswith("CC: first TEG") for w in st.prior.warnings)
    assert wp.newcomers(st.prior) == ["CC"]


# ---- live (mid-round, players on different holes)

def _staged(rnd, pl, vp, hc, holes):
    """Staged rows (``live_round.staged_holes`` format) on the all-par-4 card."""
    h = _holes(0, rnd, pl, vp, hc)
    h = h[h["Hole"].isin(holes)]
    return h[["Round", "Hole", "Pl", "GrossVP", "NetVP", "Stableford"]]


def _live_teg(vp=None, hc=None, teg=4, tegs=(1, 2, 3)):
    """Round 1 complete, round 2 has a scorecard and nothing banked."""
    vp = vp or {"AA": 1, "BB": 1}
    hc = hc or {"AA": 18, "BB": 18}
    cur = [_holes(teg, 1, pl, v, hc[pl]) for pl, v in vp.items()]
    st = wp.load_teg_state(teg, _history(cur, prior_vp=vp, hc=hc, tegs=tegs),
                           from_scores=True, field_alpha=0)
    st.n_rounds, st.cards[2] = 2, st.cards[1]
    return st


def test_snapshot_players_on_different_holes():
    st = _live_teg()
    staged = pd.concat([_staged(2, "AA", 0, 18, range(1, 13)), _staged(2, "BB", 2, 18, [10, 11, 12])])
    snap = wp.snapshot(st, staged)
    assert snap.live_round == 2 and snap.thru == {"AA": 12, "BB": 3}
    assert snap.holes_played == {"AA": 30, "BB": 21}
    assert snap.gross == {"AA": 18, "BB": 24}
    assert len(snap.remaining["AA"]) == 6 and len(snap.remaining["BB"]) == 15
    assert set(snap.remaining["BB"]["Hole"]) == set(range(1, 19)) - {10, 11, 12}
    assert snap.random_rounds == 0


def test_snapshot_ignores_staged_holes_for_other_rounds():
    st = _live_teg()
    snap = wp.snapshot(st, _staged(1, "AA", 0, 18, range(1, 5)))
    assert snap.live_round is None and snap.gross == {"AA": 18, "BB": 18}
    assert len(snap.remaining["AA"]) == 18


def test_live_without_staged_matches_latest_checkpoint():
    st = _live_teg(vp={"AA": 0, "BB": 1})
    a = wp.win_probs_live(st, None, n_sims=200, seed=3)
    b = wp.win_probs_at(st, 1, 18, n_sims=200, seed=3)
    assert a["win_prob"].to_numpy() == pytest.approx(b["win_prob"].to_numpy())
    assert (a["thru"] == 18).all() and (a["round"] == 1).all()


def test_live_holes_are_banked_once_per_player():
    # Every hole is +1 with certainty: AA thru 12 and BB thru 3, both at +1, tie exactly.
    st = _live_teg()
    staged = pd.concat([_staged(2, "AA", 1, 18, range(1, 13)), _staged(2, "BB", 1, 18, [1, 2, 3])])
    df = wp.win_probs_live(st, staged, n_sims=300, seed=1, form_var=0, day_var=0)
    g = df[df["measure"] == "gross"].set_index("player")
    assert g.loc["AA", "banked"] == 30 and g.loc["BB", "banked"] == 21
    assert g["win_prob"].to_numpy() == pytest.approx([0.5, 0.5])
    assert g.loc["AA", "thru"] == 12 and g.loc["BB", "thru"] == 3
    assert g.loc["AA", "w"] > g.loc["BB", "w"]  # w grows with each player's own holes


def test_live_good_holes_decide_the_winner():
    st = _live_teg()
    staged = pd.concat([_staged(2, "AA", -1, 18, range(1, 10)), _staged(2, "BB", 1, 18, range(1, 10))])
    df = wp.win_probs_live(st, staged, n_sims=300, seed=1, form_var=0, day_var=0, spoon=True)
    p = df.set_index(["measure", "player"])["win_prob"]
    assert p[("gross", "AA")] == 1.0 and p[("net", "AA")] == 1.0
    assert p[("spoon", "BB")] == 1.0
    assert list(df["measure"].unique()) == ["net", "gross", "spoon"]


def test_live_stableford_counts_entered_holes_actual_points():
    # Stableford era. AA (hc 36) +2 a hole and BB (hc 18) +1 a hole: 2 points every hole each.
    st = _live_teg(vp={"AA": 2, "BB": 1}, hc={"AA": 36, "BB": 18}, teg=9, tegs=(6, 7, 8))
    assert st.stableford
    staged = pd.concat([_staged(2, "AA", 2, 36, range(1, 10)), _staged(2, "BB", 1, 18, range(5, 19))])
    df = wp.win_probs_live(st, staged, n_sims=300, seed=1, form_var=0, day_var=0)
    n = df[df["measure"] == "net"].set_index("player")
    assert n.loc["AA", "banked"] == 36 + 18 and n.loc["BB", "banked"] == 36 + 28
    assert n["win_prob"].to_numpy() == pytest.approx([0.5, 0.5])


def test_live_round_without_scorecard_is_an_error():
    st = _live_teg()
    del st.cards[2]
    with pytest.raises(ValueError, match="no scorecard"):
        wp.snapshot(st, _staged(2, "AA", 1, 18, [1]))
