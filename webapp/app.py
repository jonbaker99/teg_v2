"""FastAPI application — TEG Golf Tournament Stats."""

from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from webapp.routes import (
    leaderboard, charts, records, player, scorecard,
    history, latest, performance, scoring, scorecards,
    eclectic, reports, contents,
    admin, admin_round_setup, admin_teg_setup, admin_live_round, live_round,
    admin_new_round, admin_reports, design_lab, font_lab,
)
import webapp.deps as deps
from teg_analysis.reporting import newspaper_edition
from webapp.nav import MOBILE_SHORTCUTS, NAV_SECTIONS, navigation_for_teg
from webapp.theme import (
    get_theme, THEMES,
    get_mode,
    get_title_style, TITLE_STYLES,
    get_card_header_style, CARD_HEADER_STYLES,
    get_nav_cue, NAV_CUE_STYLES,
    get_font_pairing, get_font_pairing_override, FONT_PAIRINGS,
)

app = FastAPI(title="TEG Stats")

# Serve static files (CSS themes etc.)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
# Mobile design-review mockups (static, self-contained dummy pages — not part of
# the app's page hierarchy). Served at /mockups/ so they can be browsed locally.
app.mount(
    "/mockups",
    StaticFiles(directory=str(Path(__file__).parent / "mobile_mockups"), html=True),
    name="mockups",
)
# Newspaper report-layout prototypes (static, self-contained — a presentation
# trial, not part of the app's page hierarchy). Served at /report-layouts/.
app.mount(
    "/report-layouts",
    StaticFiles(directory=str(Path(__file__).parent / "report_layout_prototypes"), html=True),
    name="report-layouts",
)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _navigation_status() -> tuple[int, bool]:
    """Read tournament status once for the labels on this response."""
    in_progress_num, _ = deps.get_current_in_progress_teg_fast()
    if in_progress_num:
        return in_progress_num, True
    completed_num, _ = deps.get_last_completed_teg_fast()
    return completed_num or deps.FALLBACK_TEG_NUM, False


def _navigation_context() -> tuple[int, bool, tuple[str, str] | None]:
    """Resolve status and the best available report away from the event loop."""
    teg_num, in_progress = _navigation_status()
    if not in_progress and newspaper_edition.has_edition(teg_num):
        return teg_num, in_progress, (f"TEG {teg_num} report", f"/teg-reports?teg={teg_num}")
    rounds = newspaper_edition.available_rounds(teg_num)
    if rounds:
        round_num = max(rounds)
        return teg_num, in_progress, (
            f"Round {round_num} report", f"/teg-reports?teg={teg_num}&round={round_num}",
        )
    return teg_num, in_progress, None


@app.middleware("http")
async def theme_middleware(request: Request, call_next):
    """Inject current theme into request.state for all routes."""
    request.state.theme = get_theme(request)
    request.state.themes = THEMES
    request.state.mode = get_mode(request)
    request.state.title_style = get_title_style(request)
    request.state.title_styles = TITLE_STYLES
    request.state.card_header_style = get_card_header_style(request)
    request.state.card_header_styles = CARD_HEADER_STYLES
    request.state.nav_cue = get_nav_cue(request)
    request.state.nav_cue_styles = NAV_CUE_STYLES
    request.state.font_pairing = get_font_pairing(request)
    request.state.font_pairings = FONT_PAIRINGS
    request.state.font_pairing_override = get_font_pairing_override(request.state.font_pairing)
    if request.url.path.startswith(("/static/", "/mockups/", "/report-layouts/")):
        request.state.nav_sections = NAV_SECTIONS
        request.state.mobile_shortcuts = MOBILE_SHORTCUTS
    else:
        teg_num, in_progress, report = await run_in_threadpool(_navigation_context)
        request.state.public_live_rounds = await run_in_threadpool(deps.get_public_live_rounds_cached)
        request.state.nav_teg_label = f"TEG {teg_num}"
        request.state.nav_sections, request.state.mobile_shortcuts = navigation_for_teg(
            teg_num, in_progress=in_progress, report=report,
        )
    return await call_next(request)


# Mount route routers
app.include_router(leaderboard.router)
app.include_router(charts.router)
app.include_router(records.router)
app.include_router(player.router)
app.include_router(scorecard.router)
app.include_router(eclectic.router)
app.include_router(history.router)
app.include_router(latest.router)
app.include_router(performance.router)
app.include_router(scoring.router)
app.include_router(scorecards.router)
app.include_router(reports.router)
app.include_router(contents.router)
app.include_router(admin.router)
app.include_router(admin_new_round.router)
app.include_router(admin_round_setup.router)
app.include_router(admin_teg_setup.router)
app.include_router(admin_live_round.router)
app.include_router(live_round.router)
app.include_router(admin_reports.router)
app.include_router(design_lab.router)
app.include_router(font_lab.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/contents")
