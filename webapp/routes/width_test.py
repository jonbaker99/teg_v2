"""Width test dev page — not in nav, used to pick max-width for layout."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from markupsafe import escape

from teg_analysis.constants import PLAYER_DICT
from webapp.deps import (
    cached_round_data,
    create_leaderboard,
    format_value,
    get_default_teg_num,
    get_net_competition_measure,
)

_NAME_TO_CODE = {v: k for k, v in PLAYER_DICT.items()}

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _build_wide_table(df, teg_num: int) -> str:
    rows = ["<table class='teg-table'>", "<thead><tr>"]
    for col in df.columns:
        if col == 'Rank':
            rows.append("<th class='col-rank'>#</th>")
        elif col == 'Player':
            rows.append("<th class='col-player'>Player</th>")
        elif col.startswith('R') and col[1:].isdigit():
            round_num = col[1:]
            rows.append(f"<th class='col-num'><a href='/scorecard?teg={teg_num}&round={round_num}'>{col}</a></th>")
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
                name = row[col]
                code = _NAME_TO_CODE.get(name)
                if code:
                    rows.append(f"<td class='col-player'><a href='/player/{code}'>{escape(name)}</a></td>")
                else:
                    rows.append(f"<td class='col-player'>{escape(name)}</td>")
            elif col == 'Total':
                rows.append(f"<td class='col-num total'>{row[col]}</td>")
            else:
                rows.append(f"<td class='col-num'>{row[col]}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


@router.get("/width-test")
async def width_test_page(request: Request):
    teg_num = get_default_teg_num()
    rd_data = cached_round_data()
    teg_rd = rd_data[rd_data['TEGNum'] == teg_num]

    net_measure = get_net_competition_measure(teg_num)
    net_ascending = net_measure == 'NetVP'
    net_lb = create_leaderboard(teg_rd, net_measure, ascending=net_ascending)
    for col in [c for c in net_lb.columns if c not in ['Rank', 'Player']]:
        net_lb[col] = net_lb[col].apply(lambda x: format_value(x, net_measure))
    net_table = _build_wide_table(net_lb, teg_num)

    gross_lb = create_leaderboard(teg_rd, 'GrossVP', ascending=True)
    for col in [c for c in gross_lb.columns if c not in ['Rank', 'Player']]:
        gross_lb[col] = gross_lb[col].apply(lambda x: format_value(x, 'GrossVP'))
    gross_table = _build_wide_table(gross_lb, teg_num)

    return templates.TemplateResponse("width_test.html", {
        "request": request,
        "active_page": "",
        "teg_num": teg_num,
        "net_table": net_table,
        "gross_table": gross_table,
    })
