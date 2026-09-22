"""Contents route — current-TEG home page with the full site map below.

State-led home (I3/I5, revised): shows the in-progress TEG, the latest
completed TEG, or an honest no-data message, chosen by
`webapp.deps.get_tournament_state()`. The complete public site map
(`webapp.nav.NAV_SECTIONS`, unchanged) always renders beneath it, so every
destination stays reachable regardless of state.
"""

from pathlib import Path

from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from webapp.nav import NAV_SECTIONS
from webapp.deps import (
    PLAYER_COLUMN,
    cached_round_data,
    create_leaderboard,
    format_value,
    get_net_competition_measure,
    get_tournament_state,
)
from webapp.routes.history import _standings_rows
from teg_analysis.reporting.newspaper_edition import available_rounds, get_edition_summary

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/contents")
def contents_page(request: Request):
    return templates.TemplateResponse("contents.html", {
        "request": request,
        "active_page": "contents",
        "sections": NAV_SECTIONS,
        "state": get_tournament_state(),
    })


def _in_progress_panel(teg_num: int) -> dict:
    """In-progress rich content: the real net-competition standings table
    (every player, ties as genuine duplicate rows -- TEG has no countback,
    so no synthetic "and 1 other" collapsing), a compact gross-competition
    line, and a round-report teaser when one exists.

    Reads `cached_round_data()` directly, bypassing `_results_context()`
    (which also builds chart JSON/readout this page doesn't need).
    """
    rd = cached_round_data()
    teg_rd = rd[rd['TEGNum'] == teg_num]
    net_measure = get_net_competition_measure(teg_num)

    net_lb = create_leaderboard(teg_rd, net_measure, ascending=(net_measure == 'NetVP'))
    net_lb['Total'] = net_lb['Total'].apply(lambda x: format_value(x, net_measure))
    # Rank/Player/Total only -- a compact home-page list, not the full
    # round-by-round table. Drop the round columns before _standings_rows()
    # builds each row's own `rounds` list, not just the top-level
    # `round_labels` key -- the two are independent, and the table partial's
    # tbody loop reads the per-row list (_standings_table.html has no
    # responsive reflow outside the .standings-page wrapper, but 3 columns
    # need none).
    net_lb = net_lb[['Rank', PLAYER_COLUMN, 'Total']]
    standings = _standings_rows(net_lb, link_players=False)

    gross_lb = create_leaderboard(teg_rd, 'GrossVP', ascending=True)
    gross_leader = None
    if not gross_lb.empty:
        top_total = gross_lb.iloc[0]['Total']
        names = gross_lb.loc[gross_lb['Total'] == top_total, PLAYER_COLUMN].tolist()
        gross_leader = {"names": names, "total": format_value(top_total, 'GrossVP')}

    report_summary = None
    rounds = available_rounds(teg_num)
    if rounds:
        report_summary = get_edition_summary(teg_num, rounds[-1])

    return {
        "standings": standings,
        "gross_leader": gross_leader,
        "net_unit": "pts" if net_measure == "Stableford" else "vs par",
        "report_summary": report_summary,
    }


@router.get("/contents/panel")
def contents_panel(request: Request, teg: int = Query(...), rounds: int = Query(...)):
    # HTMX fallback for the in-progress state (I4 R10, revised): the main
    # page renders the headline/context/actions immediately from the two
    # status CSVs, and this partial fills in the standings + report teaser
    # once cached_round_data() has loaded, instead of blocking the initial
    # response on a cold parquet load. Complete-state content is resolved
    # synchronously in get_tournament_state() instead -- its headline
    # depends on report availability, so it can't defer without a flash.
    # `rounds` (state.rounds_played) is passed through only for the
    # "Standings after Round N" heading -- not re-derived here.
    panel = _in_progress_panel(teg)
    return templates.TemplateResponse("partials/_contents_panel.html", {
        "request": request,
        "panel": panel,
        "rounds_played": rounds,
    })
