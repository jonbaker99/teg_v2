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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
