"""update_winners_cache keeps data/teg_winners.csv in step with completed_tegs.csv."""

import pandas as pd
import pytest

import teg_analysis.io.volume_operations as volume_operations
from teg_analysis.analysis.history import update_winners_cache

COLS = ['TEG', 'Year', 'Area', 'TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon']


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(volume_operations, "_REPO_ROOT", tmp_path)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    (tmp_path / "data").mkdir()
    return tmp_path


def _all_data(teg_num=30, year=2040, area="Testland"):
    """Two players, one hole each. AA: better gross, worse stableford."""
    rows = []
    for pl, gross, stab in (("AA", -2, 30), ("BB", 5, 40), ("CC", 9, 10)):
        rows.append({'TEGNum': teg_num, 'TEG': f'TEG {teg_num}', 'Year': year,
                     'Area': area, 'Player': pl, 'GrossVP': gross,
                     'NetVP': gross, 'Stableford': stab})
    return pd.DataFrame(rows)


def _write(repo, name, rows, cols):
    pd.DataFrame(rows, columns=cols).to_csv(repo / "data" / name, index=False)


def _completed(repo, nums):
    _write(repo, "completed_tegs.csv",
           [[n, f"TEG {n}", 2000 + n, "complete", 4] for n in nums],
           ['TEGNum', 'TEG', 'Year', 'Status', 'Rounds'])


def _winners(repo):
    return pd.read_csv(repo / "data" / "teg_winners.csv")


def test_missing_completed_teg_row_is_added(repo):
    _completed(repo, [2, 30])
    _write(repo, "teg_winners.csv", [["TEG 2", 2009, "Algarve", "X", "Y", "Z"]], COLS)

    assert update_winners_cache(_all_data()) is None

    df = _winners(repo)
    assert list(df.columns) == COLS
    assert list(df['TEG']) == ["TEG 2", "TEG 30"]
    new = df[df['TEG'] == "TEG 30"].iloc[0]
    assert new['Year'] == 2040 and new['Area'] == "Testland"
    assert new['TEG Trophy'] == "BB"        # stableford era: most points
    assert new['Green Jacket'] == "AA"      # best gross
    assert new['HMM Wooden Spoon'] == "CC"  # fewest points
    # Existing row untouched
    assert df.iloc[0]['TEG Trophy'] == "X"
    assert pd.api.types.is_integer_dtype(df['Year'])


def test_missing_winners_file_is_created(repo):
    _completed(repo, [30])
    update_winners_cache(_all_data())
    assert list(_winners(repo)['TEG']) == ["TEG 30"]


def test_row_for_no_longer_complete_teg_is_removed(repo):
    _completed(repo, [2])
    _write(repo, "teg_winners.csv",
           [["TEG 2", 2009, "Algarve", "X", "Y", "Z"],
            ["TEG 30", 2040, "Testland", "BB", "AA", "CC"]], COLS)

    update_winners_cache(_all_data())

    assert list(_winners(repo)['TEG']) == ["TEG 2"]


def test_no_change_does_not_write(repo, monkeypatch):
    _completed(repo, [2])
    _write(repo, "teg_winners.csv", [["TEG 2", 2009, "Algarve", "X", "Y", "Z"]], COLS)
    import teg_analysis.io as io
    calls = []
    monkeypatch.setattr(io, "write_file", lambda *a, **k: calls.append(a))

    assert update_winners_cache(_all_data()) is None
    assert calls == []


def test_defer_github_returns_file_info(repo):
    _completed(repo, [30])
    info = update_winners_cache(_all_data(), defer_github=False)
    assert info is None
    (repo / "data" / "teg_winners.csv").unlink()
    # Local (non-Railway) write_file returns None even when deferred; on Railway
    # it returns the file-info dict, which is passed straight through.
    update_winners_cache(_all_data(), defer_github=True)
    assert (repo / "data" / "teg_winners.csv").exists()


def test_teg_50_excluded(repo):
    _completed(repo, [50])
    update_winners_cache(_all_data(teg_num=50))
    assert not (repo / "data" / "teg_winners.csv").exists() or _winners(repo).empty


def test_completed_teg_without_data_raises(repo):
    _completed(repo, [30])
    with pytest.raises(ValueError):
        update_winners_cache(_all_data(teg_num=31))
