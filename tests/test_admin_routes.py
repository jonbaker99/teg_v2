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
    "/admin/teg-setup", "/admin/live-round",
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
    # Round 2 is set up and not live -> startable. Round 3 isn't set up -> not offered.
    assert 'value="2"' in resp.text
    assert 'value="3"' not in resp.text


def test_live_round_start_success(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.setattr(lrmod, "start_live_round", lambda teg_num, round_num: {
        "Token": "newtoken", "TEGNum": teg_num, "Round": round_num,
        "CreatedAt": "now", "Status": "active",
    })

    _login(client)
    resp = client.post("/admin/live-round/start", data={"teg_num": "19", "round_num": "1"})
    assert resp.status_code == 200
    assert "newtoken" in resp.text
    assert "/live-round/newtoken" in resp.text


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


def test_live_round_finalize_success(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.setattr(lrmod, "finalize_live_round", lambda token: {
        "token": token, "teg_num": 19, "round_num": 1, "records_added": 18,
        "changed_rounds": {}, "backups": [], "committed": True, "files_committed": 1,
    })

    _login(client)
    resp = client.post("/admin/live-round/tok123/finalize")
    assert resp.status_code == 200
    assert "finalized" in resp.text.lower()


def test_live_round_finalize_blocked_by_conflicts(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    def fake_finalize(token):
        raise lrmod.ConflictsUnresolvedError("Resolve every conflicted cell before finalizing this round.")

    monkeypatch.setattr(lrmod, "finalize_live_round", fake_finalize)

    _login(client)
    resp = client.post("/admin/live-round/tok123/finalize")
    assert resp.status_code == 200
    assert "resolve every conflicted cell" in resp.text.lower()


def test_live_round_cancel(client, monkeypatch):
    import teg_analysis.analysis.live_round as lrmod

    monkeypatch.setattr(lrmod, "cancel_live_round", lambda token: {"token": token, "status": "cancelled"})

    _login(client)
    resp = client.post("/admin/live-round/tok123/cancel")
    assert resp.status_code == 200
    assert "cancelled" in resp.text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
