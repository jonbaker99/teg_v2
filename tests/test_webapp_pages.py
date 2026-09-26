"""Webapp smoke tests (W10 / REVIEW_PLAN.md Chat 8).

Uses Starlette's TestClient against the real FastAPI app and the repo's real
data/ files (pattern: tests/test_admin_routes.py) -- no data is written.
Every assertion is a coarse "the page renders and doesn't show its
error-context marker" check, not a content assertion: these exist to catch a
column rename or refactor breaking a page outright, not to pin exact output.
"""

import html
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
ERROR_MARKERS = (">Error: ", "error-box", "data-public-response-error")


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


def test_phone_explore_navigation_is_complete_and_current(client):
    resp = client.get("/records")
    _assert_ok_no_error(resp)

    tabbar = re.search(r'<nav class="mobile-tabbar".*?</nav>', resp.text, re.DOTALL)
    assert tabbar
    assert len(re.findall(r'<(?:a|button)[^>]*class="mtab(?: |")', tabbar.group(0))) == 5
    for label, url in (
        ("Latest", "/leaderboard"),
        ("History", "/history"),
        ("Records", "/records"),
        ("Cards", "/scorecard"),
    ):
        assert f'href="{url}"' in tabbar.group(0)
        assert f'>{label}</span>' in tabbar.group(0)
    assert '>Explore</span>' in tabbar.group(0)
    assert '>Scoring</span>' not in tabbar.group(0)
    assert 'href="/records"' in tabbar.group(0)
    assert 'aria-current="page"' in tabbar.group(0)

    honours = client.get("/honours")
    _assert_ok_no_error(honours)
    honours_tabbar = re.search(r'<nav class="mobile-tabbar".*?</nav>', honours.text, re.DOTALL)
    assert honours_tabbar
    assert re.search(r'href="/history"\s+class="mtab mtab--active"', honours_tabbar.group(0))
    assert 'aria-current="page"' not in honours_tabbar.group(0)

    sheet = re.search(
        r'<dialog id="mobile-explore-sheet".*?</dialog>', resp.text, re.DOTALL,
    )
    assert sheet
    sheet_html = sheet.group(0)
    for section in NAV_SECTIONS:
        assert html.escape(section["label"]) in sheet_html
        for _title, url, _key, _icon in section["pages"]:
            assert sheet_html.count(f'href="{url}"') == 1
    assert '<a href="/records" aria-current="page">' in sheet_html
    assert 'data-explore-close' in sheet_html
    assert 'Toggle light or dark mode' in sheet_html

    assert 'nav-hamburger--phone' in resp.text
    assert 'nav-hamburger--tablet' in resp.text
    assert resp.text.count('aria-controls="mobile-explore-sheet"') == 2
    assert '/static/mobile.css?v=41' in resp.text
    assert '/static/ui-polish.js?v=4' in resp.text


def test_phone_explore_static_hooks(client):
    script = client.get("/static/ui-polish.js")
    assert script.status_code == 200
    for hook in (
        "showModal",
        "mobile-explore-open",
        "setExploreExpanded",
        "closeExploreAbovePhone",
    ):
        assert hook in script.text

    styles = client.get("/static/mobile.css")
    assert styles.status_code == 200
    for hook in (
        ".mobile-explore-sheet[open]",
        ".nav-hamburger.nav-hamburger--phone",
        ".nav .nav-links { display: none; }",
        "safe-area-inset-top",
        "min-height: 44px",
    ):
        assert hook in styles.text


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


def test_teg_reports_keeps_requested_in_progress_round_edition(client, monkeypatch):
    """A direct round-report link must not fall back to the latest completed TEG."""
    from teg_analysis.reporting import newspaper_edition
    from webapp.routes import reports

    in_progress_teg = 99
    selected = []

    def fake_read_file(path):
        if path == newspaper_edition.COMPLETED_TEGS_CSV:
            return pd.DataFrame({"TEGNum": [18]})
        if path == newspaper_edition.IN_PROGRESS_TEGS_CSV:
            return pd.DataFrame({"TEGNum": [in_progress_teg]})
        raise AssertionError(f"unexpected status-file read: {path}")

    def fake_build_edition(teg, round_num=None):
        selected.append((teg, round_num))
        return {"teg": teg, "round": round_num}

    monkeypatch.setattr(newspaper_edition, "read_file", fake_read_file)
    monkeypatch.setattr(newspaper_edition, "has_edition", lambda *_: False)
    monkeypatch.setattr(
        newspaper_edition,
        "available_rounds",
        lambda teg: (1,) if teg == in_progress_teg else (),
    )
    newspaper_edition.available_report_tegs.cache_clear()
    monkeypatch.setattr(reports, "available_report_tegs", newspaper_edition.available_report_tegs)
    monkeypatch.setattr(reports, "available_rounds", lambda teg: (1,) if teg == in_progress_teg else ())
    monkeypatch.setattr(reports, "has_edition", lambda *_: False)
    monkeypatch.setattr(reports, "build_edition", fake_build_edition)
    monkeypatch.setattr(reports, "render_desktop_html", lambda edition, rail, story_anchors=False: "")
    monkeypatch.setattr(reports, "for_page", lambda edition: edition)
    monkeypatch.setattr(reports, "has_pdf", lambda *_: False)

    try:
        resp = client.get("/teg-reports", params={"teg": in_progress_teg, "round": 1})
    finally:
        newspaper_edition.available_report_tegs.cache_clear()

    _assert_ok_no_error(resp)
    assert selected == [(in_progress_teg, 1)]
    assert f'<option value="{in_progress_teg}" selected>' in resp.text


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
# Player profile progression charts (R4.2): Career Trend (Overview) and
# Gross vs Par by Round (Rounds) must state their measure/direction and stay
# readable at phone widths, reusing player-profile.js's existing tick-
# thinning/theme-adaptation pattern rather than a second chart system.
# ---------------------------------------------------------------------------

