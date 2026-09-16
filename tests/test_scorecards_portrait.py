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
    build_bestball_worstball_scorecard,
    build_bestball_worstball_scorecard_portrait,
    build_bestball_contribution_bars,
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
    The cell may carry extra attrs (data-tip) before '>' and the span may too,
    so we skip over them with [^>]*."""
    return sorted(re.findall(r'data-vs-par="(-?\d+)"[^>]*><span[^>]*>(\d+)</span>', html))


def _stableford_cells(html):
    return sorted(re.findall(r'data-stableford="(-?\d+)"[^>]*><span[^>]*>(\d+)</span>', html))


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


# --- Bestball / Worstball (R3.4) ---------------------------------------------

def test_bestball_portrait_header_matches_landscape_players():
    data = _field_df()
    portrait = build_bestball_worstball_scorecard_portrait(data)
    header = re.search(r'<thead>(.*?)</thead>', portrait).group(1)
    cols = re.findall(r'<th class="col-header">(\w+)</th>', header)
    assert cols == ['Best', 'Worst', 'DM', 'JB', 'GP']  # ascending gross, same order as the field card


def test_bestball_portrait_parity_with_landscape():
    # Every (best, worst) team-cell pair and every per-player vs-par cell must
    # match between the two orientations, since they're built from the same
    # per-hole min/max and per-player GrossVP.
    data = _field_df()
    landscape = build_bestball_worstball_scorecard(data)
    portrait = build_bestball_worstball_scorecard_portrait(data)
    team_cells = lambda html: sorted(re.findall(r'data-vs-par="(-?\d+)"', html))
    assert team_cells(landscape) == team_cells(portrait)


def test_bestball_portrait_matches_landscape_per_coordinate():
    """Stronger than the multiset check above: every (player, hole) coordinate
    must show the same displayed value AND the same best/worst class in both
    orientations -- not just an equal bag of values, which could hide a
    transposition or a class assigned to the wrong player/hole."""
    data = _field_df()
    landscape = build_bestball_worstball_scorecard(data)
    portrait = build_bestball_worstball_scorecard_portrait(data)

    cell_re = re.compile(r'<td class="(bw-cell[^"]*)"[^>]*><span[^>]*>([^<]+)</span></td>')

    # Landscape: one <tr> per player, starting with a plain player-label td
    # and followed by 18 bw-cell tds in hole order (1..18). The Bestball /
    # Worstball team rows use score-cell tds, not bw-cell, so they never
    # match this shape.
    player_rows = re.findall(r'<tr><td class="player-label">.*?</td>(.*?)</tr>', landscape)
    player_rows = [row for row in player_rows if 'bw-cell' in row]
    assert len(player_rows) == 3  # DM, JB, GP

    landscape_by_coord = {}
    for p_idx, row in enumerate(player_rows):
        cells = cell_re.findall(row)
        assert len(cells) == 18
        for hole_idx, (cls, label) in enumerate(cells, start=1):
            landscape_by_coord[(p_idx, hole_idx)] = (label, cls)

    # Portrait: one data <tr> per hole (not a totals row), starting with the
    # hole number, then Best/Worst score-cells, then one bw-cell per player
    # in the same sorted-player order as the landscape rows above.
    data_rows = re.findall(r'<tr><td class="hole-label">(\d+)</td>(.*?)</tr>', portrait)
    assert len(data_rows) == 18

    portrait_by_coord = {}
    for hole_str, row in data_rows:
        hole = int(hole_str)
        cells = cell_re.findall(row)
        assert len(cells) == 3
        for p_idx, (cls, label) in enumerate(cells):
            portrait_by_coord[(p_idx, hole)] = (label, cls)

    assert landscape_by_coord == portrait_by_coord
    assert len(landscape_by_coord) == 18 * 3

    # Cross-check a sample of coordinates against directly-computed ground
    # truth (per-hole field min/max from the raw data), so a shared bug in
    # both builders' helper wouldn't slip through as "parity".
    codes = ['DM', 'JB', 'GP']  # ascending gross, same order as both tables
    for hole in (1, 9, 18):
        hole_vals = data[data['Hole'] == hole].set_index('Pl')['GrossVP']
        hmin, hmax = int(hole_vals.min()), int(hole_vals.max())
        for p_idx, code in enumerate(codes):
            v = int(hole_vals[code])
            expect_cls = 'bw-cell bw-player-best' if v == hmin else (
                'bw-cell bw-player-worst' if v == hmax else 'bw-cell')
            assert landscape_by_coord[(p_idx, hole)][1] == expect_cls


def test_bestball_portrait_totals_match_per_player():
    data = _field_df()
    portrait = build_bestball_worstball_scorecard_portrait(data)
    totals = _grand_total_cells_signed(portrait)
    hole_min = {h: int(data[data['Hole'] == h]['GrossVP'].min()) for h in range(1, 19)}
    hole_max = {h: int(data[data['Hole'] == h]['GrossVP'].max()) for h in range(1, 19)}
    expected = [sum(hole_min.values()), sum(hole_max.values())] + [
        int(data[data['Pl'] == c]['GrossVP'].sum()) for c in ['DM', 'JB', 'GP']
    ]
    assert totals == expected


def _grand_total_cells_signed(portrait_html):
    """Like _grand_total_cells, but for vs-par labels (E/+N/-N), not raw ints."""
    row = re.search(r'<tr class="totals-row grand-total">(.*?)</tr>', portrait_html).group(1)
    labels = re.findall(r'<td class="totals">([+\-]?\d+|E)</td>', row)
    return [0 if lab == 'E' else int(lab) for lab in labels]


def test_contribution_bars_sorted_and_zero_is_literal():
    data = _field_df()
    html = build_bestball_contribution_bars(data)
    best_section = html.split("bw-bars-title--worst")[0]
    worst_section = html[len(best_section):]

    def impact_values(section):
        # Impact is its own headline column: <td class="bw-col-impact"><span
        # class="bw-impact bw-impact--{kind}|--zero">value</span></td>.
        return [0 if v == '0' else int(v) for v in
                re.findall(r'class="bw-impact[^"]*">([+\-]?\d+|0)</span>', section)]

    best_values = impact_values(best_section)
    worst_values = impact_values(worst_section)
    assert len(best_values) == len(worst_values) == 3
    assert best_values == sorted(best_values)  # ascending (bestball impact <= 0)
    assert worst_values == sorted(worst_values, reverse=True)  # descending (worstball impact >= 0)
    # An exact-zero impact renders as literal '0', not the en-dash placeholder.
    if 0 in best_values or 0 in worst_values:
        assert '>0</span>' in html
    assert '–</span>' not in html


def test_contribution_bars_holes_and_solo_columns():
    data = _field_df()
    html = build_bestball_contribution_bars(data)
    # Holes contributed to / solo holes are plain, de-emphasised numeric
    # columns (not a CSS bar) -- impact stays the headline column, unchanged.
    assert 'bw-bar-track' not in html
    assert 'bw-bar-fill' not in html
    assert html.count('<th class="bw-col-context">Holes</th>') == 2
    assert html.count('<th class="bw-col-context">Solo</th>') == 2
    assert re.search(r'<td class="bw-col-context">\d+</td>', html)
