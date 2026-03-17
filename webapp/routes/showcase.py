"""Showcase route — UI component gallery for theme evaluation."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/showcase")
async def showcase_page(request: Request):
    return templates.TemplateResponse("showcase.html", {
        "request": request,
        "active_page": "showcase",
    })
