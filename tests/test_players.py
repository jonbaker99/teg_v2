"""Tests for teg_analysis.core.players (player identity: players.csv).

Unit tests monkeypatch teg_analysis.io; the end-to-end test at the bottom
drives the real "Add a new player" admin flow over HTTP against a scratch
copy of data/ (same pattern as test_live_round_e2e.py) and proves the new
player is rosterable, scoreable under their own name, and visible site-wide.
"""

import shutil
from pathlib import Path

import pandas as pd
import pytest
from starlette.testclient import TestClient

import teg_analysis.io.volume_operations as volume_operations
from teg_analysis.core import players
from teg_analysis.constants import PLAYERS_CSV, PLAYER_DICT
from webapp.app import app


# ---------------------------------------------------------------------------
# Unit: get_player_dict / add_player against a fake io layer
# ---------------------------------------------------------------------------

def _players_df():
    return pd.DataFrame(
        [
            {"Code": "DM", "Name": "David MULLIN"},
            {"Code": "ZZ", "Name": "Zed ZEDDER"},
        ]
    )


def test_get_player_dict_merges_file_over_seed(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", lambda path: _players_df())

    d = players.get_player_dict()
    assert d["ZZ"] == "Zed ZEDDER"          # file-only player present
    assert d["DM"] == "David MULLIN"        # file order wins for shared codes
    assert d["GW"] == "Gregg WILLIAMS"      # seed players still present
    # File players come first (order drives roster/selector display).
    assert list(d)[:2] == ["DM", "ZZ"]


def test_get_player_dict_falls_back_to_seed_when_file_missing(monkeypatch):
    import teg_analysis.io as tio

    def raise_missing(path):
        raise FileNotFoundError(path)

    monkeypatch.setattr(tio, "read_file", raise_missing)

    assert players.get_player_dict() == PLAYER_DICT


def test_get_name_to_code_and_get_player_name(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", lambda path: _players_df())

    assert players.get_name_to_code()["Zed ZEDDER"] == "ZZ"
    assert players.get_player_name("zz") == "Zed ZEDDER"
    assert players.get_player_name("XX") == "Unknown Player"


def test_add_player_validates_and_seeds_full_roster(monkeypatch):
    import teg_analysis.io as tio

    captured = {}

    def raise_missing(path):
        raise FileNotFoundError(path)

    def fake_write(path, df, msg, **kwargs):
        captured["path"] = path
        captured["df"] = df.copy()

    monkeypatch.setattr(tio, "read_file", raise_missing)
    monkeypatch.setattr(tio, "write_file", fake_write)

    result = players.add_player(" js ", "  John   Smith ")
    assert result == {"code": "JS", "name": "John Smith"}
    assert captured["path"] == PLAYERS_CSV
    # First write seeds the whole current roster, so the file is the complete
    # source of truth from then on, not a delta on top of constants.
    codes = set(captured["df"]["Code"])
    assert codes == set(PLAYER_DICT) | {"JS"}


@pytest.mark.parametrize(
    "code,name",
    [
        ("J", "Too Short"),        # 1-letter code
        ("JSXX", "Too Long"),      # 4-letter code
        ("J2", "Not Letters"),     # digit in code
        ("JS", ""),                # blank name
        ("JB", "Someone New"),     # code already taken (seed)
        ("XX", "Jon BAKER"),       # name already taken (case-insensitive)
    ],
)
def test_add_player_rejects_bad_input(monkeypatch, code, name):
    import teg_analysis.io as tio

    def raise_missing(path):
        raise FileNotFoundError(path)

    monkeypatch.setattr(tio, "read_file", raise_missing)
    monkeypatch.setattr(tio, "write_file", lambda *a, **k: pytest.fail("must not write"))

    with pytest.raises(players.PlayerError):
        players.add_player(code, name)


def test_cache_invalidation_on_add(monkeypatch):
    import teg_analysis.io as tio

    store = {"df": pd.DataFrame(columns=["Code", "Name"])}
    monkeypatch.setattr(tio, "read_file", lambda path: store["df"].copy())

    def fake_write(path, df, msg, **kwargs):
        store["df"] = df.copy()

    monkeypatch.setattr(tio, "write_file", fake_write)

    assert "QQ" not in players.get_player_dict()  # populates the cache
    players.add_player("QQ", "Quentin QUAIL")
    assert players.get_player_dict()["QQ"] == "Quentin QUAIL"  # cache was cleared


# ---------------------------------------------------------------------------
# End-to-end: add a player via the admin page, roster them, score them
# ---------------------------------------------------------------------------

@pytest.fixture
def scratch_repo(tmp_path, monkeypatch):
    real_data = Path(__file__).resolve().parent.parent / "data"
    shutil.copytree(real_data, tmp_path / "data")
    monkeypatch.setattr(volume_operations, "_REPO_ROOT", tmp_path)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    return tmp_path


@pytest.fixture
def admin(scratch_repo, monkeypatch):
    monkeypatch.setenv("WEBAPP_ADMIN_PASSWORD", "secret123")
    client = TestClient(app, follow_redirects=False)
    resp = client.post("/admin/login", data={"password": "secret123"})
    assert resp.status_code == 303
    return client


def test_add_player_end_to_end(admin, scratch_repo):
    # Add John SMITH (JS) from the TEG setup page.
    resp = admin.post(
        "/admin/teg-setup/19/add-player",
        data={"new_code": "js", "new_name": "John SMITH"},
    )
    assert resp.status_code == 303
    assert "added=JS" in resp.headers["location"]

    # players.csv in the scratch repo now holds the full roster + JS.
    saved = pd.read_csv(scratch_repo / "data" / "players.csv")
    assert "JS" in set(saved["Code"])
    assert len(saved) >= len(PLAYER_DICT) + 1

    # The roster form now offers JS, unticked, name resolved.
    page = admin.get("/admin/teg-setup/19")
    assert page.status_code == 200
    assert "John SMITH" in page.text
    assert 'name="playing__JS"' in page.text

    # Duplicate add bounces with an error, not a 500.
    dupe = admin.post(
        "/admin/teg-setup/19/add-player",
        data={"new_code": "JS", "new_name": "Different Name"},
    )
    assert dupe.status_code == 303
    assert "add_error=" in dupe.headers["location"]

    # Saving the roster with JS playing creates their handicaps.csv column.
    form_data = {"playing__JS": "on", "handicap__JS": "24"}
    save = admin.post("/admin/teg-setup/19/save", data=form_data)
    assert save.status_code == 200
    hc = pd.read_csv(scratch_repo / "data" / "handicaps.csv")
    assert "JS" in hc.columns
    assert int(hc[hc["TEG"] == "TEG 19"].iloc[0]["JS"]) == 24

    # And the scoring pipeline maps their name (not 'Unknown Player').
    from teg_analysis.analysis.data_update import process_round_for_all_scores

    long_df = pd.DataFrame(
        [{"TEGNum": 19, "Round": 1, "Hole": 1, "Par": 4, "SI": 1, "Pl": "JS", "Score": 5}]
    )
    hc_long = pd.DataFrame([{"TEG": "TEG 19", "Pl": "JS", "HC": 24}])
    processed = process_round_for_all_scores(long_df, hc_long)
    assert processed.iloc[0]["Player"] == "John SMITH"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
