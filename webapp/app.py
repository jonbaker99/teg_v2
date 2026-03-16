"""FastAPI application — TEG Golf Tournament Stats."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webapp.routes import leaderboard, charts, records
from webapp.theme import get_theme, THEMES

app = FastAPI(title="TEG Stats")

# Serve static files (CSS themes etc.)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.middleware("http")
async def theme_middleware(request: Request, call_next):
    """Inject current theme into request.state for all routes."""
    request.state.theme = get_theme(request)
    request.state.themes = THEMES
    return await call_next(request)


# Mount route routers
app.include_router(leaderboard.router)
app.include_router(charts.router)
app.include_router(records.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/leaderboard")
