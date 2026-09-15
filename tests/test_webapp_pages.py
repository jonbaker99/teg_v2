"""Webapp smoke tests (W10 / REVIEW_PLAN.md Chat 8).

Uses Starlette's TestClient against the real FastAPI app and the repo's real
data/ files (pattern: tests/test_admin_routes.py) -- no data is written.
Every assertion is a coarse "the page renders and doesn't show its
error-context marker" check, not a content assertion: these exist to catch a
column rename or refactor breaking a page outright, not to pin exact output.
"""

import re

import pytest
import pandas as pd
from starlette.testclient import TestClient

from webapp.app import app
from webapp.nav import NAV_SECTIONS
from webapp.chart_utils import (
    create_round_graph,
    get_round_player_color_map,
    create_cumulative_graph,
    get_teg_player_color_map,
    get_teg_chart_readout,
    CROWDED_FIELD_THRESHOLD,
)

REAL_PLAYER_CODE = "DM"

# The shared idiom every context-builder error path renders: either
# `{"error": ...}` fed into a template's `{% if error %}Error: {{ error }}`
# block, or the `error-box` class used by a few chart/table partials.
ERROR_MARKERS = (">Error: ", "error-box")


def _assert_ok_no_error(resp):
    assert resp.status_code == 200
    for marker in ERROR_MARKERS:
        assert marker not in resp.text, f"found error marker {marker!r} in response"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Every page in the nav (mirrors webapp/nav.py NAV_SECTIONS)
# ---------------------------------------------------------------------------

_NAV_URLS = [
    page_url
    for section in NAV_SECTIONS
    for (_title, page_url, _active_key, _icon) in section["pages"]
]


@pytest.mark.parametrize("url", _NAV_URLS)
def test_nav_page_renders(client, url):
    resp = client.get(url)
    _assert_ok_no_error(resp)


def test_history_page_has_round_disclosure(client):
    # R3.1: the TEG cell becomes a disclosure toggle when round_info.csv has
    # matching round-by-round metadata for that TEG.
    resp = client.get("/history")
    _assert_ok_no_error(resp)
    assert "history-toggle" in resp.text
    assert "id='history-18-details'" in resp.text
    start = resp.text.index("id='history-18-details'")
    end = resp.text.index("</tr>", start)
    detail_html = resp.text[start:end]
    assert detail_html.count("<li>") == 4  # TEG 18 played four rounds
    assert "PGA Catalunya" in detail_html
    # Preserved verbatim, not disturbed by the disclosure markup change.
    assert "Green Jacket awarded in TEG 5" in resp.text


# ---------------------------------------------------------------------------
# TEG Reports (newspaper edition — teg_analysis.reporting.newspaper_edition).
# `?round=` (round_storyline.py, 2026-09-11) renders a round through the
# newspaper layout for a round with a round-storyline edition (TEG 14 R2, TEG
# 18 R3/R4 as of 2026-09-12 — see STATUS.md); every other playable round
# falls back to the legacy one-blob markdown render (`_round_kind` in
# webapp/routes/reports.py) rather than showing "no report".
# ---------------------------------------------------------------------------
def test_teg_reports_with_teg_param_renders(client):
    from teg_analysis.reporting.newspaper_edition import available_tegs
    tegs = available_tegs()
    if not tegs:
        pytest.skip("no TEGs with storyline-first artefacts in this environment")
    resp = client.get("/teg-reports", params={"teg": tegs[0]})
    _assert_ok_no_error(resp)


def test_teg_reports_unreported_round_falls_back_to_tournament(client):
    """A `round` with no report at all (new or legacy) must not error — it
    falls back to the tournament report rather than 500ing."""
    from teg_analysis.reporting.newspaper_edition import available_tegs
    tegs = available_tegs()
    if not tegs:
        pytest.skip("no TEGs with storyline-first artefacts in this environment")
    resp = client.get("/teg-reports", params={"teg": tegs[0], "round": 99})
    _assert_ok_no_error(resp)


