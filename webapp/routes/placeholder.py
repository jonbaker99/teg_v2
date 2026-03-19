"""Placeholder routes for pages not yet implemented."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _placeholder(request: Request, title: str, subtitle: str = None, note: str = None, active_page: str = ""):
    return templates.TemplateResponse("placeholder.html", {
        "request": request,
        "active_page": active_page,
        "title": title,
        "subtitle": subtitle,
        "note": note,
    })


# --- TEG History section ---
@router.get("/teg-reports")
async def teg_reports(request: Request):
    return _placeholder(request, "TEG Reports", active_page="teg-reports")


# --- Data section ---
@router.get("/data/update")
async def data_update(request: Request):
    return _placeholder(request, "Data Update", active_page="data")


@router.get("/data/reports")
async def data_reports(request: Request):
    return _placeholder(request, "Report Generation", active_page="data")


@router.get("/data/edit")
async def data_edit(request: Request):
    return _placeholder(request, "Data Edit", active_page="data")


@router.get("/data/delete")
async def data_delete(request: Request):
    return _placeholder(request, "Delete Data", active_page="data")


@router.get("/data/volumes")
async def data_volumes(request: Request):
    return _placeholder(request, "Data Volume Management", active_page="data")
