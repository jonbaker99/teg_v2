"""Scorecard HTML generation utilities.

UI-agnostic functions for generating scorecard HTML tables.
No streamlit imports. All functions return HTML strings.
"""

import pandas as pd
from datetime import datetime
from typing import Optional


def _format_date(date_str: str) -> str:
    """Parse DD/MM/YYYY and return '17 March 2026' style."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
        return dt.strftime("%-d %B %Y")
    except (ValueError, TypeError):
        return str(date_str)


def _cell_title(row) -> str:
    """Build the hover-tooltip text for one hole's score cell.

    Shown via the native ``title`` attribute so it floats above any
    scroll/overflow wrapper on every page a scorecard appears on. Only the
    fields present in ``row`` are included, so builders work with partial data.
    """
    fields = [
        ('Hole', 'Hole'), ('SI', 'SI'), ('PAR', 'Par'),
        ('Sc', 'Score'), ('Net', 'Net'), ('Stableford', 'Stableford'),
    ]
    parts = [
        f"{label} {int(row[col])}"
        for col, label in fields
        if col in row.index and pd.notna(row[col])
    ]
    return ' · '.join(parts)


def _build_hole_header_row(label_class: str, label_text: str) -> str:
    """Build the hole-number header row."""
    parts = [f'<tr><th class="{label_class} hole-header">{label_text}</th>']
    for hole in range(1, 10):
        parts.append(f'<th class="hole-header">{hole}</th>')
    parts.append('<th class="hole-header totals front-back-divider">OUT</th>')
    for hole in range(10, 19):
        parts.append(f'<th class="hole-header">{hole}</th>')
    parts.append('<th class="hole-header totals">IN</th>')
    parts.append('<th class="hole-header totals">TOTAL</th>')
    parts.append('</tr>')
    return ''.join(parts)


def _build_par_row(df_par: pd.DataFrame, label_class: str) -> str:
    """Build the PAR row using par data from one player/round."""
    front_par = int(df_par[df_par['Hole'] <= 9]['PAR'].sum())
    back_par = int(df_par[df_par['Hole'] > 9]['PAR'].sum())
    total_par = int(df_par['PAR'].sum())

    parts = [f'<tr><th class="{label_class} par-header">PAR</th>']
    for hole in range(1, 10):
        val = int(df_par[df_par['Hole'] == hole]['PAR'].iloc[0])
        parts.append(f'<th class="par-header">{val}</th>')
    parts.append(f'<th class="totals front-back-divider par-header">{front_par}</th>')
    for hole in range(10, 19):
        val = int(df_par[df_par['Hole'] == hole]['PAR'].iloc[0])
        parts.append(f'<th class="par-header">{val}</th>')
    parts.append(f'<th class="totals par-header">{back_par}</th>')
    parts.append(f'<th class="totals par-header">{total_par}</th>')
    parts.append('</tr>')
    return ''.join(parts)


def build_single_round_combined_table(df: pd.DataFrame) -> str:
    """Build a single combined scorecard for one player, single round.

    One table with the hole/PAR header followed by a gross ``Score`` row and a
    ``Stableford`` row — mirrors the Streamlit single-round card.

    Args:
        df: 18-row DataFrame for one player/round with Hole, PAR, Sc, GrossVP,
            Stableford cols.

    Returns:
        HTML string for the combined scorecard table.
    """
    df = df.sort_values('Hole')
    front_9 = df[df['Hole'] <= 9]
    back_9 = df[df['Hole'] > 9]
    front_sc, back_sc, total_sc = int(front_9['Sc'].sum()), int(back_9['Sc'].sum()), int(df['Sc'].sum())
    front_sf, back_sf, total_sf = int(front_9['Stableford'].sum()), int(back_9['Stableford'].sum()), int(df['Stableford'].sum())

    parts = ['<table class="scorecard-table"><thead>']
    parts.append(_build_hole_header_row('label-column', 'Hole'))
    parts.append(_build_par_row(df, 'label-column'))
    parts.append('</thead><tbody>')

    # Gross score row
    parts.append('<tr><td class="label-column">Score</td>')
    for hole in range(1, 10):
        row = df[df['Hole'] == hole].iloc[0]
        parts.append(f'<td class="score-cell" data-vs-par="{int(row["GrossVP"])}"><span title="{_cell_title(row)}">{int(row["Sc"])}</span></td>')
    parts.append(f'<td class="totals front-back-divider">{front_sc}</td>')
    for hole in range(10, 19):
        row = df[df['Hole'] == hole].iloc[0]
        parts.append(f'<td class="score-cell" data-vs-par="{int(row["GrossVP"])}"><span title="{_cell_title(row)}">{int(row["Sc"])}</span></td>')
    parts.append(f'<td class="totals">{back_sc}</td>')
    parts.append(f'<td class="totals">{total_sc}</td>')
    parts.append('</tr>')

    # Stableford row
    parts.append('<tr><td class="label-column">Stableford</td>')
    for hole in range(1, 10):
        row = df[df['Hole'] == hole].iloc[0]
        parts.append(f'<td class="score-cell" data-stableford="{int(row["Stableford"])}"><span title="{_cell_title(row)}">{int(row["Stableford"])}</span></td>')
    parts.append(f'<td class="totals front-back-divider">{front_sf}</td>')
    for hole in range(10, 19):
        row = df[df['Hole'] == hole].iloc[0]
        parts.append(f'<td class="score-cell" data-stableford="{int(row["Stableford"])}"><span title="{_cell_title(row)}">{int(row["Stableford"])}</span></td>')
    parts.append(f'<td class="totals">{back_sf}</td>')
    parts.append(f'<td class="totals">{total_sf}</td>')
    parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)


def build_tournament_gross_table(player_data: pd.DataFrame) -> str:
    """Build gross scores table for one player across all tournament rounds.

    Args:
        player_data: DataFrame for one player with Round, Hole, Sc, GrossVP, PAR cols.

    Returns:
        HTML string for the gross scores table (one row per round).
    """
    rounds = sorted(player_data['Round'].unique())
    par_data = player_data[player_data['Round'] == rounds[0]].sort_values('Hole')

    parts = ['<table class="scorecard-table"><thead>']
    parts.append(_build_hole_header_row('round-label', 'Round'))
    parts.append(_build_par_row(par_data, 'round-label'))
    parts.append('</thead><tbody>')

    for round_num in rounds:
        rd = player_data[player_data['Round'] == round_num].sort_values('Hole')
        front_sc = int(rd[rd['Hole'] <= 9]['Sc'].sum())
        back_sc = int(rd[rd['Hole'] > 9]['Sc'].sum())
        total_sc = int(rd['Sc'].sum())

        parts.append(f'<tr><td class="round-label">Round {round_num}</td>')
        for hole in range(1, 10):
            row = rd[rd['Hole'] == hole].iloc[0]
            vs_par = int(row['GrossVP'])
            score = int(row['Sc'])
            parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span title="{_cell_title(row)}">{score}</span></td>')
        parts.append(f'<td class="totals front-back-divider">{front_sc}</td>')
        for hole in range(10, 19):
            row = rd[rd['Hole'] == hole].iloc[0]
            vs_par = int(row['GrossVP'])
            score = int(row['Sc'])
            parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span title="{_cell_title(row)}">{score}</span></td>')
        parts.append(f'<td class="totals">{back_sc}</td>')
        parts.append(f'<td class="totals">{total_sc}</td>')
        parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)


def build_tournament_stableford_table(player_data: pd.DataFrame) -> str:
    """Build stableford points table for one player across all tournament rounds.

    Args:
        player_data: DataFrame for one player with Round, Hole, Stableford, PAR cols.

    Returns:
        HTML string for the stableford points table (one row per round).
    """
    rounds = sorted(player_data['Round'].unique())
    par_data = player_data[player_data['Round'] == rounds[0]].sort_values('Hole')

    parts = ['<table class="scorecard-table"><thead>']
    parts.append(_build_hole_header_row('round-label', 'Round'))
    parts.append(_build_par_row(par_data, 'round-label'))
    parts.append('</thead><tbody>')

    for round_num in rounds:
        rd = player_data[player_data['Round'] == round_num].sort_values('Hole')
        front_sf = int(rd[rd['Hole'] <= 9]['Stableford'].sum())
        back_sf = int(rd[rd['Hole'] > 9]['Stableford'].sum())
        total_sf = int(rd['Stableford'].sum())

        parts.append(f'<tr><td class="round-label">Round {round_num}</td>')
        for hole in range(1, 10):
            row = rd[rd['Hole'] == hole].iloc[0]
            sf = int(row['Stableford'])
            parts.append(f'<td class="score-cell" data-stableford="{sf}"><span title="{_cell_title(row)}">{sf}</span></td>')
        parts.append(f'<td class="totals front-back-divider">{front_sf}</td>')
        for hole in range(10, 19):
            row = rd[rd['Hole'] == hole].iloc[0]
            sf = int(row['Stableford'])
            parts.append(f'<td class="score-cell" data-stableford="{sf}"><span title="{_cell_title(row)}">{sf}</span></td>')
        parts.append(f'<td class="totals">{back_sf}</td>')
        parts.append(f'<td class="totals">{total_sf}</td>')
        parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)


def _get_sorted_players(round_data: pd.DataFrame):
    """Return list of (player_code, player_name) sorted by total gross score asc."""
    player_totals = []
    for player in round_data['Pl'].unique():
        pdata = round_data[round_data['Pl'] == player]
        total_score = int(pdata['Sc'].sum())
        player_name = pdata['Player'].iloc[0]
        player_totals.append((total_score, player, player_name))
    player_totals.sort(key=lambda x: x[0])
    return [(p, name) for _, p, name in player_totals]


def build_round_comparison_gross_table(round_data: pd.DataFrame) -> str:
    """Build gross scores table comparing all players in one round.

    Args:
        round_data: DataFrame for all players in a round, with Pl, Player,
                    Hole, PAR, Sc, GrossVP cols.

    Returns:
        HTML string for the gross scores table (one row per player).
    """
    sorted_players = _get_sorted_players(round_data)
    first_player_data = round_data[round_data['Pl'] == round_data['Pl'].iloc[0]].sort_values('Hole')

    parts = ['<table class="scorecard-table"><thead>']
    parts.append(_build_hole_header_row('player-label', 'Player'))
    parts.append(_build_par_row(first_player_data, 'player-label'))
    parts.append('</thead><tbody>')

    for player_code, player_name in sorted_players:
        pdata = round_data[round_data['Pl'] == player_code].sort_values('Hole')
        front_sc = int(pdata[pdata['Hole'] <= 9]['Sc'].sum())
        back_sc = int(pdata[pdata['Hole'] > 9]['Sc'].sum())
        total_sc = int(pdata['Sc'].sum())

        parts.append(f'<tr><td class="player-label">{player_name}</td>')
        for hole in range(1, 10):
            row = pdata[pdata['Hole'] == hole].iloc[0]
            vs_par = int(row['GrossVP'])
            score = int(row['Sc'])
            parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span title="{_cell_title(row)}">{score}</span></td>')
        parts.append(f'<td class="totals front-back-divider">{front_sc}</td>')
        for hole in range(10, 19):
            row = pdata[pdata['Hole'] == hole].iloc[0]
            vs_par = int(row['GrossVP'])
            score = int(row['Sc'])
            parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span title="{_cell_title(row)}">{score}</span></td>')
        parts.append(f'<td class="totals">{back_sc}</td>')
        parts.append(f'<td class="totals">{total_sc}</td>')
        parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)


def build_round_comparison_stableford_table(round_data: pd.DataFrame) -> str:
    """Build stableford points table comparing all players in one round.

    Args:
        round_data: DataFrame for all players in a round, with Pl, Player,
                    Hole, PAR, Stableford cols.

    Returns:
        HTML string for the stableford points table (one row per player).
    """
    sorted_players = _get_sorted_players(round_data)
    first_player_data = round_data[round_data['Pl'] == round_data['Pl'].iloc[0]].sort_values('Hole')

    parts = ['<table class="scorecard-table"><thead>']
    parts.append(_build_hole_header_row('player-label', 'Player'))
    parts.append(_build_par_row(first_player_data, 'player-label'))
    parts.append('</thead><tbody>')

    for player_code, player_name in sorted_players:
        pdata = round_data[round_data['Pl'] == player_code].sort_values('Hole')
        front_sf = int(pdata[pdata['Hole'] <= 9]['Stableford'].sum())
        back_sf = int(pdata[pdata['Hole'] > 9]['Stableford'].sum())
        total_sf = int(pdata['Stableford'].sum())

        parts.append(f'<tr><td class="player-label">{player_name}</td>')
        for hole in range(1, 10):
            row = pdata[pdata['Hole'] == hole].iloc[0]
            sf = int(row['Stableford'])
            parts.append(f'<td class="score-cell" data-stableford="{sf}"><span title="{_cell_title(row)}">{sf}</span></td>')
        parts.append(f'<td class="totals front-back-divider">{front_sf}</td>')
        for hole in range(10, 19):
            row = pdata[pdata['Hole'] == hole].iloc[0]
            sf = int(row['Stableford'])
            parts.append(f'<td class="score-cell" data-stableford="{sf}"><span title="{_cell_title(row)}">{sf}</span></td>')
        parts.append(f'<td class="totals">{back_sf}</td>')
        parts.append(f'<td class="totals">{total_sf}</td>')
        parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Portrait (holes-as-rows) scorecards — mobile orientation
#
# Same data inputs and the same score-cell shape contract as the landscape
# builders above (``score-cell`` + ``data-vs-par`` / ``data-stableford``), but
# transposed: holes run down the rows and the dimension (rounds, players, or the
# gross/stableford pair) runs across the columns. Wrapped in
# ``scorecard-table-portrait`` so the portrait layout CSS is scoped to the
# mobile view while the shape styling is inherited from the shared rules.
# ---------------------------------------------------------------------------

_FRONT = range(1, 10)
_BACK = range(10, 19)
_ALL = range(1, 19)


def _portrait_value_cell(metric: str, value: int, vs_par: Optional[int], title: str = '') -> str:
    """One score cell for a portrait row. ``metric`` is 'gross' or 'stableford'."""
    t = f' title="{title}"' if title else ''
    if metric == 'gross':
        return f'<td class="score-cell" data-vs-par="{vs_par}"><span{t}>{value}</span></td>'
    return f'<td class="score-cell" data-stableford="{value}"><span{t}>{value}</span></td>'


def _portrait_header(col_labels: list) -> str:
    """Header row: Hole | PAR | one column per dimension value."""
    parts = ['<thead><tr><th class="hole-header">Hole</th><th class="par-header">PAR</th>']
    for lab in col_labels:
        parts.append(f'<th class="col-header">{lab}</th>')
    parts.append('</tr></thead>')
    return ''.join(parts)


def _build_portrait_single_metric(
    col_keys: list,
    col_labels: list,
    par_by_hole: dict,
    value_by_col_hole: dict,
    vsp_by_col_hole: Optional[dict],
    metric: str,
    title_by_col_hole: Optional[dict] = None,
) -> str:
    """Render a single-metric portrait table (rounds- or players-as-columns).

    Args:
        col_keys: ordered column identifiers (e.g. round numbers, player codes).
        col_labels: display labels for each column, aligned with ``col_keys``.
        par_by_hole: {hole: par}.
        value_by_col_hole: {col_key: {hole: value}}.
        vsp_by_col_hole: {col_key: {hole: vs_par}} for gross; ``None`` for stableford.
        metric: 'gross' or 'stableford'.
        title_by_col_hole: {col_key: {hole: tooltip}} for the hover title; optional.
    """
    parts = ['<table class="scorecard-table-portrait">', _portrait_header(col_labels), '<tbody>']

    def data_rows(holes):
        for hole in holes:
            cells = [f'<tr><td class="hole-label">{hole}</td>',
                     f'<td class="par-cell">{par_by_hole[hole]}</td>']
            for ck in col_keys:
                vsp = vsp_by_col_hole[ck][hole] if vsp_by_col_hole else None
                title = title_by_col_hole[ck][hole] if title_by_col_hole else ''
                cells.append(_portrait_value_cell(metric, value_by_col_hole[ck][hole], vsp, title))
            cells.append('</tr>')
            parts.append(''.join(cells))

    def totals_row(label, holes, extra_cls=''):
        cls = f'totals-row {extra_cls}'.strip()
        par_tot = sum(par_by_hole[h] for h in holes)
        cells = [f'<tr class="{cls}"><td class="hole-label">{label}</td>',
                 f'<td class="par-cell totals">{par_tot}</td>']
        for ck in col_keys:
            cells.append(f'<td class="totals">{sum(value_by_col_hole[ck][h] for h in holes)}</td>')
        cells.append('</tr>')
        parts.append(''.join(cells))

    data_rows(_FRONT)
    totals_row('OUT', list(_FRONT), 'front-back-divider')
    data_rows(_BACK)
    totals_row('IN', list(_BACK))
    totals_row('TOTAL', list(_ALL), 'grand-total')
    parts.append('</tbody></table>')
    return ''.join(parts)


def build_single_round_combined_portrait(df: pd.DataFrame) -> str:
    """Portrait single-round card: holes as rows, Gross + Stableford as columns.

    Args:
        df: 18-row DataFrame for one player/round with Hole, PAR, Sc, GrossVP,
            Stableford cols.

    Returns:
        HTML string for the portrait combined scorecard table.
    """
    df = df.sort_values('Hole')
    par_by_hole = {int(r['Hole']): int(r['PAR']) for _, r in df.iterrows()}
    gross = {int(r['Hole']): int(r['Sc']) for _, r in df.iterrows()}
    vsp = {int(r['Hole']): int(r['GrossVP']) for _, r in df.iterrows()}
    sf = {int(r['Hole']): int(r['Stableford']) for _, r in df.iterrows()}
    title = {int(r['Hole']): _cell_title(r) for _, r in df.iterrows()}

    parts = ['<table class="scorecard-table-portrait">',
             _portrait_header(['Gross', 'Stableford']), '<tbody>']

    def data_rows(holes):
        for hole in holes:
            parts.append(
                f'<tr><td class="hole-label">{hole}</td>'
                f'<td class="par-cell">{par_by_hole[hole]}</td>'
                + _portrait_value_cell('gross', gross[hole], vsp[hole], title[hole])
                + _portrait_value_cell('stableford', sf[hole], None, title[hole])
                + '</tr>'
            )

    def totals_row(label, holes, extra_cls=''):
        cls = f'totals-row {extra_cls}'.strip()
        parts.append(
            f'<tr class="{cls}"><td class="hole-label">{label}</td>'
            f'<td class="par-cell totals">{sum(par_by_hole[h] for h in holes)}</td>'
            f'<td class="totals">{sum(gross[h] for h in holes)}</td>'
            f'<td class="totals">{sum(sf[h] for h in holes)}</td></tr>'
        )

    data_rows(_FRONT)
    totals_row('OUT', list(_FRONT), 'front-back-divider')
    data_rows(_BACK)
    totals_row('IN', list(_BACK))
    totals_row('TOTAL', list(_ALL), 'grand-total')
    parts.append('</tbody></table>')
    return ''.join(parts)


def _tournament_portrait(player_data: pd.DataFrame, metric: str) -> str:
    """Shared builder for the portrait tournament view (rounds as columns)."""
    value_field = 'Sc' if metric == 'gross' else 'Stableford'
    rounds = sorted(player_data['Round'].unique())
    par_src = player_data[player_data['Round'] == rounds[0]].sort_values('Hole')
    par_by_hole = {int(r['Hole']): int(r['PAR']) for _, r in par_src.iterrows()}

    value_by_col_hole, vsp_by_col_hole, title_by_col_hole = {}, {}, {}
    for rnd in rounds:
        rd = player_data[player_data['Round'] == rnd]
        value_by_col_hole[rnd] = {int(r['Hole']): int(r[value_field]) for _, r in rd.iterrows()}
        title_by_col_hole[rnd] = {int(r['Hole']): _cell_title(r) for _, r in rd.iterrows()}
        if metric == 'gross':
            vsp_by_col_hole[rnd] = {int(r['Hole']): int(r['GrossVP']) for _, r in rd.iterrows()}

    return _build_portrait_single_metric(
        col_keys=rounds,
        col_labels=[f'R{r}' for r in rounds],
        par_by_hole=par_by_hole,
        value_by_col_hole=value_by_col_hole,
        vsp_by_col_hole=vsp_by_col_hole if metric == 'gross' else None,
        metric=metric,
        title_by_col_hole=title_by_col_hole,
    )


def build_tournament_gross_portrait(player_data: pd.DataFrame) -> str:
    """Portrait gross table for one player across all rounds (rounds as columns).

    Args:
        player_data: DataFrame for one player with Round, Hole, Sc, GrossVP, PAR cols.
    """
    return _tournament_portrait(player_data, 'gross')


def build_tournament_stableford_portrait(player_data: pd.DataFrame) -> str:
    """Portrait stableford table for one player across all rounds (rounds as columns).

    Args:
        player_data: DataFrame for one player with Round, Hole, Stableford, PAR cols.
    """
    return _tournament_portrait(player_data, 'stableford')


def _round_comparison_portrait(round_data: pd.DataFrame, metric: str) -> str:
    """Shared builder for the portrait field view (players as columns)."""
    value_field = 'Sc' if metric == 'gross' else 'Stableford'
    sorted_players = _get_sorted_players(round_data)  # [(code, name), …] by gross asc
    par_src = round_data[round_data['Pl'] == round_data['Pl'].iloc[0]].sort_values('Hole')
    par_by_hole = {int(r['Hole']): int(r['PAR']) for _, r in par_src.iterrows()}

    col_keys = [code for code, _ in sorted_players]
    value_by_col_hole, vsp_by_col_hole, title_by_col_hole = {}, {}, {}
    for code, _ in sorted_players:
        pdata = round_data[round_data['Pl'] == code]
        value_by_col_hole[code] = {int(r['Hole']): int(r[value_field]) for _, r in pdata.iterrows()}
        title_by_col_hole[code] = {int(r['Hole']): _cell_title(r) for _, r in pdata.iterrows()}
        if metric == 'gross':
            vsp_by_col_hole[code] = {int(r['Hole']): int(r['GrossVP']) for _, r in pdata.iterrows()}

    return _build_portrait_single_metric(
        col_keys=col_keys,
        col_labels=col_keys,
        par_by_hole=par_by_hole,
        value_by_col_hole=value_by_col_hole,
        vsp_by_col_hole=vsp_by_col_hole if metric == 'gross' else None,
        metric=metric,
        title_by_col_hole=title_by_col_hole,
    )


def build_round_comparison_gross_portrait(round_data: pd.DataFrame) -> str:
    """Portrait gross table comparing all players in one round (players as columns).

    Args:
        round_data: DataFrame for all players in a round, with Pl, Player, Hole,
                    PAR, Sc, GrossVP cols. Columns are ordered by gross total asc.
    """
    return _round_comparison_portrait(round_data, 'gross')


def build_round_comparison_stableford_portrait(round_data: pd.DataFrame) -> str:
    """Portrait stableford table comparing all players in one round (players as columns).

    Args:
        round_data: DataFrame for all players in a round, with Pl, Player, Hole,
                    PAR, Stableford cols. Columns are ordered by gross total asc.
    """
    return _round_comparison_portrait(round_data, 'stableford')


# ---------------------------------------------------------------------------
# Responsive wrapper — landscape (desktop/iPad) + portrait (phone) in one block
#
# Produces the same shape as templates/partials/scorecard_content.html so the
# field/round scorecards shown on Latest Round and Full Results auto-swap to the
# portrait (holes-as-rows) layout on narrow screens, just like the Scorecard
# page. The Gross/Stableford portrait toggle uses class-based CSS selectors so
# several blocks (e.g. one per round) can coexist on a page; ``uid`` keeps each
# block's radio group unique.
# ---------------------------------------------------------------------------

def build_round_comparison_responsive(round_data: pd.DataFrame, uid: str) -> str:
    """Build a responsive field scorecard (gross + stableford) for one round.

    Args:
        round_data: DataFrame for all players in a round (Pl, Player, Hole, PAR,
            Sc, GrossVP, Stableford, SI, Net cols).
        uid: unique suffix for the portrait toggle's radio group on this page.

    Returns:
        HTML string with a ``.sc-landscape`` block (gross then stableford,
        stacked) and a ``.sc-portrait`` block (CSS Gross/Stableford toggle).
    """
    gross_l = build_round_comparison_gross_table(round_data)
    stbl_l = build_round_comparison_stableford_table(round_data)
    gross_p = build_round_comparison_gross_portrait(round_data)
    stbl_p = build_round_comparison_stableford_portrait(round_data)

    gross_id, pts_id = f'scm-gross-{uid}', f'scm-pts-{uid}'
    return (
        '<div class="sc-landscape">'
        '<div class="card-header">Gross</div>'
        f'<div class="data-card"><div class="table-wrapper">{gross_l}</div></div>'
        '<div class="card-header">Stableford</div>'
        f'<div class="data-card"><div class="table-wrapper">{stbl_l}</div></div>'
        '</div>'
        '<div class="sc-portrait sc-metric-toggle">'
        f'<input type="radio" class="scm-gross" name="sc-metric-{uid}" id="{gross_id}" checked>'
        f'<input type="radio" class="scm-pts" name="sc-metric-{uid}" id="{pts_id}">'
        '<div class="sc-mseg">'
        f'<label class="lbl-gross" for="{gross_id}">Gross</label>'
        f'<label class="lbl-pts" for="{pts_id}">Stableford</label>'
        '</div>'
        f'<div class="sc-pane sc-pane-gross data-card"><div class="sc-scroll">{gross_p}</div></div>'
        f'<div class="sc-pane sc-pane-pts data-card"><div class="sc-scroll">{stbl_p}</div></div>'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Eclectic scorecard — render an eclectic pivot with background-shaded cells
#
# Eclectic cells hold the best (lowest) score-to-par per hole across rounds.
# They use ``data-evp`` (eclectic vs par) for CSS colouring via background
# shading — NOT the ``data-vs-par`` shapes from the regular scorecard — so the
# two style systems don't interfere.  Values are displayed as to-par labels
# (``E`` for 0, ``-1``, ``+2`` etc.).
# ---------------------------------------------------------------------------

def _vp_label(value: int) -> str:
    """Format a to-par integer for display: 0 -> 'E', else '+N' / '-N'."""
    if value == 0:
        return 'E'
    return f'+{value}' if value > 0 else str(value)


def _eclectic_vp_cell(value) -> str:
    """One eclectic cell with background shading driven by ``data-evp``."""
    if pd.isna(value):
        return '<td class="eclectic-cell"><span>-</span></td>'
    v = int(value)
    lbl = _vp_label(v)
    title = f"{lbl} vs par (best)"
    return f'<td class="eclectic-cell" data-evp="{v}" title="{title}"><span>{lbl}</span></td>'


def build_eclectic_scorecard_table(eclectic_df: pd.DataFrame, dimension_col: str) -> str:
    """Render an eclectic pivot as a background-shaded table.

    Args:
        eclectic_df: output of ``calculate_eclectic_by_dimension`` — one row per
            dimension value, integer hole columns (to-par best per hole), plus
            ``Total`` and ``Rounds``. Already sorted best-first.
        dimension_col: name of the label column (e.g. 'Player', 'TEG', 'Team').

    Returns:
        HTML string for the eclectic table.
    """
    if eclectic_df is None or eclectic_df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"

    # Hole header row + a trailing Rounds column (no PAR row: values are to-par).
    parts = ['<table class="scorecard-table eclectic-scorecard"><thead>']
    header = _build_hole_header_row('player-label', dimension_col)
    header = header.replace('</tr>', '<th class="hole-header totals">Rounds</th></tr>')
    parts.append(header)
    parts.append('</thead><tbody>')

    for _, row in eclectic_df.iterrows():
        label = row[dimension_col]
        parts.append(f'<tr><td class="player-label">{label}</td>')

        front = [row[h] for h in range(1, 10) if h in eclectic_df.columns]
        back = [row[h] for h in range(10, 19) if h in eclectic_df.columns]
        front_tot = int(sum(v for v in front if pd.notna(v)))
        back_tot = int(sum(v for v in back if pd.notna(v)))
        total = int(row['Total']) if pd.notna(row.get('Total')) else front_tot + back_tot

        for hole in range(1, 10):
            parts.append(_eclectic_vp_cell(row[hole] if hole in eclectic_df.columns else None))
        parts.append(f'<td class="totals front-back-divider">{_vp_label(front_tot)}</td>')
        for hole in range(10, 19):
            parts.append(_eclectic_vp_cell(row[hole] if hole in eclectic_df.columns else None))
        parts.append(f'<td class="totals">{_vp_label(back_tot)}</td>')
        parts.append(f'<td class="totals">{_vp_label(total)}</td>')
        rounds = int(row['Rounds']) if pd.notna(row.get('Rounds')) else ''
        parts.append(f'<td class="totals">{rounds}</td>')
        parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)