def test_teg_reports_round_with_a_storyline_edition_uses_the_newspaper_layout(client):
    resp = client.get("/teg-reports", params={"teg": 14, "round": 2})
    _assert_ok_no_error(resp)
    assert 'class="np-paper' in resp.text
    assert 'class="teg-report"' not in resp.text


def test_teg_reports_round_pills_cover_every_round_storyline_round(client):
    """The pill list must show every round with a round-storyline edition."""
    from teg_analysis.reporting.newspaper_edition import available_rounds
    resp = client.get("/teg-reports", params={"teg": 14})
    _assert_ok_no_error(resp)
    for r in available_rounds(14):
        assert f">R{r}<" in resp.text


# ---------------------------------------------------------------------------
# Player profile
# ---------------------------------------------------------------------------

def test_player_index_renders(client):
    resp = client.get("/player")
    _assert_ok_no_error(resp)


def test_player_page_renders(client):
    resp = client.get(f"/player/{REAL_PLAYER_CODE}")
    _assert_ok_no_error(resp)


def test_player_grouped_overview_preserves_full_history_and_landmarks(client):
    from webapp.routes.player import _build_overview_context, _build_roster

    ctx = _build_overview_context("JB")
    assert [card["label"] for card in ctx["glance"]] == [
        "TEGs played", "Current handicap", "Avg gross / round", "Avg Stableford",
    ]
    roster = next(player for player in _build_roster() if player["code"] == "JB")
    assert ctx["glance"][1]["value"] == roster["handicap"]
    assert [card["label"] for card in ctx["landmarks"]] == ["Holes in One", "Eagles", "Birdies"]
    assert [item["label"] for item in ctx["highlights"]] == [
        "Best Round", "Best TEG", "Best Course", "Worst Course",
    ]
    assert ctx["teg_result_count"] == 17
    # Collapsing is progressive enhancement: the complete table remains in HTML.
    assert ctx["teg_table_html"].count("<tr>") == 18
    resp = client.get("/player/JB")
    _assert_ok_no_error(resp)
    assert 'class="pp-overview-grid"' in resp.text
    assert 'data-result-count="17"' in resp.text
    assert resp.text.index("Career Highlights") < resp.text.index("Career Trend") < resp.text.index("TEG Results")
    assert 'data-player-switch' in resp.text
    assert 'title-stars' not in resp.text
    assert 'player_pills' not in resp.text


def test_player_records_tab_keeps_every_held_record_and_worst(client):
    from markupsafe import escape
    from webapp.routes.player import _build_overview_context

    ctx = _build_overview_context("JB")
    resp = client.get("/player/JB/tab/records")
    _assert_ok_no_error(resp)
    assert "All-time records and worsts held" in resp.text
    for record in ctx["records_held"] + ctx["worsts_held"]:
        assert escape(record["label"]) in resp.text
        assert escape(str(record["value"])) in resp.text
        if record.get("detail"):
            assert escape(record["detail"]) in resp.text
    assert "Personal Bests" in resp.text
    assert "Streaks" in resp.text


def test_player_with_no_scores_has_honest_empty_state(client, monkeypatch):
    from webapp.routes import player

    known = player.get_player_dict()
    monkeypatch.setattr(player, "get_player_dict", lambda: {**known, "ZZ": "New PLAYER"})
    resp = client.get("/player/ZZ")
    _assert_ok_no_error(resp)
    assert "No TEG data" in resp.text
    assert "No silverware yet" in resp.text
    assert "No outright TEG records held" in resp.text
    assert 'data-expand-profile-results' not in resp.text
    resp = client.get("/player/ZZ/tab/records")
    _assert_ok_no_error(resp)
    assert "No outright TEG worsts held" in resp.text


