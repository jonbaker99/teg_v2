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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
