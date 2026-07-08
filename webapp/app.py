"""FastAPI application — TEG Golf Tournament Stats."""

from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webapp.routes import (
    leaderboard, charts, charts_proto, records, showcase, player, scorecard,
    placeholder, history, latest, performance, scoring, scorecards,
    eclectic, width_test, title_preview, smoke_test, reports, contents,
    admin, admin_round_setup, admin_teg_setup, admin_live_round, live_round,
    admin_new_round,
)
from webapp.nav import NAV_SECTIONS
from webapp.theme import (
    get_theme, THEMES,
    get_mode,
    get_title_style, TITLE_STYLES,
    get_card_header_style, CARD_HEADER_STYLES,
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

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


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
    request.state.nav_sections = NAV_SECTIONS
    return await call_next(request)


# Mount route routers
app.include_router(leaderboard.router)
app.include_router(charts.router)
app.include_router(charts_proto.router)
app.include_router(records.router)
app.include_router(showcase.router)
app.include_router(player.router)
app.include_router(scorecard.router)
app.include_router(eclectic.router)
app.include_router(placeholder.router)
app.include_router(history.router)
app.include_router(latest.router)
app.include_router(performance.router)
app.include_router(scoring.router)
app.include_router(scorecards.router)
app.include_router(width_test.router)
app.include_router(title_preview.router)
app.include_router(smoke_test.router)
app.include_router(reports.router)
app.include_router(contents.router)
app.include_router(admin.router)
app.include_router(admin_new_round.router)
app.include_router(admin_round_setup.router)
app.include_router(admin_teg_setup.router)
app.include_router(admin_live_round.router)
app.include_router(live_round.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/contents")