def test_player_missing_handicap_is_unranked(client, monkeypatch):
    from webapp.routes import player

    monkeypatch.setattr(player, "_current_playing_handicaps", lambda: {})
    glance = player._build_overview_context("JB")["glance"]
    assert glance[1] == {"label": "Current handicap", "value": "–", "rank": "–"}


@pytest.mark.parametrize("tab", ["overview", "rounds", "scoring", "records"])
def test_player_tab_partials_render(client, tab):
    resp = client.get(f"/player/{REAL_PLAYER_CODE}/tab/{tab}")
    _assert_ok_no_error(resp)


# ---------------------------------------------------------------------------
# Latest round / latest TEG
# ---------------------------------------------------------------------------

def test_latest_round_page_renders(client):
    resp = client.get("/latest-round")
    _assert_ok_no_error(resp)


def test_latest_round_page_has_no_duplicate_oob_ids(client):
    # The tab partial normally re-renders these via hx-swap-oob after an
    # HTMX swap, replacing the existing element in place. On a full page
    # load the partial is {% include %}d directly into the same document,
    # so its OOB fragment must be suppressed there -- otherwise the page
    # ships two elements sharing each id (a real bug found by manual
    # browser testing: a second, unstyled round-pills bar rendered further
    # down the page).
    resp = client.get("/latest-round")
    _assert_ok_no_error(resp)
    # lr-chart-state has no full-page counterpart (only ever rendered by the
    # partial), so it must still ship here -- otherwise htmx has no element
    # to OOB-swap into on the very first tab switch and silently drops it,
    # permanently breaking metric/scale/player/rewind reconciliation.
    for element_id in ("lr-round-pills", "lr-round-select", "lr-context-header", "lr-chart-state"):
        assert resp.text.count(f'id="{element_id}"') == 1, f"duplicate/missing id={element_id!r} in /latest-round"

    # The standalone tab partial (what an HTMX swap actually receives) must
    # still emit exactly one OOB copy of each -- htmx replaces the existing
    # in-DOM element by id, so this response element is not a duplicate.
    tab_resp = client.get("/latest-round/tab", params={"teg": 18, "round": 1, "tab": "scoreboard"})
    _assert_ok_no_error(tab_resp)
    for element_id in ("lr-round-pills", "lr-round-select", "lr-context-header", "lr-chart-state"):
        assert tab_resp.text.count(f'id="{element_id}"') == 1, f"missing/duplicate id={element_id!r} in /latest-round/tab"


def test_latest_round_non_scoreboard_tab_echoes_chart_state(client):
    # A non-scoreboard tab (e.g. Records) has no chart of its own and never
    # computed active_metric/chart_scale/chart_player/chart_rewind -- without
    # echoing the incoming values back, #lr-chart-state falls back to
    # hardcoded template defaults and silently resets the user's real
    # scoreboard-tab selection the moment they switch tabs and back.
    resp = client.get("/latest-round/tab", params={
        "teg": 18, "round": 4, "tab": "records",
        "metric": "Stableford", "scale": "adjusted", "player": "DM", "rewind": "9",
    })
    _assert_ok_no_error(resp)
    assert 'data-metric="Stableford"' in resp.text
    assert 'data-scale="adjusted"' in resp.text
    assert 'data-player="DM"' in resp.text
    assert 'data-rewind="9"' in resp.text


