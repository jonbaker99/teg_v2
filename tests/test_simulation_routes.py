"""Route tests for /simulation (uses the repo's real data/ files, writes nothing)."""

import pytest
from starlette.testclient import TestClient

from webapp.app import app
from teg_analysis.analysis import simulation as sim


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_page_renders_controls_and_empty_state(client):
    r = client.get("/simulation")
    assert r.status_code == 200
    assert "TEG Predictatron 3100" in r.text
    assert "Run the simulation to see predictions." in r.text
    assert 'name="w_' in r.text and 'name="bands_preset"' in r.text
    assert 'name="method"' in r.text and 'name="min_holes"' in r.text
    assert 'name="po_' in r.text and 'name="pw_' in r.text
    assert 'name="shrinkage"' in r.text and 'name="n_sims"' in r.text
    assert "data-public-response-error" not in r.text


def test_distributions_partial(client):
    r = client.get("/simulation/distributions?method=bands&bands_preset=3+bands")
    assert r.status_code == 200
    assert "Par 3 / SI 1-6" in r.text
    assert "Eagle or better" in r.text


def test_distributions_bad_bands_reported(client):
    r = client.get("/simulation/distributions?method=bands&bands_custom=9,4")
    assert r.status_code == 200
    assert "strictly ascending" in r.text


def test_run_returns_results(client):
    r = client.get("/simulation/run?n_sims=500&seed=1")
    assert r.status_code == 200
    assert "500 simulations of TEG" in r.text
    assert 'data-measure="gross"' in r.text and 'data-measure="stableford"' in r.text
    assert "chart-container" in r.text


def test_run_all_zero_weights_is_an_error(client):
    r = client.get("/simulation/run?w_18=0&w_17=0&w_16=0&w_15=0")
    assert r.status_code == 200
    assert "weights are zero" in r.text
    assert "chart-container" not in r.text


def test_run_clamps_sims(client):
    r = client.get(f"/simulation/run?n_sims={sim.MAX_SIMS * 20}&seed=3")
    assert r.status_code == 200
    assert f"{sim.MAX_SIMS:,} simulations" in r.text
    assert "capped" in r.text


def test_distributions_follow_selected_player(client):
    tgt = sim.load_target_tournament()
    second = tgt.players[1]
    r = client.get(f"/simulation/distributions?dist_player={second}")
    assert r.status_code == 200
    assert f'value="{second}" selected' in r.text


def test_history_before_excludes_target_and_later():
    import pandas as pd
    from webapp.routes.simulation import _history_before
    h = pd.DataFrame({"TEGNum": [17, 18, 19, 20]})
    assert _history_before(h, 19)["TEGNum"].tolist() == [17, 18]


def test_overflowing_inputs_are_validation_errors(client):
    r = client.get("/simulation/run?seed=1e400&n_sims=100")
    assert r.status_code == 200
    assert "Seed must be" in r.text


def test_default_page_and_distributions_use_window(client):
    r = client.get("/simulation/distributions")
    assert r.status_code == 200
    assert "Par 4 / SI 1-2" in r.text and "Par 4 / SI 17-18" in r.text
    assert "<th>Window</th>" in r.text
    r = client.get("/simulation/run?n_sims=200&seed=1")
    assert "rolling SI window, min 20 holes" in r.text


def test_run_bands_method_still_works(client):
    r = client.get("/simulation/run?method=bands&n_sims=200&seed=1")
    assert r.status_code == 200
    assert "fixed SI bands" in r.text and "chart-container" in r.text


def test_min_holes_validated(client):
    r = client.get("/simulation/run?min_holes=0")
    assert "Min holes must be" in r.text
    r = client.get("/simulation/run?min_holes=40&n_sims=100&seed=1")
    assert "min 40 holes" in r.text


def _player_with_history():
    from webapp.routes.simulation import _history, _history_before
    tgt = sim.load_target_tournament()
    h = _history_before(_history(), tgt.teg_num)
    for pl in tgt.players:
        if h[h["Pl"] == pl]["TEGNum"].nunique() >= 2:
            tegs = sorted(h[h["Pl"] == pl]["TEGNum"].unique(), reverse=True)
            return pl, tgt.names[pl], [int(t) for t in tegs]
    pytest.skip("no suitable player")


