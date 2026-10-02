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
    assert "simulator" in r.text
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
    assert f"TEG {sim.default_target_teg()} simulator" in r.text
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
    assert '<details class="sim-disclosure" id="sim-dists-box">' in page  # closed by default
    r = client.get("/simulation/run?n_sims=500&seed=1").text
    assert "Gross vs par" in r
    assert "Total gross strokes" not in r
    assert "<th>Gross</th>" not in r
