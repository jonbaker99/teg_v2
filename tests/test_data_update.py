"""Unit tests for the headless data-update pipeline.

Covers the pure (no-I/O) functions in ``teg_analysis.analysis.data_update``:
reshape/validation, scoring calculation, duplicate detection and difference
analysis. The orchestrator (``execute_data_update``) is not tested here as it
performs file I/O / GitHub writes — these tests stay self-contained with
synthetic DataFrames.
"""

import pandas as pd
import pytest

from teg_analysis.analysis.data_update import (
    process_google_sheets_data,
    process_round_for_all_scores,
    find_duplicate_keys,
    analyze_hole_level_differences,
    summarise_round_scores,
    get_available_tegs_and_rounds,
    validate_deletion_selection,
    preview_deletion_data,
    find_tegs_missing_round_info,
    analyze_teg_completion,
    EDITABLE_DATA_FILES,
)
from teg_analysis.constants import PLAYER_DICT


def _wide_round(scores_by_player: dict) -> pd.DataFrame:
    """Build an 18-hole wide-format round frame for the given players.

    Args:
        scores_by_player: {player_code: [18 hole scores]}.
    """
    rows = []
    for hole in range(1, 19):
        row = {'TEGNum': 10, 'Round': 1, 'Hole': hole, 'Par': 4, 'SI': hole}
        for pl, scores in scores_by_player.items():
            row[pl] = scores[hole - 1]
        rows.append(row)
    return pd.DataFrame(rows)


def test_process_round_for_all_scores_metrics():
    """Scoring columns are computed correctly, including handicap strokes."""
    long_df = pd.DataFrame([
        # HC 18: one stroke per hole only where 18%18>=SI -> never; HCStrokes=1
        {'TEGNum': 10, 'Round': 1, 'Hole': 1, 'Par': 4, 'SI': 1, 'Pl': 'AB', 'Score': 5},
        # HC 20: HCStrokes = 1 + (20%18>=SI). SI=1 -> 2>=1 True -> 2 strokes
        {'TEGNum': 10, 'Round': 1, 'Hole': 10, 'Par': 4, 'SI': 1, 'Pl': 'JB', 'Score': 4},
    ])
    hc_long = pd.DataFrame([
        {'TEG': 'TEG 10', 'Pl': 'AB', 'HC': 18},
        {'TEG': 'TEG 10', 'Pl': 'JB', 'HC': 20},
    ])

    out = process_round_for_all_scores(long_df, hc_long).set_index('Pl')

    ab = out.loc['AB']
    assert ab['HCStrokes'] == 1
    assert ab['GrossVP'] == 1          # 5 - 4
    assert ab['Net'] == 4             # 5 - 1
    assert ab['NetVP'] == 0           # 4 - 4
    assert ab['Stableford'] == 2      # 2 - 0
    assert ab['HoleID'] == 'T10|R01|H01'
    assert ab['FrontBack'] == 'Front'
    assert ab['Player'] == PLAYER_DICT['AB']

    jb = out.loc['JB']
    assert jb['HCStrokes'] == 2
    assert jb['Net'] == 2             # 4 - 2
    assert jb['NetVP'] == -2          # 2 - 4
    assert jb['Stableford'] == 4      # 2 - (-2)
    assert jb['FrontBack'] == 'Back'  # hole 10


def test_process_round_for_all_scores_does_not_mutate_input():
    """The input frame must not be modified in place."""
    long_df = pd.DataFrame([
        {'TEGNum': 10, 'Round': 1, 'Hole': 1, 'Par': 4, 'SI': 1, 'Pl': 'AB', 'Score': 5},
    ])
    cols_before = list(long_df.columns)
    process_round_for_all_scores(long_df, pd.DataFrame(columns=['TEG', 'Pl', 'HC']))
    assert list(long_df.columns) == cols_before  # no rename/merge leaked back


def test_process_google_sheets_data_filters_incomplete_and_invalid():
    """Invalid scores are dropped and only complete 18-hole rounds survive."""
    # AB: 18 valid holes -> kept. JB: hole 1 is 0 -> removed -> 17 holes -> dropped.
    ab_scores = [4] * 18
    jb_scores = [0] + [5] * 17
    raw = _wide_round({'AB': ab_scores, 'JB': jb_scores})

    out = process_google_sheets_data(raw)

    assert set(out['Pl'].unique()) == {'AB'}
    assert len(out) == 18
    assert (out['Score'] != 0).all()


