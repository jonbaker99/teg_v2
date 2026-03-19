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
from webapp.deps import (
    cached_load_all_data,
    cached_round_data,
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
            sections.append({"title": "Green Jacket", "table_html": _summarise_wins(winners_df, "Green Jacket")})

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
            links = []
            for r in rounds:
                links.append(
                    f'<p><a href="/scorecard?teg={teg_num}&round={r}" class="text-link">'
                    f'Round {r} Scorecard</a></p>'
                )
            table_html = "".join(links) if links else "<p class='text-muted'>No rounds found.</p>"
            return {"result_title": "Scorecards", "table_html": table_html}

        if tab == "report":
            return {
                "result_title": "Report",
                "table_html": "<p class='text-muted text-sm'>Reports are not yet available in the webapp.</p>",
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

        table_html = _df_to_html(lb, link_players=True)
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

@router.get("/player-rankings")
async def player_rankings_page(request: Request):
    try:
        ranked = cached_ranked_teg_data()
        # Compute rank within each TEG (1st, 2nd, 3rd, etc.)
        ranked = ranked.copy()
        ranked['GrossVP_TegRank'] = ranked.groupby('TEGNum')['GrossVP'].rank(method='min', ascending=True).astype(int)
        # Pivot: player rows, TEG columns, gross rank values
        pivot = ranked.pivot_table(
            index='Player', columns='TEGNum', values='GrossVP_TegRank',
            aggfunc='first',
        )
        pivot.columns = [f'TEG {int(c)}' for c in pivot.columns]
        pivot = pivot.reset_index()
        teg_cols = [c for c in pivot.columns if c != 'Player']
        for col in teg_cols:
            pivot[col] = pivot[col].apply(lambda x: '—' if pd.isna(x) else str(int(x)))
        table_html = _df_to_html(pivot, link_players=True)
    except Exception as e:
        table_html = f"<p class='text-muted'>Error: {e}</p>"

    return templates.TemplateResponse("data_table.html", {
        "request": request,
        "active_page": "player-rankings",
        "title": "Player Rankings",
        "subtitle": "Gross ranking by TEG",
        "table_html": table_html,
        "sections": None,
    })
