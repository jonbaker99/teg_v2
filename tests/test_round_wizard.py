"""Unit tests for teg_analysis.analysis.round_wizard (guided setup orchestration).

teg_analysis.io.read_file/write_file are monkeypatched -- these tests never
touch real data files.
"""

import pandas as pd
import pytest

from teg_analysis.analysis import round_wizard
from teg_analysis.constants import (
    ROUND_INFO_CSV, COURSE_PARS_CSV, ROUND_PARS_CSV, ALL_SCORES_PARQUET,
    HANDICAPS_CSV, LIVE_ROUNDS_REGISTRY_CSV, PLAYERS_CSV,
)

FUTURE_TEGS_CSV = round_wizard.FUTURE_TEGS_CSV


_ROUND_INFO_COLUMNS = ["TEGNum", "Round", "Course", "Date", "TEGRd", "TEG", "Area", "Year"]


def _round_info(rows=None):
    if rows is None:
        rows = [
            {"TEGNum": 18, "Round": 1, "Course": "Boavista", "Date": "01/05/2025",
             "TEGRd": "TEG 18|1", "TEG": "TEG 18", "Area": "Algarve, Portugal", "Year": 2025},
        ]
    if not rows:
        # Real read_file(round_info.csv) still returns the header's columns
        # even for a TEG with zero rows -- a bare pd.DataFrame([]) wouldn't.
        return pd.DataFrame(columns=_ROUND_INFO_COLUMNS)
    return pd.DataFrame(rows)


def _course_pars():
    return pd.DataFrame([{"Course": "Boavista", "Hole": h, "Par": 4, "SI": h} for h in range(1, 19)])


def _handicaps(teg_str, **players):
    row = {"TEG": teg_str}
    row.update(players)
    return pd.DataFrame([row])


def _all_scores(rows=None):
    return pd.DataFrame(rows or [], columns=["TEGNum", "Round", "Hole"])


def _live_registry(rows=None):
    return pd.DataFrame(
        rows or [], columns=["Token", "TEGNum", "Round", "CreatedAt", "Status"]
    )


def _default_files(overrides: dict | None = None) -> dict:
    """Base fixture set (path -> DataFrame, or None for FileNotFoundError),
    keyed by the real constants so `read_file(path)` lookups match."""
    files = {
        ROUND_INFO_CSV: _round_info(),
        COURSE_PARS_CSV: _course_pars(),
        ROUND_PARS_CSV: None,
        ALL_SCORES_PARQUET: _all_scores(),
        HANDICAPS_CSV: _handicaps("TEG 18", DM=20, GW=18),
        LIVE_ROUNDS_REGISTRY_CSV: None,
        FUTURE_TEGS_CSV: None,
        # Player identity falls back to the PLAYER_DICT seed when missing.
        PLAYERS_CSV: None,
    }
    if overrides:
        files.update(overrides)
    return files


def _make_read_file(files: dict):
    def read_file(path):
        if path not in files:
            raise AssertionError(f"unexpected read_file call: {path}")
        val = files[path]
        if val is None:
            raise FileNotFoundError(path)
        return val

    return read_file


# ---------------------------------------------------------------- status ----

def test_status_fresh_teg_starts_at_metadata(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files({
        HANDICAPS_CSV: _handicaps("TEG 19", DM=20, GW=18),  # roster confirmed for TEG 19
    })))

    status = round_wizard.get_wizard_status(19, 1)
    assert status["already_played"] is False
    assert status["current"] == "metadata"
    by_key = {s["key"]: s for s in status["steps"]}
    assert by_key["metadata"]["done"] is False
    assert by_key["roster"]["done"] is True  # TEG 19's roster already confirmed
    assert by_key["parsi"]["locked"] is True  # needs metadata's course first
    assert by_key["golive"]["locked"] is True


def test_status_new_round_in_existing_teg_skips_confirmed_roster(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files()))

    # TEG 18 Round 2: TEG 18's roster is already confirmed (HANDICAPS_CSV default).
    status = round_wizard.get_wizard_status(18, 2)
    by_key = {s["key"]: s for s in status["steps"]}
    assert by_key["roster"]["done"] is True
    assert status["current"] == "metadata"  # Round 2's own metadata still needed


def test_status_ready_to_go_live(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files({
        ROUND_PARS_CSV: pd.DataFrame([{"TEGNum": 18, "Round": 1, "Hole": h, "Par": 4, "SI": h} for h in range(1, 19)]),
    })))

    status = round_wizard.get_wizard_status(18, 1)
    assert status["ready_to_go_live"] is True
    assert status["current"] == "golive"
    assert status["live"] is None


def test_status_active_live_round_is_done(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files({
        ROUND_PARS_CSV: pd.DataFrame([{"TEGNum": 18, "Round": 1, "Hole": h, "Par": 4, "SI": h} for h in range(1, 19)]),
        LIVE_ROUNDS_REGISTRY_CSV: _live_registry([
            {"Token": "abc123", "TEGNum": 18, "Round": 1, "CreatedAt": "2025-05-01", "Status": "active"},
        ]),
    })))

    status = round_wizard.get_wizard_status(18, 1)
    by_key = {s["key"]: s for s in status["steps"]}
    assert by_key["golive"]["done"] is True
    assert status["live"] == {"token": "abc123", "status": "active"}