def test_player_override_reflected_in_caption(client):
    pl, name, tegs = _player_with_history()
    q = f"po_{pl}=1&pw_{pl}_{tegs[0]}=0&pw_{pl}_{tegs[1]}=5"
    r = client.get(f"/simulation/run?n_sims=200&seed=1&{q}")
    assert r.status_code == 200
    assert f"custom weights for {name}" in r.text
    r = client.get(f"/simulation?{q}")
    assert f'name="po_{pl}" value="1"' in r.text and "checked" in r.text


def test_unticked_override_is_ignored(client):
    pl, name, tegs = _player_with_history()
    r = client.get(f"/simulation/run?n_sims=200&seed=1&pw_{pl}_{tegs[0]}=0")
    assert "custom weights" not in r.text


def test_all_zero_override_is_an_error(client):
    pl, name, tegs = _player_with_history()
    q = f"po_{pl}=1&" + "&".join(f"pw_{pl}_{t}=0" for t in tegs)
    r = client.get(f"/simulation/run?{q}")
    assert f"Custom weights for {name} are all zero" in r.text
    assert "chart-container" not in r.text


# --- target, players, rare events, random courses ----------------------------

def test_default_page_targets_default_teg(client):
    r = client.get("/simulation")
    assert "TEG Predictatron 3100" in r.text
    assert 'name="field_alpha"' in r.text and "Field blend (holes)" in r.text
    assert 'name="pl" value=' in r.text


def test_players_subset_and_zero_players(client):
    tgt = sim.load_target_tournament()
    two = tgt.players[:2]
    q = "&".join(f"pl={c}" for c in two)
    r = client.get(f"/simulation/run?pl_set=1&{q}&n_sims=200&seed=1")
    assert r.status_code == 200 and "chart-container" in r.text
    assert tgt.names[tgt.players[2]] not in r.text.replace("&nbsp;", " ").replace("<br>", " ")
    page = client.get(f"/simulation?pl_set=1&{q}")
    assert page.text.count('name="po_') == 2
    r = client.get("/simulation/run?pl_set=1&n_sims=100")
    assert "Pick at least one player" in r.text and "chart-container" not in r.text
    assert "Pick at least one player" in client.get("/simulation?pl_set=1").text


def test_field_alpha_validated(client):
    for bad in ("-1", "201", "abc", "nan"):
        r = client.get(f"/simulation/run?field_alpha={bad}&n_sims=100")
        assert "Field blend must be" in r.text, bad
    r = client.get("/simulation/run?field_alpha=0&n_sims=100&seed=1")
    assert "chart-container" in r.text


def test_summary_shows_eagle_and_blobs(client):
    r = client.get("/simulation/run?n_sims=300&seed=1")
    assert "Eagle %" in r.text and "Blobs" in r.text
    assert "xpected holes scoring 0 Stableford points" in r.text


@pytest.fixture
def random_target(monkeypatch):
    import dataclasses
    import pandas as pd
    from webapp.routes import simulation as route
    base = sim.load_target_tournament(20)
    tgt = dataclasses.replace(
        base, holes=pd.DataFrame(columns=["Round", "Hole", "Par", "SI"], dtype=int),
        random_rounds=4, n_rounds=4, handicaps_draft=True)
    assert tgt.course_pool
    monkeypatch.setattr(route, "_target", lambda teg, players=None: tgt)
    monkeypatch.setattr(route, "_target_options", lambda: (tgt.teg_num,))
    return tgt


def test_random_rounds_note_courses_and_no_markers(client, random_target):
    r = client.get("/simulation")
    assert "No scorecard yet for rounds 1, 2, 3, 4" in r.text
    assert f"from the {len(random_target.course_pool)} on file" in r.text
    assert "draft calculation" in r.text
    d = client.get("/simulation/distributions")
    assert "Par 4 / SI 1-2" in d.text and "sim-used" not in d.text
    r = client.get("/simulation/run?n_sims=300&seed=2")
    assert "Courses drawn" in r.text and "chart-container" in r.text
    assert "of TEG 20 (72 holes)" in r.text or "(72 holes)" in r.text


