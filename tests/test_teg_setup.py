"""Unit tests for teg_analysis.analysis.teg_setup (TEG roster + handicap setup).

teg_analysis.io.read_file/write_file are monkeypatched -- these tests never
touch real data files.
"""

import pandas as pd
import pytest

from teg_analysis.analysis import teg_setup
from teg_analysis.constants import HANDICAPS_CSV

ROSTERS = teg_setup.TEG_ROSTERS_CSV


def _reader(rosters=None, handicaps=None):
    """Fake read_file: handicaps.csv, and teg_rosters.csv (absent if None)."""

    def read(path):
        if path == ROSTERS:
            if rosters is None:
                raise FileNotFoundError(path)
            return rosters.copy()
        return (handicaps if handicaps is not None else _handicaps()).copy()

    return read


def _capture_writes(monkeypatch, captured):
    import teg_analysis.io as tio

    def fake_write_file(path, df, msg="", **kwargs):
        captured[path] = df.copy()

    monkeypatch.setattr(tio, "write_file", fake_write_file)


def _calc(monkeypatch, values):
    """Stub get_hc; values maps code -> calculated handicap (None = raise)."""
    import teg_analysis.analysis.handicaps as handicaps_mod

    def fake(teg_needed):
        if values is None:
            raise KeyError("not enough history")
        return pd.DataFrame([{"Pl": k, "hc_raw": v, "hc": v} for k, v in values.items()])

    monkeypatch.setattr(handicaps_mod, "get_hc", fake)


def _no_calc(monkeypatch):
    _calc(monkeypatch, None)


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

    monkeypatch.setattr(tio, "read_file", _reader())
    _capture_writes(monkeypatch, captured)
    _no_calc(monkeypatch)

    players = [
        {"code": "DM", "playing": True, "handicap": "21"},
        {"code": "GW", "playing": False, "handicap": ""},
        {"code": "HM", "playing": True, "handicap": "16"},
        {"code": "JB", "playing": True, "handicap": "20"},
    ]
    result = teg_setup.save_teg_roster(18, players)

    assert result == {"teg_num": 18, "players_saved": 4}
    df = captured[HANDICAPS_CSV]
    # Row count unchanged -- TEG 18 was replaced in place, not appended.
    assert len(df) == 2
    row = df[df["TEG"] == "TEG 18"].iloc[0]
    assert row["DM"] == 21
    assert pd.isna(row["GW"])  # not playing, nothing to calculate -> blank, never 0
    assert row["HM"] == 16
    assert row["JB"] == 20
    # TEG 17's row is untouched.
    row17 = df[df["TEG"] == "TEG 17"].iloc[0]
    assert row17["DM"] == 20


def test_save_teg_roster_appends_new_row_for_new_teg(monkeypatch):
    import teg_analysis.io as tio

    captured = {}
    monkeypatch.setattr(tio, "read_file", _reader())
    _capture_writes(monkeypatch, captured)
    _no_calc(monkeypatch)

    players = [
        {"code": "DM", "playing": True, "handicap": "18"},
        {"code": "GW", "playing": True, "handicap": "17"},
        {"code": "HM", "playing": False, "handicap": None},
        {"code": "JB", "playing": True, "handicap": "19"},
    ]
    teg_setup.save_teg_roster(19, players)

    df = captured[HANDICAPS_CSV]
    assert len(df) == 3
    row = df[df["TEG"] == "TEG 19"].iloc[0]
    assert row["DM"] == 18
    assert pd.isna(row["HM"])  # not playing, nothing to calculate -> blank, never 0


def test_save_non_player_gets_calculated_handicap_never_zero(monkeypatch):
    import teg_analysis.io as tio

    captured = {}
    monkeypatch.setattr(tio, "read_file", _reader())
    _capture_writes(monkeypatch, captured)
    _calc(monkeypatch, {"GW": 17})

    teg_setup.save_teg_roster(
        19,
        [
            {"code": "DM", "playing": True, "handicap": "18"},
            {"code": "GW", "playing": False, "handicap": ""},
        ],
    )
    row = captured[HANDICAPS_CSV].query("TEG == 'TEG 19'").iloc[0]
    assert row["GW"] == 17
    assert row["DM"] == 18