def test_latest_round_mobile_scoreboard_contract(client):
    resp = client.get("/latest-round", params={"teg": "invalid", "round": "invalid", "metric": "Stableford", "scale": "adjusted", "player": "invalid", "rewind": "9"})
    _assert_ok_no_error(resp)
    # Main row: # / Player / Personal rank / All-time rank / Total.
    assert all(f">{heading}<" in resp.text for heading in ("#", "Player", "Personal rank", "All-time rank", "Total"))
    # Section heading names the metric (moved out of the table into the
    # "Round leaderboard" / metric-name section-title-row).
    assert "Round leaderboard" in resp.text and "Stableford" in resp.text
    # Expandable detail row: Out/In split + per-hole score mix, collapsed by default.
    assert "data-lr-rank-toggle" in resp.text
    assert 'aria-expanded="false"' in resp.text
    assert "rank-detail-row" in resp.text and "hidden" in resp.text
    assert ">Out<" in resp.text and ">In<" in resp.text
    assert "Score mix" in resp.text
    assert "data-lr-page" in resp.text
    assert "data-lr-focus=" in resp.text
    assert "Through hole" in resp.text
    assert 'data-lr-scale="adjusted"' in resp.text
    assert 'data-lr-step="-1"' in resp.text and 'data-lr-step="1"' in resp.text
    assert 'data-lr-history="push"' not in resp.text.split('data-lr-query="metric"', 1)[1].split('</div>', 1)[0]


def test_latest_round_invalid_state_defaults_without_failure(client):
    resp = client.get("/latest-round/tab", params={"teg": "bad", "round": "bad", "tab": "bad", "metric": "bad", "scale": "adjusted", "player": "bad", "rewind": "bad"})
    _assert_ok_no_error(resp)
    # metric="bad" falls back to "Sc" -> friendly "Score".
    assert all(f">{heading}<" in resp.text for heading in ("#", "Player", "Personal rank", "All-time rank", "Total"))
    assert "Round leaderboard" in resp.text and "Score" in resp.text
    assert ">Out<" in resp.text and ">In<" in resp.text
    assert 'aria-pressed="true"' not in resp.text


def test_round_chart_rewind_keeps_endpoint_and_faint_future():
    rows = [{"TEG": "TEG 1", "Round": 1, "Hole": hole, "Pl": "AB", "Sc Cum Round": hole, "GrossVP Cum Round": hole, "Stableford Cum Round": hole * 2} for hole in range(1, 19)]
    fig = create_round_graph(pd.DataFrame(rows), "TEG 1", 1, "Sc Cum Round", "Round", rewind=9)
    assert list(fig.data[0].x)[-1] == 9
    assert list(fig.data[1].x)[0] == 9
    assert fig.data[1].opacity == 0.2
    # Both segments share player identity (name) so JS focus-by-name can
    # target them together, but the future segment is tagged distinctly so
    # focusing this player doesn't raise its un-played faint continuation to
    # full opacity (which would defeat the rewind fade).
    assert fig.data[0].name == fig.data[1].name == "AB"
    assert fig.data[0].meta is None
    assert fig.data[1].meta == "future"


def test_round_chart_colours_agree_with_readout_map_even_when_unsorted():
    # Rows deliberately NOT sorted by Hole and NOT grouped by player, so a
    # colour map derived without first sorting by Hole (like the chart itself
    # does) could assign codes in a different order than the chart -- this
    # would make webapp/routes/latest.py's readout swatches (built from
    # get_round_player_color_map) disagree with the actual chart line
    # colours for some players.
    rows = []
    for hole in range(1, 19):
        for player in ("GW", "AB", "JB"):
            rows.append({"TEG": "TEG 1", "Round": 1, "Hole": hole, "Pl": player,
                         "Sc Cum Round": hole, "GrossVP Cum Round": hole, "Stableford Cum Round": hole * 2})
    df = pd.DataFrame(rows).sample(frac=1, random_state=7).reset_index(drop=True)

    color_map = get_round_player_color_map(df, "TEG 1", 1)
    fig = create_round_graph(df, "TEG 1", 1, "Sc Cum Round", "Round")

    chart_colors = {trace.name: trace.line.color for trace in fig.data}
    assert chart_colors == color_map


