"""Latest TEG section routes: /latest-round, /latest-teg, /handicaps."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from teg_analysis.reporting.newspaper_edition import (
    available_rounds as _report_available_rounds,
    available_tegs as _report_available_tegs,
)

from teg_analysis.constants import HANDICAPS_CSV
from teg_analysis.core.players import get_name_to_code, get_player_name
from teg_analysis.io.file_operations import read_file
from teg_analysis.analysis.aggregation import (
    get_round_data,
    get_latest_round_defaults,
    get_teg_data_inc_in_progress,
    prepare_round_context_display,
    prepare_teg_context_display,
    get_round_metric_mappings,
)
from teg_analysis.analysis.records import (
    identify_aggregate_records_and_pbs,
    identify_all_time_worsts,
    identify_9hole_records_and_pbs,
    identify_streak_records,
    identify_score_count_records,
)
from teg_analysis.analysis.scoring import format_vs_par
from teg_analysis.analysis.handicaps import (
    get_hc,
    get_current_handicaps_formatted,
    get_next_teg_and_check_if_in_progress_fast,
)
from teg_analysis.analysis.aggregation import get_current_in_progress_teg_fast
from teg_analysis.analysis.streaks import get_player_window_streaks, build_streaks, pivot_window_streaks
from teg_analysis.analysis.scoring import count_scores_by_player
from teg_analysis.analysis.eclectic import (
    calculate_eclectic_by_dimension,
    rank_teg_eclectics,
)
from teg_analysis.core.metadata import get_scorecard_data, get_teg_metadata
from teg_analysis.display.scorecards import (
    build_round_comparison_responsive,
    build_eclectic_scorecard_table,
    build_bestball_worstball_scorecard,
    build_bestball_contribution_bars,
    build_teg_eclectic_scorecard,
    build_eclectic_contribution_bars,
)
from webapp.deps import (
    cached_load_all_data,
    bestball_worstball_totals,
    cached_round_data,
    cached_ranked_teg_data,
    cached_ranked_round_data,
    cached_streaks_data,
    cached_complete_teg_data,
    get_available_teg_numbers,
    get_default_teg_num,
    get_rounds_for_teg,
    parse_teg_label,
)
from webapp.chart_utils import create_round_graph, format_value, get_round_player_color_map
from webapp.tables import df_to_html as _table_df_to_html

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _df_to_html(df: pd.DataFrame, table_class: str = "teg-table") -> str:
    """Render a teg-table: first column left-aligned (player / label),
    remaining columns centred — consistent with the /results tables."""
    return _table_df_to_html(
        df, table_class=table_class,
        col_class=lambda i, col: "col-player" if i == 0 else "col-num",
    )




def _round_context_header(teg_num: int, round_num: int) -> str:
    """Build 'Course | Date' display string for a specific round."""
    try:
        meta = get_teg_metadata(teg_num, round_num)
        return " | ".join(p for p in [meta.get('Course', ''), meta.get('Date', '')] if p)
    except Exception:
        return ""


def _teg_context_header(teg_num: int) -> str:
    """Build 'Area | Year' display string for a TEG."""
    try:
        meta = get_teg_metadata(teg_num)
        area = meta.get('Area', '') or ''
        year = meta.get('Year', '')
        year_str = str(int(year)) if year and str(year).strip() else ''
        return " | ".join(p for p in [area, year_str] if p)
    except Exception:
        return ""


def _fmt_record_value(value, metric: str) -> str:
    """Format a record value: vs-par notation for GrossVP/NetVP, else integer."""
    if metric in ('GrossVP', 'NetVP'):
        return format_vs_par(value)
    return str(int(value))


def _player_score_mix(counts: pd.DataFrame, player_code: str, field: str) -> str:
    """Render one player's per-hole score distribution as 'label: count, ...'.

    ``counts`` is a count_scores_by_player(round_data, field) matrix (score
    value -> row, player code -> column); this slices out one player's
    column and formats each score level the same way the Scoring tab does
    (_format_scoring_display / format_vs_par) rather than inventing a new
    formatting scheme: vs-par notation for GrossVP, plain point values for
    Stableford.
    """
    if counts is None or counts.empty or player_code not in counts.columns:
        return ''
    col = counts[player_code]
    col = col[col > 0]
    parts = []
    for score_val, count in col.items():
        label = format_vs_par(int(score_val)) if field == 'GrossVP' else str(int(score_val))
        parts.append(f"{label}: {int(count)}")
    return ', '.join(parts)


def _compact_player_name(name: str) -> str:
    """'Jon Baker' -> 'J. Baker'. Ported from the approved prototype's
    compactName() (report_layout_prototypes/mobile_data.js) -- avoids the
    mid-word ellipsis truncation a narrow Player column otherwise forces
    ("David M...", "Gregg W..."). Unlike the prototype we don't force the
    surname's casing: player names in this repo (players.csv / get_player_name)
    are already properly cased, so there's nothing to normalise."""
    parts = str(name or '').split()
    if len(parts) < 2:
        return name
    return f"{parts[0][0]}. {' '.join(parts[1:])}"


