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


@pytest.mark.parametrize("path", [
    "/admin/edit-data", "/admin/delete-data", "/admin/volume-sync",
    "/admin/file-guide", "/admin/volume", "/admin/backups",
])
def test_routes_require_auth(client, path):
    resp = client.get(path)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/login"


def test_file_guide_renders(client):
    _login(client)
    resp = client.get("/admin/file-guide")
    assert resp.status_code == 200
    assert "File guide" in resp.text
    assert "all-scores.parquet" in resp.text


def test_volume_browser_renders(client, monkeypatch):
    import teg_analysis.io as tio
    from datetime import datetime, timezone
    monkeypatch.setattr(tio, "list_store_dir", lambda path: {
        "path": "data", "parent": "",
        "entries": [
            {"name": "commentary", "rel": "data/commentary", "is_dir": True,
             "size": None, "mtime": datetime(2026, 1, 1, tzinfo=timezone.utc)},
            {"name": "round_info.csv", "rel": "data/round_info.csv", "is_dir": False,
             "size": 12, "mtime": datetime(2026, 1, 1, tzinfo=timezone.utc)},
        ],
    })
    monkeypatch.setattr(tio, "list_sync_backups", lambda: [])
    _login(client)
    resp = client.get("/admin/volume?path=data")
    assert resp.status_code == 200
    assert "round_info.csv" in resp.text
    assert "Download" in resp.text and "Delete" in resp.text
    # round_info.csv is editable -> Edit link present
    assert "/admin/edit-data?file=round_info" in resp.text


def test_volume_download(client, monkeypatch):
    import teg_analysis.io as tio
    monkeypatch.setattr(tio, "read_store_file", lambda path: b"col\n1\n")
    _login(client)
    resp = client.get("/admin/volume/download?path=data/round_info.csv")
    assert resp.status_code == 200
    assert resp.content == b"col\n1\n"
    assert "attachment" in resp.headers["content-disposition"]


def test_volume_delete_backs_up(client, monkeypatch):
    import teg_analysis.io as tio
    monkeypatch.setattr(tio, "delete_store_file",
                        lambda path: {"deleted": path, "backup_rel": "data/backups/sync/x/" + path})
    monkeypatch.setattr(tio, "list_store_dir", lambda path: {
        "path": path, "parent": "", "entries": []})
    monkeypatch.setattr(tio, "list_sync_backups", lambda: [])
    _login(client)
    resp = client.post("/admin/volume/delete", data={"path": "data/old.csv"})
    assert resp.status_code == 200
    assert "deleted" in resp.text.lower()


def test_backups_page_and_restore(client, monkeypatch):
    import teg_analysis.io as tio
    monkeypatch.setattr(tio, "list_sync_backups", lambda: [
        {"timestamp": "20260101_000000", "original": "data/round_info.csv",
         "backup_rel": "data/backups/sync/20260101_000000/data/round_info.csv", "size": 10},
    ])
    _login(client)
    resp = client.get("/admin/backups")
    assert resp.status_code == 200
    assert "round_info.csv" in resp.text

    captured = {}
    def fake_restore(backup_rel, *, backup_current=True):
        captured["backup_rel"] = backup_rel
        captured["backup_current"] = backup_current
        return "data/round_info.csv"
    monkeypatch.setattr(tio, "restore_backup", fake_restore)
    resp = client.post("/admin/backups/restore", data={
        "backup_rel": "data/backups/sync/20260101_000000/data/round_info.csv"})
    assert resp.status_code == 200
    assert "restored" in resp.text.lower()
    assert captured["backup_rel"].endswith("round_info.csv")


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


def test_volume_sync_pull_warns_on_newer(client, monkeypatch):
    """Selecting a store file that's newer than GitHub shows the confirm screen."""
    import teg_analysis.io as tio
    from datetime import datetime, timezone
    monkeypatch.setattr(tio, "detect_pull_conflicts", lambda folder, names: [
        {"name": "round_info.csv",
         "store_time": datetime(2026, 6, 1, tzinfo=timezone.utc),
         "gh_time": datetime(2026, 1, 1, tzinfo=timezone.utc)},
    ])

    def _boom(*a, **k):
        raise AssertionError("pull must not run before confirmation")
    monkeypatch.setattr(tio, "pull_files", _boom)

    _login(client)
    resp = client.post("/admin/volume-sync/pull",
                       data={"folder": "data", "files": "round_info.csv"})
    assert resp.status_code == 200
    assert "would be overwritten" in resp.text.lower()
    assert "pull anyway" in resp.text.lower()