def test_latest_round_chart_build_failure_shows_fallback_not_silence(client, monkeypatch):
    # Previously a bare `except Exception: pass` left figure_json None and
    # the whole chart+readout+scale+rewind block silently vanished with no
    # indication anything failed, while the page still returned 200 -- an
    # empty region a user could easily miss, not the scoreboard table's own
    # equivalent failure (which does render a "No data." fallback).
    import webapp.routes.latest as latest_mod

    def boom(*args, **kwargs):
        raise RuntimeError("forced chart failure")

    monkeypatch.setattr(latest_mod, "create_round_graph", boom)
    resp = client.get("/latest-round/tab", params={"teg": 18, "round": 4, "tab": "scoreboard"})
    _assert_ok_no_error(resp)
    assert "chart-title" in resp.text
    assert "Chart unavailable for this round." in resp.text
    assert "chart-container" not in resp.text
    # The OOB chart-state echo must still ship even when the chart itself
    # failed to build, or the client-side dataset/URL sync goes stale.
    assert 'id="lr-chart-state"' in resp.text


@pytest.mark.parametrize("tab", ["scoreboard", "scoring", "eclectic", "streaks"])
def test_latest_round_tab_partials_render(client, tab):
    resp = client.get("/latest-round/tab", params={"teg": 18, "round": 1, "tab": tab})
    _assert_ok_no_error(resp)


def test_latest_teg_page_renders(client):
    resp = client.get("/latest-teg")
    _assert_ok_no_error(resp)


@pytest.mark.parametrize("tab", ["aggregate", "scoring", "eclectic", "streaks", "records", "report"])
def test_latest_teg_tab_partials_render(client, tab):
    resp = client.get("/latest-teg/tab", params={"teg": 18, "tab": tab})
    _assert_ok_no_error(resp)


# ---------------------------------------------------------------------------
# Results + honours
# ---------------------------------------------------------------------------

def test_results_page_renders(client):
    resp = client.get("/results")
    _assert_ok_no_error(resp)


def test_results_table_tab_renders(client):
    resp = client.get("/results/table", params={"teg": 18, "tab": "net"})
    _assert_ok_no_error(resp)


def test_standings_page_has_mobile_table_hook(client):
    # R3.2: results.html and leaderboard.html share the .standings-page hook
    # (mobile.css) that reveals the real table on phones (instead of only the
    # M2.7 card reflow) and opts it out of the generic sticky-column scroll.
    resp = client.get("/results", params={"teg": 18})
    _assert_ok_no_error(resp)
    assert "standings-page" in resp.text
    assert "table-wrapper--no-pin" in resp.text
    assert "leaderboard-table" in resp.text


# ---------------------------------------------------------------------------
# Tournament race chart (R4.1): create_cumulative_graph keeps exactly ONE
# figure-building contract -- the pre-R4.1 desktop/iPad one (native legend,
# full "Player: value" labels, wide margin) -- unconditionally, regardless of
# field size or caller (/results, /leaderboard, and the unlinked /charts all
# get this same figure). The phone-only compact contract (no legend, short
# labels, crowded-field label suppression) is applied client-side to that
# same figure (base.html::applyMobileChartTreatment) and is not something
# Python builds or this test suite can exercise directly.
# ---------------------------------------------------------------------------

def _race_rows(players, rounds=2):
    """Synthetic TEG-wide cumulative rows: one row per (player, round, hole),
    'Val Cum TEG' rising by 1 each hole so each player's final value is
    predictable (rounds * 18)."""
    rows = []
    for rnd in range(1, rounds + 1):
        for hole in range(1, 19):
            for i, player in enumerate(players):
                cum = (rnd - 1) * 18 + hole
                rows.append({"TEG": "TEG 1", "Round": rnd, "Hole": hole, "Pl": player,
                             "Val Cum TEG": cum + i})  # offset so players don't tie
    return pd.DataFrame(rows)


