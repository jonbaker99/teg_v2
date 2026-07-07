"""Unit tests for teg_analysis.analysis.round_setup (pre-round Par/SI setup).

teg_analysis.io.read_file/write_file are monkeypatched -- these tests never
touch real data files.
"""

import pandas as pd
import pytest

from teg_analysis.analysis import round_setup
from teg_analysis.constants import ROUND_INFO_CSV, COURSE_PARS_CSV, ROUND_PARS_CSV, ALL_SCORES_PARQUET


def _round_info():
    return pd.DataFrame(
        [
            {"TEGNum": 10, "Round": 1, "Course": "Ashdown", "Date": "01/01/2017"},
            {"TEGNum": 7, "Round": 1, "Course": "Praia D'El Rey", "Date": "02/10/2014"},
        ]
    )


def _course_pars():
    rows = []
    for h in range(1, 19):
        rows.append({"Course": "Ashdown", "Hole": h, "Par": 4, "SI": h})
    return pd.DataFrame(rows)


def _empty_all_scores():
    return pd.DataFrame(columns=["TEGNum", "Round", "Hole", "PAR", "SI"])


def _fake_read_file(path):
    if path == ROUND_INFO_CSV:
        return _round_info()
    if path == COURSE_PARS_CSV:
        return _course_pars()
    if path == ROUND_PARS_CSV:
        raise FileNotFoundError(path)
    if path == ALL_SCORES_PARQUET:
        return _empty_all_scores()
    raise AssertionError(f"unexpected read_file call: {path}")


def test_get_rounds_status_reports_setup_state(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _fake_read_file)

    rows = round_setup.get_rounds_status()
    assert len(rows) == 2
    assert all(r["is_set_up"] is False for r in rows)
    # Newest TEG first.
    assert rows[0]["teg_num"] == 10


def test_get_rounds_status_excludes_already_played_rounds(monkeypatch):
    """A round with scores already in all-scores.parquet has nothing to set up."""
    import teg_analysis.io as tio

    def read_file(path):
        if path == ALL_SCORES_PARQUET:
            return pd.DataFrame([{"TEGNum": 10, "Round": 1, "Hole": 1, "PAR": 4, "SI": 1}])
        return _fake_read_file(path)

    monkeypatch.setattr(tio, "read_file", read_file)

    rows = round_setup.get_rounds_status()
    assert len(rows) == 1
    assert rows[0]["teg_num"] == 7


def test_get_round_setup_form_prefills_from_course_pars(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _fake_read_file)

    form = round_setup.get_round_setup_form(10, 1)
    assert form["course"] == "Ashdown"
    assert form["source"] == "course_default"
    assert form["flagged"] is False
    assert len(form["holes"]) == 18
    assert form["holes"][0] == {"hole": 1, "par": 4, "si": 1}


def test_get_round_setup_form_flags_known_variable_routing(monkeypatch):
    import teg_analysis.io as tio

    def read_file(path):
        if path == ROUND_INFO_CSV:
            return _round_info()
        if path == COURSE_PARS_CSV:
            return pd.DataFrame(columns=["Course", "Hole", "Par", "SI"])
        raise FileNotFoundError(path)

    monkeypatch.setattr(tio, "read_file", read_file)

    form = round_setup.get_round_setup_form(7, 1)
    assert form["course"] == "Praia D'El Rey"
    assert form["flagged"] is True
    assert "back-9-first" in form["flag_note"]
    assert form["source"] == "blank"
    assert form["holes"][0] == {"hole": 1, "par": "", "si": ""}


def test_get_round_setup_form_prefers_confirmed_round_pars(monkeypatch):
    import teg_analysis.io as tio

    confirmed = pd.DataFrame(
        [{"TEGNum": 10, "Round": 1, "Hole": h, "Par": 5, "SI": h} for h in range(1, 19)]
    )

    def read_file(path):
        if path == ROUND_INFO_CSV:
            return _round_info()
        if path == ROUND_PARS_CSV:
            return confirmed
        if path == COURSE_PARS_CSV:
            return _course_pars()
        raise FileNotFoundError(path)

    monkeypatch.setattr(tio, "read_file", read_file)

    form = round_setup.get_round_setup_form(10, 1)
    assert form["source"] == "confirmed"
    assert form["holes"][0] == {"hole": 1, "par": 5, "si": 1}


def test_get_round_setup_form_unknown_round_raises(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _fake_read_file)

    with pytest.raises(ValueError):
        round_setup.get_round_setup_form(99, 1)


def test_save_round_setup_writes_18_rows(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", lambda path: (_ for _ in ()).throw(FileNotFoundError(path)))

    captured = {}

    def fake_write_file(path, df, msg, **kwargs):
        captured["path"] = path
        captured["df"] = df.copy()

    monkeypatch.setattr(tio, "write_file", fake_write_file)

    holes = [{"hole": h, "par": 4, "si": h} for h in range(1, 19)]
    result = round_setup.save_round_setup(10, 1, holes)

    assert result == {"teg_num": 10, "round_num": 1, "holes_saved": 18}
    assert captured["path"] == ROUND_PARS_CSV
    df = captured["df"]
    assert len(df) == 18
    assert set(df["TEGNum"]) == {10}
    assert set(df["Round"]) == {1}
    assert sorted(df["Hole"].tolist()) == list(range(1, 19))


def test_save_round_setup_replaces_existing_rows_for_same_round(monkeypatch):
    import teg_analysis.io as tio

    existing = pd.concat(
        [
            pd.DataFrame([{"TEGNum": 10, "Round": 1, "Hole": h, "Par": 3, "SI": h} for h in range(1, 19)]),
            pd.DataFrame([{"TEGNum": 11, "Round": 2, "Hole": h, "Par": 4, "SI": h} for h in range(1, 19)]),
        ],
        ignore_index=True,
    )
    monkeypatch.setattr(tio, "read_file", lambda path: existing)

    captured = {}

    def fake_write_file(path, df, msg, **kwargs):
        captured["df"] = df.copy()

    monkeypatch.setattr(tio, "write_file", fake_write_file)

    holes = [{"hole": h, "par": 5, "si": h} for h in range(1, 19)]
    round_setup.save_round_setup(10, 1, holes)

    df = captured["df"]
    # Other round's rows untouched, this round's rows replaced (Par now 5, not 3).
    assert len(df) == 36
    teg10 = df[(df["TEGNum"] == 10) & (df["Round"] == 1)]
    assert (teg10["Par"] == 5).all()
    teg11 = df[(df["TEGNum"] == 11) & (df["Round"] == 2)]
    assert (teg11["Par"] == 4).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
