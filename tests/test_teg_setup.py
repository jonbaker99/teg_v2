"""Unit tests for teg_analysis.analysis.teg_setup (TEG roster + handicap setup).

teg_analysis.io.read_file/write_file are monkeypatched -- these tests never
touch real data files.
"""

import pandas as pd
import pytest

from teg_analysis.analysis import teg_setup
from teg_analysis.constants import HANDICAPS_CSV


def _handicaps():
    return pd.DataFrame(
        [
            {"TEG": "TEG 17", "DM": 20, "GW": 18, "HM": 0, "JB": 22},
            {"TEG": "TEG 18", "DM": 19, "GW": 0, "HM": 15, "JB": 21},
        ]
    )


def test_get_roster_players_handicaps_columns_first_then_new_players(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", lambda path: _handicaps())

    # handicaps.csv column order first (stable), then every other known player
    # (here the PLAYER_DICT seed, since the monkeypatched read gives players.csv
    # no usable rows) so a newly added player is offerable before they have a
    # handicaps column.
    roster = teg_setup.get_roster_players()
    assert roster[:4] == ["DM", "GW", "HM", "JB"]
    assert set(roster[4:]) == {"AB", "SN", "JP", "GP"}
    assert len(roster) == len(set(roster))


def test_get_teg_roster_form_uses_confirmed_row(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", lambda path: _handicaps())

    form = teg_setup.get_teg_roster_form(18)
    assert form["source"] == "confirmed"
    by_code = {p["code"]: p for p in form["players"]}
    assert by_code["DM"] == {"code": "DM", "name": "David MULLIN", "playing": True, "handicap": 19, "source": "confirmed"}
    # GW's cell is 0 -> not playing, but the raw value is still surfaced.
    assert by_code["GW"]["playing"] is False
    assert by_code["GW"]["handicap"] == 0
    assert by_code["GW"]["source"] == "confirmed"


def test_get_teg_roster_form_falls_back_to_calculated(monkeypatch):
    import teg_analysis.io as tio
    import teg_analysis.analysis.handicaps as handicaps_mod

    monkeypatch.setattr(tio, "read_file", lambda path: _handicaps())
    monkeypatch.setattr(
        handicaps_mod,
        "get_hc",
        lambda teg_needed: pd.DataFrame([{"Pl": "DM", "hc_raw": 18.4, "hc": 18}, {"Pl": "GW", "hc_raw": 16.2, "hc": 16}]),
    )

    form = teg_setup.get_teg_roster_form(19)
    assert form["source"] == "calculated"
    by_code = {p["code"]: p for p in form["players"]}
    assert by_code["DM"] == {"code": "DM", "name": "David MULLIN", "playing": True, "handicap": 18, "source": "calculated"}
    # HM/JB have no calculated value -> blank, not playing.
    assert by_code["HM"] == {"code": "HM", "name": "Henry MELLER", "playing": False, "handicap": None, "source": "blank"}


def test_get_teg_roster_form_handles_calculation_errors(monkeypatch):
    import teg_analysis.io as tio
    import teg_analysis.analysis.handicaps as handicaps_mod

    monkeypatch.setattr(tio, "read_file", lambda path: _handicaps())

    def raise_error(teg_needed):
        raise KeyError("not enough history")

    monkeypatch.setattr(handicaps_mod, "get_hc", raise_error)

    form = teg_setup.get_teg_roster_form(19)
    assert form["source"] == "blank"
    assert all(p["playing"] is False for p in form["players"])


def test_save_teg_roster_replaces_existing_row_in_place(monkeypatch):
    import teg_analysis.io as tio

    captured = {}

    monkeypatch.setattr(tio, "read_file", lambda path: _handicaps())

    def fake_write_file(path, df, msg, **kwargs):
        captured["path"] = path
        captured["df"] = df.copy()

    monkeypatch.setattr(tio, "write_file", fake_write_file)

    players = [
        {"code": "DM", "playing": True, "handicap": "21"},
        {"code": "GW", "playing": False, "handicap": ""},
        {"code": "HM", "playing": True, "handicap": "16"},
        {"code": "JB", "playing": True, "handicap": "20"},
    ]
    result = teg_setup.save_teg_roster(18, players)

    assert result == {"teg_num": 18, "players_saved": 4}
    assert captured["path"] == HANDICAPS_CSV
    df = captured["df"]
    # Row count unchanged -- TEG 18 was replaced in place, not appended.
    assert len(df) == 2
    row = df[df["TEG"] == "TEG 18"].iloc[0]
    assert row["DM"] == 21
    assert row["GW"] == 0  # not playing -> 0
    assert row["HM"] == 16
    assert row["JB"] == 20
    # TEG 17's row is untouched.
    row17 = df[df["TEG"] == "TEG 17"].iloc[0]
    assert row17["DM"] == 20


def test_save_teg_roster_appends_new_row_for_new_teg(monkeypatch):
    import teg_analysis.io as tio

    captured = {}
    monkeypatch.setattr(tio, "read_file", lambda path: _handicaps())

    def fake_write_file(path, df, msg, **kwargs):
        captured["df"] = df.copy()

    monkeypatch.setattr(tio, "write_file", fake_write_file)

    players = [
        {"code": "DM", "playing": True, "handicap": "18"},
        {"code": "GW", "playing": True, "handicap": "17"},
        {"code": "HM", "playing": False, "handicap": None},
        {"code": "JB", "playing": True, "handicap": "19"},
    ]
    teg_setup.save_teg_roster(19, players)

    df = captured["df"]
    assert len(df) == 3
    row = df[df["TEG"] == "TEG 19"].iloc[0]
    assert row["DM"] == 18
    assert row["HM"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