def test_player_overview_trend_panels_state_direction_without_hover(client):
    # DM has both a gross and a Stableford trend chart (see
    # test_player_grouped_overview_preserves_full_history_and_landmarks for
    # JB's equivalent gross-only/Stableford-only edge cases) -- each panel
    # must carry its own static direction copy, not rely on a shared caption
    # or a hover tooltip a touch device can't trigger.
    resp = client.get(f"/player/{REAL_PLAYER_CODE}/tab/overview")
    _assert_ok_no_error(resp)
    gross_panel = resp.text.split('id="chart-gross"', 1)[1].split("</div></div>", 1)[0]
    stab_panel = resp.text.split('id="chart-stableford"', 1)[1].split("</div></div>", 1)[0]
    assert "Lower = better" in gross_panel
    assert "Higher = better" in stab_panel
    # Lowercase per the established aria-pressed contract (R3.4 fix).
    assert 'aria-pressed="True"' not in resp.text and 'aria-pressed="False"' not in resp.text


def test_player_rounds_chart_direction_copy_and_no_inline_height(client):
    resp = client.get(f"/player/{REAL_PLAYER_CODE}/tab/rounds")
    _assert_ok_no_error(resp)
    assert "Lower = better" in resp.text
    assert "pp-rounds-chart" in resp.text
    # The inline height style was moved to CSS (player-profile.css) so the
    # <=640px breakpoint can override it -- an inline style would win over
    # any CSS rule and silently defeat that.
    chart_div = resp.text.split('class="chart-container pp-rounds-chart"', 1)[1].split(">", 1)[0]
    assert "style=" not in chart_div


def test_rounds_chart_teg_group_labels_distinguishable_from_row_label():
    # player-profile.js's initRoundsChart thins the per-TEG-group labels at
    # phone width but must never touch the single "TEG" row-label caption --
    # it tells them apart via xref:'paper' (only the row label sets it).
    # This pins that server-side contract so a refactor of
    # _build_rounds_chart can't silently break the JS's filter.
    from webapp.routes.player import _build_rounds_chart
    import json

    fig = json.loads(_build_rounds_chart(REAL_PLAYER_CODE))
    annotations = fig["layout"]["annotations"]
    row_labels = [a for a in annotations if a.get("xref") == "paper"]
    group_labels = [a for a in annotations if a.get("xref") != "paper"]

    assert len(row_labels) == 1
    assert row_labels[0]["text"] == "TEG"
    # DM has a long history (17 TEGs) -- exactly the dense case the phone
    # thinning exists for.
    assert len(group_labels) >= 15
    assert all(a["text"] != "TEG" for a in group_labels)


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
    # computed active_metric/chart_scale/chart_player -- without echoing the
    # incoming values back, #lr-chart-state falls back to hardcoded template
    # defaults and silently resets the user's real scoreboard-tab selection
    # the moment they switch tabs and back. Rewind is no longer a live
    # control (removed 2026-09-19) -- always echoes "18" regardless of what
    # was passed in.
    resp = client.get("/latest-round/tab", params={
        "teg": 18, "round": 4, "tab": "records",
        "metric": "Stableford", "scale": "adjusted", "player": "DM", "rewind": "9",
    })
    _assert_ok_no_error(resp)
    assert 'data-metric="Stableford"' in resp.text
    assert 'data-scale="adjusted"' in resp.text
    assert 'data-player="DM"' in resp.text
    assert 'data-rewind="18"' in resp.text


def test_latest_round_mobile_scoreboard_contract(client):
    resp = client.get("/latest-round", params={"teg": "invalid", "round": "invalid", "metric": "Stableford", "scale": "adjusted", "player": "invalid", "rewind": "9"})
    _assert_ok_no_error(resp)
    # Main row: # / Player / Personal rank / All-time rank / Round (Total
    # column header is now "Round"/"TEG" depending on the round/TEG-total
    # toggle; round 1 -- the fallback for invalid input here -- has no
    # toggle and always shows "Round").
    assert all(f">{heading}<" in resp.text for heading in ("#", "Player", "Personal rank", "All-time rank", "Round"))
    # Section heading names the metric (moved out of the table into the
    # "Round leaderboard" / metric-name section-title-row).
    assert "Round leaderboard" in resp.text and "Stableford" in resp.text
    # Expandable detail row: Out/In split + per-hole score mix, collapsed by default.
    assert "data-lr-rank-toggle" in resp.text
    assert 'aria-expanded="false"' in resp.text
    assert "rank-detail-row" in resp.text and "hidden" in resp.text
    assert ">Out<" in resp.text and ">In<" in resp.text
    assert "Score mix" in resp.text
    assert "score-mix-row" in resp.text
    assert "score-mix-fill--" in resp.text
    assert 'style="width:' in resp.text
    assert "data-lr-page" in resp.text
    assert "data-lr-focus=" in resp.text
    assert 'data-lr-scale="adjusted"' in resp.text
    assert 'data-lr-history="push"' not in resp.text.split('data-lr-query="metric"', 1)[1].split('</div>', 1)[0]