def test_setup_error_message_is_shown(client, monkeypatch):
    from webapp.routes import simulation as route
    def boom(*a, **k):
        raise ValueError("No handicap for TEG 19 player(s): ZZ")
    monkeypatch.setattr(route, "_target", boom)
    r = client.get("/simulation")
    assert r.status_code == 200
    assert "No handicap for TEG 19 player(s): ZZ" in r.text


def test_run_with_one_sim_renders(client):
    r = client.get("/simulation/run?n_sims=1&seed=1")
    assert r.status_code == 200
    assert "Couldn" not in r.text


def test_gross_shown_vs_par_and_sampling_collapsed(client):
    page = client.get("/simulation").text
    assert '<details class="sim-expander" id="sim-dists-box">' in page  # closed by default
    r = client.get("/simulation/run?n_sims=500&seed=1").text
    assert "Gross vs par" in r
    assert "Total gross strokes" not in r
    assert "<th>Gross</th>" not in r


def test_stableford_default_and_odds_table(client):
    r = client.get("/simulation/run?n_sims=500&seed=1").text
    assert 'data-sim-measure="stableford" aria-pressed="true"' in r
    assert "TEG Trophy" in r and "Green Jacket" in r and "Wooden Spoon" in r
    assert "/1" in r or "Evens" in r


def test_run_includes_handicap_expanders(client):
    r = client.get("/simulation/run?n_sims=500&seed=1")
    assert r.status_code == 200
    assert "Impact of handicap changes" in r.text
    assert "Handicaps that equalise chances" in r.text


# ---- Live tab

from teg_analysis.analysis import win_probability as wp  # noqa: E402
from webapp.routes import simulation as sim_routes  # noqa: E402


@pytest.fixture
def fresh_live_cache():
    def clear():
        sim_routes._LIVE_POINTS.clear()
        sim_routes._live_state.cache_clear()
    clear()
    yield
    clear()


def test_live_tab_shell_loads_partial(client):
    r = client.get("/simulation?tab=live")
    assert r.status_code == 200
    assert 'hx-get="/simulation/live?tab=live"' in r.text
    assert 'name="w_' not in r.text  # no prediction form on the Live tab
    assert "tab-underline--active" in r.text


def test_live_no_teg_in_progress(client, monkeypatch, fresh_live_cache):
    monkeypatch.setattr(wp, "in_progress_teg", lambda: None)
    r = client.get("/simulation/live")
    assert r.status_code == 200
    assert "No TEG in progress" in r.text
    assert "nothing to simulate live" in r.text


def test_live_in_progress_shows_latest_and_history(client, monkeypatch, fresh_live_cache):
    h = sim.load_history(teg_nums=[50])
    h = h[~((h["TEGNum"] == 18) & (h["Round"] > 2))]  # TEG 18 as if 2 rounds in
    monkeypatch.setattr(sim_routes, "_history", lambda: h)
    monkeypatch.setattr(wp, "in_progress_teg", lambda: 18)
    r = client.get("/simulation/live")
    assert r.status_code == 200
    assert "TEG 18 win chances after round 2" in r.text
    assert "How the chances moved, hole by hole" in r.text and "End R2" in r.text
    assert r.text.count("sim-left") >= 6  # header + 5 players


def test_live_replay_of_finished_teg(client, fresh_live_cache):
    r = client.get("/simulation/live?teg=18")
    assert r.status_code == 200
    assert "Replay of TEG 18" in r.text and "win chances at the finish" in r.text


def test_live_ignores_bad_teg(client, monkeypatch, fresh_live_cache):
    monkeypatch.setattr(wp, "in_progress_teg", lambda: None)
    r = client.get("/simulation/live?teg=abc")
    assert "No TEG in progress" in r.text


