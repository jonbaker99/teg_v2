"""Leaderboard routes."""

from pathlib import Path

from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from webapp.deps import (
    cached_round_data,
    create_leaderboard,
    format_value,
    get_default_teg_num,
    get_available_teg_numbers,
    get_net_competition_measure,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _build_table_html(df):
    """Convert a leaderboard DataFrame to styled HTML."""
    rows = []
    rows.append("<table class='teg-table'>")
    # Header — skip Rank column header but keep the cell
    rows.append("<thead><tr><th></th>")
    for col in df.columns[1:]:
        rows.append(f"<th>{col}</th>")
    rows.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        rank_str = str(row['Rank'])
        row_class = ' class="top-rank"' if rank_str.replace('=', '') == '1' else ''
        rows.append(f"<tr{row_class}>")
        for col in df.columns:
            td_class = ' class="total"' if col == 'Total' else ''
            rows.append(f"<td{td_class}>{row[col]}</td>")
        rows.append("</tr>")

    rows.append("</tbody></table>")
    return "".join(rows)


def _get_champion(df):
    """Get champion name(s) from leaderboard."""
    champs = df[df['Rank'].isin(['1', '1='])]['Player'].tolist()
    return ', '.join(champs) if champs else None


def _get_wooden_spoon(df):
    """Get last-place player(s) from leaderboard."""
    df_copy = df.copy()
    df_copy['_rank_int'] = df_copy['Rank'].astype(str).str.replace('=', '', regex=False).astype(int)
    last_rank = df_copy['_rank_int'].max()
    losers = df_copy[df_copy['_rank_int'] == last_rank]['Player'].tolist()
    return ', '.join(losers) if losers else None


def _leaderboard_context(teg_num: int) -> dict:
    """Build template context for a given TEG number."""
    try:
        rd_data = cached_round_data()
        teg_rd = rd_data[rd_data['TEGNum'] == teg_num]

        if teg_rd.empty:
            return {"error": f"No data found for TEG {teg_num}"}

        # Net competition
        net_measure = get_net_competition_measure(teg_num)
        net_ascending = net_measure == 'NetVP'
        net_lb = create_leaderboard(teg_rd, net_measure, ascending=net_ascending)

        net_champion = _get_champion(net_lb)
        net_wooden_spoon = _get_wooden_spoon(net_lb)

        # Format values
        for col in [c for c in net_lb.columns if c not in ['Rank', 'Player']]:
            net_lb[col] = net_lb[col].apply(lambda x: format_value(x, net_measure))

        net_title_label = "TEG Trophy (Stableford)" if net_measure == 'Stableford' else "TEG Trophy (Net vs Par)"

        # Gross competition
        gross_lb = create_leaderboard(teg_rd, 'GrossVP', ascending=True)
        gross_champion = _get_champion(gross_lb)

        for col in [c for c in gross_lb.columns if c not in ['Rank', 'Player']]:
            gross_lb[col] = gross_lb[col].apply(lambda x: format_value(x, 'GrossVP'))

        return {
            "net_title": net_title_label,
            "net_table": _build_table_html(net_lb),
            "net_champion": net_champion,
            "net_wooden_spoon": net_wooden_spoon,
            "gross_title": "Claret Jug (Gross vs Par)",
            "gross_table": _build_table_html(gross_lb),
            "gross_champion": gross_champion,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/leaderboard")
async def leaderboard_page(request: Request):
    teg_num = get_default_teg_num()
    teg_numbers = get_available_teg_numbers()
    ctx = _leaderboard_context(teg_num)
    return templates.TemplateResponse("leaderboard.html", {
        "request": request,
        "active_page": "leaderboard",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        **ctx,
    })


@router.get("/leaderboard/table")
async def leaderboard_table(request: Request, teg: int = Query(...)):
    ctx = _leaderboard_context(teg)
    return templates.TemplateResponse("partials/leaderboard_table.html", {
        "request": request,
        **ctx,
    })