def test_latest_round_invalid_state_defaults_without_failure(client):
    resp = client.get("/latest-round/tab", params={"teg": "bad", "round": "bad", "tab": "bad", "metric": "bad", "scale": "adjusted", "player": "bad", "rewind": "bad"})
    _assert_ok_no_error(resp)
    # metric="bad" falls back to "Sc" -> friendly "Score". round="bad" falls
    # back to round 1, which has no round/TEG toggle and always shows "Round".
    assert all(f">{heading}<" in resp.text for heading in ("#", "Player", "Personal rank", "All-time rank", "Round"))
    assert "Round leaderboard" in resp.text and "Score" in resp.text
    assert ">Out<" in resp.text and ">In<" in resp.text
    # The metric row is a .segmented control now (it used .pill/.pill--active
    # when this test was written, which is why it used to assert that nothing
    # on the page was aria-pressed at all). Exactly one option may be marked
    # selected, and it must be the metric we fell back to.
    assert resp.text.count('aria-pressed="true"') == 1
    pressed = re.search(r'aria-pressed="true"[^>]*>\s*([^<]+)', resp.text)
    assert pressed and pressed.group(1).strip() == "Score"


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


def test_latest_streak_labels_show_inclusive_score_thresholds():
    from teg_analysis.analysis.streaks import pivot_window_streaks

    window = pd.DataFrame([
        {"Streak Type": "Birdies", "Player": "Player One", "Max Streak": 2},
        {"Streak Type": "Pars or Better", "Player": "Player One", "Max Streak": 3},
        {"Streak Type": "No +2s", "Player": "Player One", "Max Streak": 4},
    ])

    pivot = pivot_window_streaks(window)

    assert pivot["Streak Type"].tolist() == ["⩽Birdie", "⩽Par", "⩽Bogey"]


def test_latest_teg_page_renders(client):
    resp = client.get("/latest-teg")
    _assert_ok_no_error(resp)


@pytest.mark.parametrize("tab", ["aggregate", "scoring", "eclectic", "streaks", "records", "report"])
def test_latest_teg_tab_partials_render(client, tab):
    resp = client.get("/latest-teg/tab", params={"teg": 18, "tab": tab})
    _assert_ok_no_error(resp)


# ---------------------------------------------------------------------------
# Public interaction state (I2) -- full-page routes accept the same state as
# their HTMX partials, and the shared shell opts those pages into one
# success-commit / loading / failure / retry / canonical-history contract.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(("url", "markers"), [
    ("/leaderboard?teg=7&tab=gross&chart_variant=ranking", (
        'data-public-state-keys="teg,tab,chart_variant,type,round,player"',
        'id="lb-tab-input" name="tab" value="gross"',
        'id="lb-chart-variant" name="chart_variant" value="ranking"',
    )),
    ("/results?teg=7&tab=scorecards&chart_variant=standard", (
        'id="results-tab-input" name="tab" value="scorecards"',
    )),
    ("/latest-teg?teg=7&tab=scoring&score_type=GrossVP&display_mode=pct", (
        'id="lt-tab-input" name="tab" value="scoring"',
        'data-public-state-value="GrossVP"',
        'data-public-state-value="pct"',
    )),
    ("/records?tab=round", ('data-public-state-value="round"', 'tab-underline--active')),
    ("/honours?tab=spoon", ('data-public-state-value="spoon"', 'tab-underline--active')),
    ("/player-rankings?tab=jacket&row_dim=Player&col_dim=TEG", (
        'id="pr-tab" name="tab" value="jacket"',
        '<option value="Player" selected>',
        '<option value="TEG" selected>',
    )),
    ("/eclectic?dimension=Course&teg=7", (
        'id="eclectic-dimension" name="dimension" value="Course"',
        '<option value="7" selected>TEG 7</option>',
    )),
    ("/eclectic-records?dimension=Course", ('data-public-state-value="Course"', 'tab-underline--active')),
    ("/top-performances?tab=worst_round&measure=Stableford&n=5", (
        'id="tp-tab-input" name="tab" value="worst_round"',
        'id="tp-measure" name="measure" value="Stableford"',
        'id="tp-n-select" name="n" value="5"',
    )),
    ("/personal-bests?tab=best_rounds&measure=Stableford&n=5&view=tegs", (
        'id="pb-tab-input" name="tab" value="best_rounds"',
        'id="pb-measure" name="measure" value="Stableford"',
        'id="pb-n-select" name="n" value="5"',
    )),
    ("/bestball?mode=worstball&teg=7&sort_best=false&n=5", (
        'id="bb-mode" name="mode" value="worstball"',
        '<option value="false" selected>Worst First</option>',
    )),
    (f"/player/{REAL_PLAYER_CODE}?tab=records", (
        'data-public-state-key="tab" data-public-state-value="records"',
        'tab-underline--active',
    )),
    ("/charts?teg=7&type=gross", (
        '<option value="7" selected>TEG 7</option>',
        'id="chart-type-input" name="type" value="gross"',
    )),
    (f"/scorecard?teg=7&round=2&player={REAL_PLAYER_CODE}&type=one_round_one_player", (
        '<option value="7" selected>TEG 7</option>',
        'id="sc-round" name="round" value="2"',
        'value="one_round_one_player" selected',
    )),
    ("/scoring/matrix?level=round&score_type=Stableford", (
        'id="sm-level-hidden" name="level" value="round"',
        'id="sm-type-hidden" name="score_type" value="Stableford"',
    )),
])
def test_public_direct_links_restore_declared_state(client, url, markers):
    resp = client.get(url)
    _assert_ok_no_error(resp)
    for marker in markers:
        assert marker in resp.text