def test_live_page_queues_holes_in_order(client, fresh_live_cache):
    import json
    import re

    r = client.get("/simulation/live?teg=18")
    d = json.loads(re.search(r'id="sim-live-data">(.*?)</script>', r.text, re.S).group(1))
    assert d["total"] == 72 and set(d["points"]) == {"0-0", "1-18", "2-18", "3-18", "4-18"}
    steps = [q[2] for q in d["queue"]]
    assert steps == sorted(steps) and steps[:4] == [2, 2, 2, 2]  # hole 9s, then even, then odd
    assert [q[:2] for q in d["queue"][:4]] == [[4, 9], [3, 9], [2, 9], [1, 9]]
    assert len(d["queue"]) == 68 and d["scores"]["1-1"]


def test_live_point_endpoint(client, fresh_live_cache):
    r = client.get("/simulation/live/point?teg=18&round=2&hole=9&replay=1")
    assert r.status_code == 200
    body = r.json()
    assert sum(body["net"].values()) == pytest.approx(1.0) and set(body["gross"]) == set(body["net"])
    # cached points are embedded in the next page load, so they aren't queued again
    page = client.get("/simulation/live?teg=18")
    assert '"2-9"' in page.text


def test_live_point_rejects_bad_requests(client, monkeypatch, fresh_live_cache):
    monkeypatch.setattr(wp, "in_progress_teg", lambda: None)
    assert client.get("/simulation/live/point?teg=18&round=2&hole=9").status_code == 400
    assert client.get("/simulation/live/point?teg=18&round=9&hole=9&replay=1").status_code == 400
    assert client.get("/simulation/live/point?teg=99&round=1&hole=9&replay=1").status_code == 400
    assert client.get("/simulation/live/point?teg=18&round=0&hole=5&replay=1").status_code == 400
    assert client.get("/simulation/live/point?teg=18&round=1&hole=19&replay=1").status_code == 400
    assert not any(k[2] == 0 and k[3] != 0 for k in sim_routes._LIVE_POINTS)


def test_live_picker_offers_every_replayable_teg(client, monkeypatch, fresh_live_cache):
    monkeypatch.setattr(wp, "in_progress_teg", lambda: None)
    r = client.get("/simulation/live")
    assert 'id="sim-live-teg"' in r.text
    assert '<option value="18"' in r.text and '<option value="3"' in r.text
    assert '<option value="2"' not in r.text  # no earlier TEG to build form from
    r = client.get("/simulation/live?teg=2")
    assert "No TEG in progress" in r.text


def test_live_replay_has_hole_slider(client, fresh_live_cache):
    r = client.get("/simulation/live?teg=9")
    assert 'id="sim-scrub-range"' in r.text and 'max="72"' in r.text
    assert "Net vs par" not in r.text  # TEG 9 is a Stableford TEG
    r = client.get("/simulation/live?teg=6")
    assert "Net vs par" in r.text


def test_live_flags_debutant(client, fresh_live_cache):
    r = client.get("/simulation/live?teg=7")  # Alex BAKER's first TEG
    assert "First TEG for Alex BAKER" in r.text
    assert "First TEG for" not in client.get("/simulation/live?teg=8").text


# ---- Live chances mid-round

@pytest.fixture
def mid_round(monkeypatch, fresh_live_cache):
    """TEG 18 as if 2 rounds were done and round 3 had holes entered (uneven thru)."""
    import pandas as pd
    from teg_analysis.analysis import live_round
    h = sim.load_history(teg_nums=[50])
    h = h[~((h["TEGNum"] == 18) & (h["Round"] > 2))]
    monkeypatch.setattr(sim_routes, "_history", lambda: h)
    monkeypatch.setattr(wp, "in_progress_teg", lambda: 18)
    state, names = sim_routes._live_state(18, False)
    state.cards = {**state.cards, 3: state.cards[2]}  # round 3 has a scorecard
    rows = [dict(Round=3, Hole=hole, Pl=pl, GrossVP=1, NetVP=0, Stableford=2)
            for i, pl in enumerate(state.players) for hole in range(1, 4 + i)]
    monkeypatch.setattr(live_round, "staged_holes", lambda t: pd.DataFrame(rows))
    sim_routes._LIVE_NOW.clear()
    yield state
    sim_routes._LIVE_NOW.clear()