def test_volume_sync_preview_shows_table(client, monkeypatch):
    """Pull/Push first render a preview of what will be overwritten."""
    import teg_analysis.io as tio
    from datetime import datetime, timezone
    monkeypatch.setattr(tio, "build_sync_preview", lambda action, folder, names: [
        {"name": "round_info.csv", "outcome": "overwrite",
         "source_size": 10, "dest_size": 9,
         "store_time": datetime(2026, 1, 1, tzinfo=timezone.utc),
         "gh_time": datetime(2026, 6, 1, tzinfo=timezone.utc),
         "newer": "github", "is_conflict": False, "diffable": True},
    ])

    def _boom(*a, **k):
        raise AssertionError("pull must not run from the preview step")
    monkeypatch.setattr(tio, "pull_files", _boom)

    _login(client)
    resp = client.post("/admin/volume-sync/preview",
                       data={"action": "pull", "folder": "data", "files": "round_info.csv"})
    assert resp.status_code == 200
    assert "review pull" in resp.text.lower()
    assert "round_info.csv" in resp.text
    assert "confirm pull" in resp.text.lower()


def test_volume_sync_preview_empty_selection(client, monkeypatch):
    import teg_analysis.io as tio
    monkeypatch.setattr(tio, "build_sync_status", lambda folder: [])
    _login(client)
    resp = client.post("/admin/volume-sync/preview",
                       data={"action": "pull", "folder": "data"})
    assert resp.status_code == 200
    assert "no files selected" in resp.text.lower()


def test_volume_sync_diff_renders(client, monkeypatch):
    import teg_analysis.io as tio
    monkeypatch.setattr(tio, "file_diff", lambda folder, name: {
        "diffable": True, "identical": False, "truncated": False,
        "lines": ["--- store", "+++ github", "@@ -1 +1 @@", "-old", "+new"],
    })
    _login(client)
    resp = client.get("/admin/volume-sync/diff?folder=data&name=round_info.csv")
    assert resp.status_code == 200
    assert "+new" in resp.text
    assert "-old" in resp.text


def test_volume_sync_restore(client, monkeypatch):
    import teg_analysis.io as tio
    monkeypatch.setattr(tio, "restore_backup", lambda backup_rel: "data/round_info.csv")
    monkeypatch.setattr(tio, "build_sync_status", lambda folder: [])
    monkeypatch.setattr(tio, "list_sync_backups", lambda: [])
    _login(client)
    resp = client.post("/admin/volume-sync/restore",
                       data={"folder": "data", "backup_rel": "data/backups/sync/x/data/round_info.csv"})
    assert resp.status_code == 200
    assert "restored" in resp.text.lower()


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


def test_data_update_execute_blocks_missing_round_info(client, monkeypatch):
    """A round whose TEG isn't in round_info is refused before any write."""
    import pandas as pd
    import teg_analysis.analysis.pipeline as pipeline
    import teg_analysis.analysis.data_update as du

    monkeypatch.setattr(pipeline, "get_google_sheet", lambda s, w: pd.DataFrame())
    monkeypatch.setattr(du, "process_google_sheets_data",
                        lambda raw: pd.DataFrame({"TEGNum": [12], "Round": [1]}))
    monkeypatch.setattr(du, "find_tegs_missing_round_info", lambda df: [12])

    def _must_not_run(*a, **k):
        raise AssertionError("execute_data_update must not run when round_info is missing")
    monkeypatch.setattr(du, "execute_data_update", _must_not_run)

    _login(client)
    resp = client.post("/admin/data-update/execute",
                       data={"sheet": "S", "worksheet": "W", "mode": "append"})
    assert resp.status_code == 200
    assert "missing tournament metadata" in resp.text.lower()
    assert "/admin/edit-data?file=round_info" in resp.text


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