@pytest.mark.parametrize("page", ["results", "leaderboard"])
@pytest.mark.parametrize("view_type", ["one_round_all_players", "one_player_all_rounds"])
def test_embedded_scorecard_uses_shared_options_and_state(client, page, view_type):
    params = {"teg": 7, "tab": "scorecards", "type": view_type, "round": 2, "player": REAL_PLAYER_CODE}
    for path in (f"/{page}", f"/{page}/table"):
        resp = client.get(path, params=params)
        _assert_ok_no_error(resp)
        assert '<details class="sc-options">' not in resp.text
        assert 'class="sc-options-body section-controls' in resp.text
        assert f'value="{view_type}" selected' in resp.text
        assert 'value="one_round_one_player"' not in resp.text
        assert 'scorecard-table-portrait' in resp.text
        assert 'id="sc-teg"' not in resp.text
        assert f'hx-get="/{page}/table"' in resp.text
        assert f'hx-target="#{"results" if page == "results" else "lb"}-content"' in resp.text


@pytest.mark.parametrize("page", ["results", "leaderboard"])
def test_embedded_scorecard_normalises_bad_view_round_and_roster(client, page):
    resp = client.get(f"/{page}", params={
        "teg": 2, "tab": "scorecards", "type": "one_round_one_player",
        "round": "bad", "player": "AB",
    })
    _assert_ok_no_error(resp)
    assert 'value="one_round_all_players" selected' in resp.text
    assert 'name="round" value="' in resp.text
    assert 'id="sc-player"' in resp.text
    assert '<option value="AB"' not in resp.text


@pytest.mark.parametrize("page", ["results", "leaderboard"])
def test_embedded_scorecard_keeps_inactive_state_controls(client, page):
    resp = client.get(f"/{page}", params={"teg": 7, "tab": "net"})
    _assert_ok_no_error(resp)
    prefix = "results" if page == "results" else "lb"
    assert f'id="{prefix}-sc-type" name="type"' in resp.text
    assert f'id="{prefix}-sc-round" name="round"' in resp.text
    assert f'id="{prefix}-sc-player" name="player"' in resp.text
    assert f'id="{prefix}-chart-variant" name="chart_variant"' in resp.text
    partial = client.get(f"/{page}/table", params={
        "teg": 7, "tab": "net", "round": "", "type": "one_round_all_players",
    })
    _assert_ok_no_error(partial)


def test_public_request_shell_exposes_one_retry_contract(client):
    resp = client.get("/records?tab=round")
    _assert_ok_no_error(resp)
    assert 'data-request-message' in resp.text
    assert 'data-request-retry' in resp.text
    assert 'data-request-dismiss' in resp.text
    assert 'data-public-state-keys="tab"' in resp.text

    script = client.get("/static/ui-polish.js")
    assert script.status_code == 200
    assert "htmx:afterSwap" in script.text
    assert "pushState" in script.text and "replaceState" in script.text
    assert "public-state:commit" in script.text
    assert "window.location.reload()" in script.text
    assert "Loading view" not in script.text
    assert "if (retrying) retryButton.disabled = true" in script.text
    assert "retryButton.disabled = false" in script.text

    styles = client.get("/static/ui-polish.css")
    assert styles.status_code == 200
    assert '.section-panel[aria-busy="true"] { cursor: progress; }' in styles.text
    assert '.section-panel[aria-busy="true"] { opacity:' not in styles.text


@pytest.mark.parametrize(("url", "fallback_marker"), [
    ("/records?tab=not-a-tab", 'data-public-state-value="teg"'),
    ("/leaderboard?teg=999&tab=bad&chart_variant=bad", 'id="lb-tab-input" name="tab" value="net"'),
    ("/scoring/matrix?level=bad&score_type=bad", 'id="sm-level-hidden" name="level" value="teg"'),
    ("/scorecard?teg=999&round=99&player=missing&type=bad", 'value="one_round_all_players" selected'),
])
def test_public_direct_links_normalise_invalid_state(client, url, fallback_marker):
    resp = client.get(url)
    _assert_ok_no_error(resp)
    assert fallback_marker in resp.text


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
    assert '<h2 class="section-title">TEG Trophy wins</h2>' in resp.text
    assert "leaderboard-table" in resp.text


# ---------------------------------------------------------------------------
# Unified standings renderer (I1) -- one Jinja table (partials/
# _standings_table.html, fed by history._standings_rows) replaced the old
# HTML-string table, the dead .lb-cards phone path and the two drifting page
# partials. These tests pin: one row per player with one column per round;
# the round strip and the round cells carry the same values; ties and the
# empty state; the two routes render byte-identical standings markup; the
# deleted card markup never reappears; Gross omits the wooden spoon.
# ---------------------------------------------------------------------------

def _standings_table_html(html: str) -> str:
    m = re.search(r'<table class="teg-table leaderboard-table standings-table">.*?</table>', html, re.S)
    assert m, "standings table not found in response"
    return m.group(0)


def _standings_tbody_rows(table_html: str) -> list:
    tbody = re.search(r"<tbody>(.*?)</tbody>", table_html, re.S).group(1)
    return re.findall(r"<tr(?:\s+class=\"top-rank\")?>(.*?)</tr>", tbody, re.S)


def test_standings_table_has_one_row_per_player_and_round_column(client):
    # TEG 18: 5 players, 4 rounds. TEG 2: 3 rounds (fewest in the data) --
    # guards the round-count-varies case, not just the common 4-round shape.
    resp18 = client.get("/results/table", params={"teg": 18, "tab": "net"})
    table18 = _standings_table_html(resp18.text)
    assert len(re.findall(r'<th class="col-num col-round">', table18)) == 4
    assert len(_standings_tbody_rows(table18)) == 5

    resp2 = client.get("/results/table", params={"teg": 2, "tab": "net"})
    table2 = _standings_table_html(resp2.text)
    assert len(re.findall(r'<th class="col-num col-round">', table2)) == 3