def _build_scoreboard_table(values: pd.DataFrame, mix_counts: pd.DataFrame,
                            mix_field: str, uid_prefix: str) -> str:
    """Render the Scoreboards-tab table: a 5-column main row (# / Player /
    Personal rank / All-time rank / Total) plus a per-player expandable
    detail row (Out/In split + per-hole score mix), collapsed by default.

    Visual language (column order, .leaderboard table styling, .rank-toggle
    "+"/"-" disclosure, .detail-grid) is ported from the approved prototype
    at report_layout_prototypes/mobile_data.{js,css} -- see the matching CSS
    in webapp/static/mobile.css -- with one explicit swap the user made:
    the prototype's main row is # / Player / Out / In / Total; this one
    is # / Player / Personal rank / All-time rank / Total, with Out/In
    (plus a score mix the prototype doesn't have) moved into the detail row.
    ``values`` columns: Rank, Pl, Player, Out, In, Total (already
    display-formatted strings), Personal rank, All-time rank.
    """
    from html import escape

    def rank_cell(value) -> str:
        """Keep rank text accessible while de-emphasising its denominator."""
        text = str(value)
        if '/' not in text:
            return escape(text)
        numerator, denominator = text.split('/', 1)
        return (f'<span class="lr-rank-value">{escape(numerator)}'
                f'<small>/{escape(denominator)}</small></span>')

    out = ["<table class='teg-table leaderboard'><colgroup>",
           "<col class='lr-rank-col'><col class='lr-player-col'>",
           "<col class='lr-personal-col'><col class='lr-alltime-col'><col class='lr-total-col'>",
           "</colgroup><thead><tr>",
           "<th scope='col'>#</th>",
           "<th scope='col'>Player</th>",
           "<th scope='col'>Personal rank</th>",
           "<th scope='col'>All-time rank</th>",
           "<th scope='col'>Total</th>",
           "</tr></thead><tbody>"]

    for _, row in values.iterrows():
        code = str(row['Pl'])
        detail_id = f"{uid_prefix}-{code}"
        mix = _player_score_mix(mix_counts, code, mix_field)
        personal_rank = row.get('Personal rank') or '—'
        all_time_rank = row.get('All-time rank') or '—'
        row_class = " class='rank-1'" if str(row['Rank']) == '1' else ''
        out.append(
            f"<tr{row_class}>"
            f"<td>{escape(str(row['Rank']))}</td>"
            "<td class='player-name'>"
            f"<button type=\"button\" class=\"rank-toggle\" data-lr-rank-toggle "
            f"aria-expanded=\"false\" aria-controls=\"{escape(detail_id)}\">"
            f"<b>{escape(_compact_player_name(str(row['Player'])))}</b></button></td>"
            f"<td>{rank_cell(personal_rank)}</td>"
            f"<td>{rank_cell(all_time_rank)}</td>"
            f"<td>{escape(str(row['Total']))}</td>"
            "</tr>"
        )
        out.append(
            f"<tr class=\"rank-detail-row\" id=\"{escape(detail_id)}\" hidden>"
            "<td colspan=\"5\">"
            "<div class=\"detail-grid\">"
            f"<span>Out<b>{escape(str(row['Out']))}</b></span>"
            f"<span>In<b>{escape(str(row['In']))}</b></span>"
            "</div>"
            "<p class=\"detail-mix\">"
            "<span class=\"detail-mix-label\">Score mix</span> "
            f"{escape(mix) if mix else '—'}"
            "</p>"
            "</td></tr>"
        )

    out.append("</tbody></table>")
    return ''.join(out)