def test_status_cancelled_live_round_reopens_golive_step(monkeypatch):
    """A cancelled live round must not be reported as done -- the admin should
    be able to go live again, not get stuck on a dead link (regression for a
    bug where any registry row, including cancelled ones, counted as done)."""
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files({
        ROUND_PARS_CSV: pd.DataFrame([{"TEGNum": 18, "Round": 1, "Hole": h, "Par": 4, "SI": h} for h in range(1, 19)]),
        LIVE_ROUNDS_REGISTRY_CSV: _live_registry([
            {"Token": "abc123", "TEGNum": 18, "Round": 1, "CreatedAt": "2025-05-01", "Status": "cancelled"},
        ]),
    })))

    status = round_wizard.get_wizard_status(18, 1)
    by_key = {s["key"]: s for s in status["steps"]}
    assert by_key["golive"]["done"] is False
    assert status["current"] == "golive"  # not done, not locked -> still the target step
    assert status["ready_to_go_live"] is True  # so the UI can offer "Go live" again
    # The stale registry row is still surfaced (for messaging), just not "done".
    assert status["live"] == {"token": "abc123", "status": "cancelled"}


def test_status_already_played_round_short_circuits(monkeypatch):
    """A round with scores already in all-scores.parquet has nothing left to
    set up -- the wizard shouldn't walk the admin toward re-confirming Par/SI."""
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files({
        ALL_SCORES_PARQUET: _all_scores([{"TEGNum": 18, "Round": 1, "Hole": 1}]),
    })))

    status = round_wizard.get_wizard_status(18, 1)
    assert status["already_played"] is True
    assert status["steps"] == []
    assert status["current"] == "played"
    assert status["ready_to_go_live"] is False
    assert status["live"] is None


# --------------------------------------------------------- metadata form ----

def test_metadata_form_prefills_from_existing_row(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files()))

    form = round_wizard.get_round_metadata_form(18, 1)
    assert form["exists"] is True
    assert form["course"] == "Boavista"
    assert form["area"] == "Algarve, Portugal"
    assert form["year"] == "2025"


def test_metadata_form_inherits_area_year_from_sibling_round(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files()))

    # Round 2 doesn't exist yet, but Round 1 of the same TEG does.
    form = round_wizard.get_round_metadata_form(18, 2)
    assert form["exists"] is False
    assert form["course"] == ""
    assert form["area"] == "Algarve, Portugal"
    assert form["year"] == "2025"


def test_metadata_form_falls_back_to_future_tegs(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files({
        FUTURE_TEGS_CSV: pd.DataFrame([{"TEGNum": 19, "Area": "Costa Brava, Spain", "Year": 2026}]),
    })))

    form = round_wizard.get_round_metadata_form(19, 1)
    assert form["exists"] is False
    assert form["area"] == "Costa Brava, Spain"
    assert form["year"] == "2026"


# ------------------------------------------------------------- save form ----

def test_save_round_metadata_derives_columns_and_upserts(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files()))

    captured = {}

    def fake_write_file(path, df, msg, **kwargs):
        captured["path"] = path
        captured["df"] = df.copy()

    monkeypatch.setattr(tio, "write_file", fake_write_file)

    result = round_wizard.save_round_metadata(18, 2, "Estoril", "15/05/2025")

    assert result == {"teg_num": 18, "round_num": 2, "course": "Estoril", "area": "Algarve, Portugal", "year": "2025"}
    assert captured["path"] == ROUND_INFO_CSV
    df = captured["df"]
    assert len(df) == 2  # original Round 1 row + new Round 2 row
    new_row = df[(df["TEGNum"] == 18) & (df["Round"] == 2)].iloc[0]
    assert new_row["TEGRd"] == "TEG 18|2"
    assert new_row["TEG"] == "TEG 18"
    assert new_row["Area"] == "Algarve, Portugal"
    assert new_row["Year"] == "2025"


def test_save_round_metadata_replaces_existing_row_not_duplicates(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files()))

    captured = {}
    monkeypatch.setattr(tio, "write_file", lambda path, df, msg, **kw: captured.update(df=df.copy()))

    round_wizard.save_round_metadata(18, 1, "Boavista (corrected)", "02/05/2025")

    df = captured["df"]
    assert len(df) == 1  # replaced in place, not appended
    assert df.iloc[0]["Course"] == "Boavista (corrected)"


def test_save_round_metadata_year_falls_back_to_date(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files({
        ROUND_INFO_CSV: _round_info([]),  # no sibling rows to inherit from
    })))

    captured = {}
    monkeypatch.setattr(tio, "write_file", lambda path, df, msg, **kw: captured.update(df=df.copy()))

    result = round_wizard.save_round_metadata(20, 1, "Ashdown", "10/06/2027")
    assert result["area"] == ""
    assert result["year"] == "2027"


def test_save_round_metadata_requires_course_and_date(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file(_default_files()))

    with pytest.raises(ValueError):
        round_wizard.save_round_metadata(18, 2, "", "01/01/2025")
    with pytest.raises(ValueError):
        round_wizard.save_round_metadata(18, 2, "Ashdown", "")


# ---------------------------------------------------------------- misc ------

def test_get_course_options_dedupes_and_sorts(monkeypatch):
    import teg_analysis.io as tio

    monkeypatch.setattr(tio, "read_file", _make_read_file({
        COURSE_PARS_CSV: pd.DataFrame([{"Course": "Estoril"}, {"Course": "Ashdown"}, {"Course": "Ashdown"}]),
    }))

    assert round_wizard.get_course_options() == ["Ashdown", "Estoril"]


def test_suggest_next_target_falls_back_on_error(monkeypatch):
    import teg_analysis.analysis.teg_setup as teg_setup_mod

    def raise_error():
        raise RuntimeError("no history")

    monkeypatch.setattr(teg_setup_mod, "get_next_teg", raise_error)

    assert round_wizard.suggest_next_target() == {"teg_num": 1, "round_num": 1}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
