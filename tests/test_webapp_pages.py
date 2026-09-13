"""Webapp smoke tests (W10 / REVIEW_PLAN.md Chat 8).

Uses Starlette's TestClient against the real FastAPI app and the repo's real
data/ files (pattern: tests/test_admin_routes.py) -- no data is written.
Every assertion is a coarse "the page renders and doesn't show its
error-context marker" check, not a content assertion: these exist to catch a
column rename or refactor breaking a page outright, not to pin exact output.
"""

import pytest
from starlette.testclient import TestClient

from webapp.app import app
from webapp.nav import NAV_SECTIONS

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
    from webapp.routes.reports import _round_kind
    resp = client.get("/teg-reports", params={"teg": 14, "round": 2})
    assert _round_kind(14, 2) == "new"
    _assert_ok_no_error(resp)
    assert 'class="np-paper' in resp.text
    assert 'class="teg-report"' not in resp.text


def test_teg_reports_round_without_a_storyline_edition_falls_back_to_legacy_markdown(client):
    from webapp.routes.reports import _legacy_round_numbers, _round_kind
    if not _legacy_round_numbers(14):
        pytest.skip("no legacy round reports in this environment")
    assert _round_kind(14, 1) == "legacy"
    resp = client.get("/teg-reports", params={"teg": 14, "round": 1})
    _assert_ok_no_error(resp)
    assert 'class="teg-report"' in resp.text
    assert 'class="np-paper' not in resp.text


def test_teg_reports_round_pills_include_both_new_and_legacy_rounds(client):
    """TEG 14 has one round-storyline edition (R2) and legacy reports for the
    rest — the pill list must show every playable round, not just the new one."""
    from webapp.routes.reports import _legacy_round_numbers
    if not _legacy_round_numbers(14):
        pytest.skip("no legacy round reports in this environment")
    resp = client.get("/teg-reports", params={"teg": 14})
    _assert_ok_no_error(resp)
    for r in (1, 2, 3, 4):
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


def test_honours_page_renders(client):
    resp = client.get("/honours")
    _assert_ok_no_error(resp)


def test_honours_tab_renders(client):
    resp = client.get("/honours/tab/trophy")
    _assert_ok_no_error(resp)
