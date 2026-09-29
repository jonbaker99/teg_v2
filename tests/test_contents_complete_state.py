"""Regression tests: Next TEG tab crash (issue 15) and complete-state standings
without a tournament report (issue 16). Everything is faked -- no real TEG data."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from webapp.app import app
from webapp.routes import contents as contents_route
from teg_analysis.analysis import history

ERROR_MARKERS = (">Error: ", "error-box", "data-public-response-error")


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _ok(resp):
    assert resp.status_code == 200
    for marker in ERROR_MARKERS:
        assert marker not in resp.text, marker


def _complete_state(report_summary=None):
    return {
        "state": "complete", "teg_num": 19, "teg_label": "TEG 19",
        "area": "Algarve, Portugal", "year": "2026",
        "last_round_date": "11 October 2026", "dateline_month_year": "October 2026",
        "trophy": "Alex BAKER", "jacket": "Gregg WILLIAMS", "spoon": "Jon BAKER",
        "report_summary": report_summary,
    }


def _fake_standings_ctx(teg_num, honours=None):
    return {"standings": {"rows": [], "round_labels": [], "measure_label": "Pts"},
            "title": "x"}


# (c) --------------------------------------------------------------------

def test_get_future_tegs_returns_tegnum(monkeypatch):
    monkeypatch.setattr("teg_analysis.io.read_file", lambda p: pd.DataFrame(
        {"TEGNum": [19], "TEG": ["TEG 19"], "Year": [2026], "Area": ["Algarve"]}))
    out = history.get_future_tegs()
    assert "TEGNum" in out.columns and list(out["TEGNum"]) == [19]


def test_get_future_tegs_derives_tegnum_when_column_absent(monkeypatch):
    monkeypatch.setattr("teg_analysis.io.read_file", lambda p: pd.DataFrame(
        {"TEG": ["TEG 19"], "Year": [2026], "Area": ["Algarve"]}))
    assert list(history.get_future_tegs()["TEGNum"]) == [19]


def test_get_future_tegs_empty_fallback_has_tegnum(monkeypatch):
    def boom(p):
        raise FileNotFoundError(p)
    monkeypatch.setattr("teg_analysis.io.read_file", boom)
    out = history.get_future_tegs()
    assert out.empty and "TEGNum" in out.columns


# (a) --------------------------------------------------------------------

def _next_teg_setup(monkeypatch):
    monkeypatch.setattr(contents_route, "get_next_teg_and_check_if_in_progress_fast",
                        lambda: (19, 20, False))

    def _no_rounds(teg):
        raise ValueError("No round_info")
    monkeypatch.setattr(contents_route, "build_venue_context", _no_rounds)
    # Real get_future_tegs, fed a file that only knows TEG 19.
    monkeypatch.setattr("teg_analysis.io.read_file", lambda p: pd.DataFrame(
        {"TEGNum": [19], "TEG": ["TEG 19"], "Year": [2026], "Area": ["Algarve"]}))
    monkeypatch.setattr(contents_route, "_current_handicap_tiles", lambda teg: {
        "is_draft": False, "next_teg_label": "", "tiles": []})


def test_next_teg_without_round_info_or_future_row_renders_tbc(client, monkeypatch):
    _next_teg_setup(monkeypatch)
    monkeypatch.setattr(contents_route, "get_tournament_state", lambda: _complete_state())
    resp = client.get("/contents", params={"view": "next"})
    _ok(resp)
    assert "Next: TEG 20" in resp.text
    assert "Venue TBC. Dates TBC" in resp.text


def test_next_teg_survives_handicap_failure(client, monkeypatch):
    _next_teg_setup(monkeypatch)

    def boom(teg):
        raise RuntimeError("handicap calc blew up")
    monkeypatch.setattr(contents_route, "_current_handicap_tiles", boom)
    monkeypatch.setattr(contents_route, "get_tournament_state", lambda: _complete_state())
    resp = client.get("/contents", params={"view": "next"})
    _ok(resp)
    assert "Next: TEG 20" in resp.text
    assert "Dates and courses TBC" in resp.text


# (b) --------------------------------------------------------------------

def test_complete_state_without_report_loads_standings_panel(client, monkeypatch):
    monkeypatch.setattr(contents_route, "get_tournament_state", lambda: _complete_state(None))
    resp = client.get("/contents")
    _ok(resp)
    assert 'hx-get="/contents/panel?teg=19&state=complete"' in resp.text
    assert "TEG 19 results" in resp.text
    assert "Algarve, Portugal. October 2026" in resp.text
    assert "Champion" in resp.text
    assert "Final Results" not in resp.text


def test_complete_panel_without_report_is_full_width_no_headlines(client, monkeypatch):
    monkeypatch.setattr(contents_route, "get_edition_summary", lambda teg, *a: None)
    monkeypatch.setattr(contents_route, "_standings_table_context", _fake_standings_ctx)
    monkeypatch.setattr(contents_route, "_honours_by_player", lambda teg: {})
    resp = client.get("/contents/panel", params={"teg": 19, "state": "complete"})
    _ok(resp)
    assert "Final Standings" in resp.text
    assert "headlines-pane" not in resp.text
    assert "two-col" not in resp.text


def test_complete_panel_with_report_keeps_two_columns(client, monkeypatch):
    summary = {"headline": "H", "link": "/teg-reports?teg=19", "other_articles": []}
    monkeypatch.setattr(contents_route, "get_edition_summary", lambda teg, *a: summary)
    monkeypatch.setattr(contents_route, "_standings_table_context", _fake_standings_ctx)
    monkeypatch.setattr(contents_route, "_honours_by_player", lambda teg: {})
    resp = client.get("/contents/panel", params={"teg": 19, "state": "complete"})
    _ok(resp)
    assert "headlines-pane" in resp.text and "two-col equal-col" in resp.text
