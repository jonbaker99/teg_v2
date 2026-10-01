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
    "/admin/file-guide", "/admin/volume", "/admin/backups", "/admin/round-setup",
    "/admin/teg-setup", "/admin/live-round", "/admin/reports",
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
         "on_github": True, "on_store": True, "status": "Identical"},
    ])
    _login(client)
    resp = client.get("/admin/volume-sync?folder=data")
    assert resp.status_code == 200
    assert "GitHub" in resp.text
    assert "round_info.csv" in resp.text


def test_volume_sync_offers_select_by_status(client, monkeypatch):
    """One button per status present, with its count; rows carry their status
    so the button can tick them. Absent statuses get no button."""
    import teg_analysis.io as tio
    row = lambda n, st: {"name": n, "gh_size": 1, "store_size": 2,
                         "on_github": True, "on_store": True, "status": st}
    monkeypatch.setattr(tio, "build_sync_status", lambda folder: [
        row("a.md", "Different"), row("b.md", "Different"), row("c.md", "Identical"),
    ])
    _login(client)
    resp = client.get("/admin/volume-sync?folder=data/commentary")
    assert resp.status_code == 200
    assert "tegSyncSelectStatus('Different')\">Different (2)</button>" in resp.text
    assert "Identical (1)</button>" in resp.text
    assert "Only on GitHub (" not in resp.text
    assert resp.text.count('data-status="Different"') == 2


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


def test_volume_sync_reports_refreshes(client, monkeypatch):
    """The one-click reports refresh runs in the background (progress-polled);
    the pull actually happens and the final poll response reports the count."""
    import re
    import teg_analysis.io as tio

    calls = {}

    def _fake(on_progress=None):
        calls["ran"] = True
        if on_progress:
            on_progress(7, 7, "teg_9_report_styled.md")
        return {"pulled": 7, "failed": [], "folders": {"data/commentary": 7}}

    monkeypatch.setattr(tio, "sync_report_files", _fake)
    _login(client)
    resp = client.post("/admin/volume-sync/sync-reports",
                       data={"folder": "data/commentary"})
    assert resp.status_code == 200
    assert calls.get("ran") is True         # the refresh actually ran (TestClient
                                             # runs BackgroundTasks synchronously)
    assert "Syncing" in resp.text           # initial response is the progress view

    job_id = re.search(r'/admin/volume-sync/job/([0-9a-f]+)', resp.text).group(1)
    poll = client.get(f"/admin/volume-sync/job/{job_id}", params={"folder": "data/commentary"})
    assert poll.status_code == 200
    assert "7" in poll.text                 # pulled count surfaced, job finished


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


# ---------------------------------------------------------------------------
# Round setup (pre-round Par/SI confirmation) -- reads real data, never writes
# except in the explicitly monkeypatched save test.
# ---------------------------------------------------------------------------

def test_round_setup_list_renders(client):
    """With real data every round is already played, so the list is empty --
    the page should say so rather than list 18 TEGs of played history."""
    _login(client)
    resp = client.get("/admin/round-setup")
    assert resp.status_code == 200
    assert "Round setup" in resp.text
    assert "Nothing pending" in resp.text


def test_round_setup_list_shows_pending_round(client, monkeypatch):
    """A round in round_info.csv with no scores yet shows up as needing setup."""
    import teg_analysis.analysis.round_setup as rs

    monkeypatch.setattr(
        rs,
        "get_rounds_status",
        lambda: [
            {"teg_num": 19, "round_num": 1, "course": "Ashdown", "date": "01/01/2027", "is_set_up": False},
        ],
    )

    _login(client)
    resp = client.get("/admin/round-setup")
    assert resp.status_code == 200
    assert "Needs setup" in resp.text
    assert "Ashdown" in resp.text


def test_round_setup_form_renders_course_default(client):
    _login(client)
    # TEG 10 Round 1 (Boavista) has no round_pars entry yet -> course_pars default.
    resp = client.get("/admin/round-setup/10/1")
    assert resp.status_code == 200
    assert "Boavista" in resp.text
    assert "course_pars.csv" in resp.text


def test_round_setup_form_flags_variable_routing(client):
    _login(client)
    # TEG 7 Round 1 was played at Praia D'El Rey, which is flagged.
    resp = client.get("/admin/round-setup/7/1")
    assert resp.status_code == 200
    assert "back-9-first" in resp.text.lower()


def test_round_setup_form_unknown_round(client):
    _login(client)
    resp = client.get("/admin/round-setup/999/1")
    assert resp.status_code == 200
    assert "error" in resp.text.lower() or "not found" in resp.text.lower()


