"""Title preview route — compare page title styling options."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/title-preview")
async def title_preview(request: Request):
    return templates.TemplateResponse(
        "title_preview.html",
        {"request": request, "active_page": "title-preview"},
    )
