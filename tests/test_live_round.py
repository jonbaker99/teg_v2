"""Unit tests for teg_analysis.analysis.live_round (multi-device score sync).

teg_analysis.io.read_file/write_file are monkeypatched to an in-memory dict
store -- these tests never touch real data files. round_setup/teg_setup/
data_update are monkeypatched at their own module boundary, matching the
deferred-import pattern live_round.py itself uses.
"""

import pandas as pd
import pytest

from teg_analysis.analysis import live_round as lr


@pytest.fixture
def store(monkeypatch):
    """In-memory {path: DataFrame} store standing in for the volume/GitHub.

    Round-trips every write through a real CSV encode/decode (matching what
    read_file/write_file actually do against a file) rather than just storing
    the DataFrame object as-is -- a None written into a cell comes back as
    NaN (a float) after a real CSV round-trip, not None, and that distinction
    is exactly what caused a real bug (get_scores_since passing a NaN
    prev_device_name straight into a JSONResponse, which rejects NaN
    outright). An in-memory-only fake would never have caught it.
    """
    import io
    data = {}

    def fake_read_file(path):
        if path not in data:
            raise FileNotFoundError(path)
        return data[path].copy()

    def fake_write_file(path, df, msg, defer_github=False, **kwargs):
        data[path] = pd.read_csv(io.StringIO(df.to_csv(index=False)))

    import teg_analysis.io as tio
    monkeypatch.setattr(tio, "read_file", fake_read_file)
    monkeypatch.setattr(tio, "write_file", fake_write_file)
    return data


@pytest.fixture(autouse=True)
def confirmed_round_setup(monkeypatch):
    """start_live_round requires confirmed Par/SI -- default every test to that."""
    import teg_analysis.analysis.round_setup as rs

    def fake_form(teg_num, round_num):
        return {
            "teg_num": teg_num, "round_num": round_num, "course": "Ashdown",
            "source": "confirmed", "flagged": False, "flag_note": None,
            "holes": [{"hole": h, "par": 4, "si": h} for h in range(1, 19)],
        }

    monkeypatch.setattr(rs, "get_round_setup_form", fake_form)
    return fake_form


@pytest.fixture(autouse=True)
def playing_roster(monkeypatch):
    """apply_score_writes/apply_admin_edits validate the player against the
    TEG's playing roster -- default every test to DM and GW playing, matching
    the player codes every existing test's cells already use. Override
    per-test via monkeypatch.setattr(ts, "get_teg_roster_form", ...) same as
    confirmed_round_setup does for round_setup."""
    import teg_analysis.analysis.teg_setup as ts

    def fake_roster(teg_num):
        return {
            "teg_num": teg_num, "source": "confirmed",
            "players": [
                {"code": "DM", "name": "David MULLIN", "playing": True, "handicap": 18, "source": "confirmed"},
                {"code": "GW", "name": "Gregg WILLIAMS", "playing": True, "handicap": 16, "source": "confirmed"},
            ],
        }

    monkeypatch.setattr(ts, "get_teg_roster_form", fake_roster)
    return fake_roster


def test_start_live_round_creates_token_and_empty_staging(store):
    row = lr.start_live_round(10, 1)
    assert row["TEGNum"] == 10 and row["Round"] == 1 and row["Status"] == "active"
    assert row["Token"]

    reg = store[lr.LIVE_ROUNDS_REGISTRY_CSV]
    assert len(reg) == 1
    staging = store[f"data/live_rounds/{row['Token']}.csv"]
    assert staging.empty


def test_start_live_round_rejects_unconfirmed_pars(store, monkeypatch):
    import teg_analysis.analysis.round_setup as rs
    monkeypatch.setattr(rs, "get_round_setup_form", lambda t, r: {
        "teg_num": t, "round_num": r, "course": "Ashdown", "source": "blank",
        "flagged": False, "flag_note": None, "holes": [],
    })
    with pytest.raises(lr.RoundParsNotConfirmedError):
        lr.start_live_round(10, 1)


def test_start_live_round_rejects_duplicate_active(store):
    lr.start_live_round(10, 1)
    with pytest.raises(lr.LiveRoundAlreadyActiveError):
        lr.start_live_round(10, 1)


def test_apply_score_writes_basic(store):
    row = lr.start_live_round(10, 1)
    token = row["Token"]

    result = lr.apply_score_writes(token, "dev-A", "Jon's phone", [
        {"hole": 1, "player": "DM", "value": 4},
        {"hole": 1, "player": "GW", "value": 5},
    ])
    assert result["seq"] == 2

    polled = lr.get_scores_since(token, since_seq=0)
    assert polled["seq"] == 2
    assert polled["status"] == "active"
    by_key = {(c["hole"], c["player"]): c for c in polled["cells"]}
    assert by_key[(1, "DM")]["value"] == 4
    assert by_key[(1, "GW")]["value"] == 5
    assert not by_key[(1, "DM")]["conflict"]