def test_standings_round_strip_matches_round_cells(client):
    # The desktop <td class="col-round"> cells and the phone
    # .standings-rounds strip are two renderings of the *same* r.rounds list
    # (partials/_standings_table.html) -- this is the guard that stops them
    # drifting the way the old duplicated card markup could have.
    resp = client.get("/results/table", params={"teg": 18, "tab": "net"})
    table = _standings_table_html(resp.text)
    rows = _standings_tbody_rows(table)
    assert rows
    for row in rows:
        cell_values = re.findall(r'<td class="col-num col-round">([^<]*)</td>', row)
        strip = re.search(r'<span class="standings-rounds">(.*?)</span>', row, re.S)
        assert strip, "row missing .standings-rounds"
        strip_values = re.findall(r"<b>([^<]*)</b>", strip.group(1))
        assert cell_values == strip_values


def test_standings_ties_share_rank_and_leader_treatment():
    # Unit test on _standings_rows directly: real TEG data may not contain a
    # tie on any given day, so this pins the '=' suffix and shared `lead`
    # flag against a synthetic tied leaderboard shaped like create_leaderboard's
    # output (Rank as string, ties suffixed with '=').
    from webapp.routes.history import _standings_rows

    lb = pd.DataFrame({
        "Rank": ["1=", "1=", "3"],
        "Player": ["Alice ONE", "Bob TWO", "Carol THREE"],
        "R1": ["+1", "+1", "+3"],
        "Total": ["+1", "+1", "+3"],
    })
    standings = _standings_rows(lb, link_players=False)
    rows = standings["rows"]
    assert [r["rank"] for r in rows] == ["1=", "1=", "3"]
    assert [r["lead"] for r in rows] == [True, True, False]
    assert rows[0]["first"] == "Alice" and rows[0]["last"] == "ONE"


def test_standings_empty_frame_is_honest():
    from webapp.routes.history import _standings_rows

    standings = _standings_rows(pd.DataFrame(), link_players=False)
    assert standings == {"round_labels": [], "rows": []}
    standings_none = _standings_rows(None, link_players=False)
    assert standings_none == {"round_labels": [], "rows": []}


def test_standings_card_markup_is_gone(client):
    # I1 deleted the stale .lb-cards/.lb-card* phone path (dead at every
    # viewport per CSS specificity -- .standings-page .lb-cards always won
    # with display:none). This is the regression guard against it returning.
    for path, params in [
        ("/results", {"teg": 18}),
        ("/leaderboard", {}),
        ("/results/table", {"teg": 18, "tab": "net"}),
        ("/leaderboard/table", {"teg": 18, "tab": "net"}),
    ]:
        resp = client.get(path, params=params)
        _assert_ok_no_error(resp)
        assert "lb-card" not in resp.text


def test_leaderboard_and_results_render_the_same_standings(client):
    # The whole point of I1: both routes render through the same context
    # builder AND the same table partial, so their standings markup for the
    # same TEG/tab must be identical, not merely similar.
    resp_results = client.get("/results/table", params={"teg": 18, "tab": "net"})
    resp_lb = client.get("/leaderboard/table", params={"teg": 18, "tab": "net"})
    assert _standings_table_html(resp_results.text) == _standings_table_html(resp_lb.text)


def test_gross_tab_omits_wooden_spoon(client):
    resp = client.get("/results/table", params={"teg": 18, "tab": "gross"})
    _assert_ok_no_error(resp)
    assert "Wooden spoon" not in resp.text


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


def test_honours_trophy_tab_uses_mobile_table_pattern(client):
    # The Trophy/Jacket/Spoon/Doubles winner tables use the bespoke
    # honours-table markup (fixed colgroup, no leader-row shading) rather than
    # the generic df_to_html table -- see _honours_wins_table.
    resp = client.get("/honours/tab/trophy")
    _assert_ok_no_error(resp)
    assert "teg-table honours-table" in resp.text
    assert "<colgroup>" in resp.text
    assert "top-rank" not in resp.text
    assert "table-wrapper--no-pin" in resp.text


def test_honours_eagles_tab_is_a_list(client):
    # Eagles render as a plain list (name, then date/course and TEG/round/hole),
    # not a table -- see _honours_feats_list.
    resp = client.get("/honours/tab/eagles")
    _assert_ok_no_error(resp)
    assert "honours-feats" in resp.text
    assert "<table" not in resp.text


# ---------------------------------------------------------------------------
# Contents (I5: current-TEG home) -- one test per state against a stubbed
# get_tournament_state(), plus the honesty/link-preservation acceptance
# criteria from webapp/design_reviews/ui_workstream/I3-handoff.md.
# ---------------------------------------------------------------------------

import webapp.routes.contents as contents_route


def test_contents_all_nav_links_present(client):
    # Acceptance criterion 2: every NAV_SECTIONS URL appears in /contents,
    # asserted by test rather than inspection.
    resp = client.get("/contents")
    _assert_ok_no_error(resp)
    urls = [url for section in NAV_SECTIONS for (_t, url, _k, _i) in section["pages"]]
    for url in urls:
        assert f'href="{url}"' in resp.text, f"missing sitemap link {url!r}"
    # Player Profiles stay deliberately unlinked from nav (2026-09-18).
    assert 'href="/player"' not in resp.text


def test_contents_state_in_progress(client, monkeypatch):
    monkeypatch.setattr(contents_route, "get_tournament_state", lambda: {
        "state": "in_progress", "teg_num": 19, "teg_label": "TEG 19",
        "area": "Algarve, Portugal", "year": "2026",
        "rounds_played": 2, "rounds_expected": 4,
        "last_round_date": "14 May 2026",
    })
    resp = client.get("/contents")
    _assert_ok_no_error(resp)
    assert "In progress" in resp.text
    assert "TEG 19 — after Round 2 of 4" in resp.text
    assert "TEG 19 Handicaps" in resp.text
    assert "TEG 20 Handicaps" not in resp.text
    assert "Round 2 played 14 May 2026" in resp.text  # R3: dated context line
    # R2: primary action pins the current TEG, never a bare route.
    assert 'href="/leaderboard?teg=19"' in resp.text