def test_live_prediction_counts_entered_holes(mid_round):
    p = sim_routes.live_prediction()
    assert p["teg_num"] == 18 and p["rounds_done"] == 2 and p["live_round"] == 3
    assert p["measure_label"] == "Stableford"
    rows = p["players"]
    assert [r["Thru"] for r in sorted(rows, key=lambda r: r["Pl"])] == [
        3 + mid_round.players.index(pl) for pl in sorted(mid_round.players)]
    chances = [r["TrophyChancePct"] for r in rows]
    assert chances == sorted(chances, reverse=True)
    assert abs(sum(chances) - 100) < 0.6 and abs(sum(r["SpoonChancePct"] for r in rows) - 100) < 0.6
    assert all(r["NetPosition"] and r["GrossPosition"] for r in rows)
    assert all(r["HolesPlayed"] >= r["Thru"] for r in rows)
    import json
    json.dumps(p)  # plain data


def test_live_prediction_caches_per_staged_signature(mid_round, monkeypatch):
    calls = []
    real = wp.win_probs_live
    monkeypatch.setattr(wp, "win_probs_live", lambda *a, **k: calls.append(1) or real(*a, **k))
    a = sim_routes.live_prediction()
    assert sim_routes.live_prediction() is a and len(calls) == 1


def test_live_prediction_without_a_teg_raises(monkeypatch):
    monkeypatch.setattr(wp, "in_progress_teg", lambda: None)
    with pytest.raises(ValueError, match="No TEG is in progress"):
        sim_routes.live_prediction()


def test_live_tab_shows_now_caption_and_table(client, mid_round):
    r = client.get("/simulation/live")
    assert r.status_code == 200
    assert "Now: round 3 in progress, scores entered so far (thru" in r.text
    assert "sim-now-table" in r.text and "<th>Thru</th>" in r.text
    assert "How the chances moved, hole by hole" in r.text


def test_what_it_takes_resolves_player_and_passes_expected(mid_round, monkeypatch):
    from teg_analysis.analysis import live_scenarios
    seen = {}

    def fake(snap, player, competition, rivals, expected, history, expected_net):
        seen.update(player=player, competition=competition, rivals=rivals, expected=expected,
                    expected_net=expected_net)
        return {"ok": True}
    monkeypatch.setattr(live_scenarios, "what_it_takes", fake)
    monkeypatch.setattr(live_scenarios, "what_it_takes_all", lambda *a: [{"all": True}])
    assert sim_routes.what_it_takes("Jon BAKER", "jacket", "expected") == {"ok": True}
    assert seen["player"] == "JB" and seen["competition"] == "jacket"
    assert set(seen["expected"]) == set(mid_round.players)
    assert set(seen["expected_net"]) == set(mid_round.players)
    assert sim_routes.what_it_takes(None) == [{"all": True}]
    with pytest.raises(ValueError):
        sim_routes.what_it_takes("Nobody")


# --- finalised win chances on /leaderboard and the home panel ---------------

from teg_analysis.core.players import get_player_dict
from webapp.routes import contents as contents_route
from webapp.routes import history as history_route
from webapp.routes import leaderboard as lb_route
from webapp.routes import simulation as sim_route
from webapp.deps import get_available_teg_numbers


@pytest.mark.parametrize("p,label", [
    (0.0, "0%"), (0.0004, "<1%"), (0.004, "<1%"), (0.005, "1%"), (0.42, "42%"),
    (0.9951, ">99%"), (0.9999, ">99%"), (1.0, "100%"),
])
def test_pct_label(p, label):
    assert sim_route._pct_label(p) == label


def test_finalised_win_chances_none_when_not_in_progress(monkeypatch):
    monkeypatch.setattr(sim_route.wp, "in_progress_teg", lambda: None)
    assert sim_route.finalised_win_chances(19) is None
    monkeypatch.setattr(sim_route.wp, "in_progress_teg", lambda: 20)
    assert sim_route.finalised_win_chances(19) is None


def test_finalised_win_chances_none_on_error(monkeypatch):
    monkeypatch.setattr(sim_route.wp, "in_progress_teg", lambda: 19)

    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(sim_route, "_live_state", boom)
    assert sim_route.finalised_win_chances(19) is None