def test_apply_score_writes_rejects_hole_out_of_range(store):
    row = lr.start_live_round(10, 1)
    token = row["Token"]

    with pytest.raises(lr.InvalidScoreCellError) as exc_info:
        lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 19, "player": "DM", "value": 4}])
    assert exc_info.value.errors[0]["hole"] == 19

    # Rejected outright -- nothing written, not even the valid cells in the
    # same batch (a partial write would still be an unreviewed data change).
    polled = lr.get_scores_since(token, since_seq=0)
    assert polled["cells"] == []


def test_apply_score_writes_rejects_value_out_of_range(store):
    row = lr.start_live_round(10, 1)
    token = row["Token"]

    with pytest.raises(lr.InvalidScoreCellError) as exc_info:
        lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 1, "player": "DM", "value": 21}])
    assert exc_info.value.errors[0]["value"] == 21

    with pytest.raises(lr.InvalidScoreCellError):
        lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 1, "player": "DM", "value": 0}])


def test_apply_score_writes_rejects_player_not_on_roster(store):
    row = lr.start_live_round(10, 1)
    token = row["Token"]

    with pytest.raises(lr.InvalidScoreCellError) as exc_info:
        lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 1, "player": "ZZ", "value": 4}])
    assert exc_info.value.errors[0]["player"] == "ZZ"


def test_apply_score_writes_null_value_still_valid(store):
    """None clears a cell -- it must not be rejected as an out-of-range value."""
    row = lr.start_live_round(10, 1)
    token = row["Token"]

    lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 1, "player": "DM", "value": 4}])
    result = lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 1, "player": "DM", "value": None}])
    assert result["seq"] == 2

    cell = lr.get_scores_since(token, 0)["cells"][0]
    assert cell["value"] is None


def test_apply_score_writes_valid_batch_still_writes(store):
    row = lr.start_live_round(10, 1)
    token = row["Token"]

    result = lr.apply_score_writes(token, "dev-A", "Jon", [
        {"hole": 1, "player": "DM", "value": 4},
        {"hole": 2, "player": "GW", "value": 20},  # MAX_SCORE itself is valid
    ])
    assert result["seq"] == 2

    polled = lr.get_scores_since(token, 0)
    assert len(polled["cells"]) == 2


def test_apply_score_writes_unknown_token_raises(store):
    with pytest.raises(lr.LiveRoundNotFoundError):
        lr.apply_score_writes("nope", "dev-A", "Jon", [{"hole": 1, "player": "DM", "value": 4}])


def test_get_scores_since_only_returns_changed_rows(store):
    row = lr.start_live_round(10, 1)
    token = row["Token"]
    lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 1, "player": "DM", "value": 4}])
    seq1 = lr.get_scores_since(token, 0)["seq"]

    lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 2, "player": "DM", "value": 3}])
    polled = lr.get_scores_since(token, since_seq=seq1)
    assert len(polled["cells"]) == 1
    assert polled["cells"][0]["hole"] == 2


def test_same_device_overwrite_is_not_a_conflict(store):
    row = lr.start_live_round(10, 1)
    token = row["Token"]
    lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 1, "player": "DM", "value": 4}])
    lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 1, "player": "DM", "value": 5}])

    polled = lr.get_scores_since(token, 0)
    cell = polled["cells"][0]
    assert cell["value"] == 5
    assert not cell["conflict"]


def test_different_device_different_value_flags_conflict(store):
    row = lr.start_live_round(10, 1)
    token = row["Token"]
    lr.apply_score_writes(token, "dev-A", "Jon's phone", [{"hole": 1, "player": "DM", "value": 4}])
    lr.apply_score_writes(token, "dev-B", "Dave's phone", [{"hole": 1, "player": "DM", "value": 5}])

    polled = lr.get_scores_since(token, 0)
    cell = polled["cells"][0]
    assert cell["value"] == 5  # latest write still applies -- entry is never blocked
    assert cell["conflict"] is True
    assert cell["prev_value"] == 4
    assert cell["prev_device_name"] == "Jon's phone"


def test_conflict_flag_persists_until_explicitly_resolved(store):
    row = lr.start_live_round(10, 1)
    token = row["Token"]
    lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 1, "player": "DM", "value": 4}])
    lr.apply_score_writes(token, "dev-B", "Dave", [{"hole": 1, "player": "DM", "value": 5}])
    # A third write with a matching value must NOT silently clear the flag.
    lr.apply_score_writes(token, "dev-C", "Alex", [{"hole": 1, "player": "DM", "value": 5}])

    cell = lr.get_scores_since(token, 0)["cells"][0]
    assert cell["conflict"] is True


