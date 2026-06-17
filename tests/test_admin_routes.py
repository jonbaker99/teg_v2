"""Smoke tests for the auth-gated admin edit/delete routes.

Uses Starlette's TestClient against the real FastAPI app. These confirm the
auth gate (redirect to login when unauthenticated) and that the edit/delete
pages render once logged in. They read the real data files but never write.
"""

import pytest
from starlette.testclient import TestClient

from webapp.app import app


@pytest.fixture(autouse=True)
def _password(monkeypatch):
    monkeypatch.setenv("WEBAPP_ADMIN_PASSWORD", "secret123")


@pytest.fixture
def client():
    # follow_redirects=False so we can assert the 303 -> /admin/login gate.
    return TestClient(app, follow_redirects=False)


def _login(client):
    resp = client.post("/admin/login", data={"password": "secret123"})
    assert resp.status_code == 303


@pytest.mark.parametrize("path", ["/admin/edit-data", "/admin/delete-data", "/admin/volume-sync"])
def test_routes_require_auth(client, path):
    resp = client.get(path)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/login"


def test_volume_sync_page_renders_when_authed(client, monkeypatch):
    # Avoid any GitHub call: stub the status builder. The route resolves the name
    # from the teg_analysis.io package namespace, so patch it there.
    import teg_analysis.io as tio
    monkeypatch.setattr(tio, "build_sync_status", lambda folder: [
        {"name": "round_info.csv", "gh_size": 10, "store_size": 10,
         "on_github": True, "on_store": True, "status": "Same size"},
    ])
    _login(client)
    resp = client.get("/admin/volume-sync?folder=data")
    assert resp.status_code == 200
    assert "GitHub" in resp.text
    assert "round_info.csv" in resp.text


def test_volume_sync_pull_empty_selection(client, monkeypatch):
    import teg_analysis.io as tio
    monkeypatch.setattr(tio, "build_sync_status", lambda folder: [])
    _login(client)
    resp = client.post("/admin/volume-sync/pull", data={"folder": "data"})
    assert resp.status_code == 200
    assert "no files selected" in resp.text.lower()


def test_edit_page_renders_when_authed(client):
    _login(client)
    resp = client.get("/admin/edit-data?file=round_info")
    assert resp.status_code == 200
    assert "Edit data" in resp.text
    assert "Round Info" in resp.text


def test_edit_processed_view_renders(client):
    _login(client)
    resp = client.get("/admin/edit-data?file=processed")
    assert resp.status_code == 200
    assert "read-only" in resp.text.lower()


def test_delete_page_renders_when_authed(client):
    _login(client)
    resp = client.get("/admin/delete-data")
    assert resp.status_code == 200
    assert "Delete rounds" in resp.text


def test_delete_preview_validates_empty_selection(client):
    _login(client)
    resp = client.post("/admin/delete-data/preview", data={"teg": "10"})
    assert resp.status_code == 200
    assert "at least one round" in resp.text.lower()


def test_edit_save_rejects_unknown_file(client):
    _login(client)
    resp = client.post("/admin/edit-data/save", data={"file": "bogus", "columns": "[]"})
    assert resp.status_code == 200
    assert "unknown file" in resp.text.lower()


def test_unauthed_post_is_blocked(client):
    resp = client.post("/admin/delete-data/execute", data={"teg": "10", "rounds": "1"})
    assert resp.status_code == 401


def test_edit_save_reconstructs_rows(client, monkeypatch):
    """The grid POST is rebuilt into the right frame and saved (no disk write)."""
    import teg_analysis.analysis.data_update as du

    captured = {}

    def fake_save(path, df, *, commit_message=None, defer_github=False):
        captured["path"] = path
        captured["df"] = df.copy()

    monkeypatch.setattr(du, "save_data_file", fake_save)

    _login(client)
    # Two rows, two columns; rids need not be contiguous (add/delete safe).
    form = {
        "file": "teg_winners",
        "columns": '["TEG", "Winner"]',
        "cell__0__0": "TEG 1", "cell__0__1": "AB",
        "cell__5__0": "TEG 2", "cell__5__1": "JB",
    }
    resp = client.post("/admin/edit-data/save", data=form)
    assert resp.status_code == 200
    assert "saved" in resp.text.lower()

    df = captured["df"]
    assert list(df.columns) == ["TEG", "Winner"]
    assert df.shape == (2, 2)
    assert df.iloc[0].tolist() == ["TEG 1", "AB"]
    assert df.iloc[1].tolist() == ["TEG 2", "JB"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
