"""Latest TEG section routes: /latest-round, /latest-teg, /handicaps."""

from pathlib import Path

import pandas as pd
import markdown as md_lib
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from teg_analysis.constants import PLAYER_DICT, HANDICAPS_CSV, STREAKS_PARQUET
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
from teg_analysis.core.metadata import get_scorecard_data, get_teg_metadata
from teg_analysis.display.scorecards import (
    build_round_comparison_responsive,
)
from webapp.deps import (
    cached_load_all_data,
    cached_round_data,
    cached_ranked_teg_data,
    cached_ranked_round_data,
    get_available_teg_numbers,
    get_default_teg_num,
    get_rounds_for_teg,
)

_NAME_TO_CODE = {v: k for k, v in PLAYER_DICT.items()}

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _df_to_html(df: pd.DataFrame, table_class: str = "teg-table") -> str:
    """Render a DataFrame as a teg-table: first column left-aligned (player /
    label), remaining columns centred — consistent with the /results tables."""
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"
    cols = list(df.columns)
    rows = [f"<table class='{table_class}'><thead><tr>"]
    for i, col in enumerate(cols):
        cls = "col-player" if i == 0 else "col-num"
        rows.append(f"<th class='{cls}'>{col}</th>")
    rows.append("</tr></thead><tbody>")
    for _, row in df.iterrows():
        rows.append("<tr>")
        for i, col in enumerate(cols):
            cls = "col-player" if i == 0 else "col-num"
            rows.append(f"<td class='{cls}'>{row[col]}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


_COMMENTARY_DIR = Path("data/commentary")
_MD_EXTS = ["extra", "sane_lists", "smarty"]


def _render_report(candidates: list[str]) -> str | None:
    """Render the first existing markdown file (relative to data/commentary) to HTML."""
    for name in candidates:
        path = _COMMENTARY_DIR / name
        if path.is_file():
            return md_lib.markdown(path.read_text(encoding="utf-8"), extensions=_MD_EXTS)
    return None


def _fmt_record_value(value, metric: str) -> str:
    """Format a record value: vs-par notation for GrossVP/NetVP, else integer."""
    if metric in ('GrossVP', 'NetVP'):
        return format_vs_par(value)
    return str(int(value))


def _intify_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Cast every numeric column to int so counts/scores show as whole numbers
    (not '0.0') in both the cells and the row-header column."""
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].astype('int64')
    return out


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
    ("report", "Report"),
    ("scoring", "Scoring"),
    ("streaks", "Streaks"),
    ("records", "Records & PBs"),
]

# Scoring-tab score-type toggle (Gross vs Par / Stableford)
SCORING_FIELDS = [("GrossVP", "Gross vs Par"), ("Stableford", "Stableford")]

# Metric sub-tabs for the Scoreboards (round) / Aggregate (TEG) tabs
METRIC_TABS = [("Sc", "Score"), ("Stableford", "Stableford"), ("GrossVP", "Gross vs Par"), ("NetVP", "Net vs Par")]


def _latest_round_tab_context(teg_num: int, round_num: int, tab: str,
                              score_type: str = "GrossVP", metric: str = "Sc") -> dict:
    try:
        rd_data = cached_round_data()
        teg_rd = rd_data[(rd_data['TEGNum'] == teg_num) & (rd_data['Round'] == round_num)]

        if teg_rd.empty:
            return {"error": f"No data for TEG {teg_num} Round {round_num}"}

        sections = []

        if tab == "scoreboard":
            metric = metric if metric in dict(METRIC_TABS) else "Sc"
            friendly = dict(METRIC_TABS)[metric]
            teg_str = f"TEG {teg_num}"
            try:
                ranked = cached_ranked_round_data()
                ctx_df = prepare_round_context_display(ranked, teg_str, round_num, metric, friendly)
                if friendly in ctx_df.columns:
                    ctx_df[friendly] = ctx_df[friendly].apply(lambda v: _fmt_record_value(v, metric))
                table_html = _df_to_html(ctx_df)
            except Exception:
                table_html = "<p class='text-muted text-sm'>No data.</p>"
            # Per-metric cumulative-through-round chart — placeholder pending the
            # chart rebuild (see webapp/README look-and-feel roadmap, item 1b).
            return {"sections": [{"title": friendly, "table_html": table_html}],
                    "metric_tabs": METRIC_TABS, "active_metric": metric,
                    "chart_placeholder": True,
                    "chart_title": f"Cumulative {friendly} through round",
                    "chart_series": f"{metric} Cum Round",
                    "chart_teg": teg_str, "chart_round": round_num}

        elif tab == "scorecard":
            try:
                round_data = get_scorecard_data(teg_num, round_num)
                if round_data is None or round_data.empty:
                    sections.append({"title": "Scorecard", "table_html": "<p class='text-muted text-sm'>No scorecard data.</p>"})
                else:
                    # Responsive block: landscape on desktop/iPad, portrait on phone.
                    block = build_round_comparison_responsive(round_data, uid=f"lr{teg_num}r{round_num}")
                    sections.append({"title": None, "table_html": block, "raw": True})
                return {"sections": sections, "scorecard_css": True}
            except Exception as e:
                sections.append({"title": "Scorecard", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        elif tab == "records":
            try:
                ranked = cached_ranked_round_data()
                all_data = cached_load_all_data()
                streaks_df = read_file(STREAKS_PARQUET)
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
                sections.append({"title": "Records & PBs", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        elif tab == "report":
            html = _render_report([
                f"teg_{teg_num}_round_{round_num}_report_styled.md",
                f"round_reports/TEG{teg_num}_R{round_num}_report.md",
                f"round_reports/teg_{teg_num}_round_{round_num}_report.md",
            ])
            if html:
                return {"report_html": html}
            return {"report_html": None,
                    "report_message": f"No report available for TEG {teg_num} Round {round_num}."}

        elif tab == "scoring":
            field = score_type if score_type in ("GrossVP", "Stableford") else "GrossVP"
            friendly = dict(SCORING_FIELDS).get(field, field)
            all_data = cached_load_all_data()
            round_data = all_data[(all_data['TEGNum'] == teg_num) & (all_data['Round'] == round_num)]
            if not round_data.empty:
                counts = count_scores_by_player(round_data, field)
                counts_display = _intify_numeric(counts.reset_index())
                sections.append({"title": f"Score Counts ({friendly})", "table_html": _df_to_html(counts_display)})
            else:
                sections.append({"title": "Scoring", "table_html": "<p class='text-muted text-sm'>No scoring data.</p>"})
            return {"sections": sections, "scoring_fields": SCORING_FIELDS, "score_type": field}

        elif tab == "streaks":
            try:
                all_data = cached_load_all_data()
                streaks_df = read_file(STREAKS_PARQUET)
                teg_str = f"TEG {teg_num}"
                window = get_player_window_streaks(all_data, streaks_df, teg=teg_str, round_num=round_num)
                pivot = pivot_window_streaks(window)
                if not pivot.empty:
                    sections.append({"title": "Streaks", "table_html": _df_to_html(pivot)})
                    return {"sections": sections, "caption": "Eagles / birdies / par / bogeys are all 'or better'"}
                sections.append({"title": "Streaks", "table_html": "<p class='text-muted text-sm'>No streak data for this round.</p>"})
            except Exception as e:
                sections.append({"title": "Streaks", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        return {"sections": sections}
    except Exception as e:
        return {"error": str(e)}


@router.get("/latest-round")
async def latest_round_page(request: Request):
    rd_data = cached_round_data()
    teg_str, round_num = get_latest_round_defaults(rd_data)
    # teg_str is like 'TEG 18' — extract the number
    teg_num = int(teg_str.replace('TEG ', '')) if isinstance(teg_str, str) else int(teg_str)
    teg_numbers = get_available_teg_numbers()
    rounds = get_rounds_for_teg(teg_num)
    try:
        meta = get_teg_metadata(teg_num, int(round_num))
        context_header = " | ".join(p for p in [meta.get('Course', ''), meta.get('Date', '')] if p)
    except Exception:
        context_header = ""
    ctx = _latest_round_tab_context(teg_num, int(round_num), "scoreboard")
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
        "active_tab": "scoreboard",
        "context_header": context_header,
        **ctx,
    })


@router.get("/latest-round/tab")
async def latest_round_tab(request: Request, teg: int = Query(...), round: int = Query(...),
                           tab: str = Query("scoreboard"), score_type: str = Query("GrossVP"),
                           metric: str = Query("Sc")):
    rounds = get_rounds_for_teg(teg)
    round_num = round if round in rounds else (rounds[-1] if rounds else 1)
    ctx = _latest_round_tab_context(teg, round_num, tab, score_type, metric)
    return templates.TemplateResponse("partials/latest_round_tab.html", {
        "request": request,
        "teg": teg,
        "round": round_num,
        "rounds": rounds,
        **ctx,
    })


# --- /latest-teg --------------------------------------------------------------

LATEST_TEG_TABS = [
    ("aggregate", "Aggregate Score"),
    ("scoring", "Scoring"),
    ("streaks", "Streaks"),
    ("records", "Records & PBs"),
    ("report", "Report"),
]


def _latest_teg_tab_context(teg_num: int, tab: str, score_type: str = "GrossVP", metric: str = "Sc") -> dict:
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
            friendly = dict(SCORING_FIELDS).get(field, field)
            all_data = cached_load_all_data()
            teg_data = all_data[all_data['TEGNum'] == teg_num]
            if not teg_data.empty:
                counts = count_scores_by_player(teg_data, field)
                counts_display = _intify_numeric(counts.reset_index())
                sections.append({"title": f"Score Counts ({friendly})", "table_html": _df_to_html(counts_display)})
            else:
                sections.append({"title": "Scoring", "table_html": "<p class='text-muted text-sm'>No scoring data.</p>"})
            return {"sections": sections, "scoring_fields": SCORING_FIELDS, "score_type": field}

        elif tab == "report":
            html = _render_report([
                f"teg_{teg_num}_report_styled.md",
                f"teg_{teg_num}_main_report.md",
            ])
            teg_num_int = int(teg_num)
            caption = None
            if teg_num_int < 8:
                caption = ("NB: Before TEG 8 the TEG Trophy was decided by best net score "
                           "(total net vs par), not Stableford points.")
            if html:
                return {"report_html": html, "report_caption": caption}
            return {"report_html": None,
                    "report_message": f"No report available for TEG {teg_num}."}

        elif tab == "streaks":
            try:
                all_data = cached_load_all_data()
                streaks_df = read_file(STREAKS_PARQUET)
                teg_str = f"TEG {teg_num}"
                window = get_player_window_streaks(all_data, streaks_df, teg=teg_str)
                pivot = pivot_window_streaks(window)
                if not pivot.empty:
                    sections.append({"title": "Streaks", "table_html": _df_to_html(pivot)})
                    return {"sections": sections, "caption": "Eagles / birdies / par / bogeys are all 'or better'"}
                sections.append({"title": "Streaks", "table_html": "<p class='text-muted text-sm'>No streak data for this TEG.</p>"})
            except Exception as e:
                sections.append({"title": "Streaks", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        elif tab == "records":
            try:
                ranked = cached_ranked_teg_data()
                all_data = cached_load_all_data()
                streaks_df = read_file(STREAKS_PARQUET)
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
                sections.append({"title": "Records & PBs", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        return {"sections": sections}
    except Exception as e:
        return {"error": str(e)}


@router.get("/latest-teg")
async def latest_teg_page(request: Request):
    teg_num = get_default_teg_num()
    teg_numbers = get_available_teg_numbers()
    ctx = _latest_teg_tab_context(teg_num, "aggregate")
    return templates.TemplateResponse("latest_teg.html", {
        "request": request,
        "active_page": "latest-teg",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        # teg also feeds the in-partial pill hx-vals on first render.
        "teg": teg_num,
        "tabs": LATEST_TEG_TABS,
        "active_tab": "aggregate",
        **ctx,
    })


@router.get("/latest-teg/tab")
async def latest_teg_tab(request: Request, teg: int = Query(...), tab: str = Query("aggregate"),
                         score_type: str = Query("GrossVP"), metric: str = Query("Sc")):
    ctx = _latest_teg_tab_context(teg, tab, score_type, metric)
    return templates.TemplateResponse("partials/latest_teg_tab.html", {
        "request": request,
        "teg": teg,
        **ctx,
    })


# --- /handicaps ---------------------------------------------------------------

@router.get("/handicaps")
async def handicaps_page(request: Request):
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
                ctx["draft_title"] = "Draft handicaps"
                ctx["draft_html"] = f"<p class='text-muted text-sm'>Error: {e}</p>"

        return templates.TemplateResponse("handicaps.html", {
            "request": request, "active_page": "handicaps", **ctx,
        })
    except Exception as e:
        return templates.TemplateResponse("handicaps.html", {
            "request": request, "active_page": "handicaps", "error": str(e),
        })
