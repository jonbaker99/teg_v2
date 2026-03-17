"""Leaderboard routes."""

from pathlib import Path

from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates
from markupsafe import escape

from teg_analysis.constants import PLAYER_DICT
from webapp.deps import (
    cached_round_data,
    create_leaderboard,
    format_value,
    get_default_teg_num,
    get_available_teg_numbers,
    get_net_competition_measure,
)

# Reverse lookup: full name → player code
_NAME_TO_CODE = {v: k for k, v in PLAYER_DICT.items()}

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

LEADERBOARD_TABS = [
    ("net", "Net"),
    ("gross", "Gross"),
]


def _build_table_html(df, teg_num: int = None):
    """Convert a leaderboard DataFrame to styled HTML."""
    rows = []
    rows.append("<table class='teg-table'>")
    # Header
    rows.append("<thead><tr>")
    for col in df.columns:
        if col == 'Rank':
            rows.append("<th class='col-rank'>#</th>")
        elif col == 'Player':
            rows.append("<th class='col-player'>Player</th>")
        elif teg_num and col.startswith('R') and col[1:].isdigit():
            round_num = col[1:]
            rows.append(f"<th class='col-num'><a href='/scorecard?teg={teg_num}&round={round_num}' title='View scorecard'>{col}</a></th>")
        else:
            rows.append(f"<th class='col-num'>{col}</th>")
    rows.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        rank_str = str(row['Rank'])
        row_class = ' class="top-rank"' if rank_str.replace('=', '') == '1' else ''
        rows.append(f"<tr{row_class}>")
        for col in df.columns:
            if col == 'Rank':
                rows.append(f"<td class='col-rank'>{row[col]}</td>")
            elif col == 'Player':
                player_name = row[col]
                code = _NAME_TO_CODE.get(player_name)
                if code:
                    rows.append(f"<td class='col-player'><a href='/player/{code}'>{escape(player_name)}</a></td>")
                else:
                    rows.append(f"<td class='col-player'>{escape(player_name)}</td>")
            elif col == 'Total':
                rows.append(f"<td class='col-num total'>{row[col]}</td>")
            else:
                rows.append(f"<td class='col-num'>{row[col]}</td>")
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


def _leaderboard_context(teg_num: int, tab: str = "net") -> dict:
    """Build template context for a given TEG number and tab."""
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

        for col in [c for c in net_lb.columns if c not in ['Rank', 'Player']]:
            net_lb[col] = net_lb[col].apply(lambda x: format_value(x, net_measure))

        net_title_label = "TEG Trophy (Stableford)" if net_measure == 'Stableford' else "TEG Trophy (Net vs Par)"

        # Gross competition
        gross_lb = create_leaderboard(teg_rd, 'GrossVP', ascending=True)
        gross_champion = _get_champion(gross_lb)

        for col in [c for c in gross_lb.columns if c not in ['Rank', 'Player']]:
            gross_lb[col] = gross_lb[col].apply(lambda x: format_value(x, 'GrossVP'))

        # Select which table to show based on tab
        if tab == "gross":
            active_title = "Claret Jug (Gross vs Par)"
            active_table = _build_table_html(gross_lb, teg_num)
            active_champion = gross_champion
            active_spoon = None
        else:
            active_title = net_title_label
            active_table = _build_table_html(net_lb, teg_num)
            active_champion = net_champion
            active_spoon = net_wooden_spoon

        return {
            "active_title": active_title,
            "active_table": active_table,
            "active_champion": active_champion,
            "active_spoon": active_spoon,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/leaderboard")
async def leaderboard_page(request: Request):
    teg_num = get_default_teg_num()
    teg_numbers = get_available_teg_numbers()
    ctx = _leaderboard_context(teg_num, tab="net")
    return templates.TemplateResponse("leaderboard.html", {
        "request": request,
        "active_page": "leaderboard",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "leaderboard_tabs": LEADERBOARD_TABS,
        "active_lb_tab": "net",
        **ctx,
    })


@router.get("/leaderboard/table")
async def leaderboard_table(request: Request, teg: int = Query(...), tab: str = Query("net")):
    ctx = _leaderboard_context(teg, tab=tab)
    return templates.TemplateResponse("partials/leaderboard_table.html", {
        "request": request,
        "selected_teg": teg,
        "active_lb_tab": tab,
        "leaderboard_tabs": LEADERBOARD_TABS,
        **ctx,
    })