def test_contents_state_in_progress_always_defers_rich_content(client, monkeypatch):
    # In-progress rich content (standings + report teaser) always defers to
    # /contents/panel regardless of cache warmth -- its cost driver
    # (cached_round_data(), a real parquet load) never belongs on the
    # initial-paint path.
    monkeypatch.setattr(contents_route, "get_tournament_state", lambda: {
        "state": "in_progress", "teg_num": 19, "teg_label": "TEG 19",
        "area": "Algarve, Portugal", "year": "2026",
        "rounds_played": 2, "rounds_expected": 4,
        "last_round_date": "14 May 2026",
    })
    resp = client.get("/contents")
    _assert_ok_no_error(resp)
    assert 'hx-get="/contents/panel?teg=19&state=in_progress&rounds=2"' in resp.text
    assert 'hx-trigger="load"' in resp.text


def test_contents_panel_route_real_data(client):
    # /contents/panel against real TEG 18 data: a compact Rank/Player/Points/
    # Gross standings table (no round-by-round columns, Stableford-era unit
    # label) and a gross-competition summary line.
    resp = client.get("/contents/panel", params={"teg": 18, "state": "in_progress", "rounds": 4})
    _assert_ok_no_error(resp)
    assert "Standings after Round 4" in resp.text
    assert "col-round" not in resp.text  # round columns dropped -- Total only
    assert "Green Jacket (gross)" in resp.text
    assert ">Points</th>" in resp.text  # unit-aware header, Stableford era
    assert ">Gross</th>" in resp.text


@pytest.mark.parametrize("state", ["in_progress", "complete"])
def test_contents_standings_show_player_keyed_aggregated_gross(client, monkeypatch, state):
    # Gross and net standings have deliberately different orders. The Gross
    # cell must follow its player, and aggregate both rounds with explicit
    # signs, including +0.
    fake_rd = pd.DataFrame({
        "TEGNum": [19] * 6,
        "Round": [1, 2, 1, 2, 1, 2],
        "Player": ["Alex BAKER", "Alex BAKER", "Jon BAKER", "Jon BAKER", "David MULLIN", "David MULLIN"],
        "Stableford": [38, 35, 40, 40, 36, 36],
        "GrossVP": [3, -1, -2, -2, 0, 0],
    })
    monkeypatch.setattr(contents_route, "cached_round_data", lambda: fake_rd)
    if state == "in_progress":
        monkeypatch.setattr(contents_route, "available_rounds", lambda teg: ())
        params = {"teg": 19, "state": state, "rounds": 2}
    else:
        monkeypatch.setattr(contents_route, "cached_winners", lambda: pd.DataFrame({"TEG": []}))
        monkeypatch.setattr(contents_route, "get_edition_summary", lambda teg: None)
        params = {"teg": 19, "state": state}

    resp = client.get("/contents/panel", params=params)
    _assert_ok_no_error(resp)
    assert resp.text.count('<th class="col-gross col-num">Gross</th>') == 1
    body = resp.text.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    for player, gross in (("Jon", "-4"), ("Alex", "+2"), ("David", "+0")):
        row = body[body.index(player):body.index("</tr>", body.index(player))]
        assert f'<td class="col-gross col-num">{gross}</td>' in row


def test_shared_standings_table_callers_do_not_show_contents_gross(client):
    resp = client.get("/results/table", params={"teg": 18, "tab": "net"})
    _assert_ok_no_error(resp)
    assert 'class="col-gross col-num"' not in _standings_table_html(resp.text)


def test_contents_panel_unit_label_pre_teg8_is_vs_par(client, monkeypatch):
    # TEGs <=7 are NetVP (vs-par), not Stableford points -- the standings
    # header must not always say "Points".
    import pandas as pd
    fake_rd = pd.DataFrame({
        "TEGNum": [5, 5], "Round": [1, 1],
        "Player": ["Jon BAKER", "Alex BAKER"],
        "NetVP": [-2, 3], "GrossVP": [2, 3],
    })
    monkeypatch.setattr(contents_route, "cached_round_data", lambda: fake_rd)
    resp = client.get("/contents/panel", params={"teg": 5, "state": "in_progress", "rounds": 1})
    _assert_ok_no_error(resp)
    assert ">vs Par</th>" in resp.text
    assert ">Points</th>" not in resp.text


def test_contents_panel_ties_name_every_player(client, monkeypatch):
    # E2/R8: TEG has no countback -- every tied player is a genuine separate
    # row in the real standings table, never collapsed to "and 1 other".
    import pandas as pd
    fake_rd = pd.DataFrame({
        "TEGNum": [19, 19, 19, 19],
        "Round": [1, 1, 1, 1],
        "Player": ["Jon BAKER", "Alex BAKER", "Gregg WILLIAMS", "David MULLIN"],
        "Stableford": [38, 38, 33, 30],
        "GrossVP": [2, 3, 1, 4],
    })
    monkeypatch.setattr(contents_route, "cached_round_data", lambda: fake_rd)
    resp = client.get("/contents/panel", params={"teg": 19, "state": "in_progress", "rounds": 1})
    _assert_ok_no_error(resp)
    assert resp.text.count("Jon") == 1 and resp.text.count("Alex") == 1
    assert "1=" in resp.text  # tie notation, both rows present
    assert "and 1 other" not in resp.text
    assert "…" not in resp.text


