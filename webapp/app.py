"""FastAPI application — TEG Golf Tournament Stats."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from webapp.routes import leaderboard, charts, records

app = FastAPI(title="TEG Stats")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Mount route routers
app.include_router(leaderboard.router)
app.include_router(charts.router)
app.include_router(records.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/leaderboard")