def test_round_setup_save_writes_round_pars(client, monkeypatch):
    import teg_analysis.analysis.round_setup as rs

    captured = {}

    def fake_save(teg_num, round_num, holes):
        captured["teg_num"] = teg_num
        captured["round_num"] = round_num
        captured["holes"] = holes
        return {"teg_num": teg_num, "round_num": round_num, "holes_saved": len(holes)}

    monkeypatch.setattr(rs, "save_round_setup", fake_save)

    _login(client)
    form = {f"par__{h}": "4" for h in range(1, 19)}
    form.update({f"si__{h}": str(h) for h in range(1, 19)})
    resp = client.post("/admin/round-setup/10/1/save", data=form)

    assert resp.status_code == 200
    assert "saved" in resp.text.lower()
    assert captured["teg_num"] == 10
    assert captured["round_num"] == 1
    assert len(captured["holes"]) == 18


def test_round_setup_save_rejects_incomplete_form(client, monkeypatch):
    import teg_analysis.analysis.round_setup as rs

    def must_not_run(*a, **k):
        raise AssertionError("save_round_setup must not run on an incomplete form")

    monkeypatch.setattr(rs, "save_round_setup", must_not_run)

    _login(client)
    # Hole 5 missing -> should reject before saving.
    form = {f"par__{h}": "4" for h in range(1, 19) if h != 5}
    form.update({f"si__{h}": str(h) for h in range(1, 19) if h != 5})
    resp = client.post("/admin/round-setup/10/1/save", data=form)

    assert resp.status_code == 200
    assert "hole 5" in resp.text.lower()


# ---------------------------------------------------------------------------
# TEG setup (roster + handicap). Real data only for GET renders; save is
# always monkeypatched, so no test ever writes to the real handicaps.csv
# except in the explicitly monkeypatched save test.
# ---------------------------------------------------------------------------

def test_teg_setup_default_redirects_to_next_teg(client, monkeypatch):
    import teg_analysis.analysis.teg_setup as ts

    monkeypatch.setattr(ts, "get_next_teg", lambda: 19)

    _login(client)
    resp = client.get("/admin/teg-setup")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/teg-setup/19"


def test_teg_setup_form_confirmed_teg(client):
    _login(client)
    # TEG 18 already has a confirmed row in handicaps.csv.
    resp = client.get("/admin/teg-setup/18")
    assert resp.status_code == 200
    assert "TEG 18" in resp.text
    assert "Already confirmed" in resp.text


def test_teg_setup_form_unconfirmed_teg_does_not_error(client):
    _login(client)
    # No handicap history exists this far out -> falls back to blank, not a crash.
    resp = client.get("/admin/teg-setup/999")
    assert resp.status_code == 200
    assert "TEG 999" in resp.text


def test_teg_setup_save_writes_roster(client, monkeypatch):
    import teg_analysis.analysis.teg_setup as ts

    captured = {}

    def fake_save(teg_num, players):
        captured["teg_num"] = teg_num
        captured["players"] = players
        return {"teg_num": teg_num, "players_saved": len(players)}

    monkeypatch.setattr(ts, "save_teg_roster", fake_save)
    monkeypatch.setattr(ts, "get_roster_players", lambda: ["DM", "GW", "HM", "JB"])

    _login(client)
    form = {
        "playing__DM": "on", "handicap__DM": "18",
        "playing__GW": "on", "handicap__GW": "17",
        "handicap__HM": "",
        "playing__JB": "on", "handicap__JB": "20",
    }
    resp = client.post("/admin/teg-setup/19/save", data=form)

    assert resp.status_code == 200
    assert "saved" in resp.text.lower()
    assert captured["teg_num"] == 19
    by_code = {p["code"]: p for p in captured["players"]}
    assert by_code["DM"] == {"code": "DM", "playing": True, "handicap": "18"}
    assert by_code["HM"] == {"code": "HM", "playing": False, "handicap": None}


def test_teg_setup_save_rejects_playing_without_handicap(client, monkeypatch):
    import teg_analysis.analysis.teg_setup as ts

    def must_not_run(*a, **k):
        raise AssertionError("save_teg_roster must not run when a playing player has no handicap")

    monkeypatch.setattr(ts, "save_teg_roster", must_not_run)
    monkeypatch.setattr(ts, "get_roster_players", lambda: ["DM"])

    _login(client)
    resp = client.post("/admin/teg-setup/19/save", data={"playing__DM": "on", "handicap__DM": ""})

    assert resp.status_code == 200
    assert "dm" in resp.text.lower()


# ---------------------------------------------------------------------------
# Live round (admin lifecycle side). All live_round module calls are
# monkeypatched -- no test here writes to real data.
# ---------------------------------------------------------------------------

def test_live_round_review_requires_auth(client):
    resp = client.get("/admin/live-round/some-token/review")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/login"


