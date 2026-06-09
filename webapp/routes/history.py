"""History section routes: /history, /honours, /results, /player-rankings."""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates
from markupsafe import escape

from teg_analysis.constants import PLAYER_DICT
from teg_analysis.analysis.history import (
    prepare_complete_history_table_fast,
    get_teg_winners,
    calculate_trophy_jacket_doubles,
    get_eagles_data,
    get_holes_in_one_data,
)
from teg_analysis.analysis.player_rankings import (
    create_teg_ranking_table,
    create_net_competition_ranking_table,
    create_combined_position_summary,
)
from teg_analysis.core.metadata import get_scorecard_data
from teg_analysis.display.scorecards import (
    build_round_comparison_gross_table,
    build_round_comparison_stableford_table,
)
from webapp.deps import (
    cached_load_all_data,
    cached_round_data,
    cached_complete_teg_data,
    cached_ranked_teg_data,
    create_leaderboard,
    format_value,
    get_available_teg_numbers,
    get_default_teg_num,
    get_net_competition_measure,
    get_rounds_for_teg,
)

_NAME_TO_CODE = {v: k for k, v in PLAYER_DICT.items()}

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _df_to_html(df: pd.DataFrame, table_class: str = "teg-table", link_players: bool = False) -> str:
    """Convert a DataFrame to a styled HTML table."""
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"

    rows = [f"<table class='{table_class}'>"]
    rows.append("<thead><tr>")
    for col in df.columns:
        rows.append(f"<th>{col}</th>")
    rows.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        rows.append("<tr>")
        for col in df.columns:
            val = row[col]
            if link_players and col == 'Player':
                code = _NAME_TO_CODE.get(str(val))
                if code:
                    rows.append(f"<td><a href='/player/{code}'>{escape(str(val))}</a></td>")
                else:
                    rows.append(f"<td>{escape(str(val))}</td>")
            else:
                rows.append(f"<td>{val}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


# --- /history -----------------------------------------------------------------

@router.get("/history")
async def history_page(request: Request):
    try:
        df = prepare_complete_history_table_fast()
        table_html = _df_to_html(df)
        table_html += ("<p class='text-muted text-sm mt-3'>*Green Jacket awarded in TEG 5 for "
                       "best stableford round; DM had best gross score.</p>")
    except Exception as e:
        table_html = f"<p class='text-muted'>Error: {e}</p>"

    return templates.TemplateResponse("data_table.html", {
        "request": request,
        "active_page": "history",
        "title": "TEG History",
        "subtitle": "Complete history of all TEG tournaments",
        "table_html": table_html,
        "sections": None,
    })


# --- /honours -----------------------------------------------------------------

HONOURS_TABS = [
    ("trophy", "TEG Trophy"),
    ("jacket", "Green Jacket"),
    ("spoon", "Wooden Spoon"),
    ("doubles", "Doubles"),
    ("eagles", "Eagles"),
    ("hio", "Holes in One"),
]


def _compress_ranges(nums):
    """Compress consecutive integers into range strings. Only collapse runs of 3+."""
    if not nums:
        return ""
    nums = sorted(set(nums))
    runs = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
        else:
            runs.append((start, prev))
            start = prev = n
    runs.append((start, prev))
    parts = []
    for a, b in runs:
        if b - a >= 2:
            parts.append(f"{a}-{b}")
        elif b - a == 1:
            parts.extend([str(a), str(b)])
        else:
            parts.append(str(a))
    return ", ".join(parts)


def _summarise_wins(winners_df: pd.DataFrame, col: str) -> str:
    """Build a summary table: Player, Wins, TEGs with compressed ranges."""
    # Extract TEG number from 'TEG' column (e.g. "TEG 5" -> 5)
    df = winners_df[['TEG', col]].copy()
    df['_teg_num'] = df['TEG'].str.extract(r'(\d+)').astype(int)

    grouped = df.groupby(col)['_teg_num'].agg(['count', list]).reset_index()
    grouped.columns = ['Player', 'Wins', '_nums']
    grouped['TEGs'] = grouped['_nums'].apply(_compress_ranges)
    grouped = grouped.drop(columns=['_nums'])
    grouped = grouped.sort_values('Wins', ascending=False).reset_index(drop=True)

    return _df_to_html(grouped, link_players=True)


def _honours_tab_context(tab: str) -> dict:
    """Build context for an honours tab."""
    try:
        all_data = cached_load_all_data()
        winners_df = get_teg_winners(all_data)

        sections = []

        if tab == "trophy":
            sections.append({"title": "TEG Trophy", "table_html": _summarise_wins(winners_df, "TEG Trophy")})

        elif tab == "jacket":
            jacket_html = _summarise_wins(winners_df, "Green Jacket")
            jacket_html += ("<p class='text-muted text-sm mt-3'>*Green Jacket awarded in TEG 5 for "
                            "best stableford round; DM had best gross score.</p>")
            sections.append({"title": "Green Jacket", "table_html": jacket_html})

        elif tab == "spoon":
            sections.append({"title": "Wooden Spoon", "table_html": _summarise_wins(winners_df, "HMM Wooden Spoon")})

        elif tab == "doubles":
            doubles_df, count = calculate_trophy_jacket_doubles(winners_df)
            html = _df_to_html(doubles_df) if doubles_df is not None and not doubles_df.empty else "<p class='text-muted text-sm'>No doubles recorded.</p>"
            sections.append({"title": f"Trophy & Jacket Doubles ({count})", "table_html": html})

        elif tab == "eagles":
            eagles = get_eagles_data(all_data)
            sections.append({"title": "Eagles", "table_html": _df_to_html(eagles, link_players=True)})

        elif tab == "hio":
            hio = get_holes_in_one_data(all_data)
            if hio is not None and not hio.empty:
                sections.append({"title": "Holes in One", "table_html": _df_to_html(hio, link_players=True)})
            else:
                sections.append({"title": "Holes in One", "table_html": "<p class='text-muted text-sm'>No holes in one recorded.</p>"})

        return {"sections": sections}
    except Exception as e:
        return {"error": str(e)}


@router.get("/honours")
async def honours_page(request: Request):
    ctx = _honours_tab_context("trophy")
    return templates.TemplateResponse("honours.html", {
        "request": request,
        "active_page": "honours",
        "tabs": HONOURS_TABS,
        "active_tab": "trophy",
        **ctx,
    })


@router.get("/honours/tab/{tab_name}")
async def honours_tab(request: Request, tab_name: str):
    ctx = _honours_tab_context(tab_name)
    return templates.TemplateResponse("partials/honours_tab.html", {
        "request": request,
        **ctx,
    })


# --- /results -----------------------------------------------------------------

def _results_chart(teg_num: int, tab: str) -> str | None:
    """Build a cumulative race chart for net/gross results tabs. Returns JSON or None."""
    try:
        import json
        import plotly.utils
        from webapp.chart_utils import create_cumulative_graph

        all_data = cached_load_all_data()
        teg_name = f"TEG {teg_num}"

        if tab == "gross":
            fig = create_cumulative_graph(
                all_data, teg_name,
                y_series='GrossVP Cum TEG',
                title='Cumulative Gross vs Par',
                chart_type='gross',
            )
        else:
            net_measure = get_net_competition_measure(teg_num)
            if net_measure == 'Stableford':
                fig = create_cumulative_graph(
                    all_data, teg_name,
                    y_series='Stableford Cum TEG',
                    title='Cumulative Stableford',
                    chart_type='stableford',
                )
            else:
                fig = create_cumulative_graph(
                    all_data, teg_name,
                    y_series='NetVP Cum TEG',
                    title='Cumulative Net vs Par',
                    chart_type='gross',
                )

        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    except Exception:
        return None


def _results_context(teg_num: int, tab: str = "net") -> dict:
    """Build context for full results page."""
    try:
        if tab == "scorecards":
            rounds = get_rounds_for_teg(teg_num)
            parts = ['<link rel="stylesheet" href="/static/scorecard.css">']
            for r in rounds:
                try:
                    rd = get_scorecard_data(teg_num, r)
                    if rd is None or rd.empty:
                        continue
                    gross = build_round_comparison_gross_table(rd)
                    stableford = build_round_comparison_stableford_table(rd)
                    parts.append(f"<h2 class='section-title'>Round {r}</h2>")
                    parts.append("<div class='mb-2'><strong>Gross</strong></div>")
                    parts.append(gross)
                    parts.append("<div class='mt-3 mb-2'><strong>Stableford</strong></div>")
                    parts.append(stableford)
                except Exception:
                    continue
            table_html = "".join(parts) if len(parts) > 1 else "<p class='text-muted'>No rounds found.</p>"
            return {"result_title": "Scorecards", "table_html": table_html}

        if tab == "report":
            from pathlib import Path
            import markdown as md_lib
            # Prefer the styled report; fall back to the plain main report draft.
            candidates = [
                Path(f"data/commentary/teg_{teg_num}_report_styled.md"),
                Path(f"data/commentary/drafts/teg_{teg_num}_main_report.md"),
                Path(f"data/commentary/teg_{teg_num}_main_report.md"),
            ]
            path = next((p for p in candidates if p.is_file()), None)
            if path is not None:
                html = md_lib.markdown(
                    path.read_text(encoding="utf-8"),
                    extensions=["extra", "sane_lists", "smarty", "toc"],
                )
                caption = ""
                if int(teg_num) < 8:
                    caption = ("<p class='text-muted text-sm'>NB: Before TEG 8 the TEG Trophy was "
                               "decided by best net score (total net vs par), not Stableford points.</p>")
                return {
                    "result_title": "Report",
                    "table_html": (
                        '<link rel="stylesheet" href="/static/teg_reports.css">'
                        f'{caption}<div class="teg-report">{html}</div>'
                    ),
                }
            return {
                "result_title": "Report",
                "table_html": (
                    f"<p class='text-muted text-sm'>No report available yet for TEG {teg_num}.</p>"
                ),
            }

        rd_data = cached_round_data()
        teg_rd = rd_data[rd_data['TEGNum'] == teg_num]

        if teg_rd.empty:
            return {"error": f"No data found for TEG {teg_num}"}

        net_measure = get_net_competition_measure(teg_num)
        net_ascending = net_measure == 'NetVP'

        if tab == "gross":
            lb = create_leaderboard(teg_rd, 'GrossVP', ascending=True)
            for col in [c for c in lb.columns if c not in ['Rank', 'Player']]:
                lb[col] = lb[col].apply(lambda x: format_value(x, 'GrossVP'))
            title = "Gross vs Par"
        else:
            lb = create_leaderboard(teg_rd, net_measure, ascending=net_ascending)
            for col in [c for c in lb.columns if c not in ['Rank', 'Player']]:
                lb[col] = lb[col].apply(lambda x: format_value(x, net_measure))
            title = "Stableford" if net_measure == 'Stableford' else "Net vs Par"

        # Champion (top row) — plus wooden spoon (bottom row) on the net competition
        callout = ""
        if not lb.empty and 'Player' in lb.columns:
            champion = lb.iloc[0]['Player']
            if tab == "gross":
                callout = f"<p class='result-callout'><strong>Champion:</strong> {champion}</p>"
            else:
                spoon = lb.iloc[-1]['Player']
                callout = (f"<p class='result-callout'><strong>Champion:</strong> {champion} "
                           f"&nbsp;|&nbsp; <strong>Wooden spoon:</strong> {spoon}</p>")

        table_html = callout + _df_to_html(lb, link_players=True)
        chart_json = _results_chart(teg_num, tab)
        return {"result_title": title, "table_html": table_html, "chart_json": chart_json}
    except Exception as e:
        return {"error": str(e)}


@router.get("/results")
async def results_page(request: Request):
    teg_num = get_default_teg_num()
    teg_numbers = get_available_teg_numbers()
    ctx = _results_context(teg_num, "net")
    return templates.TemplateResponse("results.html", {
        "request": request,
        "active_page": "results",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "active_tab": "net",
        **ctx,
    })


@router.get("/results/table")
async def results_table(request: Request, teg: int = Query(...), tab: str = Query("net")):
    ctx = _results_context(teg, tab)
    return templates.TemplateResponse("partials/results_table.html", {
        "request": request,
        "selected_teg": teg,
        "active_tab": tab,
        **ctx,
    })


# --- /player-rankings ---------------------------------------------------------

PLAYER_RANKINGS_TABS = [
    ("trophy", "TEG Trophy"),
    ("jacket", "Green Jacket"),
]


PR_ROW_DIMS = [("Player", "Full Name"), ("Pl", "Initials")]
PR_COL_DIMS = [("TEGNum", "TEG Number"), ("TEG", "TEG Name")]


def _format_ranking_for_display(ranking: pd.DataFrame, player_col: str) -> pd.DataFrame:
    """Rename TEGNum columns to 'TEG N' and show '-' for non-participation."""
    df = ranking.copy()
    rename = {}
    for col in df.columns:
        if col == player_col:
            continue
        try:
            rename[col] = f"TEG {int(col)}"
        except (ValueError, TypeError):
            rename[col] = col
    df = df.rename(columns=rename)
    for col in [c for c in df.columns if c != player_col]:
        df[col] = df[col].apply(lambda x: "-" if pd.isna(x) else str(x))
    return df


def _player_rankings_context(tab: str, row_dim: str = "Player", col_dim: str = "TEGNum") -> dict:
    try:
        if row_dim not in ("Player", "Pl"):
            row_dim = "Player"
        if col_dim not in ("TEGNum", "TEG"):
            col_dim = "TEGNum"
        teg_data = cached_complete_teg_data()
        if tab == "trophy":
            ranking = create_net_competition_ranking_table(teg_data, row_dim, col_dim)
            rank_title = "TEG Trophy Rankings by TEG (Net Competition)"
            caption = "Uses Net vs Par for TEGs 2-7, Stableford Points for TEG 8+."
            summary_title = "TEG Trophy rankings summary"
        else:
            ranking = create_teg_ranking_table(teg_data, "GrossVP", row_dim, col_dim)
            rank_title = "Green Jacket Rankings by TEG (Gross vs Par)"
            caption = "Lower scores are better. Ties marked '='; '-' = did not participate."
            summary_title = "Green Jacket rankings summary"

        summary = create_combined_position_summary(ranking, row_dim)
        display = _format_ranking_for_display(ranking, row_dim)

        sections = [
            {"title": rank_title, "caption": caption,
             "table_html": _df_to_html(display, link_players=(row_dim == "Player"))},
            {"title": summary_title, "caption": None,
             "table_html": _df_to_html(summary, table_class="teg-table")},
        ]
        return {"sections": sections, "row_dims": PR_ROW_DIMS, "col_dims": PR_COL_DIMS,
                "selected_row_dim": row_dim, "selected_col_dim": col_dim}
    except Exception as e:
        return {"error": str(e)}


@router.get("/player-rankings")
async def player_rankings_page(request: Request, row_dim: str = Query("Player"), col_dim: str = Query("TEGNum")):
    default_tab = "trophy"
    ctx = _player_rankings_context(default_tab, row_dim, col_dim)
    return templates.TemplateResponse("player_rankings.html", {
        "request": request,
        "active_page": "player-rankings",
        "tabs": PLAYER_RANKINGS_TABS,
        "active_tab": default_tab,
        **ctx,
    })


@router.get("/player-rankings/tab")
async def player_rankings_tab(request: Request, tab: str = "trophy",
                              row_dim: str = Query("Player"), col_dim: str = Query("TEGNum")):
    ctx = _player_rankings_context(tab, row_dim, col_dim)
    return templates.TemplateResponse("partials/player_rankings_tab.html", {
        "request": request,
        "active_tab": tab,
        **ctx,
    })
