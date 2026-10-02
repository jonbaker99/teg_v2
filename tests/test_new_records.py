"""New-record marking on /records and the /design/new-records prototype."""

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


def test_lab_route_and_tab_override():
    client = TestClient(app)
    resp = client.get("/design/new-records?teg=17")
    assert resp.status_code == 200
    assert "data-new-style" in resp.text
    assert "set by the URL override" in resp.text or "TEG 17" in resp.text
    resp = client.get("/records/tab/round?new_teg=17")
    assert resp.status_code == 200