def test_live_round_list_renders(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.setattr(lrmod, "list_live_rounds", lambda: [
        {"Token": "abc123", "TEGNum": 19, "Round": 1, "CreatedAt": "2026-07-08T10:00:00Z", "Status": "active"},
    ])
    import teg_analysis.analysis.round_setup as rs
    monkeypatch.setattr(rs, "get_rounds_status", lambda: [
        {"teg_num": 19, "round_num": 2, "course": "Ashdown", "date": "01/01/2027", "is_set_up": True},
        {"teg_num": 19, "round_num": 3, "course": "Ashdown", "date": "01/01/2027", "is_set_up": False},
    ])

    _login(client)
    resp = client.get("/admin/live-round")
    assert resp.status_code == 200
    assert "abc123" in resp.text
    assert "🟢" in resp.text or "Active" in resp.text
    assert ">8 Jul 2026, 10:00</time>" in resp.text  # start time, not the raw ISO stamp
    # Round 2 is set up and not live -> startable. Round 3 isn't set up -> not offered.
    assert 'value="2"' in resp.text
    assert 'value="3"' not in resp.text


def test_live_round_list_shows_entry_link_for_active_rounds_only(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.setattr(lrmod, "list_live_rounds", lambda: [
        {"Token": "livetok", "TEGNum": 19, "Round": 2, "CreatedAt": "b", "Status": "active"},
        {"Token": "donetok", "TEGNum": 19, "Round": 1, "CreatedAt": "a", "Status": "finalized"},
    ])
    import teg_analysis.analysis.round_setup as rs
    monkeypatch.setattr(rs, "get_rounds_status", lambda: [])

    _login(client)
    resp = client.get("/admin/live-round", headers={"x-forwarded-proto": "https"})
    assert resp.status_code == 200
    # Absolute, on the request's host, with the proxy's scheme.
    assert 'data-url="https://testserver/live-round/livetok"' in resp.text
    assert "Copy link" in resp.text
    assert 'data-url="https://testserver/live-round/donetok"' not in resp.text


def test_live_round_public_link_switch(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    calls = []
    monkeypatch.setattr(lrmod, "set_public_entry_enabled", lambda enabled: calls.append(enabled))

    _login(client)
    resp = client.post("/admin/live-round/public-link", data={"enabled": "on"})
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/live-round?saved=on"
    resp = client.post("/admin/live-round/public-link", data={"enabled": "off"})
    assert resp.headers["location"] == "/admin/live-round?saved=off"
    assert calls == [True, False]


def test_live_round_public_link_switch_requires_auth(client):
    resp = client.post("/admin/live-round/public-link", data={"enabled": "on"})
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/login"


def test_public_banner_shows_only_when_switched_on(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod
    from webapp import deps

    monkeypatch.setattr(lrmod, "list_live_rounds", lambda: [
        {"Token": "livetok", "TEGNum": 19, "Round": 2, "CreatedAt": "b", "Status": "active"},
    ])
    import teg_analysis.analysis.round_setup as rs
    monkeypatch.setattr(rs, "get_rounds_status", lambda: [])
    _login(client)

    monkeypatch.setattr(lrmod, "get_public_entry_enabled", lambda: False)
    deps.clear_public_round_banners_cache()
    resp = client.get("/admin/live-round")
    assert "live-entry-banner" not in resp.text
    assert "Turn on" in resp.text

    monkeypatch.setattr(lrmod, "get_public_entry_enabled", lambda: True)
    deps.clear_public_round_banners_cache()
    resp = client.get("/admin/live-round")
    assert "live-entry-banner" in resp.text
    assert 'href="/live-round/livetok"' in resp.text
    assert "TEG 19 Round 2" in resp.text
    assert "Turn off" in resp.text
    deps.clear_public_round_banners_cache()


def test_live_round_start_success(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.setattr(lrmod, "start_live_round", lambda teg_num, round_num: {
        "Token": "newtoken", "TEGNum": teg_num, "Round": round_num,
        "CreatedAt": "now", "Status": "active",
    })

    _login(client)
    resp = client.post("/admin/live-round/start", data={"teg_num": "19", "round_num": "1"})
    assert resp.status_code == 200
    # Issue 20: redirect to the review page, where the link and Copy render,
    # instead of a fragment in a row below the fold.
    assert resp.headers["HX-Redirect"] == "/admin/live-round/newtoken/review?started=1"


def test_live_round_start_second_tap_redirects_to_active_round(client, monkeypatch):
    """Issue 20 regression: a second Go live tap must lead to the live round's
    link, not replace it with an "already active" error."""
    import teg_analysis.analysis.live_round as lrmod

    def fake_start(teg_num, round_num):
        err = lrmod.LiveRoundAlreadyActiveError("already active")
        err.token = "livetok"
        raise err

    monkeypatch.setattr(lrmod, "start_live_round", fake_start)

    _login(client)
    resp = client.post("/admin/live-round/start", data={"teg_num": "19", "round_num": "1"})
    assert resp.status_code == 200
    assert resp.headers["HX-Redirect"] == "/admin/live-round/livetok/review?started=already"
    assert "already active" not in resp.text


def test_live_round_start_already_active_without_token_shows_error(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    def fake_start(teg_num, round_num):
        raise lrmod.LiveRoundAlreadyActiveError("already active")

    monkeypatch.setattr(lrmod, "start_live_round", fake_start)

    _login(client)
    resp = client.post("/admin/live-round/start", data={"teg_num": "19", "round_num": "1"})
    assert "HX-Redirect" not in resp.headers
    assert "already active" in resp.text


def test_live_round_review_after_go_live_shows_link_and_copy(client, monkeypatch):
    """Issue 20 regression: the page Go live lands on shows the full entry
    link with Copy, with no reload."""
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.setattr(lrmod, "get_live_round_context", lambda token: {
        "token": token, "teg_num": 19, "round_num": 1, "status": "active", "course": "Ashdown",
        "players": ["DM"], "player_names": {"DM": "David MULLIN"},
        "holes": [{"hole": h, "par": 4, "si": h} for h in range(1, 19)],
    })
    monkeypatch.setattr(lrmod, "get_scores_since",
                        lambda token, since_seq=0: {"seq": 0, "status": "active", "cells": []})

    _login(client)
    resp = client.get("/admin/live-round/newtoken/review?started=1")
    assert resp.status_code == 200
    assert "ready for scores" in resp.text
    assert "/live-round/newtoken" in resp.text
    assert "Copy link" in resp.text


def test_live_round_start_rejects_unconfirmed_pars(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    def fake_start(teg_num, round_num):
        raise lrmod.RoundParsNotConfirmedError("not confirmed yet")

    monkeypatch.setattr(lrmod, "start_live_round", fake_start)

    _login(client)
    resp = client.post("/admin/live-round/start", data={"teg_num": "19", "round_num": "1"})
    assert resp.status_code == 200
    assert "not confirmed yet" in resp.text


def test_live_round_review_shows_conflicts_and_progress(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.setattr(lrmod, "get_live_round_context", lambda token: {
        "token": token, "teg_num": 19, "round_num": 1, "status": "active", "course": "Ashdown",
        "players": ["DM", "GW"], "player_names": {"DM": "David MULLIN", "GW": "Gregg WILLIAMS"},
        "holes": [{"hole": h, "par": 4, "si": h} for h in range(1, 19)],
    })
    monkeypatch.setattr(lrmod, "get_scores_since", lambda token, since_seq=0: {
        "seq": 3, "status": "active", "cells": [
            {"hole": 1, "player": "DM", "value": 4, "conflict": False, "device_name": "Jon", "prev_value": None, "prev_device_name": None},
            {"hole": 2, "player": "DM", "value": 5, "conflict": True, "device_name": "Dave", "prev_value": 4, "prev_device_name": "Jon"},
        ],
    })

    _login(client)
    resp = client.get("/admin/live-round/tok123/review")
    assert resp.status_code == 200
    assert "David MULLIN" in resp.text
    assert "1 cell" in resp.text or "disagree" in resp.text
    assert "disabled" in resp.text  # Finalize disabled while a conflict remains


def _fake_review_ctx(monkeypatch, status):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.setattr(lrmod, "get_live_round_context", lambda token: {
        "token": token, "teg_num": 19, "round_num": 1, "status": status, "course": "Ashdown",
        "players": ["DM"], "player_names": {"DM": "David MULLIN"},
        "holes": [{"hole": h, "par": 4, "si": h} for h in range(1, 19)],
    })
    monkeypatch.setattr(lrmod, "get_scores_since", lambda token, since_seq=0: {
        "seq": 0, "status": status, "cells": [],
    })


def test_live_round_review_shows_entry_link_when_active(client, monkeypatch):
    _fake_review_ctx(monkeypatch, "active")
    _login(client)
    resp = client.get("/admin/live-round/tok123/review")
    assert resp.status_code == 200
    assert 'data-url="http://testserver/live-round/tok123"' in resp.text
    assert "Copy link" in resp.text


def test_live_round_review_hides_entry_link_when_finalized(client, monkeypatch):
    _fake_review_ctx(monkeypatch, "finalized")
    _login(client)
    resp = client.get("/admin/live-round/tok123/review")
    assert resp.status_code == 200
    assert "Copy link" not in resp.text


def test_live_round_resolve(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    captured = {}
    def fake_resolve(token, hole, player, chosen_value, resolved_by):
        captured.update(token=token, hole=hole, player=player, chosen_value=chosen_value)

    monkeypatch.setattr(lrmod, "resolve_conflict", fake_resolve)

    _login(client)
    resp = client.post("/admin/live-round/tok123/resolve", data={"hole": "2", "player": "DM", "chosen_value": "5"})
    assert resp.status_code == 200
    assert captured == {"token": "tok123", "hole": 2, "player": "DM", "chosen_value": 5}
    assert "confirmed" in resp.text.lower()


@pytest.fixture
def finalize_store(tmp_path, monkeypatch):
    """Keep finalise status files out of the real store."""
    from webapp import finalize_jobs
    monkeypatch.setattr(finalize_jobs, "_store_path", lambda rel: tmp_path / rel)
    return finalize_jobs


def _fake_finalize(monkeypatch, calls=None, **extra):
    import teg_analysis.analysis.live_round as lrmod
    from webapp import deps

    def fake(token, progress=None):
        if calls is not None:
            calls.append(token)
        return {"token": token, "teg_num": 19, "round_num": 1, "records_added": 18,
                "committed": True, **extra}
    monkeypatch.setattr(lrmod, "finalize_live_round", fake)
    monkeypatch.setattr(deps, "clear_all_data_caches", lambda: None)


def test_live_round_finalize_starts_job_then_redirects(client, monkeypatch, finalize_store):
    calls = []
    _fake_finalize(monkeypatch, calls)

    _login(client)
    resp = client.post("/admin/live-round/tok123/finalize")
    assert resp.status_code == 200
    assert "finalize-status" in resp.text  # progress partial, polling itself
    assert "HX-Redirect" not in resp.headers
    assert calls == ["tok123"]  # TestClient ran the background task

    resp = client.get("/admin/live-round/tok123/finalize-status")
    assert resp.status_code == 200
    assert resp.text == ""
    assert resp.headers["HX-Redirect"] == "/admin/live-round/tok123/review?finalized=1"


def test_live_round_finalize_status_passes_cache_errors(client, monkeypatch, finalize_store):
    _fake_finalize(monkeypatch, cache_errors=[{"step": "streaks", "error": "x"}, {"step": "records", "error": "y"}])
    _login(client)
    client.post("/admin/live-round/tok123/finalize")
    resp = client.get("/admin/live-round/tok123/finalize-status")
    assert resp.headers["HX-Redirect"] == "/admin/live-round/tok123/review?finalized=1&cache_errors=streaks%2Crecords"


def test_live_round_finalize_while_active_shows_note_and_starts_nothing(client, monkeypatch, finalize_store):
    calls = []
    _fake_finalize(monkeypatch, calls)
    finalize_store.claim("tok123")  # a run is already in flight

    _login(client)
    resp = client.post("/admin/live-round/tok123/finalize")
    assert resp.status_code == 200
    assert "Already finalising" in resp.text
    assert "finalize-status" in resp.text
    assert calls == []
    assert finalize_store.read_status("tok123")["state"] == "queued"


def test_live_round_finalize_blocked_by_conflicts(client, monkeypatch, finalize_store):
    import teg_analysis.analysis.live_round as lrmod

    def fake_finalize(token, progress=None):
        raise lrmod.ConflictsUnresolvedError("Resolve every conflicted cell before finalizing this round.")

    monkeypatch.setattr(lrmod, "finalize_live_round", fake_finalize)

    _login(client)
    assert client.post("/admin/live-round/tok123/finalize").status_code == 200
    resp = client.get("/admin/live-round/tok123/finalize-status")
    assert resp.status_code == 200
    assert "HX-Redirect" not in resp.headers
    assert "resolve every conflicted cell" in resp.text.lower()


def test_live_round_finalize_status_without_run(client, finalize_store):
    _login(client)
    resp = client.get("/admin/live-round/tok123/finalize-status")
    assert resp.status_code == 200
    assert "No finalise run found" in resp.text


def test_live_round_finalize_status_requires_auth(client, finalize_store):
    resp = client.get("/admin/live-round/tok123/finalize-status")
    assert resp.headers.get("HX-Redirect") == "/admin/login"  # htmx ignores a 401, so redirect


def test_review_resumes_active_finalize(client, monkeypatch, finalize_store):
    _review_setup(monkeypatch, "active")
    finalize_store.claim("tok123")
    _login(client)
    resp = client.get("/admin/live-round/tok123/review")
    assert resp.status_code == 200
    assert "/admin/live-round/tok123/finalize-status" in resp.text


def test_review_shows_failed_finalize_error(client, monkeypatch, finalize_store):
    _review_setup(monkeypatch, "active")
    finalize_store.claim("tok123")
    finalize_store.write_status("tok123", state="error", error="Finalize failed: push failed")
    _login(client)
    resp = client.get("/admin/live-round/tok123/review")
    assert "Finalize failed: push failed" in resp.text
    assert "/finalize-status" not in resp.text


def test_live_round_cancel(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.setattr(lrmod, "cancel_live_round", lambda token: {"token": token, "status": "cancelled"})

    _login(client)
    resp = client.post("/admin/live-round/tok123/cancel")
    assert resp.status_code == 200
    assert resp.text == ""
    assert resp.headers["HX-Redirect"] == "/admin/live-round/tok123/review?cancelled=1"


def _review_setup(monkeypatch, status="active"):
    import teg_analysis.analysis.live_round as lrmod
    import teg_analysis.analysis.teg_setup as ts

    _fake_review_ctx(monkeypatch, status)
    monkeypatch.setattr(lrmod, "get_scores_since", lambda token, since_seq=0: {
        "seq": 1, "status": status, "cells": [
            {"hole": 1, "player": "DM", "value": 4, "conflict": False, "device_name": "Jon",
             "prev_value": None, "prev_device_name": None},
        ],
    })
    monkeypatch.setattr(ts, "get_teg_roster_form", lambda teg_num: {"source": "confirmed"})


def test_random_fill_requires_auth(client):
    resp = client.post("/admin/live-round/tok123/random-fill")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/login"


@pytest.mark.parametrize("var", ["RAILWAY_ENVIRONMENT_NAME", "RAILWAY_ENVIRONMENT"])
def test_random_fill_forbidden_on_production(client, monkeypatch, var):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.setenv(var, "production")
    calls = []
    monkeypatch.setattr(lrmod, "fill_random_scores", lambda token, rng=None: calls.append(token), raising=False)

    _login(client)
    resp = client.post("/admin/live-round/tok123/random-fill")
    assert resp.status_code == 403
    assert calls == []


@pytest.mark.parametrize("env", ["pr-150", None])
def test_random_fill_runs_off_production(client, monkeypatch, env):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    if env:
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", env)
    calls = []

    def fake_fill(token, rng=None):
        calls.append(token)
        return {"written": 7}

    monkeypatch.setattr(lrmod, "fill_random_scores", fake_fill, raising=False)

    _login(client)
    resp = client.post("/admin/live-round/tok123/random-fill")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/live-round/tok123/review?saved=7"
    assert calls == ["tok123"]


def test_random_fill_inactive_round_redirects_with_error(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)

    def fake_fill(token, rng=None):
        raise lrmod.LiveRoundInactiveError("Round is not active.")

    monkeypatch.setattr(lrmod, "fill_random_scores", fake_fill, raising=False)
    _login(client)
    resp = client.post("/admin/live-round/tok123/random-fill")
    assert resp.status_code == 303
    assert "?error=Round%20is%20not%20active." in resp.headers["location"]


def test_review_random_fill_button_visibility(client, monkeypatch):
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    _review_setup(monkeypatch, "active")
    _login(client)

    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "pr-150")
    resp = client.get("/admin/live-round/tok123/review")
    assert "/admin/live-round/tok123/random-fill" in resp.text
    assert "Fill empty cells with random scores" in resp.text

    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    resp = client.get("/admin/live-round/tok123/review")
    assert "random-fill" not in resp.text
    assert "name=\"score-1-DM\"" in resp.text  # still editable


def test_review_finalized_is_read_only(client, monkeypatch):
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "pr-150")
    import teg_analysis.analysis.live_round as lrmod
    _review_setup(monkeypatch, "finalized")
    monkeypatch.setattr(lrmod, "report_readiness", lambda t, r=None: {
        "ready": True, "state": "ready", "reason": None, "token": None, "round": None})
    _login(client)
    resp = client.get("/admin/live-round/tok123/review")
    assert resp.status_code == 200
    assert 'name="score-' not in resp.text
    assert "/finalize" not in resp.text
    assert "/cancel" not in resp.text
    assert "random-fill" not in resp.text
    assert "Round finalised" in resp.text
    assert "TEG 19 Round 1 is in the permanent record" in resp.text
    assert "/admin/reports?teg=19&amp;round=1" in resp.text or "/admin/reports?teg=19&round=1" in resp.text
    assert 'href="/leaderboard"' in resp.text
    assert "stale data" not in resp.text
    assert "Finalised." not in resp.text


def test_review_finalized_query_flags(client, monkeypatch):
    _review_setup(monkeypatch, "finalized")
    _login(client)
    resp = client.get("/admin/live-round/tok123/review?finalized=1&cache_errors=streaks,records")
    assert "Finalised." in resp.text
    assert "stale data" in resp.text
    assert "<strong>streaks</strong>" in resp.text
    assert "<strong>records</strong>" in resp.text


def test_review_cancelled_is_read_only(client, monkeypatch):
    _review_setup(monkeypatch, "cancelled")
    _login(client)
    resp = client.get("/admin/live-round/tok123/review?cancelled=1")
    assert 'name="score-' not in resp.text
    assert "Nothing was written to the permanent record" in resp.text
    assert 'href="/admin/live-round"' in resp.text


def test_reports_page_renders(client):
    _login(client)
    resp = client.get("/admin/reports")
    assert resp.status_code == 200
    assert "Generate round report" in resp.text
    assert "Generate tournament report" in resp.text


def test_reports_generate_enqueues_and_guards_double_run(client, monkeypatch, tmp_path):
    import webapp.report_generation as report_generation
    from webapp import deps

    # Status files land under tmp_path instead of the real store.
    monkeypatch.setattr(report_generation, "_store_path",
                        lambda rel: tmp_path / rel)

    calls = []
    monkeypatch.setattr(report_generation, "generate_report",
                        lambda teg, round_num: calls.append((teg, round_num)))

    teg = deps.get_default_teg_num()
    rounds = deps.get_rounds_for_teg(teg)
    round_num = rounds[-1] if rounds else 1

    _login(client)
    resp = client.post("/admin/reports/generate",
                       data={"kind": "round", "teg": teg, "round": round_num})
    assert resp.status_code == 200
    assert len(calls) == 1

    status = report_generation.read_status(teg, round_num)
    assert status is not None

    # A second request while the first looks "active" is refused, not enqueued
    # again — generate_report ran synchronously above (TestClient runs
    # BackgroundTasks inline) and left state "queued", since our stub never
    # writes "running"/"done" itself.
    resp2 = client.post("/admin/reports/generate",
                        data={"kind": "round", "teg": teg, "round": round_num})
    assert resp2.status_code == 200
    assert "already generating" in resp2.text.lower()
    assert len(calls) == 1


def _iso_ago(hours=0.0, minutes=0.0):
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(hours=hours, minutes=minutes)).isoformat()


def _report_env(client, monkeypatch, tmp_path):
    import webapp.report_generation as rg
    from webapp import deps
    monkeypatch.setattr(rg, "_store_path", lambda rel: tmp_path / rel)
    calls = []
    monkeypatch.setattr(rg, "generate_report", lambda t, r: calls.append((t, r)))
    teg = deps.get_default_teg_num()
    rounds = deps.get_rounds_for_teg(teg)
    round_num = rounds[-1] if rounds else 1
    _login(client)
    return rg, calls, teg, round_num


def test_running_panel_lists_all_active_runs(client, monkeypatch, tmp_path):
    from webapp import deps
    import webapp.report_generation as rg
    monkeypatch.setattr(rg, "_store_path", lambda rel: tmp_path / rel)
    _login(client)
    rg.write_status(3, 1, state="running", phase="draft", started_at=_iso_ago(minutes=5))
    rg.write_status(4, None, state="running", phase="voice", started_at=_iso_ago(minutes=2))

    other = [t for t in deps.get_available_teg_numbers() if t not in (3, 4)][0]
    for url in (f"/admin/reports?teg={other}", "/admin/reports/running"):
        resp = client.get(url)
        assert resp.status_code == 200
        assert "TEG 3 R1" in resp.text and "TEG 4 tournament" in resp.text
        assert "in progress" in resp.text and "to do" in resp.text
        assert 'hx-trigger="load delay:3s"' in resp.text

    # Nothing active: no polling element.
    rg.write_status(3, 1, state="error", phase="draft", started_at=_iso_ago(minutes=5),
                    finished_at=_iso_ago(minutes=1), error="boom")
    rg.write_status(4, None, state="done", phase="push", started_at=_iso_ago(minutes=5),
                    finished_at=_iso_ago(minutes=1))
    resp = client.get("/admin/reports/running")
    assert 'hx-trigger="load delay:3s"' not in resp.text
    assert "boom" in resp.text


def test_running_panel_empty(client, monkeypatch, tmp_path):
    _report_env(client, monkeypatch, tmp_path)
    resp = client.get("/admin/reports/running")
    assert "No reports running" in resp.text
    assert 'hx-trigger="load delay:3s"' not in resp.text


def test_running_endpoint_requires_auth(client):
    resp = client.get("/admin/reports/running")
    assert resp.status_code == 401


def test_recent_report_needs_confirmation(client, monkeypatch, tmp_path):
    rg, calls, teg, round_num = _report_env(client, monkeypatch, tmp_path)
    rg.write_status(teg, round_num, state="done", phase="push",
                    started_at=_iso_ago(hours=1, minutes=5), finished_at=_iso_ago(hours=1))
    before = rg.read_status(teg, round_num)
    data = {"kind": "round", "teg": teg, "round": round_num}

    resp = client.post("/admin/reports/generate", data=data)
    assert resp.status_code == 200
    assert "Regenerate anyway" in resp.text
    assert calls == []
    assert rg.read_status(teg, round_num) == before

    resp = client.post("/admin/reports/generate", data={**data, "confirm": 1})
    assert resp.status_code == 200
    assert len(calls) == 1
    assert resp.headers.get("HX-Trigger") == "report-started"


def test_old_report_regenerates_without_confirmation(client, monkeypatch, tmp_path):
    rg, calls, teg, round_num = _report_env(client, monkeypatch, tmp_path)
    rg.write_status(teg, round_num, state="done", phase="push",
                    started_at=_iso_ago(hours=7, minutes=5), finished_at=_iso_ago(hours=7))
    resp = client.post("/admin/reports/generate",
                       data={"kind": "round", "teg": teg, "round": round_num})
    assert "Regenerate anyway" not in resp.text
    assert len(calls) == 1


def test_running_report_confirmation_has_phase_and_no_regenerate(client, monkeypatch, tmp_path):
    rg, calls, teg, round_num = _report_env(client, monkeypatch, tmp_path)
    rg.write_status(teg, round_num, state="running", phase="voice", started_at=_iso_ago(minutes=3))
    resp = client.post("/admin/reports/generate",
                       data={"kind": "round", "teg": teg, "round": round_num})
    assert "already generating" in resp.text.lower()
    assert "Voice pass" in resp.text
    assert "Regenerate anyway" not in resp.text
    assert calls == []


def test_generate_rejects_tournament_for_in_progress_teg(client, monkeypatch, tmp_path):
    import webapp.report_generation as report_generation
    from webapp import deps

    monkeypatch.setattr(report_generation, "_store_path", lambda rel: tmp_path / rel)

    teg = deps.get_default_teg_num()
    monkeypatch.setattr(deps, "get_current_in_progress_teg_fast", lambda: (teg, 1))

    calls = []
    monkeypatch.setattr(report_generation, "generate_report",
                        lambda t, r: calls.append((t, r)))

    _login(client)
    resp = client.post("/admin/reports/generate", data={"kind": "tournament", "teg": teg})
    assert resp.status_code == 200
    assert "still in progress" in resp.text.lower()
    assert calls == []
    assert report_generation.read_status(teg, None) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


def test_progress_partial_shows_step_header_and_checklist(client, monkeypatch, finalize_store):
    from teg_analysis.analysis.live_round import FINALIZE_STEPS
    finalize_store.claim("tok123")
    finalize_store.write_status("tok123", state="running", step="scores",
                                steps={"validate": {"state": "done", "error": None},
                                       "backup": {"state": "done", "error": None},
                                       "scores": {"state": "running", "error": None}})
    _login(client)
    resp = client.get("/admin/live-round/tok123/finalize-status")
    assert f"Step 3 of {len(FINALIZE_STEPS)}: {FINALIZE_STEPS[2][1]}" in resp.text
    assert "fin-spin" in resp.text
    assert FINALIZE_STEPS[-1][1] in resp.text  # to-do steps are listed too


def test_error_partial_shows_failed_step_and_not_run(client, finalize_store):
    finalize_store.claim("tok123")
    finalize_store.write_status("tok123", state="error", error="Finalize failed: disk full",
                                steps={"validate": {"state": "done", "error": None},
                                       "scores": {"state": "failed", "error": "disk full"}})
    _login(client)
    resp = client.get("/admin/live-round/tok123/finalize-status")
    assert "disk full" in resp.text
    assert "(not run)" in resp.text
    assert "Failed." in resp.text


def test_finalised_review_shows_next_steps_checklist_and_gates_report(client, monkeypatch, finalize_store):
    import teg_analysis.analysis.live_round as lrmod
    _fake_review_ctx(monkeypatch, "finalized")
    finalize_store.write_status("tok123", state="done", committed=True, cache_errors=["streaks"],
                                steps={"streaks": {"state": "failed", "error": "bad streaks"}})
    monkeypatch.setattr(lrmod, "report_readiness", lambda t, r=None: {
        "ready": True, "state": "ready", "reason": None, "token": None, "round": None})
    _login(client)
    resp = client.get("/admin/live-round/tok123/review?finalized=1")
    assert "What happens next" in resp.text
    assert "everything went in one commit" in resp.text
    assert "Report PDFs aren't built automatically" in resp.text
    assert "bad streaks" in resp.text
    assert "Generate round report" in resp.text and "/admin/reports?teg=19" in resp.text

    monkeypatch.setattr(lrmod, "report_readiness", lambda t, r=None: {
        "ready": False, "state": "failed", "reason": "Round 1 finalise failed at scores.",
        "token": "tok123", "round": 1})
    resp = client.get("/admin/live-round/tok123/review?finalized=1")
    assert "Round 1 finalise failed at scores." in resp.text
    assert "/admin/reports?teg=19" not in resp.text


def test_finalised_review_local_run_message(client, monkeypatch, finalize_store):
    import teg_analysis.analysis.live_round as lrmod
    _fake_review_ctx(monkeypatch, "finalized")
    finalize_store.write_status("tok123", state="done", committed=False)
    monkeypatch.setattr(lrmod, "report_readiness", lambda t, r=None: {
        "ready": True, "state": "ready", "reason": None, "token": None, "round": None})
    _login(client)
    resp = client.get("/admin/live-round/tok123/review?finalized=1")
    assert "Local run: nothing was sent to GitHub." in resp.text
