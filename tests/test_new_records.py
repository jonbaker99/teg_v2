"""New-record marking and the New Records tab on /records."""

import re

import pytest
from starlette.testclient import TestClient

from webapp.app import app
from webapp.routes import records
from webapp.routes.records import _build_stacked_records_list, _record_teg, _stacked_records_html


def test_record_teg_parsing():
    assert _record_teg("TEG 10 Rd 1 (Boavista, Sep 2017)") == 10
    assert _record_teg("TEG 17 R2, H9 to H10") == 17
    # Streak spanning TEGs: the last one is where the record was reached.
    assert _record_teg("TEG 7, R1 H8 to R2 H12") == 7
    assert _record_teg("TEG 6 R4 H15 to TEG 7 R1 H3") == 7
    assert _record_teg("Boavista, Sep 2017") is None
    assert _record_teg(None) is None


@pytest.fixture
def holders(monkeypatch):
    monkeypatch.setattr(records, "get_player_dict", lambda: {"AB": "Alan B", "CD": "Cara D"})
    return [
        {"label": "Birdies", "value": "5", "player": "AB", "when": "TEG 17 Rd 2"},
        {"label": "Birdies", "value": "5", "player": "CD", "when": "TEG 10 Rd 1"},
        {"label": "Pars", "value": "9", "player": "CD", "when": "TEG 10 Rd 1"},
        {"label": "Pars", "value": "9", "player": "CD", "when": "TEG 17 Rd 3"},
        {"label": "Eagles", "value": "1", "player": "AB", "when": "TEG 17 Rd 1"},
    ]


def test_marking_classes(holders):
    html = _build_stacked_records_list(holders, min_value=None, new_teg=17)
    assert html.count("rec-group--new") == 3
    assert html.count("rec-holder--new") == 3
    assert html.count("rec-when--new") == 3
    assert "(new record)" in html
    plain = _build_stacked_records_list(holders, min_value=None)
    assert "--new" not in plain and "new record" not in plain
    # Pars group: only the TEG 17 occasion is marked, TEG 10 one is not.
    assert "<span class='rec-when'>TEG 10 Rd 1</span>" in html


def test_new_count_respects_min_value(holders):
    _, new = _stacked_records_html(holders, min_value=2, new_teg=17)
    # Eagles (value 1) is filtered out first.
    assert new == [("Birdies", "Alan B"), ("Pars", "Cara D")]
    _, new_all = _stacked_records_html(holders, min_value=None, new_teg=17)
    assert len(new_all) == 3


def test_only_new_filters_and_drops_markers(holders):
    html, _ = _stacked_records_html(holders, min_value=2, new_teg=17, only_new=True)
    assert "TEG 17 Rd 2" in html and "TEG 17 Rd 3" in html
    assert "TEG 10" not in html and "Eagles" not in html
    assert "--new" not in html and "new record" not in html


@pytest.fixture
def client():
    return TestClient(app)


def test_tab_override_and_no_banner(client):
    resp = client.get("/records/tab/round?new_teg=17")
    assert resp.status_code == 200
    assert "new-banner" not in resp.text
    assert "rec-holder--new" in resp.text


def test_tabs_new_first_teg_default(client):
    assert records.TABS[0][0] == "new"
    resp = client.get("/records?new_teg=17")
    assert resp.status_code == 200
    assert re.search(r'tab-underline tab-underline--active"[^>]*data-public-state-value="teg"', resp.text)
    # new_teg carries through the HTMX tab loads.
    assert 'hx-get="/records/tab/streaks?new_teg=17"' in resp.text


def _dots(html):
    return re.findall(r'data-public-state-value="(\w+)"[^>]*>\s*[^<]*?<span class="tab-new-mark"', html)


def test_dots_only_on_tabs_with_new_holders(client):
    resp = client.get("/records?new_teg=17")
    dotted = set(_dots(resp.text))
    expected = {t for t, _ in records.TABS if t != "new"
                and records._tab_context(t, 17)["new_count"] > 0}
    expected.add("new")  # the New tab is dotted whenever anything is new
    assert dotted == expected and dotted
    assert "(new records)" in resp.text
    # TEG 18 set no records: no dots.
    assert "tab-new-mark" not in client.get("/records?new_teg=18").text


def test_new_tab_matches_dots(client):
    resp = client.get("/records/tab/new?new_teg=17")
    assert resp.status_code == 200
    assert "Set in TEG 17" in resp.text or "Set so far in TEG 17" in resp.text
    assert "New personal bests" in resp.text
    assert "--new" not in resp.text
    total = sum(records._tab_context(t, 17)["new_count"] for t, _ in records.TABS if t != "new")
    assert records._tab_context("new", 17)["new_count"] == total
    assert resp.text.count("rec-identity") >= total


def test_new_tab_empty_states(client):
    resp = client.get("/records/tab/new?new_teg=18")
    assert resp.status_code == 200
    assert "No new records set in TEG 18." in resp.text
    assert "No new personal bests in TEG 18." in resp.text or "rec-group" in resp.text


def test_tab_context_cached_and_cleared():
    from webapp import deps
    records._tab_context("streaks", 17)
    assert ("streaks", 17) in records._TAB_CTX_CACHE
    assert records._tab_context("streaks", 17) is records._tab_context("streaks", 17)
    deps.clear_all_data_caches()
    assert not records._TAB_CTX_CACHE