def test_find_duplicate_keys_detects_overlap():
    existing = pd.DataFrame([
        {'TEGNum': 10, 'Round': 1, 'Hole': 1, 'Pl': 'AB', 'Sc': 5},
        {'TEGNum': 10, 'Round': 1, 'Hole': 2, 'Pl': 'AB', 'Sc': 4},
    ])
    new = pd.DataFrame([
        {'TEGNum': 10, 'Round': 1, 'Hole': 1, 'Pl': 'AB', 'Score': 6},   # overlap
        {'TEGNum': 11, 'Round': 1, 'Hole': 1, 'Pl': 'AB', 'Score': 4},   # new
    ])

    dupes = find_duplicate_keys(existing, new)
    assert len(dupes) == 1
    assert dupes.iloc[0]['TEGNum'] == 10
    assert dupes.iloc[0]['Hole'] == 1


def test_find_duplicate_keys_empty_existing():
    new = pd.DataFrame([{'TEGNum': 10, 'Round': 1, 'Hole': 1, 'Pl': 'AB', 'Score': 6}])
    dupes = find_duplicate_keys(pd.DataFrame(), new)
    assert dupes.empty


def test_analyze_hole_level_differences():
    existing = pd.DataFrame([
        {'TEGNum': 10, 'Round': 1, 'Hole': 1, 'Pl': 'AB', 'Sc': 5},
    ])
    new = pd.DataFrame([
        {'TEGNum': 10, 'Round': 1, 'Hole': 1, 'Pl': 'AB', 'Score': 6},
    ])
    dupes = find_duplicate_keys(existing, new)

    diffs, has_diff = analyze_hole_level_differences(existing, new, dupes)
    assert has_diff is True
    assert len(diffs) == 1
    assert diffs.iloc[0]['Score (existing)'] == 5
    assert diffs.iloc[0]['Score (google sheets)'] == 6


def test_analyze_hole_level_differences_no_diff():
    existing = pd.DataFrame([{'TEGNum': 10, 'Round': 1, 'Hole': 1, 'Pl': 'AB', 'Sc': 5}])
    new = pd.DataFrame([{'TEGNum': 10, 'Round': 1, 'Hole': 1, 'Pl': 'AB', 'Score': 5}])
    dupes = find_duplicate_keys(existing, new)

    diffs, has_diff = analyze_hole_level_differences(existing, new, dupes)
    assert has_diff is False
    assert diffs.empty


def test_summarise_round_scores_totals():
    raw = _wide_round({'AB': [4] * 18, 'JB': [5] * 18})
    long_df = process_google_sheets_data(raw)
    summary = summarise_round_scores(long_df)
    # 18 holes: AB total 72, JB total 90.
    assert summary.loc['AB'].iloc[0] == 72
    assert summary.loc['JB'].iloc[0] == 90


# ---------------------------------------------------------------------------
# Delete-flow pure functions
# ---------------------------------------------------------------------------

def _scores_frame() -> pd.DataFrame:
    """Synthetic all-scores frame spanning two TEGs / multiple rounds."""
    rows = []
    for teg in (10, 11):
        for rnd in (1, 2):
            for pl in ('AB', 'JB'):
                rows.append({'TEGNum': teg, 'Round': rnd, 'Hole': 1, 'Pl': pl, 'Sc': 4})
    return pd.DataFrame(rows)


def test_get_available_tegs_and_rounds_orders_newest_first():
    mapping = get_available_tegs_and_rounds(_scores_frame())
    assert list(mapping.keys()) == [11, 10]      # reverse-chronological
    assert mapping[10] == [1, 2]
    assert mapping[11] == [1, 2]


def test_get_available_tegs_and_rounds_empty():
    assert get_available_tegs_and_rounds(pd.DataFrame()) == {}


def test_validate_deletion_selection():
    assert validate_deletion_selection([1]) is True
    assert validate_deletion_selection([]) is False


def test_preview_deletion_data_filters_selection():
    scores = _scores_frame()
    preview = preview_deletion_data(scores, 10, [1])
    # Only TEG 10, Round 1 -> two players.
    assert len(preview) == 2
    assert set(preview['TEGNum'].unique()) == {10}
    assert set(preview['Round'].unique()) == {1}


def test_preview_deletion_data_handles_string_inputs():
    """Selections coming from form posts arrive as strings — still match."""
    scores = _scores_frame()
    preview = preview_deletion_data(scores, '11', ['2'])
    assert len(preview) == 2
    assert set(preview['TEGNum'].unique()) == {11}


def test_editable_files_registry_shape():
    """Every registry entry exposes the fields the routes rely on."""
    assert 'round_info' in EDITABLE_DATA_FILES
    for slug, meta in EDITABLE_DATA_FILES.items():
        assert meta['path'].startswith('data/') and meta['path'].endswith('.csv')
        assert meta['label'] and meta['description']
        assert meta['kind'] in {'metadata', 'status'}


# ---------------------------------------------------------------------------
# round_info validation / completion robustness
# ---------------------------------------------------------------------------

