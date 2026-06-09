"""Contents route — site map of all sections and pages.

Mirrors the Streamlit Contents page (streamlit/contents.py): lists every
section and its pages as links, driven by the shared NAV_SECTIONS structure.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from webapp.nav import NAV_SECTIONS

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/contents")
async def contents_page(request: Request):
    return templates.TemplateResponse("contents.html", {
        "request": request,
        "active_page": "contents",
        "sections": NAV_SECTIONS,
    })
