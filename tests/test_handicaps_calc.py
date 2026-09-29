"""Regression tests for the handicap calculation (issue 14).

A player with a handicap for only one of the two TEGs feeding ``get_hc`` used
to give a NaN in the pivot and crash ``.astype(int)``. They must now be
excluded (with a warning) instead of breaking the page.
"""

import pandas as pd

from teg_analysis.analysis import handicaps as hmod


def _patch_sources(monkeypatch, hc_rows, stab_rows):
    """hc_rows: (TEG, Pl, HC); stab_rows: (Pl, TEGNum, Stableford)."""
    hc_long = pd.DataFrame(hc_rows, columns=["TEG", "Pl", "HC"])
    stab = pd.DataFrame(stab_rows, columns=["Pl", "TEGNum", "Stableford"])
    num_rounds = pd.DataFrame(
        {"TEGNum": sorted(set(stab["TEGNum"])), "num_rounds": 4}
    )
    monkeypatch.setattr(hmod, "load_and_prepare_handicap_data", lambda path: hc_long.copy())
    monkeypatch.setattr(hmod, "load_all_data", lambda **kw: pd.DataFrame())
    monkeypatch.setattr(hmod, "get_teg_data_inc_in_progress", lambda: stab.copy())
    monkeypatch.setattr(hmod, "get_number_of_completed_rounds_by_teg", lambda df: num_rounds.copy())


def _hc_rows_with_gap():
    # SN has TEG 18 but no TEG 19 (e.g. a 0 that the loader dropped).
    return [
        ("TEG 18", "DM", 20), ("TEG 18", "SN", 27),
        ("TEG 19", "DM", 19),
    ]


def test_get_hc_excludes_player_missing_one_teg(monkeypatch, caplog):
    _patch_sources(
        monkeypatch,
        _hc_rows_with_gap(),
        [("DM", 18, 144), ("DM", 19, 144)],  # 36 pts/round -> AdjGross == HC
    )
    with caplog.at_level("WARNING"):
        result = hmod.get_hc(20)

    assert list(result["Pl"]) == ["DM"]
    assert result.loc[0, "hc"] == round(0.75 * 19 + 0.25 * 20)
    assert "SN" in caplog.text


def test_get_hc_excludes_player_missing_older_teg(monkeypatch):
    rows = [("TEG 19", "DM", 19), ("TEG 19", "JB", 21), ("TEG 18", "DM", 20)]
    _patch_sources(monkeypatch, rows, [("DM", 18, 144), ("DM", 19, 144)])
    result = hmod.get_hc(20)
    assert list(result["Pl"]) == ["DM"]


def test_get_hc_missing_pivot_column_returns_empty(monkeypatch):
    # No handicap rows at all for TEG N-2.
    rows = [("TEG 19", "DM", 19)]
    _patch_sources(monkeypatch, rows, [("DM", 19, 144)])
    result = hmod.get_hc(20)
    assert result.empty
    assert list(result.columns) == ["Pl", "hc_raw", "hc"]


def test_get_current_handicaps_formatted_survives_missing_player(monkeypatch):
    hc_rows = _hc_rows_with_gap()
    _patch_sources(monkeypatch, hc_rows, [("DM", 18, 144), ("DM", 19, 144)])
    monkeypatch.setattr(hmod, "get_player_name", lambda code: code)

    table, calculated = hmod.get_current_handicaps_formatted(19, 20)

    assert calculated is True
    assert list(table["Handicap"]) == ["DM"]
    assert table["TEG 20"].dtype.kind == "i"


def test_get_current_handicaps_formatted_lists_only_roster_players(monkeypatch):
    # SN sits TEG 19 out but keeps a saved 27 (36-point rule); the TEG 19
    # handicap list must still leave SN out when the roster says so.
    from teg_analysis.analysis import teg_setup

    rows = [("TEG 18", "DM", 20), ("TEG 18", "SN", 27),
            ("TEG 19", "DM", 19), ("TEG 19", "SN", 27)]
    _patch_sources(monkeypatch, rows, [("DM", 18, 144)])
    monkeypatch.setattr(hmod, "get_player_name", lambda code: code)
    monkeypatch.setattr(teg_setup, "playing_codes", lambda teg: {"DM"} if teg == 19 else None)

    table, calculated = hmod.get_current_handicaps_formatted(18, 19)

    assert calculated is False
    assert list(table["Handicap"]) == ["DM"]