def test_race_chart_keeps_native_legend_and_full_labels_regardless_of_field_size():
    # Desktop/iPad contract must not depend on player count -- no server-side
    # crowded-field branching, unlike the phone-only client treatment.
    small = _race_rows(["AB", "DM", "GW"])
    crowded = _race_rows([f"P{i}" for i in range(CROWDED_FIELD_THRESHOLD + 1)])

    fig_small = create_cumulative_graph(small, "TEG 1", "Val Cum TEG", title="")
    fig_crowded = create_cumulative_graph(crowded, "TEG 1", "Val Cum TEG", title="")

    for fig, n_players in ((fig_small, 3), (fig_crowded, CROWDED_FIELD_THRESHOLD + 1)):
        assert fig.layout.showlegend is not False  # native legend on (default True)
        assert fig.layout.margin.r == 100
        player_labels = [a for a in fig.layout.annotations if a.text and not a.text.startswith("R")]
        assert len(player_labels) == n_players
        # Full "Player: value" form (colon), not the compact phone label.
        assert all(":" in a.text for a in player_labels)


def test_race_chart_readout_colours_agree_with_chart_even_when_unsorted():
    # Same shape as test_round_chart_colours_agree_with_readout_map_even_when_unsorted:
    # rows deliberately unsorted so a readout colour map computed without
    # first sorting by Round/Hole could disagree with the chart's own colours.
    rows = []
    for rnd in range(1, 3):
        for hole in range(1, 19):
            for player in ("GW", "AB", "JB"):
                rows.append({"TEG": "TEG 1", "Round": rnd, "Hole": hole, "Pl": player,
                             "Val Cum TEG": (rnd - 1) * 18 + hole})
    df = pd.DataFrame(rows).sample(frac=1, random_state=7).reset_index(drop=True)

    color_map = get_teg_player_color_map(df, "TEG 1")
    fig = create_cumulative_graph(df, "TEG 1", "Val Cum TEG", title="")
    chart_colors = {trace.name: trace.line.color for trace in fig.data}
    assert chart_colors == color_map

    readout = get_teg_chart_readout(df, "TEG 1", "Val Cum TEG")
    assert {item["code"]: item["color"] for item in readout} == color_map


@pytest.mark.parametrize("path,tab_param", [
    ("/results/table", "tab"),
    ("/leaderboard/table", "tab"),
])
def test_race_chart_readout_matches_rendered_traces(client, path, tab_param):
    # HTMX-rendered state: the readout's player codes must exactly match the
    # figure's trace names -- not just a subset -- so every button has a
    # trace to focus and every trace has a button, in both directions.
    resp = client.get(path, params={"teg": 18, tab_param: "net", "chart_variant": "adjusted"})
    _assert_ok_no_error(resp)
    assert "chart-block" in resp.text
    # data-figure is HTML-escaped (rendered inside an attribute), so quotes
    # come through as &#34; rather than literal ".
    figure_codes = set(re.findall(r'&#34;name&#34;:&#34;(\w{2,3})&#34;', resp.text))
    readout_codes = set(re.findall(r'data-chart-focus="(\w+)"', resp.text))
    assert readout_codes
    assert readout_codes == figure_codes


def test_race_chart_readout_markup_present_regardless_of_viewport(client):
    # Desktop/iPad hides the readout via CSS (.chart-block .lr-readout is
    # display:none by default, re-shown only inside the <=640px media
    # query -- see webapp/static/mobile.css), not a server-side branch. The
    # server has no viewport to branch on, so the readout markup -- and the
    # threshold the client-side crowded-field check needs -- must always be
    # in the response.
    resp = client.get("/results/table", params={"teg": 18, "tab": "net", "chart_variant": "adjusted"})
    _assert_ok_no_error(resp)
    assert "lr-readout" in resp.text
    assert re.search(r'data-crowded-threshold="\d+"', resp.text)


def test_honours_page_renders(client):
    resp = client.get("/honours")
    _assert_ok_no_error(resp)


def test_honours_tab_renders(client):
    resp = client.get("/honours/tab/trophy")
    _assert_ok_no_error(resp)