def test_find_tegs_missing_round_info(monkeypatch):
    """TEGs in the new data but absent from round_info are reported."""
    round_info = pd.DataFrame({'TEGNum': [10, 11], 'TEG': ['TEG 10', 'TEG 11'], 'Year': [2020, 2021]})
    # find_tegs_missing_round_info does `from teg_analysis.io import read_file` lazily.
    import teg_analysis.io as tio
    monkeypatch.setattr(tio, 'read_file', lambda path: round_info)

    new = pd.DataFrame({'TEGNum': [11, 12], 'Round': [1, 1], 'Hole': [1, 1], 'Pl': ['AB', 'AB']})
    assert find_tegs_missing_round_info(new) == [12]

    new_ok = pd.DataFrame({'TEGNum': [10, 11], 'Round': [1, 1], 'Hole': [1, 1], 'Pl': ['AB', 'AB']})
    assert find_tegs_missing_round_info(new_ok) == []


def test_analyze_teg_completion_tolerates_missing_round_info(monkeypatch):
    """A TEG missing from round_info falls back instead of raising IndexError."""
    import teg_analysis.io as tio
    import teg_analysis.core.data_loader as dl
    round_info = pd.DataFrame({'TEGNum': [10], 'TEG': ['TEG 10'], 'Year': [2020]})
    monkeypatch.setattr(tio, 'read_file', lambda path: round_info)
    monkeypatch.setattr(dl, 'get_incomplete_tegs', lambda all_data: [])

    all_data = pd.DataFrame({
        'TEGNum': [10, 12], 'Round': [1, 1], 'Hole': [1, 1], 'Pl': ['AB', 'AB'],
    })
    out = analyze_teg_completion(all_data).set_index('TEGNum')
    assert out.loc[10, 'TEG'] == 'TEG 10'
    assert out.loc[12, 'TEG'] == 'TEG 12'      # fallback label
    assert pd.isna(out.loc[12, 'Year'])         # fallback year


# ---------------------------------------------------------------------------
# execute_data_update I/O (isolated scratch repo — never touches real data/)
# ---------------------------------------------------------------------------

@pytest.fixture
def scratch_repo(tmp_path, monkeypatch):
    """Point teg_analysis's local-path resolution at a scratch copy of data/,
    so I/O tests exercise the real read/write pipeline without touching the
    real repo's data/ directory."""
    import shutil
    from pathlib import Path
    import teg_analysis.io.volume_operations as volume_operations

    real_data = Path(__file__).resolve().parent.parent / 'data'
    shutil.copytree(real_data, tmp_path / 'data')

    monkeypatch.setattr(volume_operations, '_REPO_ROOT', tmp_path)
    monkeypatch.delenv('RAILWAY_ENVIRONMENT', raising=False)
    return tmp_path


def _fake_wide_round(teg_num=50, round_num=1):
    players = ['DM', 'GW', 'HM', 'JP', 'JB', 'SN', 'AB']
    rows = []
    for hole in range(1, 19):
        row = {'TEGNum': teg_num, 'Round': round_num, 'Hole': hole, 'Par': 4, 'SI': hole}
        for p in players:
            row[p] = 4
        rows.append(row)
    return pd.DataFrame(rows)


def test_execute_data_update_creates_backups(scratch_repo):
    """execute_data_update backs up all-scores/all-data before writing (Phase 1.1)."""
    from teg_analysis.analysis.data_update import execute_data_update

    long_df = process_google_sheets_data(_fake_wide_round())
    result = execute_data_update(long_df, overwrite=True)

    assert result['records_added'] > 0
    assert len(result['backups']) == 2
    for backup_path in result['backups']:
        assert (scratch_repo / backup_path).exists()


def test_execute_data_update_no_new_records_skips_backups(scratch_repo):
    """A no-op call (everything already a duplicate, new_data_only) takes no backups."""
    from teg_analysis.analysis.data_update import execute_data_update

    long_df = process_google_sheets_data(_fake_wide_round())
    execute_data_update(long_df, overwrite=True)  # establish the data
    result = execute_data_update(long_df, new_data_only=True)  # now a full duplicate

    assert result['records_added'] == 0
    assert result['backups'] == []


def test_execute_data_update_rejects_concurrent_call(scratch_repo):
    """A second add/delete call while one is already running raises
    UpdateInProgressError instead of interleaving writes (Phase 1.3)."""
    from teg_analysis.analysis.data_update import (
        execute_data_update, execute_data_deletion, _update_lock, UpdateInProgressError,
    )

    long_df = process_google_sheets_data(_fake_wide_round())

    assert _update_lock.acquire(blocking=False)
    try:
        with pytest.raises(UpdateInProgressError):
            execute_data_update(long_df, overwrite=True)
        with pytest.raises(UpdateInProgressError):
            execute_data_deletion(50, [1])
    finally:
        _update_lock.release()

    # Lock is released afterwards -> a normal call succeeds.
    result = execute_data_update(long_df, overwrite=True)
    assert result['records_added'] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
