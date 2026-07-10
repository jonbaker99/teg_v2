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
def contents_page(request: Request):
    # Contents-specific column arrangement (does not reorder NAV_SECTIONS, which
    # drives the nav bar). Columns fill top-to-bottom:
    #   1: TEG History / Records & PBs   2: Latest TEG / Scorecards   3: Scoring
    by_label = {s["label"]: s for s in NAV_SECTIONS}
    layout = [
        ("TEG History", "Records & PBs"),
        ("Latest TEG", "Scorecards"),
        ("Scoring analysis",),
    ]
    columns = [[by_label[label] for label in col if label in by_label] for col in layout]
    return templates.TemplateResponse("contents.html", {
        "request": request,
        "active_page": "contents",
        "columns": columns,
    })