def test_finalised_win_chances_formats_finalised_checkpoint(monkeypatch):
    class State:
        done = [1, 2]
    calls = []
    monkeypatch.setattr(sim_route.wp, "in_progress_teg", lambda: 19)
    monkeypatch.setattr(sim_route, "_live_state", lambda t, r: (State(), {"AB": "Alex BAKER", "JB": "Jon BAKER"}))
    monkeypatch.setattr(sim_route, "_live_point", lambda t, r, rnd, h: calls.append((rnd, h)) or
                        {"net": {"AB": 0.42, "JB": 0.001}, "gross": {"AB": 0.0, "JB": 0.999}})
    out = sim_route.finalised_win_chances(19)
    assert calls == [(2, 18)]
    assert out == {"after_round": 2, "trophy": {"Alex BAKER": "42%", "Jon BAKER": "<1%"},
                   "jacket": {"Alex BAKER": "0%", "Jon BAKER": ">99%"}}


def _fake_win(teg):
    names = list(get_player_dict().values())
    return {"after_round": 2, "trophy": {n: "42%" for n in names}, "jacket": {n: "17%" for n in names}}


@pytest.fixture
def lb_teg():
    return get_available_teg_numbers()[-1]


def test_leaderboard_shows_win_column_in_progress(client, monkeypatch, lb_teg):
    monkeypatch.setattr(history_route, "_teg_is_complete", lambda t: False)
    monkeypatch.setattr(lb_route, "finalised_win_chances", _fake_win)
    net = client.get(f"/leaderboard/table?teg={lb_teg}&tab=net").text
    assert "col-win" in net and "Win*" in net and "42%" in net
    assert "TEG Trophy after round 2" in net and "TEG Predictatron 3100" in net
    gross = client.get(f"/leaderboard/table?teg={lb_teg}&tab=gross").text
    assert "17%" in gross and "Green Jacket after round 2" in gross


def test_leaderboard_no_win_column_when_complete_or_unavailable(client, monkeypatch, lb_teg):
    monkeypatch.setattr(lb_route, "finalised_win_chances", _fake_win)
    monkeypatch.setattr(history_route, "_teg_is_complete", lambda t: True)
    assert "col-win" not in client.get(f"/leaderboard/table?teg={lb_teg}&tab=net").text
    monkeypatch.setattr(history_route, "_teg_is_complete", lambda t: False)
    monkeypatch.setattr(lb_route, "finalised_win_chances", lambda t: None)
    html = client.get(f"/leaderboard/table?teg={lb_teg}&tab=net").text
    assert "col-win" not in html and "Predictatron" not in html


def test_results_never_shows_win_column(client, monkeypatch, lb_teg):
    monkeypatch.setattr(history_route, "_teg_is_complete", lambda t: False)
    monkeypatch.setattr(lb_route, "finalised_win_chances", _fake_win)
    html = client.get(f"/results?teg={lb_teg}").text
    assert "col-win" not in html and "Win*" not in html


def test_home_panel_win_column(client, monkeypatch, lb_teg):
    monkeypatch.setattr(contents_route, "get_edition_summary", lambda *a: None)
    monkeypatch.setattr(contents_route, "finalised_win_chances", _fake_win)
    html = client.get("/contents/panel", params={"teg": lb_teg, "state": "in_progress", "rounds": 2}).text
    assert "col-win" in html and "Win*" in html and "42%" in html
    assert "TEG Trophy after round 2" in html
    monkeypatch.setattr(contents_route, "finalised_win_chances", lambda t: None)
    html = client.get("/contents/panel", params={"teg": lb_teg, "state": "in_progress", "rounds": 2}).text
    assert "col-win" not in html


def test_home_complete_panel_has_no_win_column(client, monkeypatch, lb_teg):
    monkeypatch.setattr(contents_route, "get_edition_summary", lambda *a: None)
    monkeypatch.setattr(contents_route, "finalised_win_chances", _fake_win)
    html = client.get("/contents/panel", params={"teg": lb_teg, "state": "complete"}).text
    assert "col-win" not in html