def test_apply_admin_edits_rejects_invalid_cells(store):
    row = lr.start_live_round(10, 1)
    token = row["Token"]

    with pytest.raises(lr.InvalidScoreCellError):
        lr.apply_admin_edits(token, [{"hole": 0, "player": "DM", "value": 4}], resolved_by="Admin")
    with pytest.raises(lr.InvalidScoreCellError):
        lr.apply_admin_edits(token, [{"hole": 1, "player": "DM", "value": 99}], resolved_by="Admin")
    with pytest.raises(lr.InvalidScoreCellError):
        lr.apply_admin_edits(token, [{"hole": 1, "player": "ZZ", "value": 4}], resolved_by="Admin")

    # Nothing from any rejected batch made it into staging.
    polled = lr.get_scores_since(token, since_seq=0)
    assert polled["cells"] == []


def test_apply_admin_edits_valid_batch_still_writes(store):
    row = lr.start_live_round(10, 1)
    token = row["Token"]

    result = lr.apply_admin_edits(token, [{"hole": 1, "player": "DM", "value": 5}], resolved_by="Admin")
    assert result["written"] == 1

    cell = lr.get_scores_since(token, 0)["cells"][0]
    assert cell["value"] == 5


def test_resolve_conflict_clears_flag(store):
    row = lr.start_live_round(10, 1)
    token = row["Token"]
    lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 1, "player": "DM", "value": 4}])
    lr.apply_score_writes(token, "dev-B", "Dave", [{"hole": 1, "player": "DM", "value": 5}])

    lr.resolve_conflict(token, hole=1, player="DM", chosen_value=5, resolved_by="Admin")

    cell = lr.get_scores_since(token, 0)["cells"][0]
    assert cell["value"] == 5
    assert cell["conflict"] is False


def test_finalize_refuses_with_unresolved_conflicts(store, monkeypatch):
    import teg_analysis.analysis.data_update as du
    monkeypatch.setattr(du, "execute_data_update", lambda *a, **k: pytest.fail("must not run"))

    row = lr.start_live_round(10, 1)
    token = row["Token"]
    lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 1, "player": "DM", "value": 4}])
    lr.apply_score_writes(token, "dev-B", "Dave", [{"hole": 1, "player": "DM", "value": 5}])

    with pytest.raises(lr.ConflictsUnresolvedError):
        lr.finalize_live_round(token)


def test_finalize_refuses_when_no_scores_entered(store):
    row = lr.start_live_round(10, 1)
    with pytest.raises(ValueError):
        lr.finalize_live_round(row["Token"])


def _seed_round_pars(store, teg_num=10, round_num=1):
    store["data/round_pars.csv"] = pd.DataFrame(
        [{"TEGNum": teg_num, "Round": round_num, "Hole": h, "Par": 4, "SI": h} for h in range(1, 19)]
    )


def _seed_handicaps(store, tegs=(10,), players=("DM", "GW")):
    """Seed data/handicaps.csv rows -- finalize_live_round refuses without one."""
    rows = [{"TEG": f"TEG {teg_num}", **{p: 18 for p in players}} for teg_num in tegs]
    store["data/handicaps.csv"] = pd.DataFrame(rows)


def test_finalize_only_includes_complete_18_hole_rounds(store, monkeypatch):
    _seed_round_pars(store)
    _seed_handicaps(store)
    import teg_analysis.analysis.data_update as du
    captured = {}

    def fake_execute(long_df, **kwargs):
        captured["long_df"] = long_df.copy()
        captured["kwargs"] = kwargs
        return {"records_added": len(long_df), "changed_rounds": {}, "backups": [], "committed": True, "files_committed": 1}

    monkeypatch.setattr(du, "execute_data_update", fake_execute)

    row = lr.start_live_round(10, 1)
    token = row["Token"]
    # DM plays all 18; GW only gets 3 holes entered -> excluded from finalize.
    dm_cells = [{"hole": h, "player": "DM", "value": 4} for h in range(1, 19)]
    gw_cells = [{"hole": h, "player": "GW", "value": 4} for h in range(1, 4)]
    lr.apply_score_writes(token, "dev-A", "Jon", dm_cells + gw_cells)

    result = lr.finalize_live_round(token)

    long_df = captured["long_df"]
    assert set(long_df["Pl"].unique()) == {"DM"}
    assert len(long_df) == 18
    assert captured["kwargs"] == {"new_data_only": True}
    assert (long_df["Par"] == 4).all() and (long_df["TEGNum"] == 10).all() and (long_df["Round"] == 1).all()
    assert result["teg_num"] == 10 and result["round_num"] == 1

    reg = store["data/live_rounds.csv"]
    assert reg[reg["Token"] == token].iloc[0]["Status"] == "finalized"
    assert f"data/live_rounds/archive/{token}.csv" in store


