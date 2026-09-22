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
    cached_winners,
    create_leaderboard,
    format_value,
    get_net_competition_measure,
    get_tournament_state,
)
from webapp.routes.history import _standings_rows
from teg_analysis.reporting.newspaper_edition import available_rounds, get_edition_summary

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

SITEMAP_PAGE_COUNT = sum(len(s["pages"]) for s in NAV_SECTIONS)
SITEMAP_GROUP_LABELS = ", ".join(s["label"] for s in NAV_SECTIONS)


@router.get("/contents")
def contents_page(request: Request):
    return templates.TemplateResponse("contents.html", {
        "request": request,
        "active_page": "contents",
        "sections": NAV_SECTIONS,
        "state": get_tournament_state(),
        "sitemap_page_count": SITEMAP_PAGE_COUNT,
        "sitemap_group_labels": SITEMAP_GROUP_LABELS,
    })


_HONOUR_COLUMNS = (
    ("TEG Trophy", "trophy"),
    ("Green Jacket", "jacket"),
    ("HMM Wooden Spoon", "spoon"),
)


def _format_gross_total(value: object) -> str:
    """Format a GrossVP aggregate with an explicit sign, including zero."""
    number = float(value)
    display = str(int(number)) if number.is_integer() else str(number)
    return f"+{display}" if number >= 0 else display


def _honours_by_player(teg_num: int) -> dict[str, tuple[str, ...]]:
    """Map completed-TEG winners to their displayed honour icons.

    ``cached_winners()`` is the canonical, override-aware result source. A
    player can receive more than one honour. Asterisks from historical
    overrides remain display annotations rather than identity.
    """
    winners = cached_winners()
    winner_row = winners[winners["TEG"] == f"TEG {teg_num}"]
    if winner_row.empty:
        return {}

    honours: dict[str, list[str]] = {}
    row = winner_row.iloc[0]
    for column, honour in _HONOUR_COLUMNS:
        name = row.get(column)
        if isinstance(name, str) and (name := name.replace("*", "").strip()):
            honours.setdefault(name, []).append(honour)
    return {name: tuple(awards) for name, awards in honours.items()}


def _standings_table_context(teg_num: int, honours_by_player: dict[str, tuple[str, ...]] | None = None) -> dict:
    """The real net-competition standings table (every player, ties as
    genuine duplicate rows -- TEG has no countback, so no synthetic "and 1
    other" collapsing) plus a unit-aware column header. Shared by both
    in-progress and complete panels.

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
    # responsive reflow outside the .standings-page wrapper; its compact net
    # and gross metrics need none).
    net_lb = net_lb[['Rank', PLAYER_COLUMN, 'Total']]
    standings = _standings_rows(net_lb, link_players=False)
    # Gross is a separate leaderboard: its rank order can differ from the
    # net competition's. Associate the aggregate by player name, never row
    # position, then retain the net standings order for this compact table.
    gross_lb = create_leaderboard(teg_rd, 'GrossVP', ascending=True)
    gross_by_player = {
        str(row[PLAYER_COLUMN]): _format_gross_total(row['Total'])
        for _, row in gross_lb.iterrows()
    }
    for row in standings["rows"]:
        row["gross"] = gross_by_player.get(row["player"], "—")
    if honours_by_player:
        for row in standings["rows"]:
            row["honours"] = honours_by_player.get(row["player"], ())
    # _standings_table.html's optional override for the "Total" header --
    # real TEGs before TEG 8 are vs-par, not Stableford points.
    standings["total_label"] = "Points" if net_measure == "Stableford" else "vs Par"
    standings["show_gross"] = True

    return {"standings": standings}


def _in_progress_panel(teg_num: int) -> dict:
    """In-progress rich content: standings + a compact gross-competition
    line + a round-report teaser when one exists."""
    rd = cached_round_data()
    teg_rd = rd[rd['TEGNum'] == teg_num]

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
        "state": "in_progress",
        "teg_num": teg_num,
        "gross_leader": gross_leader,
        "report_summary": report_summary,
        **_standings_table_context(teg_num),
    }


def _complete_panel(teg_num: int) -> dict:
    """Complete-state rich content: final standings (left) + "Also in this
    report" secondary headlines (right). Winners (Trophy/Jacket/spoon)
    already render synchronously in the instant honours line above this
    panel, so they're not repeated here."""
    return {
        "state": "complete",
        "teg_num": teg_num,
        "report_summary": get_edition_summary(teg_num),
        **_standings_table_context(teg_num, _honours_by_player(teg_num)),
    }


@router.get("/contents/panel")
def contents_panel(request: Request, teg: int = Query(...), state: str = Query(...),
                    rounds: int = Query(None)):
    # HTMX fallback for both states: the main page renders the instant
    # headline/context/actions immediately from the two status CSVs (plus,
    # for complete, the report headline -- resolved synchronously in
    # get_tournament_state() since its *text* depends on report
    # availability and can't defer without a flash), and this partial fills
    # in the standings table once cached_round_data() has loaded, instead of
    # blocking the initial response on a cold parquet load.
    # `rounds` (state.rounds_played) is in-progress only, for the
    # "Standings after Round N" heading -- not re-derived here.
    panel = _in_progress_panel(teg) if state == "in_progress" else _complete_panel(teg)
    return templates.TemplateResponse("partials/_contents_panel.html", {
        "request": request,
        "panel": panel,
        "rounds_played": rounds,
    })