def test_contents_complete_panel_marks_recorded_honours_only(client, monkeypatch):
    # Completed standings use the canonical winners cache, rather than
    # inferring honours from a tied position in the table. Alex and Jon tie
    # for the Trophy competition, but the recorded winner is Alex; Alex also
    # wins the Jacket, so both marks belong on one row.
    import pandas as pd
    fake_rd = pd.DataFrame({
        "TEGNum": [19, 19, 19, 19], "Round": [1, 1, 1, 1],
        "Player": ["Alex BAKER", "Jon BAKER", "Gregg WILLIAMS", "David MULLIN"],
        "Stableford": [38, 38, 33, 30], "GrossVP": [1, 2, 3, 4],
    })
    fake_winners = pd.DataFrame({
        "TEG": ["TEG 19"],
        "TEG Trophy": ["Alex BAKER"],
        "Green Jacket": ["Alex BAKER"],
        "HMM Wooden Spoon": ["David MULLIN"],
    })
    monkeypatch.setattr(contents_route, "cached_round_data", lambda: fake_rd)
    monkeypatch.setattr(contents_route, "cached_winners", lambda: fake_winners)
    monkeypatch.setattr(contents_route, "get_edition_summary", lambda teg: None)

    resp = client.get("/contents/panel", params={"teg": 19, "state": "complete"})
    _assert_ok_no_error(resp)
    assert resp.text.count('aria-label="Trophy"') == 1
    assert resp.text.count('aria-label="Green Jacket"') == 1
    assert resp.text.count('aria-label="Wooden Spoon"') == 1
    alex_row = resp.text[resp.text.index("Alex"):resp.text.index("</tr>", resp.text.index("Alex"))]
    jon_row = resp.text[resp.text.index("Jon"):resp.text.index("</tr>", resp.text.index("Jon"))]
    assert 'aria-label="Trophy"' in alex_row and 'aria-label="Green Jacket"' in alex_row
    assert 'aria-label="Trophy"' not in jon_row


def test_contents_in_progress_panel_has_no_honour_icons(client, monkeypatch):
    import pandas as pd
    fake_rd = pd.DataFrame({
        "TEGNum": [19, 19], "Round": [1, 1],
        "Player": ["Alex BAKER", "Jon BAKER"],
        "Stableford": [38, 30], "GrossVP": [1, 2],
    })
    monkeypatch.setattr(contents_route, "cached_round_data", lambda: fake_rd)
    monkeypatch.setattr(contents_route, "available_rounds", lambda teg: ())

    resp = client.get("/contents/panel", params={"teg": 19, "state": "in_progress", "rounds": 1})
    _assert_ok_no_error(resp)
    assert 'class="honour-icon' not in resp.text


def test_contents_panel_report_teaser_omitted_cleanly_with_no_round_report(client, monkeypatch):
    # E7 extended to round reports: never a dead link. When no round report
    # exists, the standings surface takes the full width instead of leaving
    # an empty second grid column.
    monkeypatch.setattr(contents_route, "available_rounds", lambda teg: ())
    resp = client.get("/contents/panel", params={"teg": 18, "state": "in_progress", "rounds": 1})
    _assert_ok_no_error(resp)
    assert "teaser-headline" not in resp.text
    assert 'class="panel-grid"' in resp.text  # no "two-col" -- single column


def test_contents_panel_complete_state_real_data(client):
    # /contents/panel?state=complete against real TEG 18 data: final
    # standings (no gross-line -- covered by the instant honours line
    # instead), secondary headlines (no "Also in this report" label) capped at 4, and
    # a "View full report" link.
    resp = client.get("/contents/panel", params={"teg": 18, "state": "complete"})
    _assert_ok_no_error(resp)
    assert "Final Standings" in resp.text
    assert "Green Jacket (gross)" not in resp.text  # not repeated -- honours line owns this
    assert "TEG 18 headlines" in resp.text
    assert 'class="lead-teaser" href="/teg-reports?teg=18#story/0"' in resp.text
    assert "Also in this report" not in resp.text
    assert "The Champion" in resp.text  # lead story kicker
    assert "teaser-standfirst" not in resp.text  # no lead synopsis
    assert resp.text.count("<li>") == 4  # capped, TEG 18 has 5 non-lead articles
    assert 'href="/results?teg=18"' in resp.text
    assert "View full report" not in resp.text  # card titles carry the links now
    assert 'href="/results?teg=18">Final Standings ↗' in resp.text
    assert 'class="panel-grid two-col equal-col"' in resp.text


def test_contents_state_complete_with_report_leads_with_headline(client, monkeypatch):
    monkeypatch.setattr(contents_route, "get_tournament_state", lambda: {
        "state": "complete", "teg_num": 18, "teg_label": "TEG 18",
        "area": "Catalonia, Spain", "year": "2025",
        "last_round_date": "14 October 2025", "dateline_month_year": "October 2025",
        "trophy": "Alex BAKER", "jacket": "Gregg WILLIAMS", "spoon": "Jon BAKER",
        "report_summary": {
            "headline": "Alex Baker Wins It in Round One",
            "standfirst": "Twelve points clear after a 46, he never quite ran out.",
            "link": "/teg-reports?teg=18",
        },
        "next_teg": {"label": "TEG 19", "year": 2026, "area": "Algarve, Portugal"},
    })
    resp = client.get("/contents")
    _assert_ok_no_error(resp)
    # Title is plain "TEG N results"; the lead headline lives in the
    # deferred report box with the other headlines, not the page h1.
    assert '<h1 class="state-headline">TEG 18 results</h1>' in resp.text
    assert "Catalonia, Spain | October 2025" in resp.text
    assert "Alex Baker Wins It in Round One" not in resp.text
    assert "TEG 18 — Final Results" not in resp.text  # fallback headline must not also render
    # Compact honours line, not stacked label/name rows.
    assert "Champion" in resp.text and "Alex BAKER" in resp.text
    assert "Green Jacket" in resp.text and "Gregg WILLIAMS" in resp.text
    assert "Wooden spoon" in resp.text and "Jon BAKER" in resp.text
    assert 'class="honours-line"' in resp.text
    # Standings/headlines defer to the panel fetch, same as in-progress.
    assert 'hx-get="/contents/panel?teg=18&state=complete"' in resp.text
    # Owner decision: Full Results only appears inside the deferred panel
    # now (moved below the standings table), not as a page-level action.
    assert "Next: TEG 19 | Algarve, Portugal | 2026" in resp.text
    assert "TEG 19 Handicaps" in resp.text
    assert "TEG 18 Handicaps" not in resp.text


