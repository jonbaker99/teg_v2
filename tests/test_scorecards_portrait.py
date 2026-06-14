"""Tests for the portrait (holes-as-rows) scorecard builders.

These mirror the existing landscape builders transposed, so the core check is
parity: every per-hole score cell and every subtotal must match the landscape
output for the same data. Synthetic DataFrames only — no data files needed.
"""

import re
import pandas as pd
import pytest

from teg_analysis.display.scorecards import (
    build_single_round_combined_table,
    build_single_round_combined_portrait,
    build_tournament_gross_table,
    build_tournament_gross_portrait,
    build_tournament_stableford_portrait,
    build_round_comparison_gross_table,
    build_round_comparison_gross_portrait,
    build_round_comparison_stableford_portrait,
)

PARS = [4, 5, 4, 3, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4]  # par 72


def _stableford(vs_par):
    return max(0, 2 - vs_par)


def _single_round_df(scores, pars=PARS):
    """18-row one-player/one-round frame with Hole, PAR, Sc, GrossVP, Stableford."""
    rows = []
    for i, (par, sc) in enumerate(zip(pars, scores), start=1):
        rows.append({'Hole': i, 'PAR': par, 'Sc': sc,
                     'GrossVP': sc - par, 'Stableford': _stableford(sc - par)})
    return pd.DataFrame(rows)


def _gross_cells(html):
    """Multiset of (vs_par, score) gross cells, order-independent per 9.
    The span may carry a title attribute, so we skip over it with [^>]*."""
    return sorted(re.findall(r'data-vs-par="(-?\d+)"><span[^>]*>(\d+)</span>', html))


def _stableford_cells(html):
    return sorted(re.findall(r'data-stableford="(-?\d+)"><span[^>]*>(\d+)</span>', html))


def _grand_total_cells(portrait_html):
    """The numeric values in the portrait TOTAL row, in column order."""
    row = re.search(r'<tr class="totals-row grand-total">(.*?)</tr>', portrait_html).group(1)
    return [int(x) for x in re.findall(r'>(\d+)<', row)]


# --- single round -----------------------------------------------------------

SCORES_A = [4, 5, 5, 3, 4, 6, 5, 2, 4, 4, 5, 3, 5, 4, 4, 4, 6, 3]  # gross 76 (+4)


def test_single_round_portrait_structure():
    html = build_single_round_combined_portrait(_single_round_df(SCORES_A))
    assert 'scorecard-table-portrait' in html
    assert html.count('<tr') == 1 + 18 + 3  # header + 18 holes + OUT/IN/TOTAL
    assert '>Gross<' in html and '>Stableford<' in html


def test_single_round_portrait_parity_with_landscape():
    df = _single_round_df(SCORES_A)
    portrait = build_single_round_combined_portrait(df)
    landscape = build_single_round_combined_table(df)
    assert _gross_cells(portrait) == _gross_cells(landscape)
    assert _stableford_cells(portrait) == _stableford_cells(landscape)


def test_single_round_portrait_totals():
    df = _single_round_df(SCORES_A)
    par_tot, gross_tot = sum(PARS), sum(SCORES_A)
    sf_tot = sum(_stableford(s - p) for s, p in zip(SCORES_A, PARS))
    assert _grand_total_cells(build_single_round_combined_portrait(df)) == [par_tot, gross_tot, sf_tot]


# --- whole TEG (rounds as columns) ------------------------------------------

def _tournament_df():
    r1 = [4, 5, 5, 3, 4, 6, 5, 2, 4, 4, 5, 3, 5, 4, 4, 4, 6, 3]
    r2 = [5, 5, 4, 4, 4, 5, 6, 3, 4, 5, 4, 3, 6, 4, 5, 3, 5, 4]
    frames = []
    for rnd, scores in [(1, r1), (2, r2)]:
        d = _single_round_df(scores)
        d['Round'] = rnd
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def test_tournament_portrait_columns_and_parity():
    data = _tournament_df()
    gross = build_tournament_gross_portrait(data)
    assert '>R1<' in gross and '>R2<' in gross
    # header Hole|PAR|R1|R2 → 4 columns
    header = re.search(r'<thead>(.*?)</thead>', gross).group(1)
    assert header.count('<th') == 4
    # gross cells parity vs landscape
    assert _gross_cells(gross) == _gross_cells(build_tournament_gross_table(data))


def test_tournament_portrait_round_totals():
    data = _tournament_df()
    gross = build_tournament_gross_portrait(data)
    totals = _grand_total_cells(gross)  # [par, R1 total, R2 total]
    r1_tot = int(data[data['Round'] == 1]['Sc'].sum())
    r2_tot = int(data[data['Round'] == 2]['Sc'].sum())
    assert totals == [sum(PARS), r1_tot, r2_tot]


def test_tournament_stableford_portrait_has_no_vs_par():
    sf = build_tournament_stableford_portrait(_tournament_df())
    assert 'data-vs-par' not in sf
    assert 'data-stableford' in sf


# --- vs field (players as columns) ------------------------------------------

def _field_df():
    # three players; DM lowest gross, GP highest → expected column order DM, JB, GP
    players = {
        'JB': ('Jon Baker', [5, 5, 4, 4, 4, 5, 6, 3, 4, 5, 4, 3, 6, 4, 5, 3, 5, 4]),
        'DM': ('David Mullin', [4, 5, 5, 3, 4, 5, 5, 2, 4, 4, 4, 3, 5, 4, 4, 4, 5, 3]),
        'GP': ('Graham Patterson', [5, 6, 5, 4, 5, 6, 6, 4, 5, 5, 5, 4, 6, 5, 5, 4, 6, 5]),
    }
    frames = []
    for code, (name, scores) in players.items():
        d = _single_round_df(scores)
        d['Pl'] = code
        d['Player'] = name
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def test_field_portrait_columns_sorted_by_gross():
    gross = build_round_comparison_gross_portrait(_field_df())
    header = re.search(r'<thead>(.*?)</thead>', gross).group(1)
    codes = re.findall(r'<th class="col-header">(\w+)</th>', header)
    assert codes == ['DM', 'JB', 'GP']  # ascending gross total


def test_field_portrait_parity_with_landscape():
    data = _field_df()
    assert _gross_cells(build_round_comparison_gross_portrait(data)) == \
        _gross_cells(build_round_comparison_gross_table(data))


def test_field_stableford_portrait_totals_match_per_player():
    data = _field_df()
    sf = build_round_comparison_stableford_portrait(data)
    totals = _grand_total_cells(sf)  # [par, DM, JB, GP] in sorted order
    expected = [sum(PARS)] + [int(data[data['Pl'] == c]['Stableford'].sum()) for c in ['DM', 'JB', 'GP']]
    assert totals == expected