def test_save_non_player_keeps_given_handicap(monkeypatch):
    import teg_analysis.io as tio

    captured = {}
    monkeypatch.setattr(tio, "read_file", _reader())
    _capture_writes(monkeypatch, captured)
    _calc(monkeypatch, {"GW": 17})

    teg_setup.save_teg_roster(
        19,
        [
            {"code": "DM", "playing": True, "handicap": "18"},
            {"code": "GW", "playing": False, "handicap": "27"},
        ],
    )
    row = captured[HANDICAPS_CSV].query("TEG == 'TEG 19'").iloc[0]
    assert row["GW"] == 27


def test_save_writes_roster_flags_replacing_this_teg_only(monkeypatch):
    import teg_analysis.io as tio

    existing = pd.DataFrame(
        [
            {"TEGNum": 18, "Pl": "DM", "Playing": True},
            {"TEGNum": 19, "Pl": "DM", "Playing": False},
            {"TEGNum": 19, "Pl": "OLD", "Playing": True},
        ]
    )
    captured = {}
    monkeypatch.setattr(tio, "read_file", _reader(rosters=existing))
    _capture_writes(monkeypatch, captured)
    _no_calc(monkeypatch)

    teg_setup.save_teg_roster(
        19,
        [
            {"code": "DM", "playing": True, "handicap": "18"},
            {"code": "GW", "playing": False, "handicap": ""},
        ],
    )
    r = captured[ROSTERS]
    assert list(r.columns) == ["TEGNum", "Pl", "Playing"]
    t18 = r[r["TEGNum"] == 18]
    assert list(t18["Pl"]) == ["DM"]
    t19 = r[r["TEGNum"] == 19].set_index("Pl")["Playing"].to_dict()
    assert t19 == {"DM": True, "GW": False}  # OLD dropped, DM flipped


def test_save_creates_roster_file_when_absent(monkeypatch):
    import teg_analysis.io as tio

    captured = {}
    monkeypatch.setattr(tio, "read_file", _reader())  # no rosters file
    _capture_writes(monkeypatch, captured)
    _no_calc(monkeypatch)

    teg_setup.save_teg_roster(19, [{"code": "DM", "playing": True, "handicap": "18"}])
    assert captured[ROSTERS].to_dict("records") == [{"TEGNum": 19, "Pl": "DM", "Playing": True}]


def test_form_roster_file_overrides_bool_of_handicap(monkeypatch):
    import teg_analysis.io as tio

    handicaps = pd.DataFrame(
        [{"TEG": "TEG 19", "DM": 19, "GW": 27, "HM": None, "JB": 21}]
    )
    rosters = pd.DataFrame(
        [
            {"TEGNum": 19, "Pl": "DM", "Playing": True},
            {"TEGNum": 19, "Pl": "GW", "Playing": False},  # has a saved hc, not playing
            {"TEGNum": 19, "Pl": "HM", "Playing": False},
        ]
    )
    monkeypatch.setattr(tio, "read_file", _reader(rosters=rosters, handicaps=handicaps))

    form = teg_setup.get_teg_roster_form(19)
    by = {p["code"]: p for p in form["players"]}
    assert form["source"] == "confirmed"
    assert by["DM"]["playing"] is True and by["DM"]["handicap"] == 19
    assert by["GW"]["playing"] is False and by["GW"]["handicap"] == 27
    assert by["HM"]["playing"] is False and by["HM"]["handicap"] is None
    assert by["JB"]["playing"] is False  # absent from roster file -> not playing


def test_form_legacy_fallback_when_roster_file_absent(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _reader())  # raises for rosters
    by = {p["code"]: p for p in teg_setup.get_teg_roster_form(18)["players"]}
    assert by["DM"]["playing"] is True
    assert by["GW"]["playing"] is False  # legacy: cell 0 -> not playing


def test_form_legacy_fallback_when_roster_file_has_no_rows_for_teg(monkeypatch):
    import teg_analysis.io as tio

    rosters = pd.DataFrame([{"TEGNum": 19, "Pl": "DM", "Playing": True}])
    monkeypatch.setattr(tio, "read_file", _reader(rosters=rosters))
    by = {p["code"]: p for p in teg_setup.get_teg_roster_form(18)["players"]}
    assert by["DM"]["playing"] is True
    assert by["GW"]["playing"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