def test_contents_state_complete_no_report_falls_back_to_results_primary(client, monkeypatch):
    monkeypatch.setattr(contents_route, "get_tournament_state", lambda: {
        "state": "complete", "teg_num": 12, "teg_label": "TEG 12",
        "area": "Algarve, Portugal", "year": "2019",
        "last_round_date": "3 May 2019", "dateline_month_year": "May 2019",
        "trophy": "David MULLIN", "jacket": "David MULLIN", "spoon": "Henry MELLER",
        "report_summary": None,
        "next_teg": None,
    })
    resp = client.get("/contents")
    _assert_ok_no_error(resp)
    # Never invents a headline for a report that doesn't exist.
    assert "TEG 12 — Final Results" in resp.text
    assert "TEG 13 Handicaps" in resp.text
    assert "TEG 12 Handicaps" not in resp.text
    assert 'class="headline-link"' not in resp.text
    assert 'class="dateline"' not in resp.text
    # E7: never a dead report link -- the sitemap's general, state-agnostic
    # /teg-reports link still renders; only the pinned report action is absent.
    assert 'href="/teg-reports?teg=12"' not in resp.text
    assert 'href="/results?teg=12"' in resp.text
    assert "state-btn-primary" in resp.text


def test_contents_state_no_data(client, monkeypatch):
    monkeypatch.setattr(contents_route, "get_tournament_state", lambda: {"state": "no_data"})
    resp = client.get("/contents")
    _assert_ok_no_error(resp)
    assert "No tournament data available." in resp.text
    # R9: no invented cause, no retry theatre; no primary action.
    assert "Scores haven" not in resp.text
    assert "state-btn-primary\"" not in resp.text
    # The full sitemap still renders beneath a no-data state.
    assert 'href="/records"' in resp.text


def test_contents_complete_state_costs_no_parquet_load(client):
    # State 2 (the ordinary between-tournaments state -- today's live truth)
    # issues no parquet load. Winners come straight from teg_winners.csv,
    # and the report summary is a separate, cached artefact-parsing cost,
    # not create_leaderboard()/cached_round_data().
    import webapp.deps as deps
    misses_before = deps.cached_round_data.cache_info().misses
    resp = client.get("/contents")
    _assert_ok_no_error(resp)
    assert deps.cached_round_data.cache_info().misses == misses_before


def test_contents_panel_actions_are_all_in_the_sitemap(client, monkeypatch):
    # I4 R11: the state panel adds zero new destinations -- every panel
    # action already exists in the NAV_SECTIONS sitemap.
    monkeypatch.setattr(contents_route, "get_tournament_state", lambda: {
        "state": "in_progress", "teg_num": 19, "teg_label": "TEG 19",
        "area": "Algarve, Portugal", "year": "2026",
        "rounds_played": 2, "rounds_expected": 4,
        "last_round_date": "14 May 2026",
    })
    resp = client.get("/contents")
    _assert_ok_no_error(resp)
    sitemap_bases = {url for section in NAV_SECTIONS for (_t, url, _k, _i) in section["pages"]}
    panel_hrefs = re.findall(r'class="state-(?:btn|link)[^"]*"\s+href="([^"]+)"', resp.text)
    assert panel_hrefs
    for href in panel_hrefs:
        base = href.split("?")[0]
        assert base in sitemap_bases, f"panel action {href!r} is not in the sitemap"


def test_contents_sitemap_is_collapsible_and_closed_by_default(client):
    # The sitemap uses a native <details>, closed by default, with a plain label.
    resp = client.get("/contents")
    _assert_ok_no_error(resp)
    i = resp.text.index('<details class="sitemap-disclosure"')
    tag = resp.text[i:resp.text.index('>', i) + 1]
    assert " open" not in tag and tag.strip() != "<details class=\"sitemap-disclosure\" open>"
    assert 'Full site contents <span class="count">(click to expand)</span>' in resp.text
    import html
    for section in NAV_SECTIONS:
        assert html.escape(section["label"]) in resp.text
    # Closed-by-default doesn't mean absent from the DOM -- every link must
    # still be present for the all-nav-links acceptance criterion to hold.
    urls = [url for section in NAV_SECTIONS for (_t, url, _k, _i) in section["pages"]]
    for url in urls:
        assert f'href="{url}"' in resp.text


def test_contents_article_links_target_stories(client):
    summary = contents_route.get_edition_summary(18)
    panel = client.get("/contents/panel", params={"teg": 18, "state": "complete"})
    _assert_ok_no_error(panel)
    assert f'href="{summary["lead_link"]}"' in panel.text
    for article in summary["other_articles"]:
        assert f'href="{article["link"]}"' in panel.text
    assert f'href="{summary["link"]}">TEG 18 headlines ↗' in panel.text
    report = client.get("/teg-reports", params={"teg": 18})
    _assert_ok_no_error(report)
    for link in [summary["lead_link"], *[a["link"] for a in summary["other_articles"]]]:
        assert f'id="{link.split("#")[1]}"' in report.text