def test_stray_out_of_range_hole_rejected_not_silently_dropping_round(store, monkeypatch):
    """Regression: an out-of-range hole (e.g. a client bug sending hole=42)
    used to be written straight into staging, giving a player a 19th row --
    finalize_live_round's `len(x) == 18` completeness filter would then
    silently exclude their entire round. Validation must reject the write
    outright instead, so a legitimate 18-hole round always finalizes."""
    _seed_round_pars(store)
    _seed_handicaps(store)
    import teg_analysis.analysis.data_update as du
    captured = {}

    def fake_execute(long_df, **kwargs):
        captured["long_df"] = long_df.copy()
        return {"records_added": len(long_df), "changed_rounds": {}, "backups": [], "committed": True, "files_committed": 1}

    monkeypatch.setattr(du, "execute_data_update", fake_execute)

    row = lr.start_live_round(10, 1)
    token = row["Token"]
    dm_cells = [{"hole": h, "player": "DM", "value": 4} for h in range(1, 19)]
    lr.apply_score_writes(token, "dev-A", "Jon", dm_cells)

    # A stray out-of-range hole must be rejected, not merged into staging.
    with pytest.raises(lr.InvalidScoreCellError):
        lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": 42, "player": "DM", "value": 4}])

    result = lr.finalize_live_round(token)

    long_df = captured["long_df"]
    assert len(long_df) == 18  # DM's round is complete and intact, not dropped
    assert set(long_df["Hole"]) == set(range(1, 19))
    assert result["teg_num"] == 10


def test_finalize_refuses_when_not_active(store, monkeypatch):
    _seed_round_pars(store)
    _seed_handicaps(store)
    import teg_analysis.analysis.data_update as du
    monkeypatch.setattr(du, "execute_data_update", lambda *a, **k: {
        "records_added": 18, "changed_rounds": {}, "backups": [], "committed": True, "files_committed": 1,
    })

    row = lr.start_live_round(10, 1)
    token = row["Token"]
    lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": h, "player": "DM", "value": 4} for h in range(1, 19)])
    lr.finalize_live_round(token)

    with pytest.raises(lr.LiveRoundInactiveError):
        lr.finalize_live_round(token)


def test_finalize_refuses_when_teg_roster_not_confirmed(store, monkeypatch):
    """finalize_live_round must refuse when the TEG has no handicaps.csv row --
    a silent HC=0 would poison net/Stableford scores."""
    _seed_round_pars(store)
    _seed_handicaps(store, tegs=(9,))  # handicaps.csv exists, but no row for TEG 10
    import teg_analysis.analysis.data_update as du
    monkeypatch.setattr(du, "execute_data_update", lambda *a, **k: pytest.fail("must not run"))

    row = lr.start_live_round(10, 1)
    token = row["Token"]
    lr.apply_score_writes(token, "dev-A", "Jon", [{"hole": h, "player": "DM", "value": 4} for h in range(1, 19)])

    with pytest.raises(ValueError, match="roster not confirmed"):
        lr.finalize_live_round(token)


def test_cancel_live_round_marks_cancelled_without_touching_scores(store, monkeypatch):
    import teg_analysis.analysis.data_update as du
    monkeypatch.setattr(du, "execute_data_update", lambda *a, **k: pytest.fail("must not run"))

    row = lr.start_live_round(10, 1)
    token = row["Token"]
    result = lr.cancel_live_round(token)
    assert result["status"] == "cancelled"

    reg = store["data/live_rounds.csv"]
    assert reg[reg["Token"] == token].iloc[0]["Status"] == "cancelled"


def test_cancel_unknown_token_raises(store):
    with pytest.raises(lr.LiveRoundNotFoundError):
        lr.cancel_live_round("nope")


def test_get_live_round_context_unknown_token_returns_none(store):
    assert lr.get_live_round_context("nope") is None


def test_get_live_round_context_combines_roster_and_pars(store, monkeypatch):
    import teg_analysis.analysis.teg_setup as ts

    monkeypatch.setattr(ts, "get_teg_roster_form", lambda teg_num: {
        "teg_num": teg_num,
        "source": "confirmed",
        "players": [
            {"code": "DM", "name": "David MULLIN", "playing": True, "handicap": 18, "source": "confirmed"},
            {"code": "GW", "name": "Gregg WILLIAMS", "playing": False, "handicap": 0, "source": "confirmed"},
        ],
    })

    row = lr.start_live_round(10, 1)
    ctx = lr.get_live_round_context(row["Token"])

    assert ctx["teg_num"] == 10 and ctx["round_num"] == 1
    assert ctx["status"] == "active"
    assert ctx["course"] == "Ashdown"
    assert ctx["players"] == ["DM"]  # GW excluded -- not playing this TEG
    assert ctx["player_names"]["DM"] == "David MULLIN"
    assert len(ctx["holes"]) == 18


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
