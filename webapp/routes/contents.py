"""Contents route — current-TEG home page with the full site map below.

State-led home (I3/I5, revised): shows the in-progress TEG, the latest
completed TEG, or an honest no-data message, chosen by
`webapp.deps.get_tournament_state()`. The request's public site map renders
beneath it, with labels and links suited to the current tournament state.
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

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
from teg_analysis.analysis.handicaps import get_next_teg_and_check_if_in_progress_fast
from webapp.routes.latest import _current_handicap_tiles, _round_scoreboard_html
from teg_analysis.analysis.history import get_future_tegs
from teg_analysis.reporting.newspaper_edition import available_rounds, get_edition_summary
from teg_analysis.reporting.venue import build_venue_context

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

@router.get("/contents")
def contents_page(request: Request, view: str = Query("results")):
    sections = request.state.nav_sections
    state = get_tournament_state()
    # ?view=next is only meaningful between tournaments.
    view_ctx = _complete_view_context(request, view, state) if state["state"] == "complete" else {}
    return templates.TemplateResponse("contents.html", {
        **view_ctx,
        "request": request,
        "active_page": "contents",
        "sections": sections,
        "state": state,
        "sitemap_page_count": sum(len(s["pages"]) for s in sections),
        "sitemap_group_labels": ", ".join(s["label"] for s in sections),
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


# In-progress left-column panes, switched in place by /contents/pane.
PANES = ("standings", "round", "handicaps")
# Round-pane score types: Stableford first, since it decides the TEG.
ROUND_METRICS = (("Stableford", "Points"), ("GrossVP", "Gross"), ("Sc", "Score"), ("NetVP", "Net"))


def _standings_pane(teg_num: int) -> dict:
    """Standings (net, with a Gross column -- no separate gross line)."""
    return _standings_table_context(teg_num)


def _pane_context(view: str, teg_num: int, rounds_played: int, metric: str = "Stableford") -> dict:
    """One in-progress pane: standings, the latest round's scoreboard (the
    /latest-round default table) or current handicaps (the /handicaps
    phone list). Each links on to its full page."""
    if view == "round":
        metric = metric if metric in dict(ROUND_METRICS) else "Stableford"
        return {"round_html": _round_scoreboard_html(teg_num, rounds_played, metric, detail=False),
                "metric": metric, "metrics": ROUND_METRICS}
    if view == "handicaps":
        # Same TEG choice as /handicaps itself, so the two never disagree.
        _last, next_tegnum, _in_progress = get_next_teg_and_check_if_in_progress_fast()
        return _current_handicap_tiles(next_tegnum)
    return _standings_pane(teg_num)


def _in_progress_panel(teg_num: int) -> dict:
    """In-progress rich content: the standings pane + a round-report teaser
    when one exists."""
    report_summary = None
    rounds = available_rounds(teg_num)
    if rounds:
        report_summary = get_edition_summary(teg_num, rounds[-1])

    return {
        "state": "in_progress",
        "teg_num": teg_num,
        "report_summary": report_summary,
        **_standings_pane(teg_num),
    }


# Complete-state views, switched in place by /contents/view: the finished
# TEG's results, or the next TEG's rounds and handicaps.
COMPLETE_VIEWS = ("results", "next")


def _round_date_parts(date_str) -> dict:
    """'10/10/2026' -> weekday 'Sat', day '10 Oct', month 'October 2026'.
    Blank or unparseable dates come back empty, for the template's TBC."""
    try:
        dt = datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
    except (ValueError, TypeError):
        return {"weekday": "", "day": "", "month": ""}
    return {"weekday": dt.strftime("%a"), "day": dt.strftime("%-d %b"), "month": dt.strftime("%B %Y")}


def _text(value) -> str:
    """A CSV cell as display text: NaN/None become ''."""
    return "" if value is None or (isinstance(value, float) and value != value) else str(value).strip()


def _next_teg_context() -> dict:
    """The next TEG: area, when, each round's date and course (from
    round_info.csv once set up) and its handicaps. The area falls back to
    future_tegs.csv before any rounds are scheduled; anything unknown is
    left blank for the template to show as TBC."""
    _last, next_tegnum, _in_progress = get_next_teg_and_check_if_in_progress_fast()
    area, when, rounds = "", "", []
    try:
        venue = build_venue_context(next_tegnum)
    except ValueError:
        venue = None  # no round_info rows yet
    if venue:
        area = _text(venue["area"])
        for r in venue["rounds"]:
            rounds.append({
                "round": r["round"],
                **_round_date_parts(r["date"]),
                "course": _text(r["course"]),
                # A course's location shows on its first round only.
                "location": "" if any(x["course"] == _text(r["course"]) for x in rounds)
                            else _text(r["location"]),
            })
        when = next((r["month"] for r in rounds if r["month"]), "")
        if not when and venue["year"]:
            when = str(venue["year"])
    if not area or not when:
        future = get_future_tegs()
        row = future[future["TEGNum"] == next_tegnum] if not future.empty else future
        if not row.empty:
            area = area or _text(row.iloc[0]["Area"])
            when = when or _text(int(row.iloc[0]["Year"]))
    return {
        "teg_num": next_tegnum,
        "area": area,
        "when": when,
        "rounds": rounds,
        "handicaps": _current_handicap_tiles(next_tegnum),
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


@router.get("/contents/pane")
def contents_pane(request: Request, teg: int = Query(...), rounds: int = Query(...),
                  view: str = Query("standings"), metric: str = Query("Stableford")):
    # In-progress only: swaps the left column between standings, the latest
    # round and handicaps without leaving Contents.
    view = view if view in PANES else "standings"
    return templates.TemplateResponse("partials/_contents_pane.html", {
        "request": request,
        "pane": view,
        "teg_num": teg,
        "rounds_played": rounds,
        "panel": _pane_context(view, teg, rounds, metric),
    })


@router.get("/contents/view")
def contents_view(request: Request, view: str = Query("results")):
    # Complete state only: swaps the whole tournament section between the
    # finished TEG's results and the next TEG, without leaving Contents.
    return templates.TemplateResponse("partials/_contents_complete_view.html",
                                      _complete_view_context(request, view))


def _complete_view_context(request: Request, view: str, state: dict | None = None) -> dict:
    view = view if view in COMPLETE_VIEWS else "results"
    return {
        "request": request,
        "view": view,
        "state": state or get_tournament_state(),
        "next_teg": _next_teg_context() if view == "next" else None,
    }