def _intify_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Cast every numeric column to int so counts/scores show as whole numbers
    (not '0.0') in both the cells and the row-header column."""
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].astype('int64')
    return out


def _format_scoring_display(counts: pd.DataFrame, field: str, mode: str) -> tuple:
    """Format a score-count pivot for display. Returns (display_df, title).

    First column (the score index) is formatted as vs-par labels for GrossVP
    or plain integers for Stableford. Data columns show raw integer counts or
    '<n>%' strings depending on mode.
    """
    friendly = dict(SCORING_FIELDS).get(field, field)
    if mode == "pct":
        col_sums = counts.sum(axis=0).replace(0, 1)
        display_df = counts.div(col_sums, axis=1).mul(100).round(0).astype(int)
        title = f"Score Distribution — % of holes ({friendly})"
    else:
        display_df = _intify_numeric(counts)
        title = f"Score Counts ({friendly})"

    display_df = display_df.reset_index()
    idx_col = display_df.columns[0]

    if field == 'GrossVP':
        display_df[idx_col] = display_df[idx_col].apply(lambda v: format_vs_par(int(v)))
    else:
        display_df[idx_col] = display_df[idx_col].apply(lambda v: str(int(v)))

    if mode == "pct":
        for col in display_df.columns[1:]:
            display_df[col] = display_df[col].apply(lambda v: f"{int(v)}%")

    return display_df, title


def _bestball_rank_summary(bb_all: pd.DataFrame, wb_all: pd.DataFrame,
                           teg_num: int, round_num: int) -> str:
    """Build the 'ranks N / M all-time' summary for this round's bestball and
    worstball totals. Both rank ascending: rank 1 = lowest GrossVP."""
    def _one(df: pd.DataFrame, label: str) -> str:
        d = df.copy()
        d['__r'] = d['GrossVP'].rank(method='min', ascending=True).astype(int)
        row = d[(d['TEGNum'] == teg_num) & (d['Round'] == round_num)]
        if row.empty:
            return ''
        vp = int(row['GrossVP'].iloc[0])
        rank = int(row['__r'].iloc[0])
        return ('<div class="bw-rank-row">'
                f'<span class="bw-rank-label">{label}</span>'
                '<span class="bw-rank-num">'
                f'<strong>{format_vs_par(vp)}</strong>'
                f'<span class="bw-rank-detail">({rank} / {len(d)})</span>'
                '</span>'
                '</div>')

    parts = [p for p in (_one(bb_all, 'Bestball'), _one(wb_all, 'Worstball')) if p]
    if not parts:
        return ''
    return '<div class="bw-rank-summary">' + ''.join(parts) + '</div>'


_RECORDS_DRAFT_NOTE = (
    "<p class='text-muted text-sm mb-2'>⚠️ Draft — the records and PBs below "
    "need to be verified before the site is published.</p>"
)


def _render_records_summary(rd: dict, page_type: str = 'TEG') -> str:
    """Render the records/PBs dict as grouped HTML (mirrors the Streamlit summary)."""
    from collections import defaultdict

    total = sum(len(rd.get(k, [])) for k in (
        'aggregate_records', 'aggregate_pbs', 'aggregate_worsts', 'all_time_worsts',
        '9hole_records', '9hole_pbs', 'streak_records', 'best_score_counts', 'worst_score_counts'))
    if total == 0:
        return f"<p class='text-muted text-sm'>No records or personal bests for this {page_type.lower()}.</p>"

    out = []

    # --- All-time records (bests) ---
    bests = []
    for r in rd.get('aggregate_records', []):
        bests.append(f"<strong>{r['friendly_name']}:</strong> {_fmt_record_value(r['value'], r['metric'])} ({r['player']})")
    for r in rd.get('9hole_records', []):
        bests.append(f"<strong>{r['segment']} 9 - {r['friendly_name']}:</strong> {_fmt_record_value(r['value'], r['metric'])} ({r['player']})")
    for r in rd.get('streak_records', []):
        bests.append(f"<strong>{r['streak_type']} streak:</strong> {r['value']} holes ({r['player']})")
    for r in rd.get('best_score_counts', []):
        bests.append(f"<strong>Most {r['score_type']}:</strong> {r['count']} ({r['player']})")
    if bests:
        out.append("<h2 class='section-title'>🏆 All-Time Records (Bests)</h2><ul class='records-list'>")
        out += [f"<li>{b}</li>" for b in bests]
        out.append("</ul>")

    # --- All-time records (worsts) ---
    worsts = []
    for r in rd.get('all_time_worsts', []):
        worsts.append(f"<strong>Worst {r['friendly_name']}:</strong> {_fmt_record_value(r['value'], r['metric'])} ({r['player']})")
    for r in rd.get('worst_score_counts', []):
        worsts.append(f"<strong>Most {r['score_type']}:</strong> {r['count']} ({r['player']})")
    if worsts:
        out.append("<h2 class='section-title'>💀 All-Time Records (Worsts)</h2><ul class='records-list'>")
        out += [f"<li>{w}</li>" for w in worsts]
        out.append("</ul>")

    # --- Personal bests (grouped by player) ---
    pbs_by_player = defaultdict(list)
    for pb in rd.get('aggregate_pbs', []):
        pbs_by_player[pb['player']].append(f"{pb['friendly_name']}: {_fmt_record_value(pb['value'], pb['metric'])}")
    for pb in rd.get('9hole_pbs', []):
        pbs_by_player[pb['player']].append(f"{pb['segment']} 9 - {pb['friendly_name']}: {_fmt_record_value(pb['value'], pb['metric'])}")
    if pbs_by_player:
        out.append("<h2 class='section-title'>⭐ Personal Bests</h2><ul class='records-list'>")
        for player in sorted(pbs_by_player):
            out.append(f"<li><strong>{player}:</strong> {', '.join(pbs_by_player[player])}</li>")
        out.append("</ul>")

    # --- Personal worsts (grouped by player) ---
    worsts_by_player = defaultdict(list)
    for w in rd.get('aggregate_worsts', []):
        worsts_by_player[w['player']].append(f"{w['friendly_name']}: {_fmt_record_value(w['value'], w['metric'])}")
    if worsts_by_player:
        out.append("<h2 class='section-title'>⚠️ Personal Worsts</h2><ul class='records-list'>")
        for player in sorted(worsts_by_player):
            out.append(f"<li><strong>{player}:</strong> {', '.join(worsts_by_player[player])}</li>")
        out.append("</ul>")

    return "".join(out)


# --- /latest-round ------------------------------------------------------------

LATEST_ROUND_TABS = [
    ("scoreboard", "Scoreboards"),
    ("scorecard", "Scorecard"),
    ("bestball", "Bestball / Worstball"),
    ("scoring", "Scoring"),
    ("streaks", "Streaks"),
    ("records", "Records & PBs"),
]

# Scoring-tab score-type toggle (Gross vs Par / Stableford)
SCORING_FIELDS = [("GrossVP", "Gross vs Par"), ("Stableford", "Stableford")]

# Metric sub-tabs for the Scoreboards (round) / Aggregate (TEG) tabs
METRIC_TABS = [("Sc", "Score"), ("Stableford", "Stableford"), ("GrossVP", "Gross vs Par"), ("NetVP", "Net vs Par")]


def _echo_chart_state(ctx: dict, metric: str, scale: str, player: str, rewind) -> dict:
    """Fill in active_metric/chart_scale/chart_player/chart_rewind when the
    tab body didn't already set them (every tab except scoreboard, which
    validates and returns its own). Without this, #lr-chart-state's OOB
    fragment falls back to hardcoded template defaults on every non-scoreboard
    tab, silently resetting the user's real metric/scale/player/rewind
    selection the moment they switch away from Scoreboards and back."""
    ctx.setdefault("active_metric", metric if metric in dict(METRIC_TABS) else "Sc")
    ctx.setdefault("chart_scale", scale if scale in ("normal", "adjusted") else "normal")
    ctx.setdefault("chart_player", player or "")
    try:
        ctx.setdefault("chart_rewind", max(1, min(int(rewind or 18), 18)))
    except (TypeError, ValueError):
        ctx.setdefault("chart_rewind", 18)
    return ctx


def _latest_round_tab_context(teg_num: int, round_num: int, tab: str,
                              score_type: str = "GrossVP", metric: str = "Sc",
                              display_mode: str = "count", scale: str = "normal",
                              player: str = "", rewind: int = 18) -> dict:
    try:
        rd_data = cached_round_data()
        teg_rd = rd_data[(rd_data['TEGNum'] == teg_num) & (rd_data['Round'] == round_num)]

        if teg_rd.empty:
            return {"error": f"No data for TEG {teg_num} Round {round_num}"}

        sections = []

        if tab == "scoreboard":
            metric = metric if metric in dict(METRIC_TABS) else "Sc"
            scale = scale if scale in ("normal", "adjusted") else "normal"
            if metric not in ("Stableford", "GrossVP"):
                scale = "normal"
            valid_players = {str(p) for p in teg_rd['Pl'].dropna().unique()}
            player = player if player in valid_players else ""
            try:
                rewind = max(1, min(int(rewind or 18), 18))
            except (TypeError, ValueError):
                rewind = 18
            friendly = dict(METRIC_TABS)[metric]
            teg_str = f"TEG {teg_num}"
            try:
                score_data = cached_load_all_data()
                score_data = score_data[(score_data['TEG'] == teg_str) & (score_data['Round'] == round_num)]
                grouped = score_data.groupby('Pl', sort=False)
                values = grouped[metric].sum().rename('Total').to_frame()
                values['Out'] = score_data[score_data['Hole'] < 10].groupby('Pl')[metric].sum()
                values['In'] = score_data[score_data['Hole'] >= 10].groupby('Pl')[metric].sum()
                values = values.reset_index()
                ascending = metric != 'Stableford'
                values = values.sort_values('Total', ascending=ascending).reset_index(drop=True)
                values.insert(0, 'Rank', values['Total'].rank(method='min', ascending=ascending).astype(int))
                values['Player'] = values['Pl'].map(lambda code: get_player_name(str(code)))
                for col in ('Out', 'In', 'Total'):
                    values[col] = values[col].apply(lambda v: _fmt_record_value(v, metric))

                # Personal-rank / all-time-rank context, reusing the same
                # ranked-round-data helper the pre-mobile-rollout scoreboard
                # table used (prepare_round_context_display) rather than
                # recomputing Rank_within_player_*/Rank_within_all_* by hand.
                # Its output keys on 'Player' (display name), which the
                # aggregated round data agrees on for the same TEG/round.
                try:
                    ranked = cached_ranked_round_data()
                    ctx_df = prepare_round_context_display(ranked, teg_str, round_num, metric, friendly)
                    rank_ctx = ctx_df[['Player', 'Pl rank', 'All time rank']].rename(
                        columns={'Pl rank': 'Personal rank', 'All time rank': 'All-time rank'})
                    values = values.merge(rank_ctx, on='Player', how='left')
                    # Tighten "n / N" -> "n/N" -- cosmetic only, saves the
                    # width these two columns can't spare at phone widths.
                    for col in ('Personal rank', 'All-time rank'):
                        values[col] = values[col].astype(str).str.replace(' / ', '/', regex=False)
                except Exception:
                    logger.exception("_latest_round_tab_context: personal/all-time rank context failed")
                    values['Personal rank'] = ''
                    values['All-time rank'] = ''

                # Per-hole score mix for the expandable detail row -- reuses
                # the Scoring tab's own field selection (GrossVP vs-par
                # notation, or Stableford point counts; Sc/NetVP have no
                # separate per-hole formatting elsewhere in this file, so
                # they fall back to the same GrossVP-style mix).
                mix_field = 'Stableford' if metric == 'Stableford' else 'GrossVP'
                mix_counts = count_scores_by_player(score_data, mix_field)

                table_html = _build_scoreboard_table(
                    values, mix_counts, mix_field,
                    uid_prefix=f"lr-rank-{teg_num}-{round_num}")
            except Exception:
                logger.exception("_latest_round_tab_context: scoreboard table build failed")
                table_html = "<p class='text-muted text-sm'>No data.</p>"
            chart_title = f"Cumulative {friendly} through round"
            y_series = f"{metric} Cum Round"
            metric_chart_type = {"Sc": "default", "GrossVP": "gross", "NetVP": "gross", "Stableford": "stableford"}
            chart_type = metric_chart_type.get(metric, "default")
            figure_json = None
            chart_build_error = None
            chart_readout = []
            try:
                all_data = cached_load_all_data()
                fig = create_round_graph(
                    all_data, teg_str, round_num, y_series, title=chart_title,
                    y_axis_label=f"Cumulative {friendly}", chart_type=chart_type,
                    scale=scale, rewind=rewind,
                    focus_player=player,
                )
                figure_json = fig.to_json()
            except Exception:
                # Previously a bare `pass`: figure_json stayed None and the
                # whole chart+tools block (title, chart, focus readout, scale
                # switch, rewind) silently disappeared from the page with no
                # indication anything failed. Mirror the scoreboard table's
                # own failure pattern (line ~472) instead of staying silent.
                logger.exception("_latest_round_tab_context: chart build failed")
                chart_build_error = "Chart unavailable for this round."
            point = max(1, min(rewind, 18))
            readout_data = teg_rd
            try:
                readout_data = cached_load_all_data()
                readout_data = readout_data[(readout_data['TEG'] == teg_str) & (readout_data['Round'] == round_num)]
            except Exception:
                pass
            # Same colour mapping create_round_graph uses for the chart lines
            # -- so a player's code in the readout below is styled in their
            # actual line colour, not a fixed generic accent colour.
            try:
                round_color_map = get_round_player_color_map(cached_load_all_data(), teg_str, round_num)
            except Exception:
                round_color_map = {}
            for code, player_df in readout_data.groupby('Pl', sort=False):
                if y_series not in player_df.columns:
                    continue
                upto = player_df[player_df['Hole'] <= point].sort_values('Hole')
                if upto.empty:
                    continue
                value = upto[y_series].iloc[-1]
                if scale == 'adjusted':
                    value -= (2 * point if chart_type == 'stableford' else point if chart_type == 'gross' else 0)
                chart_readout.append({"code": str(code), "name": get_player_name(str(code)),
                                      "value": format_value(value, chart_type),
                                      "active": str(code) == player,
                                      "color": round_color_map.get(code, '')})
            return {"sections": [{"title": friendly, "table_html": table_html}],
                    "metric_tabs": METRIC_TABS, "active_metric": metric,
                    "chart_title": chart_title,
                    "figure_json": figure_json,
                    "chart_build_error": chart_build_error,
                    "chart_players": sorted(str(p) for p in teg_rd['Pl'].dropna().unique()),
                    "chart_readout": chart_readout,
                    "chart_scale": scale, "chart_player": player,
                    "chart_rewind": rewind}

        elif tab == "scorecard":
            try:
                round_data = get_scorecard_data(teg_num, round_num, data=cached_load_all_data())
                if round_data is None or round_data.empty:
                    sections.append({"title": "Scorecard", "table_html": "<p class='text-muted text-sm'>No scorecard data.</p>"})
                else:
                    # Responsive block: landscape on desktop/iPad, portrait on phone.
                    block = build_round_comparison_responsive(round_data, uid=f"lr{teg_num}r{round_num}")
                    sections.append({"title": None, "table_html": block, "raw": True})
                return {"sections": sections, "scorecard_css": True}
            except Exception as e:
                logger.exception("_latest_round_tab_context failed")
                sections.append({"title": "Scorecard", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        elif tab == "bestball":
            try:
                all_data = cached_load_all_data()
                round_data = all_data[(all_data['TEGNum'] == teg_num) & (all_data['Round'] == round_num)]
                if round_data.empty:
                    sections.append({"title": "Bestball / Worstball", "table_html": "<p class='text-muted text-sm'>No data.</p>"})
                    return {"sections": sections}

                # All-time ranks first — shown at the top. Sourced from the
                # maintained bestball cache (falls back to live computation).
                bb_all, wb_all = bestball_worstball_totals(all_data)
                rank_html = _bestball_rank_summary(bb_all, wb_all, teg_num, round_num)
                if rank_html:
                    sections.append({"title": None, "table_html": rank_html, "raw": True})

                card_html = build_bestball_worstball_scorecard(round_data)
                sections.append({"title": None, "table_html": card_html})

                # Per-player contribution breakdown (CSS bar charts) below the card.
                bars_html = build_bestball_contribution_bars(round_data)
                sections.append({"title": "Player contributions", "table_html": bars_html})
                sections.append({
                    "title": None, "raw": True,
                    "table_html": (
                        "<p class='caption'>"
                        "<strong>Holes &amp; solo</strong>: holes where the player matched the "
                        "field best (bestball) or worst (worstball), and how many of those they "
                        "drove alone. <strong>Impact</strong>: the player's net effect on the "
                        "team total, counting only their solo holes — bestball negative (shots "
                        "they saved), worstball positive (shots they added).</p>"
                    ),
                })
                return {"sections": sections, "scorecard_css": True}
            except Exception as e:
                logger.exception("_latest_round_tab_context failed")
                sections.append({"title": "Bestball / Worstball", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        elif tab == "records":
            try:
                ranked = cached_ranked_round_data()
                all_data = cached_load_all_data()
                streaks_df = cached_streaks_data()
                teg_str = f"TEG {teg_num}"

                from webapp.deps import cached_ranked_frontback_data
                agg = identify_aggregate_records_and_pbs(ranked, teg_str, round_num)
                nine = identify_9hole_records_and_pbs(teg_str, round_num, cached_ranked_frontback_data())
                streak = identify_streak_records(all_data, streaks_df, teg_str, round_num)
                counts = identify_score_count_records(all_data, teg_str, round_num)
                rd_dict = {
                    'aggregate_records': agg['records'],
                    'aggregate_pbs': agg['personal_bests'],
                    'aggregate_worsts': agg['personal_worsts'],
                    'all_time_worsts': identify_all_time_worsts(ranked, teg_str, round_num),
                    '9hole_records': nine['records'],
                    '9hole_pbs': nine['personal_bests'],
                    'streak_records': streak['records'],
                    'best_score_counts': counts['best_score_counts'],
                    'worst_score_counts': counts['worst_score_counts'],
                }
                sections.append({"title": None, "table_html": _render_records_summary(rd_dict, 'Round')})
            except Exception as e:
                logger.exception("_latest_round_tab_context failed")
                sections.append({"title": "Records & PBs", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        elif tab == "scoring":
            field = score_type if score_type in ("GrossVP", "Stableford") else "GrossVP"
            mode = display_mode if display_mode in ("count", "pct") else "count"
            all_data = cached_load_all_data()
            round_data = all_data[(all_data['TEGNum'] == teg_num) & (all_data['Round'] == round_num)]
            if not round_data.empty:
                counts = count_scores_by_player(round_data, field)
                display_df, title = _format_scoring_display(counts, field, mode)
                sections.append({"title": title, "table_html": _df_to_html(display_df)})
            else:
                sections.append({"title": "Scoring", "table_html": "<p class='text-muted text-sm'>No scoring data.</p>"})
            return {"sections": sections, "scoring_fields": SCORING_FIELDS, "score_type": field, "display_mode": mode}

        elif tab == "streaks":
            try:
                all_data = cached_load_all_data()
                streaks_df = cached_streaks_data()
                teg_str = f"TEG {teg_num}"
                window = get_player_window_streaks(all_data, streaks_df, teg=teg_str, round_num=round_num)
                pivot = pivot_window_streaks(window)
                if not pivot.empty:
                    sections.append({"title": "Streaks", "table_html": _df_to_html(pivot)})
                    return {"sections": sections, "caption": "Eagles / birdies / par / bogeys are all 'or better'"}
                sections.append({"title": "Streaks", "table_html": "<p class='text-muted text-sm'>No streak data for this round.</p>"})
            except Exception as e:
                logger.exception("_latest_round_tab_context failed")
                sections.append({"title": "Streaks", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        return {"sections": sections}
    except Exception as e:
        logger.exception("_latest_round_tab_context failed")
        return {"error": str(e)}


@router.get("/latest-round")
def latest_round_page(request: Request, teg: Optional[str] = Query(None),
                       round: Optional[str] = Query(None),
                       tab: str = Query("scoreboard"), metric: str = Query("Sc"),
                       scale: str = Query("normal"), player: str = Query(""),
                       rewind: str = Query("18")):
    rd_data = cached_round_data()
    teg_numbers = get_available_teg_numbers()
    # Deep-link support (e.g. from /teg-reports' "Back to Round N" link) — an
    # invalid/absent teg or round falls back to the latest-played default.
    try:
        requested_teg = int(teg) if teg is not None else None
    except (TypeError, ValueError):
        requested_teg = None
    if requested_teg in teg_numbers:
        teg_num = requested_teg
        rounds = get_rounds_for_teg(teg_num)
        try:
            requested_round = int(round) if round is not None else None
        except (TypeError, ValueError):
            requested_round = None
        round_num = requested_round if requested_round in rounds else (rounds[-1] if rounds else 1)
    else:
        teg_str, round_num = get_latest_round_defaults(rd_data)
        teg_num = parse_teg_label(teg_str)
        rounds = get_rounds_for_teg(teg_num)
    context_header = _round_context_header(teg_num, int(round_num))
    active_tab = tab if tab in {item[0] for item in LATEST_ROUND_TABS} else "scoreboard"
    ctx = _latest_round_tab_context(teg_num, int(round_num), active_tab,
                                    metric=metric, scale=scale, player=player,
                                    rewind=rewind)
    ctx = _echo_chart_state(ctx, metric, scale, player, rewind)
    return templates.TemplateResponse("latest_round.html", {
        "request": request,
        "active_page": "latest-round",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "rounds": rounds,
        "selected_round": round_num,
        # teg/round also feed the in-partial pill hx-vals on first render.
        "teg": teg_num,
        "round": int(round_num),
        "tabs": LATEST_ROUND_TABS,
        "active_tab": active_tab,
        "context_header": context_header,
        # {teg: [rounds with a newspaper round report]} for every TEG this
        # page can show — drives the Report link (a real navigation to
        # /teg-reports?teg=N&round=R, not an HTMX tab) and its visibility.
        # The TEG select and round pills both swap #lr-content via HTMX
        # without a page reload, and the Report link sits outside that swap
        # target, so this whole map ships up front rather than being
        # refetched per selection (same reasoning as /results' report_tegs).
        "report_rounds_map": {t: list(_report_available_rounds(t)) for t in teg_numbers
                               if _report_available_rounds(t)},
        **ctx,
    })


@router.get("/latest-round/tab")
def latest_round_tab(request: Request, teg: str = Query(...), round: str = Query(...),
                           tab: str = Query("scoreboard"), score_type: str = Query("GrossVP"),
                           metric: str = Query("Sc"), display_mode: str = Query("count"),
                           scale: str = Query("normal"), player: str = Query(""),
                           rewind: str = Query("18")):
    teg_numbers = get_available_teg_numbers()
    try:
        teg_num = int(teg)
    except (TypeError, ValueError):
        teg_num = get_default_teg_num()
    if teg_num not in teg_numbers:
        teg_num = get_default_teg_num()
    teg = teg_num
    rounds = get_rounds_for_teg(teg)
    try:
        round_num_requested = int(round)
    except (TypeError, ValueError):
        round_num_requested = None
    round_num = round_num_requested if round_num_requested in rounds else (rounds[-1] if rounds else 1)
    if tab not in {item[0] for item in LATEST_ROUND_TABS}:
        tab = "scoreboard"
    ctx = _latest_round_tab_context(teg, round_num, tab, score_type, metric, display_mode,
                                    scale=scale, player=player, rewind=rewind)
    ctx = _echo_chart_state(ctx, metric, scale, player, rewind)
    return templates.TemplateResponse("partials/latest_round_tab.html", {
        "request": request,
        "teg": teg,
        "round": round_num,
        "tab": tab,
        "rounds": rounds,
        "context_header": _round_context_header(teg, round_num),
        **ctx,
    })


# --- /latest-teg --------------------------------------------------------------

LATEST_TEG_TABS = [
    ("aggregate", "Aggregate Score"),
    ("scoring", "Scoring"),
    ("eclectic", "Eclectic"),
    ("streaks", "Streaks"),
    ("records", "Records & PBs"),
]


def _latest_teg_tab_context(teg_num: int, tab: str, score_type: str = "GrossVP", metric: str = "Sc",
                            display_mode: str = "count") -> dict:
    """Build template context for a latest-teg tab."""
    try:
        sections = []

        if tab == "aggregate":
            metric = metric if metric in dict(METRIC_TABS) else "Sc"
            friendly = dict(METRIC_TABS)[metric]
            teg_str = f"TEG {teg_num}"
            try:
                ranked = cached_ranked_teg_data()
                ctx_df = prepare_teg_context_display(ranked, teg_str, metric, friendly)
                if friendly in ctx_df.columns:
                    ctx_df[friendly] = ctx_df[friendly].apply(lambda v: _fmt_record_value(v, metric))
                table_html = _df_to_html(ctx_df)
            except Exception:
                table_html = "<p class='text-muted text-sm'>No aggregate data available.</p>"
            return {"sections": [{"title": friendly, "table_html": table_html}],
                    "metric_tabs": METRIC_TABS, "active_metric": metric}

        elif tab == "scoring":
            field = score_type if score_type in ("GrossVP", "Stableford") else "GrossVP"
            mode = display_mode if display_mode in ("count", "pct") else "count"
            all_data = cached_load_all_data()
            teg_data = all_data[all_data['TEGNum'] == teg_num]
            if not teg_data.empty:
                counts = count_scores_by_player(teg_data, field)
                display_df, title = _format_scoring_display(counts, field, mode)
                sections.append({"title": title, "table_html": _df_to_html(display_df)})
            else:
                sections.append({"title": "Scoring", "table_html": "<p class='text-muted text-sm'>No scoring data.</p>"})
            return {"sections": sections, "scoring_fields": SCORING_FIELDS, "score_type": field, "display_mode": mode}

        elif tab == "eclectic":
            try:
                all_data = cached_load_all_data()
                eclectic_df, display_dim = calculate_eclectic_by_dimension(all_data, "TEGNum")
                if eclectic_df.empty:
                    sections.append({"title": "Eclectic", "table_html": "<p class='text-muted text-sm'>No data.</p>"})
                    return {"sections": sections}
                teg_label = f"TEG {teg_num}"
                ranked = eclectic_df.copy()
                ranked['__r'] = ranked['Total'].rank(method='min', ascending=True).astype(int)
                this_row = ranked[ranked[display_dim] == teg_label]
                if this_row.empty:
                    sections.append({"title": "Eclectic", "table_html": "<p class='text-muted text-sm'>No eclectic data for this TEG.</p>"})
                    return {"sections": sections}
                rank = int(this_row['__r'].iloc[0])
                total_val = int(this_row['Total'].iloc[0])
                total_tegs = len(ranked)

                # Rank summary at the top.
                rank_html = ('<div class="bw-rank-summary"><div class="bw-rank-row">'
                             '<span class="bw-rank-label">Best eclectic</span>'
                             '<span class="bw-rank-num">'
                             f'<strong>{format_vs_par(total_val)}</strong>'
                             f'<span class="bw-rank-detail">({rank} / {total_tegs})</span>'
                             '</span></div></div>')
                sections.append({"title": None, "table_html": rank_html, "raw": True})

                # Player ranks table: eclectic total vs all-time (complete TEGs
                # only) and vs the player's own history.
                complete_teg_nums = set(cached_complete_teg_data()['TEGNum'])
                ranks_df = rank_teg_eclectics(all_data, teg_num, complete_teg_nums=complete_teg_nums)
                if not ranks_df.empty:
                    display_ranks = pd.DataFrame({
                        'Player': ranks_df['Player'],
                        'Eclectic': ranks_df['Total'].apply(format_vs_par),
                        'All-time': ranks_df.apply(lambda r: f"{r['AllTimeRank']} / {r['AllTimeN']}", axis=1),
                        'Own history': ranks_df.apply(lambda r: f"{r['OwnRank']} of {r['OwnN']}", axis=1),
                    })
                    sections.append({
                        "title": "Player ranks",
                        "table_html": _table_df_to_html(display_ranks, link_players=True),
                    })
                    if teg_num not in complete_teg_nums:
                        sections.append({
                            "title": None, "raw": True,
                            "table_html": (
                                f"<p class='caption'>TEG {teg_num} is still in progress — its "
                                "eclectic, and these ranks, will improve as more rounds are "
                                "played.</p>"
                            ),
                        })

                # Per-player eclectic scorecard with best eclectic row at the top.
                teg_data = all_data[all_data['TEGNum'] == teg_num]
                card_html = build_teg_eclectic_scorecard(teg_data)
                sections.append({"title": None, "table_html": card_html})

                # Per-player contribution breakdown (CSS bar chart) below the card.
                bars_html = build_eclectic_contribution_bars(teg_data)
                sections.append({"title": "Player contributions", "table_html": bars_html})
                sections.append({
                    "title": None, "raw": True,
                    "table_html": (
                        "<p class='caption'>"
                        "<strong>Holes &amp; solo</strong>: holes where the player's personal "
                        "eclectic matched the team eclectic, and how many of those they reached "
                        "alone. <strong>Impact</strong>: the player's net effect on the team "
                        "eclectic total, counting only their solo holes — always negative or zero "
                        "(shots they saved the team).</p>"
                    ),
                })
                return {"sections": sections, "scorecard_css": True}
            except Exception as e:
                logger.exception("_latest_teg_tab_context failed")
                sections.append({"title": "Eclectic", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        elif tab == "streaks":
            try:
                all_data = cached_load_all_data()
                streaks_df = cached_streaks_data()
                teg_str = f"TEG {teg_num}"
                window = get_player_window_streaks(all_data, streaks_df, teg=teg_str)
                pivot = pivot_window_streaks(window)
                if not pivot.empty:
                    sections.append({"title": "Streaks", "table_html": _df_to_html(pivot)})
                    return {"sections": sections, "caption": "Eagles / birdies / par / bogeys are all 'or better'"}
                sections.append({"title": "Streaks", "table_html": "<p class='text-muted text-sm'>No streak data for this TEG.</p>"})
            except Exception as e:
                logger.exception("_latest_teg_tab_context failed")
                sections.append({"title": "Streaks", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        elif tab == "records":
            try:
                ranked = cached_ranked_teg_data()
                all_data = cached_load_all_data()
                streaks_df = cached_streaks_data()
                teg_str = f"TEG {teg_num}"

                agg = identify_aggregate_records_and_pbs(ranked, teg_str)
                streak = identify_streak_records(all_data, streaks_df, teg_str)
                counts = identify_score_count_records(all_data, teg_str)
                rd_dict = {
                    'aggregate_records': agg['records'],
                    'aggregate_pbs': agg['personal_bests'],
                    'aggregate_worsts': agg['personal_worsts'],
                    'all_time_worsts': identify_all_time_worsts(ranked, teg_str),
                    'streak_records': streak['records'],
                    'best_score_counts': counts['best_score_counts'],
                    'worst_score_counts': counts['worst_score_counts'],
                }
                sections.append({"title": None, "table_html": _render_records_summary(rd_dict, 'TEG')})
            except Exception as e:
                logger.exception("_latest_teg_tab_context failed")
                sections.append({"title": "Records & PBs", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        return {"sections": sections}
    except Exception as e:
        logger.exception("_latest_teg_tab_context failed")
        return {"error": str(e)}


@router.get("/latest-teg")
def latest_teg_page(request: Request):
    teg_num = get_default_teg_num()
    teg_numbers = get_available_teg_numbers()
    ctx = _latest_teg_tab_context(teg_num, "aggregate")
    return templates.TemplateResponse("latest_teg.html", {
        "request": request,
        "active_page": "latest-teg",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "teg": teg_num,
        "tabs": LATEST_TEG_TABS,
        "active_tab": "aggregate",
        "context_header": _teg_context_header(teg_num),
        # Drives the Report tab (a real link to /teg-reports, not an HTMX
        # swap) — same pattern as /results' report_tegs.
        "report_tegs": list(_report_available_tegs()),
        **ctx,
    })


@router.get("/latest-teg/tab")
def latest_teg_tab(request: Request, teg: int = Query(...), tab: str = Query("aggregate"),
                         score_type: str = Query("GrossVP"), metric: str = Query("Sc"),
                         display_mode: str = Query("count")):
    ctx = _latest_teg_tab_context(teg, tab, score_type, metric, display_mode)
    return templates.TemplateResponse("partials/latest_teg_tab.html", {
        "request": request,
        "teg": teg,
        "context_header": _teg_context_header(teg),
        **ctx,
    })


# --- /handicaps ---------------------------------------------------------------

@router.get("/handicaps")
def handicaps_page(request: Request):
    try:
        last_completed, next_tegnum, in_progress = get_next_teg_and_check_if_in_progress_fast()
        next_teg_str = f"TEG {next_tegnum}"
        # current_hc columns: 'Handicap' (player name), '<next_teg_str>' (value), 'Change'.
        current_hc, were_calculated = get_current_handicaps_formatted(next_tegnum - 1, next_tegnum)
        current_hc = current_hc.sort_values(by=next_teg_str, ascending=True).reset_index(drop=True)

        # --- Metric tiles: name / handicap / change (down = good → green). ---
        tiles = []
        for _, row in current_hc.iterrows():
            change = int(row["Change"])
            if change < 0:
                delta_dir, arrow = "down", "↓"
            elif change > 0:
                delta_dir, arrow = "up", "↑"
            else:
                delta_dir, arrow = "none", ""
            # First name proper case, surname(s) in caps.
            parts = str(row["Handicap"]).split(" ")
            name_parts = [parts[0]] + [p.upper() for p in parts[1:]] if parts else parts
            tiles.append({
                "name_parts": name_parts,
                "value": int(row[next_teg_str]),
                "delta_dir": delta_dir,
                "delta_arrow": arrow,
                "delta_text": str(change) if change != 0 else "–",
            })

        ctx = {
            "is_draft": were_calculated,
            "next_teg_label": f"{next_teg_str} Handicaps" + (" (Draft)" if were_calculated else ""),
            "tiles": tiles,
            "draft_html": None,
        }

        # --- Handicap history (initials, oldest-first, '-' for 0/blank). ---
        hc_df = read_file(HANDICAPS_CSV)
        hc_df = hc_df[hc_df["TEG"] != "TEG 50"].copy()
        for col in hc_df.columns:
            if col != "TEG":
                hc_df[col] = hc_df[col].apply(lambda x: "-" if pd.isna(x) or x == 0 else str(int(x)))
        ctx["history_html"] = _df_to_html(hc_df, table_class="teg-table table--full")

        # --- Draft handicaps for the TEG after next (only when one is in progress). ---
        if in_progress:
            try:
                in_progress_teg, rounds_played = get_current_in_progress_teg_fast()
                next_next = next_tegnum + 1
                draft = get_hc(next_next).sort_values("hc_raw", ascending=True, na_position="last").reset_index(drop=True)
                ctx["draft_title"] = f"Draft handicaps for TEG {next_next} (after {rounds_played} rounds of TEG {in_progress_teg})"
                ctx["draft_html"] = _df_to_html(draft)
            except Exception as e:
                logger.exception("handicaps_page failed")
                ctx["draft_title"] = "Draft handicaps"
                ctx["draft_html"] = f"<p class='text-muted text-sm'>Error: {e}</p>"

        return templates.TemplateResponse("handicaps.html", {
            "request": request, "active_page": "handicaps", **ctx,
        })
    except Exception as e:
        logger.exception("handicaps_page failed")
        return templates.TemplateResponse("handicaps.html", {
            "request": request, "active_page": "handicaps", "error": str(e),
        })
