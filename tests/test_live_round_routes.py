"""Tests for the player-facing live-round page + poll/write API.

No admin cookie needed for these routes -- the token in the URL is the
access control. All teg_analysis.analysis.live_round calls are monkeypatched;
no test here touches real data.
"""

import pytest
from starlette.testclient import TestClient

from webapp.app import app


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


def test_live_round_page_unknown_token_shows_error_not_crash(client):
    resp = client.get("/live-round/does-not-exist")
    assert resp.status_code == 200
    assert "doesn&#39;t match" in resp.text.lower() or "doesn't match" in resp.text.lower()


def test_live_round_page_renders_for_valid_token(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.setattr(lrmod, "get_live_round_context", lambda token: {
        "token": token, "teg_num": 19, "round_num": 1, "status": "active", "course": "Ashdown",
        "players": ["DM", "GW"], "player_names": {"DM": "David MULLIN", "GW": "Gregg WILLIAMS"},
        "holes": [{"hole": h, "par": 4, "si": h} for h in range(1, 19)],
    })

    resp = client.get("/live-round/tok123")
    assert resp.status_code == 200
    assert "Ashdown" in resp.text
    assert "tok123" in resp.text


def test_api_poll_scores_unknown_token_404(client):
    resp = client.get("/api/live-round/nope/scores")
    assert resp.status_code == 404


def test_api_poll_scores_returns_cells(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.setattr(lrmod, "get_scores_since", lambda token, since_seq=0: {
        "seq": 2, "status": "active",
        "cells": [{"hole": 1, "player": "DM", "value": 4, "conflict": False, "device_name": "Jon", "prev_value": None, "prev_device_name": None}],
    })

    resp = client.get("/api/live-round/tok123/scores?since=0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["seq"] == 2
    assert body["cells"][0]["value"] == 4


def test_api_write_scores_success(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    captured = {}

    def fake_apply(token, device_id, device_name, cells):
        captured.update(token=token, device_id=device_id, device_name=device_name, cells=cells)
        return {"seq": 3}

    monkeypatch.setattr(lrmod, "apply_score_writes", fake_apply)

    resp = client.post("/api/live-round/tok123/scores", json={
        "device_id": "dev-A", "device_name": "Jon's phone",
        "cells": [{"hole": 1, "player": "DM", "value": 4}],
    })
    assert resp.status_code == 200
    assert resp.json() == {"seq": 3}
    assert captured["token"] == "tok123"
    assert captured["cells"] == [{"hole": 1, "player": "DM", "value": 4}]


def test_api_write_scores_empty_cells_rejected(client):
    resp = client.post("/api/live-round/tok123/scores", json={
        "device_id": "dev-A", "device_name": "Jon", "cells": [],
    })
    assert resp.status_code == 400


def test_api_write_scores_unknown_token_404(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    def fake_apply(token, device_id, device_name, cells):
        raise lrmod.LiveRoundNotFoundError(token)

    monkeypatch.setattr(lrmod, "apply_score_writes", fake_apply)

    resp = client.post("/api/live-round/nope/scores", json={
        "device_id": "dev-A", "device_name": "Jon", "cells": [{"hole": 1, "player": "DM", "value": 4}],
    })
    assert resp.status_code == 404


def test_api_write_scores_inactive_round_409(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    def fake_apply(token, device_id, device_name, cells):
        raise lrmod.LiveRoundInactiveError("finalized already")

    monkeypatch.setattr(lrmod, "apply_score_writes", fake_apply)

    resp = client.post("/api/live-round/tok123/scores", json={
        "device_id": "dev-A", "device_name": "Jon", "cells": [{"hole": 1, "player": "DM", "value": 4}],
    })
    assert resp.status_code == 409


def test_api_write_scores_clear_cell_null_value(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    captured = {}
    monkeypatch.setattr(lrmod, "apply_score_writes", lambda token, d, n, cells: captured.setdefault("cells", cells) or {"seq": 1})

    resp = client.post("/api/live-round/tok123/scores", json={
        "device_id": "dev-A", "device_name": "Jon",
        "cells": [{"hole": 1, "player": "DM", "value": None}],
    })
    assert resp.status_code == 200
    assert captured["cells"][0]["value"] is None


# --- Site strip (snags 23, 24) ---

_CTX = {
    "token": "tok123", "teg_num": 19, "round_num": 1, "status": "active", "course": "Ashdown",
    "players": ["DM", "GW"], "player_names": {"DM": "David MULLIN", "GW": "Gregg WILLIAMS"},
    "holes": [{"hole": h, "par": 4, "si": h} for h in range(1, 19)],
}
_REVIEW = "/admin/live-round/tok123/review"


def _strip_pages(client, monkeypatch, admin: bool):
    import teg_analysis.analysis.live_round as lrmod
    monkeypatch.setattr(lrmod, "get_live_round_context", lambda token: dict(_CTX, token=token))
    monkeypatch.setattr(lrmod, "get_live_leaderboard", lambda token: {
        "token": token, "teg_num": 19, "round_num": 1, "course": "Ashdown", "status": "active",
    })
    if admin:
        from webapp.admin_auth import COOKIE_NAME, _expected_token
        client.cookies.set(COOKIE_NAME, _expected_token())
    return [client.get("/live-round/tok123").text, client.get("/live-round/tok123/leaderboard").text]


def test_site_strip_brand_and_leaderboard_links_on_both_pages(client, monkeypatch):
    for text in _strip_pages(client, monkeypatch, admin=False):
        assert 'href="/">The El Golfo</a>' in text
        assert 'href="/leaderboard?teg=19"' in text


def test_site_strip_admin_link_hidden_without_cookie(client, monkeypatch):
    for text in _strip_pages(client, monkeypatch, admin=False):
        assert _REVIEW not in text
        assert "admin_panel_settings" not in text


def test_site_strip_admin_link_shown_with_cookie(client, monkeypatch):
    for text in _strip_pages(client, monkeypatch, admin=True):
        assert f'href="{_REVIEW}"' in text


def test_site_strip_error_page_has_brand_link_only(client):
    for path in ("/live-round/does-not-exist", "/live-round/does-not-exist/leaderboard"):
        text = client.get(path).text
        assert 'href="/">The El Golfo</a>' in text
        assert "/leaderboard?teg=" not in text
        assert "/review" not in text


# --- Banner state (snag 25) ---

def _set_banner_rows(monkeypatch, rows, enabled=True):
    import teg_analysis.analysis.live_round as lrmod
    from webapp import deps

    monkeypatch.setattr(lrmod, "get_public_entry_enabled", lambda: enabled)
    monkeypatch.setattr(lrmod, "list_live_rounds", lambda: rows)
    deps.clear_public_round_banners_cache()


def _banner_row(status, token="tok1", teg=19, rnd=2):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {"Token": token, "TEGNum": teg, "Round": rnd, "CreatedAt": now,
            "Status": status, "FinalizedAt": now if status == "finalized" else None}


def test_banner_live_for_active_round(client, monkeypatch):
    from webapp import deps
    _set_banner_rows(monkeypatch, [_banner_row("active")])
    try:
        resp = client.get("/", follow_redirects=True)
        assert "live-entry-banner" in resp.text
        assert "Enter scores" in resp.text
        assert 'href="/live-round/tok1"' in resp.text
        assert "results are in" not in resp.text
    finally:
        deps.clear_public_round_banners_cache()


def test_banner_becomes_results_after_finalize(client, monkeypatch):
    from webapp import deps
    _set_banner_rows(monkeypatch, [_banner_row("active")])
    assert "Enter scores" in client.get("/", follow_redirects=True).text
    _set_banner_rows(monkeypatch, [_banner_row("finalized")])
    deps.clear_all_data_caches()
    try:
        text = client.get("/", follow_redirects=True).text
        assert "Enter scores" not in text
        assert "TEG 19 Round 2 results are in." in text
        assert 'href="/leaderboard?teg=19"' in text
        assert "live-entry-banner--results" in text
    finally:
        deps.clear_public_round_banners_cache()


def test_banner_results_hidden_on_leaderboard_page_but_live_shown(client, monkeypatch):
    from webapp import deps
    try:
        _set_banner_rows(monkeypatch, [_banner_row("finalized")])
        resp = client.get("/leaderboard")
        assert "results are in" not in resp.text
        _set_banner_rows(monkeypatch, [_banner_row("active")])
        resp = client.get("/leaderboard")
        assert "Enter scores" in resp.text
    finally:
        deps.clear_public_round_banners_cache()


def test_banner_absent_when_switch_off(client, monkeypatch):
    from webapp import deps
    _set_banner_rows(monkeypatch, [_banner_row("active")], enabled=False)
    try:
        assert "live-entry-banner" not in client.get("/", follow_redirects=True).text
    finally:
        deps.clear_public_round_banners_cache()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
